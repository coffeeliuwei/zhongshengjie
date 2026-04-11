"""
作家上下文管理器
使用向量数据库存储作家输出上下文，解决对话历史累积问题
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

from sentence_transformers import SentenceTransformer


@dataclass
class WriterOutput:
    """作家输出数据结构"""

    output_id: str  # 输出唯一ID
    session_id: str  # 会话ID
    chapter_name: str  # 章节名称
    scene_type: str  # 场景类型
    phase: str  # 执行Phase（前置/核心/收尾）
    writer_name: str  # 作家名称
    writer_skill: str  # 作家技能名称
    content: str  # 输出内容
    timestamp: str  # 时间戳
    iteration: int  # 迭代次数（0为初次创作）
    evaluation_score: Optional[Dict[str, int]] = None  # 评估分数
    evaluation_feedback: Optional[str] = None  # 评估反馈
    metadata: Dict[str, Any] = None  # 元数据

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class WriterContextManager:
    """
    作家上下文管理器

    功能：
    1. 存储作家输出到向量数据库（creation_context集合）
    2. 检索历史上下文（按session/chapter/scene过滤）
    3. 管理迭代历史（支持迭代追踪）
    4. 清理过期上下文（自动清理策略）
    """

    COLLECTION_NAME = "creation_context"

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        embedder_model: str = "all-MiniLM-L6-v2",
        max_context_entries: int = 100,
        auto_cleanup_days: int = 30,
    ):
        """
        初始化作家上下文管理器

        Args:
            qdrant_host: Qdrant主机地址
            qdrant_port: Qdrant端口
            embedder_model: 向量嵌入模型名称
            max_context_entries: 最大上下文条数
            auto_cleanup_days: 自动清理天数
        """
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client未安装，请运行: pip install qdrant-client")

        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.embedder = SentenceTransformer(embedder_model)

        self.max_context_entries = max_context_entries
        self.auto_cleanup_days = auto_cleanup_days

        # 确保集合存在
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """确保creation_context集合存在"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.COLLECTION_NAME not in collection_names:
            # 创建集合
            vector_size = self.embedder.get_sentence_embedding_dimension()
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            print(f"✅ 创建集合: {self.COLLECTION_NAME}")

    def _generate_output_id(self, output: WriterOutput) -> str:
        """
        生成输出唯一ID

        Args:
            output: 作家输出对象

        Returns:
            唯一ID字符串
        """
        # 使用session + chapter + scene + phase + writer + timestamp生成唯一ID
        key = f"{output.session_id}_{output.chapter_name}_{output.scene_type}_{output.phase}_{output.writer_name}_{output.timestamp}"
        return hashlib.md5(key.encode()).hexdigest()

    def _embed_content(self, content: str) -> List[float]:
        """
        将内容转换为向量

        Args:
            content: 文本内容

        Returns:
            向量列表
        """
        embedding = self.embedder.encode(content)
        return embedding.tolist()

    def save_writer_output(self, output: WriterOutput) -> str:
        """
        保存作家输出到向量数据库

        Args:
            output: 作家输出对象

        Returns:
            输出ID
        """
        # 生成唯一ID
        output.output_id = self._generate_output_id(output)

        # 嵌入内容向量
        vector = self._embed_content(output.content)

        # 构建payload（存储所有元数据）
        payload = asdict(output)

        # 创建向量点
        point = PointStruct(id=output.output_id, vector=vector, payload=payload)

        # 上传到Qdrant
        self.client.upsert(collection_name=self.COLLECTION_NAME, points=[point])

        print(
            f"✅ 保存作家输出: {output.writer_name} - {output.scene_type} - Phase {output.phase}"
        )

        return output.output_id

    def retrieve_context(
        self,
        session_id: Optional[str] = None,
        chapter_name: Optional[str] = None,
        scene_type: Optional[str] = None,
        phase: Optional[str] = None,
        writer_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[WriterOutput]:
        """
        检索历史上下文

        Args:
            session_id: 会话ID过滤
            chapter_name: 章节名称过滤
            scene_type: 场景类型过滤
            phase: Phase过滤
            writer_name: 作家名称过滤
            limit: 返回条数限制

        Returns:
            作家输出列表
        """
        # 构建过滤条件
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = []
        if session_id:
            conditions.append(
                FieldCondition(key="session_id", match=MatchValue(value=session_id))
            )
        if chapter_name:
            conditions.append(
                FieldCondition(key="chapter_name", match=MatchValue(value=chapter_name))
            )
        if scene_type:
            conditions.append(
                FieldCondition(key="scene_type", match=MatchValue(value=scene_type))
            )
        if phase:
            conditions.append(
                FieldCondition(key="phase", match=MatchValue(value=phase))
            )
        if writer_name:
            conditions.append(
                FieldCondition(key="writer_name", match=MatchValue(value=writer_name))
            )

        # 搜索
        filter_obj = Filter(must=conditions) if conditions else None

        results = self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            filter=filter_obj,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        # 转换为WriterOutput对象
        outputs = []
        for point in results[0]:
            output_data = point.payload
            outputs.append(WriterOutput(**output_data))

        return outputs

    def search_similar_context(
        self,
        query_content: str,
        chapter_name: Optional[str] = None,
        scene_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[WriterOutput]:
        """
        搜索相似上下文（向量相似度搜索）

        Args:
            query_content: 查询内容
            chapter_name: 章节名称过滤
            scene_type: 场景类型过滤
            limit: 返回条数限制

        Returns:
            相似的作家输出列表
        """
        # 嵌入查询内容
        query_vector = self._embed_content(query_content)

        # 构建过滤条件
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        conditions = []
        if chapter_name:
            conditions.append(
                FieldCondition(key="chapter_name", match=MatchValue(value=chapter_name))
            )
        if scene_type:
            conditions.append(
                FieldCondition(key="scene_type", match=MatchValue(value=scene_type))
            )

        filter_obj = Filter(must=conditions) if conditions else None

        # 向量搜索
        results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_vector,
            filter=filter_obj,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        # 转换为WriterOutput对象
        outputs = []
        for result in results:
            output_data = result.payload
            outputs.append(WriterOutput(**output_data))

        return outputs

    def get_iteration_history(
        self, session_id: str, chapter_name: str, scene_type: str
    ) -> List[WriterOutput]:
        """
        获取迭代历史

        Args:
            session_id: 会话ID
            chapter_name: 章节名称
            scene_type: 场景类型

        Returns:
            迭代历史列表（按迭代次数排序）
        """
        outputs = self.retrieve_context(
            session_id=session_id,
            chapter_name=chapter_name,
            scene_type=scene_type,
            limit=self.max_context_entries,
        )

        # 按迭代次数排序
        outputs.sort(key=lambda x: x.iteration)

        return outputs

    def cleanup_old_context(self) -> int:
        """
        清理过期上下文

        Returns:
            清理的条数
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=self.auto_cleanup_days)
        cutoff_str = cutoff_date.isoformat()

        # 搜索过期条目
        results = self.client.scroll(
            collection_name=self.COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False,
        )

        # 筛选过期条目
        expired_ids = []
        for point in results[0]:
            timestamp = point.payload.get("timestamp", "")
            if timestamp and timestamp < cutoff_str:
                expired_ids.append(point.id)

        # 删除过期条目
        if expired_ids:
            self.client.delete(
                collection_name=self.COLLECTION_NAME, points_selector=expired_ids
            )
            print(f"✅ 清理过期上下文: {len(expired_ids)}条")

        return len(expired_ids)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取上下文存储统计

        Returns:
            统计信息字典
        """
        collection_info = self.client.get_collection(self.COLLECTION_NAME)

        return {
            "collection_name": self.COLLECTION_NAME,
            "total_entries": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "max_context_entries": self.max_context_entries,
            "auto_cleanup_days": self.auto_cleanup_days,
        }


# 使用示例
if __name__ == "__main__":
    # 初始化管理器
    manager = WriterContextManager()

    # 创建作家输出示例
    output = WriterOutput(
        session_id="session_001",
        chapter_name="第一章-天裂",
        scene_type="战斗场景",
        phase="核心",
        writer_name="剑尘",
        writer_skill="novelist-jianchen",
        content="血牙挥舞战刀，熊血脉的力量在体内奔涌...",
        iteration=0,
    )

    # 保存输出
    output_id = manager.save_writer_output(output)

    # 检索上下文
    context = manager.retrieve_context(
        chapter_name="第一章-天裂", scene_type="战斗场景"
    )

    print(f"检索到 {len(context)} 条上下文")

    # 获取统计
    stats = manager.get_stats()
    print(f"统计: {stats}")
