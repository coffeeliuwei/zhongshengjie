"""
发布脚本 - master → release-closed 分支自动化
M6 里程碑产物

用法:
    python release.py --dry-run    # 仅打印操作步骤（不执行）
    python release.py --prepare    # 准备编译产物
    python release.py --create     # 创建 release-closed 分支（dry-run）
    python release.py --full       # 完整流程（dry-run）

约束:
    - 不在 master 分支执行 git 操作
    - release-closed 分支操作仅 dry-run
    - 用户需手动执行 git checkout/push

流程:
    1. 确认当前在 master 分支
    2. 编译 core/ 目录
    3. 创建 release-closed 分支（或切换到已有分支）
    4. 删除 core/ 下的 .py 文件（保留 __init__.py）
    5. 保留 .pyd 编译产物
    6. 提交变更

注意: 所有 git 操作都是 dry-run，用户需手动执行
"""

import subprocess
import sys
import shutil
from pathlib import Path
from argparse import ArgumentParser

def get_current_branch():
    """获取当前 Git 分支"""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

def get_compile_files():
    """获取需要编译的文件列表"""
    core_dir = Path("core")
    py_files = list(core_dir.rglob("*.py"))
    init_files = list(core_dir.rglob("__init__.py"))
    return [f for f in py_files if f not in init_files]

def get_init_files():
    """获取 __init__.py 文件列表"""
    core_dir = Path("core")
    return list(core_dir.rglob("__init__.py"))

def prepare():
    """准备编译产物"""
    print("[PREPARE] 准备编译产物...")

    # 编译
    result = subprocess.run(
        [sys.executable, "build.py"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"[ERROR] 编译失败")
        print(result.stderr)
        sys.exit(1)

    print("[OK] 编译完成")
    return True

def create_branch_dry_run():
    """创建 release-closed 分支（dry-run）"""
    branch = get_current_branch()
    print(f"[BRANCH] 当前分支: {branch}")

    if branch != "master":
        print("[WARN] 必须在 master 分支执行")
        return False

    print("\n[DRY-RUN] 创建 release-closed 分支步骤:")
    print("  1. git checkout -b release-closed")
    print("     或 git checkout release-closed（如果已存在）")
    print("  2. 删除 core/ 下的 .py 文件（保留 __init__.py）")
    print("  3. git add -A")
    print("  4. git commit -m 'Release closed-source version'")
    print("  5. git push -u origin release-closed")

    compile_files = get_compile_files()
    init_files = get_init_files()

    print(f"\n将删除的文件: {len(compile_files)} 个")
    print(f"将保留的文件: {len(init_files)} 个 __init__.py")

    print("\n[WARN] 未实际执行 git 操作（dry-run 模式）")
    return True

def full_dry_run():
    """完整流程 dry-run"""
    print("=" * 60)
    print("[RELEASE] Release Closed-Source - Dry-Run Mode")
    print("=" * 60)

    # Step 1: 检查分支
    branch = get_current_branch()
    print(f"\n[STEP-1] 当前分支 = {branch}")

    if branch != "master":
        print("[ERROR] 必须在 master 分支开始")
        return False

    # Step 2: 编译（可选）
    print("\n[STEP-2] 编译（可选，可跳过）")
    print("  命令: python build.py")
    print("  产物: core/**/*.pyd + core/**/*.c")

    # Step 3: Git 操作（dry-run）
    print("\n[STEP-3] Git 操作（dry-run）")
    print("  $ git checkout -b release-closed")
    print("  或")
    print("  $ git checkout release-closed")

    compile_files = get_compile_files()
    init_files = get_init_files()

    print(f"\n  删除 {len(compile_files)} 个 .py 文件:")
    for f in sorted(compile_files)[:5]:
        print(f"    rm {f}")
    print(f"    ... 共 {len(compile_files)} 个")

    print(f"\n  保留 {len(init_files)} 个 __init__.py:")
    for f in sorted(init_files):
        print(f"    [KEEP] {f}")

    print("\n  $ git add -A")
    print("  $ git commit -m 'Release v14.0 closed-source'")
    print("  $ git push -u origin release-closed")

    print("\n" + "=" * 60)
    print("[WARN] 所有操作都是 dry-run，请手动执行")
    print("=" * 60)

    return True

def main():
    parser = ArgumentParser(description="发布脚本")
    parser.add_argument("--dry-run", action="store_true", help="完整流程 dry-run")
    parser.add_argument("--prepare", action="store_true", help="准备编译产物")
    parser.add_argument("--create", action="store_true", help="创建分支 dry-run")
    parser.add_argument("--full", action="store_true", help="完整流程 dry-run")

    args = parser.parse_args()

    if args.prepare:
        prepare()
    elif args.create:
        create_branch_dry_run()
    elif args.dry_run or args.full:
        full_dry_run()
    else:
        # 默认显示 dry-run
        full_dry_run()

if __name__ == "__main__":
    main()