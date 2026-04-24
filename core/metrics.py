# core/metrics.py
"""Prometheus 监控指标模块

为小说创作系统提供性能监控指标，支持 Prometheus 抓取和可视化。

用法:
    from core.metrics import RETRIEVAL_COUNTER, RETRIEVAL_LATENCY
    
    # 记录检索
    RETRIEVAL_COUNTER.labels(source="technique", dimension="战斗冲突维度").inc()
    
    # 记录延迟
    with RETRIEVAL_LATENCY.labels(source="technique").time():
        # 检索逻辑...
        pass

启动 Prometheus 服务:
    from core.metrics import start_metrics_server
    start_metrics_server(9090)  # 在端口 9090 启动
"""

import os
from typing import Optional

# Prometheus 客户端可选依赖
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # 创建空占位符，避免导入错误
    Counter = None
    Histogram = None
    Gauge = None
    start_http_server = None


# ==================== 检索指标 ====================

if PROMETHEUS_AVAILABLE:
    # 检索请求计数
    RETRIEVAL_COUNTER = Counter(
        'retrieval_requests_total',
        '检索请求总数',
        ['source', 'dimension']
    )

    # 检索延迟（秒）
    RETRIEVAL_LATENCY = Histogram(
        'retrieval_latency_seconds',
        '检索延迟（秒）',
        ['source'],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
    )

    # 检索结果数量
    RETRIEVAL_RESULTS = Histogram(
        'retrieval_results_count',
        '检索结果数量分布',
        ['source'],
        buckets=[1, 3, 5, 10, 20, 50, 100]
    )
else:
    RETRIEVAL_COUNTER = None
    RETRIEVAL_LATENCY = None
    RETRIEVAL_RESULTS = None


# ==================== 创作指标 ====================

if PROMETHEUS_AVAILABLE:
    # 章节创作计数
    CHAPTER_WRITTEN = Counter(
        'chapters_written_total',
        '已创作章节总数'
    )

    # 场景创作计数
    SCENE_CREATED = Counter(
        'scenes_created_total',
        '已创作场景总数',
        ['scene_type']
    )

    # 创作字数
    WORDS_WRITTEN = Counter(
        'words_written_total',
        '已创作字数总数'
    )
else:
    CHAPTER_WRITTEN = None
    SCENE_CREATED = None
    WORDS_WRITTEN = None


# ==================== 评估指标 ====================

if PROMETHEUS_AVAILABLE:
    # 评估分数分布
    EVALUATION_SCORE = Histogram(
        'evaluation_score',
        '评估分数分布',
        ['dimension'],
        buckets=[0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0]
    )

    # 评估次数
    EVALUATION_COUNT = Counter(
        'evaluation_requests_total',
        '评估请求总数',
        ['chapter', 'result']  # result: pass/fail/retry
    )

    # 推翻事件
    AUTHOR_FORCE_PASS = Counter(
        'author_force_pass_total',
        '作者推翻评估次数'
    )
else:
    EVALUATION_SCORE = None
    EVALUATION_COUNT = None
    AUTHOR_FORCE_PASS = None


# ==================== 系统健康指标 ====================

if PROMETHEUS_AVAILABLE:
    # Qdrant 健康状态
    QDRANT_HEALTH = Gauge(
        'qdrant_healthy',
        'Qdrant 健康状态 (1=健康, 0=不可用)'
    )

    # Qdrant 集合数量
    QDRANT_COLLECTIONS = Gauge(
        'qdrant_collections_count',
        'Qdrant 集合数量'
    )

    # 记忆点数量
    MEMORY_POINTS_COUNT = Gauge(
        'memory_points_total',
        '记忆点总数'
    )
else:
    QDRANT_HEALTH = None
    QDRANT_COLLECTIONS = None
    MEMORY_POINTS_COUNT = None


# ==================== 工作流指标 ====================

if PROMETHEUS_AVAILABLE:
    # 工作流阶段耗时
    WORKFLOW_STAGE_LATENCY = Histogram(
        'workflow_stage_latency_seconds',
        '工作流各阶段耗时（秒）',
        ['stage'],
        buckets=[1, 5, 10, 30, 60, 120, 300, 600]
    )

    # 工作流阶段计数
    WORKFLOW_STAGE_COUNT = Counter(
        'workflow_stage_total',
        '工作流各阶段执行次数',
        ['stage', 'result']  # result: success/fail
    )
else:
    WORKFLOW_STAGE_LATENCY = None
    WORKFLOW_STAGE_COUNT = None


# ==================== 辅助函数 ====================

def start_metrics_server(port: int = 9090) -> bool:
    """启动 Prometheus HTTP 服务
    
    Args:
        port: 监听端口，默认 9090
    
    Returns:
        True 表示启动成功，False 表示 Prometheus 不可用
    """
    if not PROMETHEUS_AVAILABLE:
        return False
    
    try:
        start_http_server(port)
        return True
    except Exception as e:
        print(f"[metrics] 启动 Prometheus 服务失败: {e}")
        return False


def get_metrics_port() -> int:
    """从环境变量获取 Prometheus 端口
    
    Returns:
        端口号，默认 9090
    """
    return int(os.environ.get("PROMETHEUS_PORT", "9090"))


def record_retrieval(
    source: str,
    dimension: Optional[str] = None,
    latency_seconds: float = 0.0,
    results_count: int = 0
) -> None:
    """记录一次检索的指标
    
    Args:
        source: 数据源 (novel/technique/case)
        dimension: 技法维度（可选）
        latency_seconds: 检索延迟（秒）
        results_count: 返回结果数量
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    # 计数
    if dimension:
        RETRIEVAL_COUNTER.labels(source=source, dimension=dimension).inc()
    else:
        RETRIEVAL_COUNTER.labels(source=source, dimension="unknown").inc()
    
    # 延迟
    RETRIEVAL_LATENCY.labels(source=source).observe(latency_seconds)
    
    # 结果数量
    RETRIEVAL_RESULTS.labels(source=source).observe(results_count)


def record_evaluation(
    dimension: str,
    score: float,
    chapter: str = "",
    result: str = "pass"
) -> None:
    """记录一次评估的指标
    
    Args:
        dimension: 评估维度
        score: 评估分数 (0-1)
        chapter: 章节名
        result: 结果 (pass/fail/retry)
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    EVALUATION_SCORE.labels(dimension=dimension).observe(score)
    if chapter:
        EVALUATION_COUNT.labels(chapter=chapter, result=result).inc()


def update_qdrant_health(healthy: bool) -> None:
    """更新 Qdrant 健康状态
    
    Args:
        healthy: 是否健康
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    QDRANT_HEALTH.set(1 if healthy else 0)


def update_qdrant_collections(count: int) -> None:
    """更新 Qdrant 集合数量
    
    Args:
        count: 集合数量
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    QDRANT_COLLECTIONS.set(count)


def record_workflow_stage(
    stage: str,
    latency_seconds: float,
    success: bool = True
) -> None:
    """记录工作流阶段执行
    
    Args:
        stage: 阶段名 (stage_1, stage_2, ...)
        latency_seconds: 耗时（秒）
        success: 是否成功
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    WORKFLOW_STAGE_LATENCY.labels(stage=stage).observe(latency_seconds)
    WORKFLOW_STAGE_COUNT.labels(stage=stage, result="success" if success else "fail").inc()