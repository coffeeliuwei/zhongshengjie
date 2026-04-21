#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技法提炼器
==========

从用户提供的素材中自动提炼创作技法。

核心功能：
- 分析文本内容
- 检索现有技法库进行对比学习
- 提取技法要素（结构、节奏、对比等）
- 归入合适的维度（11维度）
- 生成技法候选供用户确认

参考：collection-enhancement-design.md 5.1节
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TechniqueCandidate:
    """技法候选"""

    name: str
    dimension: str
    elements: List[str]
    applicable_scenes: List[str]
    source_content: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: "")


class TechniqueExtractor:
    """技法提炼器"""

    # 11个技法维度
    DIMENSIONS = [
        "开篇维度",
        "世界观维度",
        "剧情维度",
        "人物维度",
        "战斗冲突维度",
        "氛围意境维度",
        "叙事维度",
        "主题维度",
        "情感维度",
        "读者体验维度",
        "对话维度",
    ]

    # 维度关键词映射
    DIMENSION_KEYWORDS = {
        "开篇维度": ["开场", "开篇", "引入", "第一", "开始", "序幕"],
        "世界观维度": ["世界观", "体系", "规则", "设定", "势力", "背景"],
        "剧情维度": ["剧情", "情节", "转折", "悬念", "伏笔", "冲突"],
        "人物维度": ["人物", "角色", "性格", "心理", "成长", "塑造"],
        "战斗冲突维度": ["战斗", "打斗", "冲突", "代价", "胜利", "牺牲"],
        "氛围意境维度": ["氛围", "意境", "环境", "描写", "诗意", "意象"],
        "叙事维度": ["叙事", "节奏", "结构", "视角", "POV", "叙述"],
        "主题维度": ["主题", "寓意", "象征", "深层", "哲学"],
        "情感维度": ["情感", "情绪", "感动", "共鸣", "虐心", "治愈"],
        "读者体验维度": ["读者", "体验", "期待", "爽点", "钩子"],
        "对话维度": ["对话", "台词", "语言", "表达", "互动"],
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化技法提炼器

        Args:
            project_root: 项目根目录
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.pending_technique: Optional[TechniqueCandidate] = None

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "创作技法"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent
        return Path.cwd()

    def extract_from_content(self, content: str) -> TechniqueCandidate:
        """
        从用户提供的素材中提取技法

        Args:
            content: 用户提供的文本素材

        Returns:
            TechniqueCandidate: 技法候选
        """
        # 1. 检索相似技法（如果向量库可用）
        similar_techniques = self._search_similar_techniques(content)

        # 2. 分析技法要素
        elements = self._analyze_elements(content)

        # 3. 归入维度
        dimension = self._match_dimension(elements, content)

        # 4. 生成技法名称
        name = self._generate_name(elements, dimension)

        # 5. 推断适用场景
        applicable_scenes = self._infer_scenes(content, dimension)

        # 6. 计算置信度
        confidence = self._calculate_confidence(elements, similar_techniques)

        candidate = TechniqueCandidate(
            name=name,
            dimension=dimension,
            elements=elements,
            applicable_scenes=applicable_scenes,
            source_content=content[:500],
            confidence=confidence,
        )

        # 保存待确认
        self.pending_technique = candidate

        return candidate

    def extract_from_file(self, file_path: str) -> List[TechniqueCandidate]:
        """
        从文档文件中批量提取技法

        Args:
            file_path: 文档路径（相对或绝对）

        Returns:
            技法候选列表（可能包含多个技法）
        """
        # 1. 解析路径
        full_path = self._resolve_file_path(file_path)

        if not full_path or not full_path.exists():
            print(f"[ERROR] 文件不存在: {file_path}")
            return []

        # 2. 读取文档
        content = self._read_document(full_path)

        if not content:
            print(f"[ERROR] 无法读取文件: {full_path}")
            return []

        print(f"[INFO] 读取文档: {full_path.name} ({len(content)} 字符)")

        # 3. 分段分析（长文档需要分段）
        segments = self._segment_document(content)

        # 4. 对每个段提炼技法
        candidates = []
        for i, segment in enumerate(segments):
            if len(segment) < 100:
                continue  # 跳过太短的段落

            candidate = self.extract_from_content(segment)
            candidate.source_content = f"[文档: {full_path.name}] {segment[:300]}"
            candidates.append(candidate)

            if (i + 1) % 10 == 0:
                print(f"  已分析 {i + 1}/{len(segments)} 个段落")

        # 5. 去重和合并相似技法
        unique_candidates = self._deduplicate_candidates(candidates)

        print(f"[OK] 发现 {len(unique_candidates)} 个潜在技法")

        return unique_candidates

    def _resolve_file_path(self, file_path: str) -> Optional[Path]:
        """解析文件路径"""
        path = Path(file_path)

        # 绝对路径
        if path.exists():
            return path

        # 相对于项目根目录
        relative_path = self.project_root / file_path
        if relative_path.exists():
            return relative_path

        # 相对于创作技法目录
        technique_path = self.project_root / "创作技法" / file_path
        if technique_path.exists():
            return technique_path

        # 相对于正文目录
        content_path = self.project_root / "正文" / file_path
        if content_path.exists():
            return content_path

        return None

    def _read_document(self, path: Path) -> str:
        """读取文档内容"""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="gbk")
            except Exception as e:
                print(f"[WARN] 编码问题: {e}")
                return ""
        except Exception as e:
            print(f"[WARN] 读取失败: {e}")
            return ""

    def _segment_document(self, content: str) -> List[str]:
        """分段处理长文档"""
        # 按段落分割
        paragraphs = re.split(r"\n\s*\n+", content)

        # 过滤并清理
        segments = []
        for para in paragraphs:
            para = para.strip()
            # 只保留足够长的段落
            if 100 <= len(para) <= 5000:
                segments.append(para)

        return segments

    def _deduplicate_candidates(
        self, candidates: List[TechniqueCandidate]
    ) -> List[TechniqueCandidate]:
        """去重相似技法"""
        if not candidates:
            return []

        # 按维度分组
        by_dimension: Dict[str, List[TechniqueCandidate]] = {}
        for c in candidates:
            if c.dimension not in by_dimension:
                by_dimension[c.dimension] = []
            by_dimension[c.dimension].append(c)

        # 每个维度内去重
        unique = []
        for dimension, dim_candidates in by_dimension.items():
            # 按要素相似度去重
            seen_elements = set()
            for c in dim_candidates:
                element_key = tuple(sorted(c.elements[:2]))  # 用前2个要素作为key
                if element_key not in seen_elements:
                    seen_elements.add(element_key)
                    unique.append(c)

        return unique

    def _search_similar_techniques(self, content: str) -> List[Dict]:
        """检索相似技法（使用统一检索 API）"""
        try:
            from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI

            api = UnifiedRetrievalAPI()
            results = api.search_techniques(content, top_k=3)
            return results
        except Exception:
            return []

    def _analyze_elements(self, content: str) -> List[str]:
        """
        分析技法要素

        Args:
            content: 文本内容

        Returns:
            提取的技法要素列表
        """
        elements = []

        # 技法要素关键词
        element_patterns = {
            "节奏控制": ["节奏", "快慢", "起伏", "张弛"],
            "力量代价": ["代价", "牺牲", "消耗", "付出"],
            "心理博弈": ["心理", "博弈", "抉择", "内心"],
            "情感层次": ["情感", "层次", "递进", "爆发"],
            "对比手法": ["对比", "反差", "对照", "映衬"],
            "伏笔埋设": ["伏笔", "铺垫", "暗示", "线索"],
            "悬念营造": ["悬念", "悬念", "未知", "期待"],
            "场景渲染": ["渲染", "氛围", "环境", "意境"],
            "对话技巧": ["对话", "台词", "语言", "互动"],
            "人物塑造": ["塑造", "性格", "形象", "刻画"],
        }

        for element, keywords in element_patterns.items():
            for kw in keywords:
                if kw in content:
                    elements.append(element)
                    break

        # 如果没有匹配到任何要素，使用默认
        if not elements:
            elements = ["写作技巧"]

        return elements[:5]  # 最多返回5个要素

    def _match_dimension(self, elements: List[str], content: str) -> str:
        """
        根据要素和内容归入维度

        Args:
            elements: 技法要素
            content: 文本内容

        Returns:
            维度名称
        """
        # 根据内容关键词匹配
        content_lower = content.lower()

        dimension_scores = {}
        for dimension, keywords in self.DIMENSION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            dimension_scores[dimension] = score

        # 根据要素匹配
        for element in elements:
            if "节奏" in element:
                dimension_scores["叙事维度"] = dimension_scores.get("叙事维度", 0) + 2
            if "代价" in element or "牺牲" in element:
                dimension_scores["战斗冲突维度"] = (
                    dimension_scores.get("战斗冲突维度", 0) + 2
                )
            if "心理" in element:
                dimension_scores["人物维度"] = dimension_scores.get("人物维度", 0) + 2
            if "情感" in element:
                dimension_scores["情感维度"] = dimension_scores.get("情感维度", 0) + 2

        # 返回得分最高的维度
        if dimension_scores:
            best_dimension = max(dimension_scores.items(), key=lambda x: x[1])
            if best_dimension[1] > 0:
                return best_dimension[0]

        # 默认返回综合维度
        return "叙事维度"

    def _generate_name(self, elements: List[str], dimension: str) -> str:
        """
        生成技法名称

        Args:
            elements: 技法要素
            dimension: 维度

        Returns:
            技法名称
        """
        # 根据要素组合生成名称
        if elements:
            # 取前2个要素组合
            primary = elements[0]
            if len(elements) > 1:
                secondary = elements[1]
                return f"{primary}与{secondary}"
            return primary

        # 默认名称
        return f"{dimension}技法"

    def _infer_scenes(self, content: str, dimension: str) -> List[str]:
        """
        推断适用场景

        Args:
            content: 文本内容
            dimension: 维度

        Returns:
            适用场景列表
        """
        # 场景关键词
        scene_keywords = {
            "战斗场景": ["战斗", "打斗", "冲突", "对决"],
            "情感场景": ["情感", "感情", "爱情", "亲情"],
            "开篇场景": ["开场", "开篇", "开始", "引入"],
            "高潮场景": ["高潮", "巅峰", "关键"],
            "转折场景": ["转折", "变化", "突变"],
            "对话场景": ["对话", "交谈", "沟通"],
            "心理场景": ["心理", "内心", "思考"],
            "环境场景": ["环境", "场景", "地点"],
        }

        applicable = []
        content_lower = content.lower()

        for scene, keywords in scene_keywords.items():
            if any(kw in content_lower for kw in keywords):
                applicable.append(scene)

        # 根据维度添加默认场景
        dimension_scenes = {
            "战斗冲突维度": ["战斗场景", "高潮场景"],
            "人物维度": ["心理场景", "对话场景"],
            "情感维度": ["情感场景", "心理场景"],
            "开篇维度": ["开篇场景"],
            "氛围意境维度": ["环境场景"],
        }

        default_scenes = dimension_scenes.get(dimension, [])
        for scene in default_scenes:
            if scene not in applicable:
                applicable.append(scene)

        return applicable[:3]  # 最多返回3个场景

    def _calculate_confidence(
        self, elements: List[str], similar_techniques: List[Dict]
    ) -> float:
        """
        计算置信度

        Args:
            elements: 提取的要素
            similar_techniques: 相似技法

        Returns:
            置信度 (0-1)
        """
        base = 0.5

        # 有更多要素，置信度更高
        base += len(elements) * 0.1

        # 有相似技法，置信度更高
        if similar_techniques:
            base += 0.2

        return min(base, 1.0)

    def format_candidate_for_display(self, candidate: TechniqueCandidate) -> str:
        """
        格式化技法候选供用户确认

        Args:
            candidate: 技法候选

        Returns:
            格式化的文本
        """
        return f"""
【提炼结果】
- 技法名称：{candidate.name}
- 维度：{candidate.dimension}
- 核心要素：{", ".join(candidate.elements)}
- 适用场景：{", ".join(candidate.applicable_scenes)}
- 置信度：{candidate.confidence:.0%}

素材摘要：
{candidate.source_content[:300]}...

是否入库？[确认/修改/取消]
"""

    def confirm_and_save(self) -> bool:
        """
        确认并保存技法

        Returns:
            是否成功保存
        """
        if not self.pending_technique:
            return False

        candidate = self.pending_technique

        # 1. 写入技法文件
        technique_file = self._write_technique_file(candidate)

        # 2. 同步到向量库
        if technique_file:
            self._sync_to_vectorstore(candidate)

        # 3. 清除待确认
        self.pending_technique = None

        return True

    def _write_technique_file(self, candidate: TechniqueCandidate) -> Optional[Path]:
        """
        写入技法文件

        Args:
            candidate: 技法候选

        Returns:
            文件路径
        """
        from datetime import datetime

        # 确定目录
        dimension_dir = (
            self.project_root
            / "创作技法"
            / self._get_dimension_dir(candidate.dimension)
        )
        dimension_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        safe_name = re.sub(r'[\\/:*?"<>|]', "_", candidate.name)
        file_path = dimension_dir / f"{safe_name}.md"

        # 生成内容
        content = f"""# {candidate.name}

> **维度**: {candidate.dimension}
> **创建时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
> **来源**: 用户对话提炼

---

## 核心要素

{chr(10).join(f"- {e}" for e in candidate.elements)}

## 适用场景

{chr(10).join(f"- {s}" for s in candidate.applicable_scenes)}

## 技法说明

待补充具体技法说明。

---

## 素材来源

```
{candidate.source_content}
```
"""

        try:
            file_path.write_text(content, encoding="utf-8")
            print(f"[OK] 已创建技法文件: {file_path}")
            return file_path
        except Exception as e:
            print(f"[ERROR] 创建技法文件失败: {e}")
            return None

    def _get_dimension_dir(self, dimension: str) -> str:
        """
        获取维度目录名

        Args:
            dimension: 维度名称

        Returns:
            目录名
        """
        # 维度编号映射
        dimension_num = {
            "开篇维度": "01-开篇维度",
            "世界观维度": "02-世界观维度",
            "剧情维度": "03-剧情维度",
            "人物维度": "04-人物维度",
            "战斗冲突维度": "05-战斗冲突维度",
            "氛围意境维度": "06-氛围意境维度",
            "叙事维度": "07-叙事维度",
            "主题维度": "08-主题维度",
            "情感维度": "09-情感维度",
            "读者体验维度": "10-读者体验维度",
            "对话维度": "11-对话维度",
        }
        return dimension_num.get(dimension, "99-其他")

    def _sync_to_vectorstore(self, candidate: TechniqueCandidate) -> bool:
        """
        同步到向量库

        Args:
            candidate: 技法候选

        Returns:
            是否成功
        """
        try:
            from .file_updater import FileUpdater

            updater = FileUpdater(str(self.project_root))
            data = {
                "name": candidate.name,
                "dimension": candidate.dimension,
                "elements": candidate.elements,
                "applicable_scenes": candidate.applicable_scenes,
                "content": candidate.source_content,
            }
            return updater.sync_to_vectorstore("writing_techniques_v2", data)
        except Exception as e:
            print(f"[WARN] 向量库同步失败: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    extractor = TechniqueExtractor()

    test_content = """
这段战斗描写很精彩。主角虽然赢了，但是付出了惨重的代价——断了一只手臂。
战斗过程中节奏控制得很好，先是快速的交锋，然后是心理上的博弈，最后才是决定性的攻击。
"""

    print("=" * 60)
    print("技法提炼器测试")
    print("=" * 60)

    candidate = extractor.extract_from_content(test_content)
    print(extractor.format_candidate_for_display(candidate))
