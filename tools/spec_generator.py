"""
项目目录树后序遍历 + Spec生成器

用法：
    python spec_generator.py [项目路径] [--output spec.md]

示例：
    python spec_generator.py D:\动画\众生界
    python spec_generator.py D:\动画\众生界 --output SPEC.md
"""

import os
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# 跳过的目录
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".case-library",
    "qdrant_docker",
    "__pycache__",
    ".obsidian",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
}

# 文件类型识别
FILE_TYPES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".md": "Markdown",
    ".txt": "Text",
    ".csv": "CSV",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
    ".toml": "TOML",
    ".ini": "INI",
    ".cfg": "Config",
}


def get_file_type(ext):
    return FILE_TYPES.get(ext.lower(), "Other")


def analyze_file(filepath, max_lines=50):
    """分析单个文件，提取关键信息"""
    try:
        ext = Path(filepath).suffix.lower()

        if ext in {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".ico",
            ".bin",
            ".pkl",
            ".pt",
            ".bin",
        }:
            return {"type": "binary", "size": os.path.getsize(filepath)}

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                lines.append(line)

        content = "".join(lines)

        result = {
            "type": get_file_type(ext),
            "lines": len(lines),
            "functions": [],
            "classes": [],
            "imports": [],
        }

        # Python文件分析
        if ext == ".py":
            import re

            result["functions"] = re.findall(r"def\s+(\w+)\s*\(", content)
            result["classes"] = re.findall(r"class\s+(\w+)", content)
            result["imports"] = re.findall(
                r"^(?:import|from)\s+(\S+)", content, re.MULTILINE
            )

        # JSON文件分析
        elif ext == ".json":
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    result["keys"] = list(data.keys())[:10]
                elif isinstance(data, list):
                    result["count"] = len(data)
            except:
                pass

        return result

    except Exception as e:
        return {"error": str(e)}


def postorder_traverse(root_path):
    """后序遍历目录树"""
    root = Path(root_path)

    # 收集所有目录和文件
    all_dirs = []
    all_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # 过滤跳过的目录
        dirnames[:] = [
            d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
        ]

        rel_dir = os.path.relpath(dirpath, root)
        depth = rel_dir.count(os.sep) if rel_dir != "." else 0

        all_dirs.append(
            {"path": dirpath, "rel_path": rel_dir, "depth": depth, "files": filenames}
        )

        for fname in filenames:
            if fname.startswith("."):
                continue
            all_files.append(
                {
                    "path": os.path.join(dirpath, fname),
                    "rel_path": os.path.join(rel_dir, fname)
                    if rel_dir != "."
                    else fname,
                    "depth": depth,
                }
            )

    # 按深度降序排序（后序遍历：深->浅）
    all_dirs.sort(key=lambda x: -x["depth"])
    all_files.sort(key=lambda x: -x["depth"])

    return all_dirs, all_files


def generate_spec(root_path, output_file="spec.md"):
    """生成spec.md"""
    print(f"正在分析: {root_path}")

    dirs, files = postorder_traverse(root_path)

    # 分层统计
    layer_stats = defaultdict(
        lambda: {
            "dirs": [],
            "files": [],
            "file_types": defaultdict(int),
            "total_lines": 0,
        }
    )

    # 分析文件
    file_analyses = {}
    for f in files:
        depth = f["depth"]
        analysis = analyze_file(f["path"])
        file_analyses[f["rel_path"]] = analysis

        layer_stats[depth]["files"].append(f["rel_path"])
        layer_stats[depth]["file_types"][analysis.get("type", "Unknown")] += 1
        layer_stats[depth]["total_lines"] += analysis.get("lines", 0)

    # 目录统计
    for d in dirs:
        layer_stats[d["depth"]]["dirs"].append(d["rel_path"])

    # 生成Markdown
    md_lines = [
        f"# 项目技术规格文档",
        f"",
        f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 项目路径: `{root_path}`",
        f"",
        "---",
        "",
        "## 1. 项目概览",
        "",
        f"- **总目录数**: {len(dirs)}",
        f"- **总文件数**: {len(files)}",
        f"- **最大深度**: {max(layer_stats.keys()) if layer_stats else 0}",
        "",
        "---",
        "",
        "## 2. 目录结构",
        "",
        "```",
    ]

    # 树形结构
    for d in sorted(dirs, key=lambda x: x["depth"]):
        indent = "  " * d["depth"]
        md_lines.append(f"{indent}├── {Path(d['rel_path']).name}/")

    md_lines.extend(
        [
            "```",
            "",
            "---",
            "",
            "## 3. 分层详解",
            "",
        ]
    )

    # 每层详情
    for depth in sorted(layer_stats.keys(), reverse=True):
        stats = layer_stats[depth]
        md_lines.extend(
            [
                f"### 第 {depth} 层",
                "",
                "**目录**:",
            ]
        )
        for d in stats["dirs"][:10]:
            md_lines.append(f"- `{d}`")

        md_lines.extend(
            [
                "",
                "**文件分布**:",
            ]
        )
        for ftype, count in sorted(stats["file_types"].items(), key=lambda x: -x[1]):
            md_lines.append(f"- {ftype}: {count}")

        md_lines.extend(
            [
                "",
                f"**代码行数**: {stats['total_lines']:,}",
                "",
            ]
        )

    # 主要文件分析
    md_lines.extend(
        [
            "---",
            "",
            "## 4. 核心文件",
            "",
        ]
    )

    for fpath, analysis in list(file_analyses.items())[:20]:
        if analysis.get("type") in ["Python", "JavaScript", "TypeScript"]:
            md_lines.append(f"### `{fpath}`")
            md_lines.append("")
            if analysis.get("classes"):
                md_lines.append(f"**类**: {', '.join(analysis['classes'][:5])}")
                md_lines.append("")
            if analysis.get("functions"):
                md_lines.append(f"**函数**: {', '.join(analysis['functions'][:10])}")
                md_lines.append("")
            md_lines.append("---")
            md_lines.append("")

    # 写入文件
    output_path = Path(root_path) / output_file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"✅ 已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="生成项目spec.md")
    parser.add_argument("path", help="项目路径")
    parser.add_argument("--output", "-o", default="spec.md", help="输出文件名")

    args = parser.parse_args()

    if not os.path.isdir(args.path):
        print(f"错误: 路径不存在 - {args.path}")
        sys.exit(1)

    generate_spec(args.path, args.output)
