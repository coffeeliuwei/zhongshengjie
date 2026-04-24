"""
MinHash LSH 近重复检测工具
==========================

为 case_builder.py（增量提炼去重）和 dedup_case_library.py（存量清理）
提供统一的 MinHash LSH 接口，共享同一份持久化索引
`.case-library/dedup_index.pkl`。

shingle 策略：连续 5 字符窗口，取内容前 2000 字符（平衡精度与速度）
num_perm=128（datasketch 默认，与 threshold=0.85 配合召回率 ~95%）
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Tuple

from datasketch import MinHash, MinHashLSH

NUM_PERM = 128
LSH_THRESHOLD = 0.85
SHINGLE_SIZE = 5
MAX_CHARS = 2000


def compute_minhash(text: str) -> MinHash:
    """为一段文本计算 MinHash 指纹。"""
    m = MinHash(num_perm=NUM_PERM)
    if not text:
        return m
    snippet = text[:MAX_CHARS]
    if len(snippet) < SHINGLE_SIZE:
        m.update(snippet.encode("utf-8", errors="ignore"))
        return m
    shingles = {snippet[k:k + SHINGLE_SIZE] for k in range(len(snippet) - SHINGLE_SIZE + 1)}
    for s in shingles:
        m.update(s.encode("utf-8", errors="ignore"))
    return m


def create_lsh() -> Tuple[MinHashLSH, Dict[str, MinHash]]:
    """新建空的 LSH 紟引 + minhash 缓存（用于后续持久化）。"""
    return MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM), {}


def save_lsh(lsh: MinHashLSH, cache: Dict[str, MinHash], path: Path) -> None:
    """保存 LSH 紟引 + minhash 缓存到 pickle 文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump({"lsh": lsh, "cache": cache}, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_lsh(path: Path) -> Tuple[MinHashLSH, Dict[str, MinHash]]:
    """从 pickle 文件加载 LSH 紟引；不存在则返回空索引。"""
    path = Path(path)
    if not path.exists():
        return create_lsh()
    try:
        with path.open("rb") as f:
            obj = pickle.load(f)
        return obj["lsh"], obj["cache"]
    except Exception:
        return create_lsh()


def is_near_duplicate(lsh: MinHashLSH, minhash: MinHash) -> bool:
    """判断 minhash 是否与 lsh 中已有条目近重复。"""
    return bool(lsh.query(minhash))