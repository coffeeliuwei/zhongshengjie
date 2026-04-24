"""
BGE-M3 混合检索配置

配置说明：
- DENSE: 语义向量，用于语义相似度匹配
- SPARSE: 稀疏向量，用于关键词/术语精确匹配
- COLBERT: 多向量，用于精细语义匹配和重排序

混合检索策略：
1. 召回阶段：Dense + Sparse 并行检索，RRF融合
2. 重排阶段：ColBERT对Top-K候选重排序

存储优化：
- Dense: 使用HNSW索引，支持快速检索
- Sparse: 使用倒排索引
- ColBERT: 禁用HNSW（仅用于重排，不需要索引）
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_hf_cache_dir

# ==================== 模型配置 ====================

BGE_M3_MODEL_NAME = "BAAI/bge-m3"
# 从配置加载器获取 HuggingFace 缓存目录
BGE_M3_CACHE_DIR = get_hf_cache_dir() or "E:/huggingface_cache/hub"

# 向量维度
DENSE_VECTOR_SIZE = 1024  # Dense向量维度
COLBERT_VECTOR_SIZE = 1024  # ColBERT每token向量维度

# 编码参数
MAX_LENGTH = 8192  # 最大序列长度
BATCH_SIZE = 32  # 批处理大小
USE_FP16 = True  # 使用半精度加速

# ==================== Collection配置 ====================

COLLECTION_NAMES = {
    "novel_settings": "novel_settings_v2",  # 小说设定（混合版）
    "writing_techniques": "writing_techniques_v2",  # 创作技法（混合版）
    "case_library": "case_library_v2",  # 标杆案例（混合版）
    # 扩展维度Collection
    "worldview_element": "worldview_element_v1",  # 世界观元素
    "power_vocabulary": "power_vocabulary_v1",  # 力量词汇
    "character_relation": "character_relation_v1",  # 人物关系
    "emotion_arc": "emotion_arc_v1",  # 情感弧线
    "dialogue_style": "dialogue_style_v1",  # 对话风格
    "foreshadow_pair": "foreshadow_pair_v1",  # 伏笔配对
    "power_cost": "power_cost_v1",  # 力量代价
    "author_style": "author_style_v1",  # 作者风格
    # 新增：审核维度Collection
    "evaluation_criteria": "evaluation_criteria_v1",  # 审核维度（禁止项+技法标准+阈值）
}

# 旧Collection名（用于迁移时读取）
LEGACY_COLLECTION_NAMES = {
    "novel_settings": "novel_settings",
    "writing_techniques": "writing_techniques",
    "case_library": "case_library",
}

# ==================== 混合检索权重 ====================
# 官方论文推荐权重 (MIRACL基准测试)

HYBRID_WEIGHTS = {
    # 通用RAG场景
    "general": {
        "dense": 0.2,
        "sparse": 0.4,
        "colbert": 0.4,
    },
    # 偏语义场景（如问答）
    "semantic": {
        "dense": 0.5,
        "sparse": 0.2,
        "colbert": 0.3,
    },
    # 偏精确匹配（如产品搜索）
    "exact": {
        "dense": 0.2,
        "sparse": 0.6,
        "colbert": 0.2,
    },
    # 仅Dense（快速检索）
    "dense_only": {
        "dense": 1.0,
        "sparse": 0.0,
        "colbert": 0.0,
    },
}

# 默认权重
DEFAULT_WEIGHT_PRESET = "general"

# ==================== 检索参数 ====================

RETRIEVAL_CONFIG = {
    # 召回阶段参数
    "recall": {
        "dense_limit": 100,  # Dense召回数量
        "sparse_limit": 100,  # Sparse召回数量
        "fusion_limit": 50,  # RRF融合后数量
    },
    # 重排阶段参数
    "rerank": {
        "enabled": True,  # 是否启用ColBERT重排
        "colbert_limit": 20,  # ColBERT重排后返回数量
    },
    # 默认返回数量
    "default_top_k": 10,
}

# ==================== Qdrant Collection配置模板 ====================


def get_collection_config():
    """
    获取支持混合检索的Collection配置

    Returns:
        Dict: Qdrant Collection配置
    """
    from qdrant_client import models

    return {
        "vectors_config": {
            # Dense向量：语义检索
            "dense": models.VectorParams(
                size=DENSE_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
            # ColBERT多向量：重排序
            "colbert": models.VectorParams(
                size=COLBERT_VECTOR_SIZE,
                distance=models.Distance.COSINE,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                # 关键：禁用HNSW节省内存（ColBERT用于重排，不需要索引）
                hnsw_config=models.HnswConfigDiff(m=0),
            ),
        },
        # Sparse向量：关键词检索
        "sparse_vectors_config": {"sparse": models.SparseVectorParams()},
    }


def get_hybrid_query(
    dense_vector: list,
    sparse_indices: list,
    sparse_values: list,
    colbert_vectors: list,
    weights: dict = None,
    recall_config: dict = None,
):
    """
    构建混合检索查询

    Args:
        dense_vector: Dense向量 (1024维)
        sparse_indices: Sparse向量索引
        sparse_values: Sparse向量值
        colbert_vectors: ColBERT多向量 (List[List[float]])
        weights: 权重配置
        recall_config: 召回配置

    Returns:
        Qdrant Query对象
    """
    from qdrant_client import models

    if weights is None:
        weights = HYBRID_WEIGHTS[DEFAULT_WEIGHT_PRESET]

    if recall_config is None:
        recall_config = RETRIEVAL_CONFIG["recall"]

    # 构建Sparse向量
    sparse_vector = models.SparseVector(indices=sparse_indices, values=sparse_values)

    # 两阶段混合检索
    # 阶段1: Dense + Sparse 并行召回，RRF融合
    # 阶段2: ColBERT 重排

    return models.FusionQuery(
        fusion=models.Fusion.RRF,
        prefetch=[
            # Dense召回
            models.Prefetch(
                query=dense_vector,
                using="dense",
                limit=recall_config["dense_limit"],
            ),
            # Sparse召回
            models.Prefetch(
                query=sparse_vector,
                using="sparse",
                limit=recall_config["sparse_limit"],
            ),
        ],
        limit=recall_config["fusion_limit"],
    )


# ==================== 迁移配置 ====================

MIGRATION_CONFIG = {
    # 是否删除旧Collection
    "delete_legacy": False,
    # 是否备份旧数据
    "backup_legacy": True,
    # 备份目录
    "backup_dir": ".vectorstore/backup",
    # 批处理大小
    "batch_size": 64,
    # 是否显示进度条
    "show_progress": True,
}

# ==================== 验证配置 ====================

VALIDATION_CONFIG = {
    # 测试查询
    "test_queries": [
        "林夕的角色设定",
        "血脉力量体系",
        "战斗场景描写技巧",
        "开篇高潮案例",
    ],
    # 期望返回数量
    "expected_top_k": 5,
    # 最低相似度阈值
    "min_score_threshold": 0.3,
}
