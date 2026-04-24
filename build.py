"""
Cython 编译驱动脚本
M6 里程碑产物

用法:
    python build.py           # 编译 core/ 目录
    python build.py --clean   # 清理编译产物
    python build.py --status  # 查看编译状态
    python build.py --dry-run # 仅打印将编译的文件

约束:
    - 不在 master 分支留下 .pyd/.c/build/
    - 编译产物仅用于 release-closed 分支
    - dry-run 模式不实际编译
"""

import subprocess
import sys
import shutil
from pathlib import Path
from argparse import ArgumentParser

def get_compile_files():
    """
    获取需要编译的文件列表
    [N12 2026-04-18] 排除 __init__.py 和 __main__.py（保持与 setup.py 一致）
    """
    core_dir = Path("core")
    py_files = list(core_dir.rglob("*.py"))
    excluded = {"__init__.py", "__main__.py"}
    return [f for f in py_files if f.name not in excluded]

def get_compiled_files():
    """获取已编译的产物列表"""
    core_dir = Path("core")
    pyd_files = list(core_dir.rglob("*.pyd"))
    c_files = list(core_dir.rglob("*.c"))
    return pyd_files, c_files

def clean():
    """清理编译产物"""
    print("[CLEAN] 清理编译产物...")

    pyd_files, c_files = get_compiled_files()

    # 删除 .pyd 文件
    for f in pyd_files:
        f.unlink()
        print(f"  删除: {f}")

    # 删除 .c 文件
    for f in c_files:
        f.unlink()
        print(f"  删除: {f}")

    # 删除 build/ 目录
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
        print(f"  删除: {build_dir}/")

    print("[OK] 清理完成")

def status():
    """显示编译状态"""
    compile_files = get_compile_files()
    pyd_files, c_files = get_compiled_files()

    print(f"[STATUS] 编译状态:")
    print(f"  待编译文件: {len(compile_files)}")
    print(f"  已编译 .pyd: {len(pyd_files)}")
    print(f"  已生成 .c: {len(c_files)}")

    if pyd_files:
        print(f"\n已编译模块:")
        for f in sorted(pyd_files):
            print(f"  [OK] {f}")

    if len(pyd_files) != len(compile_files):
        missing = len(compile_files) - len(pyd_files)
        print(f"\n[WARN] 未编译: {missing} 个文件")

def dry_run():
    """dry-run 模式 - 仅打印将编译的文件"""
    compile_files = get_compile_files()
    print(f"[DRY-RUN] 将编译 {len(compile_files)} 个文件")
    for f in sorted(compile_files):
        print(f"  {f}")
    print("\n[WARN] 未实际编译（dry-run 模式）")

def check_msvc():
    """
    [N12 2026-04-18] 检测 MSVC 环境是否激活
    Windows 编译 .pyd 必须先 call vcvarsall.bat x64
    没激活时 distutils 会报 "Microsoft Visual C++ 14.0 or greater is required"
    """
    if sys.platform != "win32":
        return  # 非 Windows 跳过
    # 简单检测：环境变量 INCLUDE 含 MSVC 路径标志
    import os
    include = os.environ.get("INCLUDE", "")
    if "MSVC" not in include and "Visual Studio" not in include:
        print("[ERROR] MSVC 环境未激活")
        print("        请先在 Developer Command Prompt 中跑，或手动:")
        print('        cmd /c \'call "<VS路径>\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64 && python build.py\'')
        print("        典型 VS 路径示例:")
        print('          E:\\Microsoft Visual Studio\\18\\BuildTools')
        print('          C:\\Program Files\\Microsoft Visual Studio\\2022\\Community')
        sys.exit(2)


def build():
    """执行 Cython 编译"""
    check_msvc()  # [N12] 编译前检测 MSVC

    compile_files = get_compile_files()
    print(f"[BUILD] 开始编译 {len(compile_files)} 个文件...")

    # 执行 setup.py
    result = subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"[ERROR] 编译失败:")
        print(result.stderr)
        sys.exit(1)

    # 统计结果
    pyd_files, c_files = get_compiled_files()
    print(f"[OK] 编译完成:")
    print(f"  生成 .pyd: {len(pyd_files)}")
    print(f"  生成 .c: {len(c_files)}")

    # 验证所有文件都已编译
    if len(pyd_files) != len(compile_files):
        missing = len(compile_files) - len(pyd_files)
        print(f"[WARN] 有 {missing} 个文件未成功编译")
        return False

    return True

def main():
    parser = ArgumentParser(description="Cython 编译驱动")
    parser.add_argument("--clean", action="store_true", help="清理编译产物")
    parser.add_argument("--status", action="store_true", help="查看编译状态")
    parser.add_argument("--dry-run", action="store_true", help="仅打印将编译的文件")

    args = parser.parse_args()

    if args.clean:
        clean()
    elif args.status:
        status()
    elif args.dry_run:
        dry_run()
    else:
        success = build()
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()