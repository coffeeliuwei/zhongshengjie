# core/inspiration/constraint_library.py
"""反模板约束库读写

约束库存储在 config/dimensions/anti_template_constraints.json。
本模块提供读取、按场景筛选、随机抽取的接口。
不进行约束 JSON 的修改（修改通过对话工作流触发，见 resonance_feedback）。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §3
"""

import json
import random
from pathlib import Path
from typing import List, Optional, Dict, Any


DEFAULT_CONSTRAINTS_PATH = Path("config/dimensions/anti_template_constraints.json")


class ConstraintLibrary:
    """反模板约束库。

    使用模式：
        lib = ConstraintLibrary()
        active = lib.filter_by_scene_type("战斗")
        picked = lib.pick_for_variants("战斗", n=2)
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else DEFAULT_CONSTRAINTS_PATH
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        """加载约束 JSON 文件"""
        if not self.path.exists():
            return {"version": "0.0", "constraints": []}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_active(self) -> List[Dict[str, Any]]:
        """所有 status='active' 的约束"""
        return [
            c for c in self._data.get("constraints", []) if c.get("status") == "active"
        ]

    def filter_by_scene_type(self, scene_type: str) -> List[Dict[str, Any]]:
        """筛选可兼容指定场景类型的活跃约束"""
        return [
            c
            for c in self.list_active()
            if scene_type in c.get("trigger_scene_types", [])
        ]

    def pick_for_variants(
        self,
        scene_type: str,
        n: int,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """为 N 个变体抽取约束，不同类别优先

        策略：
        1. 池中不足 N 个时，返回全部可用
        2. 池中足够时，先从不同类别各抽 1 条，再随机补足
        """
        pool = self.filter_by_scene_type(scene_type)
        if len(pool) <= n:
            return pool

        rng = random.Random(seed) if seed is not None else random.Random()

        # 按类别分桶
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for c in pool:
            by_category.setdefault(c["category"], []).append(c)

        picked: List[Dict[str, Any]] = []
        # 第一轮：每类别抽 1 条，类别顺序随机
        categories = list(by_category.keys())
        rng.shuffle(categories)
        for cat in categories:
            if len(picked) >= n:
                break
            choice = rng.choice(by_category[cat])
            picked.append(choice)

        # 第二轮：若仍不足 N，从剩余池中随机补
        if len(picked) < n:
            remaining = [c for c in pool if c not in picked]
            rng.shuffle(remaining)
            picked.extend(remaining[: n - len(picked)])

        return picked

    def get_by_id(self, constraint_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 查找约束"""
        for c in self._data.get("constraints", []):
            if c.get("id") == constraint_id:
                return c
        return None

    def get_version(self) -> str:
        """获取约束库版本"""
        return self._data.get("version", "0.0")

    def count_total(self) -> int:
        """统计约束总数（含 disabled）"""
        return len(self._data.get("constraints", []))

    def count_active(self) -> int:
        """统计活跃约束数"""
        return len(self.list_active())

    def list_categories(self) -> List[str]:
        """列出所有约束类别"""
        return list({c["category"] for c in self.list_active()})
