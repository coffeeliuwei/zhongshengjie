#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一验证入口 - 一键运行所有验证脚本

使用方法：
    python verify_all.py              # 运行所有验证
    python verify_all.py --merge      # 只运行设定合并验证
    python verify_all.py --worldview  # 只运行世界观验证
    python verify_all.py --quick      # 快速验证（跳过耗时检查）
    python verify_all.py --history    # 显示验证历史

验证项目：
    1. verify_merge.py      - 哲学设定+社会结构合并验证
    2. verify_worldview.py  - 力量体系+时间线验证
    3. verify_structures.py - 技法入库验证
    4. verify_vectorstore.py- 向量库完整性验证
    5. check_sources.py    - 案例库来源检查
"""

import sys
import io
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Any

# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 配置
SCRIPT_DIR = Path(__file__).parent

# 导入验证历史模块
try:
    from verification_history import VerificationHistory

    HAS_HISTORY = True
except ImportError:
    HAS_HISTORY = False

# 验证脚本配置
VERIFICATION_SCRIPTS = [
    {
        "id": "merge",
        "name": "哲学设定+社会结构合并验证",
        "script": "verify_merge.py",
        "quick": True,
    },
    {
        "id": "worldview",
        "name": "力量体系+时间线验证",
        "script": "verify_worldview.py",
        "quick": True,
    },
    {
        "id": "structures",
        "name": "技法入库验证",
        "script": "verify_structures.py",
        "quick": True,
    },
    {
        "id": "vectorstore",
        "name": "向量库完整性验证",
        "script": "verify_vectorstore.py",
        "quick": False,
    },
    {
        "id": "sources",
        "name": "案例库来源检查",
        "script": "check_sources.py",
        "quick": False,
    },
]


def run_script(script_path: Path) -> Tuple[bool, str]:
    """
    运行单个验证脚本

    Returns:
        (success, output)
    """
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(SCRIPT_DIR),
            timeout=120,  # 2分钟超时
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return success, output
    except subprocess.TimeoutExpired:
        return False, "超时（超过120秒）"
    except Exception as e:
        return False, f"执行错误: {e}"


def run_all_verifications(quick: bool = False, selected: List[str] = None) -> dict:
    """
    运行所有验证

    Args:
        quick: 快速模式，跳过耗时检查
        selected: 只运行指定的验证（按id）

    Returns:
        {
            "passed": int,
            "failed": int,
            "results": [{"id", "name", "success", "output"}]
        }
    """
    results = []
    passed = 0
    failed = 0

    for config in VERIFICATION_SCRIPTS:
        # 选择性运行
        if selected and config["id"] not in selected:
            continue

        # 快速模式跳过
        if quick and not config["quick"]:
            print(f"[跳过] {config['name']} (快速模式)")
            continue

        script_path = SCRIPT_DIR / config["script"]

        print(f"\n{'=' * 60}")
        print(f"[运行] {config['name']}")
        print(f"{'=' * 60}")

        if not script_path.exists():
            print(f"[错误] 脚本不存在: {script_path}")
            results.append(
                {
                    "id": config["id"],
                    "name": config["name"],
                    "success": False,
                    "output": "脚本不存在",
                }
            )
            failed += 1
            continue

        success, output = run_script(script_path)

        # 打印输出
        print(output)

        status = "✓ 通过" if success else "✗ 失败"
        print(f"\n[{status}] {config['name']}")

        results.append(
            {
                "id": config["id"],
                "name": config["name"],
                "success": success,
                "output": output[:500] if len(output) > 500 else output,
            }
        )

        if success:
            passed += 1
        else:
            failed += 1

    return {
        "passed": passed,
        "failed": failed,
        "results": results,
    }


def print_summary(report: dict):
    """打印汇总报告"""
    print(f"\n{'=' * 60}")
    print("验证汇总报告")
    print(f"{'=' * 60}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"通过: {report['passed']}")
    print(f"失败: {report['failed']}")
    print(f"{'=' * 60}")

    print("\n详细结果:")
    for r in report["results"]:
        status = "✓" if r["success"] else "✗"
        print(f"  {status} {r['name']}")

    print(f"{'=' * 60}")

    if report["failed"] == 0:
        print("✓ 所有验证通过")
        return True
    else:
        print(f"✗ {report['failed']} 个验证失败")
        return False


def save_to_history(report: dict):
    """保存验证结果到历史记录"""
    if not HAS_HISTORY:
        return

    history = VerificationHistory()

    # 保存每个验证结果
    for r in report["results"]:
        history.save_result(
            verification_type=r["id"],
            result={
                "success": r["success"],
                "name": r["name"],
            },
        )

    # 保存总体结果
    history.save_result(
        verification_type="verify_all",
        result={
            "passed": report["passed"],
            "failed": report["failed"],
            "total": report["passed"] + report["failed"],
        },
        metadata={
            "timestamp": datetime.now().isoformat(),
        },
    )


def show_history():
    """显示验证历史"""
    if not HAS_HISTORY:
        print("[错误] 验证历史模块未加载")
        return

    history = VerificationHistory()
    summary = history.get_summary()

    print("\n验证历史摘要")
    print("=" * 60)

    if not summary:
        print("暂无历史记录")
        return

    for vtype, info in summary.items():
        print(f"\n{vtype}:")
        print(f"  记录数: {info['count']}")
        print(f"  最新时间: {info['latest_time']}")
        print(f"  最新结果: {info['latest_result']}")


def main():
    parser = argparse.ArgumentParser(description="统一验证入口")
    parser.add_argument("--quick", action="store_true", help="快速模式（跳过耗时检查）")
    parser.add_argument("--merge", action="store_true", help="只运行设定合并验证")
    parser.add_argument("--worldview", action="store_true", help="只运行世界观验证")
    parser.add_argument("--structures", action="store_true", help="只运行技法验证")
    parser.add_argument("--vectorstore", action="store_true", help="只运行向量库验证")
    parser.add_argument("--sources", action="store_true", help="只运行案例库验证")
    parser.add_argument("--history", action="store_true", help="显示验证历史")
    parser.add_argument("--no-save", action="store_true", help="不保存到历史记录")

    args = parser.parse_args()

    # 显示历史
    if args.history:
        show_history()
        return

    # 确定要运行的验证
    selected = []
    if args.merge:
        selected.append("merge")
    if args.worldview:
        selected.append("worldview")
    if args.structures:
        selected.append("structures")
    if args.vectorstore:
        selected.append("vectorstore")
    if args.sources:
        selected.append("sources")

    # 如果没有指定，运行全部
    if not selected:
        selected = None

    print("=" * 60)
    print("众生界项目验证系统")
    print("=" * 60)
    print(f"模式: {'快速' if args.quick else '完整'}")
    if selected:
        print(f"验证项: {', '.join(selected)}")
    else:
        print("验证项: 全部")

    # 运行验证
    report = run_all_verifications(quick=args.quick, selected=selected)

    # 打印汇总
    all_passed = print_summary(report)

    # 保存到历史
    if not args.no_save:
        save_to_history(report)

    # 返回状态码
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
