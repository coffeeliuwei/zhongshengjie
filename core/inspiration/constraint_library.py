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

from core.config_loader import get_project_root as _get_project_root


def _default_constraints_path() -> Path:
    """从配置获取约束文件路径（而非硬编码相对路径）"""
    return (
        _get_project_root() / "config" / "dimensions" / "anti_template_constraints.json"
    )


DEFAULT_CONSTRAINTS_PATH = _default_constraints_path()


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
        """为 N 个变体抽取约束，加权随机（保证类别多样性）

        策略：
        1. 从池中随机抽 n 个（加权，多条目类别有更大概率）
        2. 若所有 n 个来自同一类别，替换 1 个为其他类别（保证最低多样性）
        """
        import random

        pool = self.filter_by_scene_type(scene_type)
        if len(pool) <= n:
            return pool

        rng = random.Random(seed)
        picked = rng.sample(pool, n)

        # 检查多样性：若全部来自同一类别，替换最后一个
        categories_picked = {p.get("category") for p in picked}
        if len(categories_picked) == 1 and len(pool) > n:
            other_pool = [c for c in pool if c.get("category") not in categories_picked]
            if other_pool:
                replacement = rng.choice(other_pool)
                picked[-1] = replacement

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

    # ============================================================
    # P1-4 新增:菜单化语义(鉴赏师浏览 API)
    # ============================================================

    def as_menu(self, scene_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """返回活跃约束的菜单视图(不随机、不采样)。

        Args:
            scene_type: None 返回全部活跃条目;否则只含 trigger_scene_types 包含该场景的条目。
        Returns:
            List[dict],每项 5 字段:id / category / trigger_scene_types /
            constraint_text / intensity(不含 status)。
            按 (category, id) 字典序排序。
        """
        if scene_type is None:
            pool = self.list_active()
        else:
            pool = self.filter_by_scene_type(scene_type)
        items = [
            {
                "id": c["id"],
                "category": c["category"],
                "trigger_scene_types": list(c.get("trigger_scene_types", [])),
                "constraint_text": c["constraint_text"],
                "intensity": c["intensity"],
            }
            for c in pool
        ]
        items.sort(key=lambda c: (c["category"], c["id"]))
        return items

    def count_by_category(self) -> Dict[str, int]:
        """按类别统计活跃约束数(disabled 不计入)。"""
        counts: Dict[str, int] = {}
        for c in self.list_active():
            cat = c.get("category", "")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """对活跃约束的 constraint_text 做 case-insensitive 子串搜索。

        Args:
            keyword: 非空字符串,纯空白视为非法。
        Returns:
            与 as_menu 字段一致的 dict 列表(不含 status)。
        Raises:
            ValueError: keyword 为空或纯空白。
        """
        if not keyword or not keyword.strip():
            raise ValueError("search_by_keyword.keyword 必须非空")
        needle = keyword.lower()
        out: List[Dict[str, Any]] = []
        for c in self.list_active():
            if needle in c.get("constraint_text", "").lower():
                out.append(
                    {
                        "id": c["id"],
                        "category": c["category"],
                        "trigger_scene_types": list(c.get("trigger_scene_types", [])),
                        "constraint_text": c["constraint_text"],
                        "intensity": c["intensity"],
                    }
                )
        return out

    def format_menu_text(self, scene_type: Optional[str] = None) -> str:
        """生成中文 Markdown 菜单,供鉴赏师 prompt 注入。

        标题:`## 反模板约束菜单(场景:XXX | 全部场景,共 N 条)`
        分组:按 category,小节 `### {category} ({n})`
        条目:`- {id} [{intensity}]:{constraint_text}`
        无匹配:追加一行 `无可用约束`。
        """
        items = self.as_menu(scene_type=scene_type)
        scene_label = f"场景:{scene_type}" if scene_type else "全部场景"
        lines: List[str] = [f"## 反模板约束菜单({scene_label},共 {len(items)} 条)"]
        if not items:
            lines.append("")
            lines.append("无可用约束")
            return "\n".join(lines)

        # 保持 as_menu 已按 (category, id) 排序的顺序
        from itertools import groupby
        for category, group in groupby(items, key=lambda c: c["category"]):
            group_list = list(group)
            lines.append("")
            lines.append(f"### {category} ({len(group_list)})")
            for c in group_list:
                lines.append(
                    f"- {c['id']} [{c['intensity']}]:{c['constraint_text']}"
                )
        return "\n".join(lines)
