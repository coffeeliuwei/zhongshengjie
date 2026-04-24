"""
反馈处理器

处理收集到的反馈，提取改进点、计算严重程度、映射到技法。
"""

import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import Counter


# 数据回流阈值配置
FEEDBACK_THRESHOLDS = {
    "technique_extraction": 8.5,  # 评分≥8.5才提取技法
    "case_extraction": 8.0,  # 评分≥8.0才提取案例
    "forbidden_detection_count": 3,  # 同一问题出现3次才加入禁止项
    "similarity_threshold": 0.85,  # 相似度阈值（用于去重）
    "min_confidence": 0.7,  # 最小置信度
}


class FeedbackProcessor:
    """反馈处理器 - 处理反馈并提取有价值信息"""

    # 问题到技法的映射
    ISSUE_TO_TECHNIQUE_MAPPING = {
        "战斗描写不够热血": {
            "dimension": "战斗",
            "technique_category": "战斗节奏",
            "suggestions": ["战斗代价三段式", "节奏把控"],
        },
        "节奏太慢": {
            "dimension": "节奏",
            "technique_category": "节奏把控",
            "suggestions": ["快节奏", "紧凑叙事"],
        },
        "语言太AI味": {
            "dimension": "语言",
            "technique_category": "语言风格",
            "suggestions": ["避免AI味", "自然表达"],
        },
        "风格不对": {
            "dimension": "风格",
            "technique_category": "风格适配",
            "suggestions": ["风格一致性", "文风匹配"],
        },
        "不一致": {
            "dimension": "一致性",
            "technique_category": "一致性维护",
            "suggestions": ["设定一致性", "契约校验"],
        },
        "不够详细": {
            "dimension": "描写",
            "technique_category": "细节描写",
            "suggestions": ["细节填充", "五感描写"],
        },
        "太啰嗦": {
            "dimension": "描写",
            "technique_category": "精简技巧",
            "suggestions": ["冗余剔除", "简洁表达"],
        },
    }

    # AI味表达模式
    AI_FLAVOR_PATTERNS = [
        r"然而[，。]",
        r"不得不[说承认]",
        r"令人[震惊惊讶]",
        r"令人难以置信",
        r"不可否认",
        r"正如我们[所见知道]",
        r"综上所述",
        r"总而言之",
        r"值得注意的是",
        r"这让我们[意识到明白]",
    ]

    def __init__(self, thresholds: Dict[str, float] = None):
        """
        初始化反馈处理器

        Args:
            thresholds: 自定义阈值配置（可选）
        """
        self.thresholds = thresholds or FEEDBACK_THRESHOLDS
        self.processed_feedbacks: List[Dict] = []
        self.issue_counter = Counter()  # 问题计数器

    def process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理反馈

        Args:
            feedback: FeedbackCollector收集的反馈

        Returns:
            {
                "processed": bool,
                "improvement_points": list,
                "severity": str,
                "technique_mapping": dict,
                "forbidden_items": list,
                "actionable": bool,
                "timestamp": str
            }
        """
        # 1. 提取改进点
        improvement_points = self._extract_improvement_points(feedback)

        # 2. 计算严重程度
        severity = self._calculate_severity(feedback, improvement_points)

        # 3. 映射到技法
        technique_mapping = self._map_to_technique(feedback, improvement_points)

        # 4. 提取禁止项
        forbidden_items = self._extract_forbidden_items(feedback)

        # 5. 判断是否可操作
        actionable = self._is_actionable(feedback, improvement_points, severity)

        # 6. 构建处理结果
        result = {
            "processed": True,
            "feedback_type": feedback.get("feedback_type"),
            "improvement_points": improvement_points,
            "severity": severity,
            "technique_mapping": technique_mapping,
            "forbidden_items": forbidden_items,
            "actionable": actionable,
            "original_feedback": feedback,
            "timestamp": datetime.now().isoformat(),
        }

        # 7. 保存到处理历史
        self.processed_feedbacks.append(result)

        # 8. 更新问题计数器
        for point in improvement_points:
            self.issue_counter[point] += 1

        return result

    def _extract_improvement_points(self, feedback: Dict) -> List[str]:
        """
        提取改进点

        Args:
            feedback: 原始反馈

        Returns:
            改进点列表
        """
        improvement_points = []

        # 从反馈类型提取
        feedback_type = feedback.get("feedback_type", "")
        feedback_category = feedback.get("feedback_category", "")

        # 从具体问题提取
        issue = feedback.get("issue", "")
        if issue:
            improvement_points.append(issue)

        # 从修改类型提取
        modification_type = feedback.get("modification_type")
        if modification_type:
            improvement_points.append(modification_type)

        # 从经验教训提取
        lesson = feedback.get("lesson")
        if lesson:
            # 提取关键教训
            lesson_points = self._parse_lesson(lesson)
            improvement_points.extend(lesson_points)

        # 从用户输入提取关键词
        raw_input = feedback.get("raw_input", "")
        if raw_input:
            keywords = self._extract_keywords_from_input(raw_input)
            improvement_points.extend(keywords)

        # 去重
        # 有序去重：保留首次出现顺序
        seen = set()
        deduped = []
        for point in improvement_points:
            if point and point not in seen:
                seen.add(point)
                deduped.append(point)
        improvement_points = deduped

        return improvement_points

    def _calculate_severity(self, feedback: Dict, improvement_points: List) -> str:
        """
        计算严重程度

        Args:
            feedback: 原始反馈
            improvement_points: 改进点列表

        Returns:
            严重程度：critical, high, medium, low, positive
        """
        # 优先使用反馈中的严重程度
        feedback_severity = feedback.get("severity")
        if feedback_severity:
            return feedback_severity

        # 基于反馈类型判断
        feedback_type = feedback.get("feedback_type", "")
        if feedback_type == "consistency_feedback":
            return "critical"
        elif feedback_type == "rewrite_request":
            return "high"
        elif feedback_type == "quality_feedback":
            return "positive"
        elif feedback_type in [
            "style_feedback",
            "detail_feedback",
            "excessive_feedback",
        ]:
            return "medium"

        # 基于改进点数量判断
        if len(improvement_points) >= 3:
            return "high"
        elif len(improvement_points) >= 1:
            return "medium"

        return "low"

    def _map_to_technique(
        self, feedback: Dict, improvement_points: List
    ) -> Dict[str, Any]:
        """
        映射到技法

        Args:
            feedback: 原始反馈
            improvement_points: 改进点列表

        Returns:
            {
                "dimension": str,
                "technique_category": str,
                "suggestions": list,
                "confidence": float
            }
        """
        technique_mapping = {
            "dimension": None,
            "technique_category": None,
            "suggestions": [],
            "confidence": 0.0,
        }

        # 查找匹配的技法映射
        for point in improvement_points:
            for issue_pattern, mapping in self.ISSUE_TO_TECHNIQUE_MAPPING.items():
                if issue_pattern in point or point in issue_pattern:
                    technique_mapping["dimension"] = mapping["dimension"]
                    technique_mapping["technique_category"] = mapping[
                        "technique_category"
                    ]
                    technique_mapping["suggestions"].extend(mapping["suggestions"])
                    technique_mapping["confidence"] = 0.8
                    break

        # 基于场景类型推断
        scene_type = feedback.get("scene_type")
        if scene_type and not technique_mapping["dimension"]:
            scene_mapping = self._get_scene_technique_mapping(scene_type)
            if scene_mapping:
                technique_mapping.update(scene_mapping)
                technique_mapping["confidence"] = 0.6

        # 基于作家推断
        writer = feedback.get("writer")
        if writer and not technique_mapping["dimension"]:
            writer_mapping = self._get_writer_technique_mapping(writer)
            if writer_mapping:
                technique_mapping.update(writer_mapping)
                technique_mapping["confidence"] = 0.5

        # 去重建议
        technique_mapping["suggestions"] = list(set(technique_mapping["suggestions"]))

        return technique_mapping

    def _extract_forbidden_items(self, feedback: Dict) -> List[str]:
        """
        提取禁止项

        Args:
            feedback: 原始反馈

        Returns:
            禁止项列表
        """
        forbidden_items = []

        # 尝试使用动态加载
        try:
            import sys
            from pathlib import Path

            # 添加core路径
            core_path = Path(__file__).parent.parent
            if str(core_path) not in sys.path:
                sys.path.insert(0, str(core_path))

            from evaluation_criteria_loader import EvaluationCriteriaLoader

            loader = EvaluationCriteriaLoader()
            loader.load()

            # 使用动态加载检测
            raw_input = feedback.get("raw_input", "")
            original = feedback.get("original", "")
            text_to_check = f"{raw_input} {original}"

            results = loader.detect_prohibitions(text_to_check)

            # 收集检测到的禁止项
            for r in results:
                if r.matches:
                    forbidden_items.append(r.name)

            # 使用动态阈值
            threshold = self.thresholds.get("forbidden_detection_count", 3)
            confirmed_forbidden = []

            for item in forbidden_items:
                history_count = self._count_pattern_in_history(item)
                if history_count >= threshold:
                    confirmed_forbidden.append(item)

            return confirmed_forbidden

        except Exception as e:
            # 回退到硬编码
            raw_input = feedback.get("raw_input", "")
            original = feedback.get("original", "")

            text_to_check = f"{raw_input} {original}"

            for pattern in self.AI_FLAVOR_PATTERNS:
                if re.search(pattern, text_to_check):
                    forbidden_items.append(pattern)

            threshold = self.thresholds.get("forbidden_detection_count", 3)
            confirmed_forbidden = []

            for item in forbidden_items:
                history_count = self._count_pattern_in_history(item)
                if history_count >= threshold:
                    confirmed_forbidden.append(item)

            return confirmed_forbidden

    def _is_actionable(
        self, feedback: Dict, improvement_points: List, severity: str
    ) -> bool:
        """
        判断是否可操作

        Args:
            feedback: 原始反馈
            improvement_points: 改进点列表
            severity: 严重程度

        Returns:
            是否可操作
        """
        # 有改进点且严重程度较高
        if len(improvement_points) > 0 and severity in ["critical", "high", "medium"]:
            return True

        # 有技法映射
        technique_mapping = self._map_to_technique(feedback, improvement_points)
        if technique_mapping.get("suggestions"):
            return True

        # 有明确的禁止项
        forbidden_items = self._extract_forbidden_items(feedback)
        if forbidden_items:
            return True

        return False

    def _parse_lesson(self, lesson: str) -> List[str]:
        """解析经验教训"""
        # 分割多个教训
        lessons = lesson.split(";")

        # 提取关键点
        points = []
        for l in lessons:
            l = l.strip()
            if l and not l.startswith("用户反馈"):
                # 提取核心内容
                match = re.search(r"用户偏好([^，。]+)", l)
                if match:
                    points.append(f"用户偏好：{match.group(1)}")

        return points

    def _extract_keywords_from_input(self, raw_input: str) -> List[str]:
        """从用户输入提取关键词"""
        keywords = []

        # 提取常见问题关键词
        keyword_patterns = [
            r"(战斗|情感|对话|描写|节奏|风格)[不够差]+",
            r"(太[长多啰嗦简略简单]+)",
            r"(不一致|矛盾|冲突)",
            r"(AI味|机器味)",
        ]

        for pattern in keyword_patterns:
            matches = re.findall(pattern, raw_input)
            keywords.extend(matches)

        return keywords

    def _get_scene_technique_mapping(self, scene_type: str) -> Optional[Dict]:
        """获取场景技法映射"""
        scene_mapping = {
            "战斗": {"dimension": "战斗", "technique_category": "战斗描写"},
            "情感": {"dimension": "情感", "technique_category": "情感刻画"},
            "对话": {"dimension": "对话", "technique_category": "对话风格"},
            "描写": {"dimension": "描写", "technique_category": "细节描写"},
            "开篇": {"dimension": "开篇", "technique_category": "开篇技巧"},
            "结尾": {"dimension": "结尾", "technique_category": "结尾技巧"},
        }

        return scene_mapping.get(scene_type)

    def _get_writer_technique_mapping(self, writer: str) -> Optional[Dict]:
        """获取作家技法映射"""
        writer_mapping = {
            "剑尘": {"dimension": "战斗", "technique_category": "战斗设计"},
            "墨言": {"dimension": "情感", "technique_category": "情感刻画"},
            "玄一": {"dimension": "剧情", "technique_category": "剧情编织"},
            "苍澜": {"dimension": "世界观", "technique_category": "世界观构建"},
            "云溪": {"dimension": "意境", "technique_category": "意境营造"},
        }

        return writer_mapping.get(writer)

    def _count_pattern_in_history(self, pattern: str) -> int:
        """计算模式在历史中出现的次数"""
        count = 0
        for processed in self.processed_feedbacks:
            if pattern in processed.get("forbidden_items", []):
                count += 1

        # 加上当前反馈的计数
        count += self.issue_counter.get(pattern, 0)

        return count

    def get_improvement_summary(self) -> Dict[str, Any]:
        """获取改进点汇总"""
        summary = {
            "total_feedbacks": len(self.processed_feedbacks),
            "critical_issues": [],
            "frequent_issues": [],
            "improvement_suggestions": [],
            "forbidden_items": [],
        }

        # 收集严重问题
        for processed in self.processed_feedbacks:
            if processed.get("severity") == "critical":
                summary["critical_issues"].extend(
                    processed.get("improvement_points", [])
                )

        # 收集频繁问题（出现次数 >= 阈值）
        threshold = self.thresholds.get("forbidden_detection_count", 3)
        for issue, count in self.issue_counter.items():
            if count >= threshold:
                summary["frequent_issues"].append({"issue": issue, "count": count})

        # 收集技法建议
        for processed in self.processed_feedbacks:
            suggestions = processed.get("technique_mapping", {}).get("suggestions", [])
            summary["improvement_suggestions"].extend(suggestions)

        summary["improvement_suggestions"] = list(
            set(summary["improvement_suggestions"])
        )

        # 收集确认的禁止项
        for processed in self.processed_feedbacks:
            forbidden = processed.get("forbidden_items", [])
            summary["forbidden_items"].extend(forbidden)

        summary["forbidden_items"] = list(set(summary["forbidden_items"]))

        return summary

    def get_processed_history(self, limit: int = 50) -> List[Dict]:
        """获取处理历史"""
        return self.processed_feedbacks[-limit:]

    def clear_history(self):
        """清空处理历史"""
        self.processed_feedbacks.clear()
        self.issue_counter.clear()

    def analyze_history_file(self, path) -> dict:
        """从 feedback_history.json 读取并分析反馈模式

        Args:
            path: feedback_history.json 文件路径

        Returns:
            {
                "total": int,
                "most_common_type": str,
                "negative_count": int,
                "by_type": dict,
                "by_scene_type": dict,
            }
        """
        import json
        from pathlib import Path
        from collections import Counter

        path = Path(path)
        if not path.exists():
            return {
                "total": 0,
                "most_common_type": None,
                "negative_count": 0,
                "by_type": {},
                "by_scene_type": {},
            }

        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)

        type_counter = Counter(fb.get("feedback_type") for fb in history)
        scene_counter = Counter(
            fb.get("scene_type") for fb in history if fb.get("scene_type")
        )
        negative_count = sum(
            1
            for fb in history
            if fb.get("feedback_category")
            in ("negative", "style", "consistency", "detail", "excessive")
        )

        return {
            "total": len(history),
            "most_common_type": type_counter.most_common(1)[0][0]
            if type_counter
            else None,
            "negative_count": negative_count,
            "by_type": dict(type_counter),
            "by_scene_type": dict(scene_counter),
        }
