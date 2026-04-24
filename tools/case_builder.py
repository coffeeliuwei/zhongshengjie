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
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

# ──────────────────────────────────────────────────────────
# 段落级内容质量过滤器
# ──────────────────────────────────────────────────────────

_AD_PATTERN = re.compile(
    r'www\.\S+|http[s]?://\S+'
    r'|(?:免费|全文|txt|epub|mobi).{0,6}(?:下载|书库|阅读站|小说网)'
    r'|本书来自\S+'
    r'|(?:手机版|移动版)\s*(?:访问|阅读)'
    r'|书友群|QQ群|微信群|公众号'
    r'|推荐票|月票|打赏|(?:求|送)\s*(?:票|赞)',
    re.IGNORECASE,
)

_CHAPTER_LINE_PATTERN = re.compile(
    r'^第[一二三四五六七八九十百千万零\d]+[章节卷部回集]\s*'
)

_SENTENCE_ENDERS = frozenset('。！？…"』」》）】')

_FORBIDDEN_PHRASES = [
    "总之", "综上所述", "不得不说", "让人不禁",
    "作为一个", "值得一提的是", "不得不承认", "毋庸置疑",
    "众所周知", "诚然", "固然", "首先，其次，",
    "叮！恭喜宿主", "系统提示：", "【叮！】", "恭喜获得",
    "经验值+", "技能书×", "属性面板",
    "攻击力：", "防御力：", "品质：稀有", "品质：传说",
]


def _is_ad_paragraph(para: str) -> bool:
    """检测广告/下载站段落。返回 True 表示应过滤。"""
    return bool(_AD_PATTERN.search(para))


def _is_catalog_page(para: str) -> bool:
    """检测目录页：>= 3 行且 >= 40% 行符合章节标题格式。"""
    lines = [l.strip() for l in para.split('\n') if l.strip()]
    if len(lines) < 3:
        return False
    chapter_lines = sum(1 for l in lines if _CHAPTER_LINE_PATTERN.match(l))
    return chapter_lines / len(lines) >= 0.4


def _get_chinese_ratio(text: str) -> float:
    """汉字占总字符数的比例。"""
    if not text:
        return 0.0
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return chinese / len(text)


def _is_sentence_complete(para: str) -> bool:
    """段落末尾是否为合法句末符号。"""
    stripped = para.rstrip()
    return bool(stripped) and stripped[-1] in _SENTENCE_ENDERS


def _info_density(text: str) -> float:
    """信息密度 = 唯一字符数 / 非空白字符总数。"""
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return 0.0
    return len(set(chars)) / len(chars)


# C4 风格行级过滤标志
_LINE_BAD_SUBSTRINGS = (
    "javascript", "cookie policy", "terms of use", "lorem ipsum",
    "用户协议", "隐私政策", "免责声明", "版权所有", "all rights reserved",
    "请扫描", "关注我们", "长按识别",
)


def _clean_lines(paragraph: str) -> str:
    """C4 风格行级清洗：逐行判定，丢弃广告/声明行后重新拼接。"""
    good_lines = []
    for line in paragraph.split('\n'):
        stripped = line.strip()
        if len(stripped) < 2:
            continue
        low = stripped.lower()
        if any(bad in low for bad in _LINE_BAD_SUBSTRINGS):
            continue
        if _AD_PATTERN.search(stripped):
            continue
        good_lines.append(stripped)
    return '\n'.join(good_lines)


import math as _math
from collections import Counter as _Counter


def _bigram_entropy(text: str) -> float:
    """计算 bigram Shannon 熵。正常汉语小说 bigram 熵 > 7.0；模板化/重复文本 < 5.0。"""
    chars = [c for c in text if not c.isspace()]
    if len(chars) < 20:
        return 0.0
    bigrams = [chars[i] + chars[i+1] for i in range(len(chars) - 1)]
    counter = _Counter(bigrams)
    total = sum(counter.values())
    return -sum(
        (count / total) * _math.log2(count / total)
        for count in counter.values()
    )


# 获取项目根目录
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档）

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
            "招",
            "剑",
            "刀",
            "拳",
            "攻击",
            "防御",
            "技能",
            "招式",
            "斗气",
            "灵力",
        ],
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
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "结尾场景": {
        "keywords": [],
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
            "山脉",
            "森林",
            "宫殿",
            "城池",
            "荒野",
            "天空",
            "云雾",
            "月光",
            "风景",
            "景色",
        ],
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
        ],
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


class CaseBuilder:
    """案例库构建器"""

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
        else:
            # 回退到旧方式
            import os
            self.config = config or {}
            self.qdrant_url = self.config.get("qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333"))
            self.collection_name = self.config.get("collections", {}).get(
                "case_library", "case_library_v2"
            )
            self.case_library_dir = case_library_dir or Path(".case-library")
            self.model_path = self.config.get("model_path")
            self.novel_sources = self.config.get("novel_sources", {}).get(
                "directories", []
            )

        # 确保 case_library_dir 是 Path 对象
        if not isinstance(self.case_library_dir, Path):
            self.case_library_dir = Path(self.case_library_dir)

        # 目录结构
        self.converted_dir = self.case_library_dir / "converted"
        self.cases_dir = self.case_library_dir / "cases"
        self.logs_dir = self.case_library_dir / "logs"
        self.index_file = self.case_library_dir / "case_index.json"
        self.stats_file = self.case_library_dir / "case_stats.json"

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

    def convert_files(self, source_dirs: Optional[List[Path]] = None, limit: int = 0):
        """转换小说格式"""
        print("\n" + "=" * 60)
        print("转换小说格式")
        print("=" * 60)

        # 确定来源目录
        if source_dirs:
            dirs = source_dirs
        else:
            config_file = self.case_library_dir / "config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                dirs = [Path(d) for d in config.get("novel_sources", [])]
            else:
                print("    ✗ 未配置小说来源目录")
                return False

        converted_count = 0
        failed_count = 0

        for source_dir in dirs:
            if not source_dir.exists():
                continue

            for file_path in source_dir.rglob("*"):
                if limit and converted_count >= limit:
                    break

                suffix = file_path.suffix.lower()

                if suffix == ".txt":
                    # 直接复制
                    dest = self.converted_dir / f"{file_path.stem}.txt"
                    if not dest.exists():
                        try:
                            content = file_path.read_text(
                                encoding="utf-8", errors="ignore"
                            )
                            dest.write_text(content, encoding="utf-8")
                            converted_count += 1
                            if converted_count % 100 == 0:
                                print(f"    已转换: {converted_count}")
                        except Exception as e:
                            failed_count += 1

                elif suffix == ".epub":
                    # 需要ebooklib
                    try:
                        import ebooklib
                        from ebooklib import epub

                        book = epub.read_epub(str(file_path))
                        content = ""
                        for doc in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                            content += doc.get_content().decode(
                                "utf-8", errors="ignore"
                            )

                        # 简单清理HTML
                        content = re.sub(r"<[^>]+>", "", content)

                        dest = self.converted_dir / f"{file_path.stem}.txt"
                        dest.write_text(content, encoding="utf-8")
                        converted_count += 1

                    except ImportError:
                        print("    ✗ 需要安装 ebooklib: pip install ebooklib")
                        return False
                    except Exception as e:
                        failed_count += 1

                elif suffix == ".mobi":
                    # MOBI需要calibre
                    print(f"    ⚠ MOBI格式需要安装calibre，跳过: {file_path.name}")
                    failed_count += 1

        print(f"\n转换完成: {converted_count} 成功, {failed_count} 失败")
        return True

    def extract_cases(self, limit: int = 1000, scene_types: Optional[List[str]] = None):
        """提取案例"""
        print("\n" + "=" * 60)
        print("提取案例")
        print("=" * 60)

        # 确定场景类型
        target_scenes = scene_types or list(SCENE_TYPES.keys())
        print(f"    目标场景: {len(target_scenes)} 种")

        # 扫描已转换的文件
        novel_files = list(self.converted_dir.glob("*.txt"))

        if not novel_files:
            print("    ✗ 未找到转换后的小说文件")
            print("    请先运行: python case_builder.py --convert")
            return False

        print(f"    小说文件: {len(novel_files)} 本")
        print(f"    提取限制: {limit} 条")

        # 提取案例
        all_cases: List[Case] = []

        for i, novel_file in enumerate(novel_files):
            if len(all_cases) >= limit:
                break

            try:
                content = novel_file.read_text(encoding="utf-8", errors="ignore")
                novel_name = novel_file.stem

                # 检测题材
                genre = self._detect_genre(content[:5000])

                # 按段落分割
                paragraphs = self._split_paragraphs(content)

                # 按场景类型提取
                for scene_type in target_scenes:
                    if len(all_cases) >= limit:
                        break

                    scene_config = SCENE_TYPES.get(scene_type, {})
                    cases = self._extract_scene_cases(
                        paragraphs=paragraphs,
                        scene_type=scene_type,
                        scene_config=scene_config,
                        novel_name=novel_name,
                        genre=genre,
                        source_file=novel_file.name,
                    )

                    all_cases.extend(cases)

                if (i + 1) % 10 == 0:
                    print(
                        f"    处理进度: {i + 1}/{len(novel_files)}, 提取: {len(all_cases)}"
                    )

            except Exception as e:
                print(f"    ✗ {novel_file.name}: {e}")

        print(f"\n提取完成: {len(all_cases)} 条案例")

        # 保存案例
        self._save_cases(all_cases)

        # 更新索引
        self._update_index(all_cases)

        return True

    def _detect_genre(self, content: str) -> str:
        """检测题材"""
        scores = {}
        for genre, keywords in GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            scores[genre] = score

        if scores:
            best = max(scores, key=scores.get)
            if scores[best] >= 3:
                return best

        return "玄幻奇幻"  # 默认

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
    ) -> List[Case]:
        """提取特定场景类型的案例"""
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
            if position == "start" and i > 5:
                continue
            if position == "end" and i < len(paragraphs) - 5:
                continue

            # 关键词检查
            match_count = 0
            matched_keywords = []
            for kw in keywords:
                if kw in para:
                    match_count += 1
                    matched_keywords.append(kw)

            # 至少匹配2个关键词（或开篇/结尾场景特殊处理）
            if position == "any" and match_count < 2:
                continue

            # 计算质量分
            quality_score = self._calculate_quality(para, match_count)

            if quality_score < 6.0:
                continue

            # 创建案例
            case = Case(
                case_id=self._generate_case_id(para),
                scene_type=scene_type,
                genre=genre,
                novel_name=novel_name,
                content=para[:2000],
                word_count=len(para),
                quality_score=quality_score,
                emotion_value=0.5,
                techniques=[],
                keywords=matched_keywords[:5],
                source_file=source_file,
            )

            cases.append(case)

        return cases

    def _calculate_quality(self, content: str, match_count: int) -> float:
        """计算质量分（扩展版：禁用词 + 信息密度 + 句末完整性）"""
        score = 6.0  # 基础分

        # 关键词匹配加分（上限 1.5）
        score += min(match_count * 0.3, 1.5)

        # 长度适中加分
        if 500 <= len(content) <= 2000:
            score += 0.5

        # 禁用词（扩展版）
        for phrase in _FORBIDDEN_PHRASES:
            if phrase in content:
                score -= 0.5

        # 对话密度加分
        quote_count = content.count('\u201c') + content.count('\u201d')
        if quote_count >= 4:
            score += 0.3

        # 信息密度奖励
        density = _info_density(content)
        if density > 0.4:
            score += 0.3
        elif density < 0.15:
            score -= 1.0

        # 句末完整性
        if not _is_sentence_complete(content):
            score -= 0.5

        # Bigram 熵（<5.0 视为模板化文本，扣 1.5）
        if len(content) > 100:
            entropy = _bigram_entropy(content)
            if entropy < 5.0:
                score -= 1.5
            elif entropy > 8.0:
                score += 0.3

        return min(max(score, 0), 10)

    def _generate_case_id(self, content: str) -> str:
        """生成案例ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

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

    def sync_to_vectorstore(self, batch_size: int = 50):
        """同步案例到向量库"""
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import (
            PointStruct,
            VectorParams,
            Distance,
            SparseVectorParams,
        )
        from FlagEmbedding import BGEM3FlagModel

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
                        case_data = json.load(f)
                    all_cases.append(case_data)
                except:
                    continue

        if not all_cases:
            print("    ✗ 未找到案例")
            return False

        print(f"    找到 {len(all_cases)} 条案例")

        # 连接Qdrant（使用统一配置）
        print(f"    连接 Qdrant: {self.qdrant_url}")
        client = QdrantClient(url=self.qdrant_url)

        # 检查collection
        try:
            info = client.get_collection(self.collection_name)
            print(f"    {self.collection_name} 已存在 ({info.points_count:,} 条)")
        except:
            print(f"    创建 {self.collection_name}...")
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": VectorParams(size=1024, distance=Distance.COSINE)
                },
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )

        # 加载模型（使用统一配置）
        print("\n加载BGE-M3模型...")
        if self.model_path:
            print(f"    模型路径: {self.model_path}")
            model = BGEM3FlagModel(self.model_path, use_fp16=True, device="cpu")
        else:
            # 回退到自动下载
            print("    自动下载模型...")
            model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
        print("    模型加载完成")

        # 同步
        print("\n同步到向量库...")

        for i in range(0, len(all_cases), batch_size):
            batch = all_cases[i : i + batch_size]

            texts = [c.get("content", "") for c in batch]
            out = model.encode(texts, return_dense=True, return_sparse=True)

            points = []
            for j, case in enumerate(batch):
                point = PointStruct(
                        id=str(uuid.uuid5(uuid.NAMESPACE_DNS, case.get("case_id", f"case_{i+j}"))),
                    vector={
                        "dense": out["dense_vecs"][j].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][j].keys()),
                            "values": list(out["lexical_weights"][j].values()),
                        },
                    },
                    payload={
                        "name": case.get("novel_name", ""),
                        "scene_type": case.get("scene_type", ""),
                        "genre": case.get("genre", ""),
                        "content": case.get("content", "")[:500],
                        "word_count": case.get("word_count", 0),
                        "quality_score": case.get("quality_score", 7.0),
                        "keywords": case.get("keywords", []),
                        "source": case.get("source_file", ""),
                    },
                )
                points.append(point)

            client.upsert(self.collection_name, points)
            progress = min(i + batch_size, len(all_cases))
            pct = progress / len(all_cases) * 100
            print(f"    [{pct:.0f}%] {progress}/{len(all_cases)}")

        # 验证
        info = client.get_collection(self.collection_name)
        print(f"\n✓ {self.collection_name}: {info.points_count:,} 条")

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
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小")
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
    elif args.scan is not None:  # --scan 被指定（可能有参数也可能没有）
        # 支持有参数和无参数两种方式
        scan_dirs = [Path(d) for d in args.scan] if args.scan else None
        builder.scan_sources(scan_dirs)
    elif args.convert:
        builder.convert_files(limit=args.limit)
    elif args.extract:
        builder.extract_cases(limit=args.limit or 1000, scene_types=args.scenes)
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
        builder.sync_to_vectorstore(batch_size=args.batch_size)
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
