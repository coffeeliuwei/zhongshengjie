"""
tools/check_env.py
众生界 AI 写作系统 —— 学生环境自检工具

用法：
    python tools/check_env.py          # 检查全部
    python tools/check_env.py --quick  # 跳过 Qdrant 连接检查（离线时用）

输出：
    每项检查结果用 ✓ / ✗ 标注
    最后给出汇总：全通 → exit 0，有问题 → exit 1
"""

import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ===================== 辅助函数 =====================

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Windows GBK 终端不支持 Unicode 符号，使用 ASCII 兼容版本
OK_MARK = "[OK]"
FAIL_MARK = "[X]"
WARN_MARK = "[!]"


def ok(msg: str):
    print(f"  {GREEN}{OK_MARK}{RESET}  {msg}")


def fail(msg: str):
    print(f"  {RED}{FAIL_MARK}{RESET}  {msg}")


def warn(msg: str):
    print(f"  {YELLOW}{WARN_MARK}{RESET}  {msg}")


def section(title: str):
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


# ===================== 检查函数 =====================


def check_python_version() -> bool:
    """Python 版本 >= 3.10"""
    v = sys.version_info
    if v >= (3, 10):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
        return True
    else:
        fail(f"Python 版本过低：{v.major}.{v.minor}.{v.micro}（需要 3.10+）")
        return False


def check_config_json() -> bool:
    """config.json 存在且是合法 JSON"""
    config_path = PROJECT_ROOT / "config.json"
    if not config_path.exists():
        fail(f"config.json 不存在：{config_path}")
        print(f"       → 执行：copy config.example.json config.json 并填写配置")
        return False
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        world = cfg.get("worldview", {}).get("current_world", "（未设置）")
        ok(f"config.json 合法  当前世界观：{world}")
        return True
    except json.JSONDecodeError as e:
        fail(f"config.json 格式错误：{e}")
        return False


def check_dirs() -> bool:
    """检查各关键目录是否存在"""
    try:
        from core.config_loader import (
            get_settings_dir,
            get_techniques_dir,
            get_logs_dir,
            get_cache_dir,
            get_temp_dir,
            get_contracts_dir,
            get_case_library_dir,
            get_world_configs_dir,
            get_config,
            ensure_all_dirs,
        )
    except ImportError as e:
        fail(f"无法导入 config_loader：{e}")
        return False

    # 先尝试自动创建
    try:
        ensure_all_dirs()
    except Exception as e:
        warn(f"ensure_all_dirs() 出错（已跳过）：{e}")

    cfg = get_config()
    output_dir = Path(cfg.get("extractor", {}).get("output_dir", r"E:\novel_extracted"))

    checks = [
        ("设定目录", get_settings_dir()),
        ("技法目录", get_techniques_dir()),
        ("日志目录", get_logs_dir()),
        ("缓存目录", get_cache_dir()),
        ("契约目录", get_contracts_dir()),
        ("案例库目录", get_case_library_dir()),
        ("世界观配置目录", get_world_configs_dir()),
        ("提炼输出目录", output_dir),
    ]

    all_ok = True
    for name, path in checks:
        if path.exists():
            ok(f"{name}：{path}")
        else:
            fail(f"{name} 不存在：{path}")
            all_ok = False

    return all_ok


def check_packages() -> bool:
    """检查关键 Python 包"""
    packages = [
        ("qdrant_client", "qdrant-client", True),  # (import名, pip名, 必须)
        ("FlagEmbedding", "FlagEmbedding", True),
        ("sentence_transformers", "sentence-transformers", False),
        ("ebooklib", "ebooklib", False),
        ("mobi", "mobi", False),
        ("pdfminer", "pdfminer.six", False),
        ("docx", "python-docx", False),
        ("pytest", "pytest", True),
    ]

    all_required_ok = True
    for import_name, pip_name, required in packages:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "?")
            ok(f"{pip_name} {version}")
        except ImportError:
            if required:
                fail(f"{pip_name} 未安装  → pip install {pip_name}")
                all_required_ok = False
            else:
                warn(f"{pip_name} 未安装（可选）→ pip install {pip_name}")

    return all_required_ok


def check_gpu() -> bool:
    """检查 GPU / CUDA 状态，始终返回 True（无 GPU 是正常情况，不阻断使用）"""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory // (1024 ** 3)
            ok(f"GPU 可用：{name}（{vram}GB VRAM）— 推理将自动使用 CUDA 加速")
        else:
            ver = torch.__version__
            if "+cpu" in ver:
                warn(
                    f"torch {ver} 是 CPU 版，推理速度较慢\n"
                    f"       → 如需加速，执行：\n"
                    f"         pip install torch --index-url https://download.pytorch.org/whl/cu128 --upgrade"
                )
            else:
                warn(f"torch {ver} 已安装，但未检测到可用 GPU，将使用 CPU 推理")
    except ImportError:
        warn("torch 未安装，GPU 状态无法检测（FlagEmbedding 安装后会自动附带）")

    return True  # GPU 不是必须项，不影响系统运行


def check_qdrant(quick: bool = False) -> bool:
    """检查 Qdrant 连接"""
    if quick:
        warn("Qdrant 检查已跳过（--quick 模式）")
        return True

    try:
        from qdrant_client import QdrantClient
        from core.config_loader import get_config

        cfg = get_config()
        url = cfg.get("database", {}).get("qdrant_url", "http://localhost:6333")
        client = QdrantClient(url=url, timeout=5)
        collections = client.get_collections().collections
        ok(f"Qdrant 连接正常（{url}），collections 数：{len(collections)}")
        return True
    except ImportError:
        fail("qdrant-client 未安装，无法检查 Qdrant")
        return False
    except Exception as e:
        fail(f"Qdrant 连接失败：{e}")
        print(
            f"       → 确认 Docker Desktop 运行中，并执行：docker ps --filter name=qdrant"
        )
        return False


def check_config_loader_importable() -> bool:
    """核心模块是否可导入"""
    try:
        from core.config_loader import get_config, get_project_root

        root = get_project_root()
        ok(f"core.config_loader 导入正常  项目根目录：{root}")
        return True
    except Exception as e:
        fail(f"core.config_loader 导入失败：{e}")
        return False


# ===================== 主函数 =====================


def main():
    parser = argparse.ArgumentParser(description="众生界环境检查工具")
    parser.add_argument("--quick", action="store_true", help="跳过 Qdrant 连接检查")
    args = parser.parse_args()

    print("=" * 50)
    print("  众生界 AI 写作系统 —— 环境自检")
    print("=" * 50)

    results = {}

    section("1. Python 版本")
    results["python"] = check_python_version()

    section("2. 核心模块")
    results["core"] = check_config_loader_importable()

    section("3. config.json")
    results["config"] = check_config_json()

    section("4. 目录检查")
    results["dirs"] = check_dirs()

    section("5. Python 包")
    results["packages"] = check_packages()

    section("6. GPU / 推理加速")
    results["gpu"] = check_gpu()

    section("7. Qdrant 连接")
    results["qdrant"] = check_qdrant(quick=args.quick)

    # ---- 汇总 ----
    print(f"\n{'=' * 50}")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    if failed == 0:
        print(f"  {GREEN}环境检查全部通过（{passed}/{total}）{OK_MARK}{RESET}")
        print(f"  可以开始使用众生界 AI 写作系统。")
        sys.exit(0)
    else:
        print(f"  {RED}有 {failed} 项检查未通过（{passed}/{total} 通过）{RESET}")
        print(f"  请根据上方提示逐项修复，修复后重新运行此脚本。")
        sys.exit(1)


if __name__ == "__main__":
    main()
