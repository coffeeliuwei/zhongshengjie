#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查清单自动评分工具

使用方法：
    # 交互式评分
    python checklist_scorer.py

    # 从文件读取章节
    python checklist_scorer.py --chapter "正文/第一章-天裂.md"

    # 输出JSON格式
    python checklist_scorer.py --json

评分体系：
    11维度，总分59分
    S: 52+ (史诗级标准)
    A: 44-51 (优秀)
    B: 35-43 (良好)
    C: 26-34 (合格)
    D: <26 (需改进)
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Windows 编码修复
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 评分维度配置
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
        "weight": 0.00,  # 不计入加权分
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
        "weight": 0.00,  # 不计入加权分
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


# 评级标准
RATINGS = {
    "S": {"min": 52, "label": "史诗级标准"},
    "A": {"min": 44, "label": "优秀"},
    "B": {"min": 35, "label": "良好"},
    "C": {"min": 26, "label": "合格"},
    "D": {"min": 0, "label": "需改进"},
}


def get_rating(score: int) -> str:
    """根据总分获取评级"""
    for rating, config in RATINGS.items():
        if score >= config["min"]:
            return rating
    return "D"


class ChecklistScorer:
    """检查清单评分器"""

    def __init__(self):
        self.scores = {}
        self.chapter_name = ""
        self.chapter_content = ""

    def load_chapter(self, chapter_path: str):
        """加载章节内容"""
        path = Path(chapter_path)
        if not path.exists():
            print(f"[错误] 文件不存在: {chapter_path}")
            return False

        self.chapter_name = path.stem
        self.chapter_content = path.read_text(encoding="utf-8")
        print(f"[加载] 章节: {self.chapter_name}, 字数: {len(self.chapter_content)}")
        return True

    def input_scores_interactive(self):
        """交互式输入评分"""
        print("\n" + "=" * 60)
        print("检查清单评分 - 交互模式")
        print("=" * 60)

        if self.chapter_name:
            print(f"章节: {self.chapter_name}")
        print(f"日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60)

        total_score = 0
        max_score = 0

        for dim_name, dim_config in DIMENSIONS.items():
            print(f"\n【{dim_name}】(权重: {dim_config['weight'] * 100:.0f}%)")
            print("-" * 40)

            p0 = dim_config.get("p0_items", 0)
            p1 = dim_config.get("p1_items", 0)
            p2 = dim_config.get("p2_items", 0)

            dim_max = p0 + p1 + p2
            max_score += dim_max

            # 显示检查项
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
                        # 格式: p0/p1 或 p0/p1/p2
                        parts = [int(x) for x in score_input.split("/")]
                        if len(parts) == 2:
                            p0_score, p1_score = parts
                            p2_score = 0
                        elif len(parts) == 3:
                            p0_score, p1_score, p2_score = parts
                        else:
                            print("  [错误] 格式错误，请输入总分或'p0/p1/p2'")
                            continue
                        score = p0_score + p1_score + p2_score
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
        self.max_score = max_score
        return total_score

    def set_scores(self, scores: Dict[str, int]):
        """
        直接设置评分

        Args:
            scores: {维度名: 分数}
        """
        total = 0
        max_total = 0

        for dim_name, dim_config in DIMENSIONS.items():
            p0 = dim_config.get("p0_items", 0)
            p1 = dim_config.get("p1_items", 0)
            p2 = dim_config.get("p2_items", 0)
            dim_max = p0 + p1 + p2
            max_total += dim_max

            score = scores.get(dim_name, 0)
            score = min(score, dim_max)  # 不超过满分

            self.scores[dim_name] = {
                "score": score,
                "max": dim_max,
                "weight": dim_config["weight"],
            }
            total += score

        self.total_score = total
        self.max_score = max_total
        return total

    def calculate_weighted_score(self) -> float:
        """计算加权总分"""
        weighted = 0.0
        for dim_name, dim_data in self.scores.items():
            weight = dim_data["weight"]
            if weight > 0:
                # 将维度分转换为百分制再乘权重
                score_pct = (
                    dim_data["score"] / dim_data["max"] if dim_data["max"] > 0 else 0
                )
                weighted += score_pct * 100 * weight
        return weighted

    def generate_report(self, output_format: str = "text") -> str:
        """
        生成评分报告

        Args:
            output_format: "text" 或 "json"
        """
        rating = get_rating(self.total_score)
        weighted = self.calculate_weighted_score()

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
                "=" * 60,
            ]
        )

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="检查清单自动评分工具")
    parser.add_argument("--chapter", type=str, help="章节文件路径")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    parser.add_argument("--scores", type=str, help="直接输入评分 (JSON格式)")

    args = parser.parse_args()

    scorer = ChecklistScorer()

    # 加载章节
    if args.chapter:
        scorer.load_chapter(args.chapter)

    # 直接设置评分
    if args.scores:
        try:
            scores = json.loads(args.scores)
            scorer.set_scores(scores)
        except json.JSONDecodeError:
            print("[错误] 评分JSON格式错误")
            sys.exit(1)
    else:
        # 交互式输入
        scorer.input_scores_interactive()

    # 生成报告
    output_format = "json" if args.json else "text"
    report = scorer.generate_report(output_format)
    print("\n" + report)


if __name__ == "__main__":
    main()
