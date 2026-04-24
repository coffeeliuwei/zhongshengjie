#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证管理器 - 统一验证入口
整合 verify_all.py 的核心功能，提供模块化验证接口

功能：
1. 运行所有验证脚本
2. 管理验证历史
3. 支持快速模式和选择性验证
4. 与CLI对接

使用方法：
    from modules.validation import ValidationManager

    manager = ValidationManager()
    manager.run_all()           # 运行所有验证
    manager.run_quick()         # 快速验证
    manager.validate_merge()    # 设定合并验证
"""

import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

# [N14 2026-04-18] 改为 core 包内的 config_loader
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from core.config_loader import (
        get_project_root,
        get_vectorstore_dir,
        get_knowledge_graph_path,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ValidationHistory:
    """验证历史管理（整合 verification_history.py）"""

    def __init__(self, history_dir: Optional[Path] = None):
        """
        初始化验证历史

        Args:
            history_dir: 历史记录存储目录
        """
        if history_dir is None:
            if HAS_CONFIG_LOADER:
                history_dir = get_vectorstore_dir() / "verification_history"
            else:
                history_dir = Path(".vectorstore/verification_history")
        self.history_dir = history_dir
        self.history_file = self.history_dir / "history.json"
        self._ensure_dir()
        self._history = self._load_history()

    def _ensure_dir(self) -> None:
        """确保目录存在"""
        self.history_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history({"version": "1.0", "records": {}})

    def _load_history(self) -> Dict:
        """加载历史记录"""
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"version": "1.0", "records": {}}

    def _save_history(self, data: Dict) -> None:
        """保存历史记录"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_result(
        self,
        verification_type: str,
        result: Dict[str, Any],
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        保存验证结果

        Args:
            verification_type: 验证类型
            result: 验证结果
            metadata: 额外元数据

        Returns:
            record_id: 记录ID
        """
        timestamp = datetime.now().isoformat()
        record_id = f"{verification_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        record = {
            "id": record_id,
            "type": verification_type,
            "timestamp": timestamp,
            "result": result,
            "metadata": metadata or {},
        }

        if verification_type not in self._history["records"]:
            self._history["records"][verification_type] = []

        self._history["records"][verification_type].append(record)
        self._save_history(self._history)

        return record_id

    def get_recent(self, verification_type: str, limit: int = 10) -> List[Dict]:
        """获取最近的验证记录"""
        records = self._history["records"].get(verification_type, [])
        return records[-limit:][::-1]

    def get_latest(self, verification_type: str) -> Optional[Dict]:
        """获取最新验证记录"""
        records = self._history["records"].get(verification_type, [])
        return records[-1] if records else None

    def get_summary(self) -> Dict:
        """获取所有验证类型的摘要"""
        summary = {}
        for vtype, records in self._history["records"].items():
            if records:
                latest = records[-1]
                summary[vtype] = {
                    "count": len(records),
                    "latest_time": latest["timestamp"],
                    "latest_result": latest["result"],
                }
        return summary

    def cleanup_old_records(self, keep_count: int = 50) -> None:
        """清理旧记录"""
        for vtype in self._history["records"]:
            records = self._history["records"][vtype]
            if len(records) > keep_count:
                self._history["records"][vtype] = records[-keep_count:]
        self._save_history(self._history)


class ValidationManager:
    """
    验证管理器 - 统一验证入口

    整合功能：
    1. verify_all.py - 统一验证入口
    2. verification_history.py - 验证历史管理
    3. verify_merge.py - 哲学设定+社会结构验证
    4. verify_worldview.py - 力量体系+时间线验证
    5. verify_structures.py - 技法入库验证
    """

    # 验证阈值配置（来自 CONFIG.md）
    VALIDATION_THRESHOLDS = {
        "世界自洽": 7,
        "人物立体": 6,
        "情感真实": 6,
        "战斗逻辑": 6,
        "文风克制": 6,
        "剧情张力": 6,
    }

    # 验证脚本配置
    VERIFICATION_SCRIPTS = [
        {
            "id": "merge",
            "name": "哲学设定+社会结构合并验证",
            "script": "verify_merge.py",
            "quick": True,
            "internal": True,  # 内部实现，不调用脚本
        },
        {
            "id": "worldview",
            "name": "力量体系+时间线验证",
            "script": "verify_worldview.py",
            "quick": True,
            "internal": True,
        },
        {
            "id": "structures",
            "name": "技法入库验证",
            "script": "verify_structures.py",
            "quick": True,
            "internal": False,  # 需调用外部脚本
        },
        {
            "id": "vectorstore",
            "name": "向量库完整性验证",
            "script": "verify_vectorstore.py",
            "quick": False,
            "internal": False,
        },
        {
            "id": "sources",
            "name": "案例库来源检查",
            "script": "check_sources.py",
            "quick": False,
            "internal": True,
        },
    ]

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化验证管理器

        Args:
            project_root: 项目根目录，默认从配置自动获取
        """
        if HAS_CONFIG_LOADER:
            self.project_root = project_root or get_project_root()
            self.vectorstore_dir = get_vectorstore_dir()
            self.knowledge_graph_path = get_knowledge_graph_path()
        else:
            self.project_root = project_root or Path.cwd()
            self.vectorstore_dir = self.project_root / ".vectorstore"
            self.knowledge_graph_path = self.vectorstore_dir / "knowledge_graph.json"
        self.history = ValidationHistory(self.vectorstore_dir / "verification_history")

    def _run_script(self, script_path: Path) -> Tuple[bool, str]:
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
                cwd=str(self.vectorstore_dir),
                timeout=120,
            )
            output = result.stdout + result.stderr
            success = result.returncode == 0
            return success, output
        except subprocess.TimeoutExpired:
            return False, "超时（超过120秒）"
        except Exception as e:
            return False, f"执行错误: {e}"

    def _validate_merge(self) -> Tuple[bool, Dict]:
        """
        验证哲学设定和社会结构合并

        整合 verify_merge.py 功能
        """
        if not self.knowledge_graph_path.exists():
            return False, {"error": "knowledge_graph.json 不存在"}

        try:
            with open(self.knowledge_graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, {"error": f"加载失败: {e}"}

        entities = data.get("实体", {})
        results = {"philosophy_count": 0, "society_count": 0, "details": []}

        # 检查角色哲学设定
        for entity_id, entity in entities.items():
            if entity_id.startswith("char_"):
                props = entity.get("属性", {})
                if "哲学设定" in props:
                    results["philosophy_count"] += 1
                    name = entity.get("名称", entity_id)
                    philosophy = props["哲学设定"].get("哲学流派", "未知")
                    results["details"].append(f"{name}: {philosophy}")

        # 检查势力社会结构
        for entity_id, entity in entities.items():
            if entity_id.startswith("faction_"):
                props = entity.get("属性", {})
                if "社会结构" in props:
                    results["society_count"] += 1

        success = results["philosophy_count"] > 0 and results["society_count"] > 0
        return success, results

    def _validate_worldview(self) -> Tuple[bool, Dict]:
        """
        验证力量体系和时间线

        整合 verify_worldview.py 功能
        """
        if not self.knowledge_graph_path.exists():
            return False, {"error": "knowledge_graph.json 不存在"}

        try:
            with open(self.knowledge_graph_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return False, {"error": f"加载失败: {e}"}

        entities = data.get("实体", {})
        results = {"power_systems": 0, "power_branches": 0, "eras": 0, "bloodlines": []}

        for entity_id, entity in entities.items():
            entity_type = entity.get("类型", "")
            if entity_type == "力量体系":
                results["power_systems"] += 1
            elif entity_type == "力量派别":
                results["power_branches"] += 1
            elif entity_type == "时代":
                results["eras"] += 1

        # 检查血脉派别
        for entity_id, entity in entities.items():
            if entity_id.startswith("bloodline_"):
                info = entity.get("属性", {})
                results["bloodlines"].append(
                    {"id": entity_id, "name": info.get("名称", "未知")}
                )

        success = results["power_systems"] >= 7 and results["eras"] >= 1
        return success, results

    def _check_sources(self) -> Tuple[bool, Dict]:
        """
        检查案例库来源

        整合 check_sources.py 功能
        """
        try:
            from qdrant_client import QdrantClient
        except ImportError:
            return False, {"error": "qdrant_client 未安装"}

        qdrant_dir = self.vectorstore_dir / "qdrant"

        if not qdrant_dir.exists():
            return False, {"error": "Qdrant 数据目录不存在"}

        try:
            client = QdrantClient(path=str(qdrant_dir))
            result = client.scroll(
                collection_name="case_library",
                limit=6000,
                with_payload=True,
                with_vectors=False,
            )

            cases = result[0]
            genres = {}
            novels = set()

            for p in cases:
                payload = p.payload
                genre = payload.get("genre", "未知")
                genres[genre] = genres.get(genre, 0) + 1
                novels.add(payload.get("novel_name", "未知"))

            return True, {
                "total_cases": len(cases),
                "genres": genres,
                "novels_count": len(novels),
            }
        except Exception as e:
            return False, {"error": str(e)}

    def run_all(
        self,
        quick: bool = False,
        selected: Optional[List[str]] = None,
        save_history: bool = True,
    ) -> Dict:
        """
        运行所有验证

        Args:
            quick: 快速模式，跳过耗时检查
            selected: 只运行指定的验证（按id）
            save_history: 是否保存到历史记录

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

        for config in self.VERIFICATION_SCRIPTS:
            # 选择性运行
            if selected and config["id"] not in selected:
                continue

            # 快速模式跳过
            if quick and not config["quick"]:
                print(f"[跳过] {config['name']} (快速模式)")
                continue

            print(f"\n{'=' * 60}")
            print(f"[运行] {config['name']}")
            print(f"{'=' * 60}")

            # 根据配置决定内部实现还是调用脚本
            if config["internal"]:
                # 内部方法验证
                method_map = {
                    "merge": self._validate_merge,
                    "worldview": self._validate_worldview,
                    "sources": self._check_sources,
                }
                method = method_map.get(config["id"])
                if method:
                    success, output = method()
                    if isinstance(output, dict):
                        output_str = json.dumps(output, ensure_ascii=False, indent=2)
                    else:
                        output_str = str(output)
                    print(output_str)
                else:
                    success, output = False, "方法未实现"
            else:
                # 调用外部脚本
                script_path = self.vectorstore_dir / config["script"]
                if not script_path.exists():
                    print(f"[错误] 脚本不存在: {script_path}")
                    success, output = False, "脚本不存在"
                else:
                    success, output = self._run_script(script_path)
                    print(output)

            status = "✓ 通过" if success else "✗ 失败"
            print(f"\n[{status}] {config['name']}")

            results.append(
                {
                    "id": config["id"],
                    "name": config["name"],
                    "success": success,
                    "output": str(output)[:500]
                    if len(str(output)) > 500
                    else str(output),
                }
            )

            if success:
                passed += 1
            else:
                failed += 1

        report = {
            "passed": passed,
            "failed": failed,
            "results": results,
        }

        # 保存到历史
        if save_history:
            for r in results:
                self.history.save_result(
                    verification_type=r["id"],
                    result={"success": r["success"], "name": r["name"]},
                )
            self.history.save_result(
                verification_type="verify_all",
                result={
                    "passed": passed,
                    "failed": failed,
                    "total": passed + failed,
                },
                metadata={"timestamp": datetime.now().isoformat()},
            )

        return report

    def run_quick(self) -> Dict:
        """快速验证（只运行快速验证项）"""
        return self.run_all(quick=True)

    def validate_chapter(self, chapter_path: str) -> Dict:
        """
        验证指定章节

        Args:
            chapter_path: 章节文件路径

        Returns:
            验证结果
        """
        from .scorer_manager import ScorerManager

        scorer = ScorerManager()
        if scorer.load_chapter(chapter_path):
            return scorer.get_dimension_scores()
        else:
            return {"error": f"无法加载章节: {chapter_path}"}

    def show_history(self) -> None:
        """显示验证历史"""
        summary = self.history.get_summary()
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

    def print_summary(self, report: Dict) -> bool:
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


# ============================================================
# CLI 适配接口
# ============================================================


def run_validation_cli(args) -> int:
    """
    CLI验证入口

    Args:
        args: argparse解析后的参数

    Returns:
        退出码
    """
    manager = ValidationManager()

    if args.history:
        manager.show_history()
        return 0

    if args.all:
        report = manager.run_all(quick=args.quick)
        all_passed = manager.print_summary(report)
        return 0 if all_passed else 1

    if args.chapter:
        result = manager.validate_chapter(args.chapter)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if "error" not in result else 1

    # 默认运行全部
    report = manager.run_all()
    all_passed = manager.print_summary(report)
    return 0 if all_passed else 1
