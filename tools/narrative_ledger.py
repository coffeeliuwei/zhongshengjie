"""tools/narrative_ledger.py
叙事台账：跨章节节拍/情绪/主题三维度多样性追踪。

问题背景：写手每次创作只看当章，无法感知"最近10章在宏观层面发生了什么"，
导致30-40章后节拍同质、情绪麻木、主题停滞。

解决机制：
  - 阶段8（经验写入）后更新台账
  - 阶段1（大纲解析）后读取台账，生成多样性约束注入当章创作

用法（CLI）：
    python tools/narrative_ledger.py update 5 --beats 战斗 突破 --tension 4 --themes 力量的代价:3 身份认同:1
    python tools/narrative_ledger.py constraints 6
    python tools/narrative_ledger.py show

用法（模块）：
    from tools.narrative_ledger import update_chapter, get_diversity_constraints
    update_chapter(chapter=5, scene_types=["战斗","突破"], tension_level=4,
                   themes_touched={"力量的代价": 3})
    block = get_diversity_constraints(next_chapter=6)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    sys.exit("缺少 pyyaml，请先：pip install pyyaml")

_ROOT = Path(__file__).parent.parent
_CFG_PATH = _ROOT / "config" / "narrative_ledger_config.yaml"


# ─── 配置加载 ──────────────────────────────────────────────────

def _load_cfg() -> dict:
    if not _CFG_PATH.exists():
        return {}
    with open(_CFG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _ledger_path() -> Path:
    cfg = _load_cfg()
    rel = cfg.get("ledger_path", "data/narrative_ledger.json")
    p = _ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ─── 台账读写 ──────────────────────────────────────────────────

def _load_ledger() -> dict:
    p = _ledger_path()
    if not p.exists():
        return {"chapters": {}, "meta": {"created_at": _now()}}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save_ledger(data: dict) -> None:
    data["meta"]["last_updated"] = _now()
    with open(_ledger_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─── 核心接口 ──────────────────────────────────────────────────

def update_chapter(
    chapter: int,
    scene_types: list[str],
    tension_level: int,
    themes_touched: dict[str, int] | None = None,
) -> None:
    """在阶段8经验写入后调用，更新台账。

    Args:
        chapter:       章节号（整数）
        scene_types:   本章使用的场景类型列表（如 ["战斗","突破"]）
        tension_level: 本章整体张力等级 1-5
        themes_touched: 触碰的主题及深度 {"主题名": depth(1-3)}
    """
    ledger = _load_ledger()
    ledger["chapters"][str(chapter)] = {
        "scene_types": scene_types,
        "tension_level": max(1, min(5, tension_level)),
        "themes_touched": themes_touched or {},
        "recorded_at": _now(),
    }
    _save_ledger(ledger)


def get_diversity_constraints(next_chapter: int) -> str:
    """在阶段1大纲解析后调用，返回可直接注入 prompt 的多样性约束块。

    Args:
        next_chapter: 即将创作的章节号

    Returns:
        格式化的约束字符串；若台账不足3章数据则返回空字符串（冷启动跳过）。
    """
    ledger = _load_ledger()
    chapters = ledger.get("chapters", {})

    # 按章节号排序，只取 next_chapter 之前的记录
    history = sorted(
        [(int(k), v) for k, v in chapters.items() if int(k) < next_chapter],
        key=lambda x: x[0],
    )

    if len(history) < 3:
        return ""  # 冷启动，数据不足

    cfg = _load_cfg()

    hard_constraints: list[str] = []
    suggestions: list[str] = []

    # ── 1. 节拍多样性分析 ──────────────────────────────────────
    beat_cfg = cfg.get("beat_tracking", {})
    window = beat_cfg.get("window", 10)
    consec_ban = beat_cfg.get("consecutive_ban_threshold", 3)
    freq_warn = beat_cfg.get("window_frequency_warn", 4)
    type_groups: dict[str, list[str]] = beat_cfg.get("type_groups", {})

    recent = history[-window:]

    # 统计各场景类型在窗口内出现次数
    type_counts: dict[str, int] = {}
    for _, ch in recent:
        for st in ch.get("scene_types", []):
            type_counts[st] = type_counts.get(st, 0) + 1

    # 检测连续相同类型组
    def _group_of(st: str) -> str | None:
        for g, members in type_groups.items():
            if st in members:
                return g
        return None

    # 最后连续几章的主导组
    last_groups: list[str | None] = []
    for _, ch in history[-consec_ban:]:
        types = ch.get("scene_types", [])
        groups = [_group_of(t) for t in types if _group_of(t)]
        if groups:
            last_groups.append(groups[0])  # 取第一个有效分组

    # 连续 consec_ban 章都是同一组 → 禁止
    if len(last_groups) == consec_ban and len(set(last_groups)) == 1:
        banned_group = last_groups[0]
        banned_types = type_groups.get(banned_group, [])
        if banned_types:
            hard_constraints.append(
                f"【节拍禁止】连续 {consec_ban} 章均为「{banned_group}」场景，"
                f"本章禁止使用：{'/'.join(banned_types)}；"
                f"必须切换到其他场景组（人物/氛围/叙事/悬念等）。"
            )

    # 窗口内高频类型 → 降频建议
    for st, cnt in sorted(type_counts.items(), key=lambda x: -x[1]):
        if cnt >= freq_warn:
            suggestions.append(
                f"【节拍降频】「{st}」在最近 {window} 章中已出现 {cnt} 次，"
                f"本章如非必要请减少比重或换角度处理。"
            )
            break  # 只提示最高频的那一个

    # ── 2. 情绪曲线分析 ────────────────────────────────────────
    tension_cfg = cfg.get("tension_tracking", {})
    t_window = tension_cfg.get("window", 10)
    high_consec = tension_cfg.get("high_consecutive_threshold", 4)
    high_lvl = tension_cfg.get("high_level", 4)
    low_consec = tension_cfg.get("low_consecutive_threshold", 3)
    low_lvl = tension_cfg.get("low_level", 2)

    recent_t = history[-t_window:]
    tension_vals = [ch.get("tension_level", 3) for _, ch in recent_t]

    # 连续高张力
    if len(tension_vals) >= high_consec and all(
        t >= high_lvl for t in tension_vals[-high_consec:]
    ):
        hard_constraints.append(
            f"【张力降温】连续 {high_consec} 章张力 >= {high_lvl}，"
            f"本章必须安排一段低张力内容（日常/内省/氛围/过渡），"
            f"让读者情绪有喘息空间，否则高潮感会麻木。"
        )

    # 连续低张力
    elif len(tension_vals) >= low_consec and all(
        t <= low_lvl for t in tension_vals[-low_consec:]
    ):
        suggestions.append(
            f"【张力升温】连续 {low_consec} 章张力 <= {low_lvl}，"
            f"故事节奏偏缓，本章建议埋入一个新冲突种子或推进一条悬念线。"
        )

    # ── 3. 主题沉睡分析 ────────────────────────────────────────
    theme_cfg = cfg.get("theme_tracking", {})
    dormant_th = theme_cfg.get("dormant_threshold", 30)
    lost_th = theme_cfg.get("lost_threshold", 50)
    core_themes: list[dict] = theme_cfg.get("core_themes", [])

    # 统计每个主题最后一次出现的章节
    theme_last: dict[str, int] = {}
    for ch_num, ch in history:
        for theme_name, depth in ch.get("themes_touched", {}).items():
            if isinstance(theme_name, str) and depth >= 1:
                theme_last[theme_name] = ch_num

    dormant: list[str] = []
    lost: list[str] = []
    for t in core_themes:
        tname = t["name"]
        last = theme_last.get(tname)
        if last is None:
            gap = next_chapter  # 从未出现
        else:
            gap = next_chapter - last

        if gap >= lost_th:
            lost.append(f"{tname}（{gap}章未触碰）")
        elif gap >= dormant_th:
            dormant.append(f"{tname}（{gap}章未触碰）")

    if lost:
        hard_constraints.append(
            f"【遗失议题警告】以下核心主题已严重缺席，本章必须触碰其中至少1个：\n"
            + "  " + "、".join(lost)
        )
    elif dormant:
        suggestions.append(
            f"【沉睡议题提醒】以下主题已超过 {dormant_th} 章未出现，"
            f"建议本章以侧笔或场景背景方式唤醒：\n"
            + "  " + "、".join(dormant)
        )

    # ── 4. 组装输出 ────────────────────────────────────────────
    out_cfg = cfg.get("output", {})
    max_hard = out_cfg.get("max_hard_constraints", 3)
    max_soft = out_cfg.get("max_suggestions", 2)

    hard_constraints = hard_constraints[:max_hard]
    suggestions = suggestions[:max_soft]

    if not hard_constraints and not suggestions:
        return ""

    lines = [f"★ 【叙事台账约束 — 第{next_chapter}章】（基于前{len(history)}章数据）"]

    if hard_constraints:
        lines.append("")
        lines.append("## 强制约束（必须执行，不得忽略）")
        for i, c in enumerate(hard_constraints, 1):
            lines.append(f"{i}. {c}")

    if suggestions:
        lines.append("")
        lines.append("## 建议（软约束，可结合具体场景判断）")
        for s in suggestions:
            lines.append(f"- {s}")

    lines.append("")
    return "\n".join(lines)


# ─── CLI 展示 ──────────────────────────────────────────────────

def show_summary() -> str:
    """生成台账当前状态的可读摘要。"""
    ledger = _load_ledger()
    chapters = ledger.get("chapters", {})
    if not chapters:
        return "台账为空（还没有章节数据）"

    history = sorted([(int(k), v) for k, v in chapters.items()], key=lambda x: x[0])
    lines = [f"=== 叙事台账摘要（共 {len(history)} 章记录）===", ""]

    # 最近5章概览
    lines.append("【最近5章】")
    for ch_num, ch in history[-5:]:
        beats = "/".join(ch.get("scene_types", []))
        tension = ch.get("tension_level", "?")
        themes = list(ch.get("themes_touched", {}).keys())
        theme_str = "、".join(themes) if themes else "无"
        lines.append(f"  第{ch_num}章 | 节拍:{beats} | 张力:{tension} | 主题:{theme_str}")

    # 张力曲线（最近10章）
    recent10 = history[-10:]
    tension_bar = "".join(
        ["▁▂▃▄▅▆▇█"[min(ch.get("tension_level", 1) - 1, 7)] for _, ch in recent10]
    )
    lines.append(f"\n【张力曲线（近{len(recent10)}章）】 {tension_bar}")

    return "\n".join(lines)


# ─── CLI ──────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="众生界叙事台账",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd")

    # update 子命令
    p_update = sub.add_parser("update", help="更新台账（阶段8调用）")
    p_update.add_argument("chapter", type=int, help="章节号")
    p_update.add_argument("--beats", nargs="+", default=[], metavar="类型",
                          help="本章场景类型列表（如：战斗 突破）")
    p_update.add_argument("--tension", type=int, default=3, metavar="1-5",
                          help="本章整体张力等级 1-5")
    p_update.add_argument("--themes", nargs="*", default=[], metavar="主题名:深度",
                          help="触碰的主题及深度（如：力量的代价:3 身份认同:1）")

    # constraints 子命令
    p_con = sub.add_parser("constraints", help="读取约束（阶段1调用）")
    p_con.add_argument("chapter", type=int, help="即将创作的章节号")

    # show 子命令
    sub.add_parser("show", help="展示台账摘要")

    args = parser.parse_args()

    if args.cmd == "update":
        themes: dict[str, int] = {}
        for t in args.themes:
            if ":" in t:
                name, depth = t.rsplit(":", 1)
                themes[name.strip()] = int(depth)
            else:
                themes[t.strip()] = 1
        update_chapter(args.chapter, args.beats, args.tension, themes)
        print(f"[台账] 第{args.chapter}章已记录：节拍={args.beats} 张力={args.tension}")

    elif args.cmd == "constraints":
        block = get_diversity_constraints(args.chapter)
        if block:
            print(block)
        else:
            print(f"[台账] 第{args.chapter}章：数据不足或无约束触发，正常创作即可")

    elif args.cmd == "show":
        print(show_summary())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
