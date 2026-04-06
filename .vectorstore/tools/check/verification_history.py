#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证结果持久化模块

功能：
1. 保存验证结果到JSON文件
2. 加载历史验证记录
3. 对比验证结果变化
4. 生成趋势报告

使用方法：
    from verification_history import VerificationHistory

    history = VerificationHistory()

    # 保存验证结果
    history.save_result("verify_merge", {"passed": True, "details": {...}})

    # 获取最近N次验证
    results = history.get_recent("verify_merge", limit=5)

    # 对比变化
    diff = history.compare_with_previous("verify_merge", current_result)
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# 配置
SCRIPT_DIR = Path(__file__).parent
HISTORY_DIR = SCRIPT_DIR / "verification_history"
HISTORY_FILE = HISTORY_DIR / "history.json"


class VerificationHistory:
    """验证结果历史管理"""

    def __init__(self, history_dir: Path = None):
        self.history_dir = history_dir or HISTORY_DIR
        self.history_file = self.history_dir / "history.json"
        self._ensure_dir()
        self._history = self._load_history()

    def _ensure_dir(self):
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

    def _save_history(self, data: Dict):
        """保存历史记录"""
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_result(
        self, verification_type: str, result: Dict[str, Any], metadata: Dict = None
    ) -> str:
        """
        保存验证结果

        Args:
            verification_type: 验证类型 (如 "verify_merge", "checklist_score")
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
        """
        获取最近的验证记录

        Args:
            verification_type: 验证类型
            limit: 最大返回数量

        Returns:
            记录列表（最新的在前）
        """
        records = self._history["records"].get(verification_type, [])
        return records[-limit:][::-1]  # 最新的在前

    def get_latest(self, verification_type: str) -> Optional[Dict]:
        """获取最新验证记录"""
        records = self._history["records"].get(verification_type, [])
        return records[-1] if records else None

    def compare_with_previous(self, verification_type: str, current: Dict) -> Dict:
        """
        与上次验证结果对比

        Returns:
            {
                "has_previous": bool,
                "previous": Dict,
                "changes": Dict,  # 变化的字段
                "improved": List,  # 改善的项目
                "regressed": List, # 退化的项目
            }
        """
        previous = self.get_latest(verification_type)

        if not previous:
            return {
                "has_previous": False,
                "previous": None,
                "changes": {},
                "improved": [],
                "regressed": [],
            }

        prev_result = previous.get("result", {})
        changes = {}
        improved = []
        regressed = []

        # 对比数值字段
        for key in set(prev_result.keys()) | set(current.keys()):
            prev_val = prev_result.get(key)
            curr_val = current.get(key)

            if prev_val != curr_val:
                changes[key] = {
                    "previous": prev_val,
                    "current": curr_val,
                }

                # 判断改善或退化
                if isinstance(prev_val, (int, float)) and isinstance(
                    curr_val, (int, float)
                ):
                    if curr_val > prev_val:
                        improved.append(key)
                    elif curr_val < prev_val:
                        regressed.append(key)

        return {
            "has_previous": True,
            "previous": prev_result,
            "changes": changes,
            "improved": improved,
            "regressed": regressed,
        }

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

    def cleanup_old_records(self, keep_count: int = 50):
        """
        清理旧记录，只保留最近的N条

        Args:
            keep_count: 每个验证类型保留的最大记录数
        """
        for vtype in self._history["records"]:
            records = self._history["records"][vtype]
            if len(records) > keep_count:
                self._history["records"][vtype] = records[-keep_count:]

        self._save_history(self._history)
        print(f"[清理] 每个验证类型保留最近{keep_count}条记录")


# ============================================================
# 命令行工具
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="验证结果历史管理")
    parser.add_argument("--summary", action="store_true", help="显示所有验证类型摘要")
    parser.add_argument(
        "--recent", type=str, metavar="TYPE", help="显示指定类型的最近记录"
    )
    parser.add_argument("--limit", type=int, default=10, help="显示记录数量")
    parser.add_argument(
        "--cleanup", type=int, metavar="N", help="清理旧记录，保留最近N条"
    )

    args = parser.parse_args()

    history = VerificationHistory()

    if args.summary:
        summary = history.get_summary()
        print("\n验证历史摘要")
        print("=" * 60)
        for vtype, info in summary.items():
            print(f"\n{vtype}:")
            print(f"  记录数: {info['count']}")
            print(f"  最新时间: {info['latest_time']}")
            print(f"  最新结果: {info['latest_result']}")

    elif args.recent:
        records = history.get_recent(args.recent, args.limit)
        print(f"\n{args.recent} - 最近{len(records)}条记录")
        print("=" * 60)
        for r in records:
            print(f"\n[{r['timestamp']}]")
            print(f"  结果: {r['result']}")

    elif args.cleanup:
        history.cleanup_old_records(args.cleanup)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
