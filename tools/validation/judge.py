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


_JUDGE_PROMPT = """\
你是一位网络小说写作专家。以下是一条搜索查询和一条检索结果。
请判断结果与查询的相关程度：
0 = 无关，1 = 部分相关，2 = 高度相关。
只回复数字，不要解释。

查询：{query}
集合类型：{collection_type}
检索结果：{result_text}"""


def _parse_score(text: str) -> int | None:
    """从 LLM 返回文本中提取 0/1/2"""
    m = re.search(r"[012]", text.strip())
    return int(m.group()) if m else None


class OpenAICompatibleJudge(BaseJudge):
    """兼容 OpenAI 协议的 LLM judge（Ollama / DeepSeek / Qwen 等）"""

    def __init__(self, base_url: str, api_key: str, model: str):
        import openai
        self._client = openai.OpenAI(
            base_url=base_url if base_url and base_url != "none" else None,
            api_key=api_key if api_key != "none" else "none",
        )
        self._model = model

    def score(self, query: str, result_text: str, collection_type: str) -> int | None:
        prompt = _JUDGE_PROMPT.format(
            query=query,
            collection_type=collection_type,
            result_text=result_text[:500],
        )
        for attempt in range(3):
            try:
                resp = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=5,
                    temperature=0,
                )
                return _parse_score(resp.choices[0].message.content)
            except Exception:
                if attempt == 2:
                    return None


class OpenAIJudge(OpenAICompatibleJudge):
    """OpenAI 官方 API judge"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model


class ClaudeJudge(BaseJudge):
    """Anthropic Claude judge"""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def score(self, query: str, result_text: str, collection_type: str) -> int | None:
        prompt = _JUDGE_PROMPT.format(
            query=query,
            collection_type=collection_type,
            result_text=result_text[:500],
        )
        for attempt in range(3):
            try:
                msg = self._client.messages.create(
                    model=self._model,
                    max_tokens=5,
                    messages=[{"role": "user", "content": prompt}],
                )
                return _parse_score(msg.content[0].text)
            except Exception:
                if attempt == 2:
                    return None


def make_judge(provider: str, **kwargs) -> BaseJudge:
    """工厂函数，根据 provider 字符串创建对应 Judge 实例"""
    if provider == "skip":
        return SkipJudge()
    if provider == "manual":
        return ManualJudge()
    if provider == "openai":
        return OpenAIJudge(**kwargs)
    if provider == "claude":
        return ClaudeJudge(**kwargs)
    if provider == "compatible":
        return OpenAICompatibleJudge(**kwargs)
    raise ValueError(f"未知 judge provider: {provider!r}，支持: skip/manual/openai/claude/compatible")
