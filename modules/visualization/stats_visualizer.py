#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统计可视化模块
提供项目数据的统计分析和可视化功能

功能:
    - 知识图谱统计 (实体/关系分布)
    - 技法库统计 (维度/作家分布)
    - 数据质量统计
    - 使用情况统计
    - 支持多种输出格式 (JSON、HTML、PNG)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import Counter


# ============================================================
# 统计可视化类
# ============================================================


class StatsVisualizer:
    """统计可视化器

    支持功能:
        - 知识图谱统计
        - 技法库统计
        - 数据库统计
        - 生成可视化报告
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or Path.cwd()
        self.vectorstore_dir = self.project_root / ".vectorstore"

    def get_knowledge_graph_stats(self) -> Dict:
        """
        获取知识图谱统计

        Returns:
            统计数据
        """
        stats = {
            "实体": {"总数": 0, "类型分布": {}},
            "关系": {"总数": 0, "类型分布": {}},
            "数据源": [],
        }

        # 从 JSON 文件读取
        graph_file = self.vectorstore_dir / "knowledge_graph.json"
        if graph_file.exists():
            with open(graph_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 实体统计
            entities = data.get("实体", {})
            stats["实体"]["总数"] = len(entities)

            for entity_id, entity_data in entities.items():
                entity_type = entity_data.get("类型", "未知")
                stats["实体"]["类型分布"][entity_type] = (
                    stats["实体"]["类型分布"].get(entity_type, 0) + 1
                )

            # 关系统计
            relations = data.get("关系", [])
            stats["关系"]["总数"] = len(relations)

            for rel in relations:
                rel_type = rel.get("关系类型", "未知")
                stats["关系"]["类型分布"][rel_type] = (
                    stats["关系"]["类型分布"].get(rel_type, 0) + 1
                )

            # 数据源
            stats["数据源"].append("knowledge_graph.json")

        return stats

    def get_technique_stats(self) -> Dict:
        """
        获取技法库统计

        Returns:
            统计数据
        """
        stats = {
            "总数": 0,
            "核心维度": {},
            "非核心维度": {},
            "作家分布": {},
            "数据源": [],
        }

        # 核心维度
        CORE_DIMENSIONS = [
            "世界观",
            "剧情",
            "人物",
            "战斗",
            "氛围",
            "叙事",
            "主题",
            "情感",
            "读者体验",
            "元维度",
            "节奏",
        ]

        # 从 JSON 文件读取技法统计
        # 如果有技法数据文件
        technique_files = list(self.vectorstore_dir.glob("technique_*.json"))

        for file in technique_files:
            stats["数据源"].append(file.name)

        return stats

    def get_database_stats(self) -> Dict:
        """
        获取数据库统计

        Returns:
            统计数据
        """
        stats = {
            "Qdrant": {"状态": "未连接", "集合": []},
            "数据源": [],
        }

        # 检查 Qdrant
        qdrant_path = self.vectorstore_dir / "qdrant"
        if qdrant_path.exists():
            stats["Qdrant"]["状态"] = "本地可用"
            stats["Qdrant"]["集合"] = [
                "novel_settings",
                "writing_techniques",
                "case_library",
            ]
            stats["数据源"].append("qdrant/")

        return stats

    def get_project_stats(self) -> Dict:
        """
        获取项目整体统计

        Returns:
            综合统计数据
        """
        stats = {
            "timestamp": datetime.now().isoformat(),
            "知识图谱": self.get_knowledge_graph_stats(),
            "技法库": self.get_technique_stats(),
            "数据库": self.get_database_stats(),
            "文件统计": {},
        }

        # 统计文件数量
        vectorstore_files = list(self.vectorstore_dir.glob("*.py"))
        stats["文件统计"]["Python脚本"] = len(vectorstore_files)

        json_files = list(self.vectorstore_dir.glob("*.json"))
        stats["文件统计"]["JSON文件"] = len(json_files)

        md_files = list(self.vectorstore_dir.glob("**/*.md"))
        stats["文件统计"]["Markdown文件"] = len(md_files)

        return stats

    def generate_report(
        self, output: Optional[Path] = None, format: str = "json"
    ) -> str:
        """
        生成统计报告

        Args:
            output: 输出文件路径
            format: 输出格式 (json/html/text)

        Returns:
            报告内容
        """
        stats = self.get_project_stats()

        if format == "json":
            content = json.dumps(stats, ensure_ascii=False, indent=2)

        elif format == "text":
            content = self._render_text_report(stats)

        elif format == "html":
            content = self._render_html_report(stats)

        else:
            content = json.dumps(stats, ensure_ascii=False, indent=2)

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"报告已保存: {output}")

        return content

    def _render_text_report(self, stats: Dict) -> str:
        """渲染文本格式报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("众生界 - 项目统计报告")
        lines.append("=" * 60)
        lines.append(f"生成时间: {stats['timestamp']}")
        lines.append("")

        # 知识图谱统计
        kg_stats = stats["知识图谱"]
        lines.append("【知识图谱】")
        lines.append(f"  实体总数: {kg_stats['实体']['总数']}")
        lines.append(f"  关系总数: {kg_stats['关系']['总数']}")

        if kg_stats["实体"]["类型分布"]:
            lines.append(f"\n  实体类型分布:")
            for type_name, count in sorted(
                kg_stats["实体"]["类型分布"].items(), key=lambda x: -x[1]
            ):
                lines.append(f"    {type_name}: {count}")

        if kg_stats["关系"]["类型分布"]:
            lines.append(f"\n  关系类型分布:")
            for type_name, count in sorted(
                kg_stats["关系"]["类型分布"].items(), key=lambda x: -x[1]
            ):
                lines.append(f"    {type_name}: {count}")

        lines.append("")

        # 数据库统计
        db_stats = stats["数据库"]
        lines.append("【数据库】")
        lines.append(f"  Qdrant: {db_stats['Qdrant']['状态']}")
        lines.append("")

        # 文件统计
        file_stats = stats["文件统计"]
        lines.append("【文件统计】")
        for file_type, count in file_stats.items():
            lines.append(f"  {file_type}: {count}")

        return "\n".join(lines)

    def _render_html_report(self, stats: Dict) -> str:
        """渲染 HTML 格式报告"""
        timestamp = stats["timestamp"]
        kg_stats = stats["知识图谱"]

        # 实体类型分布条形图
        entity_types_html = ""
        if kg_stats["实体"]["类型分布"]:
            max_count = max(kg_stats["实体"]["类型分布"].values())
            for type_name, count in sorted(
                kg_stats["实体"]["类型分布"].items(), key=lambda x: -x[1]
            ):
                width = int(count / max_count * 100)
                entity_types_html += f"""
                <div class="stat-row">
                    <span class="stat-label">{type_name}</span>
                    <span class="stat-bar" style="width: {width}%; background: #58a6ff;"></span>
                    <span class="stat-value">{count}</span>
                </div>
                """

        # 关系类型分布条形图
        relation_types_html = ""
        if kg_stats["关系"]["类型分布"]:
            max_count = max(kg_stats["关系"]["类型分布"].values())
            for type_name, count in sorted(
                kg_stats["关系"]["类型分布"].items(), key=lambda x: -x[1]
            ):
                width = int(count / max_count * 100)
                relation_types_html += f"""
                <div class="stat-row">
                    <span class="stat-label">{type_name}</span>
                    <span class="stat-bar" style="width: {width}%; background: #238636;"></span>
                    <span class="stat-value">{count}</span>
                </div>
                """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>众生界统计报告 - {timestamp}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: "Microsoft YaHei", sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 40px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #8b949e;
        }}
        
        .section {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        
        .section-title {{
            font-size: 18px;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .stat-row {{
            display: flex;
            align-items: center;
            margin: 8px 0;
            gap: 12px;
        }}
        
        .stat-label {{
            min-width: 150px;
            font-size: 14px;
        }}
        
        .stat-bar {{
            height: 20px;
            border-radius: 4px;
            flex: 1;
        }}
        
        .stat-value {{
            font-weight: bold;
            color: #58a6ff;
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        
        .metric-card {{
            background: #21262d;
            border-radius: 6px;
            padding: 16px;
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #58a6ff;
        }}
        
        .metric-label {{
            font-size: 13px;
            color: #8b949e;
            margin-top: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 众生界统计报告</h1>
            <p>生成时间: {timestamp}</p>
        </div>
        
        <div class="section">
            <h2 class="section-title">🕸️ 知识图谱</h2>
            
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value">{kg_stats["实体"]["总数"]}</div>
                    <div class="metric-label">实体总数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{kg_stats["关系"]["总数"]}</div>
                    <div class="metric-label">关系总数</div>
                </div>
            </div>
            
            <h3 style="margin-top: 24px; font-size: 14px; color: #8b949e;">实体类型分布</h3>
            {entity_types_html}
            
            <h3 style="margin-top: 24px; font-size: 14px; color: #8b949e;">关系类型分布</h3>
            {relation_types_html}
        </div>
        
        <div class="section">
            <h2 class="section-title">📚 数据库状态</h2>
            <div class="stat-row">
                <span class="stat-label">Qdrant</span>
                <span class="stat-value">{stats["数据库"]["Qdrant"]["状态"]}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Collection</span>
                <span class="stat-value">novel_settings, writing_techniques, case_library</span>
            </div>
        </div>
    </div>
</body>
</html>"""

        return html

    def print_summary(self):
        """打印统计摘要"""
        stats = self.get_project_stats()
        report = self._render_text_report(stats)
        print(report)


# ============================================================
# 命令行入口
# ============================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="统计可视化")
    parser.add_argument("--report", action="store_true", help="生成报告")
    parser.add_argument(
        "--format", choices=["json", "html", "text"], default="text", help="输出格式"
    )
    parser.add_argument("--output", type=str, help="输出文件路径")

    args = parser.parse_args()

    viz = StatsVisualizer()

    if args.report:
        output = Path(args.output) if args.output else None
        viz.generate_report(output, args.format)

    else:
        viz.print_summary()


if __name__ == "__main__":
    main()
