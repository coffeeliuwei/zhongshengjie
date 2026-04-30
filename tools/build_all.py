#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
众生界统一入库管线
==================

新用户使用此脚本从零构建完整的小说创作系统。

作者：coffeeliuwei
版本：v15.0
日期：2026-04-30

用法：
    python tools/build_all.py                          # 全量入库（断点续跑）
    python tools/build_all.py --status                 # 查看 collection 条数
    python tools/build_all.py --only case,dialogue     # 只跑指定阶段
    python tools/build_all.py --rebuild                # 强制清数据重跑
    python tools/build_all.py --only technique_batch --rebuild

阶段列表：case, extract, technique_batch, dialogue

完整使用流程：
    0. 安装Skills：cp -r skills/* ~/.agents/skills/
    1. 克隆项目：git clone https://github.com/coffeeliuwei/zhongshengjie.git
    2. 安装依赖：pip install -r requirements.txt
    3. 启动Qdrant：docker run -d --name qdrant-server -p 6333:6333
                   -p 6334:6334 -v E:/qdrant_storage:/qdrant/storage
                   -e QDRANT__SERVICE__MAX_REQUEST_SIZE_MB=256 qdrant/qdrant
    4. 配置系统：cp config.example.json config.json（编辑路径）
    5. 构建数据：python tools/build_all.py
    6. 创建大纲：对话 "创建总大纲"
    7. 创建设定：对话 "添加角色设定"
    8. 开始创作：对话 "写第一章"
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.config_loader import get_qdrant_url

QDRANT_URL = get_qdrant_url()

DEFAULT_TECHNIQUE_JSON = "E:/novel_extracted/technique/technique_all.json"

STAGES = [
    {
        "name": "case",
        "label": "案例库构建（case_library_v2）",
        "cmd": [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "tools" / "case_builder.py"),
            "--all",
        ],
        "rebuild_extra": [],
        "log": str(PROJECT_ROOT / "logs" / "case_log.txt"),
    },
    {
        "name": "extract",
        "label": "10维度提炼+入库",
        "cmd": [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "tools" / "batch_extract.py"),
            "--skip-case",
        ],
        "rebuild_extra": [],
        "log": str(PROJECT_ROOT / "logs" / "batch_log.txt"),
    },
    {
        "name": "technique_batch",
        "label": "批量技法入库（writing_techniques_batch_v1）",
        "cmd": [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "modules" / "knowledge_base" / "hybrid_sync_manager.py"),
            "--sync",
            "technique-json",
            "--json-path",
            "{technique_json}",
        ],
        "rebuild_extra": ["--rebuild"],
        "log": str(PROJECT_ROOT / "logs" / "technique_batch_sync.log"),
    },
    {
        "name": "dialogue",
        "label": "对话风格聚合（dialogue_style_v1）",
        "cmd": [
            sys.executable,
            "-u",
            str(PROJECT_ROOT / "tools" / "aggregate_dialogue_style.py"),
        ],
        "rebuild_extra": [],
        "log": str(PROJECT_ROOT / "logs" / "aggregate_dialogue_style.log"),
    },
]

STAGE_ORDER = ["case", "extract", "technique_batch", "dialogue"]


def _build_cmd(stage: dict, rebuild: bool, technique_json: str) -> List[str]:
    """构建阶段的实际命令，替换占位符，按需追加 rebuild_extra"""
    cmd = []
    for arg in stage["cmd"]:
        cmd.append(technique_json if arg == "{technique_json}" else arg)
    if rebuild:
        cmd.extend(stage["rebuild_extra"])
    return cmd


def run_stage(stage: dict, rebuild: bool, technique_json: str) -> bool:
    """运行一个阶段，输出同时打印到终端和写入日志文件"""
    log_path = Path(stage["log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = _build_cmd(stage, rebuild, technique_json)

    print(f"\n{'=' * 60}")
    print(f"[阶段] {stage['label']}")
    print(f"命令: {' '.join(cmd)}")
    print(f"日志: {log_path}")
    print("=" * 60)

    start = datetime.now()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    with open(log_path, "w", encoding="utf-8", errors="replace") as log_file:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        for raw_line in process.stdout:
            text = raw_line.decode("utf-8", errors="replace")
            print(text, end="", flush=True)
            log_file.write(text)
            log_file.flush()
        process.wait()

    elapsed = datetime.now() - start
    minutes = int(elapsed.total_seconds() // 60)
    seconds = int(elapsed.total_seconds() % 60)

    if process.returncode == 0:
        print(f"\n[OK] {stage['label']} 完成，耗时 {minutes}m {seconds}s")
        return True
    else:
        print(f"\n[FAIL] {stage['label']} 失败（返回码 {process.returncode}）")
        print(f"查看日志: {log_path}")
        return False


def show_status(qdrant_url: str = None) -> None:
    """显示各 collection 当前条数"""
    url = qdrant_url or QDRANT_URL
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=url, timeout=10)
        cols = client.get_collections().collections
        print(f"\n{'Collection':<35} {'条数':>10}")
        print("-" * 47)
        for c in sorted(cols, key=lambda x: x.name):
            info = client.get_collection(c.name)
            print(f"{c.name:<35} {info.points_count:>10,}")
    except Exception as e:
        print(f"[错误] 无法连接 Qdrant ({url}): {e}")


def clear_case_data(case_lib_path: Path = None) -> None:
    """--rebuild 时清除 case 阶段索引文件，不删小说源文件"""
    case_lib = case_lib_path or Path("E:/case-library")
    targets = [
        "case_index.json",
        "dedup_index.pkl",
        "convert_failures.txt",
        "convert_quality.tsv",
    ]
    for name in targets:
        p = case_lib / name
        if p.exists():
            p.unlink()
            print(f"    [删除] {name}")
    cases_dir = case_lib / "cases"
    if cases_dir.exists():
        shutil.rmtree(cases_dir)
        cases_dir.mkdir()
        print("    [清空] cases/")


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_step(step, total, message):
    """打印步骤"""
    print(f"\n[{step}/{total}] {message}")


def check_dependencies():
    """检查依赖"""
    print_header("检查依赖")

    missing = []

    # Python版本
    py_version = sys.version_info
    print(f"    Python: {py_version.major}.{py_version.minor}")
    if py_version < (3, 9):
        missing.append("Python 3.9+")

    # 核心包
    packages = [
        ("qdrant_client", "qdrant-client"),
        ("FlagEmbedding", "FlagEmbedding"),
    ]

    for module, package in packages:
        try:
            __import__(module)
            print(f"    ✓ {package}")
        except ImportError:
            print(f"    ✗ {package} (缺失)")
            missing.append(package)

    if missing:
        print(f"\n缺失依赖: {missing}")
        print("请运行: pip install " + " ".join(missing))
        return False

    return True


def check_docker():
    """检查Docker"""
    import subprocess

    print_header("检查Docker")

    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("    ✓ Docker运行中")

            # 检查Qdrant
            import urllib.request

            try:
                with urllib.request.urlopen(
                    f"{QDRANT_URL}/collections", timeout=5
                ) as response:
                    if response.status == 200:
                        print("    ✓ Qdrant运行中")
                        return True
            except:
                print("    ✗ Qdrant未运行")
                print(
                    "    启动命令: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant"
                )
                return False
        else:
            print("    ✗ Docker未运行")
            return False

    except FileNotFoundError:
        print("    ✗ Docker未安装")
        print("    下载: https://www.docker.com/products/docker-desktop")
        return False
    except Exception as e:
        print(f"    ✗ Docker检查失败: {e}")
        return False


def init_project(project_dir: Path, novel_name: str):
    """初始化项目"""
    print_step(1, 5, "初始化项目结构")

    # 创建目录
    directories = {
        "正文": "已发布章节",
        "章节大纲": "章节规划",
        "设定": "世界观/人物设定",
        "创作技法": "技法库",
        "章节经验日志": "经验沉淀",
        "写作标准积累": "用户修改要求",
        ".vectorstore": "向量数据库",
        ".case-library": "案例库",
        "logs": "日志",
        ".cache": "缓存",
        "core": "核心模块",
        "modules": "功能模块",
        "tools": "工具脚本",
        "tests": "测试",
        "docs": "文档",
    }

    for name, desc in directories.items():
        dir_path = project_dir / name
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"    ✓ {name}/ - {desc}")

    # 复制工具脚本（如果从模板项目构建）
    # 这里假设工具脚本已经存在

    return True


def build_techniques(techniques_dir: Path, quick: bool = False):
    """构建技法库"""
    print_step(2, 5, "构建技法库")

    if quick:
        print("    [快速模式] 跳过技法同步")
        return True

    try:
        from tools.technique_builder import TechniqueBuilder

        builder = TechniqueBuilder(techniques_dir)

        # 初始化目录
        builder.init_structure()

        # 同步到向量库
        print("\n    同步到向量库...")
        builder.sync_to_vectorstore()

        return True
    except Exception as e:
        print(f"    ✗ 构建失败: {e}")
        return False


def build_knowledge(settings_dir: Path, quick: bool = False):
    """构建知识库"""
    print_step(3, 5, "构建知识库")

    if quick:
        print("    [快速模式] 跳过知识同步")
        return True

    try:
        from tools.knowledge_builder import KnowledgeBuilder

        builder = KnowledgeBuilder(settings_dir)

        # 初始化目录
        builder.init_structure()

        # 构建知识图谱
        print("\n    构建知识图谱...")
        builder.build_knowledge_graph()

        # 同步到向量库
        print("\n    同步到向量库...")
        builder.sync_to_vectorstore()

        return True
    except Exception as e:
        print(f"    ✗ 构建失败: {e}")
        return False


def build_cases(case_library_dir: Path, skip: bool = False, quick: bool = False):
    """构建案例库"""
    print_step(4, 6, "构建案例库")

    if skip or quick:
        print("    [跳过] 案例库构建")
        return True

    try:
        from tools.case_builder import CaseBuilder

        builder = CaseBuilder(case_library_dir)

        # 初始化目录
        builder.init_structure()

        print("\n    案例库已初始化")
        print("    如需提取案例，请运行:")
        print("      python case_builder.py --scan <小说资源目录>")
        print("      python case_builder.py --convert")
        print("      python case_builder.py --extract --limit 1000")
        print("      python case_builder.py --sync")

        return True
    except Exception as e:
        print(f"    ✗ 构建失败: {e}")
        return False


def build_scene_mapping(vectorstore_dir: Path, quick: bool = False):
    """构建场景映射"""
    print_step(5, 6, "构建场景映射")

    if quick:
        print("    [快速模式] 跳过场景映射")
        return True

    try:
        from tools.scene_mapping_builder import SceneMappingBuilder

        builder = SceneMappingBuilder(vectorstore_dir)

        # 初始化映射
        builder.init_mapping()

        return True
    except Exception as e:
        print(f"    ✗ 构建失败: {e}")
        return False


def verify_system(project_dir: Path):
    """验证系统"""
    print_step(6, 6, "验证系统")

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=QDRANT_URL)

        collections = {
            "writing_techniques_v2": "技法库",
            "novel_settings_v2": "知识库",
            "case_library_v2": "案例库",
        }

        print("\n    [向量库状态]")
        all_ok = True

        for col_name, display_name in collections.items():
            try:
                info = client.get_collection(col_name)
                count = info.points_count
                print(f"        {display_name}: {count:,} 条")
            except:
                print(f"        {display_name}: 未创建")
                all_ok = False

        # 检查目录
        print("\n    [目录状态]")
        dirs_to_check = {
            "技法库": project_dir / "创作技法",
            "知识库": project_dir / "设定",
            "案例库": project_dir / ".case-library",
        }

        for name, path in dirs_to_check.items():
            if path.exists():
                file_count = len(list(path.rglob("*.md"))) + len(
                    list(path.rglob("*.txt"))
                )
                print(f"        {name}: {file_count} 文件")
            else:
                print(f"        {name}: 不存在")

        return all_ok

    except Exception as e:
        print(f"    ✗ 验证失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="一键构建小说创作系统")
    parser.add_argument("--project-dir", default=".", help="项目目录")
    parser.add_argument("--novel-name", default="我的小说", help="小说名称")
    parser.add_argument("--skip-cases", action="store_true", help="跳过案例库构建")
    parser.add_argument("--quick", action="store_true", help="快速模式（仅初始化目录）")
    parser.add_argument("--skip-deps", action="store_true", help="跳过依赖检查")

    args = parser.parse_args()

    print_header("一键构建小说创作系统")
    print(f"    项目目录: {args.project_dir}")
    print(f"    小说名称: {args.novel_name}")
    print(f"    快速模式: {'是' if args.quick else '否'}")

    project_dir = Path(args.project_dir)

    # 检查依赖
    if not args.skip_deps:
        if not check_dependencies():
            print("\n请先安装缺失的依赖")
            return

        if not check_docker():
            print("\n请先启动Docker和Qdrant")
            return

    # 构建
    results = []

    # 1. 初始化项目
    results.append(init_project(project_dir, args.novel_name))

    # 2. 构建技法库
    results.append(build_techniques(project_dir / "创作技法", args.quick))

    # 3. 构建知识库
    results.append(build_knowledge(project_dir / "设定", args.quick))

    # 4. 构建案例库
    results.append(
        build_cases(project_dir / ".case-library", args.skip_cases, args.quick)
    )

    # 5. 验证系统
    results.append(verify_system(project_dir))

    # 总结
    print_header("构建完成")

    if all(results):
        print("    ✓ 所有步骤完成")
        print("\n完整使用流程：")
        print("    步骤0: 安装Skills（已完成）")
        print("    步骤1-5: 构建数据系统（已完成）")
        print("\n下一步（对话方式）：")
        print('    6. 创建总大纲 → 对话 "创建总大纲"')
        print('    7. 添加角色设定 → 对话 "添加角色：XXX，性格：XXX"')
        print('    8. 添加势力设定 → 对话 "添加势力：XXX，类型：宗门"')
        print('    9. 开始创作 → 对话 "写第一章"')
        print("\n或使用工具命令：")
        print("    python tools/unified_extractor.py  # 提炼外部小说库")
        print("    python tools/unified_extractor.py --status  # 查看状态")
    else:
        print("    ⚠ 部分步骤未完成")
        print("    请检查上方输出中的错误信息")


if __name__ == "__main__":
    main()
