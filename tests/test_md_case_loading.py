"""
验证 sync_to_qdrant._load_md_cases_from_directory 能正确解析
novel-paste-extract / novel-inspiration-ingest 产出的 .md 案例文件。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / ".case-library" / "scripts"))


def _make_syncer(tmp_path, monkeypatch):
    """构造一个 QdrantSyncer，将 CASES_DIR 指向 tmp_path。"""
    import importlib
    import sync_to_qdrant as stq

    monkeypatch.setattr(stq, "CASES_DIR", tmp_path)
    importlib.reload  # noqa
    return stq.QdrantSyncer(use_docker=False)


def test_parses_paste_extract_md(tmp_path, monkeypatch):
    sub = tmp_path / "99-从小说提取" / "03-人物维度"
    sub.mkdir(parents=True)
    md = sub / "2026-04-24-paste-1-a.md"
    md.write_text(
        """---
title: 侧写式出场
dimension: 03-人物维度
applicable_scene: 人物初登场
source: 素材库/2026-04-24-paste-1/source.md
created_at: "2026-04-24 15:00 Asia/Shanghai"
---

# 侧写式出场

## 原文

他从雾中走出，黑袍覆体，唯有一双眼睛像冷铁般折射出月光。
身后三步之外，空气仿佛被某种看不见的压力压得微微扭曲。
没人敢开口，连风都在他脚下绕路。

## 为什么值得学习

通过环境反应侧写角色威压，不直写强弱。
""",
        encoding="utf-8",
    )

    syncer = _make_syncer(tmp_path, monkeypatch)
    cases = syncer._load_md_cases_from_directory()

    assert len(cases) == 1
    c = cases[0]
    assert c.scene_type == "人物初登场"
    assert c.genre == "03-人物维度"
    assert c.novel_name == "2026-04-24-paste-1"
    assert "黑袍覆体" in c.content
    assert "为什么值得学习" not in c.content  # 只提取"## 原文"段
    assert c.quality_score == 7.5
    assert c.case_id.startswith("md_")


def test_skips_too_short(tmp_path, monkeypatch):
    sub = tmp_path / "99-从小说提取" / "08-情感维度"
    sub.mkdir(parents=True)
    md = sub / "short.md"
    md.write_text(
        """---
title: 短案
dimension: 08-情感维度
---

## 原文

太短。
""",
        encoding="utf-8",
    )

    syncer = _make_syncer(tmp_path, monkeypatch)
    cases = syncer._load_md_cases_from_directory()
    assert cases == []


def test_handles_md_without_frontmatter(tmp_path, monkeypatch):
    sub = tmp_path / "99-从小说提取"
    sub.mkdir(parents=True)
    md = sub / "no_fm.md"
    md.write_text(
        """# 未加frontmatter的案例

这是一段作为正文的内容，描述了主角在雨夜中独行的场景。
他的靴子踩过积水，倒影被震碎又复合。
街灯昏黄，映照出他沉默的侧脸。
""",
        encoding="utf-8",
    )

    syncer = _make_syncer(tmp_path, monkeypatch)
    cases = syncer._load_md_cases_from_directory()

    assert len(cases) == 1
    assert "雨夜" in cases[0].content
    # 一级标题应被去掉
    assert "未加frontmatter" not in cases[0].content


def test_empty_directory_returns_empty_list(tmp_path, monkeypatch):
    syncer = _make_syncer(tmp_path, monkeypatch)
    cases = syncer._load_md_cases_from_directory()
    assert cases == []
