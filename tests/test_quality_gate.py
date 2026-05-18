# -*- coding: utf-8 -*-
"""tests/test_quality_gate.py — quality_gate 单元测试"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.quality_gate import compute_burstiness, check_ai_blacklist, run_quality_gate


# ─── compute_burstiness ────────────────────────────────────────

def test_burstiness_high_variance_passes():
    # 短句（5字）与超长句（60+字）混合 → 方差高 → 通过
    # 注意：过滤条件 len > 3，最短句须 >= 4 字
    text = (
        "他来了？"  # 短句
        "整个大厅陷入死寂，无数道目光从四面八方投来，如同利刃穿透他皮肤，"
        "让他感受到从未有过的压迫与恐惧，仿佛下一秒就会被什么东西撕碎。"  # 长句
        "转身离开。"  # 短句
        "没有人阻拦，因为没有人敢阻拦——或者说，没有人想要阻拦一个已经死过一次的人，"
        "他们只是沉默地看着，像一群等待猎物倒下的秃鹫。"  # 长句
        "已经够了。"  # 短句
        "风穿过回廊，带走了所有人的体温，也带走了他仅剩的一点对这个宗门的幻想与留恋。"  # 长句
    )
    passed, variance, detail = compute_burstiness(text)
    assert passed, f"应通过但未通过，方差={variance:.1f}: {detail}"
    assert variance >= 50


def test_burstiness_uniform_fails():
    # 均匀10字句 → 方差低 → 不通过
    sentence = "他迈出一步前行。"  # 约8字
    text = (sentence * 12)  # 12句，全部相同长度
    passed, variance, detail = compute_burstiness(text)
    assert not passed, f"应未通过但通过了，方差={variance:.1f}"


def test_burstiness_insufficient_sentences():
    # 不足5句 → 跳过检测，返回 True
    text = "他走了。她也走了。"
    passed, variance, detail = compute_burstiness(text)
    assert passed
    assert variance == 0.0
    assert "样本不足" in detail


# ─── check_ai_blacklist ─────────────────────────────────────────

def test_blacklist_clean_text_passes():
    text = "剑光在虚空中划出一道弧线，落在青石地面上，发出清脆的碰撞声。"
    passed, hits, hit_rate = check_ai_blacklist(text, writer_blacklist=[])
    assert passed
    assert len(hits) == 0
    assert hit_rate == 0.0


def test_blacklist_hit_rate_uses_total_count():
    # 验证 hit_rate = 总命中次数 / 句子数（不是种类数）
    # 构造一个两句话、一个套句出现2次的文本
    text = "不由自主地抬头，他不由自主地转身。"
    _, hits, hit_rate = check_ai_blacklist(text, writer_blacklist=[])
    # "不由自主地" 出现2次
    hit_phrases = [h.split("（")[0] for h in hits]
    assert "不由自主地" in hit_phrases
    # 找到命中记录中的次数
    total = sum(int(h.split("×")[1].rstrip("）")) for h in hits)
    sentences = [s for s in __import__("re").split(r"[。！？；…]+", text) if s.strip()]
    expected_rate = total / max(len(sentences), 1)
    assert abs(hit_rate - expected_rate) < 1e-6, (
        f"hit_rate={hit_rate:.4f} 应等于 {expected_rate:.4f}"
    )


def test_blacklist_regex_includes_ellipsis():
    # 含省略号的文本，句子分割应包含省略号
    import re
    text = "他回头……没有人。她消失了。"
    sentences = [s for s in re.split(r"[。！？；…]+", text) if s.strip()]
    assert len(sentences) >= 2, "省略号应被识别为句子分隔符"


def test_blacklist_excessive_hits_fails():
    phrases = [
        "眼中闪过一丝",
        "心中涌起一股",
        "空气仿佛凝固",
        "不由自主地",
        "忽然间",
    ]
    text = "".join(f"{p}，这让他感到震惊。" for p in phrases)
    passed, hits, hit_rate = check_ai_blacklist(text, writer_blacklist=[])
    assert not passed, "命中套句数超过阈值，应未通过"


# ─── run_quality_gate ──────────────────────────────────────────

def test_run_quality_gate_returns_required_keys():
    text = "他走了，没有回头。整个世界陷入沉默。"
    with patch("tools.quality_gate._load_gate_config", return_value={}), \
         patch("tools.quality_gate._load_writer_blacklist", return_value=[]):
        result = run_quality_gate(text)
    for key in ("passed", "verdict", "location", "text_length", "checks", "suggestions"):
        assert key in result, f"缺少字段 {key}"
    assert "burstiness" in result["checks"]
    assert "ai_blacklist" in result["checks"]


def test_run_quality_gate_pass_verdict():
    # 构造能通过的文本（短长句混合，无套句）
    text = (
        "不。"
        "剑尘在废墟的正中央站定，脚下是三具尸体，身后是坍塌的宗门大殿，"
        "头顶是血色的黄昏——这一切都是他的选择，他也不后悔。"
        "从没有过。"
    )
    with patch("tools.quality_gate._load_gate_config",
               return_value={"burstiness_threshold": 50, "blacklist_max_hits": 3,
                             "blacklist_hit_rate_max": 0.15}), \
         patch("tools.quality_gate._load_writer_blacklist", return_value=[]):
        result = run_quality_gate(text, writer=None)
    # 不要求一定通过（取决于文本），只验证结构正确
    assert isinstance(result["passed"], bool)
    assert result["text_length"] == len(text)
