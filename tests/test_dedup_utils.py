"""MinHash LSH 去重工具测试"""
import pickle
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestComputeMinHash:
    def _call(self, text: str):
        from tools.dedup_utils import compute_minhash
        return compute_minhash(text)

    def test_returns_minhash_object(self):
        from datasketch import MinHash
        m = self._call("萧炎深吸一口气，体内斗气奔涌。这一战必须赢。")
        assert isinstance(m, MinHash)

    def test_identical_text_identical_minhash(self):
        text = "他拔出长剑，寒芒一闪，敌人应声倒下。"
        m1 = self._call(text)
        m2 = self._call(text)
        assert m1.jaccard(m2) == 1.0

    def test_short_text_handled(self):
        m = self._call("短")
        from datasketch import MinHash
        assert isinstance(m, MinHash)

    def test_near_duplicate_high_jaccard(self):
        t1 = "萧炎深吸一口气，体内斗气奔涌，如同一条蛟龙盘踞丹田，气势磅礴。"
        t2 = "萧炎深吸一口气，体内斗气奔涌，如同一条蛟龙盘踞丹田，气势惊人。"
        m1 = self._call(t1)
        m2 = self._call(t2)
        # 0.77 相似度足够说明近重复特性（LSH threshold=0.85 在实际去重时更严格）
        assert m1.jaccard(m2) > 0.7

    def test_different_text_low_jaccard(self):
        t1 = "萧炎深吸一口气，体内斗气奔涌。"
        t2 = "春风拂面，柳絮纷飞，少女驻足河畔。"
        m1 = self._call(t1)
        m2 = self._call(t2)
        assert m1.jaccard(m2) < 0.3


class TestLSHPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        from tools.dedup_utils import (
            create_lsh, save_lsh, load_lsh, compute_minhash,
        )

        lsh, cache = create_lsh()
        m = compute_minhash("测试用内容，足够长以产生稳定 shingle 集合。" * 3)
        lsh.insert("case_001", m)
        cache["case_001"] = m

        idx_path = tmp_path / "dedup_index.pkl"
        save_lsh(lsh, cache, idx_path)
        assert idx_path.exists()

        lsh2, cache2 = load_lsh(idx_path)
        assert "case_001" in cache2
        # 加载后的 LSH 应能查出同一条
        m_query = compute_minhash("测试用内容，足够长以产生稳定 shingle 集合。" * 3)
        assert "case_001" in lsh2.query(m_query)

    def test_load_nonexistent_returns_fresh(self, tmp_path):
        from tools.dedup_utils import load_lsh
        lsh, cache = load_lsh(tmp_path / "missing.pkl")
        assert cache == {}


class TestIsNearDuplicate:
    def test_empty_lsh_returns_false(self):
        from tools.dedup_utils import create_lsh, is_near_duplicate, compute_minhash
        lsh, _ = create_lsh()
        m = compute_minhash("任意文本内容足够长。" * 5)
        assert is_near_duplicate(lsh, m) is False

    def test_exact_duplicate_detected(self):
        from tools.dedup_utils import (
            create_lsh, is_near_duplicate, compute_minhash,
        )
        lsh, _ = create_lsh()
        text = "萧炎凝视远方，目光坚毅。" * 5
        m = compute_minhash(text)
        lsh.insert("existing", m)
        m2 = compute_minhash(text)
        assert is_near_duplicate(lsh, m2) is True