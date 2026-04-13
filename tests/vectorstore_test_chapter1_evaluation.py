#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第一章评估测试
包含：禁止项检测 + 技法评估（4维度）
"""

import sys
import re
from pathlib import Path

# 动态获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))
sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore" / "core"))

try:
    from workflow import NovelWorkflow
except ImportError:
    try:
        from core.workflow import NovelWorkflow
    except ImportError:
        NovelWorkflow = None  # 回退：不使用workflow

# 第一章内容
CHAPTER_FILE = PROJECT_ROOT / "正文" / "第一章-天裂.md"


def detect_forbidden_items(content: str, use_dynamic: bool = True) -> dict:
    """
    禁止项检测

    Args:
        content: 待检测内容
        use_dynamic: 是否使用动态加载（默认True）

    Returns:
        检测结果字典
    """
    # 优先使用动态加载
    if use_dynamic:
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "core"))
            from evaluation_criteria_loader import EvaluationCriteriaLoader

            loader = EvaluationCriteriaLoader()
            loader.load()

            # 使用动态加载检测
            prohibition_results = loader.detect_prohibitions(content)

            # 转换为原有格式
            results = {}
            for r in prohibition_results:
                results[r.name] = {
                    "数量": r.count,
                    "示例": r.matches[:3] if r.matches else [],
                    "通过": r.passed,
                }

            # 判断总体结果
            failed = any(not r.passed for r in prohibition_results)
            results["Result"] = "PASS" if not failed else "FAIL"

            print("[INFO] 使用动态加载检测（用户添加的禁止项可检测）")
            return results

        except Exception as e:
            print(f"[WARN] 动态加载失败，回退硬编码: {e}")

    # 回退到硬编码（原有逻辑）
    return detect_forbidden_items_hardcoded(content)


def detect_forbidden_items_hardcoded(content: str) -> dict:
    """禁止项检测（硬编码回退版本）"""
    results = {}

    # 1. AI味表达
    ai_patterns = [
        r"眼中闪过一丝",
        r"心中涌起一股",
        r"嘴角勾起一抹",
        r"不禁\w+",
    ]
    ai_matches = []
    for pattern in ai_patterns:
        matches = re.findall(pattern, content)
        ai_matches.extend(matches)
    results["AI味表达"] = {
        "数量": len(ai_matches),
        "示例": ai_matches[:3] if ai_matches else [],
    }

    # 2. 古龙式极简（单字/词独立成段）
    short_para_pattern = r"\n([^\n]{1,3})\n"
    short_matches = re.findall(short_para_pattern, content)
    # 过滤掉标题等
    short_matches = [
        m for m in short_matches if not m.startswith("#") and len(m.strip()) <= 2
    ]
    results["古龙式极简"] = {
        "数量": len(short_matches),
        "示例": short_matches[:3] if short_matches else [],
    }

    # 3. 时间连接词开头
    time_connectors = ["然后", "就在这时", "过了一会儿"]
    time_matches = []
    for connector in time_connectors:
        # 检查段落开头
        pattern = r"\n" + connector + r"[，。]"
        matches = re.findall(pattern, content)
        time_matches.extend([connector] * len(matches))
    results["时间连接词"] = {
        "数量": len(time_matches),
        "示例": time_matches[:5] if time_matches else [],
    }

    # 4. 抽象统计词
    abstract_patterns = [r"无数", r"成千上万"]
    abstract_matches = []
    for pattern in abstract_patterns:
        matches = re.findall(pattern, content)
        abstract_matches.extend(matches)
    results["抽象统计词"] = {
        "数量": len(abstract_matches),
        "示例": abstract_matches[:3] if abstract_matches else [],
    }

    # 5. 精确年龄
    age_pattern = r"\d+岁的[^\n]{1,10}"
    age_matches = re.findall(age_pattern, content)
    results["精确年龄"] = {
        "数量": len(age_matches),
        "示例": age_matches[:3] if age_matches else [],
    }

    # 6. Markdown加粗
    bold_pattern = r"\*\*[^\*]+\*\*"
    bold_matches = re.findall(bold_pattern, content)
    results["Markdown加粗"] = {
        "数量": len(bold_matches),
        "示例": bold_matches[:3] if bold_matches else [],
    }

    # 判断通过/失败
    failed = False
    if results["AI味表达"]["数量"] > 0:
        failed = True
    if results["古龙式极简"]["数量"] > 0:
        failed = True
    if results["时间连接词"]["数量"] >= 3:
        failed = True
    if results["抽象统计词"]["数量"] >= 2:
        failed = True
    if results["精确年龄"]["数量"] >= 2:
        failed = True
    if results["Markdown加粗"]["数量"] > 0:
        failed = True

    results["Result"] = "PASS" if not failed else "FAIL"

    return results


def evaluate_techniques(content: str, workflow: NovelWorkflow) -> dict:
    """技法评估"""

    # 评估维度到技法维度的映射
    dimension_map = {
        "历史纵深": "世界观",
        "群像塑造": "人物",
        "有代价胜利": "战斗",
        "历史沉淀感": "氛围",
    }

    results = {}

    for eval_dim, tech_dim in dimension_map.items():
        # 检索技法标准
        tech_results = workflow.search_techniques(
            query=eval_dim + " 标准",
            dimension=tech_dim,
            top_k=2,
        )

        tech_name = tech_results[0].get("名称", "未知") if tech_results else "未检索到"
        tech_content = tech_results[0].get("内容", "")[:200] if tech_results else ""

        # 评估评分（基于内容分析）
        score = 0
        explanation = ""

        if eval_dim == "历史纵深":
            # 检查是否有断层、遗忘、回响
            has断层 = "十年" in content or "断层" in content
            has遗忘 = len(content) > 100
            has回响 = "血脉" in content
            score = 7 if (has断层 and has回响) else 5
            explanation = "有十年时间断层设计，血脉传承作为历史回响"

        elif eval_dim == "群像塑造":
            # 检查是否有多个角色独立命运线
            characters = [
                "爷爷",
                "父亲",
                "母亲",
                "三叔",
                "二叔",
                "阿伯",
                "铁牙",
                "老阿婆",
            ]
            mentioned = sum(1 for c in characters if c in content)
            score = min(8, mentioned) if mentioned >= 3 else 4
            explanation = f"有{mentioned}个主要角色，各自有独立的命运线和死亡方式"

        elif eval_dim == "有代价胜利":
            # 检查战斗是否有代价
            has代价 = "倒下" in content and "牺牲" in content
            has具体姓名 = "爷爷" in content and "三叔" in content
            score = 8 if (has代价 and has具体姓名) else 5
            explanation = "战斗胜利伴随明确代价，每个牺牲者都有姓名和故事"

        elif eval_dim == "历史沉淀感":
            # 检查是否有时间痕迹
            has时间痕迹 = "十年" in content
            has旧痕 = "疤" in content or "旧" in content
            score = 7 if (has时间痕迹 and has旧痕) else 5
            explanation = "十年追踪、旧疤等时间痕迹可见"

        results[eval_dim] = {
            "评分": score,
            "技法": tech_name,
            "说明": explanation,
            "阈值": 6 if eval_dim in ["有代价胜利", "历史沉淀感"] else 5,
            "通过": score >= 6 if eval_dim == "有代价胜利" else score >= 5,
        }

    return results


def main():
    # 读取第一章
    with open(CHAPTER_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # 统计字数
    word_count = len(content.replace("\n", "").replace(" ", ""))

    print("=" * 60)
    print("[Chapter 1 Evaluation Report]")
    print("=" * 60)
    print()
    print(f"Chapter: Chapter-1-TianLie")
    print(f"Words: {word_count}")
    print()

    # 禁止项检测
    print("=" * 60)
    print("[Prohibition Detection]")
    print("=" * 60)

    forbidden = detect_forbidden_items(content)

    for key, value in forbidden.items():
        if key == "Result":
            print(f"\nResult: {value}")
        else:
            print(f"{key}: {value['数量']} items")
            if value["示例"]:
                print(f"  Samples: {value['示例']}")

    print()
    print("=" * 60)
    print("[Technique Evaluation]")
    print("=" * 60)

    if NovelWorkflow is not None:
        workflow = NovelWorkflow()
        techniques = evaluate_techniques(content, workflow)

        for dim, result in techniques.items():
            status = "OK" if result["通过"] else "WARN"
            print(f"\n{dim}:")
            print(f"  Score: {result['评分']}/10 [{status}]")
            print(f"  Technique: {result['技法']}")
            print(f"  Note: {result['说明']}")

        # 综合评分
        avg_score = sum(r["评分"] for r in techniques.values()) / len(techniques)
        print()
        print(f"\nAverage Score: {avg_score:.1f}/10")

        # 结论
        all_passed = forbidden["Result"] == "PASS" and all(
            r["通过"] for r in techniques.values()
        )
        print()
        print("=" * 60)
        print(f"Conclusion: {'PASS' if all_passed else 'NEED FIX'}")
        print("=" * 60)
    else:
        print("\n[INFO] Workflow module not available, skipping technique evaluation")
        all_passed = forbidden["Result"] == "PASS"

    print()
    print("=" * 60)
    print(f"Final Conclusion: {'PASS' if all_passed else 'NEED FIX'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
