# core/inspiration/status_reporter.py
"""灵感引擎状态查询响应

供 inspiration_status_query 意图调用，生成可直接呈现给作者的状态报告文本。

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md §8.4 类型 5
"""

from typing import Optional

from core.inspiration.memory_point_sync import MemoryPointSync

# N5修复：导入配置读取
from core.config_loader import get_config


def _get_thresholds():
    """从配置获取阈值"""
    cfg = get_config()
    inspiration_cfg = cfg.get("inspiration_engine", {})
    return (
        inspiration_cfg.get("appraisal_cold_start_threshold", 50),
        inspiration_cfg.get("appraisal_growing_threshold", 300),
    )


def report_status(sync: Optional[MemoryPointSync] = None) -> str:
    """生成状态报告文本

    Args:
        sync: MemoryPointSync 实例；为 None 时自动创建（URL via get_qdrant_url()）

    Returns:
        可直接呈现给作者的多行文本
    """
    if sync is None:
        sync = MemoryPointSync()

    # N5修复：从配置读取阈值
    cold_threshold, growing_threshold = _get_thresholds()

    try:
        total = sync.count()
    except Exception:
        total = 0

    try:
        overturn_count = sync.count_overturn_events()
    except Exception:
        overturn_count = 0

    if total < cold_threshold:
        phase = "冷启动"
        phase_desc = "鉴赏师纯靠 LLM 直感判断，未注入参照样本"
    elif total < growing_threshold:
        phase = "成长期"
        phase_desc = "鉴赏师注入 top 3 相关记忆点作为参照"
    else:
        phase = "成熟期"
        phase_desc = "鉴赏师注入 top 5 + 结构特征摘要，直觉降级为 tiebreaker"

    return (
        f"【灵感引擎状态】\n"
        f"  · 累计记忆点：{total} 条\n"
        f"  · 推翻事件：{overturn_count} 条\n"
        f"  · 鉴赏师当前阶段：{phase}\n"
        f"  · 行为：{phase_desc}\n"
    )
