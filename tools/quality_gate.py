"""tools/quality_gate.py
场景文本质量门控：Burstiness 检测 + AI 套句黑名单检测。

AI 文本的两大统计特征：
  1. Burstiness 低：句子长度方差 < 30（节奏均匀，无超短句/超长句混合）
  2. 套句高频：固定情感触发词出现密度高（每5-7句1次）

通过阈值：方差 ≥ 50 且套句命中 ≤ 3 条。

用法（CLI）：
    python tools/quality_gate.py --file path/to/scene.txt --writer 剑尘
    python tools/quality_gate.py --text "场景文本" [--json]

用法（模块）：
    from tools.quality_gate import run_quality_gate
    result = run_quality_gate(text, writer="剑尘", chapter=3, scene_index=2)
    if not result["passed"]:
        print(result["suggestions"])
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("缺少 pyyaml，请先：pip install pyyaml")

_ROOT = Path(__file__).parent.parent
_STYLES_PATH = _ROOT / "docs" / "style_collection" / "author_styles.yaml"
_CONFIG_PATH = _ROOT / "config" / "writers_style_config.yaml"

# ─── 通用 AI 套句黑名单（跨所有写手/作家）──────────────────────────────
_UNIVERSAL_BLACKLIST: list[str] = [
    # 眼/心理模板
    "眼中闪过一丝", "眼眸中闪烁着", "心中涌起一股", "心头一震",
    "内心深处", "心中暗道", "心里清楚",
    # 气氛堆砌
    "令人窒息的", "空气仿佛凝固", "扑面而来", "弥漫在空气中",
    "沉默良久", "沉默片刻后",
    # 动作模板
    "身体本能地", "本能地感知到", "不由自主地", "不禁",
    "缓缓地", "慢慢地", "轻轻地",
    # 时间连接
    "忽然间", "就在这时", "与此同时", "突然之间", "随即",
    "一时间", "片刻后", "须臾之间",
    # 表情模板
    "嘴角微微上扬", "脸上露出满意", "眉头微皱", "嘴角勾起一抹",
    # 感叹模板
    "竟然", "竟是", "不知为何", "莫名其妙",
    # 描述滥用
    "整个人都", "浑身上下", "全身", "无尽的", "难以言喻",
    "一道道", "只见得", "只见",
    # 套路推进
    "陷入了沉思", "不禁想到", "脑海中浮现",
]


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_writer_blacklist(writer: str) -> list[str]:
    """加载写手配置中所有作家的黑名单（并集）。"""
    styles_data = _load_yaml(_STYLES_PATH)
    config_data = _load_yaml(_CONFIG_PATH)
    author_mix: dict = (
        config_data.get("writers", {}).get(writer, {}).get("author_mix", {})
    )
    blacklist: set[str] = set()
    for author_name in author_mix:
        for a in styles_data.get("authors", []):
            if a.get("name") == author_name or a.get("id") == author_name:
                blacklist.update(a.get("ai_blacklist", []))
                break
    return list(blacklist)


def _load_gate_config() -> dict:
    config_data = _load_yaml(_CONFIG_PATH)
    return config_data.get("quality_gate", {})


def compute_burstiness(text: str) -> tuple[bool, float, str]:
    """计算句子长度方差（Burstiness 指标）。

    人类写作：短长句随机混合，方差高（>50）。
    AI 写作：每句贡献大致相同信息量，方差低（<30）。

    Returns:
        (passed, variance, detail_message)
    """
    gate_cfg = _load_gate_config()
    threshold: float = gate_cfg.get("burstiness_threshold", 50)

    # 按中文句末标点分句（保留结构完整性）
    parts = re.split(r"[。！？；…]+", text)
    lengths = [len(s.strip()) for s in parts if len(s.strip()) > 3]

    if len(lengths) < 5:
        return True, 0.0, f"样本不足（{len(lengths)} 句），跳过 Burstiness 检测"

    variance = statistics.variance(lengths)
    mean_len = statistics.mean(lengths)
    min_len = min(lengths)
    max_len = max(lengths)
    passed = variance >= threshold

    if passed:
        detail = (
            f"方差={variance:.1f} >= {threshold}（均值={mean_len:.0f}字，"
            f"最短={min_len}字，最长={max_len}字）[OK] 节奏多样性良好"
        )
    else:
        detail = (
            f"方差={variance:.1f} < {threshold}（均值={mean_len:.0f}字，"
            f"最短={min_len}字，最长={max_len}字）[X] AI感强\n"
            f"  -> 建议：加入 2-3 处超短句（<=8字）或让一段扩展到 60字以上"
        )
    return passed, variance, detail


def check_ai_blacklist(
    text: str,
    writer_blacklist: list[str] | None = None,
) -> tuple[bool, list[str], float]:
    """检测 AI 套句命中情况。

    Returns:
        (passed, hit_records, hit_rate)
        hit_records 格式：["套句（×出现次数）", ...]
    """
    gate_cfg = _load_gate_config()
    max_hits: int = gate_cfg.get("blacklist_max_hits", 3)
    max_rate: float = gate_cfg.get("blacklist_hit_rate_max", 0.15)

    combined = list(_UNIVERSAL_BLACKLIST) + (writer_blacklist or [])
    # 去重（作家黑名单可能与通用重叠）
    combined = list(dict.fromkeys(combined))

    hits: list[str] = []
    total_hits: int = 0
    for phrase in combined:
        count = text.count(phrase)
        if count > 0:
            hits.append(f"{phrase}（×{count}）")
            total_hits += count

    # 句子数估算（与 compute_burstiness 保持相同分割标准）
    sentences = [s for s in re.split(r"[。！？；…]+", text) if s.strip()]
    sentence_count = max(len(sentences), 1)
    hit_rate = total_hits / sentence_count

    passed = len(hits) <= max_hits and hit_rate <= max_rate
    return passed, hits, hit_rate


def run_quality_gate(
    text: str,
    writer: str | None = None,
    chapter: int | None = None,
    scene_index: int | None = None,
) -> dict[str, Any]:
    """执行完整质量检测。

    Args:
        text:        待检测的场景文本
        writer:      主写手名称（用于加载对应黑名单；可为 None）
        chapter:     章节号（仅用于报告标签）
        scene_index: 场景序号（仅用于报告标签）

    Returns:
        结构化检测结果字典：
        {
            "passed": bool,
            "verdict": str,
            "location": str,
            "text_length": int,
            "checks": { "burstiness": {...}, "ai_blacklist": {...} },
            "suggestions": [str],
        }
    """
    writer_blacklist = _load_writer_blacklist(writer) if writer else []

    burst_pass, variance, burst_detail = compute_burstiness(text)
    list_pass, hits, hit_rate = check_ai_blacklist(text, writer_blacklist)

    overall_pass = burst_pass and list_pass

    suggestions: list[str] = []
    if not burst_pass:
        suggestions.append(
            "【节奏】在场景内加入 2-3 处极短句（人名/感叹/空行停顿，≤8字），"
            "或将某段环境描写扩展到 60 字以上，打破长度均匀感。"
        )
    if not list_pass:
        top_hits = "、".join(h.split("（")[0] for h in hits[:4])
        suggestions.append(
            f"【套句】命中 {len(hits)} 条（{top_hits}…），"
            "逐一替换为具体感官描写或角色行为动作，禁用抽象情感词。"
        )

    if chapter and scene_index:
        location = f"第{chapter}章·场景{scene_index}"
    elif chapter:
        location = f"第{chapter}章"
    else:
        location = "未知位置"

    return {
        "passed": overall_pass,
        "verdict": "PASS [OK]" if overall_pass else "FAIL [X] -- 建议定向重写",
        "location": location,
        "writer": writer,
        "text_length": len(text),
        "checks": {
            "burstiness": {
                "passed": burst_pass,
                "variance": round(variance, 2),
                "detail": burst_detail,
            },
            "ai_blacklist": {
                "passed": list_pass,
                "hit_count": len(hits),
                "hit_rate": round(hit_rate, 3),
                "hits": hits[:10],
            },
        },
        "suggestions": suggestions,
    }


def format_report(result: dict) -> str:
    """格式化为可读报告文本。"""
    sep = "=" * 60
    lines = [
        "",
        sep,
        f"质量门控报告 — {result['location']}（{result.get('writer', '未知写手')}）",
        sep,
        f"总体结论：{result['verdict']}",
        f"文本长度：{result['text_length']} 字",
        "",
    ]

    bc = result["checks"]["burstiness"]
    lines += [
        f"[1] Burstiness 检测：{'通过 [OK]' if bc['passed'] else '未通过 [X]'}",
        f"    {bc['detail']}",
        "",
    ]

    bl = result["checks"]["ai_blacklist"]
    lines += [
        f"[2] AI套句检测：{'通过 [OK]' if bl['passed'] else '未通过 [X]'}",
        f"    命中 {bl['hit_count']} 条 / 命中率 {bl['hit_rate']:.1%}",
    ]
    for h in bl["hits"][:6]:
        lines.append(f"    - {h}")

    if result["suggestions"]:
        lines += ["", "改进建议："]
        for s in result["suggestions"]:
            lines.append(f"  → {s}")

    lines.append(sep)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="众生界场景文本质量门控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--text", help="直接传入待检测文本")
    grp.add_argument("--file", help="待检测文本文件路径")
    parser.add_argument("--writer", default=None,
                        choices=["剑尘", "墨言", "云溪", "玄一", "苍澜", None],
                        help="主写手（用于加载黑名单）")
    parser.add_argument("--chapter", type=int, default=None)
    parser.add_argument("--scene", type=int, default=None)
    parser.add_argument("--json", dest="json_out", action="store_true",
                        help="JSON 格式输出")
    args = parser.parse_args()

    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    result = run_quality_gate(text, args.writer, args.chapter, args.scene)

    if args.json_out:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(result))

    # 返回码：0=通过，1=未通过
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
