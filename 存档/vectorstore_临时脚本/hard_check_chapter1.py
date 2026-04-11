#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一章硬性约束检测
使用正则表达式检测AI味、古龙式等硬性约束
"""

import re
from pathlib import Path

CHAPTER_FILE = Path(r"D:\动画\众生界\正文\第一章-天裂.md")

# 检测规则
PATTERNS = {
    "AI味表达": [
        r"眼中闪过一丝",
        r"心中涌起一股",
        r"嘴角勾起一抹",
        r"不禁\w+",
        r"难以言喻",
    ],
    "抽象统计词": [
        r"无数",
        r"成千上万",
    ],
    "精确年龄": [
        r"\d+岁",
    ],
    "叙述转折": [
        r"^然后",
        r"^就在这时",
        r"^过了一会",
    ],
    "Markdown加粗": [
        r"\*\*[^*]+\*\*",
    ],
    "术语问题": [
        r"血脉之力",  # 应该用其他表达
    ],
}


def check_patterns(content: str, name: str, patterns: list) -> dict:
    """检测一组模式"""
    matches = []
    lines = content.split("\n")

    for pattern in patterns:
        regex = re.compile(pattern, re.MULTILINE)
        for i, line in enumerate(lines, 1):
            found = regex.findall(line)
            if found:
                matches.append(
                    {
                        "line": i,
                        "pattern": pattern,
                        "match": found[0] if isinstance(found[0], str) else found,
                        "context": line.strip()[:80],
                    }
                )

    return {"count": len(matches), "matches": matches, "passed": len(matches) == 0}


def main():
    print("=" * 60)
    print("第一章硬性约束检测报告")
    print("=" * 60)

    content = CHAPTER_FILE.read_text(encoding="utf-8")

    # 统计
    total_chars = len(content)
    total_lines = len(content.split("\n"))

    print(f"\n章节信息:")
    print(f"  总字符: {total_chars}")
    print(f"  总行数: {total_lines}")

    # 检测各项
    results = {}
    all_passed = True

    for name, patterns in PATTERNS.items():
        result = check_patterns(content, name, patterns)
        results[name] = result

        status = "PASS" if result["passed"] else f"FAIL ({result['count']}处)"
        print(f"\n【{name}】: {status}")

        if not result["passed"]:
            all_passed = False
            for m in result["matches"][:5]:  # 最多显示5个
                print(f"  行{m['line']}: {m['match']}")
                print(f"    上下文: {m['context']}...")

    # 总结
    print("\n" + "=" * 60)
    print("检测结果总结")
    print("=" * 60)

    for name, result in results.items():
        status = "✓ 通过" if result["passed"] else f"✗ 失败 ({result['count']}处)"
        print(f"  {name}: {status}")

    print(f"\n总体结果: {'✓ 全部通过' if all_passed else '✗ 存在问题'}")

    return all_passed


if __name__ == "__main__":
    import sys

    passed = main()
    sys.exit(0 if passed else 1)
