# core/inspiration/embedder.py
"""BGE-M3 embedding 封装

懒加载模型（首次调用时加载），避免启动时加载耗时。
复用 file_updater.py 中已验证的 FlagEmbedding 集成模式。

设计文档：docs/superpowers/plans/2026-04-15-embedding-integration.md
"""

from typing import List, Optional

from core.config_loader import get_model_path

_MODEL = None  # 懒加载单例


def _load_model():
    """加载 BGE-M3 模型（首次调用）"""
    global _MODEL
    from FlagEmbedding import BGEM3FlagModel

    model_path = get_model_path()
    if not model_path:
        raise RuntimeError(
            "BGE-M3 模型路径未配置，请检查 config.json 或环境变量 BGE_M3_MODEL_PATH"
        )
    from core.config_loader import get_device
    _MODEL = BGEM3FlagModel(model_path, use_fp16=True, device=get_device(verbose=False))
    return _MODEL


def _get_model():
    """获取模型实例（懒加载）"""
    global _MODEL
    if _MODEL is None:
        _MODEL = _load_model()
    return _MODEL


def embed_text(text: str) -> List[float]:
    """将文本编码为 1024 维 dense vector

    Args:
        text: 待编码文本（空字符串时返回零向量，避免崩溃）

    Returns:
        List[float]，长度 1024
    """
    if not text or not text.strip():
        return [0.0] * 1024

    model = _get_model()
    output = model.encode(
        [text],
        batch_size=1,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    vector = output["dense_vecs"][0]
    return [float(v) for v in vector]


def embed_scene_context(scene_context: dict) -> List[float]:
    """将场景上下文 dict 拼接为文本后编码

    拼接顺序：scene_type + 其余字段值
    """
    parts = []
    if "scene_type" in scene_context:
        parts.append(str(scene_context["scene_type"]))
    for k, v in scene_context.items():
        if k != "scene_type":
            parts.append(str(v))
    text = " ".join(parts)
    return embed_text(text)
