"""
众生界 - 命令行入口
提供统一的CLI接口，支持所有模块操作
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .config_manager import ConfigManager, get_config
from .path_manager import PathManager, get_path_manager


class CLI:
    """命令行接口"""

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化CLI

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or Path.cwd()
        self.config = get_config(project_root)
        self.path_manager = get_path_manager(self.config)
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        """创建命令行解析器"""
        parser = argparse.ArgumentParser(
            prog="众生界", description="众生界小说创作支持系统 - 统一CLI入口"
        )

        subparsers = parser.add_subparsers(dest="module", help="模块选择")

        # ==================== 配置模块 ====================
        config_parser = subparsers.add_parser("config", help="配置管理")
        config_parser.add_argument("--show", action="store_true", help="显示当前配置")
        config_parser.add_argument("--init", action="store_true", help="初始化配置文件")
        config_parser.add_argument(
            "--add-resource", nargs=2, metavar=("ID", "PATH"), help="添加自定义资源目录"
        )

        # ==================== 入库模块 ====================
        kb_parser = subparsers.add_parser("kb", help="知识入库管理")
        kb_parser.add_argument(
            "--sync",
            choices=["novel", "technique", "case", "all"],
            help="同步数据到向量库",
        )
        kb_parser.add_argument("--stats", action="store_true", help="显示数据库统计")
        kb_parser.add_argument(
            "--db-status", action="store_true", help="检查数据库连接状态"
        )
        kb_parser.add_argument("--search-novel", metavar="QUERY", help="检索小说设定")
        kb_parser.add_argument(
            "--search-technique", metavar="QUERY", help="检索创作技法"
        )
        kb_parser.add_argument("--search-case", metavar="QUERY", help="检索案例")

        # ==================== 验证模块 ====================
        val_parser = subparsers.add_parser("validate", help="验证管理")
        val_parser.add_argument("--all", action="store_true", help="运行所有验证")
        val_parser.add_argument("--quick", action="store_true", help="快速验证模式")
        val_parser.add_argument("--chapter", metavar="FILE", help="验证指定章节")
        val_parser.add_argument("--history", action="store_true", help="显示验证历史")

        # ==================== 创作模块 ====================
        create_parser = subparsers.add_parser("create", help="创作管理")
        create_parser.add_argument("--chapter", metavar="NAME", help="创作章节")
        create_parser.add_argument("--scene", metavar="TYPE", help="创作指定场景类型")
        create_parser.add_argument("--evaluate", metavar="FILE", help="评估章节内容")
        create_parser.add_argument(
            "--workflow", action="store_true", help="执行完整工作流"
        )

        # ==================== 移植模块 ====================
        migrate_parser = subparsers.add_parser("migrate", help="移植管理")
        migrate_parser.add_argument(
            "--export-template", action="store_true", help="导出项目模板（不含数据）"
        )
        migrate_parser.add_argument(
            "--init-environment", action="store_true", help="初始化新环境"
        )
        migrate_parser.add_argument("--target", metavar="DIR", help="目标目录")

        # ==================== 可视化模块 ====================
        viz_parser = subparsers.add_parser("visualize", help="可视化管理")
        viz_parser.add_argument(
            "--graph", action="store_true", help="生成知识图谱可视化"
        )
        viz_parser.add_argument("--stats", action="store_true", help="生成统计可视化")

        # ==================== 世界观切换模块 (M8 新增) ====================
        world_parser = subparsers.add_parser("switch-world", help="切换当前世界观")
        world_parser.add_argument("world_name", nargs="?", help="目标世界观名称")
        world_parser.add_argument("--list", action="store_true", help="列出所有可用世界观")

        return parser

    def run(self, args: Optional[list] = None) -> int:
        """
        运行CLI

        Args:
            args: 命令行参数，默认使用sys.argv

        Returns:
            退出码
        """
        parsed = self.parser.parse_args(args)

        if parsed.module is None:
            self.parser.print_help()
            return 0

        # 根据模块分发
        module_handlers = {
            "config": self._handle_config,
            "kb": self._handle_knowledge_base,
            "validate": self._handle_validation,
            "create": self._handle_creation,
            "migrate": self._handle_migration,
            "visualize": self._handle_visualization,
            "switch-world": self._handle_switch_world,
        }

        handler = module_handlers.get(parsed.module)
        if handler:
            return handler(parsed)
        else:
            print(f"未知模块: {parsed.module}")
            return 1

    # ==================== 模块处理器 ====================

    def _handle_config(self, args: argparse.Namespace) -> int:
        """处理配置模块"""
        if args.show:
            summary = self.config.get_config_summary()
            print("=== 当前配置 ===")
            for key, value in summary.items():
                print(f"{key}: {value}")
            return 0

        if args.init:
            self.config.ensure_directories()
            self.config.save_system_config()
            print("配置已初始化")
            return 0

        if args.add_resource:
            resource_id, resource_path = args.add_resource
            path = Path(resource_path)
            self.config.update_custom_resource(resource_id, path)
            self.config.save_system_config()
            print(f"已添加资源: {resource_id} -> {path}")
            return 0

        print("请指定操作: --show, --init, 或 --add-resource")
        return 1

    def _handle_knowledge_base(self, args: argparse.Namespace) -> int:
        """处理知识入库模块"""
        from modules.knowledge_base import KnowledgeBase

        kb = KnowledgeBase()

        # 检查数据库状态
        if args.db_status:
            info = kb.check_database()
            print("=" * 60)
            print("数据库连接状态")
            print("=" * 60)
            print(f"状态: {info['status']}")
            print(f"主机: {info['host']}:{info['port']}")
            print(f"消息: {info['message']}")
            if info.get("latency_ms"):
                print(f"延迟: {info['latency_ms']:.2f}ms")
            if info.get("collections"):
                print("\n集合统计:")
                for name, count in info["collections"].items():
                    print(f"  {name}: {count} 条")

            if kb.is_degraded:
                print("\n⚠️ 当前处于降级模式，使用本地缓存")
                print("   启动 Qdrant: docker run -p 6333:6333 qdrant/qdrant")
            return 0

        # 检查是否降级模式，给出提示
        if kb.is_degraded:
            print("⚠️ 数据库不可用，使用本地缓存模式")
            print("   启动 Qdrant: docker run -p 6333:6333 qdrant/qdrant")
            print()

        # 同步操作
        if args.sync:
            print(f"同步数据: {args.sync}")
            result = kb.sync(target=args.sync, rebuild=False)
            print("\n同步结果:")
            for key, count in result.items():
                print(f"  {key}: {count} 条")
            return 0

        # 显示统计
        if args.stats:
            stats = kb.get_stats()
            print("=" * 60)
            print("知识库统计")
            print("=" * 60)
            for source, info in stats.items():
                print(f"\n【{source}】")
                for k, v in info.items():
                    print(f"  {k}: {v}")
            return 0

        # 检索小说设定
        if args.search_novel:
            print(f"检索小说设定: {args.search_novel}")
            results = kb.search_novel(args.search_novel, top_k=5)
            if results:
                print("\n【检索结果】")
                for i, r in enumerate(results, 1):
                    print(
                        f"\n[{i}] {r['name']} ({r['type']}) - 相似度: {r['score']:.0%}"
                    )
                    desc = r.get("description", "")[:150]
                    if desc:
                        print(f"    {desc}...")
            else:
                print("未找到匹配结果")
            return 0

        # 检索创作技法
        if args.search_technique:
            print(f"检索创作技法: {args.search_technique}")
            results = kb.search_technique(args.search_technique, top_k=5)
            if results:
                print("\n【检索结果】")
                for i, r in enumerate(results, 1):
                    print(
                        f"\n[{i}] {r['name']} ({r['dimension']}) - 相似度: {r['score']:.0%}"
                    )
                    content = r.get("content", "")[:150]
                    if content:
                        print(f"    {content}...")
            else:
                print("未找到匹配结果")
            return 0

        # 检索案例
        if args.search_case:
            print(f"检索案例: {args.search_case}")
            results = kb.search_case(args.search_case, top_k=5)
            if results:
                print("\n【检索结果】")
                for i, r in enumerate(results, 1):
                    print(
                        f"\n[{i}] {r['novel_name']} ({r['scene_type']}) - 相似度: {r['score']:.0%}"
                    )
                    content = r.get("content", "")[:150]
                    if content:
                        print(f"    {content}...")
            else:
                print("未找到匹配结果")
            return 0

        # 无操作时显示帮助
        print("请指定操作:")
        print("  --sync [novel|technique|case|all]  同步数据到向量库")
        print("  --stats                            显示数据库统计")
        print("  --search-novel QUERY               检索小说设定")
        print("  --search-technique QUERY           检索创作技法")
        print("  --search-case QUERY                检索案例")
        return 1

    def _handle_validation(self, args: argparse.Namespace) -> int:
        """处理验证模块"""
        try:
            from modules.validation import run_validation_cli

            return run_validation_cli(args)
        except ImportError:
            # 回退到原有脚本
            print("验证模块未安装，使用原有脚本")
            print("请使用: python .vectorstore/verify_all.py")
            return 1

    def _handle_creation(self, args: argparse.Namespace) -> int:
        """
        处理创作模块（M2-β 后该模块已归档，转为引导用户走 skill 入口）

        [N13 2026-04-18] 旧 modules.creation 已归档至 .archived/modules_creation_archived/
        创作工作流现在通过 Claude Code skill (novel-workflow) 启动，不再走 CLI。
        """
        print()
        print("=" * 60)
        print("[INFO] 创作工作流已迁移至 Claude Code skill 入口")
        print("=" * 60)
        print()
        print("旧的 `python -m core create` CLI 入口在 M2-β 重构后已停用。")
        print("现在请通过以下方式启动小说创作工作流：")
        print()
        print("  方式 1（推荐）: 在 Claude Code 中使用 skill")
        print("    > /novel-workflow")
        print()
        print("  方式 2: 直接在对话中描述需求，Claude 会自动调用相应 skill")
        print("    > 请帮我写第3章的战斗场景")
        print()
        print("  方式 3: 使用单个写手 skill")
        print("    > /novelist-canglan      # 苍澜（玄幻）")
        print("    > /novelist-xuanyi       # 玄一（古风）")
        print("    > /novelist-moyan        # 墨言（言情）")
        print("    > /novelist-jianchen     # 剑尘（武侠）")
        print("    > /novelist-yunxi        # 云溪（治愈）")
        print()
        print("=" * 60)
        return 2  # exit code 2 = 命令存在但未实现/已迁移

    def _handle_migration(self, args: argparse.Namespace) -> int:
        """处理移植模块"""
        # TODO: 实现移植工具
        print("移植模块 - 功能开发中")
        print("移植工具开发进行中")
        return 0

    def _handle_visualization(self, args: argparse.Namespace) -> int:
        """处理可视化模块"""
        try:
            from modules.visualization import GraphVisualizer, StatsVisualizer

            output_dir = self.project_root / ".vectorstore"

            if args.graph:
                viz = GraphVisualizer(self.project_root)

                # 生成知识图谱
                kg_output = output_dir / "knowledge_graph.html"
                print(f"\n生成知识图谱...")
                viz.generate_knowledge_graph_html(output=kg_output)

                # 生成技法图谱
                tech_output = output_dir / "technique_graph.html"
                print(f"\n生成技法图谱...")
                viz.generate_technique_graph_html(output=tech_output)

                print(f"\n可视化文件已生成:")
                print(f"  - {kg_output}")
                print(f"  - {tech_output}")
                return 0

            if args.stats:
                stats = StatsVisualizer(self.project_root)

                # 生成统计报告
                stats_output = output_dir / "stats_report.html"
                print(f"\n生成统计报告...")
                stats.generate_report(output=stats_output, format="html")

                # 打印摘要
                stats.print_summary()

                print(f"\n统计报告已生成: {stats_output}")
                return 0

            print("请指定操作: --graph 或 --stats")
            return 1

        except ImportError as e:
            print(f"可视化模块导入失败: {e}")
            print("请确保 modules/visualization/ 模块已正确安装")
            return 1

    def _handle_switch_world(self, args: argparse.Namespace) -> int:
        """处理世界观切换模块 (M8 新增)"""
        from .world_loader import switch_world, list_available_worlds, get_current_world_name

        if args.list:
            worlds = list_available_worlds(self.project_root)
            current = get_current_world_name(self.project_root)
            print(f"当前世界观: {current}")
            print("可用世界观:")
            for w in worlds:
                marker = " ← 当前" if w == current else ""
                print(f"  {w}{marker}")
            return 0

        if not args.world_name:
            print("用法: python -m core switch-world <世界观名称>")
            print("     python -m core switch-world --list")
            return 1

        try:
            switch_world(args.world_name, self.project_root)
            return 0
        except FileNotFoundError as e:
            print(f"❌ {e}")
            return 1
        except ValueError as e:
            print(f"❌ {e}")
            return 1


def main():
    """CLI入口函数"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == "__main__":
    main()
