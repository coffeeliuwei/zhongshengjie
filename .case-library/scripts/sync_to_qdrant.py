#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
案例同步到Qdrant向量数据库
===========================

将所有案例同步到Qdrant，支持语义检索。

使用方法：
    python sync_to_qdrant.py              # 同步全部（本地模式）
    python sync_to_qdrant.py --docker     # 同步到Docker Qdrant
    python sync_to_qdrant.py --limit 1000 # 测试同步
    python sync_to_qdrant.py --stats      # 查看状态
    python sync_to_qdrant.py --docker --no-resume  # Docker模式完整同步
"""

import os
import sys
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

# Windows编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 配置
PROJECT_DIR = Path(__file__).parent.parent.parent
CASE_LIBRARY_DIR = PROJECT_DIR / ".case-library"
CASES_DIR = CASE_LIBRARY_DIR / "cases"
VECTORSTORE_DIR = PROJECT_DIR / ".vectorstore"
QDRANT_DIR = VECTORSTORE_DIR / "qdrant"
LOGS_DIR = CASE_LIBRARY_DIR / "logs"

# 确保目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "qdrant_sync.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Qdrant配置
COLLECTION_NAME = "case_library_v2"
VECTOR_SIZE = 384


@dataclass
class CaseForSync:
    """待同步案例"""

    case_id: str
    scene_type: str
    genre: str
    novel_name: str
    content: str
    word_count: int
    quality_score: float
    emotion_value: float
    techniques: List[str]
    keywords: List[str]
    writers: List[str]


class QdrantSyncer:
    """Qdrant同步器（支持断点续传和Docker模式）"""

    def __init__(self, use_docker: bool = False):
        self.client = None
        self.model = None
        self.existing_ids = set()  # 已同步的case_id
        self.use_docker = use_docker  # Docker模式开关
        self.sync_stats = {
            "start_time": None,
            "end_time": None,
            "total_cases": 0,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "mode": "docker" if use_docker else "local",
        }

    def _get_existing_ids(self) -> set:
        """获取Qdrant中已存在的case_id集合"""
        if not self._init_client():
            return set()

        try:
            from qdrant_client.http.models import Filter

            existing = set()
            offset = None
            batch_count = 0

            print("检查已同步的案例（断点续传）...")
            if self.use_docker:
                print("Docker模式：遍历速度更快，预计几秒钟完成...")
            else:
                print("本地模式：遍历31万向量点需要1-2分钟，请耐心等待...")

            while True:
                # 批量获取点（每次1000个）
                result, offset = self.client.scroll(
                    collection_name=COLLECTION_NAME,
                    limit=1000,
                    offset=offset,
                    with_payload=["case_id"],
                    with_vectors=False,
                )

                for point in result:
                    if point.payload and "case_id" in point.payload:
                        existing.add(point.payload["case_id"])

                batch_count += 1
                if batch_count % 50 == 0:  # 每5万个点输出一次
                    print(f"  已扫描: {len(existing):,} 个案例...")

                if offset is None:
                    break

            print(f"已同步案例数: {len(existing):,}")
            return existing

        except Exception as e:
            logger.warning(f"获取已存在ID失败: {e}")
            return set()

    def _init_client(self):
        """初始化Qdrant客户端（支持本地模式和Docker模式）"""
        if self.client is None:
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http.models import Distance, VectorParams

                # Docker模式：连接到localhost:6333
                # 本地模式：使用文件存储
                if self.use_docker:
                    logger.info("连接Docker Qdrant: http://localhost:6333")
                    self.client = QdrantClient(url="http://localhost:6333")
                else:
                    logger.info(f"使用本地模式: {QDRANT_DIR}")
                    QDRANT_DIR.mkdir(parents=True, exist_ok=True)
                    self.client = QdrantClient(path=str(QDRANT_DIR))

                # 创建集合（如果不存在）
                collections = self.client.get_collections().collections
                collection_names = [c.name for c in collections]

                if COLLECTION_NAME not in collection_names:
                    logger.info(f"创建Qdrant集合: {COLLECTION_NAME}")
                    self.client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=VECTOR_SIZE, distance=Distance.COSINE
                        ),
                    )
                    logger.info("集合创建完成")

                return True
            except ImportError:
                logger.error("请安装 qdrant-client: pip install qdrant-client")
                return False
            except Exception as e:
                logger.error(f"Qdrant初始化失败: {e}")
                return False
        return True

    def _init_model(self):
        """初始化嵌入模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("加载嵌入模型...")
                self.model = SentenceTransformer(
                    "paraphrase-multilingual-MiniLM-L12-v2"
                )
                logger.info("嵌入模型加载完成")
                return True
            except ImportError:
                logger.error(
                    "请安装 sentence-transformers: pip install sentence-transformers"
                )
                return False
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                return False
        return True

    def _load_cases_from_directory(self, limit: int = None) -> List[CaseForSync]:
        """从cases目录加载案例（使用rglob遍历所有JSON）"""
        cases = []

        logger.info("扫描cases目录（使用rglob遍历所有JSON）...")

        # 使用rglob遍历所有JSON文件
        for json_file in CASES_DIR.rglob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 读取内容：优先从JSON的content字段读取，否则读取txt文件
                content = data.get("content", "")

                # 如果JSON没有content，尝试读取txt文件
                if not content:
                    txt_file = json_file.with_suffix(".txt")
                    if txt_file.exists():
                        with open(txt_file, "r", encoding="utf-8") as f:
                            content = f.read()

                if not content:
                    continue

                # 从路径和文件名提取scene_type和genre
                # 路径格式: cases/scene_type/case_xxx.json
                # 文件名格式: scene_type_genre_novel-author.json
                rel_path = json_file.relative_to(CASES_DIR)
                parts = rel_path.parts

                # 提取scene_type（去除编号前缀）
                raw_scene_type = parts[0] if len(parts) > 0 else "未知"
                scene_type = (
                    raw_scene_type.split("-", 1)[-1]
                    if "-" in raw_scene_type
                    else raw_scene_type
                )

                # 从文件名提取genre
                filename = json_file.stem
                filename_parts = filename.split("_")
                genre = filename_parts[1] if len(filename_parts) >= 2 else "未知"

                case = CaseForSync(
                    case_id=data.get("case_id", json_file.stem),
                    scene_type=data.get("scene", {}).get(
                        "type", data.get("scene_type", scene_type)
                    ),
                    genre=data.get("source", {}).get("genre", genre),
                    novel_name=data.get("source", {}).get("novel_name", "未知"),
                    content=content,
                    word_count=data.get("scene", {}).get("word_count", len(content)),
                    quality_score=data.get("quality", {}).get("overall_score", 7.0),
                    emotion_value=data.get("quality", {}).get("emotion_value", 5.0),
                    techniques=data.get("tags", {}).get("techniques", []),
                    keywords=data.get("tags", {}).get("keywords", []),
                    writers=data.get("tags", {}).get("recommended_writers", []),
                )

                cases.append(case)

                if limit and len(cases) >= limit:
                    return cases

            except Exception as e:
                logger.warning(f"读取案例失败: {json_file.name} - {e}")

        logger.info(f"共加载 {len(cases)} 个案例")
        return cases

    def sync(
        self, limit: int = None, batch_size: int = 100, resume: bool = True
    ) -> Dict:
        """同步案例到Qdrant（支持断点续传）"""
        print("=" * 60)
        print("同步案例到Qdrant向量数据库")
        print("=" * 60)

        self.sync_stats["start_time"] = datetime.now().isoformat()

        # 初始化
        if not self._init_client():
            return {"error": "Qdrant初始化失败"}
        if not self._init_model():
            return {"error": "模型初始化失败"}

        # 断点续传：获取已同步的case_id
        skipped = 0
        if resume:
            self.existing_ids = self._get_existing_ids()
        else:
            self.existing_ids = set()

        # 加载案例
        all_cases = self._load_cases_from_directory(limit)

        # 过滤已同步的案例
        if resume and self.existing_ids:
            cases = [c for c in all_cases if c.case_id not in self.existing_ids]
            skipped = len(all_cases) - len(cases)
            print(f"跳过已同步: {skipped} 个")
        else:
            cases = all_cases

        total = len(cases)

        if total == 0:
            print("没有需要同步的案例")
            return {"synced": 0, "skipped": skipped, "total": 0}

        print(f"\n待同步案例: {total} 个（已跳过 {skipped} 个）")

        # 批量生成嵌入
        print("\n生成嵌入向量...")
        from qdrant_client.http.models import PointStruct

        synced = 0
        failed = 0
        points = []

        # 分批处理
        for i in range(0, total, batch_size):
            batch = cases[i : i + batch_size]
            texts = [c.content[:2000] for c in batch]  # 限制长度

            try:
                # 生成嵌入
                embeddings = self.model.encode(texts, show_progress_bar=True)

                # 创建点
                for case, embedding in zip(batch, embeddings):
                    try:
                        # 生成UUID（基于case_id的确定性UUID）
                        case_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, case.case_id))

                        point = PointStruct(
                            id=case_uuid,
                            vector=embedding.tolist(),
                            payload={
                                "case_id": case.case_id,
                                "scene_type": case.scene_type,
                                "genre": case.genre,
                                "novel_name": case.novel_name,
                                "word_count": case.word_count,
                                "quality_score": case.quality_score,
                                "emotion_value": case.emotion_value,
                                "techniques": case.techniques,
                                "keywords": case.keywords,
                                "writers": case.writers,
                                "content_preview": case.content[:500],
                            },
                        )
                        points.append(point)

                    except Exception as e:
                        failed += 1
                        logger.warning(f"创建点失败: {case.case_id} - {e}")

                # 批量上传
                if len(points) >= batch_size:
                    try:
                        self.client.upsert(
                            collection_name=COLLECTION_NAME, points=points
                        )
                        synced += len(points)
                        print(f"进度: {synced}/{total}")
                        points = []
                    except Exception as e:
                        logger.error(f"批量上传失败: {e}")
                        failed += len(points)
                        points = []

            except Exception as e:
                logger.error(f"嵌入生成失败: {e}")
                failed += len(batch)

        # 上传剩余点
        if points:
            try:
                self.client.upsert(collection_name=COLLECTION_NAME, points=points)
                synced += len(points)
            except Exception as e:
                logger.error(f"最后批次上传失败: {e}")
                failed += len(points)

        # 更新统计
        self.sync_stats["end_time"] = datetime.now().isoformat()
        self.sync_stats["total_cases"] = total
        self.sync_stats["synced"] = synced
        self.sync_stats["failed"] = failed
        self.sync_stats["skipped"] = skipped

        # 保存日志
        self._save_sync_log()

        print(f"\n同步完成!")
        print(f"  成功: {synced}")
        print(f"  失败: {failed}")
        print(f"  跳过: {skipped}")
        print(f"  待同步: {total}")

        return {"synced": synced, "failed": failed, "skipped": skipped, "total": total}

    def _save_sync_log(self):
        """保存同步日志"""
        log_file = LOGS_DIR / "qdrant_sync_log.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(self.sync_stats, f, ensure_ascii=False, indent=2)

    def get_stats(self) -> Dict:
        """获取Qdrant状态"""
        if not self._init_client():
            return {"error": "Qdrant未初始化"}

        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return {
                "collection_name": COLLECTION_NAME,
                "total_points": info.points_count,
                "status": info.status.value,
            }
        except Exception as e:
            return {"error": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="同步案例到Qdrant（支持断点续传）")
    parser.add_argument("--limit", type=int, default=None, help="限制同步数量")
    parser.add_argument("--batch-size", type=int, default=100, help="批量大小")
    parser.add_argument("--stats", action="store_true", help="查看状态")
    parser.add_argument(
        "--docker", action="store_true", help="使用Docker模式连接Qdrant"
    )
    parser.add_argument(
        "--no-resume", action="store_true", help="禁用断点续传，重新同步所有案例"
    )

    args = parser.parse_args()

    syncer = QdrantSyncer(use_docker=args.docker)

    if args.stats:
        stats = syncer.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    else:
        resume = not args.no_resume
        syncer.sync(limit=args.limit, batch_size=args.batch_size, resume=resume)


if __name__ == "__main__":
    main()
