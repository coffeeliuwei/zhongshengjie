"""验证 CaseBuilder 在提炼时跳过近重复。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_filter_near_duplicate_cases(tmp_path):
    from tools.case_builder import CaseBuilder, Case
    from tools.dedup_utils import compute_minhash, create_lsh, save_lsh

    # 预先建一个 LSH 索引，里面已有一条内容
    existing_text = "萧炎凝视远方，目光坚毅。他深知这一战必须赢。" * 5
    lsh, cache = create_lsh()
    m = compute_minhash(existing_text)
    lsh.insert("existing_case", m)
    cache["existing_case"] = m

    idx_path = tmp_path / "dedup_index.pkl"
    save_lsh(lsh, cache, idx_path)

    # 构造 builder
    builder = CaseBuilder.__new__(CaseBuilder)
    builder.case_library_dir = tmp_path
    builder.index_file = tmp_path / "idx.json"

    # 两条候选案例：一条近重复，一条全新
    dup_case = Case(
        case_id="dup_1", scene_type="战斗场景", genre="玄幻奇幻",
        novel_name="test", content=existing_text, word_count=len(existing_text),
        quality_score=7.0, emotion_value=5.0, techniques=[], keywords=[],
        source_file="test.txt",
    )
    new_case = Case(
        case_id="new_1", scene_type="战斗场景", genre="玄幻奇幻",
        novel_name="test", content="春风拂面，柳絮纷飞，少女驻足河畔。" * 5,
        word_count=100, quality_score=7.0, emotion_value=5.0,
        techniques=[], keywords=[], source_file="test.txt",
    )

    filtered, stats = builder._filter_near_duplicates(
        [dup_case, new_case], index_path=idx_path,
    )

    assert len(filtered) == 1
    assert filtered[0].case_id == "new_1"
    assert stats["skipped"] == 1
    assert stats["kept"] == 1


def test_no_index_file_keeps_all(tmp_path):
    """索引文件不存在时，所有案例都保留，并建立新索引。"""
    from tools.case_builder import CaseBuilder, Case

    builder = CaseBuilder.__new__(CaseBuilder)
    builder.case_library_dir = tmp_path

    cases = [
        Case(
            case_id=f"c_{i}", scene_type="开篇场景", genre="玄幻奇幻",
            novel_name="test", content=f"内容{i} " * 30,
            word_count=120, quality_score=7.0, emotion_value=5.0,
            techniques=[], keywords=[], source_file="test.txt",
        )
        for i in range(3)
    ]

    idx_path = tmp_path / "dedup_index.pkl"
    filtered, stats = builder._filter_near_duplicates(cases, index_path=idx_path)

    assert len(filtered) == 3
    assert stats["skipped"] == 0
    assert idx_path.exists()   # 新建并保存了索引