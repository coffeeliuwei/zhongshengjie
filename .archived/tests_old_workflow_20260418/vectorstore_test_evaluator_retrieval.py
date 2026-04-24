#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估器技法检索优先级测试
验证：数据库优先 → 文件回退
"""

import sys
from pathlib import Path

# 动态获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))
from workflow import NovelWorkflow

# 技法文件路径（回退用）
TECHNIQUE_DIR = PROJECT_ROOT / "创作技法"

# 维度到文件映射
DIMENSION_FILE_MAP = {
    "世界观": "01-世界观维度/02-世界观维度.md",
    "剧情": "02-剧情维度/03-剧情维度.md",
    "人物": "03-人物维度/04-人物维度.md",
    "战斗": "04-战斗冲突维度/05-战斗冲突维度.md",
    "氛围": "05-氛围意境维度/06-氛围意境维度.md",
}

# 评估维度到技法维度的映射
dimension_map = {
    "历史纵深": "世界观",
    "群像塑造": "人物",
    "有代价胜利": "战斗",
    "历史沉淀感": "氛围",
}


def main():
    workflow = NovelWorkflow()

    db_count = 0
    file_count = 0
    results_detail = []
    file_fallback_detail = []

    for eval_dim, tech_dim in dimension_map.items():
        # Step 1: 数据库检索（优先）
        try:
            results = workflow.search_techniques(
                query=eval_dim + " 标准",
                dimension=tech_dim,
                top_k=2,
            )

            if results and len(results) > 0:
                db_count += 1
                results_detail.append(
                    {
                        "评估维度": eval_dim,
                        "技法维度": tech_dim,
                        "技法名称": results[0].get("名称", "未知"),
                        "检索方式": "数据库",
                        "内容长度": len(results[0].get("内容", "")),
                    }
                )
                continue
        except Exception as e:
            print(f"[数据库检索失败] {eval_dim}: {e}")

        # Step 2: 文件回退（数据库失败时）
        file_path = TECHNIQUE_DIR / DIMENSION_FILE_MAP[tech_dim]
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                file_count += 1
                file_fallback_detail.append(
                    {
                        "评估维度": eval_dim,
                        "技法维度": tech_dim,
                        "文件路径": str(file_path),
                        "检索方式": "文件回退",
                        "原因": "数据库检索失败或无结果",
                    }
                )
            except Exception as e:
                print(f"[文件读取失败] {file_path}: {e}")

    print("=" * 60)
    print("【检索流程验证】")
    print("=" * 60)
    print()
    print("数据库检索成功:")
    for r in results_detail:
        print(f"  - {r['评估维度']}: {r['技法名称']} (内容{r['内容长度']}字)")
    print()
    print("文件回退:")
    for r in file_fallback_detail:
        print(f"  - {r['评估维度']}: {r['文件路径']}")
    print()
    print(f"[检索统计] 数据库: {db_count}条, 文件回退: {file_count}条")


if __name__ == "__main__":
    main()
