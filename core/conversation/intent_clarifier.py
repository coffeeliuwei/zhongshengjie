#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
意图澄清器
==========

处理模糊表达，生成澄清问题。

核心功能：
- 判断是否需要澄清
- 生成澄清问题
- 处理用户澄清回复
- 记录澄清历史

参考：统一提炼引擎重构方案.md 第10.3.2节
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from .intent_classifier import IntentResult


class ClarificationType(Enum):
    """澄清类型"""

    LOW_CONFIDENCE = "low_confidence"  # 置信度过低
    AMBIGUOUS = "ambiguous"  # 多个意图匹配
    TRIGGER_PATTERN = "trigger_pattern"  # 触发特定模式
    MISSING_ENTITY = "missing_entity"  # 缺少关键实体


@dataclass
class ClarificationQuestion:
    """澄清问题"""

    clarification_type: ClarificationType
    question_text: str
    options: List[str]
    context: str
    original_intent: str


class IntentClarifier:
    """意图澄清器"""

    # 澄清模板
    CLARIFICATION_TEMPLATES = {
        # 能力提升相关
        "add_character_ability": {
            "triggers": ["更强了", "变强了", "提升了", "升级了", "突破了"],
            "questions": [
                "您是指：",
                "1. 境界提升了？",
                "2. 获得了新能力？",
                "3. 血脉觉醒了？",
                "4. 其他提升？",
                "请选择或补充说明。",
            ],
        },
        # 修改相关
        "modify_character": {
            "triggers": ["不对", "错了", "改一下", "修改", "调整"],
            "questions": [
                "请问具体哪里需要修改？",
                "1. 角色设定？",
                "2. 能力描述？",
                "3. 关系设定？",
                "4. 其他？",
                "请选择或补充说明。",
            ],
        },
        # 章节相关
        "ambiguous_chapter": {
            "triggers": ["写一章", "来一章", "创作一章"],
            "questions": [
                "请问是第几章？",
                "1. 继续下一章",
                "2. 指定其他章节",
                "请回复章节号。",
            ],
        },
        # 力量体系相关
        "power_system": {
            "triggers": ["力量", "能力", "境界", "血脉"],
            "questions": [
                "请问具体是？",
                "1. 增加新的力量体系？",
                "2. 增加新的境界等级？",
                "3. 角色境界提升？",
                "4. 其他？",
            ],
        },
        # 势力相关
        "faction": {
            "triggers": ["势力", "门派", "宗门", "组织"],
            "questions": [
                "请问具体是？",
                "1. 添加新势力？",
                "2. 角色加入势力？",
                "3. 势力间关系？",
                "4. 其他？",
            ],
        },
        # 伏笔相关
        "hook": {
            "triggers": ["伏笔", "暗示", "铺垫"],
            "questions": [
                "请问具体是？",
                "1. 布下伏笔？",
                "2. 推进伏笔？",
                "3. 回收伏笔？",
                "4. 查询伏笔状态？",
            ],
        },
        # 资源相关
        "resource": {
            "triggers": ["物品", "道具", "资源", "宝物"],
            "questions": [
                "请问具体是？",
                "1. 角色获得物品？",
                "2. 角色消耗物品？",
                "3. 查询物品持有情况？",
                "4. 其他？",
            ],
        },
    }

    # 置信度阈值
    CONFIDENCE_THRESHOLD = 0.7

    # 关键实体列表（缺少这些实体需要澄清）
    KEY_ENTITIES = {
        "start_chapter": ["chapter"],
        "add_character": ["character_name"],
        "add_character_ability": ["character", "ability"],
        "add_faction": ["faction_name"],
        "modify_character": ["character"],
        "query_character": ["character_name"],
    }

    def __init__(self):
        """初始化意图澄清器"""
        self._clarification_history: List[ClarificationQuestion] = []

    def needs_clarification(self, intent_result: IntentResult) -> bool:
        """
        判断是否需要澄清

        Args:
            intent_result: 意图识别结果

        Returns:
            是否需要澄清
        """
        # 1. 置信度过低
        if intent_result.confidence < self.CONFIDENCE_THRESHOLD:
            return True

        # 2. 意图模糊（有多个高置信度匹配）
        if intent_result.is_ambiguous:
            return True

        # 3. 缺少关键实体
        intent = intent_result.intent
        required_entities = self.KEY_ENTITIES.get(intent, [])

        for entity in required_entities:
            if (
                entity not in intent_result.entities
                or not intent_result.entities[entity]
            ):
                return True

        return False

    def generate_clarification(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion:
        """
        生成澄清问题

        Args:
            intent_result: 意图识别结果
            user_input: 用户原始输入

        Returns:
            ClarificationQuestion
        """
        clarification_type = self._determine_clarification_type(intent_result)

        # 根据澄清类型生成问题
        if clarification_type == ClarificationType.LOW_CONFIDENCE:
            return self._generate_low_confidence_question(intent_result, user_input)

        elif clarification_type == ClarificationType.AMBIGUOUS:
            return self._generate_ambiguous_question(intent_result)

        elif clarification_type == ClarificationType.TRIGGER_PATTERN:
            return self._generate_trigger_question(intent_result, user_input)

        elif clarification_type == ClarificationType.MISSING_ENTITY:
            return self._generate_missing_entity_question(intent_result)

        # 默认问题
        return ClarificationQuestion(
            clarification_type=clarification_type,
            question_text="我不太确定您的意图，能否详细说明？",
            options=["重新描述", "选择其他操作"],
            context=user_input,
            original_intent=intent_result.intent,
        )

    def _determine_clarification_type(
        self, intent_result: IntentResult
    ) -> ClarificationType:
        """
        确定澄清类型

        Args:
            intent_result: 意图识别结果

        Returns:
            ClarificationType
        """
        # 置信度过低
        if intent_result.confidence < self.CONFIDENCE_THRESHOLD:
            return ClarificationType.LOW_CONFIDENCE

        # 意图模糊
        if intent_result.is_ambiguous:
            return ClarificationType.AMBIGUOUS

        # 缺少关键实体
        intent = intent_result.intent
        required_entities = self.KEY_ENTITIES.get(intent, [])

        for entity in required_entities:
            if (
                entity not in intent_result.entities
                or not intent_result.entities[entity]
            ):
                return ClarificationType.MISSING_ENTITY

        return ClarificationType.TRIGGER_PATTERN

    def _generate_low_confidence_question(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion:
        """生成低置信度问题"""
        intent = intent_result.intent

        # 检查是否有匹配的模板
        template = self._find_matching_template(user_input)

        if template:
            questions = template.get("questions", [])
            return ClarificationQuestion(
                clarification_type=ClarificationType.LOW_CONFIDENCE,
                question_text="\n".join(questions),
                options=[str(i) for i in range(1, len(questions) - 1)],
                context=user_input,
                original_intent=intent,
            )

        # 默认低置信度问题
        return ClarificationQuestion(
            clarification_type=ClarificationType.LOW_CONFIDENCE,
            question_text="我不太确定您想做什么。您是想：\n1. 创作章节\n2. 更新设定\n3. 查询信息\n4. 其他操作\n请选择或详细说明。",
            options=["1", "2", "3", "4"],
            context=user_input,
            original_intent=intent,
        )

    def _generate_ambiguous_question(
        self, intent_result: IntentResult
    ) -> ClarificationQuestion:
        """生成模糊意图问题"""
        alternatives = intent_result.alternatives or []

        # 构建选项
        options_text = []
        options = []

        for i, alt in enumerate(alternatives[:3], 1):  # 最多显示3个替代选项
            alt_intent = alt.get("intent", "")
            alt_entities = alt.get("entities", {})

            # 生成选项描述
            option_desc = self._generate_intent_description(alt_intent, alt_entities)
            options_text.append(f"{i}. {option_desc}")
            options.append(str(i))

        question = f"您的表达有多种理解方式：\n{chr(10).join(options_text)}\n请选择最接近的选项，或补充说明。"

        return ClarificationQuestion(
            clarification_type=ClarificationType.AMBIGUOUS,
            question_text=question,
            options=options,
            context=str(intent_result.entities),
            original_intent=intent_result.intent,
        )

    def _generate_trigger_question(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion:
        """生成触发模式问题"""
        template = self._find_matching_template(user_input)

        if template:
            questions = template.get("questions", [])
            return ClarificationQuestion(
                clarification_type=ClarificationType.TRIGGER_PATTERN,
                question_text="\n".join(questions),
                options=[str(i) for i in range(1, len(questions) - 1)],
                context=user_input,
                original_intent=intent_result.intent,
            )

        # 未找到模板，返回通用问题
        return ClarificationQuestion(
            clarification_type=ClarificationType.TRIGGER_PATTERN,
            question_text="请详细说明您想做什么。",
            options=["重新描述"],
            context=user_input,
            original_intent=intent_result.intent,
        )

    def _generate_missing_entity_question(
        self, intent_result: IntentResult
    ) -> ClarificationQuestion:
        """生成缺少实体问题"""
        intent = intent_result.intent
        required_entities = self.KEY_ENTITIES.get(intent, [])

        missing = []
        for entity in required_entities:
            if (
                entity not in intent_result.entities
                or not intent_result.entities[entity]
            ):
                missing.append(entity)

        # 生成提示
        entity_names = {
            "chapter": "章节号",
            "character": "角色名",
            "character_name": "角色名",
            "ability": "能力名",
            "faction_name": "势力名",
            "faction": "势力名",
        }

        missing_names = [entity_names.get(e, e) for e in missing if e]
        # 过滤掉 None 值
        missing_names = [name for name in missing_names if name]

        question = f"请补充以下信息：\n- {chr(10).join(f'请提供「{name}」' for name in missing_names)}\n您可以直接回复，如「第一章」「血牙」等。"

        return ClarificationQuestion(
            clarification_type=ClarificationType.MISSING_ENTITY,
            question_text=question,
            options=missing_names,
            context=str(intent_result.entities),
            original_intent=intent,
        )

    def _find_matching_template(self, user_input: str) -> Optional[Dict[str, Any]]:
        """
        查找匹配的澄清模板

        Args:
            user_input: 用户输入

        Returns:
            匹配的模板
        """
        for intent_key, template in self.CLARIFICATION_TEMPLATES.items():
            triggers = template.get("triggers", [])

            for trigger in triggers:
                if trigger in user_input.lower():
                    return template

        return None

    def _generate_intent_description(
        self, intent: str, entities: Dict[str, str]
    ) -> str:
        """
        生成意图描述

        Args:
            intent: 意图类型
            entities: 实体字典

        Returns:
            意图描述
        """
        descriptions = {
            "start_chapter": f"创作第{entities.get('chapter', '?')}章",
            "add_character": f"添加角色「{entities.get('character_name', '?')}」",
            "add_character_ability": f"为「{entities.get('character', '?')}」添加能力「{entities.get('ability', '?')}」",
            "add_faction": f"添加势力「{entities.get('faction_name', '?')}」",
            "modify_character": f"修改「{entities.get('character', '?')}」的设定",
            "query_character": f"查询「{entities.get('character_name', '?')}」的设定",
            "add_hook": f"埋下伏笔「{entities.get('hook_content', '?')}」",
            "add_resource": f"记录「{entities.get('character', '?')}」获得「{entities.get('resource', '?')}」",
        }

        return descriptions.get(intent, intent)

    def process_clarification_response(
        self, user_response: str, clarification: ClarificationQuestion
    ) -> Dict[str, Any]:
        """
        处理用户澄清回复

        Args:
            user_response: 用户回复
            clarification: 澄清问题

        Returns:
            处理结果
        """
        result: Dict[str, Any] = {
            "resolved": False,
            "new_intent": None,
            "new_entities": {},
            "needs_retry": False,
        }

        # 尝试解析选项选择
        if user_response.strip() in clarification.options:
            # 用户选择了某个选项
            option_index = clarification.options.index(user_response.strip())

            # 根据澄清类型处理
            if clarification.clarification_type == ClarificationType.AMBIGUOUS:
                # 从替代选项中选择
                # 这里需要外部提供 alternatives 数据
                result["resolved"] = True
                result["needs_retry"] = True

            elif clarification.clarification_type in [
                ClarificationType.LOW_CONFIDENCE,
                ClarificationType.TRIGGER_PATTERN,
            ]:
                # 用户选择了操作类型，需要重新处理
                result["resolved"] = True
                result["needs_retry"] = True

        else:
            # 用户提供了详细描述
            result["resolved"] = True
            result["needs_retry"] = True
            result["new_input"] = user_response

        # 记录澄清历史
        self._clarification_history.append(clarification)

        return result

    def get_clarification_history(self, limit: int = 10) -> List[ClarificationQuestion]:
        """
        获取澄清历史

        Args:
            limit: 返回数量

        Returns:
            澄清历史列表
        """
        return self._clarification_history[-limit:]

    def clear_history(self) -> None:
        """清空澄清历史"""
        self._clarification_history = []


# 测试代码
if __name__ == "__main__":
    from .intent_classifier import IntentClassifier

    classifier = IntentClassifier()
    clarifier = IntentClarifier()

    print("=" * 60)
    print("意图澄清器测试")
    print("=" * 60)

    # 测试低置信度
    test_inputs = [
        "血牙更强了",
        "不对",
        "写一章",
    ]

    for input_text in test_inputs:
        result = classifier.classify(input_text)

        print(f"\n输入: {input_text}")
        print(f"意图: {result.intent}")
        print(f"置信度: {result.confidence:.2f}")
        print(f"需要澄清: {clarifier.needs_clarification(result)}")

        if clarifier.needs_clarification(result):
            question = clarifier.generate_clarification(result, input_text)
            print(f"\n澄清问题:\n{question.question_text}")
