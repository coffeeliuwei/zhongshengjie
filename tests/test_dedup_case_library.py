"""存量清理工具测试"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _write_case(dir_: Path, case_id: str, content: str) -> Path:
    """辅助：写一对 json+txt 案例文件。"""
    dir_.mkdir(parents=True, exist_ok=True)
    jp = dir_ / f"{case_id}.json"
    tp = dir_ / f"{case_id}.txt"
    jp.write_text(
        json.dumps({"case_id": case_id, "content": content}, ensure_ascii=False),
        encoding="utf-8",
    )
    tp.write_text(content, encoding="utf-8")
    return jp


def test_exact_duplicate_archived(tmp_path):
    from tools.dedup_case_library import run_dedup

    cases_dir = tmp_path / "cases" / "战斗场景"
    text = "萧炎凝视远方，体内斗气奔涌。" * 10
    _write_case(cases_dir, "case_001", text)
    _write_case(cases_dir, "case_002", text)  # 完全相同
    _write_case(cases_dir, "case_003", "春风拂面，柳絮纷飞，少女驻足河畔。" * 10)

    archive_dir = tmp_path / "_duplicates_archive"
    index_path = tmp_path / "dedup_index.pkl"

    stats = run_dedup(
        cases_root=tmp_path / "cases",
        archive_root=archive_dir,
        index_path=index_path,
        dry_run=False,
    )

    assert stats["total"] == 3
    assert stats["duplicates"] == 1
    assert stats["kept"] == 2
    # 被归档的文件应在 archive_dir
    archived_files = list(archive_dir.rglob("*.json"))
    assert len(archived_files) == 1
    # 保留文件应仍在原处
    kept_ids = {p.stem for p in (tmp_path / "cases").rglob("*.json")}
    assert "case_001" in kept_ids or "case_002" in kept_ids
    assert "case_003" in kept_ids
    # 索引应已保存
    assert index_path.exists()


def test_dry_run_does_not_move_files(tmp_path):
    from tools.dedup_case_library import run_dedup

    cases_dir = tmp_path / "cases" / "开篇场景"
    text = "他仰望星空，心中一片澄明。" * 10
    _write_case(cases_dir, "case_a", text)
    _write_case(cases_dir, "case_b", text)

    archive_dir = tmp_path / "_duplicates_archive"
    stats = run_dedup(
        cases_root=tmp_path / "cases",
        archive_root=archive_dir,
        index_path=tmp_path / "dedup_index.pkl",
        dry_run=True,
    )

    assert stats["duplicates"] == 1
    # 文件仍在原位
    assert len(list((tmp_path / "cases").rglob("*.json"))) == 2
    # 归档目录不应被创建
    assert not archive_dir.exists() or not any(archive_dir.rglob("*.json"))


def test_txt_sibling_moved_together(tmp_path):
    from tools.dedup_case_library import run_dedup

    cases_dir = tmp_path / "cases" / "情感场景"
    text = "她站在窗前，望着远方。" * 10
    _write_case(cases_dir, "case_x", text)
    _write_case(cases_dir, "case_y", text)

    archive_dir = tmp_path / "_duplicates_archive"
    run_dedup(
        cases_root=tmp_path / "cases",
        archive_root=archive_dir,
        index_path=tmp_path / "dedup_index.pkl",
        dry_run=False,
    )

    # 被归档文件的 .txt 同名兄弟也应一起移走
    archived_json = list(archive_dir.rglob("*.json"))
    assert len(archived_json) == 1
    archived_stem = archived_json[0].stem
    archived_txt = archived_json[0].with_suffix(".txt")
    assert archived_txt.exists()