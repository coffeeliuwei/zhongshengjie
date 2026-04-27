#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诗词意象库构建器
================

构建云溪诗词能力所需的意象库，支持向量检索。

用法：
    python imagery_builder.py --init              # 初始化意象数据
    python imagery_builder.py --sync              # 同步到向量库
    python imagery_builder.py --test              # 测试检索功能
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加路径
PROJECT_ROOT = Path(__file__).parent.parent
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档），改用 core 包
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Windows编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 集合名称
IMAGERY_COLLECTION = "poetry_imagery_v2"


# ============================================================
# 意象数据
# ============================================================

# 通用意象数据
GENERAL_IMAGERY = [
    # ===== 自然意象 =====
    {
        "name": "明月",
        "category": "自然",
        "subcategory": "天象",
        "emotion_core": "思乡、怀人、永恒、孤独",
        "emotion_tags": ["思乡", "怀人", "永恒", "孤独", "清冷"],
        "emotion_mapping": {"思乡": 0.95, "怀人": 0.9, "永恒": 0.85, "孤独": 0.8},
        "description": "夜晚的月亮，象征思乡怀人、永恒不变",
        "usage_examples": [
            "举头望明月，低头思故乡",
            "明月几时有，把酒问青天",
            "海上生明月，天涯共此时",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "落花",
        "category": "自然",
        "subcategory": "植物",
        "emotion_core": "凋零、时光流逝、美好不再",
        "emotion_tags": ["凋零", "时光流逝", "伤感", "美好不再"],
        "emotion_mapping": {"凋零": 0.95, "时光流逝": 0.9, "伤感": 0.85},
        "description": "飘落的花朵，象征美好事物的消逝",
        "usage_examples": [
            "落花人独立，微雨燕双飞",
            "流水落花春去也，天上人间",
            "花谢花飞花满天，红消香断有谁怜",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "孤鸿",
        "category": "自然",
        "subcategory": "动物",
        "emotion_core": "孤独、漂泊、失群",
        "emotion_tags": ["孤独", "漂泊", "失意", "高洁"],
        "emotion_mapping": {"孤独": 0.95, "漂泊": 0.9, "失意": 0.85},
        "description": "孤独飞翔的大雁，象征游子漂泊、志士失意",
        "usage_examples": ["拣尽寒枝不肯栖，寂寞沙洲冷", "孤鸿号外野，翔鸟鸣北林"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "流水",
        "category": "自然",
        "subcategory": "水景",
        "emotion_core": "时光、离别、愁绪绵长",
        "emotion_tags": ["时光", "离别", "愁绪", "绵长"],
        "emotion_mapping": {"时光": 0.9, "离别": 0.85, "愁绪": 0.9},
        "description": "流动的水，象征时光流逝、愁绪无尽",
        "usage_examples": [
            "问君能有几多愁，恰似一江春水向东流",
            "抽刀断水水更流，举杯消愁愁更愁",
            "滚滚长江东逝水，浪花淘尽英雄",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "青山",
        "category": "自然",
        "subcategory": "山岳",
        "emotion_core": "永恒、归宿、隐逸",
        "emotion_tags": ["永恒", "归宿", "隐逸", "坚定"],
        "emotion_mapping": {"永恒": 0.9, "归宿": 0.85, "隐逸": 0.8},
        "description": "苍翠的山峦，象征永恒不变、归隐之地",
        "usage_examples": [
            "青山遮不住，毕竟东流去",
            "采菊东篱下，悠然见南山",
            "我见青山多妩媚，料青山见我应如是",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "夕阳",
        "category": "自然",
        "subcategory": "天象",
        "emotion_core": "暮年、衰败、苍凉",
        "emotion_tags": ["暮年", "衰败", "苍凉", "眷恋"],
        "emotion_mapping": {"暮年": 0.9, "衰败": 0.85, "苍凉": 0.9},
        "description": "傍晚的太阳，象征英雄迟暮、王朝末路",
        "usage_examples": [
            "夕阳无限好，只是近黄昏",
            "古道西风瘦马，夕阳西下",
            "山映斜阳天接水，芳草无情，更在斜阳外",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "残阳",
        "category": "自然",
        "subcategory": "天象",
        "emotion_core": "战争后、凄凉、余晖",
        "emotion_tags": ["战争", "凄凉", "余晖", "血色"],
        "emotion_mapping": {"战争": 0.9, "凄凉": 0.9, "余晖": 0.85},
        "description": "将落未落的太阳，多用于战争后、悲壮场景",
        "usage_examples": ["残阳如血染征袍", "一道残阳铺水中，半江瑟瑟半江红"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "寒星",
        "category": "自然",
        "subcategory": "天象",
        "emotion_core": "孤寂、高洁、冷眼旁观",
        "emotion_tags": ["孤寂", "高洁", "冷峻", "遥远"],
        "emotion_mapping": {"孤寂": 0.9, "高洁": 0.85, "冷峻": 0.8},
        "description": "清冷的星星，象征隐士、孤高之士",
        "usage_examples": ["迢迢牵牛星，皎皎河汉女", "昨夜星辰昨夜风"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "浮云",
        "category": "自然",
        "subcategory": "天象",
        "emotion_core": "漂泊无定、功名虚幻",
        "emotion_tags": ["漂泊", "虚幻", "游子", "无常"],
        "emotion_mapping": {"漂泊": 0.95, "虚幻": 0.85, "游子": 0.9},
        "description": "飘动的云，象征游子漂泊、功名虚幻",
        "usage_examples": [
            "浮云游子意，落日故人情",
            "不畏浮云遮望眼，自缘身在最高层",
            "总为浮云能蔽日，长安不见使人愁",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "长风",
        "category": "自然",
        "subcategory": "气象",
        "emotion_core": "豪迈、志向远大",
        "emotion_tags": ["豪迈", "壮志", "远行", "力量"],
        "emotion_mapping": {"豪迈": 0.95, "壮志": 0.9, "远行": 0.85},
        "description": "强劲的风，象征豪迈壮志、远大理想",
        "usage_examples": [
            "长风破浪会有时，直挂云帆济沧海",
            "长风万里送秋雁，对此可以酣高楼",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "秋雨",
        "category": "自然",
        "subcategory": "气象",
        "emotion_core": "愁思、凄凉、离别",
        "emotion_tags": ["愁思", "凄凉", "离别", "寒意"],
        "emotion_mapping": {"愁思": 0.95, "凄凉": 0.9, "离别": 0.85},
        "description": "秋天的雨，象征愁思、离别",
        "usage_examples": [
            "君问归期未有期，巴山夜雨涨秋池",
            "梧桐更兼细雨，到黄昏点点滴滴",
            "秋风秋雨愁煞人",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "落雪",
        "category": "自然",
        "subcategory": "气象",
        "emotion_core": "虚无、寂静、覆盖",
        "emotion_tags": ["虚无", "寂静", "覆盖", "寒冷"],
        "emotion_mapping": {"虚无": 0.9, "寂静": 0.85, "覆盖": 0.8},
        "description": "飘落的雪，象征虚无、寂静、掩埋一切",
        "usage_examples": [
            "千山鸟飞绝，万径人踪灭",
            "忽如一夜春风来，千树万树梨花开",
            "空营落雪月无声",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    # ===== 植物意象 =====
    {
        "name": "梅",
        "category": "植物",
        "subcategory": "花卉",
        "emotion_core": "高洁、坚韧、傲骨",
        "emotion_tags": ["高洁", "坚韧", "傲骨", "孤傲"],
        "emotion_mapping": {"高洁": 0.95, "坚韧": 0.9, "傲骨": 0.9},
        "description": "梅花，象征隐士、志士的品格",
        "usage_examples": [
            "零落成泥碾作尘，只有香如故",
            "墙角数枝梅，凌寒独自开",
            "不要人夸好颜色，只留清气满乾坤",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "柳",
        "category": "植物",
        "subcategory": "树木",
        "emotion_core": "离别、挽留、柔情",
        "emotion_tags": ["离别", "挽留", "柔情", "春光"],
        "emotion_mapping": {"离别": 0.95, "挽留": 0.85, "柔情": 0.8},
        "description": "柳树，谐音'留'，象征离别挽留",
        "usage_examples": [
            "昔我往矣，杨柳依依",
            "渭城朝雨浥轻尘，客舍青青柳色新",
            "杨柳岸，晓风残月",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "梧桐",
        "category": "植物",
        "subcategory": "树木",
        "emotion_core": "孤独、悲伤、爱情",
        "emotion_tags": ["孤独", "悲伤", "爱情", "秋意"],
        "emotion_mapping": {"孤独": 0.9, "悲伤": 0.9, "秋意": 0.85},
        "description": "梧桐树，象征孤独、悲伤、悼亡",
        "usage_examples": ["梧桐更兼细雨，到黄昏点点滴滴", "寂寞梧桐深院锁清秋"],
        "world_context": None,
        "philosophy_link": None,
    },
    # ===== 战争意象 =====
    {
        "name": "残旗",
        "category": "战争",
        "subcategory": "器物",
        "emotion_core": "虚无感、胜利后的凄凉",
        "emotion_tags": ["虚无", "战争", "代价", "凄凉"],
        "emotion_mapping": {"虚无": 0.95, "战争": 0.9, "代价": 0.85},
        "description": "战斗后残破的旗帜，象征胜利的代价",
        "usage_examples": ["独倚残旗望故里", "残旗猎猎风不语", "血染残旗战未休"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "空营",
        "category": "战争",
        "subcategory": "场所",
        "emotion_core": "虚无、人去楼空",
        "emotion_tags": ["虚无", "空旷", "战争后", "寂静"],
        "emotion_mapping": {"虚无": 0.9, "空旷": 0.85, "战争后": 0.9},
        "description": "战斗后空荡的营帐，象征胜利后的虚无",
        "usage_examples": ["空营落雪月无声", "空营唯有寒风过"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "断剑",
        "category": "战争",
        "subcategory": "器物",
        "emotion_core": "壮志未酬、悲壮",
        "emotion_tags": ["壮志未酬", "悲壮", "战争", "代价"],
        "emotion_mapping": {"壮志未酬": 0.9, "悲壮": 0.9, "代价": 0.85},
        "description": "断裂的剑，象征壮志未酬、战斗惨烈",
        "usage_examples": ["断剑残垣血未干", "提断剑，望故乡"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "剑",
        "category": "战争",
        "subcategory": "器物",
        "emotion_core": "壮志、报国、侠义",
        "emotion_tags": ["壮志", "报国", "侠义", "豪迈"],
        "emotion_mapping": {"壮志": 0.9, "报国": 0.85, "侠义": 0.9},
        "description": "宝剑，象征壮志、侠义",
        "usage_examples": ["醉里挑灯看剑，梦回吹角连营", "十年磨一剑，霜刃未曾试"],
        "world_context": None,
        "philosophy_link": None,
    },
    # ===== 人文意象 =====
    {
        "name": "孤舟",
        "category": "人文",
        "subcategory": "器物",
        "emotion_core": "漂泊、羁旅、自由",
        "emotion_tags": ["漂泊", "羁旅", "孤独", "自由"],
        "emotion_mapping": {"漂泊": 0.95, "羁旅": 0.9, "孤独": 0.85},
        "description": "孤零零的小船，象征漂泊羁旅",
        "usage_examples": ["亲朋无一字，老病有孤舟", "孤舟蓑笠翁，独钓寒江雪"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "酒",
        "category": "人文",
        "subcategory": "器物",
        "emotion_core": "消愁、壮行、相聚",
        "emotion_tags": ["消愁", "壮行", "相聚", "豪放"],
        "emotion_mapping": {"消愁": 0.9, "壮行": 0.85, "豪放": 0.85},
        "description": "酒，象征消愁、壮行、豪放",
        "usage_examples": [
            "浊酒一杯家万里，燕然未勒归无计",
            "劝君更尽一杯酒，西出阳关无故人",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "灯烛",
        "category": "人文",
        "subcategory": "器物",
        "emotion_core": "孤独、思念、温暖",
        "emotion_tags": ["孤独", "思念", "温暖", "夜晚"],
        "emotion_mapping": {"孤独": 0.85, "思念": 0.9, "温暖": 0.75},
        "description": "灯烛，象征孤独中的陪伴、思念",
        "usage_examples": [
            "何当共剪西窗烛，却话巴山夜雨时",
            "今宵酒醒何处？杨柳岸，晓风残月",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "长亭",
        "category": "人文",
        "subcategory": "场所",
        "emotion_core": "离别、送行",
        "emotion_tags": ["离别", "送行", "羁旅", "思念"],
        "emotion_mapping": {"离别": 0.95, "送行": 0.9, "羁旅": 0.85},
        "description": "古代送别的场所，象征离别",
        "usage_examples": ["长亭外，古道边", "寒蝉凄切，对长亭晚"],
        "world_context": None,
        "philosophy_link": None,
    },
    {
        "name": "高楼",
        "category": "人文",
        "subcategory": "场所",
        "emotion_core": "思念、望远、孤独",
        "emotion_tags": ["思念", "望远", "孤独", "怀人"],
        "emotion_mapping": {"思念": 0.9, "望远": 0.85, "孤独": 0.85},
        "description": "高楼，象征登高望远、怀人思念",
        "usage_examples": [
            "独上高楼，望尽天涯路",
            "昨夜西风凋碧树，独上高楼，望尽天涯路",
        ],
        "world_context": None,
        "philosophy_link": None,
    },
]

# 众生界特色意象数据
ZHONGSHENGJIE_IMAGERY = [
    {
        "name": "棋",
        "category": "众生界",
        "subcategory": "命运",
        "emotion_core": "被操控感、无力感、命运感",
        "emotion_tags": ["被操控", "无力", "命运", "棋子", "博弈"],
        "emotion_mapping": {"被操控": 0.95, "无力": 0.9, "命运": 0.85, "博弈": 0.9},
        "description": "众生皆弈，无人是棋手，皆是棋子",
        "usage_examples": [
            "执子终成枰上客",
            "千山隐迹路何寻，万象归墟棋自沉",
            "众生皆弈，无人是棋手",
        ],
        "world_context": "众生界",
        "philosophy_link": "众生皆弈，无人是棋手，执子之人终化作棋子",
    },
    {
        "name": "风碑",
        "category": "众生界",
        "subcategory": "历史",
        "emotion_core": "历史沉默、见证者、无言",
        "emotion_tags": ["沉默", "见证", "历史", "无言", "永恒"],
        "emotion_mapping": {"沉默": 0.95, "见证": 0.9, "历史": 0.9, "无言": 0.95},
        "description": "风碑无言证浮沉，象征历史的沉默见证",
        "usage_examples": ["风碑无言证浮沉", "风过石碑纹路深"],
        "world_context": "众生界",
        "philosophy_link": "风碑无言证浮沉，无人应答的追问",
    },
    {
        "name": "缝隙",
        "category": "众生界",
        "subcategory": "空间",
        "emotion_core": "夹缝生存、无处可逃",
        "emotion_tags": ["困境", "挣扎", "无路", "夹缝", "被困"],
        "emotion_mapping": {"困境": 0.95, "挣扎": 0.9, "无路": 0.9, "被困": 0.95},
        "description": "被棋局困在缝隙之间，象征夹缝生存",
        "usage_examples": ["被棋局困在缝隙之间", "缝隙里的他们，早把名字尘封"],
        "world_context": "众生界",
        "philosophy_link": "被棋局困在缝隙之间，缝隙里的他们早把名字尘封",
    },
    {
        "name": "尘封的名字",
        "category": "众生界",
        "subcategory": "身份",
        "emotion_core": "身份消逝、无名者、历史遗忘",
        "emotion_tags": ["遗忘", "无名", "消逝", "尘封", "追问"],
        "emotion_mapping": {"遗忘": 0.95, "无名": 0.9, "消逝": 0.9, "追问": 0.85},
        "description": "早把名字尘封，象征身份消逝、无名者",
        "usage_examples": ["缝隙里的他们，早把名字尘封", "名字被尘封，只留下嘱托"],
        "world_context": "众生界",
        "philosophy_link": "众生追问'我是谁'，无人应答，名字被尘封",
    },
    {
        "name": "盐霜",
        "category": "众生界",
        "subcategory": "苦难",
        "emotion_core": "苦涩、苦难痕迹、生命代价",
        "emotion_tags": ["苦涩", "苦难", "代价", "痕迹", "荒凉"],
        "emotion_mapping": {"苦涩": 0.95, "苦难": 0.9, "代价": 0.85, "荒凉": 0.9},
        "description": "荒野的盐霜，象征苦难痕迹、生命代价",
        "usage_examples": ["风穿过荒野的盐霜", "血染的战旗下，盐霜覆盖了痕迹"],
        "world_context": "众生界",
        "philosophy_link": "生命的代价，苦难的痕迹",
    },
    {
        "name": "黎明前日落",
        "category": "众生界",
        "subcategory": "时间",
        "emotion_core": "瞬间即逝、无人见证、遗憾",
        "emotion_tags": ["遗憾", "无人见证", "瞬间", "错过", "牺牲"],
        "emotion_mapping": {"遗憾": 0.9, "无人见证": 0.95, "瞬间": 0.85, "牺牲": 0.85},
        "description": "黎明前无人铭记的日落，象征无人见证的遗憾",
        "usage_examples": ["穿过黎明前无人铭记的日落", "他们死在黎明前的日落里"],
        "world_context": "众生界",
        "philosophy_link": "无人铭记的日落，无人应答的追问",
    },
    {
        "name": "未落定的棋子",
        "category": "众生界",
        "subcategory": "命运",
        "emotion_core": "不甘心、挣扎、存在证明",
        "emotion_tags": ["不甘", "挣扎", "存在", "未定", "反抗"],
        "emotion_mapping": {"不甘": 0.9, "挣扎": 0.9, "存在": 0.85, "反抗": 0.85},
        "description": "静默地宣布自己的存在，象征不甘与挣扎",
        "usage_examples": [
            "如同一枚未落定的棋子，静默地宣布自己的存在",
            "棋子未落，命运未定",
        ],
        "world_context": "众生界",
        "philosophy_link": "未落定的棋子，静默地宣布存在",
    },
]


class ImageryBuilder:
    """诗词意象库构建器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # 尝试从统一配置加载器获取 Qdrant URL
        try:
            from core.config_loader import get_qdrant_url
            self.qdrant_url = self.config.get("qdrant_url", get_qdrant_url())
        except ImportError:
            import os
            self.qdrant_url = self.config.get("qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333"))
        self.client = None
        self.model = None

    def _get_client(self):
        """获取Qdrant客户端"""
        if self.client is None:
            try:
                from qdrant_client import QdrantClient

                self.client = QdrantClient(url=self.qdrant_url)
                print(f"    ✓ 已连接Qdrant: {self.qdrant_url}")
            except Exception as e:
                print(f"    ✗ 连接Qdrant失败: {e}")
                raise
        return self.client

    def _get_model(self):
        """获取BGE-M3模型"""
        if self.model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel

                # 尝试多种方式获取模型路径
                model_path = None

                # 方式1：从config_loader
                try:
                    sys.path.insert(0, str(VECTORSTORE_CORE))
                    from config_loader import get_model_path

                    model_path = get_model_path()
                    if model_path:
                        print(f"    使用配置模型路径: {model_path}")
                except Exception as e:
                    print(f"    [调试] config_loader加载失败: {e}")

                # 方式2：检查常见路径
                if not model_path:
                    common_paths = [
                        Path.home()
                        / ".cache"
                        / "huggingface"
                        / "hub"
                        / "models--BAAI--bge-m3"
                        / "snapshots",
                        Path("E:/huggingface_cache/hub/models--BAAI--bge-m3/snapshots"),
                    ]
                    for base_path in common_paths:
                        if base_path.exists():
                            # 获取最新的snapshot
                            snapshots = list(base_path.iterdir())
                            if snapshots:
                                model_path = str(sorted(snapshots)[-1])
                                print(f"    找到本地模型: {model_path}")
                                break

                if not model_path:
                    print("    未找到本地模型，尝试在线加载...")
                    model_path = "BAAI/bge-m3"

                self.model = BGEM3FlagModel(model_path, use_fp16=True)
                print(f"    ✓ 已加载BGE-M3模型")
            except Exception as e:
                print(f"    ✗ 加载模型失败: {e}")
                raise
        return self.model

    def _get_embedding(self, text: str) -> List[float]:
        """获取文本向量"""
        model = self._get_model()
        result = model.encode([text], return_dense=True)
        return result["dense_vecs"][0].tolist()

    def init_imagery_data(self) -> List[Dict]:
        """初始化意象数据"""
        all_imagery = []

        # 合并通用意象和众生界特色意象
        all_imagery.extend(GENERAL_IMAGERY)
        all_imagery.extend(ZHONGSHENGJIE_IMAGERY)

        # 添加ID
        for i, imagery in enumerate(all_imagery):
            imagery["id"] = f"imagery_{i + 1:03d}"

        print(f"\n初始化意象数据:")
        print(f"    通用意象: {len(GENERAL_IMAGERY)}条")
        print(f"    众生界特色意象: {len(ZHONGSHENGJIE_IMAGERY)}条")
        print(f"    总计: {len(all_imagery)}条")

        return all_imagery

    def sync_to_qdrant(self, imagery_list: List[Dict]):
        """同步到Qdrant向量库"""
        print("\n同步到向量库...")

        client = self._get_client()

        # 检查/创建集合
        from qdrant_client.http import models

        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if IMAGERY_COLLECTION not in collection_names:
            print(f"    创建集合: {IMAGERY_COLLECTION}")
            client.create_collection(
                collection_name=IMAGERY_COLLECTION,
                vectors_config=models.VectorParams(
                    size=1024,  # BGE-M3向量维度
                    distance=models.Distance.COSINE,
                ),
            )
        else:
            print(f"    集合已存在: {IMAGERY_COLLECTION}")

        # 向量化并存储
        points = []
        for i, imagery in enumerate(imagery_list, 1):
            # 构建向量化文本
            text_for_embedding = f"{imagery['name']} {imagery['emotion_core']} {' '.join(imagery['emotion_tags'])} {imagery['description']}"

            vector = self._get_embedding(text_for_embedding)

            # 使用整数ID
            point = models.PointStruct(id=i, vector=vector, payload=imagery)
            points.append(point)

            if len(points) % 10 == 0:
                print(f"    已处理: {len(points)}/{len(imagery_list)}")

        # 批量上传
        client.upsert(collection_name=IMAGERY_COLLECTION, points=points)

        print(f"    ✓ 已同步 {len(points)} 条意象到向量库")

        return len(points)

    def test_search(self, query: str, world_context: str = None, top_k: int = 5):
        """测试检索功能"""
        print(f"\n测试检索: '{query}'")

        client = self._get_client()
        from qdrant_client.http import models

        # 获取查询向量
        query_vector = self._get_embedding(query)

        # 构建过滤条件
        query_filter = None
        if world_context:
            query_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="world_context",
                        match=models.MatchValue(value=world_context),
                    )
                ]
            )

        # 检索
        results = client.query_points(
            collection_name=IMAGERY_COLLECTION,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        print(f"\n检索结果 ({len(results.points)}条):")
        for i, result in enumerate(results.points, 1):
            payload = result.payload
            print(f"  {i}. {payload['name']} (score: {result.score:.3f})")
            print(f"     情感内核: {payload['emotion_core']}")
            if payload.get("world_context"):
                print(f"     [众生界特色]")

        return results


def main():
    parser = argparse.ArgumentParser(description="诗词意象库构建器")
    parser.add_argument("--init", action="store_true", help="初始化意象数据")
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--test", action="store_true", help="测试检索功能")
    parser.add_argument("--query", type=str, help="测试检索查询")
    parser.add_argument("--world", type=str, help="世界观过滤 (众生界)")

    args = parser.parse_args()

    builder = ImageryBuilder()

    if args.init:
        imagery_list = builder.init_imagery_data()
        # 保存到JSON文件
        output_file = PROJECT_ROOT / ".vectorstore" / "poetry_imagery_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(imagery_list, f, ensure_ascii=False, indent=2)
        print(f"\n    ✓ 已保存到: {output_file}")

    elif args.sync:
        # 从JSON文件读取
        input_file = PROJECT_ROOT / ".vectorstore" / "poetry_imagery_data.json"
        if not input_file.exists():
            print("    请先运行 --init 初始化数据")
            return
        with open(input_file, "r", encoding="utf-8") as f:
            imagery_list = json.load(f)
        builder.sync_to_qdrant(imagery_list)

    elif args.test or args.query:
        query = args.query or "虚无感、战争后"
        world_context = args.world if args.world != "null" else None
        builder.test_search(query, world_context)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
