#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据构建管理器 - 一键构建全部数据
==================================

新用户使用此工具构建自己的小说创作系统数据：

1. 初始化向量库（创建所有collections）
2. 同步技法数据
3. 同步设定数据
4. 构建案例库

用法：
    python data_builder.py --init                     # 初始化向量库
    python data_builder.py --sync-techniques          # 同步技法
    python data_builder.py --sync-settings            # 同步设定
    python data_builder.py --build-cases              # 构建案例库
    python data_builder.py --build-all                # 一键构建全部
    python data_builder.py --status                   # 查看状态
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 配置
import os

DEFAULT_CONFIG = {
    "qdrant_url": os.environ.get("QDRANT_URL", "http://localhost:6333"),
    "collections": {
        # 核心 Collections (v2 - BGE-M3混合检索)
        "novel_settings": "novel_settings_v2",
        "writing_techniques": "writing_techniques_v2",
        "case_library": "case_library_v2",
        # 剧情/大纲 Collections
        "novel_plot": "novel_plot_v1",  # 总大纲/剧情变更 (I19)
        "chapter_outlines": "chapter_outlines",  # 章节大纲 (I18)
        # 扩展维度 Collections (v1 - M3修复)
        "worldview_element": "worldview_element_v1",  # 世界观元素检索
        "character_relation": "character_relation_v1",  # 角色关系检索
        "author_style": "author_style_v1",  # 风格检索
        "foreshadow_pair": "foreshadow_pair_v1",  # 伏笔检索
        "power_cost": "power_cost_v1",  # 功法/力量代价检索
        "evaluation_criteria": "evaluation_criteria_v1",  # 评审标准检索
        "dialogue_style": "dialogue_style_v1",  # 对话风格检索
        "emotion_arc": "emotion_arc_v1",  # 情感弧线检索
        "power_vocabulary": "power_vocabulary_v1",  # 力量词汇检索
    },
    "vector_size": 1024,  # BGE-M3
    "model": "BAAI/bge-m3",
}


class DataBuilder:
    """数据构建管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.client = None
        self.model = None

    def _load_config(self, config_path: Optional[Path]) -> Dict:
        """加载配置"""
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_CONFIG

    def _connect_qdrant(self):
        """连接Qdrant"""
        from qdrant_client import QdrantClient

        # 尝试从统一配置获取 URL
        qdrant_url = self.config.get("qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333"))
        try:
            from core.config_loader import get_qdrant_url
            qdrant_url = get_qdrant_url()
        except ImportError:
            pass

        self.client = QdrantClient(url=qdrant_url)
        return self.client

    def _load_model(self):
        """加载嵌入模型"""
        from FlagEmbedding import BGEM3FlagModel

        model_path = self.config.get("model_path")
        if model_path:
            self.model = BGEM3FlagModel(model_path, use_fp16=True)
        else:
            # 尝试环境变量或默认路径
            import os

            cache_path = os.environ.get("BGE_M3_MODEL_PATH")
            if cache_path:
                self.model = BGEM3FlagModel(cache_path, use_fp16=True)
            else:
                self.model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        return self.model

    def init_collections(self):
        """初始化所有向量库collections"""
        from qdrant_client.http.models import VectorParams, Distance, SparseVectorParams

        print("\n" + "=" * 60)
        print("[1] 初始化向量库")
        print("=" * 60)

        self._connect_qdrant()

        collections = self.config.get("collections", DEFAULT_CONFIG["collections"])
        vector_size = self.config.get("vector_size", 1024)

        for name, collection_name in collections.items():
            try:
                info = self.client.get_collection(collection_name)
                print(f"    ✓ {collection_name} 已存在 ({info.points_count:,} 条)")
            except:
                print(f"    + 创建 {collection_name}...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=vector_size, distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={"sparse": SparseVectorParams()},
                )
                print(f"    ✓ {collection_name} 创建成功")

        print("\n向量库初始化完成!")
        return True

    def sync_techniques(self, techniques_dir: Optional[Path] = None):
        """同步技法数据"""
        print("\n" + "=" * 60)
        print("[2] 同步技法数据")
        print("=" * 60)

        # 确定技法目录
        if techniques_dir:
            tech_dir = techniques_dir
        else:
            base_path = Path(self.config.get("data_base_path", "."))
            tech_dir = base_path / self.config.get("paths", {}).get(
                "techniques", "创作技法"
            )

        if not tech_dir.exists():
            print(f"    ✗ 技法目录不存在: {tech_dir}")
            print("    请先创建技法目录并添加技法文件")
            return False

        # 连接和加载
        self._connect_qdrant()
        self._load_model()

        collection_name = self.config["collections"]["writing_techniques"]

        # 解析技法文件
        techniques = self._parse_techniques(tech_dir)

        if not techniques:
            print("    ✗ 未找到技法文件")
            return False

        print(f"    找到 {len(techniques)} 条技法")

        # 同步到向量库
        self._sync_to_collection(
            collection_name=collection_name,
            items=techniques,
            batch_size=20,
        )

        print("\n技法同步完成!")
        return True

    def sync_settings(self, settings_dir: Optional[Path] = None):
        """同步设定数据"""
        print("\n" + "=" * 60)
        print("[3] 同步设定数据")
        print("=" * 60)

        # 确定设定目录
        if settings_dir:
            settings_dir = settings_dir
        else:
            base_path = Path(self.config.get("data_base_path", "."))
            settings_dir = base_path / self.config.get("paths", {}).get(
                "settings", "设定"
            )

        if not settings_dir.exists():
            print(f"    ✗ 设定目录不存在: {settings_dir}")
            print("    请先创建设定目录并添加设定文件")
            return False

        # 连接和加载
        self._connect_qdrant()
        self._load_model()

        collection_name = self.config["collections"]["novel_settings"]

        # 解析设定文件
        settings = self._parse_settings(settings_dir)

        if not settings:
            print("    ✗ 未找到设定文件")
            return False

        print(f"    找到 {len(settings)} 条设定")

        # 同步到向量库
        self._sync_to_collection(
            collection_name=collection_name,
            items=settings,
            batch_size=20,
        )

        print("\n设定同步完成!")
        return True

    def build_case_library(
        self,
        source_dirs: Optional[List[Path]] = None,
        scene_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        """构建案例库"""
        print("\n" + "=" * 60)
        print("[4] 构建案例库")
        print("=" * 60)

        # 确定小说来源目录
        if source_dirs:
            novel_dirs = source_dirs
        else:
            novel_dirs = self.config.get("novel_sources", [])
            if not novel_dirs:
                print("    ✗ 未配置小说来源目录")
                print("    请在config.json中添加 novel_sources 配置")
                print("    或使用 --source 参数指定")
                return False

        # 验证目录存在
        valid_dirs = []
        for dir_path in novel_dirs:
            if isinstance(dir_path, str):
                dir_path = Path(dir_path)
            if dir_path.exists():
                valid_dirs.append(dir_path)
                print(f"    ✓ {dir_path}")
            else:
                print(f"    ✗ {dir_path} 不存在")

        if not valid_dirs:
            print("    ✗ 没有有效的小说来源目录")
            return False

        # 场景类型
        scenes = scene_types or self._get_default_scene_types()
        print(f"\n    场景类型: {len(scenes)} 种")
        print(f"    {' | '.join(scenes[:5])} ...")

        # 连接和加载
        self._connect_qdrant()
        self._load_model()

        collection_name = self.config["collections"]["case_library"]

        # 提取案例
        print("\n[提取案例]")
        cases = self._extract_cases(
            novel_dirs=valid_dirs,
            scene_types=scenes,
            limit=limit,
        )

        if not cases:
            print("    ✗ 未提取到案例")
            return False

        print(f"\n    提取到 {len(cases)} 条案例")

        # 同步到向量库
        print("\n[同步到向量库]")
        self._sync_to_collection(
            collection_name=collection_name,
            items=cases,
            batch_size=50,
        )

        print("\n案例库构建完成!")
        return True

    def get_status(self):
        """获取系统状态"""
        print("\n" + "=" * 60)
        print("系统状态")
        print("=" * 60)

        self._connect_qdrant()

        collections = self.config.get("collections", DEFAULT_CONFIG["collections"])

        print("\n[向量库状态]")
        for name, collection_name in collections.items():
            try:
                info = self.client.get_collection(collection_name)
                status = info.status
                count = info.points_count
                indexed = info.indexed_vectors_count
                print(f"    {collection_name}:")
                print(f"        状态: {status}")
                print(f"        数据量: {count:,}")
                print(f"        已索引: {indexed:,}")
            except:
                print(f"    {collection_name}: 未创建")

        print("\n[目录状态]")
        base_path = Path(self.config.get("data_base_path", "."))

        dirs_to_check = {
            "技法目录": self.config.get("paths", {}).get("techniques", "创作技法"),
            "设定目录": self.config.get("paths", {}).get("settings", "设定"),
            "案例目录": self.config.get("paths", {}).get(
                "case_library", ".case-library"
            ),
        }

        for name, rel_path in dirs_to_check.items():
            full_path = base_path / rel_path
            if full_path.exists():
                file_count = len(list(full_path.rglob("*.md"))) + len(
                    list(full_path.rglob("*.txt"))
                )
                print(f"    {name}: ✓ ({file_count} 文件)")
            else:
                print(f"    {name}: ✗ 不存在")

        return True

    def build_all(self):
        """一键构建全部"""
        print("\n" + "=" * 60)
        print("一键构建全部数据")
        print("=" * 60)

        # 1. 初始化向量库
        self.init_collections()

        # 2. 同步技法
        self.sync_techniques()

        # 3. 同步设定
        self.sync_settings()

        # 4. 构建案例库（可选）
        if self.config.get("novel_sources"):
            self.build_case_library()
        else:
            print("\n[4] 案例库构建 - 跳过（未配置小说来源）")
            print("    如需构建案例库，请在config.json中添加 novel_sources")

        # 5. 显示状态
        self.get_status()

        print("\n" + "=" * 60)
        print("全部构建完成!")
        print("=" * 60)
        return True

    # ========== 内部方法 ==========

    def _parse_techniques(self, tech_dir: Path) -> List[Dict]:
        """解析技法文件"""
        import re

        techniques = []

        # 扫描所有MD文件
        for md_file in tech_dir.rglob("*.md"):
            if md_file.name in ["README.md", "index.md"]:
                continue

            content = md_file.read_text(encoding="utf-8")

            # 提取维度
            dimension = None
            for part in md_file.parts:
                if part.endswith("维度"):
                    dimension = part
                    break

            # 提取技法名称
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            name = title_match.group(1) if title_match else md_file.stem

            # 提取场景
            scenes = []
            scene_pattern = re.compile(
                r"适用场景[：:]\s*([\s\S]+?)(?:核心原理|注意事项|---)", re.IGNORECASE
            )
            scene_match = scene_pattern.search(content)
            if scene_match:
                scene_text = scene_match.group(1)
                scenes = [s.strip() for s in scene_text.split("-") if s.strip()]

            techniques.append(
                {
                    "id": md_file.stem,
                    "name": name,
                    "dimension": dimension or "通用",
                    "content": content[:3000],
                    "scenes": scenes[:5],
                    "word_count": len(content),
                    "source": md_file.name,
                }
            )

        return techniques

    def _parse_settings(self, settings_dir: Path) -> List[Dict]:
        """解析设定文件"""
        import re

        settings = []

        for md_file in settings_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")

            # 提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else md_file.stem

            # 自动分类
            category = self._classify_setting(md_file.name, title, content)

            settings.append(
                {
                    "id": md_file.stem,
                    "name": title,
                    "category": category,
                    "content": content[:500],
                    "word_count": len(content),
                    "source": md_file.name,
                }
            )

        return settings

    def _classify_setting(self, filename: str, title: str, content: str) -> str:
        """自动分类设定"""
        filename_lower = filename.lower()
        title_lower = title.lower()

        categories = {
            "世界观": ["世界", "世界观", "力量", "势力", "规则"],
            "人物": ["人物", "角色", "主角", "配角", "性格"],
            "剧情": ["大纲", "剧情", "主线", "转折"],
            "其他": [],
        }

        for category, keywords in categories.items():
            if category == "其他":
                continue
            for kw in keywords:
                if kw in filename_lower or kw in title_lower:
                    return category

        return "其他"

    def _get_default_scene_types(self) -> List[str]:
        """获取默认场景类型"""
        return [
            "开篇场景",
            "人物出场",
            "战斗场景",
            "对话场景",
            "情感场景",
            "悬念场景",
            "转折场景",
            "结尾场景",
            "环境场景",
            "心理场景",
            "打脸场景",
            "高潮场景",
        ]

    def _extract_cases(
        self,
        novel_dirs: List[Path],
        scene_types: List[str],
        limit: Optional[int],
    ) -> List[Dict]:
        """提取案例（简化版本）"""
        import re

        cases = []
        total_limit = limit or 10000  # 默认限制

        # 场景关键词
        scene_keywords = {
            "开篇场景": ["第一章", "第1章", "序幕", "开篇"],
            "打脸场景": ["废物", "嘲讽", "震惊", "不可能", "跪下", "震撼"],
            "高潮场景": ["决战", "爆发", "生死", "极限", "巅峰"],
            "战斗场景": ["招", "剑", "刀", "拳", "攻击", "防御", "技能"],
            "对话场景": ['"', '"', "说道", "问道", "答道"],
            "情感场景": ["泪", "感动", "心", "情", "爱", "恨"],
        }

        # 扫描小说
        for novel_dir in novel_dirs:
            for novel_file in novel_dir.rglob("*.txt"):
                if len(cases) >= total_limit:
                    break

                try:
                    content = novel_file.read_text(encoding="utf-8", errors="ignore")
                    novel_name = novel_file.stem

                    # 按段落分割
                    paragraphs = content.split("\n\n")

                    for scene_type in scene_types:
                        keywords = scene_keywords.get(scene_type, [])

                        for para in paragraphs:
                            if len(para) < 200 or len(para) > 3000:
                                continue

                            # 检查是否匹配场景关键词
                            match_count = sum(1 for kw in keywords if kw in para)
                            if match_count >= 2:
                                cases.append(
                                    {
                                        "id": f"case_{len(cases)}",
                                        "scene_type": scene_type,
                                        "genre": "玄幻奇幻",
                                        "novel_name": novel_name,
                                        "content": para[:2000],
                                        "word_count": len(para),
                                        "quality_score": 7.0,
                                        "emotion_value": 0.5,
                                        "techniques": [],
                                        "keywords": keywords[:3],
                                    }
                                )

                                if len(cases) >= total_limit:
                                    break

                except Exception as e:
                    print(f"    ✗ {novel_file.name}: {e}")
                    continue

        return cases

    def _sync_to_collection(
        self,
        collection_name: str,
        items: List[Dict],
        batch_size: int,
    ):
        """同步数据到collection"""
        from qdrant_client.http.models import PointStruct

        print(f"\n    同步到 {collection_name}...")

        total = len(items)

        for i in range(0, total, batch_size):
            batch = items[i : i + batch_size]

            # 批量编码
            texts = [item.get("content", "") for item in batch]
            out = self.model.encode(texts, return_dense=True, return_sparse=True)

            # 创建点
            points = []
            for j, item in enumerate(batch):
                # 生成唯一ID
                item_id = hash(item.get("id", f"item_{i + j}")) % (2**31)

                point = PointStruct(
                    id=item_id,
                    vector={
                        "dense": out["dense_vecs"][j].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][j].keys()),
                            "values": list(out["lexical_weights"][j].values()),
                        },
                    },
                    payload={
                        "name": item.get("name", ""),
                        "dimension": item.get("dimension", ""),
                        "category": item.get("category", ""),
                        "scene_type": item.get("scene_type", ""),
                        "genre": item.get("genre", ""),
                        "content": item.get("content", "")[:500],
                        "word_count": item.get("word_count", 0),
                        "source": item.get("source", ""),
                        "quality_score": item.get("quality_score", 7.0),
                        "techniques": item.get("techniques", []),
                        "keywords": item.get("keywords", []),
                        "scenes": item.get("scenes", []),
                    },
                )
                points.append(point)

            self.client.upsert(collection_name, points)

            progress = min(i + batch_size, total)
            pct = progress / total * 100
            print(f"    [{pct:.0f}%] {progress}/{total}")

        # 验证
        info = self.client.get_collection(collection_name)
        print(f"\n    ✓ {collection_name}: {info.points_count:,} 条")


def main():
    parser = argparse.ArgumentParser(description="数据构建管理器")
    parser.add_argument("--config", help="配置文件路径")
    parser.add_argument("--init", action="store_true", help="初始化向量库")
    parser.add_argument("--sync-techniques", action="store_true", help="同步技法数据")
    parser.add_argument("--sync-settings", action="store_true", help="同步设定数据")
    parser.add_argument("--build-cases", action="store_true", help="构建案例库")
    parser.add_argument("--build-all", action="store_true", help="一键构建全部")
    parser.add_argument("--status", action="store_true", help="查看状态")

    # 技法/设定目录
    parser.add_argument("--techniques-dir", help="技法目录路径")
    parser.add_argument("--settings-dir", help="设定目录路径")

    # 案例库参数
    parser.add_argument("--source", nargs="+", help="小说来源目录")
    parser.add_argument("--scenes", nargs="+", help="场景类型")
    parser.add_argument("--limit", type=int, help="提取数量限制")

    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config) if args.config else None
    builder = DataBuilder(config_path)

    # 执行命令
    if args.init:
        builder.init_collections()
    elif args.sync_techniques:
        tech_dir = Path(args.techniques_dir) if args.techniques_dir else None
        builder.sync_techniques(tech_dir)
    elif args.sync_settings:
        settings_dir = Path(args.settings_dir) if args.settings_dir else None
        builder.sync_settings(settings_dir)
    elif args.build_cases:
        source_dirs = [Path(s) for s in args.source] if args.source else None
        scenes = args.scenes
        limit = args.limit
        builder.build_case_library(source_dirs, scenes, limit)
    elif args.build_all:
        builder.build_all()
    elif args.status:
        builder.get_status()
    else:
        # 默认显示帮助
        parser.print_help()
        print("\n示例:")
        print("  python data_builder.py --init              # 初始化向量库")
        print("  python data_builder.py --build-all         # 一键构建全部")
        print("  python data_builder.py --status            # 查看状态")


if __name__ == "__main__":
    main()
