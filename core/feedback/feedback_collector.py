"""
用户反馈收集器

从用户的重写请求、修改操作和显式反馈中收集反馈信息。
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime


# 反馈模板配置
FEEDBACK_TEMPLATES = {
    "rewrite_request": {
        "triggers": ["重写", "写得不好", "再来一遍", "不行", "太差了", "换一个"],
        "questions": [
            "为了帮我改进，能告诉我具体问题吗？",
            "1. 战斗描写不够热血？",
            "2. 节奏太慢？",
            "3. 语言太AI味？",
            "4. 其他问题？",
        ],
        "severity": "high",
    },
    "quality_feedback": {
        "triggers": ["这段很好", "写得不错", "保持了", "优秀", "很好", "很棒"],
        "questions": [
            "谢谢反馈！这段好在哪里？",
            "1. 战斗节奏紧凑",
            "2. 人物刻画生动",
            "3. 语言自然流畅",
            "4. 其他优点",
        ],
        "severity": "positive",
    },
    "style_feedback": {
        "triggers": ["风格不对", "文笔不对", "语气不对", "味道不对"],
        "questions": [
            "请问风格哪里不对？",
            "1. 太正式/太书面",
            "2. 太随意/太口语",
            "3. 缺少原著风格",
            "4. 其他风格问题",
        ],
        "severity": "medium",
    },
    "consistency_feedback": {
        "triggers": ["不一致", "矛盾", "前后矛盾", "设定不对"],
        "questions": [
            "请问哪里不一致？",
            "1. 人物性格",
            "2. 能力设定",
            "3. 世界观设定",
            "4. 时间线",
        ],
        "severity": "critical",
    },
    "detail_feedback": {
        "triggers": ["不够详细", "太简单", "太简略", "缺细节"],
        "questions": [
            "请问哪里需要更多细节？",
            "1. 战斗过程",
            "2. 心理描写",
            "3. 环境描写",
            "4. 人物外貌",
        ],
        "severity": "medium",
    },
    "excessive_feedback": {
        "triggers": ["太多了", "太长", "太啰嗦", "冗余"],
        "questions": [
            "请问哪里需要精简？",
            "1. 战斗描写",
            "2. 心理描写",
            "3. 环境描写",
            "4. 对话内容",
        ],
        "severity": "medium",
    },
}


class FeedbackCollector:
    """用户反馈收集器 - 从用户修改中学习"""

    # 反馈类型映射
    FEEDBACK_TYPE_MAPPING = {
        "rewrite_request": "negative",
        "quality_feedback": "positive",
        "style_feedback": "style",
        "consistency_feedback": "consistency",
        "detail_feedback": "detail",
        "excessive_feedback": "excessive",
    }

    def __init__(self):
        """初始化反馈收集器"""
        self.feedback_history: List[Dict] = []

    def collect_from_rewrite(self, user_input: str) -> Dict[str, Any]:
        """
        从重写请求收集反馈

        Args:
            user_input: 用户输入的重写请求

        Returns:
            {
                "feedback_type": "rewrite_request",
                "issue": "战斗描写不够热血",
                "scene_type": Optional[str],
                "writer": Optional[str],
                "should_log": bool,
                "timestamp": str,
                "severity": str
            }
        """
        # 1. 识别反馈类型
        feedback_type = self._identify_feedback_type(user_input)

        # 2. 提取具体问题
        issue = self._extract_issue(user_input, feedback_type)

        # 3. 提取场景类型（如果有）
        scene_type = self._extract_scene_type(user_input)

        # 4. 提取作家信息（如果有）
        writer = self._extract_writer(user_input)

        # 5. 判断是否需要记录
        should_log = (
            feedback_type != "quality_feedback"
            or self._is_significant_positive(user_input)
        )

        # 6. 获取严重程度
        severity = FEEDBACK_TEMPLATES.get(feedback_type, {}).get("severity", "medium")

        feedback = {
            "feedback_type": feedback_type,
            "feedback_category": self.FEEDBACK_TYPE_MAPPING.get(
                feedback_type, "neutral"
            ),
            "issue": issue,
            "scene_type": scene_type,
            "writer": writer,
            "should_log": should_log,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "raw_input": user_input,
        }

        # 保存到历史
        self.feedback_history.append(feedback)

        return feedback

    def collect_from_modification(
        self, user_input: str, original: str, modified: str
    ) -> Dict[str, Any]:
        """
        从用户修改操作收集反馈

        Args:
            user_input: 用户输入（修改说明）
            original: 原始内容
            modified: 修改后的内容

        Returns:
            {
                "feedback_type": "modification",
                "modification_type": str,
                "original": str,
                "modified": str,
                "diff_analysis": dict,
                "lesson": str,
                "timestamp": str
            }
        """
        # 1. 分析差异
        diff_analysis = self._analyze_diff(original, modified)

        # 2. 提取修改类型
        modification_type = self._identify_modification_type(
            original, modified, diff_analysis
        )

        # 3. 提取经验教训
        lesson = self._extract_lesson_from_modification(
            user_input, modification_type, diff_analysis
        )

        # 4. 提取场景类型
        scene_type = self._extract_scene_type(user_input)

        # 5. 提取作家信息
        writer = self._extract_writer(user_input)

        feedback = {
            "feedback_type": "modification",
            "feedback_category": "modification",
            "modification_type": modification_type,
            "original": original,
            "modified": modified,
            "diff_analysis": diff_analysis,
            "lesson": lesson,
            "scene_type": scene_type,
            "writer": writer,
            "should_log": True,
            "timestamp": datetime.now().isoformat(),
            "severity": "medium",
            "raw_input": user_input,
        }

        # 保存到历史
        self.feedback_history.append(feedback)

        return feedback

    def collect_from_explicit(self, user_input: str) -> Dict[str, Any]:
        """
        从显式反馈收集

        Args:
            user_input: 用户明确表达的反馈

        Returns:
            {
                "feedback_type": str,
                "feedback_category": str,
                "issue": str,
                "scene_type": Optional[str],
                "writer": Optional[str],
                "should_log": bool,
                "timestamp": str,
                "severity": str
            }
        """
        # 直接调用重写请求收集方法（逻辑相同）
        return self.collect_from_rewrite(user_input)

    def _identify_feedback_type(self, user_input: str) -> str:
        """识别反馈类型"""
        for feedback_type, template in FEEDBACK_TEMPLATES.items():
            for trigger in template.get("triggers", []):
                if trigger in user_input:
                    return feedback_type

        # 默认类型
        return "general_feedback"

    def _extract_issue(self, user_input: str, feedback_type: str) -> str:
        """提取具体问题"""
        # 尝试从用户输入中提取具体问题
        issue_patterns = {
            "rewrite_request": [
                r"重写[，。]?([^，。]+)",
                r"(战斗|情感|对话|描写)[不够差]+([^，。]+)",
            ],
            "style_feedback": [
                r"风格[不对]+[，。]?([^，。]+)",
                r"(文笔|语气)[不对]+([^，。]+)",
            ],
            "consistency_feedback": [
                r"(不一致|矛盾|冲突)[：:]?([^，。]+)",
            ],
            "detail_feedback": [
                r"([^，。]+)[不够太简略简单]+",
            ],
            "excessive_feedback": [
                r"([^，。]+)[太多太长啰嗦冗余]+",
            ],
        }

        patterns = issue_patterns.get(feedback_type, [])
        for pattern in patterns:
            match = re.search(pattern, user_input)
            if match:
                return match.group(1) if match.lastindex else match.group(0)

        # 返回反馈类型描述
        template = FEEDBACK_TEMPLATES.get(feedback_type, {})
        return f"{feedback_type}: {user_input[:50]}"

    def _extract_scene_type(self, user_input: str) -> Optional[str]:
        """提取场景类型"""
        scene_keywords = {
            "战斗": ["战斗", "打", "战", "对决", "厮杀"],
            "情感": ["情感", "爱情", "告白", "恋爱", "分手"],
            "对话": ["对话", "交谈", "说话", "聊天"],
            "描写": ["描写", "描述", "刻画"],
            "开篇": ["开篇", "开头", "开始"],
            "结尾": ["结尾", "结局", "结束"],
        }

        for scene_type, keywords in scene_keywords.items():
            for kw in keywords:
                if kw in user_input:
                    return scene_type

        return None

    def _extract_writer(self, user_input: str) -> Optional[str]:
        """提取作家信息"""
        writer_keywords = {
            "剑尘": ["剑尘", "战斗", "热血"],
            "墨言": ["墨言", "情感", "心理"],
            "玄一": ["玄一", "剧情", "转折"],
            "苍澜": ["苍澜", "世界观", "势力"],
            "云溪": ["云溪", "意境", "诗意"],
        }

        for writer, keywords in writer_keywords.items():
            for kw in keywords:
                if kw in user_input:
                    return writer

        return None

    def _is_significant_positive(self, user_input: str) -> bool:
        """判断是否是重要的正面反馈"""
        significant_keywords = ["非常", "特别", "完美", "极佳", "优秀"]
        return any(kw in user_input for kw in significant_keywords)

    def _analyze_diff(self, original: str, modified: str) -> Dict[str, Any]:
        """分析文本差异"""
        # 简单的差异分析
        original_len = len(original)
        modified_len = len(modified)

        # 长度变化
        length_change = modified_len - original_len

        # 比例变化
        length_ratio = modified_len / original_len if original_len > 0 else 0

        # 内容变化类型
        change_type = "unknown"
        if length_ratio > 1.3:
            change_type = "expansion"
        elif length_ratio < 0.7:
            change_type = "reduction"
        elif abs(length_ratio - 1.0) < 0.1:
            change_type = "style_change"

        return {
            "original_length": original_len,
            "modified_length": modified_len,
            "length_change": length_change,
            "length_ratio": length_ratio,
            "change_type": change_type,
        }

    def _identify_modification_type(
        self, original: str, modified: str, diff_analysis: Dict
    ) -> str:
        """识别修改类型"""
        change_type = diff_analysis.get("change_type", "unknown")

        modification_type_mapping = {
            "expansion": "添加细节",
            "reduction": "精简内容",
            "style_change": "风格调整",
        }

        return modification_type_mapping.get(change_type, "内容修改")

    def _extract_lesson_from_modification(
        self, user_input: str, modification_type: str, diff_analysis: Dict
    ) -> str:
        """从修改中提取经验教训"""
        lessons = []

        # 基于修改类型
        if modification_type == "添加细节":
            lessons.append("用户偏好更多细节描写")
        elif modification_type == "精简内容":
            lessons.append("用户偏好简洁表达，避免冗余")
        elif modification_type == "风格调整":
            lessons.append("用户对特定风格有偏好")

        # 基于用户输入
        if user_input:
            lessons.append(f"用户反馈：{user_input[:50]}")

        return "; ".join(lessons) if lessons else "修改反映了用户偏好"

    def get_feedback_history(self, limit: int = 50) -> List[Dict]:
        """获取反馈历史"""
        return self.feedback_history[-limit:]

    def clear_history(self):
        """清空反馈历史"""
        self.feedback_history.clear()

    @staticmethod
    def has_feedback_signal(user_input: str) -> bool:
        """快速检测输入是否含有反馈关键词（用于旁路筛查）"""
        all_triggers = [
            kw
            for tmpl in FEEDBACK_TEMPLATES.values()
            for kw in tmpl.get("triggers", [])
        ]
        return any(t in user_input for t in all_triggers)

    def save_history(self, path: Path) -> None:
        """持久化 feedback_history 到 JSON 文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.feedback_history, f, ensure_ascii=False, indent=2)

    def load_history(self, path: Path) -> None:
        """从 JSON 文件恢复 feedback_history；文件不存在时静默跳过"""
        path = Path(path)
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            self.feedback_history = json.load(f)
