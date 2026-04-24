"""
Cython 编译配置 - 用于闭源分发
M6 里程碑产物

用法:
    python setup.py build_ext --inplace  # 本地编译测试
    python build.py                       # 使用 build.py 驱动编译

注意:
    - 不编译 __init__.py（子包导入需要）
    - 不编译 modules/、scripts/、tools/、tests/
    - 编译产物: .pyd (Windows) / .so (Linux/Mac)
"""

from setuptools import setup, Extension
from Cython.Build import cythonize
from pathlib import Path
import os

def get_core_extensions():
    """
    收集 core/ 目录下需要编译的 Python 文件
    排除所有 __init__.py 和 __main__.py（python -m core 入口必须保留 .py 源）
    """
    core_dir = Path("core")
    extensions = []

    for py_file in core_dir.rglob("*.py"):
        # 排除 __init__.py（Cython 编译会破坏包识别）
        if py_file.name == "__init__.py":
            continue
        # 排除 __main__.py（python -m core 机制要求 .py 源，
        # 编成 .pyd 后报 "No code object available for core.__main__"）
        # [N12 2026-04-18] Claude 真编译验证发现：__main__.pyd 会让 CLI 崩
        if py_file.name == "__main__.py":
            continue

        # 转换路径格式
        module_path = str(py_file).replace("/", ".").replace("\\", ".").replace(".py", "")

        extensions.append(
            Extension(
                name=module_path,
                sources=[str(py_file)],
                # [N12 2026-04-18] 删除 extra_compile_args=["-O2"]：
                # MSVC 不识别该 GCC 风格参数（沉默失败），跨平台编译反而引入混淆。
                # MSVC 默认已开启合理优化级别，无需手工指定。
            )
        )

    return extensions

# 编译配置
ext_modules = cythonize(
    get_core_extensions(),
    compiler_directives={
        "language_level": "3",
        # [N12 2026-04-18] boundscheck/wraparound 改回 Cython 默认 True：
        # 1. core/ 7 处使用负索引（lst[-1] 等），wraparound=False 时未定义行为
        # 2. 本项目非性能瓶颈，安全优先；性能差异 <1%
        "boundscheck": True,
        "wraparound": True,
        "binding": True,         # 保留函数签名 introspection（方便调试）
        "embedsignature": True,  # docstring 含签名（IDE 提示友好）
    },
    exclude=["**/__init__.py", "**/__main__.py"],  # 双重保险
    nthreads=4,                  # 并行编译加速
)

setup(
    name="zhongshengjie-core",
    version="14.0.0",
    description="众生界核心模块（闭源编译版）",
    author="coffeeliuwei",
    ext_modules=ext_modules,
    zip_safe=False,
)