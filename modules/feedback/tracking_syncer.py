# -*- coding: utf-8 -*-
"""
追踪同步层 - 修改后自动更新追踪文件
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .types import ModificationLevel, TrackingUpdate

# 配置导入
try:
    from core.config_loader import get_project_root
except ImportError:
    # 兼容独立运行场景
    def get_project_root():
        return Path.cwd()


class TrackingSyncer:
    """追踪同步器"""

    # 追踪文件路径
    TRACKING_FILES = {
        "hook_ledger": "追踪/hook_ledger.json",
        "timeline_tracking": "追踪/timeline_tracking.json",
        "information_boundary": "追踪/information_boundary.json",
        "payoff_tracking": "追踪/payoff_tracking.json",
    }

    # 是否需要更新的规则
    UPDATE_RULES = {
        ModificationLevel.WORD_POLISH: False,  # 不更新
        ModificationLevel.CONTENT_TWEAK: "detect",  # 检测后决定
        ModificationLevel.PLOT_CHANGE: True,  # 必须更新
        ModificationLevel.SETTING_CHANGE: True,  # 必须更新
    }

    def __init__(self, project_root: str = None):
        """
        初始化追踪同步器

        Args:
            project_root: 项目根目录，默认从配置自动获取
        """
        if project_root is None:
            self.project_root = get_project_root()
        else:
            self.project_root = Path(project_root)

    def sync(
        self,
        original_content: str,
        modified_content: str,
        modification_level: ModificationLevel,
        tracking_files: Dict[str, Any] = None,
    ) -> TrackingUpdate:
        """
        同步追踪文件

        Args:
            original_content: 原内容
            modified_content: 修改后内容
            modification_level: 修改层级
            tracking_files: 当前追踪文件内容（可选）

        Returns:
            TrackingUpdate: 追踪更新结果
        """
        # 1. 检查是否需要更新
        need_update = self._need_update(modification_level)

        if not need_update:
            return TrackingUpdate(manual_confirm_needed=["层级1修改，无需更新追踪文件"])

        # 2. 检测内容变化
        changes = self._detect_changes(original_content, modified_content)

        # 3. 分析变化对追踪的影响
        impact = self._analyze_impact(changes, modification_level)

        # 4. 生成更新内容
        updates = self._generate_updates(impact, tracking_files)

        # 5. 确定需要人工确认的项目
        manual_confirm = self._get_manual_confirm_items(impact)

        return TrackingUpdate(
            hook_ledger=updates.get("hook_ledger", {}),
            timeline_tracking=updates.get("timeline_tracking", {}),
            information_boundary=updates.get("information_boundary", {}),
            payoff_tracking=updates.get("payoff_tracking", {}),
            manual_confirm_needed=manual_confirm,
        )

    def _need_update(self, modification_level: ModificationLevel) -> bool:
        """检查是否需要更新"""
        rule = self.UPDATE_RULES.get(modification_level, False)
        return rule is True or rule == "detect"

    def _detect_changes(self, original: str, modified: str) -> List[Dict[str, Any]]:
        """检测内容变化"""
        changes = []

        # 使用 SequenceMatcher 找出变化
        matcher = SequenceMatcher(None, original, modified)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                changes.append(
                    {
                        "type": "replace",
                        "original": original[i1:i2],
                        "modified": modified[j1:j2],
                        "position": i1,
                    }
                )
            elif tag == "delete":
                changes.append(
                    {
                        "type": "delete",
                        "original": original[i1:i2],
                        "modified": "",
                        "position": i1,
                    }
                )
            elif tag == "insert":
                changes.append(
                    {
                        "type": "insert",
                        "original": "",
                        "modified": modified[j1:j2],
                        "position": i1,
                    }
                )

        return changes

    def _analyze_impact(
        self, changes: List[Dict[str, Any]], modification_level: ModificationLevel
    ) -> Dict[str, Any]:
        """分析变化对追踪的影响"""
        impact = {
            "hooks": [],
            "timeline": [],
            "boundaries": [],
            "payoffs": [],
            "severity": "LOW",
        }

        # 关键词模式
        hook_patterns = [r"伏笔[:：]\s*(.+)", r"暗示[:：]\s*(.+)", r"埋下[:：]\s*(.+)"]

        payoff_patterns = [
            r"代价[:：]\s*(.+)",
            r"牺牲[:：]\s*(.+)",
            r"付出[:：]\s*(.+)",
        ]

        # 分析每个变化
        for change in changes:
            modified_text = change.get("modified", "")

            # 检测伏笔变化
            for pattern in hook_patterns:
                matches = re.findall(pattern, modified_text)
                for match in matches:
                    impact["hooks"].append(
                        {
                            "content": match,
                            "position": change["position"],
                            "change_type": change["type"],
                        }
                    )

            # 检测代价变化
            for pattern in payoff_patterns:
                matches = re.findall(pattern, modified_text)
                for match in matches:
                    impact["payoffs"].append(
                        {
                            "content": match,
                            "position": change["position"],
                            "change_type": change["type"],
                        }
                    )

        # 根据修改层级确定严重程度
        if modification_level == ModificationLevel.PLOT_CHANGE:
            impact["severity"] = "MEDIUM"
        elif modification_level == ModificationLevel.SETTING_CHANGE:
            impact["severity"] = "HIGH"

        return impact

    def _generate_updates(
        self, impact: Dict[str, Any], tracking_files: Dict[str, Any]
    ) -> Dict[str, Dict]:
        """生成更新内容"""
        updates = {}

        # 更新 hook_ledger
        if impact["hooks"]:
            updates["hook_ledger"] = {
                "added_hooks": [
                    h["content"]
                    for h in impact["hooks"]
                    if h["change_type"] in ["insert", "replace"]
                ],
                "removed_hooks": [
                    h["content"]
                    for h in impact["hooks"]
                    if h["change_type"] == "delete"
                ],
            }

        # 更新 payoff_tracking
        if impact["payoffs"]:
            updates["payoff_tracking"] = {
                "added_payoffs": [
                    p["content"]
                    for p in impact["payoffs"]
                    if p["change_type"] in ["insert", "replace"]
                ],
                "removed_payoffs": [
                    p["content"]
                    for p in impact["payoffs"]
                    if p["change_type"] == "delete"
                ],
            }

        # 根据严重程度更新其他追踪
        if impact["severity"] in ["MEDIUM", "HIGH"]:
            updates["timeline_tracking"] = {
                "needs_review": True,
                "reason": "剧情修改可能影响时间线",
            }
            updates["information_boundary"] = {
                "needs_review": True,
                "reason": "剧情修改可能影响信息边界",
            }

        return updates

    def _get_manual_confirm_items(self, impact: Dict[str, Any]) -> List[str]:
        """获取需要人工确认的项目"""
        items = []

        if impact["severity"] == "HIGH":
            items.append("设定修改影响全书，建议人工确认追踪更新")

        if len(impact["hooks"]) > 3:
            items.append(f"检测到{len(impact['hooks'])}处伏笔变化，建议人工确认")

        if len(impact["payoffs"]) > 2:
            items.append(f"检测到{len(impact['payoffs'])}处代价变化，建议人工确认")

        return items

    def load_tracking_file(self, name: str) -> Dict[str, Any]:
        """加载追踪文件"""
        if name not in self.TRACKING_FILES:
            return {}

        file_path = self.project_root / self.TRACKING_FILES[name]
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[TrackingSyncer] 加载追踪文件失败: {e}")
            return {}

    def save_tracking_file(self, name: str, data: Dict[str, Any]) -> bool:
        """保存追踪文件"""
        if name not in self.TRACKING_FILES:
            return False

        file_path = self.project_root / self.TRACKING_FILES[name]
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[TrackingSyncer] 保存追踪文件失败: {e}")
            return False


def sync_tracking(
    original_content: str,
    modified_content: str,
    modification_level: ModificationLevel,
    tracking_files: Dict[str, Any] = None,
    project_root: str = None,
) -> TrackingUpdate:
    """
    同步追踪文件（便捷函数）

    Args:
        original_content: 原内容
        modified_content: 修改后内容
        modification_level: 修改层级
        tracking_files: 当前追踪文件
        project_root: 项目根目录，默认从配置自动获取

    Returns:
        追踪更新结果
    """
    syncer = TrackingSyncer(project_root)
    return syncer.sync(
        original_content, modified_content, modification_level, tracking_files
    )
