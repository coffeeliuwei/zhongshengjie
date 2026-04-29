#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
意图分类器
==========

识别用户对话中的意图类型，支持25+种意图类型的自动分类。

核心功能：
- 识别核心意图（设定更新、工作流控制、数据提炼）
- 识别扩展意图（伏笔、资源、信息、承诺等追踪系统）
- 提取实体信息
- 计算置信度

参考：统一提炼引擎重构方案.md 第9.11节
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class IntentCategory(Enum):
    """意图分类"""

    WORKFLOW = "workflow"  # 工作流控制
    DATA_EXTRACTION = "extraction"  # 数据提炼
    WORKFLOW_CONTROL = "workflow_control"  # 工作流控制（新增）
    SETTING_UPDATE = "setting_update"  # 设定更新（新增）
    CHARACTER = "character"  # 角色设定
    FACTION = "faction"  # 势力设定
    POWER = "power"  # 力量体系
    TIMELINE = "timeline"  # 时间线
    TRACKING = "tracking"  # 追踪系统
    PLOT = "plot"  # 剧情
    QUERY = "query"  # 查询
    TECHNIQUE = "technique"  # 技法提炼（新增）
    EVALUATION = "evaluation"  # 审核维度（新增）
    CONFIRMATION = "confirmation"  # 认操作（新增）
    FEEDBACK = "feedback"  # 灵感引擎反馈（新增）
    MANAGEMENT = "management"  # 灵感引擎管理（新增）
    UNKNOWN = "unknown"  # 未知


@dataclass
class IntentResult:
    """意图识别结果"""

    intent: str  # 意图类型
    category: IntentCategory  # 意图分类
    confidence: float  # 置信度 (0.0-1.0)
    entities: Dict[str, str]  # 提取的实体
    is_ambiguous: bool = False  # 是否模糊
    matched_pattern: Optional[str] = None  # 匹配的模式
    alternatives: Optional[List[Dict[str, Any]]] = None  # 替代结果


class IntentClassifier:
    """意图分类器（M4 后 patterns 从 config/intent_patterns.json 加载）"""

    # [M4] 类 B 字符串外化：patterns 从 JSON 读取，类属性 CORE_INTENTS/EXTENDED_INTENTS 已废弃
    _PATTERNS_JSON_PATH = (
        Path(__file__).resolve().parents[2] / "config" / "intent_patterns.json"
    )

    @classmethod
    def _load_patterns_from_json(cls) -> Tuple[Dict, Dict]:
        """从 config/intent_patterns.json 加载 core+extended，把 category 字符串映回 IntentCategory enum"""
        if not cls._PATTERNS_JSON_PATH.exists():
            raise FileNotFoundError(
                f"intent_patterns.json 不存在: {cls._PATTERNS_JSON_PATH}\n"
                "请先运行 python tools/extract_intent_patterns_to_json.py"
            )
        with open(cls._PATTERNS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        def _restore(intents: dict) -> dict:
            out = {}
            for name, cfg in intents.items():
                cat_name = cfg["category"]
                try:
                    cat_enum = IntentCategory[cat_name]
                except KeyError:
                    raise ValueError(
                        f"intent_patterns.json 中 {name} 的 category={cat_name!r} "
                        f"不在 IntentCategory 枚举中"
                    )
                out[name] = {
                    "patterns": list(cfg["patterns"]),
                    "category": cat_enum,
                    "entities": list(cfg.get("entities", [])),
                }
            return out

        return _restore(data["core_intents"]), _restore(data["extended_intents"])

    # 核心意图（高优先级）
    CORE_INTENTS = {
        # 工作流控制
        "start_chapter": {
            "patterns": [
                r"写第(.+?)章",
                r"开始创作第(.+?)章",
                r"帮我写第(.+?)章",
                r"创作第(.+?)章",
            ],
            "category": IntentCategory.WORKFLOW_CONTROL,
            "entities": ["chapter"],
        },
        "continue_workflow": {
            "patterns": [
                r"继续",
                r"继续写",
                r"接着刚才",
                r"往下写",
            ],
            "category": IntentCategory.WORKFLOW,
            "entities": [],
        },
        "pause_workflow": {
            "patterns": [
                r"暂停",
                r"等一下",
                r"先停",
                r"休息一下",
            ],
            "category": IntentCategory.WORKFLOW_CONTROL,
            "entities": [],
        },
        "undo_last": {
            "patterns": [
                r"撤销",
                r"不对",
                r"我说错了",
                r"重写",
                r"重来",
            ],
            "category": IntentCategory.WORKFLOW,
            "entities": [],
        },
        # 数据提炼
        "full_extraction": {
            "patterns": [
                r"提炼数据",
                r"初始化数据",
                r"全面提炼",
                r"更新案例库",
                r"重新提炼",
                r"全量提炼",
            ],
            "category": IntentCategory.DATA_EXTRACTION,
            "entities": [],
        },
        "incremental_extraction": {
            "patterns": [
                r"增量提炼",
                r"同步新小说",
                r"更新数据",
                r"同步小说库",
                r"增量同步",
            ],
            "category": IntentCategory.DATA_EXTRACTION,
            "entities": [],
        },
        # 角色设定
        "add_character": {
            "patterns": [
                r"加个新角色叫(.+)",
                r"新增角色(.+)",
                r"有个新角色(.+)",
                r"加一个角色(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["character_name"],
        },
        "add_character_ability": {
            "patterns": [
                r"(.+?)有个新能力叫(.+)",
                r"(.+?)的血脉能力是(.+)",
                r"(.+?)获得了(.+)能力",
                r"(.+?)学会了(.+)",
                r"(.+?)觉醒了(.+)能力",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["character", "ability"],
        },
        "add_character_relation": {
            "patterns": [
                r"(.+?)和(.+?)是(.+)",
                r"(.+?)和(.+?)的关系是(.+)",
                r"(.+?)是(.+?)的(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["character1", "character2", "relation"],
        },
        "modify_character": {
            "patterns": [
                r"(.+?)的性格改成(.+)",
                r"(.+?)的设定改成(.+)",
                r"修改(.+?)的(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["character", "attribute", "value"],
        },
        # 势力设定
        "add_faction": {
            "patterns": [
                r"加个新势力叫(.+)",
                r"有个新势力叫(.+)",
                r"新增势力(.+)",
                r"加一个势力(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["faction_name"],
        },
        "add_faction_member": {
            "patterns": [
                r"(.+?)加入(.+)",
                r"(.+?)归属于(.+)",
                r"(.+?)属于(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["character", "faction"],
        },
        # 剧情修改
        "modify_plot": {
            "patterns": [
                r"剧情改成(.+)",
                r"(.+?)改成(.+)",
                r"修改剧情(.+)",
                r"剧情变成(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["plot_change"],
        },
        "add_plot_point": {
            "patterns": [
                r"加个剧情(.+)",
                r"新增剧情(.+)",
                r"加一个情节(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["plot_point"],
        },
    }

    # 扩展意图（追踪系统）
    EXTENDED_INTENTS = {
        # 伏笔追踪
        "add_hook": {
            "patterns": [
                r"这里埋个伏笔[：:]?(.+)",
                r"埋下伏笔[：:]?(.+)",
                r"伏笔(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["hook_content"],
        },
        "advance_hook": {
            "patterns": [
                r"这个伏笔推进一下",
                r"推进伏笔(.+)",
                r"伏笔(.+?)推进",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["hook_name"],
        },
        "resolve_hook": {
            "patterns": [
                r"这个伏笔回收了",
                r"回收伏笔(.+)",
                r"伏笔(.+?)回收",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["hook_name"],
        },
        # 资源追踪
        "add_resource": {
            "patterns": [
                r"(.+?)获得了(.+)",
                r"(.+?)得到(.+)",
                r"(.+?)拥有了(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character", "resource"],
        },
        "consume_resource": {
            "patterns": [
                r"(.+?)用了(.+)",
                r"(.+?)消耗了(.+)",
                r"(.+?)花费了(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character", "resource"],
        },
        "add_injury": {
            "patterns": [
                r"(.+?)受了(.+)",
                r"(.+?)受伤(.+)",
                r"(.+?)的伤(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character", "injury"],
        },
        # 信息边界
        "add_character_info": {
            "patterns": [
                r"(.+?)知道了(.+)",
                r"(.+?)发现(.+)",
                r"(.+?)得知(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character", "info"],
        },
        "share_info": {
            "patterns": [
                r"(.+?)告诉(.+?)(.+)",
                r"(.+?)向(.+?)透露(.+)",
                r"(.+?)通知(.+?)(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character1", "character2", "info"],
        },
        # 承诺追踪
        "add_payoff": {
            "patterns": [
                r"(.+?)发誓要(.+)",
                r"(.+?)承诺(.+)",
                r"(.+?)决心(.+)",
                r"(.+?)发誓(.+)",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["character", "promise"],
        },
        "deliver_payoff": {
            "patterns": [
                r"这个承诺兑现了",
                r"兑现承诺(.+)",
                r"承诺(.+?)完成",
            ],
            "category": IntentCategory.TRACKING,
            "entities": ["promise_name"],
        },
        # 力量体系
        "add_power_type": {
            "patterns": [
                r"加个新力量体系叫(.+)",
                r"新增力量体系(.+)",
                r"加一个力量类型(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["power_type"],
        },
        "add_power_level": {
            "patterns": [
                r"力量体系加个新境界(.+)",
                r"(.+?)的力量境界是(.+)",
                r"加一个境界(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["power_system", "level"],
        },
        "add_power_cost": {
            "patterns": [
                r"(.+?)的代价是(.+)",
                r"使用(.+?)代价(.+)",
                r"(.+?)代价(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["power", "cost"],
        },
        # 时间线
        "add_era": {
            "patterns": [
                r"加个新时代叫(.+)",
                r"新增时代(.+)",
                r"加一个时代(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["era_name"],
        },
        "add_era_event": {
            "patterns": [
                r"(.+?)时代加个事件(.+)",
                r"(.+?)时代发生(.+)",
                r"(.+?)时代事件(.+)",
            ],
            "category": IntentCategory.SETTING_UPDATE,
            "entities": ["era", "event"],
        },
        # 查询
        "query_character": {
            "patterns": [
                r"(.+?)是什么设定",
                r"查一下(.+?)(的)?(设定|背景|能力|信息|情况|状态|资料)",
                r"(.+?)的设定",
                r"查询角色(.+)",
            ],
            "category": IntentCategory.QUERY,
            "entities": ["character_name"],
        },
        "query_progress": {
            "patterns": [
                r"进度",
                r"写到哪了",
                r"现在在干什么",
                r"当前状态",
            ],
            "category": IntentCategory.QUERY,
            "entities": [],
        },
        # 技法提炼（新增 - collection-enhancement-design.md 5.1节）
        "extract_technique": {
            "patterns": [
                r"从(.+)提炼技法",
                r"这段(.+)用了什么技法",
                r"分析(.+)的写法",
                r"学习(.+)的技巧",
                r"(.+)有什么技法可以学习",
                r"看看(.+)用的是什么手法",
                r"提炼一下(.+)的技法",
                r"这段(.+)很好，提炼技法",
            ],
            "category": IntentCategory.TECHNIQUE,
            "entities": ["content_reference"],
        },
        "extract_technique_from_file": {
            "patterns": [
                r"从文件(.+)提炼技法",
                r"分析文档(.+)的技法",
                r"提炼(.+)\\.md里的技法",
                r"看看(.+)文档有什么技法",
                r"分析(.+)\\.txt中的技法",
                r"帮我分析(.+)文档",
                r"提炼这个文档(.+)的技法",
            ],
            "category": IntentCategory.TECHNIQUE,
            "entities": ["file_path"],
        },
        "confirm_technique": {
            "patterns": [
                r"确认入库",
                r"这个技法可以",
                r"好的入库",
                r"入库吧",
                r"没问题入库",
            ],
            "category": IntentCategory.CONFIRMATION,
            "entities": [],
        },
        "modify_technique": {
            "patterns": [
                r"技法名称改成(.+)",
                r"改成(.+)技法",
                r"名称用(.+)",
            ],
            "category": IntentCategory.TECHNIQUE,
            "entities": ["new_name"],
        },
        # 审核维度（新增 - evaluation-criteria-extension-design.md）
        "add_evaluation_criteria": {
            "patterns": [
                r"添加禁止项(.+)",
                r"新禁止项(.+)",
                r"加入禁止项(.+)",
                r"添加评估标准(.+)",
                r"新评估标准(.+)",
                r"(.+)感觉很假，加入禁止项",
                r"(.+)这个表达很假",
                r"这个表达很假(.+)",
                r"(.+)感觉很假",
                r"(.+)是假的",
                r"这个表达很假",
                r"这个感觉很假",
            ],
            "category": IntentCategory.EVALUATION,
            "entities": ["criteria_content"],
        },
        "discover_prohibitions_from_file": {
            "patterns": [
                r"从文档(.+)发现禁止项",
                r"扫描文件(.+)找禁止项",
                r"分析(.+)文档的禁止项",
                r"发现(.+)\\.md里的假表达",
                r"扫描(.+)文档找假表达",
                r"帮我从(.+)文档发现常见问题表达",
            ],
            "category": IntentCategory.EVALUATION,
            "entities": ["file_path"],
        },
        "modify_evaluation_threshold": {
            "patterns": [
                r"修改阈值(.+)",
                r"调整阈值(.+)",
                r"把(.+)阈值改成(.+)",
                r"(.+)的阈值改为(.+)",
            ],
            "category": IntentCategory.EVALUATION,
            "entities": ["threshold_name", "new_value"],
        },
        "confirm_evaluation_criteria": {
            "patterns": [
                r"确认添加",
                r"添加这个禁止项",
                r"好的添加",
            ],
            "category": IntentCategory.CONFIRMATION,
            "entities": [],
        },
        # ===== 灵感引擎新增意图（11个）=====
        # 反馈类（FEEDBACK）
        "reader_moment_feedback": {
            "patterns": [
                r"(第.+章|刚才|那段|这段).*(很|太|有点).*(解气|好|漂亮|棒|震撼|感动|燃|舒服|对味)",
                r"(第.+章|刚才|那段|这段).*(很|太|有点).*(出戏|乏味|假|别扭)",
            ],
            "category": IntentCategory.FEEDBACK,
            "entities": ["chapter_ref", "resonance_type"],
        },
        "comparative_moment_feedback": {
            "patterns": [
                r"(.+)比(.+)(好|差|强|弱).+因为",
                r"原来.+换成.+就",
            ],
            "category": IntentCategory.FEEDBACK,
            "entities": ["segment_a", "segment_b", "reason"],
        },
        "external_moment_inject": {
            "patterns": [
                r"把.+这段.+记(下|一下)",
                r"粘给你.+记",
            ],
            "category": IntentCategory.FEEDBACK,
            "entities": ["segment_text"],
        },
        "overturn_feedback": {
            "patterns": [
                r"(这|那)版.*不(接受|满意)",
                r"鉴赏师.*选错",
                r"评估师.*漏了",
                r"虽然(过了|定稿).*但",
            ],
            "category": IntentCategory.FEEDBACK,
            "entities": [],
        },
        "connoisseur_audit_response": {
            "patterns": [
                r"第.+次.*(真|是)点火",
                r"都是敷衍",
                r"审计.*[1-9]",
            ],
            "category": IntentCategory.FEEDBACK,
            "entities": ["audit_result"],
        },
        # 查询类（QUERY）
        "inspiration_status_query": {
            "patterns": [
                r"你(现在|最近).*(学到|记住|倾向)",
                r"灵感引擎.*状态",
            ],
            "category": IntentCategory.QUERY,
            "entities": [],
        },
        "constraint_query": {
            "patterns": [
                r"查(一下)?.*约束",
                r"现在有(多少|哪些)约束",
            ],
            "category": IntentCategory.QUERY,
            "entities": [],
        },
        # 管理类（MANAGEMENT）
        "constraint_tuning": {
            "patterns": [
                r"(那条|这个).*约束.*(别扭|太怪|没用|有效)",
                r"(禁用|调整).*约束",
            ],
            "category": IntentCategory.MANAGEMENT,
            "entities": ["constraint_id"],
        },
        "constraint_add": {
            "patterns": [
                r"加(一条|个)约束",
                r"我想加约束",
            ],
            "category": IntentCategory.MANAGEMENT,
            "entities": [],
        },
        # 工作流类（WORKFLOW）
        "inspiration_conflict_resolution": {
            "patterns": [
                r"用变体.[ABC12345]",
                r"放宽.*一次",
                r"调整.*后重写",
            ],
            "category": IntentCategory.WORKFLOW,
            "entities": ["variant_choice"],
        },
        "inspiration_bailout": {
            "patterns": [
                r"关(掉|闭).*灵感(引擎)?",
                r"这章.*不(要)?折腾",
                r"走原(流程)?",
            ],
            "category": IntentCategory.WORKFLOW,
            "entities": [],
        },
    }

    def __init__(self):
        """初始化意图分类器（[M4] 从 config/intent_patterns.json 加载 patterns）"""
        try:
            core, extended = self._load_patterns_from_json()
        except (FileNotFoundError, ValueError, KeyError) as e:
            print(f"[WARN] intent_patterns.json 加载失败，降级使用内置 patterns: {e}")
            core = self.CORE_INTENTS
            extended = self.EXTENDED_INTENTS
        self._all_intents = {**core, **extended}
        # 类属性 CORE_INTENTS/EXTENDED_INTENTS 暂保留供向后兼容（如有外部代码读取）
        # 预编译正则表达式
        self._compiled_patterns: Dict[str, List[Tuple[re.Pattern, List[str]]]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译所有正则表达式"""
        import warnings
        failed = []
        for intent_name, intent_config in self._all_intents.items():
            patterns = []
            for pattern_str in intent_config["patterns"]:
                try:
                    compiled = re.compile(pattern_str, re.IGNORECASE)
                    patterns.append((compiled, intent_config["entities"]))
                except re.error as e:
                    failed.append(f"{intent_name}: {pattern_str!r} → {e}")
            self._compiled_patterns[intent_name] = patterns
        if failed:
            warnings.warn(
                f"intent_classifier: {len(failed)} 个正则编译失败，对应意图将无法匹配:\n"
                + "\n".join(f"  {f}" for f in failed),
                stacklevel=2,
            )

    def classify(self, user_input: str) -> IntentResult:
        """
        分类用户输入的意图

        Args:
            user_input: 用户输入的文本

        Returns:
            IntentResult: 意图识别结果
        """
        # 先匹配核心意图（优先级高）
        result = self._match_patterns(user_input, self.CORE_INTENTS, True)

        # 如果核心意图没有匹配，尝试扩展意图
        if result is None:
            result = self._match_patterns(user_input, self.EXTENDED_INTENTS, False)

        # 如果都没有匹配，返回未知意图
        if result is None:
            return IntentResult(
                intent="unknown",
                category=IntentCategory.UNKNOWN,
                confidence=0.0,
                entities={},
                is_ambiguous=False,
            )

        return result

    def _match_patterns(
        self, text: str, intent_configs: Dict, is_core: bool
    ) -> Optional[IntentResult]:
        """
        匹配意图模式

        Args:
            text: 输入文本
            intent_configs: 意图配置字典
            is_core: 是否核心意图

        Returns:
            IntentResult or None
        """
        matches = []

        for intent_name, intent_config in intent_configs.items():
            for compiled_pattern, entity_names in self._compiled_patterns[intent_name]:
                match = compiled_pattern.search(text)
                if match:
                    entities = self._extract_entities(match, entity_names)
                    confidence = self._calculate_confidence(match, text, is_core)
                    matches.append(
                        {
                            "intent": intent_name,
                            "category": intent_config["category"],
                            "confidence": confidence,
                            "entities": entities,
                            "matched_pattern": compiled_pattern.pattern,
                            "match_span": match.span(),
                        }
                    )

        if not matches:
            return None

        # 按置信度排序
        matches.sort(key=lambda x: x["confidence"], reverse=True)

        # 检查是否有多个高置信度匹配（模糊情况）
        best_match = matches[0]
        is_ambiguous = (
            len(matches) > 1
            and matches[1]["confidence"] > 0.7
            and (matches[0]["confidence"] - matches[1]["confidence"]) < 0.1
        )

        return IntentResult(
            intent=best_match["intent"],
            category=best_match["category"],
            confidence=best_match["confidence"],
            entities=best_match["entities"],
            is_ambiguous=is_ambiguous,
            matched_pattern=best_match["matched_pattern"],
            alternatives=matches[1:] if is_ambiguous else None,
        )

    def _extract_entities(
        self, match: re.Match, entity_names: List[str]
    ) -> Dict[str, str]:
        """
        从正则匹配中提取实体

        Args:
            match: 正则匹配对象
            entity_names: 实体名称列表

        Returns:
            实体字典
        """
        entities = {}
        groups = match.groups()

        for i, entity_name in enumerate(entity_names):
            if i < len(groups) and groups[i]:
                entities[entity_name] = groups[i].strip()

        return entities

    def _calculate_confidence(self, match: re.Match, text: str, is_core: bool) -> float:
        """计算意图置信度

        基于关键词是否为核心意图，不依赖输入长度，保证稳定性。
        """
        base_confidence = 0.9 if is_core else 0.8

        # 匹配到的关键词在 text 中的位置越靠前（开头），置信度微增
        match_start = match.start()
        text_length = max(len(text), 1)
        position_bonus = 0.05 * (1 - match_start / text_length)

        return min(1.0, base_confidence + position_bonus)

    def get_intent_info(self, intent_name: str) -> Optional[Dict]:
        """获取意图详细信息"""
        return self._all_intents.get(intent_name)

    def get_all_intents(self) -> Dict[str, List[str]]:
        """获取所有支持的意图类型"""
        return {name: config["patterns"] for name, config in self._all_intents.items()}

    def get_intents_by_category(self, category: IntentCategory) -> List[str]:
        """按分类获取意图类型"""
        return [
            name
            for name, config in self._all_intents.items()
            if config["category"] == category
        ]


# 测试代码
if __name__ == "__main__":
    classifier = IntentClassifier()

    test_inputs = [
        "写第一章",
        "血牙有个新能力叫血脉守护",
        "加个新势力叫暗影宗",
        "这里埋个伏笔：血牙的身世之谜",
        "提炼数据",
        "继续",
        "血牙获得了三颗灵石",
        "血牙发誓要杀了魔王",
        "查一下血牙的设定",
    ]

    print("=" * 60)
    print("意图分类器测试")
    print("=" * 60)

    for input_text in test_inputs:
        result = classifier.classify(input_text)
        print(f"\n输入: {input_text}")
        print(f"意图: {result.intent}")
        print(f"分类: {result.category.value}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"实体: {result.entities}")
        print(f"模糊: {result.is_ambiguous}")
