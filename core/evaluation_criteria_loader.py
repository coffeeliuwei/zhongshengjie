#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审核维度加载器
==============

从 evaluation_criteria_v1 Collection 加载审核标准，
并提供可执行的检测接口。

功能：
1. 加载禁止项列表（可执行的正则pattern）
2. 加载技法评估标准
3. 加载阈值配置
4. 执行文本检测

参考：evaluation-criteria-extension-design.md
"""

import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_loader import get_qdrant_url


@dataclass
class ProhibitionMatch:
    """禁止项匹配结果"""

    name: str
    pattern: str
    matches: List[str]
    count: int
    threshold: str
    passed: bool


class EvaluationCriteriaLoader:
    """审核维度加载器"""

    # 可执行的禁止项正则（从Skill硬编码迁移）
    EXECUTABLE_PROHIBITIONS = {
        "AI味表达": [
            r"眼中闪过(一丝|一抹|一道)",
            r"心中涌起(一股|一丝)",
            r"嘴角勾起(一抹|一丝)",
            r"不禁(\w+)",
        ],
        "古龙式极简": [
            r"^\s*[痒疼痛死]\s*[。！]$",  # 单字句（痒。疼。痛。）
            r"^\s*[^\n]{1,2}[。！]$",  # 1-2字句（需要更严格）
        ],
        "时间连接词": [
            r"\n然后[，。]",
            r"\n就在这时",
            r"过了一会儿",
        ],
        "抽象统计词": [
            r"无数(个|人|次)",
            r"成千上万",
        ],
        "精确年龄": [
            r"\d{1,2}岁的(少年|女子|男子|人)",
        ],
        "Markdown加粗": [
            r"\*\*[^\*]+\*\*",
        ],
    }

    def __init__(self):
        """初始化"""
        from qdrant_client import QdrantClient

        self.client = QdrantClient(url=get_qdrant_url())
        self.collection_name = "evaluation_criteria_v1"

        self.prohibitions: List[Dict] = []
        self.technique_criteria: List[Dict] = []
        self.thresholds: List[Dict] = []

        self._loaded = False

    def load(self) -> Dict[str, int]:
        """
        从向量库加载审核标准

        Returns:
            各类型的加载数量
        """
        if self._loaded:
            return {
                "prohibition": len(self.prohibitions),
                "technique_criteria": len(self.technique_criteria),
                "threshold": len(self.thresholds),
            }

        # 从向量库scroll所有记录
        results, _ = self.client.scroll(
            self.collection_name,
            limit=100,
            with_payload=True,
        )

        # 分类存储
        for r in results:
            payload = r.payload
            type_ = payload.get("dimension_type", "")

            if type_ == "prohibition":
                # 将模板pattern转换为可执行正则
                payload["executable_patterns"] = self._convert_to_executable(
                    payload.get("name", ""),
                    payload.get("pattern", ""),
                )
                self.prohibitions.append(payload)

            elif type_ == "technique_criteria":
                self.technique_criteria.append(payload)

            elif type_ == "threshold":
                self.thresholds.append(payload)

        self._loaded = True

        return {
            "prohibition": len(self.prohibitions),
            "technique_criteria": len(self.technique_criteria),
            "threshold": len(self.thresholds),
        }

    def _convert_to_executable(self, name: str, template_pattern: str) -> List[str]:
        """
        将模板pattern转换为可执行正则

        Args:
            name: 禁止项名称
            template_pattern: 模板pattern（如 '眼中闪过一丝{emotion}'）

        Returns:
            可执行正则列表
        """
        # 优先使用预定义的可执行正则
        if name in self.EXECUTABLE_PROHIBITIONS:
            return self.EXECUTABLE_PROHIBITIONS[name]

        # 尝试转换模板
        # {emotion} -> (一丝|一抹|一道)
        # {action} -> V+
        conversions = {
            "{emotion}": "(一丝|一抹|一道|冷意|笑意|暖意)",
            "{action}": r"(\w+)",
            "{single_word}": r"(\w)",
            "{number}": r"(\d+)",
            "{character}": r"(\w+)",
            "{content}": r"([^*]+)",
        }

        executable = template_pattern
        for placeholder, replacement in conversions.items():
            executable = executable.replace(placeholder, replacement)

        return [executable]

    def detect_prohibitions(self, text: str) -> List[ProhibitionMatch]:
        """
        检测文本中的禁止项

        Args:
            text: 待检测文本

        Returns:
            匹配结果列表
        """
        self.load()  # 确保已加载

        results = []

        for prohibition in self.prohibitions:
            name = prohibition.get("name", "")
            threshold = prohibition.get("threshold", "")
            patterns = prohibition.get("executable_patterns", [])

            matches = []
            for pattern in patterns:
                try:
                    found = re.findall(pattern, text)
                    matches.extend(found)
                except re.error:
                    continue

            if matches:
                # 判断是否失败
                # threshold格式: "出现1个即失败" / "出现≥3个即失败"
                fail_count = 1
                if "≥" in threshold or ">=" in threshold:
                    match = re.search(r"[≥>](\d+)", threshold)
                    if match:
                        fail_count = int(match.group(1))

                passed = len(matches) < fail_count

                results.append(
                    ProhibitionMatch(
                        name=name,
                        pattern=str(patterns),
                        matches=matches[:10],  # 只保留前10个
                        count=len(matches),
                        threshold=threshold,
                        passed=passed,
                    )
                )

        return results

    def get_technique_criteria(self, dimension: str = None) -> List[Dict]:
        """
        获取技法评估标准

        Args:
            dimension: 维度过滤（可选）

        Returns:
            技法标准列表
        """
        self.load()

        if dimension:
            return [
                c
                for c in self.technique_criteria
                if c.get("dimension_name", "").startswith(dimension)
            ]

        return self.technique_criteria

    def get_thresholds(self) -> Dict[str, Any]:
        """
        获取阈值配置

        Returns:
            阈值配置字典
        """
        self.load()

        thresholds = {}
        for t in self.thresholds:
            thresholds[t.get("name", "")] = t

        return thresholds

    def format_prohibition_report(self, results: List[ProhibitionMatch]) -> str:
        """
        格式化禁止项检测报告

        Args:
            results: 检测结果

        Returns:
            格式化的报告文本
        """
        lines = ["[Prohibition Detection Report]"]

        for r in results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"{r.name}: {r.count} items - {status}")

            if r.matches:
                examples = r.matches[:3]
                lines.append(f"  Sample: {', '.join(str(ex) for ex in examples)}")

        # 总体判定
        failed_count = sum(1 for r in results if not r.passed)
        overall = "PASS" if failed_count == 0 else "FAIL"
        lines.append(f"\nOverall Result: {overall}")

        return "\n".join(lines)


# 测试代码
if __name__ == "__main__":
    loader = EvaluationCriteriaLoader()

    print("=" * 60)
    print("Evaluation Criteria Loader Test")
    print("=" * 60)

    # 1. 加载测试
    print("\n[1] Loading Criteria...")
    counts = loader.load()
    for type_, count in counts.items():
        print(f"  {type_}: {count}")

    # 2. 检测测试
    print("\n[2] Prohibition Detection...")
    test_text = """
    林夕站在山巅，眼中闪过一丝冷意。
    她看着远方的敌人，心中涌起一股怒火。
    嘴角勾起一抹冷笑，她决定出手。
    然后她轻轻跃起，不禁感叹。
    """

    results = loader.detect_prohibitions(test_text)
    print(loader.format_prohibition_report(results))

    # 3. 技法标准测试
    print("\n[3] Technique Criteria...")
    techniques = loader.get_technique_criteria("战斗")
    print(f"  战斗相关技法: {len(techniques)}")
    for t in techniques[:3]:
        print(f"    - {t.get('name', '')}: 阈值{t.get('threshold_score', '')}")

    print("\n" + "=" * 60)
