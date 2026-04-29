#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LLM-as-judge 可插拔评判模块"""

import re
from abc import ABC, abstractmethod


class BaseJudge(ABC):
    """抽象基类：给定查询和检索结果，返回相关性得分"""

    @abstractmethod
    def score(self, query: str, result_text: str, collection_type: str) -> int | None:
        """返回 0（无关）/ 1（部分相关）/ 2（高度相关）/ None（失败/跳过）"""


class SkipJudge(BaseJudge):
    """不调用 LLM，所有得分返回 None，只看 Qdrant 分数分布"""

    def score(self, query: str, result_text: str, collection_type: str) -> None:
        return None


class ManualJudge(BaseJudge):
    """终端交互，人工逐条打分"""

    def score(self, query: str, result_text: str, collection_type: str) -> int | None:
        print(f"\n集合：{collection_type}")
        print(f"查询：{query}")
        print(f"结果：{result_text[:300]}")
        while True:
            raw = input("相关性评分 (0=无关 / 1=部分相关 / 2=高度相关): ").strip()
            if raw in ("0", "1", "2"):
                return int(raw)
            print("请输入 0、1 或 2")


def make_judge(provider: str, **kwargs) -> BaseJudge:
    """工厂函数，根据 provider 字符串创建对应 Judge 实例"""
    if provider == "skip":
        return SkipJudge()
    if provider == "manual":
        return ManualJudge()
    if provider in ("openai", "claude", "compatible"):
        raise NotImplementedError(f"judge provider {provider!r} 将在 Task 3 中实现，请追加 LLM judge 类后再使用")
    raise ValueError(f"未知 judge provider: {provider!r}，支持: skip/manual/openai/claude/compatible")
