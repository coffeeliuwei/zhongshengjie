"""
章节经验写入器

将章节创作经验沉淀到日志，供后续章节检索复用。
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from collections import Counter


class ExperienceWriter:
    """章节经验写入器 - 让系统记住创作经验"""

    # 经验重要性权重
    IMPORTANCE_WEIGHTS = {
        "positive": 1.0,  # 正面经验（成功的做法）
        "negative": 1.5,  # 负面经验（失败的做法，权重更高）
        "modification": 1.2,  # 用户修改（反映了真实偏好）
        "insight": 1.0,  # 系统洞察
    }

    def __init__(self, log_dir: str = None):
        """
        初始化经验写入器

        Args:
            log_dir: 经验日志目录（默认为项目根目录）
        """
        self.log_dir = Path(log_dir) if log_dir else Path.cwd()
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write_chapter_experience(
        self, chapter: int, experience: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        写入章节经验

        Args:
            chapter: 章节号
            experience: {
                "content": str,              # 章节内容
                "evaluation_result": dict,   # 评估结果
                "user_modifications": list,  # 用户修改
                "techniques_used": list,     # 使用的技法
                "scene_types": list,         # 场景类型
                "writers": list,             # 参与作家
                "scores": dict,              # 各项评分
                "issues": list,              # 问题列表
                "highlights": list           # 亮点列表
            }

        Returns:
            {
                "success": bool,
                "log_file": str,
                "experience_data": dict
            }
        """
        # 1. 提取成功的做法
        what_worked = self._extract_what_worked(experience)

        # 2. 提取失败的做法
        what_didnt_work = self._extract_what_didnt_work(experience)

        # 3. 生成洞察
        insights = self._generate_insights(experience)

        # 4. 构建经验数据
        experience_data = {
            "chapter": chapter,
            "timestamp": datetime.now().isoformat(),
            "what_worked": what_worked,
            "what_didnt_work": what_didnt_work,
            "insights": insights,
            "scene_types": experience.get("scene_types", []),
            "writers": experience.get("writers", []),
            "scores": experience.get("scores", {}),
            "techniques_used": experience.get("techniques_used", []),
            "user_modifications": experience.get("user_modifications", []),
            "issues": experience.get("issues", []),
            "highlights": experience.get("highlights", []),
        }

        # 5. 写入日志文件
        log_file = self.log_dir / f"第{chapter}章_log.json"

        # 读取现有日志（如果存在）
        if log_file.exists():
            try:
                existing_data = json.loads(log_file.read_text(encoding="utf-8"))
                # 合并数据
                if isinstance(existing_data, dict):
                    # 更新现有数据
                    existing_data.update(experience_data)
                    experience_data = existing_data
                elif isinstance(existing_data, list):
                    # 如果是列表格式，追加
                    experience_data = {
                        "chapter": chapter,
                        "entries": existing_data + [experience_data],
                    }
            except (json.JSONDecodeError, Exception):
                # 如果读取失败，使用新数据
                pass

        # 写入文件
        try:
            log_file.write_text(
                json.dumps(experience_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            success = True
        except Exception as e:
            success = False
            print(f"写入经验日志失败: {e}")

        return {
            "success": success,
            "log_file": str(log_file),
            "experience_data": experience_data,
        }

    def _extract_what_worked(self, experience: Dict) -> List[Dict[str, Any]]:
        """
        提取成功的做法

        Args:
            experience: 章节经验数据

        Returns:
            [{"item": str, "context": str, "importance": float}]
        """
        what_worked = []

        # 1. 从高分评估项提取
        scores = experience.get("scores", {})
        overall_score = scores.get("overall", 0)

        if overall_score >= 8.0:
            # 识别高分维度
            for dimension, score in scores.items():
                if dimension == "overall":
                    continue
                if score >= 8.5:
                    what_worked.append(
                        {
                            "item": f"{dimension}维度表现优秀",
                            "context": f"评分: {score}/10",
                            "importance": self.IMPORTANCE_WEIGHTS["positive"]
                            * (score / 10),
                        }
                    )

        # 2. 从亮点提取
        highlights = experience.get("highlights", [])
        for highlight in highlights:
            item = highlight.get("content", "") or highlight.get("description", "")
            if item:
                what_worked.append(
                    {
                        "item": item[:200],  # 限制长度
                        "context": highlight.get("type", "highlight"),
                        "importance": self.IMPORTANCE_WEIGHTS["positive"],
                    }
                )

        # 3. 从使用的技法提取（如果评分高）
        techniques_used = experience.get("techniques_used", [])
        if overall_score >= 8.0:
            for tech in techniques_used:
                if isinstance(tech, str):
                    what_worked.append(
                        {
                            "item": f"技法「{tech}」应用成功",
                            "context": "来自高分章节",
                            "importance": self.IMPORTANCE_WEIGHTS["positive"],
                        }
                    )
                elif isinstance(tech, dict):
                    what_worked.append(
                        {
                            "item": f"技法「{tech.get('name', '未知')}」应用成功",
                            "context": tech.get("effect", ""),
                            "importance": self.IMPORTANCE_WEIGHTS["positive"],
                        }
                    )

        # 4. 从正面反馈提取
        user_modifications = experience.get("user_modifications", [])
        for mod in user_modifications:
            if mod.get("type") == "positive" or "好" in mod.get("comment", ""):
                what_worked.append(
                    {
                        "item": mod.get("content", "")[:200],
                        "context": "用户正面反馈",
                        "importance": self.IMPORTANCE_WEIGHTS["modification"],
                    }
                )

        return what_worked

    def _extract_what_didnt_work(self, experience: Dict) -> List[Dict[str, Any]]:
        """
        提取失败的做法

        Args:
            experience: 章节经验数据

        Returns:
            [{"item": str, "context": str, "importance": float}]
        """
        what_didnt_work = []

        # 1. 从问题列表提取
        issues = experience.get("issues", [])
        for issue in issues:
            if isinstance(issue, str):
                what_didnt_work.append(
                    {
                        "item": issue,
                        "context": "评估问题",
                        "importance": self.IMPORTANCE_WEIGHTS["negative"],
                    }
                )
            elif isinstance(issue, dict):
                what_didnt_work.append(
                    {
                        "item": issue.get("description", ""),
                        "context": issue.get("type", "issue"),
                        "importance": self.IMPORTANCE_WEIGHTS["negative"]
                        * (issue.get("severity", 1.0)),
                    }
                )

        # 2. 从低分维度提取
        scores = experience.get("scores", {})
        for dimension, score in scores.items():
            if dimension == "overall":
                continue
            if score < 6.0:
                what_didnt_work.append(
                    {
                        "item": f"{dimension}维度表现不佳",
                        "context": f"评分: {score}/10",
                        "importance": self.IMPORTANCE_WEIGHTS["negative"]
                        * (1 - score / 10),
                    }
                )

        # 3. 从用户修改提取
        user_modifications = experience.get("user_modifications", [])
        for mod in user_modifications:
            if mod.get("type") in ["rewrite", "negative"]:
                what_didnt_work.append(
                    {
                        "item": f"用户修改: {mod.get('reason', '原因未知')}",
                        "context": f"原内容: {mod.get('original', '')[:100]}",
                        "importance": self.IMPORTANCE_WEIGHTS["modification"],
                    }
                )

        # 4. 从失败技法提取
        techniques_used = experience.get("techniques_used", [])
        overall_score = scores.get("overall", 0)

        if overall_score < 6.0 and techniques_used:
            for tech in techniques_used:
                if isinstance(tech, str):
                    what_didnt_work.append(
                        {
                            "item": f"技法「{tech}」可能不适合此场景",
                            "context": "来自低分章节",
                            "importance": self.IMPORTANCE_WEIGHTS["negative"] * 0.8,
                        }
                    )

        return what_didnt_work

    def _generate_insights(self, experience: Dict) -> List[Dict[str, Any]]:
        """
        生成洞察

        Args:
            experience: 章节经验数据

        Returns:
            [{"insight": str, "category": str, "confidence": float}]
        """
        insights = []

        # 1. 分析场景-技法关联
        scene_types = experience.get("scene_types", [])
        techniques_used = experience.get("techniques_used", [])
        scores = experience.get("scores", {})
        overall_score = scores.get("overall", 0)

        if scene_types and techniques_used:
            for scene in scene_types:
                # 提取该场景的技法
                scene_techniques = self._extract_scene_techniques(
                    techniques_used, scene
                )

                if scene_techniques and overall_score >= 7.0:
                    insights.append(
                        {
                            "insight": f"场景「{scene}」适合技法：{', '.join(scene_techniques[:3])}",
                            "category": "scene_technique_mapping",
                            "confidence": min(0.9, overall_score / 10),
                            "importance": self.IMPORTANCE_WEIGHTS["insight"],
                        }
                    )

        # 2. 分析作家-场景匹配
        writers = experience.get("writers", [])
        if writers and scene_types and overall_score >= 7.5:
            for writer in writers:
                insights.append(
                    {
                        "insight": f"作家「{writer}」在场景「{', '.join(scene_types[:2])}」表现良好",
                        "category": "writer_scene_mapping",
                        "confidence": overall_score / 10,
                        "importance": self.IMPORTANCE_WEIGHTS["insight"],
                    }
                )

        # 3. 分析问题模式
        issues = experience.get("issues", [])
        if len(issues) >= 3:
            # 统计问题类型
            issue_types = Counter()
            for issue in issues:
                if isinstance(issue, dict):
                    issue_type = issue.get("type", "unknown")
                else:
                    issue_type = "general"
                issue_types[issue_type] += 1

            # 提取高频问题
            for issue_type, count in issue_types.most_common(2):
                if count >= 2:
                    insights.append(
                        {
                            "insight": f"注意避免重复问题：「{issue_type}」出现了{count}次",
                            "category": "issue_pattern",
                            "confidence": 0.85,
                            "importance": self.IMPORTANCE_WEIGHTS["insight"] * 1.2,
                        }
                    )

        # 4. 从用户修改学习
        user_modifications = experience.get("user_modifications", [])
        if user_modifications:
            # 分析修改模式
            mod_patterns = self._analyze_modification_patterns(user_modifications)

            for pattern in mod_patterns:
                insights.append(
                    {
                        "insight": pattern,
                        "category": "user_preference",
                        "confidence": 0.8,
                        "importance": self.IMPORTANCE_WEIGHTS["modification"],
                    }
                )

        return insights

    def _extract_scene_techniques(self, techniques_used: List, scene: str) -> List[str]:
        """提取场景相关的技法"""
        scene_techniques = []

        for tech in techniques_used:
            if isinstance(tech, str):
                scene_techniques.append(tech)
            elif isinstance(tech, dict):
                tech_name = tech.get("name", "")
                if tech_name:
                    scene_techniques.append(tech_name)

        return scene_techniques[:5]  # 最多返回5个

    def _analyze_modification_patterns(self, user_modifications: List) -> List[str]:
        """分析用户修改模式"""
        patterns = []

        # 统计修改类型
        mod_types = Counter()
        for mod in user_modifications:
            mod_type = mod.get("type", "unknown")
            mod_types[mod_type] += 1

        # 生成模式洞察
        if mod_types.get("style_change", 0) >= 2:
            patterns.append("用户对风格一致性要求较高")

        if mod_types.get("detail_addition", 0) >= 2:
            patterns.append("用户偏好更详细的描写")

        if mod_types.get("reduction", 0) >= 2:
            patterns.append("用户偏好简洁表达")

        return patterns

    def retrieve_chapter_experience(
        self, chapter: int, scene_type: str = None, writer: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        检索章节经验

        Args:
            chapter: 章节号
            scene_type: 场景类型（可选过滤）
            writer: 作家（可选过滤）

        Returns:
            章节经验数据
        """
        log_file = self.log_dir / f"第{chapter}章_log.json"

        if not log_file.exists():
            return None

        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))

            # 过滤场景类型
            if scene_type and scene_type in data.get("scene_types", []):
                return data

            # 过滤作家
            if writer and writer in data.get("writers", []):
                return data

            return data
        except Exception:
            return None

    def retrieve_recent_experiences(
        self,
        before_chapter: int,
        scene_type: str = None,
        writer: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        检索最近的章节经验

        Args:
            before_chapter: 在此章节之前的经验
            scene_type: 场景类型（可选过滤）
            writer: 作家（可选过滤）
            limit: 返回数量限制

        Returns:
            章节经验列表
        """
        experiences = []

        # 查找所有日志文件
        log_files = sorted(
            self.log_dir.glob("*_log.json"), key=lambda f: f.stem, reverse=True
        )

        for log_file in log_files[: limit * 2]:  # 多读一些，过滤后截取
            # 解析章节号
            match = re.search(r"第(\d+)章", log_file.stem)
            if not match:
                continue

            chapter = int(match.group(1))

            # 只检索指定章节之前的
            if chapter >= before_chapter:
                continue

            # 读取经验
            try:
                data = json.loads(log_file.read_text(encoding="utf-8"))

                # 过滤场景类型
                if scene_type and scene_type not in data.get("scene_types", []):
                    continue

                # 过滤作家
                if writer and writer not in data.get("writers", []):
                    continue

                experiences.append(data)

                if len(experiences) >= limit:
                    break
            except Exception:
                continue

        return experiences

    def aggregate_lessons(
        self, scene_type: str = None, limit_chapters: int = 50
    ) -> Dict[str, Any]:
        """
        汇总经验教训

        Args:
            scene_type: 场景类型（可选过滤）
            limit_chapters: 最多汇总的章节数

        Returns:
            {
                "common_issues": Counter,
                "effective_techniques": Counter,
                "failed_approaches": Counter,
                "insights_summary": list
            }
        """
        aggregated = {
            "common_issues": Counter(),
            "effective_techniques": Counter(),
            "failed_approaches": Counter(),
            "insights_summary": [],
        }

        # 检索所有相关经验
        experiences = self.retrieve_recent_experiences(
            before_chapter=9999, scene_type=scene_type, limit=limit_chapters
        )

        for exp in experiences:
            # 汇总成功做法
            for worked in exp.get("what_worked", []):
                item = worked.get("item", "")
                if item:
                    aggregated["effective_techniques"][item] += 1

            # 汇总失败做法
            for didnt_work in exp.get("what_didnt_work", []):
                item = didnt_work.get("item", "")
                if item:
                    aggregated["failed_approaches"][item] += 1

            # 汇总问题
            for issue in exp.get("issues", []):
                if isinstance(issue, dict):
                    issue_type = issue.get("type", "unknown")
                else:
                    issue_type = "general"
                aggregated["common_issues"][issue_type] += 1

            # 汇总洞察
            for insight in exp.get("insights", []):
                aggregated["insights_summary"].append(insight)

        # 转换Counter为字典（JSON可序列化）
        aggregated["common_issues"] = dict(aggregated["common_issues"].most_common(10))
        aggregated["effective_techniques"] = dict(
            aggregated["effective_techniques"].most_common(10)
        )
        aggregated["failed_approaches"] = dict(
            aggregated["failed_approaches"].most_common(10)
        )

        return aggregated
