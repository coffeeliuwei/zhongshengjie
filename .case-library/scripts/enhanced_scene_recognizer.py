#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能场景识别器 v2.0
=====================================

增强版场景识别：关键词 + 密度检测 + 位置感知 + LLM辅助

10种场景类型：
- 开篇场景、人物出场、战斗场景、对话场景、情感场景
- 悬念场景、转折场景、结尾场景、环境场景、心理场景
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SceneType(Enum):
    """场景类型枚举 - 共22种已启用场景"""

    # 原有场景（10种）
    OPENING = "开篇场景"
    CHARACTER = "人物出场"
    BATTLE = "战斗场景"
    DIALOGUE = "对话场景"
    EMOTION = "情感场景"
    SUSPENSE = "悬念场景"
    TWIST = "转折场景"
    ENDING = "结尾场景"
    ENVIRONMENT = "环境场景"
    PSYCHOLOGY = "心理场景"
    
    # 第一批新增（8种）
    CULTIVATION = "修炼突破"
    FACTION = "势力登场"
    RESOURCE = "资源获取"
    EXPLORATION = "探索发现"
    FORESHADOW = "伏笔回收"
    CRISIS = "危机降临"
    GROWTH = "成长蜕变"
    INTEL = "情报揭示"
    
    # 第二批新增（4种）- 基于跨题材策略可立即启用
    SOCIAL = "社交场景"
    CONSPIRACY = "阴谋揭露"
    CONFLICT = "冲突升级"
    TEAM = "团队组建"


@dataclass
class SceneSegment:
    """场景片段"""

    scene_type: str
    content: str
    start_pos: int
    end_pos: int
    chapter_index: int
    confidence: float
    features: Dict[str, float]


class EnhancedSceneRecognizer:
    """增强版场景识别器"""

    # 场景特征配置
    SCENE_FEATURES = {
        SceneType.OPENING: {
            "keywords": ["第一章", "第一节", "开篇", "序幕", "引子", "楔子", "前言", "起始"],
            "position_rule": "chapter_first",
            "position_weight": 0.9,
            "keyword_weight": 0.1,
        },
        SceneType.ENDING: {
            "keywords": ["章末", "结尾", "本章完", "下章预告", "待续", "未完待续", "全书完", "大结局", "终章"],
            "position_rule": "chapter_last",
            "position_weight": 0.7,
            "keyword_weight": 0.3,
        },
        SceneType.BATTLE: {
            "keywords": [
                "战斗", "打斗", "厮杀", "交锋", "对决", "激战", "交战", "对战",
                "过招", "比武", "决斗", "厮杀", "杀戮", "搏杀", "火拼", "对轰",
                "交手", "动手", "出手", "开战", "鏖战", "混战", "群战", "单挑"
            ],
            "action_verbs": [
                # 攻击动作
                "劈", "砍", "刺", "轰", "砸", "斩", "削", "劈砍", "刺杀", "轰击",
                "拳", "踢", "掌", "爪", "拍", "撞", "冲", "突", "扫", "挥",
                # 防御动作
                "挡", "闪", "避", "躲", "格挡", "闪避", "抵挡", "招架", "格挡",
                # 力量词
                "爆", "裂", "碎", "崩", "毁", "灭", "破", "穿", "透", "击",
                # 移动词
                "跃", "跳", "腾", "飞", "掠", "闪", "窜", "窜出", "冲出", "飞出",
            ],
            "power_words": [
                "招", "式", "功法", "法术", "神通", "技能", "绝招", "秘技",
                "剑法", "刀法", "拳法", "掌法", "指法", "腿法",
                "灵力", "真气", "斗气", "魂力", "神力", "法力",
                "威压", "气势", "杀气", "战意", "斗志",
                "阵法", "符箓", "禁制", "封印", "结界",
            ],
            "battle_patterns": [
                r"一(招|式|拳|掌|刀|剑|击)",
                r"(拳|掌|指|爪|刀|剑|枪)(风|影|气|劲|芒)",
                r"(轰|炸|爆|碎|裂|崩)(开|出|碎|裂)",
                r"(身|剑|刀|拳|掌)(影|光|气|风)",
            ],
            "density_threshold": 0.012,  # 动词密度阈值（降低以提高召回）
            "keyword_weight": 0.35,
            "density_weight": 0.40,
            "pattern_weight": 0.25,
        },
        SceneType.DIALOGUE: {
            "quote_chars": ['"', '"', "「", "」", "『", "』", "“", "”", "‹", "›"],
            "speech_verbs": [
                # 基本言语
                "说", "道", "问", "答", "回", "应", "喊", "叫", "呼", "唤",
                # 详细言语
                "说道", "问道", "答道", "回道", "喊道", "叫道", "低声", "轻声", "沉声",
                "冷冷道", "淡淡道", "平静道", "微笑道", "叹息道", "沉声道", "厉声道",
                "开口", "出声", "发声", "附和", "插嘴", "打断", "接过话",
                # 情感言语
                "怒道", "喜道", "急道", "惊道", "诧异道", "疑惑道", "激动道",
                "冷笑道", "嘲讽道", "讥讽道", "不屑道", "嗤笑道",
                # 动作伴随
                "说完", "话音刚落", "话声未落", "声音响起", "传来声音",
            ],
            "dialogue_markers": [
                r'["「『]([^"」』]+)["」』]',  # 引号内容
                r"(\w+)道[:：]",  # XX道：
                r"(\w+)(问|答|说|喊|叫)道",  # XX说道
            ],
            "quote_density_threshold": 0.08,  # 降低阈值提高召回
            "keyword_weight": 0.25,
            "density_weight": 0.50,
            "pattern_weight": 0.25,
        },
        SceneType.EMOTION: {
            "keywords": [
                # 基本情感
                "泪", "哭", "笑", "悲", "喜", "怒", "爱", "恨",
                # 详细情感
                "悲伤", "悲伤", "痛苦", "绝望", "希望", "欣慰", "感动",
                "愤怒", "愤怒", "狂怒", "暴怒", "怒火", "怒气",
                "欢喜", "欣喜", "喜悦", "快乐", "幸福", "甜蜜",
                "恐惧", "害怕", "惊恐", "惊惧", "战栗", "颤抖",
                "忧伤", "忧郁", "惆怅", "落寞", "孤独", "寂寞",
                "感动", "感激", "感恩", "动容", "触动",
            ],
            "emotion_verbs": [
                "流泪", "哭泣", "落泪", "含泪", "泪流", "泪如雨下",
                "微笑", "大笑", "狂笑", "苦笑", "冷笑", "傻笑",
                "颤抖", "发抖", "哆嗦", "战栗", "震颤",
                "心痛", "心碎", "心疼", "心寒", "心酸",
            ],
            "internal_words": ["心", "情", "感", "念", "思", "意", "魂", "神", "灵"],
            "emotion_pattern": r"[悲喜怒哀乐愁怨恨爱慕恋痴][伤痛泪笑欢欣狂怒惧恐]",
            "emotion_intensity": {
                "强": ["绝望", "崩溃", "疯狂", "暴怒", "狂喜"],
                "中": ["悲伤", "愤怒", "喜悦", "恐惧", "感动"],
                "弱": ["惆怅", "无奈", "欣慰", "担心", "惦记"],
            },
            "keyword_weight": 0.50,
            "pattern_weight": 0.30,
            "intensity_weight": 0.20,
        },
        SceneType.SUSPENSE: {
            "question_words": ["?", "？", "究竟", "为何", "难道", "莫非", "到底", "为什么", "怎么会"],
            "mystery_words": [
                "秘密", "隐藏", "未知", "谜", "疑惑", "谜团", "谜底", "真相",
                "诡异", "神秘", "玄机", "奥秘", "暗藏", "深藏", "潜伏", "隐匿",
            ],
            "hint_words": [
                "似乎", "好像", "仿佛", "隐隐", "隐约", "似有", "若有", "像是",
                "可能", "或许", "也许", "大概", "恐怕", "只怕",
            ],
            "foreshadow_words": [
                "伏笔", "铺垫", "暗示", "预示", "征兆", "前兆", "端倪", "蛛丝马迹",
            ],
            "keyword_weight": 0.60,
            "hint_weight": 0.25,
            "foreshadow_weight": 0.15,
        },
        SceneType.TWIST: {
            "keywords": [
                "突然", "忽然", "意外", "没想到", "想不到", "不料", "竟", "竟然",
                "骤然", "猛然", "陡然", "倏然", "蓦然", "猝然", "突兀",
                "出乎意料", "始料未及", "措手不及", "猝不及防",
            ],
            "change_words": [
                "转折", "变故", "突变", "反转", "逆转", "巨变", "剧变", "骤变",
                "风云突变", "峰回路转", "柳暗花明", "急转直下",
            ],
            "surprise_pattern": r"(突然|忽然|意外|骤然|猛然|陡然).*?(出现|发生|改变|袭来|降临)",
            "twist_markers": [
                r"(然而|但是|可是|不过|哪知|谁知|岂知)",
                r"(竟然|居然|想不到|没想到)",
                r"(反转|逆转|翻盘)",
            ],
            "keyword_weight": 0.40,
            "pattern_weight": 0.35,
            "marker_weight": 0.25,
        },
        SceneType.ENVIRONMENT: {
            "nature_words": [
                # 地理
                "山", "水", "河", "江", "海", "湖", "溪", "泉", "潭", "瀑",
                "峰", "岭", "崖", "谷", "沟", "洞", "窟", "穴", "岩", "石",
                "林", "树", "草", "花", "叶", "枝", "根", "藤", "苔",
                # 天象
                "风", "雨", "雪", "月", "日", "云", "雾", "霜", "露", "虹",
                "雷", "电", "星", "空", "天", "阳", "阴", "光", "暗",
                # 时节
                "春", "夏", "秋", "冬", "晨", "暮", "夜", "昼", "黄昏", "黎明",
            ],
            "scene_words": [
                "景色", "风景", "景象", "氛围", "环境", "风光", "景致", "画面",
                "气息", "气象", "气势", "气韵", "意境", "境界",
            ],
            "sense_words": [
                "看", "望", "视", "观", "瞧", "瞄", "瞥", "瞪", "凝视", "注视",
                "听", "闻", "嗅", "触", "感", "觉", "品", "尝",
            ],
            "atmosphere_words": [
                "寂静", "喧嚣", "清幽", "幽静", "萧瑟", "凄凉", "苍凉", "荒凉",
                "庄严", "肃穆", "神秘", "诡异", "祥和", "宁和", "安详",
            ],
            "density_threshold": 0.025,
            "keyword_weight": 0.40,
            "density_weight": 0.35,
            "atmosphere_weight": 0.25,
        },
        SceneType.PSYCHOLOGY: {
            "think_words": [
                "心想", "心中", "内心", "暗想", "沉思", "思索", "思忖", "思量",
                "思虑", "思考", "寻思", "琢磨", "盘算", "打算", "计划",
                "默想", "默念", "暗道", "暗自", "暗暗", "悄然",
            ],
            "feel_words": [
                "感觉", "觉得", "感到", "觉得", "感受到", "感觉到",
                "察觉", "发觉", "发现", "意识到", "领悟到",
            ],
            "emotion_state_words": [
                "忐忑", "不安", "焦虑", "紧张", "担心", "担忧", "挂念",
                "迷茫", "困惑", "疑惑", "不解", "疑惑",
                "释然", "坦然", "坦然", "平静", "安宁",
                "纠结", "矛盾", "挣扎", "煎熬", "痛苦",
            ],
            "inner_pattern": r"(心|内|胸|脑)[中里暗间底].*?(想|思|念|道|觉|感)",
            "monologue_markers": [
                r"（[^）]+）",  # 括号内心声
                r"「[^」]+」",  # 引号内心声
                r"(他|她|它)(想|念|道)[:：]?",
            ],
            "keyword_weight": 0.35,
            "pattern_weight": 0.35,
            "state_weight": 0.30,
        },
        SceneType.CHARACTER: {
            "appearance_words": [
                "出现", "登场", "首次", "第一次见到", "现身", "露面", "来到",
                "踏入", "走进", "推门", "破门", "飞落", "降落", "降临",
            ],
            "motion_words": [
                "走进", "踏入", "推门", "现身", "缓步", "快步", "疾步", "踱步",
                "走出", "离开", "退下", "退去", "消失", "隐去",
            ],
            "look_pattern": r"[男女].{0,8}(身穿|身披|身形|面容|长相|相貌|容貌|外貌|身姿|体态)",
            "feature_words": [
                # 外貌特征
                "面容", "容貌", "相貌", "长相", "五官", "眉眼", "眼神", "目光",
                "身形", "身姿", "体态", "身材", "体型", "背影",
                "气质", "气息", "气场", "气势", "风度", "风姿",
                # 服饰特征
                "身穿", "身披", "身着", "头戴", "脚穿", "腰悬", "背负",
                "白袍", "黑衣", "青衫", "红衣", "锦衣", "素衣",
            ],
            "keyword_weight": 0.30,
            "pattern_weight": 0.40,
            "feature_weight": 0.30,
        },
        
        # ==================== 新增启用场景（8种）====================
        SceneType.CULTIVATION: {
            "keywords": [
                "突破", "晋升", "进阶", "晋升", "升阶", "跨入", "踏入",
                "领悟", "顿悟", "感悟", "参悟", "参透", "悟透",
                "境界", "瓶颈", "桎梏", "屏障", "壁障", "关卡",
            ],
            "action_words": [
                "突破", "冲破", "打破", "粉碎", "撕裂",
                "凝聚", "凝练", "凝实", "凝成", "铸就",
                "蜕变", "升华", "进化", "跃迁", "飞升",
            ],
            "result_words": [
                "成功", "晋升", "踏入", "跨入", "达到", "迈入",
                "圆满", "大成", "小成", "初成", "登堂入室",
            ],
            "cultivation_patterns": [
                r"(突破|冲破|打破).*?(瓶颈|桎梏|屏障|境界)",
                r"(境界|实力|修为).*?(提升|暴涨|飞升|跃迁)",
                r"(领悟|顿悟).*?(真意|奥义|法则|大道)",
            ],
            "keyword_weight": 0.40,
            "action_weight": 0.35,
            "pattern_weight": 0.25,
        },
        SceneType.FACTION: {
            "keywords": [
                # 门派组织
                "宗门", "门派", "帮派", "教派", "宗派", "门下",
                "组织", "势力", "联盟", "联盟", "联盟", "联盟",
                "家族", "世家", "皇族", "王族", "贵族",
                # 势力相关
                "根基", "底蕴", "传承", "底蕴", "气象",
            ],
            "scale_words": [
                "庞大", "宏伟", "恢弘", "壮观", "壮观",
                "千年", "万年", "古老", "传承", "底蕴",
            ],
            "member_words": [
                "弟子", "长老", "掌门", "宗主", "家主", "盟主",
                "核心", "精英", "天才", "强者", "高手",
            ],
            "faction_patterns": [
                r"(宗门|门派|家族|势力).{0,10}(坐落|位于|建立|成立)",
                r"(弟子|长老|强者).{0,5}(数千|数万|无数)",
            ],
            "keyword_weight": 0.45,
            "scale_weight": 0.30,
            "pattern_weight": 0.25,
        },
        SceneType.RESOURCE: {
            "keywords": [
                # 资源类型
                "宝物", "宝贝", "珍宝", "宝器", "神器", "仙器",
                "功法", "秘籍", "秘法", "神功", "绝学", "传承",
                "资源", "宝药", "灵药", "丹药", "灵丹", "仙丹",
                "遗产", "遗物", "传承", "宝藏", "秘藏",
            ],
            "acquire_words": [
                "获得", "得到", "获取", "得到", "夺得", "抢到",
                "继承", "继承", "继承", "继承", "继承", "继承",
                "意外", "偶然", "无意", "误入", "闯入",
            ],
            "value_words": [
                "珍贵", "稀有", "罕见", "绝世", "无价", "稀世",
                "强大", "厉害", "恐怖", "惊人", "惊人",
            ],
            "resource_patterns": [
                r"(获得|得到|获取).{0,5}(宝物|功法|秘籍|传承)",
                r"(意外|偶然|无意).{0,5}(发现|得到|获得)",
            ],
            "keyword_weight": 0.40,
            "acquire_weight": 0.35,
            "value_weight": 0.25,
        },
        SceneType.EXPLORATION: {
            "keywords": [
                # 探索行为
                "发现", "探索", "寻找", "搜寻", "探查", "勘察",
                "深入", "闯入", "误入", "进入", "踏入",
                # 探索目标
                "遗迹", "遗址", "废墟", "古墓", "洞府", "秘境",
                "禁地", "秘地", "秘洞", "秘谷", "秘林",
            ],
            "discovery_words": [
                "惊喜", "意外", "震惊", "震惊", "震撼",
                "发现", "看到", "找到", "寻到", "探到",
            ],
            "danger_words": [
                "危险", "危机", "凶险", "险境", "险地",
                "机关", "陷阱", "阵法", "禁制", "封印",
            ],
            "exploration_patterns": [
                r"(发现|找到).{0,5}(遗迹|秘境|洞府|宝藏)",
                r"(深入|闯入|进入).{0,5}(遗迹|秘境|禁地)",
            ],
            "keyword_weight": 0.40,
            "discovery_weight": 0.30,
            "danger_weight": 0.30,
        },
        SceneType.FORESHADOW: {
            "keywords": [
                "原来", "竟是", "竟然是", "没想到", "想不到",
                "真相", "真相", "真相", "事实", "实情",
                "早已", "早就", "已经", "一直", "始终",
            ],
            "reveal_words": [
                "揭示", "揭露", "暴露", "暴露", "揭晓",
                "想起", "回忆", "记起", "想起", "想起",
                "明白", "明白", "理解", "明白", "明白",
            ],
            "connection_words": [
                "原来如此", "难怪", "怪不得", "难怪", "难怪",
                "前后呼应", "早已埋下", "伏笔", "铺垫",
            ],
            "foreshadow_patterns": [
                r"(原来|竟是|竟然).{0,10}(是|为|乃)",
                r"(真相|事实|真相).{0,5}(揭露|揭示|大白)",
                r"(难怪|怪不得|原来如此)",
            ],
            "keyword_weight": 0.40,
            "reveal_weight": 0.35,
            "pattern_weight": 0.25,
        },
        SceneType.CRISIS: {
            "keywords": [
                "危机", "大难", "灾祸", "祸事", "劫难", "浩劫",
                "灾难", "大灾", "天灾", "人祸", "浩劫",
                "威胁", "危险", "危机", "险境", "险情",
            ],
            "imminent_words": [
                "降临", "来临", "到来", "逼近", "迫近",
                "爆发", "来袭", "袭来", "席卷", "吞噬",
            ],
            "impact_words": [
                "毁灭", "毁灭", "毁灭", "毁灭", "毁灭",
                "波及", "牵连", "影响", "波及", "波及",
                "伤亡", "损失", "代价", "伤亡", "伤亡",
            ],
            "crisis_patterns": [
                r"(危机|灾难|浩劫).{0,5}(降临|来临|爆发)",
                r"(毁灭|吞噬|席卷).{0,5}(一切|万物|苍生)",
            ],
            "keyword_weight": 0.40,
            "imminent_weight": 0.35,
            "pattern_weight": 0.25,
        },
        SceneType.GROWTH: {
            "keywords": [
                "成长", "蜕变", "进化", "升华", "觉醒",
                "改变", "转变", "改变", "改变", "改变",
                "突破", "超越", "超越", "超越", "超越",
            ],
            "transformation_words": [
                "脱胎换骨", "浴火重生", "涅槃", "蜕变", "蜕变",
                "今非昔比", "判若两人", "恍如隔世",
            ],
            "realization_words": [
                "领悟", "明白", "理解", "看透", "看破",
                "放下", "释然", "释然", "释然", "释然",
            ],
            "growth_patterns": [
                r"(成长|蜕变|觉醒).{0,5}(经历|过程|代价)",
                r"(终于|终于|终于).{0,5}(明白|理解|领悟)",
            ],
            "keyword_weight": 0.35,
            "transformation_weight": 0.35,
            "realization_weight": 0.30,
        },
        SceneType.INTEL: {
            "keywords": [
                "消息", "情报", "信息", "消息", "消息",
                "得知", "获知", "知晓", "了解", "听闻",
                "传来", "送来", "带来", "传来", "传来",
            ],
            "source_words": [
                "探子", "暗探", "密探", "眼线", "线人",
                "信使", "使者", "传讯", "飞鸽", "传音",
            ],
            "reaction_words": [
                "震惊", "震惊", "震惊", "震惊", "震惊",
                "意外", "惊讶", "诧异", "意外", "意外",
                "担忧", "焦虑", "担忧", "担忧", "担忧",
            ],
            "intel_patterns": [
                r"(消息|情报).{0,5}(传来|送来|得知)",
                r"(得知|获知|听闻).{0,5}(消息|情报|消息)",
            ],
            "keyword_weight": 0.40,
            "source_weight": 0.30,
            "reaction_weight": 0.30,
        },
        
        # ==================== 第二批新增场景（4种）- 基于跨题材策略启用 ====================
        SceneType.SOCIAL: {
            "keywords": [
                # 社交活动
                "宴会", "聚会", "宴席", "酒宴", "宴请", "设宴",
                "拜访", "登门", "造访", "来访", "做客", "拜访",
                "接待", "招待", "款待", "迎客", "接风", "洗尘",
                # 社交关系
                "结交", "结识", "攀交", "攀谈", "寒暄", "客套",
            ],
            "activity_words": [
                "敬酒", "举杯", "碰杯", "畅饮", "把酒", "共饮",
                "落座", "入座", "上座", "主位", "客座", "陪座",
                "告辞", "辞别", "告别", "起身", "离席", "告退",
            ],
            "atmosphere_words": [
                "热闹", "喧嚣", "觥筹交错", "推杯换盏", "宾客满座",
                "觥筹交错", "宾主尽欢", "其乐融融", "欢声笑语",
            ],
            "social_patterns": [
                r"(宴会|聚会|宴席).{0,10}(举行|召开|开始)",
                r"(拜访|登门|造访).{0,5}(拜访|登门|造访)",
            ],
            "keyword_weight": 0.40,
            "activity_weight": 0.35,
            "atmosphere_weight": 0.25,
        },
        SceneType.CONSPIRACY: {
            "keywords": [
                # 阴谋相关
                "阴谋", "诡计", "陷阱", "圈套", "算计", "谋划",
                "密谋", "暗算", "陷害", "设计", "策划", "布局",
                "毒计", "毒计", "毒计", "毒计", "毒计",
            ],
            "reveal_words": [
                "揭露", "暴露", "败露", "败露", "败露",
                "识破", "看穿", "看破", "识破", "识破",
                "真相", "真相", "真相", "真相", "真相",
            ],
            "reaction_words": [
                "震惊", "震惊", "震惊", "震惊", "震惊",
                "愤怒", "暴怒", "狂怒", "愤怒", "愤怒",
                "后怕", "心惊", "胆寒", "后怕", "后怕",
            ],
            "conspiracy_patterns": [
                r"(阴谋|诡计|陷阱).{0,5}(揭露|败露|暴露)",
                r"(原来|竟是|竟然).{0,5}(阴谋|诡计|陷阱)",
            ],
            "keyword_weight": 0.45,
            "reveal_weight": 0.35,
            "reaction_weight": 0.20,
        },
        SceneType.CONFLICT: {
            "keywords": [
                # 冲突类型
                "矛盾", "冲突", "争执", "争端", "纠纷", "纷争",
                "对立", "对抗", "对峙", "僵持", "僵局", "僵持",
                "嫌隙", "芥蒂", "隔阂", "嫌隙", "嫌隙",
            ],
            "escalation_words": [
                "激化", "加剧", "升级", "恶化", "加深",
                "爆发", "爆发", "爆发", "爆发", "爆发",
                "不可调和", "水火不容", "势不两立", "针锋相对",
            ],
            "trigger_words": [
                "导火索", "引爆", "点燃", "点燃", "点燃",
                "因", "因为", "由于", "缘于", "源于",
            ],
            "conflict_patterns": [
                r"(矛盾|冲突|争执).{0,5}(激化|升级|爆发)",
                r"(因|因为|由于).{0,10}(矛盾|冲突|争执)",
            ],
            "keyword_weight": 0.40,
            "escalation_weight": 0.35,
            "trigger_weight": 0.25,
        },
        SceneType.TEAM: {
            "keywords": [
                # 组建行为
                "结盟", "联盟", "结伴", "组队", "组队", "组队",
                "合作", "联手", "携手", "联合", "联合", "联合",
                "招揽", "招募", "收拢", "吸纳", "吸纳", "吸纳",
            ],
            "member_words": [
                "伙伴", "同伴", "队友", "盟友", "盟友", "盟友",
                "成员", "成员", "成员", "成员", "成员",
                "骨干", "核心", "精英", "骨干", "骨干",
            ],
            "purpose_words": [
                "共同", "一起", "一同", "共同", "共同",
                "目标", "目的", "任务", "使命", "目标",
                "对抗", "对付", "对抗", "对抗", "对抗",
            ],
            "team_patterns": [
                r"(结盟|联盟|组队).{0,5}(共同|一起|一同)",
                r"(招募|招揽|吸纳).{0,5}(伙伴|成员|盟友)",
            ],
            "keyword_weight": 0.40,
            "member_weight": 0.35,
            "purpose_weight": 0.25,
        },
    }

    # AI味检测词汇
    AI_EXPRESSIONS = [
        "一股",
        "一种",
        "仿佛",
        "宛如",
        "似乎",
        "好像",
        "不言而喻",
        "可想而知",
        "显而易见",
        "令人",
        "让人",
        "使人",
        "倍感",
        "不由得",
        "忍不住",
        "情不自禁",
        "恍若",
        "犹如",
        "恰似",
        "某种",
        "某种意义上",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译正则模式"""
        self.compiled_patterns = {}
        for scene_type, features in self.SCENE_FEATURES.items():
            patterns = {}
            if "emotion_pattern" in features:
                patterns["emotion"] = re.compile(features["emotion_pattern"])
            if "surprise_pattern" in features:
                patterns["surprise"] = re.compile(features["surprise_pattern"])
            if "inner_pattern" in features:
                patterns["inner"] = re.compile(features["inner_pattern"])
            if "look_pattern" in features:
                patterns["look"] = re.compile(features["look_pattern"])
            
            # 编译战斗模式
            if "battle_patterns" in features:
                patterns["battle"] = [re.compile(p) for p in features["battle_patterns"]]
            
            # 编译对话模式
            if "dialogue_markers" in features:
                patterns["dialogue"] = []
                for p in features["dialogue_markers"]:
                    try:
                        patterns["dialogue"].append(re.compile(p))
                    except:
                        pass
            
            # 编译转折标记
            if "twist_markers" in features:
                patterns["twist"] = []
                for p in features["twist_markers"]:
                    try:
                        patterns["twist"].append(re.compile(p))
                    except:
                        pass
            
            # 编译内心独白标记
            if "monologue_markers" in features:
                patterns["monologue"] = []
                for p in features["monologue_markers"]:
                    try:
                        patterns["monologue"].append(re.compile(p))
                    except:
                        pass
            
            self.compiled_patterns[scene_type] = patterns

    def detect_opening(
        self, chapter_index: int, position_ratio: float
    ) -> Tuple[bool, float]:
        """检测开篇场景"""
        if chapter_index == 1 and position_ratio < 0.2:
            return True, 0.95
        return False, 0.0

    def detect_ending(self, position_ratio: float, content: str) -> Tuple[bool, float]:
        """检测结尾场景"""
        if position_ratio > 0.85:
            # 检查结尾关键词
            features = self.SCENE_FEATURES[SceneType.ENDING]
            keywords = features["keywords"]
            keyword_score = sum(1 for kw in keywords if kw in content) / len(keywords)
            confidence = 0.7 + keyword_score * 0.3
            return True, confidence
        return False, 0.0

    def detect_battle(self, content: str) -> Tuple[bool, float]:
        """检测战斗场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.BATTLE]

        # 关键词计数
        keyword_count = sum(content.count(kw) for kw in features["keywords"])

        # 动词密度
        action_verbs = features["action_verbs"]
        verb_count = sum(content.count(v) for v in action_verbs)
        verb_density = verb_count / len(content) if content else 0

        # 功法词
        power_count = sum(content.count(w) for w in features["power_words"])

        # 战斗模式匹配
        pattern_matches = 0
        for pattern in features.get("battle_patterns", []):
            pattern_matches += len(re.findall(pattern, content))

        # 综合评分
        score = 0.0

        # 动词密度贡献
        if verb_density > features["density_threshold"]:
            score += verb_density * 8

        # 关键词贡献
        score += min(keyword_count * 0.05, 0.3)

        # 功法词贡献
        score += min(power_count * 0.015, 0.2)

        # 模式匹配贡献
        score += min(pattern_matches * 0.08, 0.25)

        if score > 0.25:
            confidence = min(score + 0.3, 0.95)
            return True, confidence

        return False, 0.0

    def detect_dialogue(self, content: str) -> Tuple[bool, float]:
        """检测对话场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.DIALOGUE]

        # 引号密度
        quote_count = sum(content.count(c) for c in features["quote_chars"])
        quote_density = quote_count / len(content) if content else 0

        # 言语动词
        speech_count = sum(content.count(v) for v in features["speech_verbs"])

        # 对话模式匹配
        pattern_matches = 0
        for pattern in features.get("dialogue_markers", []):
            try:
                pattern_matches += len(re.findall(pattern, content))
            except:
                pass

        # 综合评分
        score = 0.0

        # 引号密度贡献
        if quote_density > features["quote_density_threshold"]:
            score += quote_density * 3

        # 言语动词贡献
        score += min(speech_count * 0.04, 0.3)

        # 模式匹配贡献
        score += min(pattern_matches * 0.05, 0.2)

        if score > 0.2:
            confidence = min(score + 0.35, 0.95)
            return True, confidence

        return False, 0.0

    def detect_emotion(self, content: str) -> Tuple[bool, float]:
        """检测情感场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.EMOTION]

        # 关键词计数
        keyword_count = sum(content.count(kw) for kw in features["keywords"])

        # 情感动词
        emotion_verb_count = sum(content.count(v) for v in features.get("emotion_verbs", []))

        # 内心词
        internal_count = sum(content.count(w) for w in features["internal_words"])

        # 情感模式
        pattern = self.compiled_patterns[SceneType.EMOTION].get("emotion")
        pattern_matches = len(pattern.findall(content)) if pattern else 0

        # 情感强度词
        intensity_score = 0
        for level, words in features.get("emotion_intensity", {}).items():
            level_count = sum(content.count(w) for w in words)
            if level == "强":
                intensity_score += level_count * 0.15
            elif level == "中":
                intensity_score += level_count * 0.08
            else:
                intensity_score += level_count * 0.03

        # 综合评分
        score = (
            keyword_count * 0.08 +
            emotion_verb_count * 0.12 +
            internal_count * 0.02 +
            pattern_matches * 0.12 +
            intensity_score
        )

        if score > 0.25:
            return True, min(score + 0.2, 0.92)

        return False, 0.0

    def detect_suspense(self, content: str) -> Tuple[bool, float]:
        """检测悬念场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.SUSPENSE]

        question_count = sum(content.count(w) for w in features["question_words"])
        mystery_count = sum(content.count(w) for w in features["mystery_words"])
        hint_count = sum(content.count(w) for w in features["hint_words"])
        foreshadow_count = sum(content.count(w) for w in features.get("foreshadow_words", []))

        score = (
            question_count * 0.06 +
            mystery_count * 0.12 +
            hint_count * 0.04 +
            foreshadow_count * 0.10
        )
        if score > 0.25:
            return True, min(score + 0.25, 0.88)

        return False, 0.0

    def detect_twist(self, content: str) -> Tuple[bool, float]:
        """检测转折场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.TWIST]

        keyword_count = sum(content.count(kw) for kw in features["keywords"])
        change_count = sum(content.count(w) for w in features["change_words"])

        pattern = self.compiled_patterns[SceneType.TWIST].get("surprise")
        pattern_matches = len(pattern.findall(content)) if pattern else 0

        # 转折标记匹配
        marker_matches = 0
        for marker in features.get("twist_markers", []):
            try:
                marker_matches += len(re.findall(marker, content))
            except:
                pass

        score = (
            keyword_count * 0.08 +
            change_count * 0.12 +
            pattern_matches * 0.15 +
            marker_matches * 0.10
        )
        if score > 0.20:
            return True, min(score + 0.3, 0.88)

        return False, 0.0

    def detect_environment(self, content: str) -> Tuple[bool, float]:
        """检测环境场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.ENVIRONMENT]

        nature_count = sum(content.count(w) for w in features["nature_words"])
        scene_count = sum(content.count(w) for w in features["scene_words"])
        sense_count = sum(content.count(w) for w in features.get("sense_words", []))
        atmosphere_count = sum(content.count(w) for w in features.get("atmosphere_words", []))

        density = nature_count / len(content) if content else 0

        # 综合评分
        score = 0.0

        # 自然词密度
        if density > features["density_threshold"]:
            score += density * 4

        # 场景词贡献
        score += min(scene_count * 0.08, 0.2)

        # 感官词贡献
        score += min(sense_count * 0.03, 0.15)

        # 氛围词贡献
        score += min(atmosphere_count * 0.10, 0.25)

        if score > 0.25:
            return True, min(score + 0.3, 0.88)

        return False, 0.0

    def detect_psychology(self, content: str) -> Tuple[bool, float]:
        """检测心理场景 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.PSYCHOLOGY]

        think_count = sum(content.count(w) for w in features["think_words"])
        feel_count = sum(content.count(w) for w in features["feel_words"])
        state_count = sum(content.count(w) for w in features.get("emotion_state_words", []))

        pattern = self.compiled_patterns[SceneType.PSYCHOLOGY].get("inner")
        pattern_matches = len(pattern.findall(content)) if pattern else 0

        # 内心独白标记
        monologue_count = 0
        for marker in features.get("monologue_markers", []):
            try:
                monologue_count += len(re.findall(marker, content))
            except:
                pass

        score = (
            think_count * 0.08 +
            feel_count * 0.06 +
            state_count * 0.10 +
            pattern_matches * 0.12 +
            monologue_count * 0.08
        )
        if score > 0.20:
            return True, min(score + 0.3, 0.88)

        return False, 0.0

    def detect_character_appearance(self, content: str) -> Tuple[bool, float]:
        """检测人物出场 - 增强版"""
        features = self.SCENE_FEATURES[SceneType.CHARACTER]

        appearance_count = sum(content.count(w) for w in features["appearance_words"])
        motion_count = sum(content.count(w) for w in features["motion_words"])
        feature_count = sum(content.count(w) for w in features.get("feature_words", []))

        pattern = self.compiled_patterns[SceneType.CHARACTER].get("look")
        pattern_matches = len(pattern.findall(content)) if pattern else 0

        score = (
            appearance_count * 0.12 +
            motion_count * 0.08 +
            feature_count * 0.10 +
            pattern_matches * 0.15
        )
        if score > 0.18:
            return True, min(score + 0.3, 0.88)

        return False, 0.0

    def detect_ai_taste(self, content: str) -> Tuple[bool, int, List[str]]:
        """检测AI味表达"""
        found = []
        for expr in self.AI_EXPRESSIONS:
            count = content.count(expr)
            if count > 0:
                found.append((expr, count))

        total_count = sum(c for _, c in found)
        has_ai_taste = total_count > 5

        return has_ai_taste, total_count, found

    def analyze_segment(
        self, content: str, chapter_index: int = 1, position_ratio: float = 0.0
    ) -> List[SceneSegment]:
        """
        分析文本片段，识别所有可能的场景类型

        Args:
            content: 文本内容
            chapter_index: 章节索引
            position_ratio: 在章节中的位置比例（0-1）

        Returns:
            检测到的场景片段列表
        """
        detected_scenes = []

        # 开篇检测
        is_opening, conf = self.detect_opening(chapter_index, position_ratio)
        if is_opening:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.OPENING.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"position_rule": True},
                )
            )

        # 结尾检测
        is_ending, conf = self.detect_ending(position_ratio, content)
        if is_ending:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.ENDING.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"position_ratio": position_ratio},
                )
            )

        # 战斗检测
        is_battle, conf = self.detect_battle(content)
        if is_battle:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.BATTLE.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"battle_score": conf},
                )
            )

        # 对话检测
        is_dialogue, conf = self.detect_dialogue(content)
        if is_dialogue:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.DIALOGUE.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"quote_density": conf},
                )
            )

        # 情感检测
        is_emotion, conf = self.detect_emotion(content)
        if is_emotion:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.EMOTION.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"emotion_score": conf},
                )
            )

        # 悬念检测
        is_suspense, conf = self.detect_suspense(content)
        if is_suspense:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.SUSPENSE.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"suspense_score": conf},
                )
            )

        # 转折检测
        is_twist, conf = self.detect_twist(content)
        if is_twist:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.TWIST.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"twist_score": conf},
                )
            )

        # 环境检测
        is_env, conf = self.detect_environment(content)
        if is_env:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.ENVIRONMENT.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"env_density": conf},
                )
            )

        # 心理检测
        is_psy, conf = self.detect_psychology(content)
        if is_psy:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.PSYCHOLOGY.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"psychology_score": conf},
                )
            )

        # 人物出场检测
        is_char, conf = self.detect_character_appearance(content)
        if is_char:
            detected_scenes.append(
                SceneSegment(
                    scene_type=SceneType.CHARACTER.value,
                    content=content,
                    start_pos=0,
                    end_pos=len(content),
                    chapter_index=chapter_index,
                    confidence=conf,
                    features={"character_score": conf},
                )
            )

        # 按置信度排序
        detected_scenes.sort(key=lambda x: x.confidence, reverse=True)

        return detected_scenes

    def get_primary_scene_type(
        self, content: str, chapter_index: int = 1
    ) -> Tuple[str, float]:
        """
        获取主要场景类型

        Returns:
            (场景类型, 置信度)
        """
        scenes = self.analyze_segment(content, chapter_index)
        if scenes:
            return scenes[0].scene_type, scenes[0].confidence
        return "未知", 0.0


def main():
    """测试"""
    import argparse

    parser = argparse.ArgumentParser(description="智能场景识别器")
    parser.add_argument("--content", "-c", type=str, help="测试内容")
    parser.add_argument("--file", "-f", type=str, help="测试文件")

    args = parser.parse_args()

    recognizer = EnhancedSceneRecognizer()

    content = args.content
    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except:
            with open(args.file, "r", encoding="gbk") as f:
                content = f.read()

    if content:
        scenes = recognizer.analyze_segment(content)

        print(f"检测到 {len(scenes)} 种场景类型:\n")
        for scene in scenes:
            print(f"  {scene.scene_type}: {scene.confidence:.0%}")

        primary, conf = recognizer.get_primary_scene_type(content)
        print(f"\n主要场景: {primary} ({conf:.0%})")

        # AI味检测
        has_ai, count, words = recognizer.detect_ai_taste(content)
        print(f"\nAI味检测: {'有' if has_ai else '无'} ({count} 次)")
        if words:
            for word, cnt in words[:5]:
                print(f"  {word}: {cnt}")


if __name__ == "__main__":
    main()
