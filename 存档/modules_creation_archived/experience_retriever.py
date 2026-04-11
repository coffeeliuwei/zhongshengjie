"""
章节经验检索器

功能：
1. 检索前几章的经验日志
2. 提取有效做法、无效做法、可复用洞察
3. 根据场景类型过滤相关经验
4. 格式化为可注入的上下文
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any


class ExperienceRetriever:
    """
    章节经验检索器

    用法：
        retriever = ExperienceRetriever(log_dir="章节经验日志")
        experiences = retriever.retrieve(current_chapter=2, scene_types=["战斗", "人物"])
        context = retriever.format_context(experiences)
    """

    # 场景关键词映射
    SCENE_KEYWORDS = {
        "战斗": ["战斗", "代价", "胜利", "牺牲", "群体", "对手", "血脉"],
        "人物": ["人物", "角色", "情感", "成长", "出场", "性格", "外貌"],
        "世界观": ["世界观", "势力", "设定", "背景", "血脉", "体系"],
        "剧情": ["剧情", "伏笔", "悬念", "反转", "推进", "钩子"],
        "氛围": ["氛围", "意境", "描写", "环境", "场景", "气氛"],
        "情感": ["情感", "情绪", "心理", "感受", "关系"],
    }

    def __init__(self, log_dir: str = "D:/动画/众生界/章节经验日志"):
        """
        初始化经验检索器

        Args:
            log_dir: 经验日志目录路径
        """
        self.log_dir = Path(log_dir)

    def retrieve(
        self,
        current_chapter: int,
        scene_types: List[str],
        max_previous_chapters: int = 3,
    ) -> Dict[str, Any]:
        """
        检索前几章的经验日志

        Args:
            current_chapter: 当前章节号
            scene_types: 当前章节涉及的场景类型列表
            max_previous_chapters: 最多检索前几章（默认3章）

        Returns:
            经验上下文字典，包含：
            - what_worked: 有效做法列表
            - what_didnt_work: 无效做法列表
            - insights: 可复用洞察列表
            - for_next_chapter: 给下一章建议列表
            - source_chapters: 来源章节列表
        """
        experiences = {
            "what_worked": [],
            "what_didnt_work": [],
            "insights": [],
            "for_next_chapter": [],
            "source_chapters": [],
        }

        if not self.log_dir.exists():
            print(f"[经验检索] 目录不存在: {self.log_dir}")
            return experiences

        # 检索前N章
        start_chapter = max(1, current_chapter - max_previous_chapters)
        end_chapter = current_chapter - 1

        if end_chapter < 1:
            print(f"[经验检索] 当前是第一章，无前章经验")
            return experiences

        for chapter in range(end_chapter, start_chapter - 1, -1):
            log_file = self.log_dir / f"第{chapter}章_log.json"

            if not log_file.exists():
                continue

            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    log = json.load(f)

                # 提取经验
                experiences["what_worked"].extend(
                    self._prefix_items(log.get("what_worked", []), chapter)
                )
                experiences["what_didnt_work"].extend(
                    self._prefix_items(log.get("what_didnt_work", []), chapter)
                )
                experiences["for_next_chapter"].extend(
                    self._prefix_items(log.get("for_next_chapter", []), chapter)
                )

                # 过滤与当前场景相关的洞察
                for insight in log.get("insights", []):
                    if self._is_insight_relevant(insight, scene_types):
                        insight["_source_chapter"] = chapter
                        experiences["insights"].append(insight)

                experiences["source_chapters"].append(chapter)

            except Exception as e:
                print(f"[经验检索] 读取日志失败 {log_file}: {e}")

        # 去重
        experiences["what_worked"] = self._deduplicate(experiences["what_worked"])
        experiences["what_didnt_work"] = self._deduplicate(
            experiences["what_didnt_work"]
        )
        experiences["for_next_chapter"] = self._deduplicate(
            experiences["for_next_chapter"]
        )

        print(f"[经验检索] 检索了 {len(experiences['source_chapters'])} 章经验")
        return experiences

    def format_context(self, experiences: Dict[str, Any], max_items: int = 5) -> str:
        """
        格式化经验上下文

        Args:
            experiences: 经验字典
            max_items: 每类最多显示条数

        Returns:
            格式化的上下文字符串
        """
        if not any(
            [
                experiences.get("what_worked"),
                experiences.get("what_didnt_work"),
                experiences.get("insights"),
                experiences.get("for_next_chapter"),
            ]
        ):
            return ""

        context = "【前章经验参考】\n\n"

        if experiences.get("what_worked"):
            context += "✅ 有效做法（可参考）：\n"
            for item in experiences["what_worked"][:max_items]:
                context += f"  - {item}\n"
            context += "\n"

        if experiences.get("what_didnt_work"):
            context += "⚠️ 避免重复错误：\n"
            for item in experiences["what_didnt_work"][:max_items]:
                context += f"  - {item}\n"
            context += "\n"

        if experiences.get("insights"):
            context += "💡 可复用洞察：\n"
            for insight in experiences["insights"][:3]:
                content = insight.get("content", "")
                condition = insight.get("scene_condition", "")
                source = insight.get("_source_chapter", "")
                context += f"  - {content}\n"
                if condition:
                    context += f"    适用：{condition}\n"
                if source:
                    context += f"    （来源：第{source}章）\n"
            context += "\n"

        if experiences.get("for_next_chapter"):
            context += "📝 前章建议：\n"
            for item in experiences["for_next_chapter"][:max_items]:
                context += f"  - {item}\n"

        return context

    def write_log(
        self,
        chapter_name: str,
        techniques_used: List[Dict],
        what_worked: List[str],
        what_didnt_work: List[str],
        insights: List[Dict],
        for_next_chapter: List[str],
    ) -> Path:
        """
        写入章节经验日志

        Args:
            chapter_name: 章节名称
            techniques_used: 使用的技法列表
            what_worked: 有效做法列表
            what_didnt_work: 无效做法列表
            insights: 可复用洞察列表
            for_next_chapter: 给下一章建议列表

        Returns:
            日志文件路径
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 提取章节号
        match = re.search(r"第(\d+)章", chapter_name)
        chapter_num = match.group(1) if match else "0"

        log_file = self.log_dir / f"第{chapter_num}章_log.json"

        # 构建日志内容
        log_content = {
            "chapter": chapter_name,
            "created_at": datetime.now().isoformat(),
            "techniques_used": techniques_used,
            "what_worked": what_worked,
            "what_didnt_work": what_didnt_work,
            "insights": insights,
            "for_next_chapter": for_next_chapter,
        }

        # 写入文件
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_content, f, ensure_ascii=False, indent=2)

        print(f"[经验写入] 已写入: {log_file}")
        return log_file

    def _is_insight_relevant(self, insight: Dict, scene_types: List[str]) -> bool:
        """判断洞察是否与当前场景相关"""
        scene_condition = insight.get("scene_condition", "")
        content = insight.get("content", "")

        for scene_type in scene_types:
            keywords = self.SCENE_KEYWORDS.get(scene_type, [])
            for keyword in keywords:
                if keyword in scene_condition or keyword in content:
                    return True

        return False

    def _prefix_items(self, items: List[str], chapter: int) -> List[str]:
        """为条目添加来源章节前缀"""
        return [f"[第{chapter}章] {item}" for item in items]

    def _deduplicate(self, items: List[str]) -> List[str]:
        """去重并保持顺序"""
        seen = set()
        result = []
        for item in items:
            # 去掉前缀后比较
            clean_item = re.sub(r"^\[第\d+章\]\s*", "", item)
            if clean_item not in seen:
                seen.add(clean_item)
                result.append(item)
        return result


# 便捷函数
def retrieve_chapter_experience(
    current_chapter: int, scene_types: List[str]
) -> Dict[str, Any]:
    """
    便捷函数：检索前几章经验

    Args:
        current_chapter: 当前章节号
        scene_types: 场景类型列表

    Returns:
        经验字典
    """
    retriever = ExperienceRetriever()
    return retriever.retrieve(current_chapter, scene_types)


def format_experience_context(experiences: Dict[str, Any]) -> str:
    """
    便捷函数：格式化经验上下文

    Args:
        experiences: 经验字典

    Returns:
        格式化的上下文字符串
    """
    retriever = ExperienceRetriever()
    return retriever.format_context(experiences)


def write_chapter_log(
    chapter_name: str,
    evaluation_result: Dict[str, Any],
    techniques_used: Optional[List[Dict]] = None,
) -> Path:
    """
    便捷函数：写入章节经验日志

    Args:
        chapter_name: 章节名称
        evaluation_result: Evaluator输出的评估结果
        techniques_used: 使用的技法列表（可选）

    Returns:
        日志文件路径
    """
    retriever = ExperienceRetriever()

    # 从评估结果中提取洞察
    insight_data = evaluation_result.get("反馈", {}).get("洞察提取", {})

    return retriever.write_log(
        chapter_name=chapter_name,
        techniques_used=techniques_used or [],
        what_worked=insight_data.get("有效做法", []),
        what_didnt_work=insight_data.get("无效做法", []),
        insights=insight_data.get("可复用洞察", []),
        for_next_chapter=insight_data.get("给下一章建议", []),
    )


# 使用示例
if __name__ == "__main__":
    # 示例：检索经验
    retriever = ExperienceRetriever()
    experiences = retriever.retrieve(current_chapter=2, scene_types=["战斗", "人物"])

    context = retriever.format_context(experiences)
    print(context)

    # 示例：写入日志
    # retriever.write_log(
    #     chapter_name="第二章-觉醒",
    #     techniques_used=[{"name": "有代价胜利", "effect": "有效"}],
    #     what_worked=["代价描写具体"],
    #     what_didnt_work=["节奏过快"],
    #     insights=[{"content": "代价要有痛感", "scene_condition": "战斗场景"}],
    #     for_next_chapter=["注意节奏控制"]
    # )
