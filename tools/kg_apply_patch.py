#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将大纲审计得到的血牙信息写入 .vectorstore/knowledge_graph.json 的实体映射。
仅添加，不覆盖已有字段。运行后请手动执行 sync_manager 同步入库。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from core.config_loader import get_project_root


def main():
    project_root = get_project_root()
    kg_path = project_root / ".vectorstore" / "knowledge_graph.json"
    if not kg_path.exists():
        raise SystemExit(f"knowledge_graph.json 不存在：{kg_path}")

    data: Dict[str, Any] = json.loads(kg_path.read_text(encoding="utf-8"))
    entities = data.setdefault("实体", {})

    eid = "character_bloody_fang"
    if eid not in entities:
        entities[eid] = {
            "id": eid,
            "名称": "血牙",
            "类型": "角色",
            "属性": {}
        }

    attrs: Dict[str, Any] = entities[eid].setdefault("属性", {})
    attrs.setdefault("阵营", "兽族文明")
    attrs.setdefault("血脉", "熊血脉（守护之力）")
    history = attrs.setdefault("过往经历", {})
    history.setdefault("年龄时间线", "灭族时约10-13岁，现在约23岁（十年后）")
    history.setdefault("父亲之死", "铁牙在山林中张开双臂护妇孺，后背被射成筛子战死")
    history.setdefault("幸存原因", "母亲藏进树洞，血脉自动压制气息，未被佣兵发现")
    # 用列表承载多项目睹内容
    if "目睹内容" not in history:
        history["目睹内容"] = ["上吊的妇孺被肢解", "村口男人残肢"]
    history.setdefault("仇恨指向", "佣兵联盟（当时并不知 AI 入侵真相）")

    # 简单维护元数据统计中的角色数量（可选）
    meta = data.setdefault("元数据", {})
    stats = meta.setdefault("实体统计", {})
    try:
        # 去重计数：按“角色”键自增（仅在此前未包含血牙时大致修正）
        if eid not in entities:
            stats["角色"] = int(stats.get("角色", 0)) + 1
    except Exception:
        pass

    kg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入实体：{eid} → {kg_path}")


if __name__ == "__main__":
    main()
