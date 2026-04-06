#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评分管理器 - 整合检查清单评分功能
整合 checklist_scorer.py 的核心功能

功能：
1. 11维度评分体系
2. 章节评分
3. 评级计算
4. 评分报告生成

使用方法：
    from modules.validation import ScorerManager

    scorer = ScorerManager()
    scorer.load_chapter("正文/第一章-天裂.md")
    scorer.set_scores({"世界观": 6, "剧情": 5, ...})
    report = scorer.generate_report()
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 评分维度配置（来自 CONFIG.md 和 checklist_scorer.py）
# ============================================================

DIMENSIONS = {
    "世界观": {
        "weight": 0.20,
        "p0_items": 3,
        "p1_items": 4,
        "checks": [
            "历史纵深：有断层、有遗忘、有回响",
            "内在逻辑一致性：规则稳定，不可随意突破",
            "世界观自生长：从核心规则自然衍生",
            "跨文明层级：势力有发展阶段差异",
            "势力历史恩怨：冲突有数代积累",
            "文化传承与断裂：知识有遗失、传统有扭曲",
            "地理真实感：地形影响文化/战争",
        ],
    },
    "剧情": {
        "weight": 0.15,
        "p0_items": 3,
        "p1_items": 3,
        "checks": [
            "命运驱动：时代裹挟角色",
            "历史回响：过去在现在中显现",
            "无简单结局：结局留下历史延续感",
            "多线交织：3+条命运线交织",
            "伏笔跨度：有跨卷伏笔",
            "历史转折点：事件改变格局",
        ],
    },
    "人物": {
        "weight": 0.15,
        "p0_items": 3,
        "p1_items": 3,
        "checks": [
            "群像塑造：多主角/多POV",
            "独立命运线：配角有独立动机和结局",
            "选择有代价：选择有不可逆后果",
            "道德灰色地带：立场分明而非正邪分明",
            "敌人有立场：反派有逻辑和价值观",
            "角色成长弧：世界观重塑而非能力升级",
        ],
    },
    "战斗": {
        "weight": 0.05,
        "p0_items": 2,
        "p1_items": 3,
        "checks": [
            "有代价的胜利：胜利伴随重大牺牲",
            "群体牺牲有姓名：具体姓名和细节",
            "战术逻辑：有战略考量",
            "战斗影响格局：改变权力/文明格局",
            "敌人有战术智慧：反方主动战略",
        ],
    },
    "氛围": {
        "weight": 0.15,
        "p0_items": 3,
        "p1_items": 3,
        "checks": [
            "厚重感：统计数字具体化",
            "静默中的悲怆：平静叙述重大事件",
            "时间沉淀感：时间痕迹可见",
            "物是人非感：过去在现在中显现",
            "语言重量感：每句话落地有声",
            "历史的温度：有人情温度",
        ],
    },
    "节奏": {
        "weight": 0.10,
        "p0_items": 0,
        "p1_items": 5,
        "checks": [
            "快慢交替：有合理的快慢变化",
            "情绪曲线：情绪有起伏、有高潮沉淀",
            "句子长度控制：情绪与句长匹配",
            "时间折叠：大跨度用简洁语言",
            "疲劳控制：高潮后有沉淀",
        ],
    },
    "叙事": {
        "weight": 0.10,
        "p0_items": 0,
        "p1_items": 6,
        "checks": [
            "视角切换：多视角呈现复杂性",
            "时间折叠：过去/现在交织",
            "预言式伏笔：预言/诗词暗示未来",
            "叙述克制：重大事件平静叙述",
            "信息不对称：角色不知读者所知",
            "史诗诗词：开篇诗承载世界观",
        ],
    },
    "主题": {
        "weight": 0.05,
        "p0_items": 0,
        "p1_items": 5,
        "checks": [
            "超越个人：关乎人类/文明议题",
            "触及永恒议题：权力、生存、牺牲、命运",
            "无明确答案：探讨而非解答",
            "多主题交织：多层议题并行",
            "主题深化：主题随剧情推进深化",
        ],
    },
    "情感": {
        "weight": 0.05,
        "p0_items": 0,
        "p1_items": 5,
        "checks": [
            "集体情感：家族/时代/文明情感",
            "历史创伤：过去伤害持续影响",
            "克制中的深沉：不大喊大叫表达深沉",
            "情感有代价：情感选择有后果",
            "情感承载具体：具体姓名承载情感",
        ],
    },
    "读者体验": {
        "weight": 0.00,
        "p0_items": 0,
        "p1_items": 0,
        "p2_items": 4,
        "checks": [
            "认知沉浸：读者相信世界存在",
            "情感共鸣：读者关心角色命运",
            "可诠释空间：留下思考空间",
            "出不来感：结束后仍思考世界",
        ],
    },
    "元维度": {
        "weight": 0.00,
        "p0_items": 0,
        "p1_items": 0,
        "p2_items": 4,
        "checks": [
            "作者信念：作者相信自己的世界",
            "世界观自洽度：设定不互相矛盾",
            "文本层次：有表层/中层/深层",
            "可诠释空间：不同解读可能",
        ],
    },
}

# 评级标准（来自 CONFIG.md）
RATINGS = {
    "S": {"min": 52, "label": "史诗级标准"},
    "A": {"min": 44, "label": "优秀"},
    "B": {"min": 35, "label": "良好"},
    "C": {"min": 26, "label": "合格"},
    "D": {"min": 0, "label": "需改进"},
}

# 验证阈值（来自 CONFIG.md）
VALIDATION_THRESHOLDS = {
    "世界自洽": 7,
    "人物立体": 6,
    "情感真实": 6,
    "战斗逻辑": 6,
    "文风克制": 6,
    "剧情张力": 6,
}


def get_rating(score: int) -> str:
    """根据总分获取评级"""
    for rating, config in RATINGS.items():
        if score >= config["min"]:
            return rating
    return "D"


class ScorerManager:
    """
    评分管理器

    整合 checklist_scorer.py 功能
    提供11维度评分和评级计算
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化评分管理器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or Path.cwd()
        self.scores: Dict[str, Dict] = {}
        self.chapter_name: str = ""
        self.chapter_content: str = ""
        self.total_score: int = 0
        self.max_score: int = 59  # 总满分

    def load_chapter(self, chapter_path: str) -> bool:
        """
        加载章节内容

        Args:
            chapter_path: 章节文件路径

        Returns:
            是否成功加载
        """
        path = Path(chapter_path)
        if not path.exists():
            # 尝试相对路径
            path = self.project_root / chapter_path
            if not path.exists():
                print(f"[错误] 文件不存在: {chapter_path}")
                return False

        self.chapter_name = path.stem
        self.chapter_content = path.read_text(encoding="utf-8")
        print(f"[加载] 章节: {self.chapter_name}, 字数: {len(self.chapter_content)}")
        return True

    def get_dimension_max_score(self, dim_name: str) -> int:
        """获取维度满分"""
        dim_config = DIMENSIONS.get(dim_name, {})
        p0 = dim_config.get("p0_items", 0)
        p1 = dim_config.get("p1_items", 0)
        p2 = dim_config.get("p2_items", 0)
        return p0 + p1 + p2

    def set_scores(self, scores: Dict[str, int]) -> int:
        """
        设置评分

        Args:
            scores: {维度名: 分数}

        Returns:
            总分
        """
        total = 0

        for dim_name, dim_config in DIMENSIONS.items():
            dim_max = self.get_dimension_max_score(dim_name)
            score = min(scores.get(dim_name, 0), dim_max)

            self.scores[dim_name] = {
                "score": score,
                "max": dim_max,
                "weight": dim_config["weight"],
            }
            total += score

        self.total_score = total
        return total

    def get_dimension_scores(self) -> Dict[str, Any]:
        """
        获取维度评分

        Returns:
            维度评分详情
        """
        return {
            "chapter": self.chapter_name,
            "dimensions": self.scores,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "rating": get_rating(self.total_score),
            "thresholds": VALIDATION_THRESHOLDS,
        }

    def calculate_weighted_score(self) -> float:
        """计算加权总分"""
        weighted = 0.0
        for dim_name, dim_data in self.scores.items():
            weight = dim_data["weight"]
            if weight > 0 and dim_data["max"] > 0:
                score_pct = dim_data["score"] / dim_data["max"]
                weighted += score_pct * 100 * weight
        return weighted

    def check_thresholds(self) -> Dict[str, Any]:
        """
        检查是否达标

        Returns:
            {
                "passed": bool,
                "failed_dimensions": List[str],
                "details": Dict
            }
        """
        passed = True
        failed_dimensions = []
        details = {}

        # 映射维度到阈值名称
        dim_to_threshold = {
            "世界观": "世界自洽",
            "人物": "人物立体",
            "情感": "情感真实",
            "战斗": "战斗逻辑",
            "氛围": "文风克制",
            "剧情": "剧情张力",
        }

        for dim_name, threshold_name in dim_to_threshold.items():
            threshold = VALIDATION_THRESHOLDS.get(threshold_name)
            if threshold and dim_name in self.scores:
                dim_score = self.scores[dim_name]["score"]
                dim_max = self.scores[dim_name]["max"]

                # 计算百分制分数
                score_pct = (dim_score / dim_max) * 10 if dim_max > 0 else 0

                details[threshold_name] = {
                    "score": dim_score,
                    "max": dim_max,
                    "percentage": round(score_pct, 2),
                    "threshold": threshold,
                    "passed": score_pct >= threshold,
                }

                if score_pct < threshold:
                    passed = False
                    failed_dimensions.append(threshold_name)

        return {
            "passed": passed,
            "failed_dimensions": failed_dimensions,
            "details": details,
        }

    def generate_report(self, output_format: str = "text") -> str:
        """
        生成评分报告

        Args:
            output_format: "text" 或 "json"

        Returns:
            报告内容
        """
        rating = get_rating(self.total_score)
        weighted = self.calculate_weighted_score()
        threshold_check = self.check_thresholds()

        if output_format == "json":
            return json.dumps(
                {
                    "chapter": self.chapter_name,
                    "date": datetime.now().isoformat(),
                    "dimensions": self.scores,
                    "total_score": self.total_score,
                    "max_score": self.max_score,
                    "weighted_score": round(weighted, 2),
                    "rating": rating,
                    "rating_label": RATINGS[rating]["label"],
                    "threshold_check": threshold_check,
                },
                ensure_ascii=False,
                indent=2,
            )

        # 文本格式
        lines = [
            "=" * 60,
            "检查清单评分报告",
            "=" * 60,
            f"章节: {self.chapter_name or '未指定'}",
            f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 60,
            "",
        ]

        for dim_name, dim_data in self.scores.items():
            score = dim_data["score"]
            max_s = dim_data["max"]
            weight = dim_data["weight"]
            bar = "█" * score + "░" * (max_s - score)
            lines.append(
                f"【{dim_name}】 {score}/{max_s} [{bar}] (权重{weight * 100:.0f}%)"
            )

        lines.extend(
            [
                "",
                "=" * 60,
                f"总分: {self.total_score}/{self.max_score}",
                f"加权分: {weighted:.2f}/100",
                f"评级: {rating} ({RATINGS[rating]['label']})",
                "",
                "阈值检查:",
            ]
        )

        for threshold_name, detail in threshold_check["details"].items():
            status = "✓" if detail["passed"] else "✗"
            lines.append(
                f"  {status} {threshold_name}: {detail['percentage']} ≥ {detail['threshold']}"
            )

        if threshold_check["passed"]:
            lines.append("  ✓ 所有维度达标")
        else:
            lines.append(
                f"  ✗ 未达标维度: {', '.join(threshold_check['failed_dimensions'])}"
            )

        lines.append("=" * 60)

        return "\n".join(lines)

    def interactive_score(self) -> int:
        """
        交互式评分

        Returns:
            总分
        """
        print("\n" + "=" * 60)
        print("检查清单评分 - 交互模式")
        print("=" * 60)

        if self.chapter_name:
            print(f"章节: {self.chapter_name}")
        print(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

        total_score = 0

        for dim_name, dim_config in DIMENSIONS.items():
            print(f"\n【{dim_name}】(权重: {dim_config['weight'] * 100:.0f}%)")
            print("-" * 40)

            dim_max = self.get_dimension_max_score(dim_name)

            # 显示检查项
            p0 = dim_config.get("p0_items", 0)
            p1 = dim_config.get("p1_items", 0)

            for i, check in enumerate(dim_config["checks"], 1):
                priority = "P0" if i <= p0 else ("P1" if i <= p0 + p1 else "P2")
                print(f"  {priority}-{i}. {check}")

            # 输入评分
            while True:
                try:
                    score_input = input(
                        f"\n  评分 (满分{dim_max}分，或输入维度分如'2/3'): "
                    ).strip()

                    if "/" in score_input:
                        parts = [int(x) for x in score_input.split("/")]
                        score = sum(parts)
                    else:
                        score = int(score_input)

                    if 0 <= score <= dim_max:
                        self.scores[dim_name] = {
                            "score": score,
                            "max": dim_max,
                            "weight": dim_config["weight"],
                        }
                        total_score += score
                        break
                    else:
                        print(f"  [错误] 分数必须在0-{dim_max}之间")
                except ValueError:
                    print("  [错误] 请输入有效数字")

        self.total_score = total_score
        return total_score


# ============================================================
# CLI 适配接口
# ============================================================


def run_scorer_cli(args) -> int:
    """
    CLI评分入口

    Args:
        args: argparse解析后的参数

    Returns:
        退出码
    """
    scorer = ScorerManager()

    if args.chapter:
        scorer.load_chapter(args.chapter)

    if args.scores:
        try:
            scores = json.loads(args.scores)
            scorer.set_scores(scores)
        except json.JSONDecodeError:
            print("[错误] 评分JSON格式错误")
            return 1
    else:
        scorer.interactive_score()

    output_format = "json" if args.json else "text"
    report = scorer.generate_report(output_format)
    print("\n" + report)

    threshold_check = scorer.check_thresholds()
    return 0 if threshold_check["passed"] else 1
