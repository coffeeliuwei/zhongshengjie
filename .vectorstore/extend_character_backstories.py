#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展角色实体属性 - 将过往经历、情绪触发、行为烙印整合到知识图谱

执行方式：
    python extend_character_backstories.py
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir, get_settings_dir

# 配置
PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
KNOWLEDGE_GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"
BACKSTORY_FILE = get_settings_dir() / "角色过往经历与情绪触发.md"


def parse_backstory_file() -> Dict[str, Dict]:
    """解析角色过往经历文件"""

    with open(BACKSTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    characters = {}

    # 按角色分割 - 使用 findall 而非 split，更可靠
    # 格式: #### 数字. 角色名（身份）
    # 有些角色如血牙有额外标记，需要清理
    character_pattern = r"####\s*\d+\.\s*([^\(]+?)\s*（([^）]+?)）.*?\n"
    matches = list(re.finditer(character_pattern, content))

    print(f"  [解析] 找到 {len(matches)} 个角色区块")

    for idx, match in enumerate(matches):
        char_name = match.group(1).strip()
        char_identity = match.group(2).strip()

        # 获取该角色的内容（从匹配结束到下一个角色或文件结束）
        start_pos = match.end()
        if idx + 1 < len(matches):
            end_pos = matches[idx + 1].start()
        else:
            end_pos = len(content)

        char_content = content[start_pos:end_pos]

        # 解析过往经历
        backstory = parse_backstory_section(char_content)

        # 解析情绪触发
        emotion_triggers = parse_emotion_section(char_content)

        # 解析行为烙印
        behavior_imprints = parse_behavior_section(char_content)

        characters[char_name] = {
            "身份": char_identity,
            "过往经历": backstory,
            "情绪触发": emotion_triggers,
            "行为烙印": behavior_imprints,
        }

        print(
            f"  [解析] {char_name}（{char_identity}): 过往经历={len(backstory)}项, 情绪={len(emotion_triggers)}种, 行为烙印={len(behavior_imprints)}条"
        )

    return characters


def parse_backstory_section(content: str) -> Dict[str, str]:
    """解析过往经历部分"""
    backstory = {}

    # 查找过往经历部分
    backstory_match = re.search(
        r"\*\*过往经历\*\*[：:]?\s*\n(.*?)(?=\n\*\*情绪触发|\n---|\n####|\Z)",
        content,
        re.DOTALL,
    )
    if not backstory_match:
        return backstory

    backstory_content = backstory_match.group(1)

    # 解析表格中的内容
    dimensions = [
        "童年",
        "成长期",
        "关键事件",
        "关键创伤",
        "形成的信念",
        "创伤",
        "我是谁根源",
        "孤独根源",
    ]

    for dim in dimensions:
        # 匹配表格行: | **维度** | 内容 | ...
        pattern = rf"\|\s*\*\*{re.escape(dim)}\*\*\s*\|\s*([^|]+)\s*\|"
        match = re.search(pattern, backstory_content)
        if match:
            backstory[dim] = match.group(1).strip()

    # 也匹配带（早期）/（后期）的信念
    belief_pattern = r"\|\s*\*\*形成的信念（早期）\*\*\s*\|\s*([^|]+)\s*\|"
    match = re.search(belief_pattern, backstory_content)
    if match:
        backstory["形成的信念（早期）"] = match.group(1).strip()

    belief_pattern = r"\|\s*\*\*形成的信念（后期）\*\*\s*\|\s*([^|]+)\s*\|"
    match = re.search(belief_pattern, backstory_content)
    if match:
        backstory["形成的信念（后期）"] = match.group(1).strip()

    return backstory


def parse_emotion_section(content: str) -> Dict[str, Dict[str, str]]:
    """解析情绪触发部分"""
    emotions = {}

    # 查找情绪触发部分
    emotion_match = re.search(
        r"\*\*情绪触发\*\*[：:]?\s*\n(.*?)(?=\n\*\*行为烙印|\n---|\n####|\Z)",
        content,
        re.DOTALL,
    )
    if not emotion_match:
        return emotions

    emotion_content = emotion_match.group(1)

    # 解析表格中的情绪
    emotion_types = [
        "平静",
        "愤怒",
        "悲伤",
        "焦虑",
        "恐惧",
        "兴奋",
        "挣扎",
        "纠结",
        "温暖",
        "崩溃",
        "接受",
        "解脱",
        "被控制",
    ]

    for emotion in emotion_types:
        # 匹配表格行
        pattern = rf"\|\s*{re.escape(emotion)}\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|"
        match = re.search(pattern, emotion_content)
        if match:
            emotions[emotion] = {
                "触发条件": match.group(1).strip(),
                "行为变化": match.group(2).strip(),
            }

    return emotions


def parse_behavior_section(content: str) -> List[Dict[str, str]]:
    """解析行为烙印部分"""
    imprints = []

    # 查找行为烙印部分
    behavior_match = re.search(
        r"\*\*行为烙印\*\*[：:]?\s*\n(.*?)(?=\n---|\n####|\Z)", content, re.DOTALL
    )
    if not behavior_match:
        return imprints

    behavior_content = behavior_match.group(1)

    # 解析表格行
    lines = behavior_content.split("\n")
    for line in lines:
        if (
            line.startswith("|")
            and not line.startswith("| 触发情境")
            and not line.startswith("|---")
        ):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 3:
                imprints.append(
                    {
                        "触发情境": parts[0],
                        "行为反应": parts[1],
                        "依据": parts[2] if len(parts) > 2 else "",
                    }
                )

    return imprints


def update_knowledge_graph(characters: Dict[str, Dict]) -> None:
    """更新知识图谱中的角色实体"""

    # 读取现有知识图谱
    with open(KNOWLEDGE_GRAPH_FILE, "r", encoding="utf-8") as f:
        kg_data = json.load(f)

    entities = kg_data.get("实体", {})
    updated_count = 0

    # 角色名映射（处理可能的名称差异）
    name_mapping = {
        "林夕": "char_linxi",
        "艾琳娜": "char_elena",
        "塞巴斯蒂安": "char_sebastian",
        "陈傲天": "char_chen_aotian",
        "洛影": "char_luoying",
        "赵恒": "char_zhaoheng",
        "林正阳": "char_lin_zhengyang",
        "苏瑾": "char_sujin",
        "鬼影": "char_guiying",
        "白露": "char_bailu",
        "李道远": "char_li_daoyuan",
        "血牙": "char_xueya",
        "虎啸": "char_huxiao",
        "花姬": "char_huaji",
        "月牙": "char_yueya",
        "零": "char_zero",
        "幽灵": "char_youling",
        "艾达": "char_aida",  # Note: not in current KG, may need to add
        "陈风": "char_chenfeng",  # Note: not in current KG, may need to add
        "老鬼": "char_laogui",  # Note: not in current KG, may need to add
        "K-7": "char_k7",
        "镜": "char_jing",
        "小蝶": "char_xiaodie",
    }

    # 更新每个角色实体
    for char_name, char_data in characters.items():
        # 查找对应的实体ID
        entity_id = name_mapping.get(char_name)

        # 如果映射不存在，尝试在实体中搜索
        if not entity_id:
            for eid, entity in entities.items():
                if entity.get("名称") == char_name and entity.get("类型") == "角色":
                    entity_id = eid
                    break

        if entity_id and entity_id in entities:
            # 更新实体属性
            entity = entities[entity_id]

            # 添加过往经历
            if char_data["过往经历"]:
                if "属性" not in entity:
                    entity["属性"] = {}
                entity["属性"]["过往经历"] = char_data["过往经历"]

            # 添加情绪触发
            if char_data["情绪触发"]:
                if "属性" not in entity:
                    entity["属性"] = {}
                entity["属性"]["情绪触发"] = char_data["情绪触发"]

            # 添加行为烙印
            if char_data["行为烙印"]:
                if "属性" not in entity:
                    entity["属性"] = {}
                entity["属性"]["行为烙印"] = char_data["行为烙印"]

            updated_count += 1
            print(f"  [OK] 已更新: {char_name}")
        else:
            print(f"  [WARN] 未找到实体: {char_name}")

    # 保存更新后的知识图谱
    with open(KNOWLEDGE_GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(kg_data, f, ensure_ascii=False, indent=2)

    print(f"\n[完成] 已更新 {updated_count} 个角色实体")


def main():
    print("=" * 60)
    print("扩展角色实体属性 - 过往经历/情绪触发/行为烙印")
    print("=" * 60)

    # 解析角色过往经历文件
    print("\n[1/2] 解析角色过往经历文件...")
    characters = parse_backstory_file()
    print(f"  解析到 {len(characters)} 个角色")

    # 更新知识图谱
    print("\n[2/2] 更新知识图谱...")
    update_knowledge_graph(characters)

    print("\n" + "=" * 60)
    print("扩展完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
