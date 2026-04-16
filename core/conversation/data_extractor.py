#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
会话数据提取器
============

根据意图识别结果提取结构化数据并更新对应的设定文件。

核心功能：
- 意图到目标文件的映射
- 结构化数据提取
- 文件更新触发
- 向量数据库同步

参考：统一提炼引擎重构方案.md 第9.8节
"""

from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass
import json

from .intent_classifier import IntentResult, IntentCategory
from .file_updater import FileUpdater


@dataclass
class ExtractionResult:
    """提取结果"""

    status: str  # "updated", "skipped", "error"
    intent: str
    file_updated: Optional[str] = None
    vectorstore_synced: bool = False
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class ConversationDataExtractor:
    """会话数据提取器"""

    # 意图到目标文件的映射
    INTENT_FILE_MAPPING = {
        # 核心设定类
        "add_character": "设定/人物谱.md",
        "add_character_ability": "设定/人物谱.md",
        "add_character_relation": "设定/人物谱.md",
        "modify_character": "设定/人物谱.md",
        "add_faction": "设定/十大势力.md",
        "add_faction_member": "设定/十大势力.md",
        # 力量体系类
        "add_power_type": "设定/力量体系.md",
        "add_power_level": "设定/力量体系.md",
        "add_power_cost": "设定/力量体系.md",
        # 时间线类
        "add_era": "设定/时间线.md",
        "add_era_event": "设定/时间线.md",
        # 追踪系统类
        "add_hook": "设定/hook_ledger.md",
        "advance_hook": "设定/hook_ledger.md",
        "resolve_hook": "设定/hook_ledger.md",
        "add_resource": "设定/resource_ledger.md",
        "consume_resource": "设定/resource_ledger.md",
        "add_injury": "设定/resource_ledger.md",
        "add_character_info": "设定/information_boundary.md",
        "share_info": "设定/information_boundary.md",
        "add_payoff": "设定/payoff_tracking.md",
        "deliver_payoff": "设定/payoff_tracking.md",
        # 剧情类
        "modify_plot": "总大纲.md",
        "add_plot_point": "总大纲.md",
    }

    # 向量数据库Collection映射
    INTENT_COLLECTION_MAPPING = {
        "add_character": "novel_settings_v2",
        "add_character_ability": "novel_settings_v2",
        "add_character_relation": "novel_settings_v2",
        "add_faction": "novel_settings_v2",
        "add_faction_member": "novel_settings_v2",
        "add_power_type": "novel_settings_v2",
        "add_power_level": "novel_settings_v2",
        "modify_plot": "novel_plot_v1",  # 新增：I19
        "add_plot_point": "novel_plot_v1",  # 新增：I19
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化数据提取器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.file_updater = FileUpdater(str(self.project_root))

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        # 从当前文件向上查找
        current = Path(__file__).resolve()

        # 标记文件
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                if (parent / "设定").exists():
                    return parent

        # 如果找不到，使用当前工作目录
        return Path.cwd()

    def extract_and_update(
        self, user_input: str, intent_result: IntentResult
    ) -> ExtractionResult:
        """
        提取数据并更新文件

        Args:
            user_input: 用户原始输入
            intent_result: 意图识别结果

        Returns:
            ExtractionResult: 提取结果
        """
        intent = intent_result.intent

        # 检查是否是需要数据更新的意图
        if intent not in self.INTENT_FILE_MAPPING:
            return ExtractionResult(
                status="skipped",
                intent=intent,
                message=f"意图 '{intent}' 不需要数据更新",
            )

        # 获取目标文件
        target_file = self.INTENT_FILE_MAPPING[intent]

        # 提取结构化数据
        structured_data = self._extract_structured_data(intent, intent_result.entities)

        if not structured_data:
            return ExtractionResult(
                status="error",
                intent=intent,
                message="无法提取结构化数据",
            )

        # 更新源文件
        file_update_result = self._update_source_file(
            target_file, intent, structured_data
        )

        # 同步到向量数据库（如果需要）
        collection = self.INTENT_COLLECTION_MAPPING.get(intent)
        vectorstore_synced = False
        if collection:
            vectorstore_synced = self._sync_to_vectorstore(collection, structured_data)

        return ExtractionResult(
            status="updated" if file_update_result else "error",
            intent=intent,
            file_updated=target_file if file_update_result else None,
            vectorstore_synced=vectorstore_synced,
            message=self._generate_feedback(
                intent, structured_data, file_update_result
            ),
            data=structured_data,
        )

    def _extract_structured_data(
        self, intent: str, entities: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """
        提取结构化数据

        Args:
            intent: 意图类型
            entities: 提取的实体

        Returns:
            结构化数据字典
        """
        # 根据不同意图类型构建不同的数据结构
        data_builders = {
            "add_character": self._build_character_data,
            "add_character_ability": self._build_character_ability_data,
            "add_character_relation": self._build_relation_data,
            "add_faction": self._build_faction_data,
            "add_faction_member": self._build_faction_member_data,
            "modify_plot": self._build_plot_data,
            "add_hook": self._build_hook_data,
            "add_resource": self._build_resource_data,
            "add_payoff": self._build_payoff_data,
            "add_power_type": self._build_power_type_data,
            "add_power_level": self._build_power_level_data,
            "add_era": self._build_era_data,
        }

        builder = data_builders.get(intent)
        if builder:
            return builder(entities)

        # 默认：直接使用实体
        return {"entities": entities, "intent": intent}

    def _build_character_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建角色数据"""
        return {
            "type": "character",
            "name": entities.get("character_name", ""),
            "description": "",
            "abilities": [],
            "relations": [],
            "faction": "",
            "status": "active",
        }

    def _build_character_ability_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建角色能力数据"""
        return {
            "type": "character_ability",
            "character": entities.get("character", ""),
            "ability": entities.get("ability", ""),
            "description": "",
        }

    def _build_relation_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建关系数据"""
        return {
            "type": "character_relation",
            "character1": entities.get("character1", ""),
            "character2": entities.get("character2", ""),
            "relation": entities.get("relation", ""),
        }

    def _build_faction_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建势力数据"""
        return {
            "type": "faction",
            "name": entities.get("faction_name", ""),
            "description": "",
            "members": [],
            "power_type": "",
        }

    def _build_faction_member_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建势力成员数据"""
        return {
            "type": "faction_member",
            "character": entities.get("character", ""),
            "faction": entities.get("faction", ""),
        }

    def _build_plot_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建剧情数据"""
        return {
            "type": "plot_change",
            "content": entities.get("plot_change", ""),
        }

    def _build_hook_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建伏笔数据"""
        return {
            "type": "hook",
            "content": entities.get("hook_content", ""),
            "status": "planted",
            "chapter": "",
        }

    def _build_resource_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建资源数据"""
        return {
            "type": "resource",
            "character": entities.get("character", ""),
            "resource": entities.get("resource", ""),
            "action": "acquired",
        }

    def _build_payoff_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建承诺数据"""
        return {
            "type": "payoff",
            "character": entities.get("character", ""),
            "promise": entities.get("promise", ""),
            "status": "pending",
        }

    def _build_power_type_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建力量体系数据"""
        return {
            "type": "power_system",
            "name": entities.get("power_type", ""),
            "levels": [],
            "costs": [],
        }

    def _build_power_level_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建力量境界数据"""
        return {
            "type": "power_level",
            "system": entities.get("power_system", ""),
            "level": entities.get("level", ""),
        }

    def _build_era_data(self, entities: Dict[str, str]) -> Dict[str, Any]:
        """构建时代数据"""
        return {
            "type": "era",
            "name": entities.get("era_name", ""),
            "events": [],
        }

    def _update_source_file(
        self, file_path: str, intent: str, data: Dict[str, Any]
    ) -> bool:
        """
        更新源文件

        Args:
            file_path: 相对文件路径
            intent: 意图类型
            data: 结构化数据

        Returns:
            是否成功更新
        """
        full_path = self.project_root / file_path

        # 根据文件类型选择更新方法
        if file_path.endswith(".md"):
            return self.file_updater.update_markdown(str(full_path), intent, data)
        elif file_path.endswith(".json"):
            return self.file_updater.update_json(str(full_path), intent, data)

        return False

    def _sync_to_vectorstore(self, collection: str, data: Dict[str, Any]) -> bool:
        """
        同步到向量数据库

        Args:
            collection: Collection名称
            data: 数据内容

        Returns:
            是否成功同步
        """
        return self.file_updater.sync_to_vectorstore(collection, data)

    def _generate_feedback(
        self, intent: str, data: Dict[str, Any], success: bool
    ) -> str:
        """
        生成用户反馈

        Args:
            intent: 意图类型
            data: 数据内容
            success: 是否成功

        Returns:
            反馈消息
        """
        if not success:
            return f"❌ 更新失败：{intent}"

        # 根据意图类型生成不同反馈
        feedback_templates = {
            "add_character": "✅ 已记录新角色「{name}」，已更新人物谱",
            "add_character_ability": "✅ 已记录角色「{character}」的新能力「{ability}」",
            "add_faction": "✅ 已记录新势力「{name}」",
            "add_hook": "✅ 已记录伏笔「{content}」",
            "add_resource": "✅ 已记录资源变更：{character} 获得 {resource}",
            "add_payoff": "✅ 已记录承诺：{character} 发誓要 {promise}",
        }

        template = feedback_templates.get(intent)
        if template:
            try:
                return template.format(**data)
            except KeyError:
                pass

        return f"✅ 已更新：{intent}"

    def get_target_file(self, intent: str) -> Optional[str]:
        """获取意图对应的目标文件"""
        return self.INTENT_FILE_MAPPING.get(intent)

    def get_collection(self, intent: str) -> Optional[str]:
        """获取意图对应的向量数据库Collection"""
        return self.INTENT_COLLECTION_MAPPING.get(intent)


# 测试代码
if __name__ == "__main__":
    from .intent_classifier import IntentClassifier

    # 初始化
    classifier = IntentClassifier()
    extractor = ConversationDataExtractor()

    test_inputs = [
        "血牙有个新能力叫血脉守护",
        "加个新势力叫暗影宗",
        "这里埋个伏笔：血牙的身世之谜",
    ]

    print("=" * 60)
    print("会话数据提取器测试")
    print("=" * 60)

    for input_text in test_inputs:
        # 意图识别
        intent_result = classifier.classify(input_text)

        # 数据提取
        extraction_result = extractor.extract_and_update(input_text, intent_result)

        print(f"\n输入: {input_text}")
        print(f"意图: {extraction_result.intent}")
        print(f"状态: {extraction_result.status}")
        print(f"目标文件: {extraction_result.file_updated}")
        print(f"反馈: {extraction_result.message}")
        if extraction_result.data:
            print(f"数据: {json.dumps(extraction_result.data, ensure_ascii=False)}")
