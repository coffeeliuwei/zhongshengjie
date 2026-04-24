#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审计报告生成器：大纲 key_settings vs 设定知识图谱 对照

输出：.cache/outline_vs_settings_report.json 与控制台摘要

逻辑：
1) 遍历项目根下“章节大纲/”与“总大纲.md”（存在则解析）
2) 使用 ChapterOutlineParser 提取 key_settings，标准化为 {entity, field, value, source}
3) 加载 .vectorstore/knowledge_graph.json 中的实体与属性
4) 以 entity+field 为键比对：
   - 两侧值相同 → duplicate
   - 两侧值不同 → conflict
   - 仅在大纲侧 → outline_only
   - 仅在设定侧 → settings_only（不输出，作为参考）

注意：此脚本为只读，不修改任何文件
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple

from core.parsing.chapter_outline_parser import ChapterOutlineParser
from core.config_loader import get_project_root, get_config_dir


def load_outline_key_settings(project_root: Path) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    parser = ChapterOutlineParser()

    # 1. 章节大纲目录
    outline_dir = project_root / "章节大纲"
    if outline_dir.exists():
        for fp in outline_dir.glob("*.md"):
            data = parser.parse_file(fp)
            if not data:
                continue
            key_settings = data.get("key_settings", {})
            for k, v in key_settings.items():
                results.append({
                    "entity": k.strip(),
                    "field": "关键设定",
                    "value": v.strip(),
                    "source": str(fp.relative_to(project_root))
                })

    # 2. 总大纲.md（可选）
    total_outline = project_root / "总大纲.md"
    if total_outline.exists():
        data = parser.parse_file(total_outline)
        if data:
            key_settings = data.get("key_settings", {})
            for k, v in key_settings.items():
                results.append({
                    "entity": k.strip(),
                    "field": "关键设定",
                    "value": v.strip(),
                    "source": "总大纲.md"
                })

    return results


def load_knowledge_graph(project_root: Path) -> Dict[str, Any]:
    kg_path = project_root / ".vectorstore" / "knowledge_graph.json"
    if not kg_path.exists():
        return {}
    with open(kg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_settings(kg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    将知识图谱实体的“属性”浅层展开为 entity -> { field -> value }
    仅做一层展开，嵌套对象以 JSON 串对比
    """
    mapping: Dict[str, Dict[str, Any]] = {}
    entities = kg.get("实体", {}) if isinstance(kg, dict) else {}
    for eid, info in entities.items():
        attrs = info.get("属性", {})
        flat: Dict[str, Any] = {}
        # 一层展平：保留原字段；若为 dict，则生成点分字段键（如 过往经历.年龄时间线）
        for k, v in attrs.items():
            if isinstance(v, dict):
                for sk, sv in v.items():
                    key = f"{k}.{sk}"
                    if isinstance(sv, (dict, list)):
                        flat[key] = json.dumps(sv, ensure_ascii=False, sort_keys=True)
                    else:
                        flat[key] = sv
                # 同时保留原字段 JSON 字符串供回退匹配
                flat[k] = json.dumps(v, ensure_ascii=False, sort_keys=True)
            elif isinstance(v, list):
                flat[k] = json.dumps(v, ensure_ascii=False, sort_keys=True)
            else:
                flat[k] = v
        # 使用别名：名称 字段 作为 entity 的候选 key
        name = info.get("名称") or eid
        mapping[name] = flat
        mapping[eid] = flat
    return mapping


def _load_field_aliases() -> Dict[str, str]:
    """从 config/audit_field_map.json 读取字段映射（不存在则返回默认通用映射）。"""
    cfg_path = get_config_dir() / "audit_field_map.json"
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8")).get("field_aliases", {})
        except Exception:
            pass
    # 默认通用映射（与设定中过往经历子字段对齐）
    return {
        "年龄": "过往经历.年龄时间线",
        "年龄时间线": "过往经历.年龄时间线",
        "父亲之死": "过往经历.父亲之死",
        "幸存原因": "过往经历.幸存原因",
        "目睹内容": "过往经历.目睹内容",
        "仇恨指向": "过往经历.仇恨指向",
    }


def _build_known_entities(settings_map: Dict[str, Dict[str, Any]]) -> List[str]:
    # settings_map 的 key 已包含 名称 与 id，直接使用
    return sorted(set(settings_map.keys()), key=len, reverse=True)


def _match_entity_prefix(text: str, candidates: List[str]) -> Tuple[str, str]:
    """在 text 中寻找最长前缀实体名，返回 (entity, suffix)；找不到返回 (text, '')."""
    for name in candidates:
        if text.startswith(name):
            return name, text[len(name):].lstrip()
    return text, ""


def _derive_entity_and_field(item: Dict[str, Any], settings_map: Dict[str, Dict[str, Any]]) -> Tuple[str, str]:
    """从大纲条目推导 entity 与精确字段名。
    规则：
    - 支持 "实体:字段" 键名（如 血牙:仇恨指向）
    - 支持“实体前缀+字段”的合并键：用已知实体名集合做最长前缀匹配，剩余作为字段候选
    - 常见中文键名通过别名映射到过往经历子字段（数据驱动，可在 config/audit_field_map.json 配置）
    - 否则返回 (entity, field) 原样
    """
    aliases = _load_field_aliases()
    entity = item["entity"].strip()
    field = item["field"].strip()
    key = entity
    # 1) 显式 "实体:字段"
    if ":" in key:
        e, f = [p.strip() for p in key.split(":", 1)]
        # 应用别名（若存在）
        return e, aliases.get(f, f)
    # 2) 合并键：实体名前缀 + 字段名（如 “血牙年龄”）
    e2, suffix = _match_entity_prefix(entity, _build_known_entities(settings_map))
    if suffix:
        suffix = suffix.lstrip(" ：:，,./")
        return e2, aliases.get(suffix, suffix or field)
    # 3) 若 field=关键设定，尝试将常见键名映射到子字段
    mapped = aliases.get(entity)
    if field == "关键设定" and mapped:
        return entity, mapped
    return entity, field


def build_report(outline_items: List[Dict[str, Any]], settings_map: Dict[str, Dict[str, Any]]):
    report = {
        "conflicts": [],
        "duplicates": [],
        "outline_only": [],
        "stats": {"outline_items": len(outline_items)}
    }

    for item in outline_items:
        # 推导更精确的 entity 与 field
        entity, field = _derive_entity_and_field(item, settings_map)
        value = item["value"]
        source = item["source"]

        settings = settings_map.get(entity)
        if not settings:
            report["outline_only"].append(item)
            continue

        # 支持点分字段（过往经历.年龄时间线），若未命中，回退到 JSON 串对比
        settings_value = settings.get(field)
        if settings_value is None and "." in field:
            root = field.split(".", 1)[0]
            settings_value = settings.get(root)
        if settings_value is None:
            report["outline_only"].append(item)
            continue

        # 统一字符串化对比
        sv = settings_value if isinstance(settings_value, str) else json.dumps(settings_value, ensure_ascii=False, sort_keys=True)
        if sv.strip() == value.strip():
            report["duplicates"].append(item)
        else:
            report["conflicts"].append({
                "entity": entity,
                "field": field,
                "outline_value": value,
                "settings_value": sv,
                "source": source
            })

    return report


def main():
    project_root = get_project_root()
    outline_items = load_outline_key_settings(project_root)
    kg = load_knowledge_graph(project_root)
    settings_map = flatten_settings(kg)

    report = build_report(outline_items, settings_map)

    out_dir = project_root / ".cache"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "outline_vs_settings_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 控制台摘要
    print("=== Outline vs Settings Audit ===")
    print(f"outline items: {report['stats']['outline_items']}")
    print(f"conflicts    : {len(report['conflicts'])}")
    print(f"duplicates   : {len(report['duplicates'])}")
    print(f"outline_only : {len(report['outline_only'])}")
    if report["conflicts"]:
        print("-- sample conflicts (up to 5) --")
        for c in report["conflicts"][:5]:
            print(f"- [{c['entity']}:{c['field']}] {c['outline_value']}  ||  {c['settings_value']}  ({c['source']})")


if __name__ == "__main__":
    main()
