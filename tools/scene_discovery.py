#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动场景发现工具
================

从大量小说片段中自动识别新的场景模式，生成新场景类型配置。

核心流程：
1. 收集无法归类的片段（对所有现有场景关键词匹配数<2）
2. 使用BGE-M3语义向量聚类相似片段
3. 从聚类中心提取高频关键词
4. 生成新场景类型配置
5. 自动更新SCENE_TYPES和scene_writer_mapping.json

用法：
    python scene_discovery.py --analyze                    # 分析未归类片段
    python scene_discovery.py --discover                   # 发现新场景类型
    python scene_discovery.py --apply                      # 应用新场景到配置
    python scene_discovery.py --full                       # 完整流程
"""

import argparse
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from collections import Counter
import numpy as np

# 导入现有配置
try:
    from case_builder import SCENE_TYPES, GENRE_KEYWORDS, Case, CaseBuilder
except ImportError:
    # 定义备用场景类型
    SCENE_TYPES = {}
    GENRE_KEYWORDS = {}


# ============================================================
# 配置
# ============================================================

# 聚类参数
CLUSTER_CONFIG = {
    "min_cluster_size": 10,  # 最小聚类大小（片段数）
    "max_clusters": 20,  # 最大发现新场景数
    "similarity_threshold": 0.75,  # 聚类相似度阈值
    "keyword_min_freq": 3,  # 关键词最小出现次数
    "keyword_top_k": 8,  # 提取关键词数量
}

# 新场景默认配置
NEW_SCENE_DEFAULTS = {
    "position": "any",
    "min_len": 300,
    "max_len": 2000,
}

# BGE-M3 向量维度
VECTOR_SIZE = 1024


# ============================================================
# 数据结构
# ============================================================


@dataclass
class UnclassifiedFragment:
    """未归类片段"""

    fragment_id: str
    content: str
    novel_name: str
    genre: str
    word_count: int
    quality_score: float
    source_file: str
    matched_keywords: List[str]  # 最佳匹配场景的关键词
    best_scene_match: str  # 最佳匹配场景类型
    match_score: float  # 最佳匹配分数


@dataclass
class DiscoveredScene:
    """发现的新场景类型"""

    scene_name: str
    keywords: List[str]
    description: str
    fragments: List[str]  # 代表性片段ID
    fragment_count: int
    avg_quality: float
    avg_similarity: float
    confidence: float  # 发现置信度
    genre_distribution: Dict[str, int]
    suggested_status: str  # active/pending_activation/can_activate
    created_at: str


# ============================================================
# 关键词提取器
# ============================================================


class KeywordExtractor:
    """关键词提取器 - 从文本片段中提取高频关键词"""

    # 常见停用词（中文小说领域）
    STOPWORDS = {
        "的",
        "了",
        "是",
        "在",
        "有",
        "和",
        "与",
        "就",
        "也",
        "都",
        "这",
        "那",
        "他",
        "她",
        "它",
        "我",
        "你",
        "们",
        "自己",
        "一个",
        "一些",
        "什么",
        "怎么",
        "为什么",
        "如何",
        "可以",
        "可能",
        "应该",
        "必须",
        "需要",
        "已经",
        "正在",
        "将要",
        "曾经",
        "非常",
        "很",
        "太",
        "更",
        "最",
        "不过",
        "但是",
        "然而",
        "虽然",
        "因为",
        "所以",
        "如果",
        "只要",
        "一",
        "二",
        "三",
        "四",
        "五",
        "六",
        "七",
        "八",
        "九",
        "十",
        "上",
        "下",
        "左",
        "右",
        "前",
        "后",
        "里",
        "外",
        "中",
        "来",
        "去",
        "到",
        "从",
        "向",
        "往",
        "说",
        "道",
        "想",
        "看",
        "听",
        "做",
        "走",
        "跑",
        "站",
        "坐",
        "时",
        "候",
        "年",
        "月",
        "日",
        "天",
        "点",
        "分",
        "秒",
        "人",
        "物",
        "事",
        "情",
        "地",
        "方",
        "处",
    }

    # 现有场景关键词（避免重复）
    EXISTING_KEYWORDS: Set[str] = set()

    def __init__(self, existing_scene_types: Dict = None):
        if existing_scene_types:
            for scene_config in existing_scene_types.values():
                self.EXISTING_KEYWORDS.update(scene_config.get("keywords", []))

    def extract_keywords(
        self, fragments: List[str], top_k: int = 8, min_freq: int = 3
    ) -> List[Tuple[str, int]]:
        """
        从片段中提取高频关键词

        Args:
            fragments: 文本片段列表
            top_k: 提取关键词数量
            min_freq: 最小出现次数

        Returns:
            [(关键词, 出现次数), ...]
        """
        # 合并所有片段
        all_text = " ".join(fragments)

        # 中文分词（简单实现：基于常见词边界）
        # 提取2-4字词组
        words = []

        # 提取标点分隔的短语
        phrases = re.split(r"[，。！？；：、\s]+", all_text)
        for phrase in phrases:
            phrase = phrase.strip()
            if 2 <= len(phrase) <= 4:
                words.append(phrase)

        # 提取特定模式的关键词
        patterns = [
            r"(\w{2,4})(?:着|了|过)",  # 动词相关
            r"(?:被|把|让|使)(\w{2,4})",  # 被动/使动
            r"(\w{2,3})(?:之|于|为)",  # 古风表达
            r"(?:忽然|突然|瞬间)(\w{2,4})",  # 时间转折
            r"(\w{2,4})(?:感|觉|悟)",  # 心理相关
            r"(?:心中|内心|脑海)(\w{2,4})",  # 心理场景
        ]

        for pattern in patterns:
            matches = re.findall(pattern, all_text)
            words.extend(matches)

        # 统计词频
        word_counts = Counter(words)

        # 过滤停用词和现有关键词
        filtered = []
        for word, count in word_counts.items():
            if word not in self.STOPWORDS:
                if word not in self.EXISTING_KEYWORDS:
                    if count >= min_freq:
                        filtered.append((word, count))

        # 按频率排序，取top_k
        filtered.sort(key=lambda x: -x[1])
        return filtered[:top_k]

    def generate_scene_name(self, keywords: List[str]) -> str:
        """
        根据关键词生成场景名称

        Args:
            keywords: 关键词列表

        Returns:
            场景名称
        """
        # 预定义的场景名称模板
        name_templates = [
            "{action}场景",  # 动作类
            "{emotion}场景",  # 情感类
            "{object}场景",  # 对象类
            "{state}状态",  # 状态类
            "{event}事件",  # 事件类
        ]

        # 分析关键词类型
        action_words = ["走", "跑", "飞", "追", "逃", "寻", "探", "行"]
        emotion_words = ["惊", "喜", "悲", "怒", "惧", "疑", "惑", "期待"]

        # 尝试生成名称
        for kw in keywords[:3]:
            # 检查是否包含动作词
            for aw in action_words:
                if aw in kw:
                    return kw + "场景"

            # 检查是否包含情感词
            for ew in emotion_words:
                if ew in kw:
                    return kw + "场景"

        # 默认使用第一个关键词
        if keywords:
            return keywords[0] + "场景"

        return "新场景类型"


# ============================================================
# 聚类引擎
# ============================================================


class ClusteringEngine:
    """语义聚类引擎 - 使用BGE-M3向量聚类相似片段"""

    def __init__(self, model_path: str = None):
        self._model = None
        self._model_path = model_path

    def _load_model(self):
        """懒加载BGE-M3模型"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
                from core.config_loader import get_model_path, get_device

                model_path = self._model_path or get_model_path()
                self._model = BGEM3FlagModel(model_path, use_fp16=True, device=get_device())
            except ImportError:
                print("请安装 FlagEmbedding: pip install FlagEmbedding")
                return None
            except Exception as e:
                print(f"加载BGE-M3模型失败: {e}")
                return None
        return self._model

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        获取文本嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量矩阵 (n_texts, 1024)
        """
        model = self._load_model()
        if model is None:
            return np.zeros((len(texts), VECTOR_SIZE))

        try:
            out = model.encode(texts, return_dense=True)
            return np.array(out["dense_vecs"])
        except Exception as e:
            print(f"生成嵌入失败: {e}")
            return np.zeros((len(texts), VECTOR_SIZE))

    def cluster_fragments(
        self,
        fragments: List[UnclassifiedFragment],
        min_cluster_size: int = 10,
        similarity_threshold: float = 0.75,
        max_clusters: int = 20,
    ) -> List[List[UnclassifiedFragment]]:
        """
        聚类未归类片段

        Args:
            fragments: 未归类片段列表
            min_cluster_size: 最小聚类大小
            similarity_threshold: 相似度阈值
            max_clusters: 最大聚类数

        Returns:
            聚类结果列表 [[片段, ...], ...]
        """
        if len(fragments) < min_cluster_size:
            print(f"片段数量不足: {len(fragments)} < {min_cluster_size}")
            return []

        print(f"\n开始聚类 {len(fragments)} 个未归类片段...")

        # 获取嵌入向量
        texts = [f.content for f in fragments]
        embeddings = self.get_embeddings(texts)

        # 使用简单的凝聚聚类（Agglomerative Clustering）
        from sklearn.cluster import AgglomerativeClustering

        # 计算相似度矩阵
        # 余弦相似度 = 1 - 余弦距离
        from sklearn.metrics.pairwise import cosine_similarity

        similarity_matrix = cosine_similarity(embeddings)

        # 转换为距离矩阵
        distance_matrix = 1 - similarity_matrix

        # 聚类
        n_clusters = min(max_clusters, len(fragments) // min_cluster_size)

        clustering = AgglomerativeClustering(
            n_clusters=n_clusters, metric="precomputed", linkage="average"
        )

        labels = clustering.fit_predict(distance_matrix)

        # 按标签分组
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(fragments[i])

        # 过滤太小或相似度不足的聚类
        valid_clusters = []
        for label, cluster_fragments in clusters.items():
            if len(cluster_fragments) < min_cluster_size:
                continue

            # 计算聚类内平均相似度
            cluster_indices = [fragments.index(f) for f in cluster_fragments]
            cluster_similarities = []
            for i in cluster_indices:
                for j in cluster_indices:
                    if i < j:
                        cluster_similarities.append(similarity_matrix[i, j])

            avg_sim = np.mean(cluster_similarities) if cluster_similarities else 0

            if avg_sim >= similarity_threshold:
                valid_clusters.append(cluster_fragments)
                print(
                    f"  聚类 {label}: {len(cluster_fragments)} 片段, 平均相似度 {avg_sim:.2f}"
                )

        return valid_clusters


# ============================================================
# 场景发现器
# ============================================================


class SceneDiscovery:
    """自动场景发现器"""

    def __init__(
        self,
        case_library_dir: Path,
        config: Optional[Dict] = None,
        scene_types: Dict = None,
    ):
        self.case_library_dir = case_library_dir
        self.config = config or CLUSTER_CONFIG

        # 使用传入或默认场景类型
        self.scene_types = scene_types or SCENE_TYPES

        # 工具实例
        self.keyword_extractor = KeywordExtractor(self.scene_types)
        self.clustering_engine = ClusteringEngine()

        # 输出目录
        self.discovery_dir = case_library_dir / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)

        # 输出文件
        self.unclassified_file = self.discovery_dir / "unclassified_fragments.json"
        self.discovered_file = self.discovery_dir / "discovered_scenes.json"
        self.stats_file = self.discovery_dir / "discovery_stats.json"

    def collect_unclassified_fragments(
        self, converted_dir: Path, limit: int = 5000
    ) -> List[UnclassifiedFragment]:
        """
        收集无法归类的片段

        Args:
            converted_dir: 转换后的小说文件目录
            limit: 最大收集数量

        Returns:
            未归类片段列表
        """
        print("\n" + "=" * 60)
        print("收集未归类片段")
        print("=" * 60)

        unclassified = []

        novel_files = list(converted_dir.glob("*.txt"))
        print(f"扫描 {len(novel_files)} 个小说文件...")

        for novel_file in novel_files:
            if len(unclassified) >= limit:
                break

            try:
                content = novel_file.read_text(encoding="utf-8", errors="ignore")
                novel_name = novel_file.stem

                # 检测题材
                genre = self._detect_genre(content[:5000])

                # 分割段落
                paragraphs = self._split_paragraphs(content)

                for para in paragraphs:
                    if len(unclassified) >= limit:
                        break

                    # 长度检查
                    if not (300 <= len(para) <= 3000):
                        continue

                    # 检查所有场景类型的匹配度
                    best_match = self._find_best_scene_match(para)

                    # 如果最佳匹配分数 < 2（关键词匹配数），则归为未归类
                    if best_match["match_count"] < 2:
                        # 计算质量分
                        quality_score = self._calculate_quality(
                            para, best_match["match_count"]
                        )

                        if quality_score >= 6.0:
                            fragment = UnclassifiedFragment(
                                fragment_id=hashlib.md5(para.encode()).hexdigest()[:12],
                                content=para[:2000],
                                novel_name=novel_name,
                                genre=genre,
                                word_count=len(para),
                                quality_score=quality_score,
                                source_file=novel_file.name,
                                matched_keywords=best_match["matched_keywords"][:5],
                                best_scene_match=best_match["scene_type"],
                                match_score=best_match["match_count"],
                            )
                            unclassified.append(fragment)

            except Exception as e:
                print(f"  ✗ {novel_file.name}: {e}")

        print(f"\n收集完成: {len(unclassified)} 个未归类片段")

        # 保存结果
        self._save_unclassified(unclassified)

        return unclassified

    def _detect_genre(self, content: str) -> str:
        """检测题材"""
        scores = {}
        for genre, keywords in GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            scores[genre] = score

        if scores:
            best = max(scores, key=scores.get)
            if scores[best] >= 3:
                return best

        return "玄幻奇幻"

    def _split_paragraphs(self, content: str) -> List[str]:
        """分割段落"""
        paragraphs = re.split(r"\n\s*\n", content)
        filtered = []
        for p in paragraphs:
            p = p.strip()
            if 100 <= len(p) <= 5000:
                filtered.append(p)
        return filtered

    def _find_best_scene_match(self, content: str) -> Dict:
        """找到最佳场景匹配"""
        best_match = {"scene_type": "无", "match_count": 0, "matched_keywords": []}

        for scene_type, config in self.scene_types.items():
            keywords = config.get("keywords", [])
            matched = [kw for kw in keywords if kw in content]
            match_count = len(matched)

            if match_count > best_match["match_count"]:
                best_match = {
                    "scene_type": scene_type,
                    "match_count": match_count,
                    "matched_keywords": matched,
                }

        return best_match

    def _calculate_quality(self, content: str, match_count: int) -> float:
        """计算质量分"""
        score = 6.0

        # 长度适中加分
        if 500 <= len(content) <= 2000:
            score += 0.5

        # 检查禁止项
        forbidden = ["总之", "综上所述", "不得不说", "让人不禁"]
        for f in forbidden:
            if f in content:
                score -= 0.5

        # 对话密度
        quote_count = content.count('"') + content.count('"')
        if quote_count >= 4:
            score += 0.3

        return min(max(score, 0), 10)

    def discover_new_scenes(
        self, unclassified: List[UnclassifiedFragment]
    ) -> List[DiscoveredScene]:
        """
        发现新场景类型

        Args:
            unclassified: 未归类片段列表

        Returns:
            发现的新场景列表
        """
        print("\n" + "=" * 60)
        print("发现新场景类型")
        print("=" * 60)

        if not unclassified:
            print("没有未归类片段可供分析")
            return []

        # 聚类
        clusters = self.clustering_engine.cluster_fragments(
            unclassified,
            min_cluster_size=self.config["min_cluster_size"],
            similarity_threshold=self.config["similarity_threshold"],
            max_clusters=self.config["max_clusters"],
        )

        if not clusters:
            print("没有发现有效的聚类")
            return []

        # 从每个聚类生成场景类型
        discovered_scenes = []

        for i, cluster_fragments in enumerate(clusters):
            # 提取关键词
            texts = [f.content for f in cluster_fragments]
            keywords_with_freq = self.keyword_extractor.extract_keywords(
                texts,
                top_k=self.config["keyword_top_k"],
                min_freq=self.config["keyword_min_freq"],
            )

            keywords = [kw for kw, freq in keywords_with_freq]

            if not keywords:
                continue

            # 生成场景名称
            scene_name = self.keyword_extractor.generate_scene_name(keywords)

            # 检查是否与现有场景重复
            if scene_name in self.scene_types:
                scene_name = f"{scene_name}_新{i + 1}"

            # 计算统计数据
            avg_quality = np.mean([f.quality_score for f in cluster_fragments])
            avg_similarity = self._calc_cluster_similarity(cluster_fragments)

            # 题材分布
            genre_dist = Counter([f.genre for f in cluster_fragments])

            # 计算置信度
            confidence = self._calculate_confidence(
                len(cluster_fragments), avg_similarity, len(keywords), avg_quality
            )

            # 建议状态
            suggested_status = "pending_activation"
            if confidence >= 0.8:
                suggested_status = "can_activate"
            if confidence >= 0.95:
                suggested_status = "active"

            # 创建发现场景
            discovered = DiscoveredScene(
                scene_name=scene_name,
                keywords=keywords,
                description=f"自动发现的场景类型，包含{len(cluster_fragments)}个相似片段",
                fragments=[f.fragment_id for f in cluster_fragments[:5]],  # 代表性片段
                fragment_count=len(cluster_fragments),
                avg_quality=avg_quality,
                avg_similarity=avg_similarity,
                confidence=confidence,
                genre_distribution=dict(genre_dist),
                suggested_status=suggested_status,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

            discovered_scenes.append(discovered)

            print(f"\n  发现: {scene_name}")
            print(f"    关键词: {keywords}")
            print(f"    片段数: {len(cluster_fragments)}")
            print(f"    置信度: {confidence:.2f}")
            print(f"    建议状态: {suggested_status}")

        # 保存结果
        self._save_discovered(discovered_scenes)

        return discovered_scenes

    def _calc_cluster_similarity(self, fragments: List[UnclassifiedFragment]) -> float:
        """计算聚类内平均相似度"""
        embeddings = self.clustering_engine.get_embeddings(
            [f.content for f in fragments]
        )

        from sklearn.metrics.pairwise import cosine_similarity

        sim_matrix = cosine_similarity(embeddings)

        # 取非对角线元素的平均值
        n = len(fragments)
        total_sim = 0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                total_sim += sim_matrix[i, j]
                count += 1

        return total_sim / count if count > 0 else 0

    def _calculate_confidence(
        self,
        fragment_count: int,
        avg_similarity: float,
        keyword_count: int,
        avg_quality: float,
    ) -> float:
        """
        计算发现置信度

        综合考虑：
        - 片段数量（越多越可信）
        - 平均相似度（越高越可信）
        - 关键词数量（越多越可信）
        - 平均质量分（越高越可信）
        """
        # 各项权重
        weights = {
            "fragment_count": 0.25,
            "avg_similarity": 0.30,
            "keyword_count": 0.25,
            "avg_quality": 0.20,
        }

        # 标准化各项指标
        # 片段数量：10为基准，100为满分
        fc_score = min(fragment_count / 100, 1.0)

        # 相似度：直接使用
        sim_score = avg_similarity

        # 关键词数量：5为基准，10为满分
        kc_score = min(keyword_count / 10, 1.0)

        # 质量分：6为基准，10为满分
        q_score = (avg_quality - 6) / 4

        # 综合计算
        confidence = (
            weights["fragment_count"] * fc_score
            + weights["avg_similarity"] * sim_score
            + weights["keyword_count"] * kc_score
            + weights["avg_quality"] * q_score
        )

        return max(0, min(1, confidence))

    def apply_discovered_scenes(
        self,
        discovered: List[DiscoveredScene],
        scene_types_file: Path = None,
        mapping_file: Path = None,
    ) -> bool:
        """
        应用发现的新场景到配置文件

        Args:
            discovered: 发现的新场景列表
            scene_types_file: 场景类型配置文件路径
            mapping_file: 场景映射配置文件路径

        Returns:
            是否成功
        """
        print("\n" + "=" * 60)
        print("应用新场景到配置")
        print("=" * 60)

        if not discovered:
            print("没有新场景需要应用")
            return False

        # 更新SCENE_TYPES
        updated_scene_types = dict(self.scene_types)

        for ds in discovered:
            if ds.confidence >= 0.6:  # 置信度阈值
                new_config = {
                    "keywords": ds.keywords,
                    "position": NEW_SCENE_DEFAULTS["position"],
                    "min_len": NEW_SCENE_DEFAULTS["min_len"],
                    "max_len": NEW_SCENE_DEFAULTS["max_len"],
                    "discovered": True,
                    "discovery_confidence": ds.confidence,
                    "fragment_count": ds.fragment_count,
                }
                updated_scene_types[ds.scene_name] = new_config
                print(f"  + {ds.scene_name}: {ds.keywords}")

        # 如果提供了配置文件路径，则更新
        if scene_types_file:
            self._update_scene_types_file(scene_types_file, updated_scene_types)

        # 更新scene_writer_mapping.json
        if mapping_file:
            self._update_mapping_file(mapping_file, discovered)

        # 保存统计
        self._save_stats(discovered, updated_scene_types)

        print(
            f"\n成功应用 {len([d for d in discovered if d.confidence >= 0.6])} 个新场景"
        )
        return True

    def _save_unclassified(self, fragments: List[UnclassifiedFragment]):
        """保存未归类片段"""
        data = {
            "total": len(fragments),
            "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fragments": [asdict(f) for f in fragments],
        }

        with open(self.unclassified_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  保存: {self.unclassified_file}")

    def _save_discovered(self, scenes: List[DiscoveredScene]):
        """保存发现的新场景"""
        data = {
            "total": len(scenes),
            "discovered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scenes": [asdict(s) for s in scenes],
        }

        with open(self.discovered_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"  保存: {self.discovered_file}")

    def _save_stats(self, discovered: List[DiscoveredScene], updated_scene_types: Dict):
        """保存统计信息"""
        stats = {
            "original_scene_types": len(self.scene_types),
            "new_scene_types": len(discovered),
            "total_scene_types": len(updated_scene_types),
            "high_confidence": len([d for d in discovered if d.confidence >= 0.8]),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "new_scenes": [d.scene_name for d in discovered],
        }

        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

    def _update_scene_types_file(self, file_path: Path, scene_types: Dict):
        """更新场景类型配置文件"""
        # 生成Python格式的内容
        content = "# 场景类型定义（含自动发现的场景）\n"
        content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "SCENE_TYPES = {\n"

        for scene_name, config in scene_types.items():
            content += f'    "{scene_name}": {{\n'
            content += f'        "keywords": {config.get("keywords", [])},\n'
            content += f'        "position": "{config.get("position", "any")}",\n'
            content += f'        "min_len": {config.get("min_len", 300)},\n'
            content += f'        "max_len": {config.get("max_len", 2000)},\n'
            if config.get("discovered"):
                content += f'        "discovered": True,\n'
                content += f'        "discovery_confidence": {config.get("discovery_confidence", 0)},\n'
            content += "    },\n"

        content += "}\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  更新: {file_path}")

    def _update_mapping_file(
        self, mapping_file: Path, discovered: List[DiscoveredScene]
    ):
        """更新场景映射配置文件"""
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mapping_data = json.load(f)
        except:
            mapping_data = {"scene_writer_mapping": {}}

        # 添加新场景映射
        for ds in discovered:
            if ds.confidence >= 0.6:
                # 为新场景创建默认作家协作配置
                new_mapping = {
                    "description": ds.description,
                    "status": ds.suggested_status,
                    "collaboration": [
                        {
                            "writer": "玄一",
                            "role": "剧情框架",
                            "phase": "核心",
                            "contribution": ["剧情推进", "情节设计"],
                            "weight": 0.40,
                            "technique_dimension": "剧情维度",
                        },
                        {
                            "writer": "墨言",
                            "role": "人物刻画",
                            "phase": "核心",
                            "contribution": ["人物状态", "心理描写"],
                            "weight": 0.35,
                            "technique_dimension": "人物维度",
                        },
                        {
                            "writer": "云溪",
                            "role": "氛围渲染",
                            "phase": "收尾",
                            "contribution": ["氛围营造", "润色"],
                            "weight": 0.25,
                            "technique_dimension": "氛围意境维度",
                        },
                    ],
                    "workflow_order": ["玄一", "墨言", "云溪"],
                    "primary_writer": "玄一",
                    "case_library_filter": {
                        "scene_type": ds.scene_name,
                        "reference_focus": ds.keywords[:3],
                    },
                    "discovered": True,
                    "discovery_confidence": ds.confidence,
                }

                mapping_data["scene_writer_mapping"][ds.scene_name] = new_mapping

        # 更新场景计数
        scene_count = mapping_data.get("scene_count", {})
        scene_count["total"] = len(mapping_data["scene_writer_mapping"])
        scene_count["pending_activation"] = len(
            [
                s
                for s in mapping_data["scene_writer_mapping"].values()
                if s.get("status") == "pending_activation"
            ]
        )
        mapping_data["scene_count"] = scene_count

        # 更新时间
        mapping_data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping_data, f, indent=2, ensure_ascii=False)

        print(f"  更新: {mapping_file}")

    def get_status(self) -> Dict:
        """获取发现状态"""
        status = {"unclassified_count": 0, "discovered_count": 0, "applied_count": 0}

        if self.unclassified_file.exists():
            with open(self.unclassified_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            status["unclassified_count"] = data.get("total", 0)

        if self.discovered_file.exists():
            with open(self.discovered_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            status["discovered_count"] = data.get("total", 0)

        if self.stats_file.exists():
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            status["applied_count"] = data.get("new_scene_types", 0)

        return status


# ============================================================
# 命令行接口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="自动场景发现工具")

    parser.add_argument(
        "--case-library-dir", default=".case-library", help="案例库目录路径"
    )

    parser.add_argument(
        "--mapping-file",
        default=".vectorstore/scene_writer_mapping.json",
        help="场景映射配置文件路径",
    )

    # 命令
    parser.add_argument("--analyze", action="store_true", help="收集未归类片段")
    parser.add_argument("--discover", action="store_true", help="发现新场景类型")
    parser.add_argument("--apply", action="store_true", help="应用新场景到配置")
    parser.add_argument("--full", action="store_true", help="完整流程")
    parser.add_argument("--status", action="store_true", help="查看状态")

    # 参数
    parser.add_argument("--limit", type=int, default=5000, help="最大收集片段数")
    parser.add_argument("--min-cluster-size", type=int, default=10, help="最小聚类大小")
    parser.add_argument("--max-clusters", type=int, default=20, help="最大发现场景数")
    parser.add_argument(
        "--confidence-threshold", type=float, default=0.6, help="应用置信度阈值"
    )

    args = parser.parse_args()

    # 初始化
    case_library_dir = Path(args.case_library_dir)
    mapping_file = Path(args.mapping_file)

    config = {
        "min_cluster_size": args.min_cluster_size,
        "max_clusters": args.max_clusters,
        "similarity_threshold": 0.75,
        "keyword_min_freq": 3,
        "keyword_top_k": 8,
    }

    discovery = SceneDiscovery(case_library_dir, config)

    # 执行命令
    if args.status:
        status = discovery.get_status()
        print("\n" + "=" * 60)
        print("自动场景发现状态")
        print("=" * 60)
        print(f"  未归类片段: {status['unclassified_count']}")
        print(f"  发现场景数: {status['discovered_count']}")
        print(f"  已应用场景: {status['applied_count']}")
        return

    if args.full:
        # 完整流程
        converted_dir = case_library_dir / "converted"

        # 1. 收集未归类片段
        unclassified = discovery.collect_unclassified_fragments(
            converted_dir, args.limit
        )

        # 2. 发现新场景
        discovered = discovery.discover_new_scenes(unclassified)

        # 3. 应用到配置
        if discovered:
            discovery.apply_discovered_scenes(discovered, None, mapping_file)

        print("\n完整流程执行完成!")
        return

    if args.analyze:
        converted_dir = case_library_dir / "converted"
        discovery.collect_unclassified_fragments(converted_dir, args.limit)
        return

    if args.discover:
        # 从已保存的未归类片段中发现
        if discovery.unclassified_file.exists():
            with open(discovery.unclassified_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            fragments = [UnclassifiedFragment(**f) for f in data.get("fragments", [])]

            discovery.discover_new_scenes(fragments)
        else:
            print("请先运行 --analyze 收集未归类片段")
        return

    if args.apply:
        # 应用已发现的新场景
        if discovery.discovered_file.exists():
            with open(discovery.discovered_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            scenes = [DiscoveredScene(**s) for s in data.get("scenes", [])]

            discovery.apply_discovered_scenes(scenes, None, mapping_file)
        else:
            print("请先运行 --discover 发现新场景")
        return

    # 无命令时显示帮助
    parser.print_help()
    print("\n示例:")
    print("  python scene_discovery.py --status")
    print("  python scene_discovery.py --analyze --limit 3000")
    print("  python scene_discovery.py --discover")
    print("  python scene_discovery.py --apply")
    print("  python scene_discovery.py --full --limit 5000")


if __name__ == "__main__":
    main()
