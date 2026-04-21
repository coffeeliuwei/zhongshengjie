#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缺失信息检测器
============

检测执行所需但缺失的信息，主动询问用户补充。

核心功能：
- 检测缺失的必要信息
- 生成缺失信息提示
- 检测文件是否存在
- 检测设定是否完整

参考：统一提炼引擎重构方案.md 第10.3.4节
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, TypedDict, Union
from dataclasses import dataclass
from enum import Enum


class SeverityLevel(Enum):
    """严重程度"""

    CRITICAL = "critical"  # 必须处理
    WARNING = "warning"  # 建议处理
    INFO = "info"  # 可忽略


class RequiredInfoConfig(TypedDict, total=False):
    """必需信息配置"""

    check: Callable[..., bool]
    message: str
    suggestion: str
    severity: SeverityLevel
    auto_fix: bool


@dataclass
class MissingInfo:
    """缺失信息"""

    type: str
    message: str
    suggestion: str
    severity: SeverityLevel
    context: Optional[str] = None
    auto_fix_available: bool = False


class MissingInfoDetector:
    """缺失信息检测器"""

    # 必需信息定义 - 类型声明
    REQUIRED_INFO: Dict[str, Dict[str, RequiredInfoConfig]] = {
        # 章节创作
        "start_chapter": {
            "chapter_outline": {
                "check": lambda project_root, chapter: (
                    Path(project_root) / f"章节大纲/第{chapter}章大纲.md"
                ).exists(),
                "message": "章节大纲文件不存在",
                "suggestion": "先提供大纲，或让我根据总大纲生成",
                "severity": SeverityLevel.WARNING,
                "auto_fix": True,
            },
            "character_settings": {
                # [N16 2026-04-18] start_chapter 调用方总传 (project_root, chapter)，
                # 这里不需要 chapter 但必须接受第二个参数避免 TypeError
                "check": lambda project_root, _chapter: (
                    Path(project_root) / "设定/人物谱.md"
                ).exists(),
                "message": "角色设定文件不存在",
                "suggestion": "请先创建角色设定",
                "severity": SeverityLevel.WARNING,
                "auto_fix": False,
            },
            "worldview_config": {
                # [N16 2026-04-18] 同上
                "check": lambda project_root, _chapter: (
                    Path(project_root) / "config" / "worlds"
                ).exists(),
                "message": "世界观配置目录不存在",
                "suggestion": "使用默认世界观或创建自定义配置",
                "severity": SeverityLevel.INFO,
                "auto_fix": True,
            },
        },
        # 角色能力添加
        "add_character_ability": {
            "character_exists": {
                "check": lambda project_root, entities: _check_character_exists(
                    project_root, entities.get("character", "")
                ),
                "message": "角色不存在于人物谱",
                "suggestion": "请先添加角色「{character}」，或使用现有角色",
                "severity": SeverityLevel.WARNING,
                "auto_fix": False,
            },
        },
        # 势力添加
        "add_faction": {
            "faction_file": {
                "check": lambda project_root: (
                    Path(project_root) / "设定/十大势力.md"
                ).exists(),
                "message": "势力设定文件不存在",
                "suggestion": "创建势力设定文件",
                "severity": SeverityLevel.WARNING,
                "auto_fix": True,
            },
        },
        # 数据提炼
        "full_extraction": {
            "novel_library": {
                "check": lambda project_root: _check_novel_library(project_root),
                "message": "未配置外部小说库路径",
                "suggestion": "在 config.json 中配置 novel_sources.directories",
                "severity": SeverityLevel.CRITICAL,
                "auto_fix": False,
            },
            "vector_database": {
                "check": lambda project_root: _check_vector_database(),
                "message": "向量数据库未连接",
                "suggestion": "启动 Qdrant: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant",
                "severity": SeverityLevel.CRITICAL,
                "auto_fix": False,
            },
        },
        # 工作流继续
        "continue_workflow": {
            "pending_workflow": {
                "check": lambda project_root, session_id: False,  # 需要外部检查
                "message": "没有未完成的工作流",
                "suggestion": "先启动一个工作流",
                "severity": SeverityLevel.INFO,
                "auto_fix": False,
            },
        },
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化缺失信息检测器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        return Path.cwd()

    def detect_missing(
        self, intent: str, entities: Dict[str, str], session_id: Optional[str] = None
    ) -> List[MissingInfo]:
        """
        检测缺失信息

        Args:
            intent: 意图类型
            entities: 提取的实体
            session_id: 会话ID（可选）

        Returns:
            缺失信息列表
        """
        missing: List[MissingInfo] = []

        # 获取该意图的必需信息配置
        required_config = self.REQUIRED_INFO.get(intent)

        if not required_config:
            return missing

        # 检查每个必需项
        for info_type, config in required_config.items():
            check_func = config.get("check")
            if not check_func:
                continue

            # 调用检查函数
            try:
                # 根据意图类型传递不同参数
                if intent == "start_chapter":
                    chapter = entities.get("chapter", "1")
                    is_ok = check_func(str(self.project_root), chapter)
                elif intent == "add_character_ability":
                    is_ok = check_func(str(self.project_root), entities)
                elif intent == "continue_workflow":
                    is_ok = check_func(str(self.project_root), session_id or "")
                else:
                    is_ok = check_func(str(self.project_root))

                if not is_ok:
                    # 格式化消息和建议
                    message = config.get("message", "未知问题")
                    suggestion = config.get("suggestion", "请检查")

                    # 替换模板变量
                    if "{character}" in suggestion:
                        suggestion = suggestion.replace(
                            "{character}", entities.get("character", "")
                        )

                    missing.append(
                        MissingInfo(
                            type=info_type,
                            message=message,
                            suggestion=suggestion,
                            severity=config.get("severity", SeverityLevel.WARNING),
                            context=str(entities),
                            auto_fix_available=config.get("auto_fix", False),
                        )
                    )

            except Exception as e:
                print(f"Error checking {info_type}: {e}")

        return missing

    def generate_missing_prompt(self, missing: List[MissingInfo]) -> str:
        """
        生成缺失信息提示

        Args:
            missing: 缺失信息列表

        Returns:
            提示文本
        """
        if not missing:
            return ""

        # 图标映射
        icons = {
            SeverityLevel.CRITICAL: "❌",
            SeverityLevel.WARNING: "⚠️",
            SeverityLevel.INFO: "ℹ️",
        }

        lines = ["我注意到以下问题，可能影响创作质量："]

        # 添加问题描述
        for m in missing:
            icon = icons.get(m.severity, "⚠️")
            lines.append(f"{icon} {m.message}")

        # 添加建议
        lines.append("\n建议：")
        suggestions = list(set(m.suggestion for m in missing))
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")

        # 添加自动修复提示
        auto_fix_available = any(m.auto_fix_available for m in missing)
        if auto_fix_available:
            lines.append("\n部分问题可以自动修复。回复「自动修复」来处理。")

        lines.append("\n您希望如何处理？")

        return "\n".join(lines)

    def check_file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 相对文件路径

        Returns:
            是否存在
        """
        full_path = self.project_root / file_path
        return full_path.exists()

    def check_setting_complete(self, setting_type: str) -> Dict[str, Any]:
        """
        检查设定是否完整

        Args:
            setting_type: 设定类型（character, faction, power, timeline）

        Returns:
            检查结果
        """
        result: Dict[str, Any] = {
            "exists": False,
            "complete": False,
            "missing_items": [],
        }

        setting_files = {
            "character": "设定/人物谱.md",
            "faction": "设定/十大势力.md",
            "power": "设定/力量体系.md",
            "timeline": "设定/时间线.md",
        }

        file_path = setting_files.get(setting_type)
        if not file_path:
            return result

        full_path = self.project_root / file_path
        result["exists"] = full_path.exists()

        if result["exists"]:
            try:
                content = full_path.read_text(encoding="utf-8")

                # 检查是否有内容
                result["complete"] = len(content.strip()) > 100

                # 简单的完整性检查
                missing_items: List[str] = []
                if setting_type == "character" and "###" not in content:
                    missing_items.append("缺少角色条目")
                result["missing_items"] = missing_items

            except Exception:
                result["complete"] = False

        return result

    def auto_fix(self, missing: List[MissingInfo]) -> Dict[str, Any]:
        """
        自动修复可修复的问题

        Args:
            missing: 缺失信息列表

        Returns:
            修复结果
        """
        fixed = []
        failed = []

        for m in missing:
            if m.auto_fix_available:
                success = self._try_auto_fix(m)
                if success:
                    fixed.append(m.type)
                else:
                    failed.append(m.type)

        return {
            "fixed": fixed,
            "failed": failed,
            "message": f"自动修复完成：{len(fixed)}个成功，{len(failed)}个失败",
        }

    def _try_auto_fix(self, missing_info: MissingInfo) -> bool:
        """
        尝试自动修复

        Args:
            missing_info: 缺失信息

        Returns:
            是否成功修复
        """
        # 创建缺失的文件
        if missing_info.type in ["chapter_outline", "faction_file", "worldview_config"]:
            try:
                # 根据类型创建文件
                if missing_info.type == "chapter_outline":
                    # 从总大纲生成章节大纲
                    return self._generate_chapter_outline()

                elif missing_info.type == "faction_file":
                    # 创建势力设定文件
                    return self._create_faction_file()

                elif missing_info.type == "worldview_config":
                    # 创建默认世界观配置
                    return self._create_default_worldview()

            except Exception as e:
                print(f"Auto fix failed: {e}")
                return False

        return False

    def _generate_chapter_outline(self) -> bool:
        """生成章节大纲"""
        # 这里简化实现，实际需要调用工作流
        outline_dir = self.project_root / "章节大纲"
        outline_dir.mkdir(parents=True, exist_ok=True)

        # 创建示例大纲
        sample_outline = """# 第一章大纲

## 场景列表
1. 开篇场景
2. 觉醒场景
3. 战斗场景

## 关键设定
- 主角：血牙
- 场景类型：开篇、觉醒、战斗

---
> 自动生成，请补充详细内容
"""

        outline_file = outline_dir / "第一章大纲.md"
        outline_file.write_text(sample_outline, encoding="utf-8")

        return True

    def _create_faction_file(self) -> bool:
        """创建势力设定文件"""
        setting_dir = self.project_root / "设定"
        setting_dir.mkdir(parents=True, exist_ok=True)

        sample_faction = """# 十大势力

> 自动生成于 {date}

---

## 势力列表

### 1. 血牙宗
- 简介：待填写
- 成员：待填写
- 力量类型：血脉之力

---
""".format(date=__import__("datetime").datetime.now().strftime("%Y-%m-%d"))

        faction_file = setting_dir / "十大势力.md"
        faction_file.write_text(sample_faction, encoding="utf-8")

        return True

    def _create_default_worldview(self) -> bool:
        """创建默认世界观配置"""
        worldview_dir = self.project_root / "config" / "worlds"
        worldview_dir.mkdir(parents=True, exist_ok=True)

        # 复制默认配置
        return True


# 辅助检查函数
def _check_character_exists(project_root: str, character_name: str) -> bool:
    """检查角色是否存在"""
    if not character_name:
        return True  # 没有角色名时跳过检查

    character_file = Path(project_root) / "设定/人物谱.md"

    if not character_file.exists():
        return False

    try:
        content = character_file.read_text(encoding="utf-8")
        return character_name in content
    except Exception:
        return False


def _check_novel_library(project_root: str) -> bool:
    """检查小说库配置"""
    config_file = Path(project_root) / "config.json"

    if not config_file.exists():
        return False

    try:
        import json

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 检查是否配置了小说库路径
        novel_sources = config.get("novel_sources", {})
        directories = novel_sources.get("directories", [])

        return len(directories) > 0

    except Exception:
        return False


def _check_vector_database() -> bool:
    """检查向量数据库连接"""
    try:
        from qdrant_client import QdrantClient
        from core.config_loader import get_qdrant_url

        client = QdrantClient(url=get_qdrant_url())
        client.get_collections()
        return True

    except Exception:
        return False


# 测试代码
if __name__ == "__main__":
    detector = MissingInfoDetector()

    print("=" * 60)
    print("缺失信息检测器测试")
    print("=" * 60)

    # 测试章节创作缺失检测
    missing = detector.detect_missing(
        intent="start_chapter",
        entities={"chapter": "一"},
    )

    print(f"\n检测到缺失信息: {len(missing)} 条")
    for m in missing:
        print(f"  - {m.severity.value}: {m.message}")

    if missing:
        print("\n" + detector.generate_missing_prompt(missing))
