#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检索质量交叉验证工具"""

import math


def ndcg_at_5(scores: list[int]) -> float:
    """计算 nDCG@5，scores 为 [0,1,2] 列表，长度 5"""
    dcg = sum(s / math.log2(i + 2) for i, s in enumerate(scores))
    ideal = sorted(scores, reverse=True)
    idcg = sum(s / math.log2(i + 2) for i, s in enumerate(ideal))
    return round(dcg / idcg, 4) if idcg > 0 else 0.0


def precision_at_5(scores: list[int]) -> float:
    """Precision@5，得分 >= 1 视为相关"""
    return round(sum(1 for s in scores if s >= 1) / 5, 4)
