#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例库构建器
============

帮助新用户从自己的小说资源中提取标杆案例。

流程：
1. 格式转换（epub/mobi → txt）
2. 场景识别（自动识别关键场景）
3. 案例提取（提取高质量片段）
4. 质量评估（多维度评分）
5. 同步向量库（支持语义检索）
6. 自动发现新场景类型（NEW）

用法：
    python case_builder.py --init                    # 初始化案例库
    python case_builder.py --scan SOURCES...         # 扫描小说资源
    python case_builder.py --convert                 # 转换格式
    python case_builder.py --extract --limit 1000    # 提取案例
    python case_builder.py --discover                # 自动发现新场景类型
    python case_builder.py --sync                    # 同步到向量库
    python case_builder.py --status                  # 查看状态
"""

import argparse
import json
import re
import hashlib
import uuid
import sys
import time
import tempfile
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

# Windows GBK 控制台无法输出 ✓/✗ 等 Unicode 符号，保持 GBK 编码但替换无法编码的字符
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

# ──────────────────────────────────────────────────────────
# 段落级内容质量过滤器
# ──────────────────────────────────────────────────────────

_AD_PATTERN = re.compile(
    r"www\.\S+|http[s]?://\S+"
    r"|(?:免费|全文|txt|epub|mobi).{0,6}(?:下载|书库|阅读站|小说网)"
    r"|本书来自\S+"
    r"|(?:手机版|移动版)\s*(?:访问|阅读)"
    r"|书友群|QQ群|微信群|公众号"
    r"|推荐票|月票|打赏|(?:求|送)\s*(?:票|赞)",
    re.IGNORECASE,
)

_CHAPTER_LINE_PATTERN = re.compile(
    r"^第[一二三四五六七八九十百千万零\d]+[章节卷部回集]\s*"
)

_SENTENCE_ENDERS = frozenset('。！？…"』」》）】')

# 全局禁用词（任何场景都排除：AI 生成痕迹、说教文风）
_FORBIDDEN_PHRASES_GLOBAL = [
    "总之",
    "综上所述",
    "不得不说",
    "让人不禁",
    "作为一个",
    "值得一提的是",
    "不得不承认",
    "毋庸置疑",
    "众所周知",
    "诚然",
    "固然",
    "首先，其次，",
]

# 系统流专用词（仅在非系统流场景中禁用）
_FORBIDDEN_PHRASES_SYSTEM_FLOW = [
    "叮！恭喜宿主",
    "系统提示：",
    "【叮！】",
    "恭喜获得",
    "经验值+",
    "技能书×",
    "属性面板",
    "攻击力：",
    "防御力：",
    "品质：稀有",
    "品质：传说",
]

# 场景类型白名单（允许系统流词汇的场景）
_SYSTEM_FLOW_SCENE_TYPES = {"系统提示"}

# 合并后的禁用词列表（用于旧代码兼容）
_FORBIDDEN_PHRASES = _FORBIDDEN_PHRASES_GLOBAL + _FORBIDDEN_PHRASES_SYSTEM_FLOW


def _is_ad_paragraph(para: str) -> bool:
    """检测广告/下载站段落。返回 True 表示应过滤。"""
    return bool(_AD_PATTERN.search(para))


def _is_catalog_page(para: str) -> bool:
    """检测目录页：>= 3 行且 >= 40% 行符合章节标题格式。"""
    lines = [l.strip() for l in para.split("\n") if l.strip()]
    if len(lines) < 3:
        return False
    chapter_lines = sum(1 for l in lines if _CHAPTER_LINE_PATTERN.match(l))
    return chapter_lines / len(lines) >= 0.4


def _get_chinese_ratio(text: str) -> float:
    """汉字占总字符数的比例。"""
    if not text:
        return 0.0
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return chinese / len(text)


def _is_sentence_complete(para: str) -> bool:
    """段落末尾是否为合法句末符号。"""
    stripped = para.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_ENDERS


def _info_density(text: str) -> float:
    """词汇多样性（TTR）= 唯一 bigram 数 / 总 bigram 数。

    正常汉语小说（内容丰富）: 0.70+
    重复模板文本（打打打打打）: 0.10-
    普通内心独白（中等重复）: 0.50-0.70
    """
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 10:
        return 0.0
    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    if not bigrams:
        return 0.0
    return len(set(bigrams)) / len(bigrams)


# C4 风格行级过滤标志
_LINE_BAD_SUBSTRINGS = (
    "javascript",
    "cookie policy",
    "terms of use",
    "lorem ipsum",
    "用户协议",
    "隐私政策",
    "免责声明",
    "版权所有",
    "all rights reserved",
    "请扫描",
    "关注我们",
    "长按识别",
)


def _clean_lines(paragraph: str) -> str:
    """C4 风格行级清洗：逐行判定，丢弃广告/声明行后重新拼接。"""
    good_lines = []
    for line in paragraph.split("\n"):
        stripped = line.strip()
        if len(stripped) < 2:
            continue
        low = stripped.lower()
        if any(bad in low for bad in _LINE_BAD_SUBSTRINGS):
            continue
        if _AD_PATTERN.search(stripped):
            continue
        good_lines.append(stripped)
    return "\n".join(good_lines)


import math as _math
from collections import Counter as _Counter


def _bigram_entropy(text: str) -> float:
    """计算 bigram Shannon 熵。正常汉语小说 bigram 熵 > 7.0；模板化/重复文本 < 5.0。"""
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 20:
        return 0.0
    bigrams = [chars[i] + chars[i + 1] for i in range(len(chars) - 1)]
    counter = _Counter(bigrams)
    total = sum(counter.values())
    return -sum(
        (count / total) * _math.log2(count / total) for count in counter.values()
    )


# 获取项目根目录
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档）

# fail-fast：dedup 依赖，启动时立即检测，避免跑几小时后才报缺包
try:
    from tools.dedup_utils import compute_minhash, load_lsh, save_lsh  # noqa: F401
except ImportError as _e:
    raise ImportError(
        f"[!] 缺少依赖: {_e}\n    请先运行: pip install datasketch"
    ) from _e

# 尝试导入统一配置加载器
try:
    from core.config_loader import (
        get_config,
        get_qdrant_url,
        get_model_path,
        get_case_library_dir,
        get_collection_name,
        get_novel_sources,
        get_project_root,
        get_scene_writer_mapping_path,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False
    print("[case_builder] 警告: 未找到 config_loader，使用默认配置")


# 场景类型定义
SCENE_TYPES = {
    "开篇场景": {
        "keywords": ["第一章", "第1章", "序章", "开篇", "序幕"],
        "position": "start",
        "min_len": 500,
        "max_len": 2000,
    },
    "打脸场景": {
        "keywords": [
            "废物",
            "嘲讽",
            "震惊",
            "不可能",
            "震撼",
            "跪下",
            "死寂",
            "倒吸凉气",
            "瞳孔收缩",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "高潮场景": {
        "keywords": [
            "决战",
            "爆发",
            "生死",
            "极限",
            "巅峰",
            "终极",
            "最后",
            "拼尽全力",
        ],
        "position": "any",
        "min_len": 500,
        "max_len": 3000,
    },
    "战斗场景": {
        "keywords": [
            # 动作词组（比单字精确）
            "出招",
            "一招",
            "招式",
            "剑光",
            "剑气",
            "刀光",
            "刀气",
            "拳印",
            "掌力",
            "一拳",
            "一掌",
            "出手",
            "挥剑",
            "挥刀",
            # 战斗状态词（精确）
            "攻击",
            "防御",
            "闪避",
            "格挡",
            "反击",
            "斩出",
            # 修炼系战斗词（精确）
            "斗气",
            "灵力",
            "真气",
            "元力",
            "法力",
            "战气",
            # 通用激烈动作（高精确度）
            "杀招",
            "必杀",
            "绝招",
            "秘技",
        ],
        "neg_keywords": ["招呼", "招募", "招聘", "菜刀", "刀叉", "刀具"],
        "min_kw_score": 1.0,
        "position": "any",
        "min_len": 400,
        "max_len": 2500,
    },
    "对话场景": {
        "keywords": ['"', '"', "说道", "问道", "答道", "笑道", "沉声道"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "情感场景": {
        "keywords": [
            "泪",
            "感动",
            "心疼",
            "温暖",
            "苦涩",
            "复杂",
            "情绪",
            "眼眶",
            "哽咽",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "悬念场景": {
        "keywords": [
            "究竟",
            "到底",
            "秘密",
            "真相",
            "谜团",
            "不可思议",
            "难以置信",
            "未知",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "转折场景": {
        "keywords": ["突然", "意外", "却", "竟", "不料", "没想到", "反转", "转折"],
        "keyword_weights": {
            "却": 0.05,  # 近乎无效：最高频虚词
            "竟": 0.1,  # 低效：常用副词
            "突然": 0.4,
            "意外": 0.4,
            "不料": 1.0,
            "没想到": 1.0,
            "反转": 1.5,
            "转折": 1.5,
        },
        "min_kw_score": 1.0,  # 至少要有1个实质性词（不能只靠"却+竟"）
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "结尾场景": {
        "keywords": ["结局", "最终", "终于", "落幕", "尾声", "完结", "谢幕", "大结局"],
        "min_kw_score": 0.5,  # position=end 时放宽，但至少有1个结尾词
        "position": "end",
        "min_len": 300,
        "max_len": 1000,
    },
    "人物出场": {
        "keywords": ["首次", "第一次", "登场", "亮相", "出现在"],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    # ========== 新增场景类型 (18种) ==========
    "环境场景": {
        "keywords": [
            # 地理地貌（精确）
            "山脉",
            "森林",
            "宫殿",
            "城池",
            "荒野",
            "平原",
            "峡谷",
            # 氛围环境（需配合描写动词）
            "云雾弥漫",
            "月光如水",
            "风景如画",
            "景色宜人",
            "鸟语花香",
            "寂静无声",
            "万籁俱寂",
            # 建筑/场所描写
            "古朴",
            "巍峨",
            "雄伟",
            "幽深",
            "静谧",
        ],
        "neg_keywords": ["冲向", "追赶", "逃跑", "厮杀"],  # 动作段排除
        "min_kw_score": 1.5,  # 要求更高分，避免偶然出现
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "心理场景": {
        "keywords": [
            "心中",
            "内心",
            "思绪",
            "纠结",
            "矛盾",
            "挣扎",
            "沉思",
            "暗想",
            "心道",
            "默念",
            "思考",
            "明悟",
            "领悟",
            "顿悟",
            "自问",
            "心想",
            "暗忖",
        ],
        "neg_keywords": ["一拳", "一剑", "出手", "攻击", "斩出"],  # 动作段排除
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "社交场景": {
        "keywords": [
            "宴席",
            "聚会",
            "酒楼",
            "茶馆",
            "客套",
            "寒暄",
            "礼节",
            "应酬",
            "交际",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "冲突升级": {
        "keywords": [
            "矛盾",
            "冲突",
            "争执",
            "争吵",
            "对峙",
            "剑拔弩张",
            "火药味",
            "激化",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "阴谋揭露": {
        "keywords": [
            "阴谋",
            "诡计",
            "陷阱",
            "幕后",
            "黑手",
            "真相",
            "原来",
            "早就",
            "布局",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "团队组建": {
        "keywords": [
            "结盟",
            "联手",
            "合作",
            "同伴",
            "队友",
            "伙伴",
            "组队",
            "一起",
            "同行",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "修炼突破": {
        "keywords": [
            "突破",
            "晋级",
            "境界",
            "修炼",
            "感悟",
            "顿悟",
            "瓶颈",
            "冲击",
            "稳固",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "势力登场": {
        "keywords": [
            "宗门",
            "家族",
            "门派",
            "势力",
            "组织",
            "帮派",
            "商会",
            "联盟",
            "朝廷",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "成长蜕变": {
        "keywords": ["成长", "蜕变", "改变", "觉悟", "明白", "懂得", "成熟", "不再是"],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "伏笔设置": {
        "keywords": ["无意中", "不经意", "似乎", "隐约", "模糊", "若隐若现", "暗示"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "伏笔回收": {
        "keywords": ["原来如此", "终于明白", "想起", "回忆起", "当初", "之前", "那时"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "危机降临": {
        "keywords": [
            "危机",
            "灾难",
            "浩劫",
            "末日",
            "大难",
            "灭顶",
            "危在旦夕",
            "迫在眉睫",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "资源获取": {
        "keywords": [
            "宝物",
            "神器",
            "灵药",
            "秘籍",
            "传承",
            "收获",
            "得到",
            "获得",
            "得到",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "探索发现": {
        "keywords": ["发现", "意外", "惊喜", "遗迹", "秘境", "古墓", "洞穴", "密室"],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "情报揭示": {
        "keywords": ["消息", "情报", "传闻", "据说", "得知", "获悉", "打探", "消息"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "反派出场": {
        "keywords": ["反派", "敌人", "仇人", "对手", "恶人", "魔头", "邪修", "妖兽"],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
    "恢复休养": {
        "keywords": ["疗伤", "恢复", "休养", "调息", "静养", "养伤", "恢复", "痊愈"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "回忆场景": {
        "keywords": [
            "记得",
            "记得当年",
            "想起从前",
            "当年",
            "往事",
            "曾经",
            "回忆",
            "那时",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    # ========== 补充 5 种高频网文场景类型 ==========
    "境界突破": {
        "keywords": [
            "突破",
            "晋级",
            "境界提升",
            "大圆满",
            "瓶颈",
            "修为突破",
            "突破了",
            "晋入",
            "踏入",
            "跨入",
        ],
        "neg_keywords": ["突破重围", "突破防线", "突破封锁"],  # 排除军事突围
        "min_kw_score": 1.5,
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "拍卖竞标": {
        "keywords": [
            "拍卖",
            "起拍价",
            "灵石",
            "竞价",
            "出价",
            "加价",
            "落槌",
            "底价",
            "拍品",
            "竞拍",
            "成交价",
        ],
        "min_kw_score": 2.0,
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "试炼考核": {
        "keywords": [
            "试炼",
            "考核",
            "闯关",
            "关卡",
            "积分",
            "淘汰",
            "晋级赛",
            "选拔",
            "测试",
            "考验",
        ],
        "min_kw_score": 1.5,
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "悟道领悟": {
        "keywords": [
            "领悟",
            "感悟",
            "顿悟",
            "豁然贯通",
            "道韵",
            "明悟",
            "悟道",
            "参悟",
            "恍然大悟",
            "心境",
        ],
        "min_kw_score": 1.0,
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "系统提示": {
        "keywords": [
            "系统提示",
            "叮！",
            "恭喜宿主",
            "签到成功",
            "任务完成",
            "获得奖励",
            "属性面板",
            "经验值",
        ],
        "min_kw_score": 2.0,
        "position": "any",
        "min_len": 100,
        "max_len": 1000,
    },
}

# Q4：场景类型语义描述（用于 Zero-shot 语义校验）
SCENE_TYPE_DESCRIPTIONS = {
    "开篇场景": "故事开始，主角登场，世界观初步介绍，序章内容",
    "打脸场景": "被嘲讽轻视的主角在关键时刻反击，令对方震惊震慑的场面",
    "高潮场景": "故事最激烈的决战顶点，生死之战，全力爆发",
    "战斗场景": "双方交手对决，招式动作描写，攻防对抗",
    "对话场景": "人物之间的深刻对话交流，包含说话问答的场景",
    "情感场景": "人物间情感交流，感动落泪，深厚情谊或爱情表达",
    "悬念场景": "谜团未解，秘密揭露，真相浮现，令人好奇的悬疑情节",
    "转折场景": "情节发生意想不到的转折逆转，与之前预期完全相反",
    "结尾场景": "故事结尾，大局已定，落幕收场，人物命运终局",
    "人物出场": "重要人物首次登场亮相，外貌气质描写，给人深刻印象",
    "环境场景": "自然风景、建筑场所的详细描写，烘托氛围",
    "心理场景": "人物内心深处的思考挣扎，独白反思，心理活动描写",
    "成长场景": "人物经历磨练后成熟蜕变，觉悟顿悟，性格转变",
    "伏笔场景": "隐约暗示未来情节，埋下伏笔，若隐若现的线索",
    "揭秘场景": "真相大白，秘密被揭开，多年谜团终于解开",
    "突破场景": "主角修为境界突破，实力大幅提升，关键进阶",
    "羁绊场景": "人物之间深厚情谊，生死与共的情义，重要的情感连接",
    "危机场景": "主角或重要角色面临生死危机，险象环生，危在旦夕",
    "反派场景": "反派登场行动，阴谋诡计，邪恶势力的描写",
    "资源场景": "获得宝物资源，机缘际遇，重要物品或传承获取",
    "休整场景": "战后休养，修炼恢复，平静时光的日常描写",
    "探索场景": "探索未知地域，发现遗迹秘境，冒险旅途",
    "情报场景": "打探消息，获取情报，信息交流的场景",
    "势力场景": "门派宗门，势力格局，组织架构的描写",
    "契约场景": "签订盟约协议，重要承诺，誓言立约",
    "变故场景": "意外变故，计划被打乱，突发事件",
    "记忆场景": "回忆往事，回想过去，历史追述的片段",
    "传承场景": "传授功法技艺，接受指导，师徒传承",
    # ========== 补充 5 种高频网文场景类型描述 ==========
    "境界突破": "修炼者突破境界瓶颈，实力提升的关键时刻，感受到境界晋升的描写",
    "拍卖竞标": "拍卖场景，各方势力竞相出价争夺珍贵物品",
    "试炼考核": "进入试炼场地，闯过关卡或考核，展示实力争取晋级",
    "悟道领悟": "人物顿悟天道或功法要义，豁然贯通，境界心境发生质变",
    "系统提示": "游戏系统或金手指系统的提示弹窗，显示奖励、属性、任务完成",
}

# 题材关键词
GENRE_KEYWORDS = {
    "玄幻奇幻": [
        "修炼",
        "境界",
        "灵气",
        "丹药",
        "功法",
        "宗门",
        "武道",
        "元婴",
        "金丹",
    ],
    "武侠仙侠": ["江湖", "武功", "内功", "轻功", "剑法", "侠", "道长", "掌门"],
    "现代都市": ["总裁", "公司", "都市", "现代", "城市", "白领", "董事长"],
    "历史军事": ["将军", "皇帝", "朝代", "军队", "战争", "城池", "谋略"],
    "科幻灵异": ["星际", "飞船", "异能", "超能力", "未来", "科技", "异变"],
    "青春校园": ["学校", "校园", "同学", "老师", "青春", "班级", "考试"],
    "游戏竞技": ["游戏", "玩家", "副本", "BOSS", "等级", "装备", "公会"],
    "女频言情": ["王爷", "妃", "宫", "公主", "丞相", "将军府", "嫡女"],
    # Q2：新增题材类型
    "穿越重生": ["穿越", "重生", "穿书", "转世", "时空", "回到", "前世", "今生"],
    "盗墓探险": ["盗墓", "古墓", "陵寝", "机关", "棺椁", "摸金", "粽子", "倒斗"],
    "末日废土": ["末日", "丧尸", "末世", "病毒", "废土", "异变", "变异", "幸存"],
    "系统流": ["系统", "签到", "宿主", "任务面板", "属性面板", "称号", "商城", "兑换"],
    "女频古言": ["王爷", "侧妃", "嫡女", "庶女", "府中", "姨娘", "宫斗", "穿越成"],
}


@dataclass
class Case:
    """案例数据结构"""

    case_id: str
    scene_type: str
    genre: str
    novel_name: str
    content: str
    word_count: int
    quality_score: float
    emotion_value: float
    techniques: List[str]
    keywords: List[str]
    source_file: str
    chapter: int = 0
    position: str = ""


def _mobi_to_txt(task: tuple) -> str:
    """ProcessPoolExecutor worker：mobi → epub → txt。

    每个进程有独立内存，可以安全设置 tempfile.tempdir，不影响主进程或其他 worker。
    返回值："ok" / "skip" / "fail" / "err:..." / "no_lib"
    """
    path_str, dest_str, mobi_temp_str = task
    import re as _re, tempfile as _tf, shutil as _sh
    from pathlib import Path as _P

    dest = _P(dest_str)
    if dest.exists():
        return "skip"

    _P(mobi_temp_str).mkdir(parents=True, exist_ok=True)
    _tf.tempdir = mobi_temp_str  # 进程独占，无竞争

    tmpdir_path = None
    try:
        from mobi import extract
        result = extract(path_str)
        if isinstance(result, tuple):
            tmpdir_path = _P(result[0]) if result[0] else None
            epub_path = _P(result[1]) if len(result) > 1 else _P(result[0])
        else:
            epub_path = _P(result)

        if not epub_path.exists():
            return "fail"

        # epub → text（与 _read_epub 逻辑一致，不能跨进程调用实例方法）
        try:
            from ebooklib import epub as _epub
            book = _epub.read_epub(str(epub_path), options={"ignore_ncx": True})
            parts = []
            for item in book.get_items():
                html = None
                if hasattr(item, "get_body_content"):
                    try:
                        html = item.get_body_content()
                    except Exception:
                        pass
                if html is None and hasattr(item, "get_content") and hasattr(item, "media_type"):
                    if item.media_type and "html" in item.media_type.lower():
                        try:
                            html = item.get_content()
                        except Exception:
                            pass
                if html:
                    if isinstance(html, bytes):
                        html = html.decode("utf-8", errors="ignore")
                    text = _re.sub(r"<[^>]+>", "", html)
                    text = _re.sub(r"\s+", " ", text).strip()
                    if text:
                        parts.append(text)
            content = "\n\n".join(parts) if parts else None
        except Exception:
            content = None

        if content:
            dest.write_text(content, encoding="utf-8")
            return "ok"
        return "fail"

    except ImportError:
        return "no_lib"
    except Exception as e:
        return f"err:{e}"
    finally:
        if tmpdir_path and tmpdir_path.exists():
            if str(tmpdir_path).startswith(mobi_temp_str):
                _sh.rmtree(tmpdir_path, ignore_errors=True)


class CaseBuilder:
    """案例库构建器"""

    _mobi_lock = threading.Lock()  # tempfile.tempdir 是全局变量，mobi 解压需串行

    def __init__(self, case_library_dir: Path = None, config: Optional[Dict] = None):
        """
        初始化案例库构建器

        Args:
            case_library_dir: 案例库目录，None 则使用 config_loader 获取
            config: 配置字典，None 则使用 config_loader 获取
        """
        # 使用统一配置加载器
        if HAS_CONFIG_LOADER:
            self.config = config or get_config()
            self.qdrant_url = get_qdrant_url()
            self.collection_name = get_collection_name("case_library")
            self.case_library_dir = case_library_dir or get_case_library_dir()
            self.model_path = get_model_path()
            self.novel_sources = get_novel_sources()

            # 从 config 读取 case_builder 配置节
            cb_cfg = self.config.get("case_builder", {})
            self.quality_score_base = cb_cfg.get("quality_score_base", 4.5)
            self.quality_score_min = cb_cfg.get("quality_score_min", 5.0)
            self.bigram_entropy_min = cb_cfg.get("bigram_entropy_min", 5.0)
            self.bigram_entropy_penalty = cb_cfg.get("bigram_entropy_penalty", 1.5)
            self.content_max_len = cb_cfg.get("content_max_len", 3000)
            self.embed_truncate_len = cb_cfg.get("embed_truncate_len", 1000)
            self.boundary_delta_threshold = cb_cfg.get("boundary_delta_threshold", 0.12)
            self.embedding_window_size = cb_cfg.get("embedding_window_size", 3)
            self.semantic_min_similarity = cb_cfg.get("semantic_min_similarity", 0.20)
            self.position_start_window = cb_cfg.get("position_start_window", 5)
            self.position_end_window = cb_cfg.get("position_end_window", 5)
            self.genre_detection_threshold = cb_cfg.get("genre_detection_threshold", 3)
            self.genre_sample_size = cb_cfg.get("genre_sample_size", 5000)
            self.minhash_threshold = cb_cfg.get("minhash_threshold", 0.80)
        else:
            # 回退到旧方式
            import os

            self.config = config or {}
            self.qdrant_url = self.config.get(
                "qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333")
            )
            self.collection_name = self.config.get("collections", {}).get(
                "case_library", "case_library_v2"
            )
            self.case_library_dir = case_library_dir or Path(".case-library")
            self.model_path = self.config.get("model_path")
            self.novel_sources = self.config.get("novel_sources", {}).get(
                "directories", []
            )

            # 从 config 读取 case_builder 配置节（回退模式）
            cb_cfg = self.config.get("case_builder", {})
            self.quality_score_base = cb_cfg.get("quality_score_base", 4.5)
            self.quality_score_min = cb_cfg.get("quality_score_min", 5.0)
            self.bigram_entropy_min = cb_cfg.get("bigram_entropy_min", 5.0)
            self.bigram_entropy_penalty = cb_cfg.get("bigram_entropy_penalty", 1.5)
            self.content_max_len = cb_cfg.get("content_max_len", 3000)
            self.embed_truncate_len = cb_cfg.get("embed_truncate_len", 1000)
            self.boundary_delta_threshold = cb_cfg.get("boundary_delta_threshold", 0.12)
            self.embedding_window_size = cb_cfg.get("embedding_window_size", 3)
            self.semantic_min_similarity = cb_cfg.get("semantic_min_similarity", 0.20)
            self.position_start_window = cb_cfg.get("position_start_window", 5)
            self.position_end_window = cb_cfg.get("position_end_window", 5)
            self.genre_detection_threshold = cb_cfg.get("genre_detection_threshold", 3)
            self.genre_sample_size = cb_cfg.get("genre_sample_size", 5000)
            self.minhash_threshold = cb_cfg.get("minhash_threshold", 0.80)

        # 确保 case_library_dir 是 Path 对象
        if not isinstance(self.case_library_dir, Path):
            self.case_library_dir = Path(self.case_library_dir)

        # 目录结构
        self.converted_dir = self.case_library_dir / "converted"
        self.cases_dir = self.case_library_dir / "cases"
        self.logs_dir = self.case_library_dir / "logs"
        self.index_file = self.case_library_dir / "case_index.json"
        self.stats_file = self.case_library_dir / "case_stats.json"

        # mobi 解压临时目录（从 config 读取，默认 E:/tmp_mobi，不能放 C 盘）
        if HAS_CONFIG_LOADER:
            _paths = self.config.get("paths", {})
            self.mobi_temp_dir = Path(_paths.get("mobi_temp_dir", "E:/tmp_mobi"))
        else:
            self.mobi_temp_dir = Path("E:/tmp_mobi")

        # 内部状态
        self.novel_index: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()

    def init_structure(self):
        """初始化案例库目录结构"""
        print("\n" + "=" * 60)
        print("初始化案例库目录结构")
        print("=" * 60)

        # 创建目录
        dirs = [
            self.case_library_dir,
            self.converted_dir,
            self.cases_dir,
            self.logs_dir,
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ {d.name}/")

        # 创建场景类型目录
        for scene_type in SCENE_TYPES.keys():
            scene_dir = self.cases_dir / scene_type
            scene_dir.mkdir(exist_ok=True)
        print(f"    ✓ 场景目录 ({len(SCENE_TYPES)} 种)")

        # 创建README
        readme = self.case_library_dir / "README.md"
        readme_content = """# 案例库

案例库存储从优秀小说中提取的标杆片段，供创作参考。

## 目录结构

```
.case-library/
├── converted/          # 转换后的小说文件
├── cases/              # 提取的案例（按场景类型分类）
│   ├── 开篇场景/
│   ├── 打脸场景/
│   ├── 战斗场景/
│   └── ...
├── logs/               # 日志文件
├── case_index.json     # 案例索引
└── case_stats.json     # 统计信息
```

## 支持的场景类型

| 场景类型 | 提取标准 |
|----------|----------|
| 开篇场景 | 第一章开头500-2000字 |
| 打脸场景 | 包含嘲讽+震惊的片段 |
| 高潮场景 | 情绪顶点/决战时刻 |
| 战斗场景 | 完整战斗描写 |
| 对话场景 | 有意义的对话片段 |
| 情感场景 | 情感表达段落 |
| 悬念场景 | 悬念设置片段 |
| 转折场景 | 剧情转折点 |
| 结尾场景 | 章节结尾300-1000字 |
| 人物出场 | 人物首次亮相描写 |

## 快速构建

```bash
# 1. 扫描小说资源
python case_builder.py --scan "E:/小说资源"

# 2. 转换格式（epub/mobi → txt）
python case_builder.py --convert

# 3. 提取案例
python case_builder.py --extract --limit 5000

# 4. 同步到向量库
python case_builder.py --sync
```

## 质量标准

案例入库需要满足：
- 质量评分 ≥ 6.0
- 内容完整（非断裂片段）
- 无AI味/禁止项
- 有技法体现
"""
        readme.write_text(readme_content, encoding="utf-8")
        print(f"    ✓ README.md")

        # 创建配置文件
        config_file = self.case_library_dir / "config.json"
        if not config_file.exists():
            default_config = {
                "novel_sources": [],
                "scene_types": list(SCENE_TYPES.keys()),
                "quality_threshold": 6.0,
                "max_cases_per_type": 10000,
                "batch_size": 100,
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"    ✓ config.json")

        print("\n案例库初始化完成!")
        print(f"目录位置: {self.case_library_dir}")
        return True

    def scan_sources(self, source_dirs: List[Path] = None):
        """
        扫描小说资源目录

        Args:
            source_dirs: 要扫描的目录列表，None 则使用 config.json 中的 novel_sources
        """
        print("\n" + "=" * 60)
        print("扫描小说资源")
        print("=" * 60)

        # 如果未指定目录，使用配置中的 novel_sources
        if source_dirs is None or len(source_dirs) == 0:
            if self.novel_sources:
                source_dirs = [Path(d) for d in self.novel_sources]
                print(f"    使用配置中的 novel_sources: {len(source_dirs)} 个目录")
            else:
                print("    ✗ 未指定扫描目录，且 config.json 中未配置 novel_sources")
                return False

        total_files = 0
        file_types = {"txt": 0, "epub": 0, "mobi": 0, "other": 0}

        for source_dir in source_dirs:
            if not source_dir.exists():
                print(f"    ✗ {source_dir} 不存在")
                continue

            print(f"\n    扫描: {source_dir}")

            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower().lstrip(".")
                    if suffix in file_types:
                        file_types[suffix] += 1
                    else:
                        file_types["other"] += 1
                    total_files += 1

        print("\n" + "-" * 40)
        print(f"    总文件数: {total_files}")
        print(f"    TXT: {file_types['txt']}")
        print(f"    EPUB: {file_types['epub']}")
        print(f"    MOBI: {file_types['mobi']}")
        print(f"    其他: {file_types['other']}")

        # 保存扫描结果
        scan_result = {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total_files,
            "file_types": file_types,
            "source_dirs": [str(d) for d in source_dirs],
        }

        result_file = self.case_library_dir / "scan_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(scan_result, f, indent=2, ensure_ascii=False)

        print(f"\n    扫描结果已保存: {result_file}")
        return True

    # ── 统一文件读取（对齐路径二 base_extractor）────────────────────────

    def _read_novel(self, novel_path: Path) -> Optional[str]:
        """统一入口：读取任意格式小说，返回纯文本。失败返回 None。"""
        suffix = novel_path.suffix.lower()
        try:
            if suffix == ".txt":
                return self._read_txt(novel_path)
            elif suffix == ".epub":
                return self._read_epub(novel_path)
            elif suffix == ".mobi":
                return self._read_mobi(novel_path)
            elif suffix == ".pdf":
                return self._read_pdf(novel_path)
            elif suffix == ".docx":
                return self._read_docx(novel_path)
        except Exception as e:
            print(f"    [!] 读取失败 {novel_path.name}: {e}")
        return None

    @staticmethod
    def _cjk_ratio(text: str, sample: int = 3000) -> float:
        """CJK 字符在非空白字符中的占比（前 sample 字符采样）"""
        s = text[:sample].replace(" ", "").replace("\n", "").replace("\r", "")
        if not s:
            return 0.0
        cjk = sum(
            1 for c in s
            if "一" <= c <= "鿿" or "㐀" <= c <= "䶿"
        )
        return cjk / len(s)

    def _read_txt_meta(self, path: Path) -> "tuple[str, str, float]":
        """读取 txt，返回 (text, detected_enc, cjk_ratio)。
        检测链：BOM → charset-normalizer + CJK验证 → gb18030强制 → utf-8兜底
        """
        raw = path.read_bytes()

        def _wrap(text: str, enc: str) -> "tuple[str, str, float]":
            return text, enc, self._cjk_ratio(text)

        # BOM 快速路径
        if raw.startswith(b"\xef\xbb\xbf"):
            return _wrap(raw[3:].decode("utf-8", errors="replace"), "utf-8-bom")
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return _wrap(raw.decode("utf-16", errors="replace"), "utf-16")

        # charset-normalizer 检测 + CJK 验证
        try:
            from charset_normalizer import from_bytes
            result = from_bytes(raw).best()
            if result:
                text = str(result)
                ratio = self._cjk_ratio(text)
                if ratio >= 0.15:
                    return text, result.encoding, ratio
        except Exception:
            pass

        # CJK 比例不足 → 强制 gb18030 / utf-8
        # 用前 50KB 采样判断 CJK 比例，再对全文用 errors='ignore' 容忍少量非法字节
        for enc in ("gb18030", "utf-8"):
            try:
                sample = raw[:50000].decode(enc, errors="ignore")
                ratio = self._cjk_ratio(sample)
                if ratio >= 0.10:
                    return raw.decode(enc, errors="ignore"), enc + "-forced", ratio
            except LookupError:
                continue

        # 兜底（不崩，但内容可能有乱码）
        text = raw.decode("utf-8", errors="replace")
        return text, "utf-8-replace", self._cjk_ratio(text)

    def _read_txt(self, path: Path) -> Optional[str]:
        """txt 编码自动检测，返回解码后文本（供 _read_novel 调用）"""
        text, _, _ = self._read_txt_meta(path)
        return text or None

    def _read_epub(self, path: Path) -> Optional[str]:
        """epub 双路径 HTML 检测（对齐 base_extractor）"""
        try:
            from ebooklib import epub
            book = epub.read_epub(str(path), options={"ignore_ncx": True})
            parts = []
            for item in book.get_items():
                html = None
                if hasattr(item, "get_body_content"):
                    try:
                        html = item.get_body_content()
                    except Exception:
                        pass
                elif (
                    hasattr(item, "get_content")
                    and hasattr(item, "media_type")
                    and item.media_type
                    and "html" in item.media_type.lower()
                ):
                    try:
                        html = item.get_content()
                    except Exception:
                        pass
                if html:
                    if isinstance(html, bytes):
                        html = html.decode("utf-8", errors="ignore")
                    text = re.sub(r"<[^>]+>", "", html)
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        parts.append(text)
            return "\n\n".join(parts) if parts else None
        except ImportError:
            print("    [!] 需要安装 ebooklib: pip install ebooklib")
            return None
        except Exception as e:
            print(f"    [!] epub 读取失败 {path.name}: {e}")
            return None

    def _read_mobi(self, path: Path) -> Optional[str]:
        """mobi → epub 路径，安全 tempfile.tempdir 设置（串行锁保证多线程安全）"""
        self.mobi_temp_dir.mkdir(parents=True, exist_ok=True)
        with self._mobi_lock:
            return self._read_mobi_locked(path)

    def _read_mobi_locked(self, path: Path) -> Optional[str]:
        old_tempdir = tempfile.tempdir
        try:
            from mobi import extract
            tempfile.tempdir = str(self.mobi_temp_dir)
            result = extract(str(path))
            if isinstance(result, tuple):
                tmpdir, epub_path = result[0], (result[1] if len(result) > 1 else result[0])
            else:
                tmpdir, epub_path = None, result
            epub_path = Path(epub_path)
            if epub_path.exists():
                try:
                    return self._read_epub(epub_path)
                finally:
                    clean = Path(tmpdir) if tmpdir else epub_path.parent
                    if clean.exists() and str(clean).startswith(str(self.mobi_temp_dir)):
                        shutil.rmtree(clean, ignore_errors=True)
            return None
        except ImportError:
            print(f"    [!] 需要安装 mobi: pip install mobi")
            return None
        except Exception as e:
            print(f"    [!] mobi 读取失败 {path.name}: {e}")
            return None
        finally:
            tempfile.tempdir = old_tempdir

    def _read_pdf(self, path: Path) -> Optional[str]:
        """pdf → pdfminer.six（可选依赖）"""
        try:
            from pdfminer.high_level import extract_text
            content = extract_text(str(path))
            content = content.replace("\x00", "")
            content = "\n".join(l.strip() for l in content.splitlines() if l.strip())
            return content if content.strip() else None
        except ImportError:
            print(f"    [!] pdfminer.six 未安装，跳过 PDF: {path.name}")
            return None
        except Exception as e:
            print(f"    [!] pdf 读取失败 {path.name}: {e}")
            return None

    def _read_docx(self, path: Path) -> Optional[str]:
        """docx → python-docx（可选依赖）"""
        try:
            from docx import Document
            doc = Document(str(path))
            parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            return "\n\n".join(parts) if parts else None
        except ImportError:
            print(f"    [!] python-docx 未安装，跳过 DOCX: {path.name}")
            return None
        except Exception as e:
            print(f"    [!] docx 读取失败 {path.name}: {e}")
            return None

    def convert_files(
        self,
        source_dirs: Optional[List[Path]] = None,
        limit: int = 0,
        workers: int = 8,
    ):
        """转换小说格式（多线程 I/O 加速）"""
        print("\n" + "=" * 60)
        print("转换小说格式")
        print("=" * 60)

        if source_dirs:
            dirs = source_dirs
        elif self.novel_sources:
            dirs = [Path(d) for d in self.novel_sources]
        else:
            print("    ✗ 未配置小说来源目录")
            return False

        SUPPORTED = {".txt", ".epub", ".mobi", ".pdf", ".docx"}

        # 收集所有待转换文件，mobi 单独分组
        todo_other: List[Path] = []
        todo_mobi: List[Path] = []
        for source_dir in dirs:
            if not source_dir.exists():
                continue
            for fp in source_dir.rglob("*"):
                if fp.suffix.lower() not in SUPPORTED:
                    continue
                dest = self.converted_dir / f"{fp.stem}.txt"
                if dest.exists():
                    continue
                if fp.suffix.lower() == ".mobi":
                    todo_mobi.append(fp)
                else:
                    todo_other.append(fp)

        if limit > 0:
            # limit 按总量截断
            all_todo = todo_other + todo_mobi
            all_todo = all_todo[:limit]
            todo_other = [f for f in all_todo if f.suffix.lower() != ".mobi"]
            todo_mobi  = [f for f in all_todo if f.suffix.lower() == ".mobi"]

        total = len(todo_other) + len(todo_mobi)
        mobi_workers = max(1, min(workers, 4))
        print(f"    待转换: {total} 本（非mobi {len(todo_other)} 本 workers={workers}，mobi {len(todo_mobi)} 本 workers={mobi_workers}）")

        ok = fail = done = 0
        fail_log = self.case_library_dir / "convert_failures.txt"
        quality_log = self.case_library_dir / "convert_quality.tsv"
        _quality_lock = threading.Lock()

        # 写质量日志头（首次运行时）
        if not quality_log.exists():
            quality_log.write_text(
                "file\tresult\tencoding\tcjk_ratio\treason\n", encoding="utf-8"
            )

        def _log_fail(name: str, reason: str = ""):
            with open(fail_log, "a", encoding="utf-8") as f:
                f.write(f"{name}\t{reason}\n")

        def _log_quality(name: str, result: str, enc: str, ratio: float, reason: str = ""):
            suspicious = "[!] " if ratio < 0.10 and result == "ok" else ""
            with _quality_lock:
                with open(quality_log, "a", encoding="utf-8") as f:
                    f.write(f"{suspicious}{name}\t{result}\t{enc}\t{ratio:.3f}\t{reason}\n")

        # ── 非 mobi：ThreadPoolExecutor（线程安全）──────────────────────
        def _do_one(fp: Path) -> tuple:
            dest = self.converted_dir / f"{fp.stem}.txt"
            if dest.exists():
                return "skip", fp.name, "", "", 0.0
            enc = ""
            ratio = 0.0
            if fp.suffix.lower() == ".txt":
                content, enc, ratio = self._read_txt_meta(fp)
            else:
                content = self._read_novel(fp)
            if content:
                dest.write_text(content, encoding="utf-8")
                return "ok", fp.name, "", enc, ratio
            return "fail", fp.name, "内容为空或解析失败", enc, ratio

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_do_one, fp): fp for fp in todo_other}
            for fut in as_completed(futs):
                r, name, reason, enc, ratio = fut.result()
                done += 1
                if r == "ok":
                    ok += 1
                    _log_quality(name, "ok", enc, ratio)
                elif r == "fail":
                    fail += 1
                    _log_fail(name, reason)
                    _log_quality(name, "fail", enc, ratio, reason)
                if done % 200 == 0:
                    print(f"    进度: {done}/{total}，成功 {ok}，失败 {fail}")

        # ── mobi：ProcessPoolExecutor（每进程独立 tempfile.tempdir）────
        if todo_mobi:
            from concurrent.futures import ProcessPoolExecutor
            mobi_temp_str = str(self.mobi_temp_dir)
            task_map = {
                (str(fp), str(self.converted_dir / f"{fp.stem}.txt"), mobi_temp_str): fp
                for fp in todo_mobi
            }
            with ProcessPoolExecutor(max_workers=mobi_workers) as ex:
                futs = {ex.submit(_mobi_to_txt, t): t for t in task_map}
                for fut in as_completed(futs):
                    task = futs[fut]
                    fp = task_map[task]
                    done += 1
                    res = fut.result()
                    if res == "ok":
                        ok += 1
                    elif res != "skip":
                        fail += 1
                        _log_fail(fp.name, res)  # res 含 "err:..." 或 "fail"/"no_lib"
                    if done % 200 == 0:
                        print(f"    进度: {done}/{total}，成功 {ok}，失败 {fail}")

        print(f"\n转换完成: {ok} 成功, {fail} 失败")
        return True

    def extract_cases(
        self,
        limit: int = 0,
        scene_types: Optional[List[str]] = None,
        embed_batch: int = 128,
    ):
        """提取案例（Q3/Q4 批量推理，每本书只调两次 BGE-M3 而非逐候选调用）"""
        print("\n" + "=" * 60)
        print("提取案例")
        print("=" * 60)

        target_scenes = scene_types or list(SCENE_TYPES.keys())
        print(f"    目标场景: {len(target_scenes)} 种")

        # 加载 BGE-M3（可选，失败则跳过 Q3/Q4）
        _bge_model = None
        _scene_anchors = None
        try:
            from FlagEmbedding import BGEM3FlagModel
            from core.config_loader import get_device, get_model_path

            device = get_device()
            model_path = get_model_path()
            _bge_model = BGEM3FlagModel(
                model_path or "BAAI/bge-m3", use_fp16=True, device=device
            )
            print("    [Q3] BGE-M3 已加载，启用场景边界验证")
            _scene_anchors = self._build_scene_type_anchors(_bge_model)
            if _scene_anchors:
                print(f"    [Q4] 场景类型锚向量已构建，启用 zero-shot 语义校验")
        except Exception as e:
            print(f"    [Q3/Q4] BGE-M3 加载失败，跳过边界验证和语义校验: {e}")

        novel_files = list(self.converted_dir.glob("*.txt"))
        if not novel_files:
            print("    ✗ 未找到转换后的小说文件，请先运行 --convert")
            return False

        print(f"    小说文件: {len(novel_files)} 本")
        print(f"    提取限制: {limit if limit > 0 else '无限制'} 条")

        progress_dir = self.converted_dir / ".extract_progress"
        progress_dir.mkdir(parents=True, exist_ok=True)

        partial_path = self.case_library_dir / "extract_partial.jsonl"
        all_cases: List[Case] = []
        if partial_path.exists():
            print("    [恢复] 加载上次中断的部分结果...")
            _loaded = 0
            with partial_path.open("r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line:
                        try:
                            all_cases.append(Case(**json.loads(_line)))
                            _loaded += 1
                        except Exception:
                            pass
            print(f"    [恢复] 已加载 {_loaded} 条案例")
        _cases_at_last_save = len(all_cases)
        _novels_since_save = 0

        for i, novel_file in enumerate(novel_files):
            if limit > 0 and len(all_cases) >= limit:
                break

            novel_id = hashlib.md5(novel_file.stem.encode()).hexdigest()[:12]
            processed_marker = progress_dir / f".processed_{novel_id}"
            if processed_marker.exists():
                continue

            try:
                content = self._read_novel(novel_file)
                if not content:
                    continue
                novel_name = novel_file.stem
                genre = self._detect_genre(content[:5000])
                paragraphs = self._split_paragraphs(content)

                # ── Phase 1: Q1/Q2 CPU 筛选，不调 BGE-M3 ──────────────
                # 返回 (para_idx, scene_type, case)，供后续批量 Q3/Q4 使用
                raw: List[tuple] = []
                for scene_type in target_scenes:
                    if limit > 0 and len(all_cases) + len(raw) >= limit:
                        break
                    scene_config = SCENE_TYPES.get(scene_type, {})
                    for para_idx, case in self._extract_scene_cases(
                        paragraphs=paragraphs,
                        scene_type=scene_type,
                        scene_config=scene_config,
                        novel_name=novel_name,
                        genre=genre,
                        source_file=novel_file.name,
                        bge_model=None,          # Phase1: 不做语义验证
                        scene_anchors=None,
                        _return_indices=True,
                    ):
                        raw.append((para_idx, scene_type, case))

                if not raw:
                    processed_marker.touch()
                    continue

                # ── Phase 2: 批量 BGE-M3（全书候选一次性推理）──────────
                if _bge_model is not None:
                    import numpy as np

                    n = len(raw)
                    # Q3：每个候选构造 [before_window, after_window] 共 2n 条
                    q3_texts = []
                    q3_do = []  # True=做 Q3，False=position 非 any 跳过
                    for para_idx, scene_type, _ in raw:
                        pos = SCENE_TYPES.get(scene_type, {}).get("position", "any")
                        if pos == "any":
                            before = " ".join(
                                paragraphs[max(0, para_idx - self.embedding_window_size): para_idx]
                            )
                            after = " ".join(
                                paragraphs[para_idx: para_idx + self.embedding_window_size]
                            )
                            q3_texts += [before, after]
                            q3_do.append(True)
                        else:
                            q3_texts += ["", ""]
                            q3_do.append(False)

                    # Q4：每个候选的正文截断文本（n 条）
                    q4_texts = [c.content[: self.embed_truncate_len] for _, _, c in raw]

                    # 一次性编码 Q3（2n 条）
                    q3_vecs = _bge_model.encode(
                        q3_texts, batch_size=embed_batch, return_dense=True
                    )["dense_vecs"]
                    # 一次性编码 Q4（n 条）
                    q4_vecs = _bge_model.encode(
                        q4_texts, batch_size=embed_batch, return_dense=True
                    )["dense_vecs"]

                    for j, (para_idx, scene_type, case) in enumerate(raw):
                        # Q3 过滤
                        if q3_do[j]:
                            a = np.array(q3_vecs[j * 2])
                            b = np.array(q3_vecs[j * 2 + 1])
                            if a.any() and b.any():
                                sim = float(
                                    np.dot(a, b)
                                    / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
                                )
                                if (1.0 - sim) < self.boundary_delta_threshold:
                                    continue  # 场景中段噪音，丢弃

                        # Q4 语义校验
                        if _scene_anchors is not None:
                            vec = np.array(q4_vecs[j])
                            corrected = self._semantic_verify_case(
                                vec, scene_type, _scene_anchors
                            )
                            if corrected is None:
                                continue
                            if corrected != scene_type:
                                case = Case(
                                    case_id=case.case_id,
                                    scene_type=corrected,
                                    genre=case.genre,
                                    novel_name=case.novel_name,
                                    content=case.content,
                                    word_count=case.word_count,
                                    quality_score=case.quality_score,
                                    emotion_value=case.emotion_value,
                                    techniques=case.techniques,
                                    keywords=case.keywords + [f"[语义修正自:{scene_type}]"],
                                    source_file=case.source_file,
                                )
                        all_cases.append(case)
                else:
                    # 无 BGE-M3，直接取 Q1/Q2 结果
                    all_cases.extend(c for _, _, c in raw)

                processed_marker.touch()
                _novels_since_save += 1
                if _novels_since_save >= 200:
                    _new = all_cases[_cases_at_last_save:]
                    if _new:
                        with partial_path.open("a", encoding="utf-8") as _f:
                            for _c in _new:
                                _f.write(json.dumps(asdict(_c), ensure_ascii=False) + "\n")
                        _cases_at_last_save = len(all_cases)
                    _novels_since_save = 0
                    print(f"    [断点保存] 累计 {len(all_cases)} 条，进度已保存")

                if (i + 1) % 10 == 0:
                    print(
                        f"    处理进度: {i + 1}/{len(novel_files)}, 提取: {len(all_cases)}"
                    )

            except Exception as e:
                print(f"    ✗ {novel_file.name}: {e}")

        print(f"\n提取完成: {len(all_cases)} 条案例")

        # 刷写尚未保存的剩余案例
        _remaining = all_cases[_cases_at_last_save:]
        if _remaining:
            with partial_path.open("a", encoding="utf-8") as _f:
                for _c in _remaining:
                    _f.write(json.dumps(asdict(_c), ensure_ascii=False) + "\n")

        # MinHash LSH 近重复过滤（跨运行持久化）
        all_cases, dedup_stats = self._filter_near_duplicates(all_cases)
        print(
            f"\n[去重] 保留 {dedup_stats['kept']} 条，跳过近重复 {dedup_stats['skipped']} 条"
        )

        # 保存案例
        self._save_cases(all_cases)

        # 更新索引
        self._update_index(all_cases)

        # 全流程成功，清理断点文件
        if partial_path.exists():
            partial_path.unlink()

        return True

    def _detect_genre(self, content: str) -> str:
        """多位置采样题材检测（Q2：3段采样 + 扩充词库 + 默认未分类）"""
        sample_size = self.genre_sample_size
        threshold = self.genre_detection_threshold

        length = len(content)
        # 从开头、1/3处、2/3处各取 sample_size 字，避免只看开篇
        samples = [
            content[:sample_size],
            content[
                max(0, length // 3 - sample_size // 2) : length // 3 + sample_size // 2
            ],
            content[
                max(0, 2 * length // 3 - sample_size // 2) : 2 * length // 3
                + sample_size // 2
            ],
        ]

        total_scores: Dict[str, int] = {}
        for genre, keywords in GENRE_KEYWORDS.items():
            score = sum(sum(1 for kw in keywords if kw in sample) for sample in samples)
            total_scores[genre] = score

        if total_scores:
            best = max(total_scores, key=lambda g: total_scores[g])
            if total_scores[best] >= threshold:
                return best

        return "未分类"  # Q2：改为"未分类"，不再硬编码玄幻奇幻

    def _compute_boundary_delta(
        self,
        paragraphs: List[str],
        para_index: int,
        model,
        window: int = 3,
    ) -> float:
        """Q3：Embedding Delta Signal (Schneider et al. 2021).

        计算 para_index 位置的场景边界强度：
        - 用 BGE-M3 分别编码前 window 段和后 window 段的拼接文本
        - 返回两者的余弦距离（0~2，越大越像真实边界）
        - 降级：model=None 时返回 1.0（默认通过，不过滤）
        """
        if model is None:
            return 1.0

        before = " ".join(paragraphs[max(0, para_index - window) : para_index])
        after = " ".join(paragraphs[para_index : para_index + window])
        if not before or not after:
            return 1.0

        try:
            import numpy as np

            result = model.encode([before, after], batch_size=2, return_dense=True)
            vecs = result["dense_vecs"]
            a, b = np.array(vecs[0]), np.array(vecs[1])
            cosine_sim = float(
                np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
            )
            return 1.0 - cosine_sim  # cosine distance
        except Exception:
            return 1.0

    def _build_scene_type_anchors(self, model) -> Optional[Dict[str, Any]]:
        """Q4：为 28 种场景类型预计算锚向量（one-time，结果不缓存到磁盘）。

        Returns:
            {"type_name": np.ndarray} 或 None（model=None 时）
        """
        if model is None:
            return None
        try:
            import numpy as np

            types = list(SCENE_TYPE_DESCRIPTIONS.keys())
            descs = [SCENE_TYPE_DESCRIPTIONS[t] for t in types]
            result = model.encode(descs, batch_size=len(descs), return_dense=True)
            vecs = result["dense_vecs"]
            return {t: np.array(vecs[i]) for i, t in enumerate(types)}
        except Exception as e:
            print(f"    [Q4] 锚向量构建失败，跳过语义校验: {e}")
            return None

    def _semantic_verify_case(
        self,
        case_embedding,  # np.ndarray，案例段落的 BGE-M3 dense vector
        keyword_scene_type: str,
        anchors: Dict[str, Any],
        min_similarity: float = None,
    ) -> Optional[str]:
        """Q4：Zero-shot 语义校验场景类型。

        Returns:
            修正后的 scene_type，或 None（相似度过低，丢弃该案例）
        """
        if min_similarity is None:
            min_similarity = self.semantic_min_similarity

        import numpy as np

        best_type = keyword_scene_type
        best_sim = -1.0
        for stype, anchor_vec in anchors.items():
            sim = float(
                np.dot(case_embedding, anchor_vec)
                / (np.linalg.norm(case_embedding) * np.linalg.norm(anchor_vec) + 1e-9)
            )
            if sim > best_sim:
                best_sim = sim
                best_type = stype

        if best_sim < min_similarity:
            return None  # 语义相关度太低，丢弃

        return best_type  # 以语义分类为准

    def _split_paragraphs(self, content: str) -> List[str]:
        """分割段落，并过滤广告/目录/低质量内容。"""
        paragraphs = re.split(r"\n\s*\n", content)

        filtered = []
        for p in paragraphs:
            p = p.strip()
            # C4 风格行级清洗（先清理段内坏行）
            p = _clean_lines(p)
            # 长度门槛（清洗后再检查）
            if not (100 <= len(p) <= 5000):
                continue
            # 广告/下载站
            if _is_ad_paragraph(p):
                continue
            # 目录页
            if _is_catalog_page(p):
                continue
            # 汉字比例不足
            if _get_chinese_ratio(p) < 0.6:
                continue
            filtered.append(p)

        return filtered

    def _extract_scene_cases(
        self,
        paragraphs: List[str],
        scene_type: str,
        scene_config: Dict,
        novel_name: str,
        genre: str,
        source_file: str,
        bge_model=None,
        scene_anchors=None,
        _return_indices: bool = False,
    ):
        """提取特定场景类型的案例（含 Q3/Q4 语义验证）。

        _return_indices=True：跳过 Q3/Q4，返回 [(para_idx, Case), ...]，供批量推理用。
        _return_indices=False（默认）：直接做 Q3/Q4，返回 [Case, ...]。
        """
        cases = []

        keywords = scene_config.get("keywords", [])
        min_len = scene_config.get("min_len", 300)
        max_len = scene_config.get("max_len", 3000)
        position = scene_config.get("position", "any")

        for i, para in enumerate(paragraphs):
            # 长度检查
            if not (min_len <= len(para) <= max_len):
                continue

            # 位置检查
            if position == "start" and i > self.position_start_window:
                continue
            if position == "end" and i < len(paragraphs) - self.position_end_window:
                continue

            # 关键词检查（Q1：加权评分 + 负关键词过滤）
            neg_keywords = scene_config.get("neg_keywords", [])
            if any(nkw in para for nkw in neg_keywords):
                continue

            keyword_weights = scene_config.get("keyword_weights", {})
            min_kw_score = scene_config.get("min_kw_score", None)

            match_count = 0
            kw_score = 0.0
            matched_keywords = []
            for kw in keywords:
                if kw in para:
                    match_count += 1
                    matched_keywords.append(kw)
                    kw_score += keyword_weights.get(kw, 1.0)

            if min_kw_score is not None:
                # 新权重模式：用分数门槛
                if kw_score < min_kw_score:
                    continue
            else:
                # 兼容旧模式：至少2个关键词（position=any）
                if position == "any" and match_count < 2:
                    continue

            # 计算质量分
            quality_score = self._calculate_quality(
                para, match_count, kw_score, scene_type=scene_type
            )

            if quality_score < self.quality_score_min:
                continue

            # 创建案例
            case = Case(
                case_id=self._generate_case_id(para),
                scene_type=scene_type,
                genre=genre,
                novel_name=novel_name,
                content=para[: self.content_max_len],
                word_count=len(para),
                quality_score=quality_score,
                emotion_value=0.5,
                techniques=[],
                keywords=matched_keywords[:5],
                source_file=source_file,
            )

            # 批量推理模式：直接返回 (para_idx, case)，Q3/Q4 由调用方批量处理
            if _return_indices:
                cases.append((i, case))
                continue

            # Q3：边界验证（有 BGE-M3 时才做，失败降级通过）
            if bge_model is not None and position == "any":
                delta = self._compute_boundary_delta(
                    paragraphs, i, bge_model, window=self.embedding_window_size
                )
                if delta < self.boundary_delta_threshold:
                    continue  # 场景中段噪音，丢弃

            # Q4：zero-shot 语义校验（有锚向量时才做）
            if scene_anchors is not None and bge_model is not None:
                try:
                    import numpy as np

                    enc = bge_model.encode(
                        [para[: self.embed_truncate_len]],
                        batch_size=1,
                        return_dense=True,
                    )
                    para_vec = np.array(enc["dense_vecs"][0])
                    corrected_type = self._semantic_verify_case(
                        para_vec, scene_type, scene_anchors
                    )
                    if corrected_type is None:
                        continue  # 语义相关度过低，丢弃
                    if corrected_type != scene_type:
                        case = Case(
                            case_id=case.case_id,
                            scene_type=corrected_type,
                            genre=case.genre,
                            novel_name=case.novel_name,
                            content=case.content,
                            word_count=case.word_count,
                            quality_score=case.quality_score,
                            emotion_value=case.emotion_value,
                            techniques=case.techniques,
                            keywords=case.keywords + [f"[语义修正自:{scene_type}]"],
                            source_file=case.source_file,
                        )
                except Exception:
                    pass  # 降级：不影响结果

            cases.append(case)

        return cases

    def _calculate_quality(
        self,
        content: str,
        match_count: int,
        kw_score: float = 0.0,
        scene_type: str = "",
    ) -> float:
        """计算质量分（扩展版：禁用词 + 信息密度 + 句末完整性 + Q1加权分）"""
        score = self.quality_score_base  # 基础分（从 config 读取）

        # 关键词匹配加分（Q1：用加权分替代纯 match_count，上限 1.5）
        score += min(max(kw_score, match_count) * 0.3, 1.5)

        # 长度适中加分
        if 500 <= len(content) <= 2000:
            score += 0.5

        # 全局禁用词
        for phrase in _FORBIDDEN_PHRASES_GLOBAL:
            if phrase in content:
                score -= 0.5

        # 系统流词汇只在非系统流场景中禁用
        if scene_type not in _SYSTEM_FLOW_SCENE_TYPES:
            for phrase in _FORBIDDEN_PHRASES_SYSTEM_FLOW:
                if phrase in content:
                    score -= 0.5

        # 对话密度加分
        quote_count = content.count("\u201c") + content.count("\u201d")
        if quote_count >= 4:
            score += 0.3

        # 信息密度奖励（TTR阈值调整：>0.65 加分，<0.30 扣分）
        density = _info_density(content)
        if density > 0.65:
            score += 0.3
        elif density < 0.30:
            score -= 1.0

        # 句末完整性
        if not _is_sentence_complete(content):
            score -= 0.5

        # Bigram 熵（从 config 读取阈值和扣分值）
        if len(content) > 100:
            entropy = _bigram_entropy(content)
            if entropy < self.bigram_entropy_min:
                score -= self.bigram_entropy_penalty
            elif entropy > 8.0:
                score += 0.3

        return min(max(score, 0), 10)

    def _generate_case_id(self, content: str) -> str:
        """生成案例ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _filter_near_duplicates(
        self,
        cases: "List[Case]",
        index_path: Optional[Path] = None,
    ) -> "tuple[List[Case], Dict[str, int]]":
        """用 MinHash LSH 过滤近重复案例，并把新增案例写入持久化索引。

        Args:
            cases: 候选案例列表
            index_path: LSH pickle 路径；None 则用 case_library_dir/dedup_index.pkl

        Returns:
            (filtered_cases, stats) — stats keys: kept / skipped
        """
        from tools.dedup_utils import (
            compute_minhash,
            load_lsh,
            save_lsh,
        )

        if index_path is None:
            index_path = self.case_library_dir / "dedup_index.pkl"

        lsh, cache = load_lsh(index_path)
        kept: List[Case] = []
        skipped = 0

        for case in cases:
            m = compute_minhash(case.content)
            if lsh.query(m):
                skipped += 1
                continue
            lsh.insert(case.case_id, m)
            cache[case.case_id] = m
            kept.append(case)

        save_lsh(lsh, cache, index_path)
        return kept, {"kept": len(kept), "skipped": skipped}

    def _save_cases(self, cases: List[Case]):
        """保存案例到文件"""
        print("\n保存案例...")

        # 按场景类型分组保存
        for scene_type in SCENE_TYPES.keys():
            scene_cases = [c for c in cases if c.scene_type == scene_type]

            if not scene_cases:
                continue

            scene_dir = self.cases_dir / scene_type
            scene_dir.mkdir(exist_ok=True)

            for case in scene_cases:
                case_file = scene_dir / f"{case.case_id}.txt"
                case_file.write_text(case.content, encoding="utf-8")

                meta_file = scene_dir / f"{case.case_id}.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(case), f, indent=2, ensure_ascii=False)

            print(f"    {scene_type}: {len(scene_cases)} 条")

    def _update_index(self, cases: List[Case]):
        """更新案例索引"""
        index = {
            "total": len(cases),
            "by_scene": {},
            "by_genre": {},
            "updated": datetime.now().strftime("%Y-%m-%d"),
        }

        for case in cases:
            # 按场景统计
            if case.scene_type not in index["by_scene"]:
                index["by_scene"][case.scene_type] = 0
            index["by_scene"][case.scene_type] += 1

            # 按题材统计
            if case.genre not in index["by_genre"]:
                index["by_genre"][case.genre] = 0
            index["by_genre"][case.genre] += 1

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"\n索引更新: {self.index_file}")

    def sync_to_vectorstore(
        self,
        batch_size: int = 128,
        embed_batch: Optional[int] = None,
        skip_existing: bool = False,
    ):
        """同步案例到向量库（对齐路径二：HNSW禁用 + upsert重试 + embed/upsert流水线）"""
        import os
        from qdrant_client import QdrantClient
        from qdrant_client.models import (
            PointStruct, VectorParams, Distance,
            SparseVectorParams, OptimizersConfigDiff,
        )
        from FlagEmbedding import BGEM3FlagModel

        # embed_batch：CLI 传入 > config model.batch_size > 128
        if embed_batch is None:
            if HAS_CONFIG_LOADER:
                from core.config_loader import get_batch_size
                embed_batch = get_batch_size() or 128
            else:
                embed_batch = 128

        # HF_HOME：对齐路径二，防止 HuggingFace 默认写 C 盘
        hf_cache = self.config.get("model", {}).get("hf_cache_dir")
        if hf_cache:
            os.environ["HF_HOME"] = str(hf_cache)
            os.environ["TRANSFORMERS_CACHE"] = str(hf_cache)

        print("\n" + "=" * 60)
        print("同步案例到向量库")
        print("=" * 60)

        # 收集所有案例
        all_cases = []
        for scene_dir in self.cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue
            for meta_file in scene_dir.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        all_cases.append(json.load(f))
                except Exception:
                    continue

        if not all_cases:
            print("    ✗ 未找到案例")
            return False

        total = len(all_cases)
        print(f"    找到 {total:,} 条案例")

        # 连接 Qdrant
        print(f"    连接 Qdrant: {self.qdrant_url}")
        client = QdrantClient(url=self.qdrant_url, timeout=60)

        # --skip-existing：条数一致则跳过
        if skip_existing:
            try:
                existing = [c.name for c in client.get_collections().collections]
                if self.collection_name in existing:
                    info = client.get_collection(self.collection_name)
                    if info.points_count == total:
                        print(f"    [跳过] 已同步 {total:,} 条，条数一致")
                        return True
                    print(f"    [重建] Qdrant {info.points_count:,} 条 ≠ 本地 {total:,} 条，重建")
            except Exception as e:
                print(f"    [警告] 无法检查已有条数（{e}），继续")

        # 建/重建 collection，上传期间禁用 HNSW（避免越写越慢）
        existing = [c.name for c in client.get_collections().collections]
        if self.collection_name in existing:
            client.delete_collection(self.collection_name)
        client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                "dense": VectorParams(size=1024, distance=Distance.COSINE),
            },
            sparse_vectors_config={"sparse": SparseVectorParams()},
            optimizers_config=OptimizersConfigDiff(indexing_threshold=0),
        )
        print(f"    [创建] {self.collection_name}（上传期间禁用 HNSW）")

        # 加载模型
        print("\n加载 BGE-M3 模型...")
        from core.config_loader import get_device
        device = get_device()
        model = BGEM3FlagModel(
            self.model_path or "BAAI/bge-m3", use_fp16=True, device=device
        )
        print("    模型加载完成")

        def _upsert_with_retry(pts, retries=5, backoff=5):
            """upsert 失败自动重试，防 Qdrant 502 闪断"""
            for attempt in range(retries):
                try:
                    client.upsert(collection_name=self.collection_name, points=pts)
                    return
                except Exception as e:
                    if attempt == retries - 1:
                        raise
                    wait = backoff * (attempt + 1)
                    print(f"\n    [重试] {e.__class__.__name__}，{wait}s 后重试({attempt+1}/{retries})...")
                    time.sleep(wait)

        # 流水线：GPU 推理下一批时，后台线程上传当前批
        print("\n同步到向量库...")
        synced = 0
        t0 = time.time()
        pending_future: Optional[Future] = None
        pending_count = 0

        with ThreadPoolExecutor(max_workers=1) as executor:
            for batch_start in range(0, total, batch_size):
                batch = all_cases[batch_start: batch_start + batch_size]
                texts = [c.get("content", "")[:1000] for c in batch]

                out = model.encode(texts, batch_size=embed_batch, return_dense=True, return_sparse=True)

                points = []
                for j, case in enumerate(batch):
                    cid = case.get("case_id", f"case_{batch_start + j}")
                    points.append(PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, cid)),
                        vector={
                            "dense": out["dense_vecs"][j].tolist(),
                            "sparse": {
                                "indices": list(out["lexical_weights"][j].keys()),
                                "values": list(out["lexical_weights"][j].values()),
                            },
                        },
                        payload={
                            "novel_name": case.get("novel_name", ""),
                            "scene_type": case.get("scene_type", ""),
                            "genre": case.get("genre", ""),
                            "content": case.get("content", "")[:500],
                            "word_count": case.get("word_count", 0),
                            "quality_score": case.get("quality_score", 7.0),
                            "keywords": case.get("keywords", []),
                            "cross_genre_value": case.get("cross_genre_value", ""),
                            "source": case.get("source_file", ""),
                        },
                    ))

                # 等上一批完成
                if pending_future is not None:
                    pending_future.result()
                    synced += pending_count
                    elapsed = time.time() - t0
                    speed = synced / elapsed if elapsed > 0 else 0
                    eta = (total - synced) / speed if speed > 0 else 0
                    print(
                        f"  [{synced:>6}/{total}] {synced/total*100:5.1f}%"
                        f"  速度:{speed:.0f}条/s  剩余:{eta/60:.1f}min",
                        end="\r", flush=True,
                    )

                pending_future = executor.submit(_upsert_with_retry, points)
                pending_count = len(batch)

            if pending_future is not None:
                pending_future.result()
                synced += pending_count

        # 恢复 HNSW 阈值，触发后台索引构建
        client.update_collection(
            collection_name=self.collection_name,
            optimizer_config=OptimizersConfigDiff(indexing_threshold=20000),
        )
        print(f"\n  [索引] HNSW 后台构建已触发")

        elapsed = time.time() - t0
        info = client.get_collection(self.collection_name)
        print(f"✓ {self.collection_name}: {info.points_count:,} 条  耗时:{elapsed/60:.1f}min")
        return True

    def get_status(self):
        """获取案例库状态"""
        print("\n" + "=" * 60)
        print("案例库状态")
        print("=" * 60)

        # 检查目录
        print("\n[目录状态]")
        for d in [self.converted_dir, self.cases_dir, self.logs_dir]:
            if d.exists():
                file_count = len(list(d.rglob("*")))
                print(f"    {d.name}/: {file_count} 文件")
            else:
                print(f"    {d.name}/: 不存在")

        # 检查索引
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

            print("\n[案例统计]")
            print(f"    总计: {index.get('total', 0)}")

            print("\n    按场景:")
            for scene, count in index.get("by_scene", {}).items():
                print(f"      {scene}: {count}")

            print("\n    按题材:")
            for genre, count in index.get("by_genre", {}).items():
                print(f"      {genre}: {count}")
        else:
            print("\n[案例索引] 未创建")

        return True

    def discover_new_scenes(
        self,
        limit: int = 5000,
        min_cluster_size: int = 10,
        max_clusters: int = 20,
        auto_apply: bool = False,
    ):
        """
        自动发现新场景类型

        Args:
            limit: 最大收集片段数
            min_cluster_size: 最小聚类大小
            max_clusters: 最大发现场景数
            auto_apply: 是否自动应用高置信度场景
        """
        print("\n" + "=" * 60)
        print("自动发现新场景类型")
        print("=" * 60)

        # 导入发现器
        try:
            from scene_discovery import SceneDiscovery, CLUSTER_CONFIG
        except ImportError as e:
            print(f"    ✗ 未找到 scene_discovery.py: {e}")
            return False

        # 配置
        config = {
            "min_cluster_size": min_cluster_size,
            "max_clusters": max_clusters,
            "similarity_threshold": 0.75,
            "keyword_min_freq": 3,
            "keyword_top_k": 8,
        }

        # 创建发现器
        discoverer = SceneDiscovery(self.case_library_dir, config, SCENE_TYPES)

        # 收集未归类片段
        print(f"\n收集未归类片段 (限制: {limit})...")
        unclassified = discoverer.collect_unclassified_fragments(
            self.converted_dir, limit
        )

        if not unclassified:
            print("\n未发现未归类片段")
            return True

        # 发现新场景
        print("\n聚类分析中...")
        discovered = discoverer.discover_new_scenes(unclassified)

        if discovered:
            print(f"\n发现 {len(discovered)} 个新场景类型:")
            for i, scene in enumerate(discovered, 1):
                status_emoji = {
                    "active": "✅",
                    "can_activate": "🟡",
                    "pending_activation": "⏳",
                }.get(scene.suggested_status, "❓")
                print(f"\n  [{i}] {status_emoji} {scene.scene_name}")
                print(f"      关键词: {', '.join(scene.keywords[:5])}")
                print(
                    f"      片段数: {scene.fragment_count}, 置信度: {scene.confidence:.0%}"
                )
                print(f"      建议状态: {scene.suggested_status}")

            # 自动应用高置信度场景
            if auto_apply:
                high_confidence = [s for s in discovered if s.confidence >= 0.8]
                if high_confidence:
                    print(f"\n自动应用 {len(high_confidence)} 个高置信度场景...")
                    mapping_file = (
                        get_scene_writer_mapping_path()
                        if HAS_CONFIG_LOADER
                        else self.case_library_dir.parent
                        / ".vectorstore"
                        / "scene_writer_mapping.json"
                    )
                    discoverer.apply_discovered_scenes(
                        high_confidence,
                        None,  # 不更新SCENE_TYPES文件
                        mapping_file if mapping_file.exists() else None,
                    )
            else:
                print("\n下一步:")
                print("  1. 检查发现的场景是否合理")
                print("  2. 运行 python scene_discovery.py --apply 应用到配置")
        else:
            print("\n未发现新场景类型（样本不足或模式不明显）")

        return True

    def apply_discovered_scenes(self, confidence_threshold: float = 0.6):
        """
        应用发现的新场景类型

        Args:
            confidence_threshold: 置信度阈值
        """
        print("\n" + "=" * 60)
        print("应用发现的新场景类型")
        print("=" * 60)

        try:
            from scene_discovery import SceneDiscovery
        except ImportError:
            print("    ✗ 未找到 scene_discovery.py")
            return False

        # 检查发现结果文件
        discovery_dir = self.case_library_dir / "discovery"
        discovered_file = discovery_dir / "discovered_scenes.json"

        if not discovered_file.exists():
            print("    没有发现的新场景")
            print("    请先运行: python case_builder.py --discover")
            return False

        # 加载发现结果
        with open(discovered_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        from scene_discovery import DiscoveredScene

        scenes = [DiscoveredScene(**s) for s in data.get("scenes", [])]

        # 过滤置信度
        valid_scenes = [s for s in scenes if s.confidence >= confidence_threshold]

        if not valid_scenes:
            print(f"    没有置信度 >= {confidence_threshold:.0%} 的新场景")
            return False

        print(f"    待应用的场景: {len(valid_scenes)} 个")
        for scene in valid_scenes:
            print(f"      - {scene.scene_name} (置信度: {scene.confidence:.0%})")

        # 应用到配置
        discoverer = SceneDiscovery(self.case_library_dir, {}, SCENE_TYPES)
        mapping_file = (
            get_scene_writer_mapping_path()
            if HAS_CONFIG_LOADER
            else self.case_library_dir.parent
            / ".vectorstore"
            / "scene_writer_mapping.json"
        )

        success = discoverer.apply_discovered_scenes(
            valid_scenes, None, mapping_file if mapping_file.exists() else None
        )

        if success:
            print("\n✓ 应用完成!")
            print("  下次运行 --extract 时将包含新场景类型")

            # 更新内存中的SCENE_TYPES
            for scene in valid_scenes:
                if scene.confidence >= 0.6:
                    SCENE_TYPES[scene.scene_name] = {
                        "keywords": scene.keywords,
                        "position": "any",
                        "min_len": 300,
                        "max_len": 2000,
                        "discovered": True,
                        "discovery_confidence": scene.confidence,
                    }
        else:
            print("\n✗ 应用失败，请检查日志")

        return success


def main():
    parser = argparse.ArgumentParser(description="案例库构建器")
    parser.add_argument(
        "--case-library-dir", default=".case-library", help="案例库目录路径"
    )
    parser.add_argument("--config", help="配置文件路径")

    # 命令
    parser.add_argument("--init", action="store_true", help="初始化案例库")
    parser.add_argument(
        "--scan",
        nargs="*",
        metavar="DIR",
        help="扫描小说资源目录（无参数则使用 config.json 中的 novel_sources）",
    )
    parser.add_argument("--all", action="store_true", help="一键完整流程：convert → extract → sync（等价于分别执行三步）")
    parser.add_argument("--convert", action="store_true", help="转换小说格式")
    parser.add_argument("--extract", action="store_true", help="提取案例")
    parser.add_argument("--discover", action="store_true", help="自动发现新场景类型")
    parser.add_argument(
        "--apply-discovered", action="store_true", help="应用发现的新场景"
    )
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--status", action="store_true", help="查看状态")

    # 参数
    parser.add_argument("--limit", type=int, default=0, help="处理数量限制")
    parser.add_argument("--scenes", nargs="+", help="指定场景类型")
    parser.add_argument("--workers", type=int, default=8, help="--convert 并发线程数（I/O 密集，默认 8）")
    parser.add_argument("--batch-size", type=int, default=128, help="sync upsert 批次大小")
    parser.add_argument("--embed-batch", type=int, default=128, help="embedding 推理 batch size（GPU 建议 128）")
    parser.add_argument("--skip-existing", action="store_true", help="sync 时条数一致则跳过重建")
    parser.add_argument("--min-cluster-size", type=int, default=10, help="最小聚类大小")
    parser.add_argument("--max-clusters", type=int, default=20, help="最大发现场景数")
    parser.add_argument("--confidence", type=float, default=0.6, help="置信度阈值")
    parser.add_argument(
        "--auto-apply", action="store_true", help="自动应用高置信度场景"
    )

    args = parser.parse_args()

    # 加载配置（可选）
    config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    # 案例库目录（可选，None 则使用 config_loader）
    case_library_dir = None
    if args.case_library_dir and args.case_library_dir != ".case-library":
        case_library_dir = Path(args.case_library_dir)

    # 创建构建器（使用统一配置）
    builder = CaseBuilder(case_library_dir, config)

    # 执行命令
    if args.init:
        builder.init_structure()
    elif args.all:
        # 一键全流程：convert → extract → sync
        print("=== 一键全流程：convert → extract → sync ===")
        builder.convert_files(limit=args.limit, workers=args.workers)
        builder.extract_cases(
            limit=args.limit,
            scene_types=args.scenes,
            embed_batch=args.embed_batch,
        )
        builder.sync_to_vectorstore(
            batch_size=args.batch_size,
            embed_batch=args.embed_batch,
            skip_existing=args.skip_existing,
        )
    elif args.scan is not None:  # --scan 被指定（可能有参数也可能没有）
        # 支持有参数和无参数两种方式
        scan_dirs = [Path(d) for d in args.scan] if args.scan else None
        builder.scan_sources(scan_dirs)
    elif args.convert:
        builder.convert_files(limit=args.limit, workers=args.workers)
    elif args.extract:
        builder.extract_cases(
            limit=args.limit,
            scene_types=args.scenes,
            embed_batch=args.embed_batch,
        )
    elif args.discover:
        builder.discover_new_scenes(
            limit=args.limit or 5000,
            min_cluster_size=args.min_cluster_size,
            max_clusters=args.max_clusters,
            auto_apply=args.auto_apply,
        )
    elif args.apply_discovered:
        builder.apply_discovered_scenes(confidence_threshold=args.confidence)
    elif args.sync:
        builder.sync_to_vectorstore(
            batch_size=args.batch_size,
            embed_batch=args.embed_batch,
            skip_existing=args.skip_existing,
        )
    elif args.status:
        builder.get_status()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python case_builder.py --init")
        print(
            "  python case_builder.py --scan  # 自动使用 config.json 中的 novel_sources"
        )
        print("  python case_builder.py --convert")
        print("  python case_builder.py --extract --limit 1000")
        print(
            "  python case_builder.py --discover --limit 5000              # 发现新场景"
        )
        print(
            "  python case_builder.py --discover --auto-apply              # 发现并自动应用"
        )
        print("  python case_builder.py --apply-discovered --confidence 0.7 # 手动应用")
        print("  python case_builder.py --sync")
        print()
        print("配置来源: config.json (通过 config_loader.py 统一加载)")


if __name__ == "__main__":
    main()
