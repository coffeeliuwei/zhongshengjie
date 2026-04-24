#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
解析缺失数据并更新知识图谱

缺失数据：
1. 行为预判模板.md - 场景模板、情绪状态对照表
2. 角色过往经历与情绪触发.md - 角色深度设定
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir, get_settings_dir

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
SETTINGS_DIR = get_settings_dir()
KNOWLEDGE_GRAPH = VECTORSTORE_DIR / "knowledge_graph.json"

# ============================================================
# 解析行为预判模板
# ============================================================


def parse_behavior_template():
    """解析行为预判模板.md"""
    file_path = SETTINGS_DIR / "行为预判模板.md"

    if not file_path.exists():
        print(f"[警告] 文件不存在: {file_path}")
        return {}, {}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析场景模板（16种核心场景）
    scene_templates = {}

    # 找到"核心场景类型"后的表格
    scene_section = re.search(r"核心场景类型.*?\n\n\|(.+?)\n```", content, re.DOTALL)
    if scene_section:
        table_content = scene_section.group(1)
        # 解析表格行
        for line in table_content.split("\n"):
            if line.startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 3 and cells[0] and not cells[0].startswith("场景"):
                    # 移除**标记
                    scene_name = cells[0].replace("**", "").strip()
                    core_elements = cells[1].strip()
                    concerns = cells[2].strip()

                    scene_templates[scene_name] = {
                        "id": f"template_{scene_name}",
                        "名称": scene_name,
                        "类型": "预判模板",
                        "属性": {"核心要素": core_elements, "常见行为关注点": concerns},
                    }

    # 解析情绪状态对照表
    emotion_states = {}

    emotion_section = re.search(
        r"情绪状态对照表.*?\n\n\|(.+?)\n---", content, re.DOTALL
    )
    if emotion_section:
        table_content = emotion_section.group(1)
        for line in table_content.split("\n"):
            if line.startswith("|") and "---" not in line:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 4 and cells[0] and not cells[0].startswith("情绪"):
                    emotion_name = cells[0].replace("**", "").strip()
                    cognitive = cells[1].strip()
                    behavior = cells[2].strip()
                    typical = cells[3].strip()

                    emotion_states[emotion_name] = {
                        "认知影响": cognitive,
                        "行为倾向": behavior,
                        "典型表现": typical,
                    }

    print(f"[解析] 场景模板: {len(scene_templates)}个")
    print(f"[解析] 情绪状态: {len(emotion_states)}种")

    return scene_templates, emotion_states


# ============================================================
# 解析角色深度设定
# ============================================================


def parse_character_deep_settings():
    """解析角色过往经历与情绪触发.md"""
    file_path = SETTINGS_DIR / "角色过往经历与情绪触发.md"

    if not file_path.exists():
        print(f"[警告] 文件不存在: {file_path}")
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {}
    lines = content.split("\n")

    current_role = None
    current_section = None
    in_table = False
    table_rows = []

    for line in lines:
        # 检测角色名
        role_match = re.match(r"####\s+(\d+)\.\s*([^\s（(（]+)", line)
        if role_match:
            # 保存上一个角色
            if current_role and current_section and table_rows:
                _save_table_data(result, current_role, current_section, table_rows)

            current_role = role_match.group(2).strip()
            result[current_role] = {"过往经历": {}, "情绪触发": {}, "行为烙印": []}
            current_section = None
            in_table = False
            table_rows = []
            continue

        if not current_role:
            continue

        # 检测章节
        if "**过往经历**" in line:
            if current_section and table_rows:
                _save_table_data(result, current_role, current_section, table_rows)
            current_section = "过往经历"
            in_table = False
            table_rows = []
        elif "**情绪触发**" in line:
            if current_section and table_rows:
                _save_table_data(result, current_role, current_section, table_rows)
            current_section = "情绪触发"
            in_table = False
            table_rows = []
        elif "**行为烙印**" in line:
            if current_section and table_rows:
                _save_table_data(result, current_role, current_section, table_rows)
            current_section = "行为烙印"
            in_table = False
            table_rows = []

        # 检测表格行
        elif current_section and line.strip().startswith("|"):
            if re.match(r"^\|[\s\-:]+\|", line):
                in_table = True
                continue

            if in_table:
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells:
                    table_rows.append(cells)

    # 保存最后一组
    if current_role and current_section and table_rows:
        _save_table_data(result, current_role, current_section, table_rows)

    print(f"[解析] 角色深度设定: {len(result)}个角色")

    return result


def _save_table_data(result, role, section, rows):
    """保存表格数据"""
    if not rows or role not in result:
        return

    if section == "过往经历":
        for row in rows:
            if len(row) >= 2:
                dimension = row[0].replace("**", "").strip()
                content = row[1].strip() if len(row) > 1 else ""
                impact = row[2].strip() if len(row) > 2 else ""
                result[role]["过往经历"][dimension] = {"内容": content, "影响": impact}

    elif section == "情绪触发":
        for row in rows:
            if len(row) >= 2:
                emotion = row[0].replace("**", "").strip()
                trigger = row[1].strip() if len(row) > 1 else ""
                behavior = row[2].strip() if len(row) > 2 else ""
                result[role]["情绪触发"][emotion] = {
                    "触发条件": trigger,
                    "行为变化": behavior,
                }

    elif section == "行为烙印":
        for row in rows:
            if len(row) >= 2:
                situation = row[0].replace("**", "").strip()
                reaction = row[1].strip() if len(row) > 1 else ""
                basis = row[2].strip() if len(row) > 2 else ""
                result[role]["行为烙印"].append(
                    {"触发情境": situation, "行为反应": reaction, "依据": basis}
                )


# ============================================================
# 更新知识图谱
# ============================================================


def update_knowledge_graph(scene_templates, emotion_states, character_deep):
    """更新知识图谱"""

    # 读取现有数据
    with open(KNOWLEDGE_GRAPH, "r", encoding="utf-8") as f:
        data = json.load(f)

    entities = data.get("实体", {})

    # 1. 添加场景模板
    for name, template in scene_templates.items():
        entities[template["id"]] = template
    print(f"[更新] 添加场景模板: {len(scene_templates)}个")

    # 2. 添加情绪状态对照表（作为单个参考数据实体）
    if emotion_states:
        entities["emotion_states_reference"] = {
            "id": "emotion_states_reference",
            "名称": "情绪状态对照表",
            "类型": "参考数据",
            "属性": emotion_states,
        }
        print(f"[更新] 添加情绪状态对照表: 1个")

    # 3. 更新角色深度设定
    updated_chars = 0
    for eid, entity in entities.items():
        if entity.get("类型") != "角色":
            continue

        char_name = entity.get("名称", "")
        if char_name in character_deep:
            deep_data = character_deep[char_name]

            # 获取现有属性
            props = entity.get("属性", {})
            if isinstance(props, str):
                try:
                    props = json.loads(props)
                except:
                    props = {}

            # 更新属性
            props["过往经历"] = deep_data.get("过往经历", {})
            props["情绪触发"] = deep_data.get("情绪触发", {})
            props["行为烙印"] = deep_data.get("行为烙印", [])

            entity["属性"] = props
            updated_chars += 1

    print(f"[更新] 更新角色深度设定: {updated_chars}个")

    # 更新元数据
    data["实体"] = entities
    metadata = data.get("元数据", {})
    metadata["更新时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata["数据来源"] = list(
        set(
            metadata.get("数据来源", [])
            + ["行为预判模板.md", "角色过往经历与情绪触发.md"]
        )
    )

    # 重新统计
    type_counts = {}
    for e in entities.values():
        t = e.get("类型", "未知")
        type_counts[t] = type_counts.get(t, 0) + 1
    metadata["实体类型分布"] = type_counts

    data["元数据"] = metadata

    # 保存
    with open(KNOWLEDGE_GRAPH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 知识图谱已更新")
    print(f"  总实体: {len(entities)}")
    print(f"  实体类型分布:")
    for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"    {t}: {count}")

    return len(entities)


# ============================================================
# 主函数
# ============================================================


def main():
    print("=" * 60)
    print("解析缺失数据并更新知识图谱")
    print("=" * 60)

    # 解析行为预判模板
    print("\n[1] 解析行为预判模板...")
    scene_templates, emotion_states = parse_behavior_template()

    # 解析角色深度设定
    print("\n[2] 解析角色深度设定...")
    character_deep = parse_character_deep_settings()

    # 更新知识图谱
    print("\n[3] 更新知识图谱...")
    update_knowledge_graph(scene_templates, emotion_states, character_deep)

    print("\n" + "=" * 60)
    print("完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
