#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M8 A类硬编码批量替换脚本
=======================

将 skill 文件中的世界观专属名词替换为通用占位符。
在 *示例代码块* 中使用占位符，保留文档可读性。

运行：
    cd "C:/Users/39477/.agents/skills"
    python "D:/动画/众生界/docs/m8_artifacts/m8_replace_a_class.py" --dry-run
    python "D:/动画/众生界/docs/m8_artifacts/m8_replace_a_class.py" --apply

注意：
    - --dry-run  只打印差异，不写文件（默认）
    - --apply    实际写入文件
    - 已有 "示例:" / "[众生界示例]" 标注的段落不做替换
"""

import re
import sys
from pathlib import Path

SKILLS_DIR = Path.home() / ".agents" / "skills"

# ──────────────────────────────────────────────
# 替换规则：(正则模式, 替换文本, 说明)
# 顺序有优先级：较长/较精确的规则放前面
# ──────────────────────────────────────────────
RULES = [
    # B/C 类（以防遗漏，再跑一遍兜底）
    (r'D:/动画/众生界/章节经验日志', '{PROJECT_ROOT}/{experience_dir}', 'B类路径'),
    (r'D:\\动画\\众生界\\创作技法\\', '{PROJECT_ROOT}/{techniques_dir}/', 'B类路径'),
    (r'E:/Users/39477/Desktop/', '<用户本地路径>/', 'C类路径'),

    # A 类——角色名（在代码示例和 YAML 示例中替换）
    # 规则：只替换出现在 Python 代码块 / YAML 代码块中的，
    #       保留 markdown 散文里作为"众生界示例"的说明性引用
    # 策略：替换 = 在引号内的字符串 + 字典 value + YAML 值
    (r'"血牙"', '"[示例角色A]"', 'A类角色名'),
    (r"'血牙'", "'[示例角色A]'", 'A类角色名'),
    (r': "血牙"', ': "[示例角色A]"', 'A类角色名(YAML)'),
    (r'（血牙）', '（[示例角色A]）', 'A类角色名'),
    (r'"林夕"', '"[示例角色B]"', 'A类角色名'),
    (r"'林夕'", "'[示例角色B]'", 'A类角色名'),
    (r': "林夕"', ': "[示例角色B]"', 'A类角色名(YAML)'),

    # A 类——地点名
    (r'"村庄广场"', '"[示例地点]"', 'A类地点名'),
    (r"'村庄广场'", "'[示例地点]'", 'A类地点名'),
    (r': "村庄广场"', ': "[示例地点]"', 'A类地点名(YAML)'),
    (r'"东方修仙界"', '"[势力/区域名]"', 'A类区域名'),
    (r"'东方修仙界'", "'[势力/区域名]'", 'A类区域名'),
    (r': "东方修仙界"', ': "[势力/区域名]"', 'A类区域名(YAML)'),

    # A 类——力量体系（仅限 API 调用参数，不替换体系说明文字）
    (r'get_power_battle_guide\("修仙"\)', 'get_power_battle_guide("[力量体系名]")', 'A类API参数'),
    (r'get_battle_expert_techniques\("修仙"\)', 'get_battle_expert_techniques("[力量体系名]")', 'A类API参数'),
    (r'compose_battle_scene\(\s*power_name="修仙"', 'compose_battle_scene(\n    power_name="[力量体系名]"', 'A类API参数'),
    (r'search_battle_cases\("修仙战斗', 'search_battle_cases("[力量体系名]战斗', 'A类API查询'),
    (r'get_character_profile\("血牙"\)', 'get_character_profile("[主要角色名]")', 'A类API参数'),
    (r'get_faction_character_guide\("兽族文明"\)', 'get_faction_character_guide("[势力名]")', 'A类API参数'),
    (r'get_character_behavior_patterns\("东方修仙"\)', 'get_character_behavior_patterns("[势力名]")', 'A类API参数'),
    (r'compose_character_scene\(\s*character_name="血牙"', 'compose_character_scene(\n    character_name="[主要角色名]"', 'A类API参数'),
    (r'faction_name="兽族文明"', 'faction_name="[势力名]"', 'A类API参数'),

    # A 类——血脉/力量体系特有名词（仅在 YAML/代码块值位置）
    (r'"血脉-天裂"', '"[力量技能名]"', 'A类力量名'),
    (r"'血脉-天裂'", "'[力量技能名]'", 'A类力量名'),
    (r': "血脉-天裂', ': "[力量技能名]"', 'A类力量名(YAML)'),
    (r'默认引用: "血脉-天裂基础设定"', '默认引用: "[世界观默认设定]"', 'A类设定引用'),
    (r'血设定: "血脉-天裂"', '血设定: "[力量技能名]"', 'A类力量名'),
    (r'get_battle_cost_rules\("血脉燃烧"\)', 'get_battle_cost_rules("[代价类型名]")', 'A类API参数'),
]

# 以下模式命中则 **跳过该行**（不替换），避免破坏文档性说明
SKIP_LINE_PATTERNS = [
    r'^\s*#',           # Python注释
    r'\[众生界示例\]',   # 已标注示例
    r'^\s*>',          # Markdown引用块（说明性文字）
    r'^\| \*\*',       # Markdown表格标题行
]


def should_skip(line: str) -> bool:
    for pat in SKIP_LINE_PATTERNS:
        if re.search(pat, line):
            return True
    return False


def process_file(path: Path, apply: bool = False) -> int:
    """处理单个文件，返回替换次数"""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    new_lines = []
    total_changes = 0

    for line in lines:
        if should_skip(line):
            new_lines.append(line)
            continue

        new_line = line
        for pattern, replacement, label in RULES:
            new_line, n = re.subn(pattern, replacement, new_line)
            if n > 0:
                total_changes += n

        new_lines.append(new_line)

    if total_changes > 0:
        new_text = "".join(new_lines)
        if apply:
            path.write_text(new_text, encoding="utf-8")
            print(f"  [OK] 写入 {path.name}：{total_changes} 处替换")
        else:
            print(f"  [DRY-RUN] {path.name}：{total_changes} 处会被替换（dry-run，未写入）")

    return total_changes


def main():
    apply = "--apply" in sys.argv
    dry_run = not apply
    mode = "dry-run" if dry_run else "APPLY"
    print(f"\n=== M8 A类替换脚本 [{mode}] ===")
    print(f"Skills 目录: {SKILLS_DIR}\n")

    skill_files = list(SKILLS_DIR.rglob("SKILL.md"))
    if not skill_files:
        print("❌ 未找到任何 SKILL.md，请检查 SKILLS_DIR 路径")
        sys.exit(1)

    grand_total = 0
    for sf in sorted(skill_files):
        count = process_file(sf, apply=apply)
        grand_total += count

    print(f"\n{'=' * 40}")
    print(f"合计 {grand_total} 处{'（dry-run，未写入）' if dry_run else '已写入'}")
    if dry_run:
        print("用 --apply 参数实际执行替换")


if __name__ == "__main__":
    main()