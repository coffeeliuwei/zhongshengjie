"""tools/style_injector.py
风格注入器：根据写手配置和场景类型，构建作家风格上下文提示块。

用法（CLI）：
    python tools/style_injector.py --writer 剑尘 --scene 战斗 [--seed 42]

用法（模块）：
    from tools.style_injector import build_writer_style_context
    prompt_block = build_writer_style_context("剑尘", "战斗", seed=42)
"""
from __future__ import annotations

import argparse
import random
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

# 自我风格：记忆点数量阈值（低于此值跳过注入，避免冷启动噪音）
_SELF_STYLE_MIN_POINTS = 10

# 场景类型 → 风格锚点键映射
_ANCHOR_KEY_MAP = {
    "战斗": "battle",       "高潮": "battle",       "危机": "battle",
    "修炼突破": "breakthrough", "修炼": "breakthrough",
    "人物": "character",    "情感": "character",    "心理": "character",
    "成长": "character",    "对话": "character",
    "环境": "atmosphere",   "氛围": "atmosphere",   "意境": "atmosphere",
    "开篇": "opening",      "结尾": "closing",
    "悬念": "suspense",     "伏笔": "suspense",     "转折": "reversal",
    "世界观": "worldview",  "势力": "worldview",    "传承": "worldview",
}


def _fetch_self_style_block() -> str:
    """从 memory_points_v1 读取本书自我风格偏好，拼成 prompt 追加块。

    - 记忆点数 < _SELF_STYLE_MIN_POINTS 时返回空字符串（冷启动跳过）
    - Qdrant 不可用时静默降级，不阻断主流程
    - 自我风格为全书共享，不按写手过滤
    """
    try:
        sys.path.insert(0, str(_ROOT))
        from core.inspiration.memory_point_sync import MemoryPointSync  # type: ignore

        sync = MemoryPointSync()

        # 冷启动检测
        total = sync.count()
        if total < _SELF_STYLE_MIN_POINTS:
            return ""

        pos_points = sync.list_recent("+", top_k=5)
        neg_points = sync.list_recent("-", top_k=3)

        if not pos_points:
            return ""

        def _fmt(mp: dict, max_chars: int = 60) -> str:
            payload = mp.get("payload", {})
            chapter = payload.get("chapter_ref") or ""
            text = payload.get("segment_text", "").strip()
            # 取前 max_chars 字，超长加省略号
            snippet = text[:max_chars] + ("…" if len(text) > max_chars else "")
            prefix = f"[{chapter}] " if chapter else ""
            return f"  - {prefix}{snippet}"

        lines = [
            f"★ 【本书自我风格偏好（已学习 {total} 段）】",
            "正样本偏好（写法向这些靠拢）：",
        ]
        lines.extend(_fmt(mp) for mp in pos_points)

        if neg_points:
            lines.append("负样本禁忌（避开类似句式结构）：")
            lines.extend(_fmt(mp) for mp in neg_points)

        lines.append("")
        return "\n".join(lines)

    except ImportError:
        # qdrant_client 或 core 模块未安装，静默跳过
        return ""
    except Exception as exc:  # noqa: BLE001
        # Qdrant 连接失败、collection 不存在等运行时错误，记录警告后跳过
        import logging
        logging.getLogger(__name__).warning(
            "[style_injector] _fetch_self_style_block 失败，跳过自我风格注入: %s", exc
        )
        return ""


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_author(styles_data: dict, name: str) -> dict | None:
    for a in styles_data.get("authors", []):
        if a.get("name") == name or a.get("id") == name:
            return a
    return None


def build_writer_style_context(
    writer: str,
    scene_type: str,
    seed: int | None = None,
) -> str:
    """构建写手风格上下文提示块。

    Args:
        writer:     写手名称（剑尘/墨言/云溪/玄一/苍澜）
        scene_type: 当前场景类型（战斗/人物/环境 等）
        seed:       随机种子，保证同次章节内约束一致

    Returns:
        格式化的风格上下文字符串，可直接追加到写手 prompt 末段。
        若配置缺失或作家未找到，返回空字符串（不阻断流程）。
    """
    rng = random.Random(seed)
    styles_data = _load_yaml(_STYLES_PATH)
    config_data = _load_yaml(_CONFIG_PATH)

    writer_cfg = config_data.get("writers", {}).get(writer, {})
    author_mix: dict[str, float] = writer_cfg.get("author_mix", {})
    if not author_mix:
        return ""

    # 归一化权重
    total = sum(author_mix.values())
    if total <= 0:
        return ""
    normalized = {a: w / total for a, w in author_mix.items()}

    inj_cfg = config_data.get("injection", {})
    constraints_target: int = inj_cfg.get("constraints_per_scene", 8)
    anchor_max: int = inj_cfg.get("anchor_max_chars", 300)
    bad_habits_max: int = inj_cfg.get("bad_habits_max", 2)

    anchor_key = _ANCHOR_KEY_MAP.get(scene_type, "character")

    # 收集各作家数据
    collected_constraints: list[str] = []
    collected_bad_habits: list[str] = []
    collected_anchors: list[tuple[float, str]] = []  # (weight, text)
    all_blacklist: set[str] = set()
    author_names_used: list[str] = []

    for author_name, weight in sorted(normalized.items(), key=lambda x: -x[1]):
        author = _get_author(styles_data, author_name)
        if not author:
            continue

        author_names_used.append(author_name)

        # 行为约束：按权重比例决定取几条
        n = max(1, round(weight * constraints_target))
        constraints: list[str] = author.get("behavior_constraints", [])
        if constraints:
            sample = rng.sample(constraints, min(n, len(constraints)))
            collected_constraints.extend(sample)

        # 坏习惯：权重≥0.2的作者各取1条
        if weight >= 0.2:
            bad_habits: list[str] = author.get("bad_habits", [])
            if bad_habits:
                collected_bad_habits.append(rng.choice(bad_habits))

        # 风格锚点：按权重降序，取最匹配场景类型的
        anchors: dict = author.get("style_anchors", {})
        anchor_text = (
            anchors.get(anchor_key)
            or anchors.get("character")
            or anchors.get("battle")
            or ""
        )
        if anchor_text and weight >= 0.25:
            collected_anchors.append((weight, anchor_text.strip()[:anchor_max]))

        # 黑名单合并（并集）
        all_blacklist.update(author.get("ai_blacklist", []))

    if not collected_constraints:
        return ""

    # 去重，保留顺序
    seen: set[str] = set()
    deduped_constraints: list[str] = []
    for c in collected_constraints:
        if c not in seen:
            seen.add(c)
            deduped_constraints.append(c)

    # 组装 prompt 块
    author_label = " × ".join(
        f"{n}({normalized[n]:.0%})" for n in author_names_used[:3]
    )
    lines: list[str] = [
        f"【作家风格包：{writer} — {author_label}】",
        "",
        "### 行为约束（本场景必须遵守，不得忽略）",
    ]
    for i, c in enumerate(deduped_constraints[:constraints_target], 1):
        lines.append(f"{i}. {c}")

    if collected_bad_habits:
        lines.append("")
        lines.append("### 专属语言 quirk（适度植入 1-2 处，制造人味）")
        for h in collected_bad_habits[:bad_habits_max]:
            lines.append(f"- {h}")

    # 取权重最高的锚点
    if collected_anchors:
        collected_anchors.sort(key=lambda x: -x[0])
        lines.append("")
        lines.append("### 风格锚点（仅参考密度与节奏，禁止抄袭句式）")
        lines.append(collected_anchors[0][1])

    if all_blacklist:
        lines.append("")
        lines.append("### AI套句黑名单（命中任意一条即需重写该句）")
        blacklist_sorted = sorted(all_blacklist)[:18]
        lines.append("  " + " / ".join(f"「{p}」" for p in blacklist_sorted))

    # 追加本书自我风格偏好（来自 memory_points_v1 审美指纹库）
    self_style = _fetch_self_style_block()
    if self_style:
        lines.append("")
        lines.append(self_style)

    lines.append("")
    return "\n".join(lines)


def list_available_authors(writer: str) -> list[str]:
    """列出写手可用的作家列表（供用户调整配比时参考）。"""
    config_data = _load_yaml(_CONFIG_PATH)
    return config_data.get("writers", {}).get(writer, {}).get("available_authors", [])


def get_current_mix(writer: str) -> dict[str, float]:
    """返回写手当前的作家配比。"""
    config_data = _load_yaml(_CONFIG_PATH)
    return config_data.get("writers", {}).get(writer, {}).get("author_mix", {})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="为众生界写手生成作家风格上下文提示",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--writer", required=True,
                        choices=["剑尘", "墨言", "云溪", "玄一", "苍澜"],
                        help="目标写手")
    parser.add_argument("--scene", required=True,
                        help="场景类型（战斗/人物/环境/悬念/世界观 等）")
    parser.add_argument("--seed", type=int, default=None,
                        help="随机种子（不指定则每次随机）")
    parser.add_argument("--list-authors", action="store_true",
                        help="列出写手可用作家，不生成风格包")
    parser.add_argument("--show-mix", action="store_true",
                        help="显示写手当前配比，不生成风格包")
    args = parser.parse_args()

    if args.list_authors:
        authors = list_available_authors(args.writer)
        print(f"\n{args.writer} 可用作家（共 {len(authors)} 位）：")
        for a in authors:
            print(f"  - {a}")
        return

    if args.show_mix:
        mix = get_current_mix(args.writer)
        print(f"\n{args.writer} 当前配比：")
        for a, w in sorted(mix.items(), key=lambda x: -x[1]):
            print(f"  {a}: {w:.0%}")
        return

    result = build_writer_style_context(args.writer, args.scene, args.seed)
    if result:
        print(result)
    else:
        print(f"[style_injector] 未能生成风格包：请检查 {_CONFIG_PATH} 和 {_STYLES_PATH}")


if __name__ == "__main__":
    main()
