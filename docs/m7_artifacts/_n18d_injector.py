"""
[N18d 2026-04-19] skill 标记注入器(事后补建,仅作审计痕迹)

本脚本记录首次 N18cd 执行时**应当使用的**注入逻辑与注入内容模板。
首次执行中 opencode 绕过脚本直接修改了 4 个 SKILL.md,本脚本在 N18cd-PATCH
阶段事后补写,以固化"注入了什么内容、遵循什么规则"的审计事实。

本脚本在补建时已完成使命,**不应再次运行**:当前 4 个 SKILL.md 已含正确标记,
再次运行会因幂等保护而全部 SKIP。

运行方式(仅供参考,补建后不必执行):
    python docs/m7_artifacts/_n18d_injector.py

参考计划:
    docs/计划_N18cd_worldview核验与4skill清理_20260419.md (首次)
    docs/计划_N18cd_patch补做_20260419.md              (补建)
"""
from pathlib import Path
import sys

SKILLS_ROOT = Path(r"C:/Users/39477/.agents/skills")

NOTE_GENERIC = """
> **[N18d 2026-04-19] 12 skill 清理口径**
>
> 本 skill 已纳入 v2 §6 第 3 步"12 skill 全清理"范围。
> 2026-04-19 核验:**无** `.vectorstore/core` 死引用、**无** `from modules.creation`
> 死引用、**无** M2-β 重构后的路径/符号冲突。skill 与当前代码库兼容,无需修改功能内容。
> 参见:`docs/计划_N18cd_worldview核验与4skill清理_20260419.md` Part B。
"""

NOTE_CONNOISSEUR = """
> **[N18d 2026-04-19] 12 skill 清理口径 + P1-3 待重写占位**
>
> 本 skill 已纳入 v2 §6 第 3 步"12 skill 全清理"范围。
> 2026-04-19 核验:**无** `.vectorstore/core` 死引用、**无** `from modules.creation`
> 死引用、**无** M2-β 冲突。
>
> ⚠️ **重要**:本 skill 将由 **P1-3**(见 `docs/ROADMAP_众生界v2实施_20260419.md` §3.2)
> 大改为 v2"创意注入器 + 派单监工"角色。当前 v1"选最活的"描述**仅临时保留**,
> 请勿基于当前内容构建下游依赖。
> 参见:`docs/计划_N18cd_worldview核验与4skill清理_20260419.md` Part B。
"""

TARGETS = [
    ("novel-inspiration-ingest", NOTE_GENERIC),
    ("novelist-connoisseur",     NOTE_CONNOISSEUR),
    ("novelist-shared",          NOTE_GENERIC),
    ("novelist-technique-search", NOTE_GENERIC),
]


def inject(skill_name: str, note: str) -> str:
    f = SKILLS_ROOT / skill_name / "SKILL.md"
    if not f.is_file():
        return f"FAIL:missing {f}"
    text = f.read_text(encoding="utf-8")
    if "[N18d 2026-04-19]" in text:
        return "SKIPPED(已含标记)"
    if not text.startswith("---"):
        return "FAIL:frontmatter missing opening ---"
    second = text.find("\n---", 3)
    if second == -1:
        return "FAIL:frontmatter missing closing ---"
    insert_pos = text.find("\n", second + 1) + 1
    new_text = text[:insert_pos] + note + text[insert_pos:]
    tmp = f.with_suffix(".md.tmp")
    tmp.write_text(new_text, encoding="utf-8", newline="\n")
    tmp.replace(f)
    return "INJECTED"


if __name__ == "__main__":
    results = []
    for name, note in TARGETS:
        r = inject(name, note)
        print(f"{name:35s} {r}")
        results.append((name, r))
    fails = [r for r in results if r[1].startswith("FAIL")]
    sys.exit(1 if fails else 0)