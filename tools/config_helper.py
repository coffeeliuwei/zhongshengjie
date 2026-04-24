#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置助手
========

帮助新用户快速创建配置文件，自动检测系统路径。

用法：
    python tools/config_helper.py              # 交互式创建配置
    python tools/config_helper.py --detect     # 自动检测路径
    python tools/config_helper.py --show       # 显示当前配置
"""

import os
import json
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any


def detect_project_root() -> Path:
    """自动检测项目根目录"""
    current = Path(__file__).resolve()

    # 从当前文件向上查找标记文件
    markers = ["README.md", "config.example.json", "tools", "core"]

    for parent in current.parents:
        if (parent / "tools").exists() and (parent / "core").exists():
            return parent

    return Path.cwd()


def detect_huggingface_cache() -> Optional[Path]:
    """检测 HuggingFace 缓存目录"""
    # 常见位置
    common_paths = []

    if platform.system() == "Windows":
        # Windows 常见位置
        common_paths = [
            Path("E:/huggingface_cache"),
            Path("D:/huggingface_cache"),
            Path.home() / ".cache" / "huggingface",
        ]
    else:
        # Linux/macOS
        common_paths = [
            Path.home() / ".cache" / "huggingface",
            Path("/data/huggingface_cache"),
        ]

    # 检查环境变量
    hf_home = os.environ.get("HF_HOME") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if hf_home:
        common_paths.insert(0, Path(hf_home))

    # 返回第一个存在的路径
    for path in common_paths:
        if path.exists():
            return path

    return None


def find_bge_m3_model(cache_dir: Optional[Path] = None) -> Optional[str]:
    """查找 BGE-M3 模型路径"""
    if cache_dir is None:
        cache_dir = detect_huggingface_cache()

    if cache_dir is None:
        return None

    # 查找模型目录
    model_dir = cache_dir / "hub" / "models--BAAI--bge-m3"

    if not model_dir.exists():
        return None

    # 查找 snapshots
    snapshots_dir = model_dir / "snapshots"
    if snapshots_dir.exists():
        snapshots = sorted(
            snapshots_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
        )
        if snapshots:
            return str(snapshots[0])

    return None


def detect_novel_sources() -> List[str]:
    """检测可能的小说资源目录"""
    common_paths = []

    if platform.system() == "Windows":
        common_paths = [
            "E:/小说资源",
            "D:/小说资源",
            "C:/小说资源",
        ]
    else:
        common_paths = [
            "/data/novels",
            str(Path.home() / "novels"),
        ]

    found = []
    for path_str in common_paths:
        path = Path(path_str)
        if path.exists():
            found.append(str(path))

    return found


def create_config(
    project_root: Path,
    model_path: Optional[str] = None,
    novel_sources: List[str] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """创建配置字典"""

    config = {
        "project": {
            "name": "My Novel",
            "version": "1.0.0",
        },
        "paths": {
            "project_root": str(project_root),
            "settings_dir": "设定",
            "techniques_dir": "创作技法",
            "chapters_dir": "章节大纲",
            "content_dir": "正文",
            "experience_dir": "章节经验日志",
            "standards_dir": "写作标准积累",
            "vectorstore_dir": ".vectorstore",
            "case_library_dir": ".case-library",
            "logs_dir": "logs",
            "cache_dir": ".cache",
        },
        "database": {
            "qdrant_host": "localhost",
            "qdrant_port": 6333,
            "collections": {
                "novel_settings": "novel_settings_v2",
                "writing_techniques": "writing_techniques_v2",
                "case_library": "case_library_v2",
            },
        },
        "model": {
            "embedding_model": "BAAI/bge-m3",
            "model_path": model_path,
            "vector_size": 1024,
        },
        "novel_sources": novel_sources or [],
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    return config


def interactive_setup():
    """交互式配置"""
    print("=" * 60)
    print("小说创作系统 - 配置助手")
    print("=" * 60)

    # 检测项目根目录
    project_root = detect_project_root()
    print(f"\n[1] 项目根目录")
    print(f"    自动检测: {project_root}")

    use_detected = input("    使用此路径? [Y/n]: ").strip().lower()
    if use_detected == "n":
        custom_path = input("    请输入项目根目录: ").strip()
        project_root = Path(custom_path)

    # 检测模型路径
    print(f"\n[2] BGE-M3 模型路径")
    model_path = find_bge_m3_model()
    if model_path:
        print(f"    自动检测: {model_path}")
        use_detected = input("    使用此路径? [Y/n]: ").strip().lower()
        if use_detected == "n":
            model_path = input("    请输入模型路径 (留空自动下载): ").strip() or None
    else:
        print("    未检测到本地模型，将自动下载")
        model_path = input("    或输入模型路径 (留空自动下载): ").strip() or None

    # 检测小说资源
    print(f"\n[3] 小说资源目录 (用于案例提取)")
    novel_sources = detect_novel_sources()
    if novel_sources:
        print(f"    自动检测:")
        for src in novel_sources:
            print(f"      - {src}")

        use_detected = input("    使用这些目录? [Y/n]: ").strip().lower()
        if use_detected == "n":
            custom = input("    请输入目录 (多个用逗号分隔): ").strip()
            novel_sources = [p.strip() for p in custom.split(",") if p.strip()]
    else:
        print("    未检测到小说资源目录")
        custom = input("    请输入目录 (多个用逗号分隔，留空跳过): ").strip()
        novel_sources = [p.strip() for p in custom.split(",") if p.strip()]

    # 创建配置
    config_path = project_root / "config.json"
    print(f"\n[4] 创建配置文件")
    print(f"    路径: {config_path}")

    create_config(
        project_root=project_root,
        model_path=model_path,
        novel_sources=novel_sources,
        output_path=config_path,
    )

    print("\n" + "=" * 60)
    print("配置完成!")
    print("=" * 60)
    print(f"配置文件: {config_path}")
    print("\n下一步:")
    print("  1. 检查配置文件内容")
    print("  2. 运行: python tools/build_all.py")


def show_config():
    """显示当前配置"""
    project_root = detect_project_root()
    config_path = project_root / "config.json"

    print("=" * 60)
    print("当前配置")
    print("=" * 60)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        print(f"\n配置文件: {config_path}")
        print(f"\n[路径配置]")
        paths = config.get("paths", {})
        print(f"  项目根目录: {paths.get('project_root', '未配置')}")
        print(f"  设定目录: {paths.get('settings_dir', '设定')}")
        print(f"  技法目录: {paths.get('techniques_dir', '创作技法')}")

        print(f"\n[模型配置]")
        model = config.get("model", {})
        print(f"  模型: {model.get('embedding_model', 'BAAI/bge-m3')}")
        print(f"  本地路径: {model.get('model_path') or '自动下载'}")

        print(f"\n[小说资源]")
        sources = config.get("novel_sources", [])
        if sources:
            for src in sources:
                print(f"  - {src}")
        else:
            print("  (未配置)")

        print(f"\n[数据库配置]")
        db = config.get("database", {})
        print(
            f"  Qdrant: {db.get('qdrant_host', 'localhost')}:{db.get('qdrant_port', 6333)}"
        )
    else:
        print(f"\n配置文件不存在: {config_path}")
        print("运行以下命令创建配置:")
        print("  python tools/config_helper.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="配置助手")
    parser.add_argument("--detect", action="store_true", help="自动检测并显示路径")
    parser.add_argument("--show", action="store_true", help="显示当前配置")

    args = parser.parse_args()

    if args.show:
        show_config()
    elif args.detect:
        print("=" * 60)
        print("自动检测结果")
        print("=" * 60)
        print(f"\n项目根目录: {detect_project_root()}")
        print(f"HuggingFace缓存: {detect_huggingface_cache() or '未检测到'}")
        print(f"BGE-M3模型: {find_bge_m3_model() or '未检测到，将自动下载'}")
        print(f"\n小说资源目录:")
        for src in detect_novel_sources():
            print(f"  - {src}")
    else:
        interactive_setup()


if __name__ == "__main__":
    main()
