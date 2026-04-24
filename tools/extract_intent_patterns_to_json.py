#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[M4 一次性脚本] 提取 IntentClassifier 的 CORE_INTENTS + EXTENDED_INTENTS 到 JSON

为什么存在：
- intent_classifier.py 含 459+ 中文 regex 字符串，M6 Cython 编译时这类字符串
  应外化到 JSON 让用户可独立修改（详见审核报告 §5「类 B 字符串外化」）
- 手抄 459 个 regex 极易出错，本脚本通过 import 直接序列化保证一致性

使用：
    python tools/extract_intent_patterns_to_json.py
    # 输出：config/intent_patterns.json

一次性：跑完一次产出 JSON 后基本不再用；保留以备日后需要重新提取。
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.conversation.intent_classifier import IntentClassifier, IntentCategory


def _serialize_intents(intents: dict) -> dict:
    """把 IntentCategory enum 转成字符串名，patterns 与 entities 原样保留"""
    out = {}
    for name, cfg in intents.items():
        category = cfg["category"]
        if isinstance(category, IntentCategory):
            category_name = category.name
        else:
            raise TypeError(
                f"Intent {name} 的 category 不是 IntentCategory: {type(category)}"
            )
        out[name] = {
            "patterns": list(cfg["patterns"]),
            "category": category_name,
            "entities": list(cfg.get("entities", [])),
        }
    return out


def main():
    output_path = PROJECT_ROOT / "config" / "intent_patterns.json"

    core = _serialize_intents(IntentClassifier.CORE_INTENTS)
    extended = _serialize_intents(IntentClassifier.EXTENDED_INTENTS)

    payload = {
        "_meta": {
            "version": "1.0",
            "extracted_from": "core/conversation/intent_classifier.py",
            "extracted_at": datetime.now().isoformat(timespec="seconds"),
            "milestone": "M4 (类 B 字符串外化)",
            "core_intents_count": len(core),
            "extended_intents_count": len(extended),
            "total_pattern_strings": sum(len(v["patterns"]) for v in core.values())
            + sum(len(v["patterns"]) for v in extended.values()),
        },
        "core_intents": core,
        "extended_intents": extended,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    meta = payload["_meta"]
    print(f"[OK] 写入 {output_path}")
    print(
        f"  核心意图: {meta['core_intents_count']} | "
        f"扩展意图: {meta['extended_intents_count']} | "
        f"regex 总数: {meta['total_pattern_strings']}"
    )


if __name__ == "__main__":
    main()