"""
力量体系代价提取器

从战斗场景中提取各力量体系使用代价的具体描写方式：
- 代价类型
- 具体表现
- 触发条件
- 恢复方式

用于Generator生成符合设定的战斗代价描写
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass

from base_extractor import BaseExtractor
from config import EXTRACTION_DIMENSIONS


@dataclass
class PowerCost:
    """力量代价"""

    power_type: str  # 力量类型
    cost_type: str  # 代价类型
    expression: str  # 具体表现
    context: str  # 上下文
    trigger: str = ""  # 触发条件
    recovery: str = ""  # 恢复方式
    novel_id: str = ""  # 来源小说
    scene_type: str = ""  # 场景类型


class PowerCostExtractor(BaseExtractor):
    """力量体系代价提取器"""

    def __init__(self):
        super().__init__("power_cost")

        # 力量体系关键词
        self.power_keywords = {
            "修仙": {
                "技能": [
                    "剑气",
                    "飞剑",
                    "法术",
                    "阵法",
                    "符咒",
                    "神识",
                    "真气",
                    "灵力",
                ],
                "代价表现": [
                    "真气耗尽",
                    "经脉剧痛",
                    "神识涣散",
                    "脸色苍白",
                    "喷出一口鲜血",
                    "气息萎靡",
                    "身形踉跄",
                    "虎口崩裂",
                    "经脉受损",
                    "丹田空虚",
                    "头痛欲裂",
                    "意识模糊",
                    "真气逆流",
                    "道心不稳",
                ],
                "恢复方式": ["打坐调息", "服用丹药", "运转功法", "吸纳灵气"],
            },
            "魔法": {
                "技能": ["火球", "冰刃", "雷击", "风刃", "土墙", "禁咒", "魔法阵"],
                "代价表现": [
                    "魔力枯竭",
                    "精神萎靡",
                    "流鼻血",
                    "反噬",
                    "昏迷",
                    "精神损耗",
                    "魔力透支",
                    "魔法反噬",
                    "意识涣散",
                ],
                "恢复方式": ["冥想", "魔力药剂", "休息"],
            },
            "神术": {
                "技能": ["圣光", "审判", "治愈", "神盾", "祝福", "神迹"],
                "代价表现": [
                    "信仰动摇",
                    "圣光灼烧",
                    "灵魂疲惫",
                    "神恩消散",
                    "信念崩塌",
                    "圣光反噬",
                    "灵魂负担",
                ],
                "恢复方式": ["祈祷", "虔诚修行", "神恩洗礼"],
            },
            "科技": {
                "技能": ["机甲", "激光", "导弹", "护盾", "芯片", "改造"],
                "代价表现": [
                    "能源耗尽",
                    "设备过载",
                    "身体麻木",
                    "设备发热",
                    "能源灯闪烁",
                    "系统警告",
                    "身体负担",
                ],
                "恢复方式": ["充能", "维修", "更换零件", "医疗舱"],
            },
            "兽力": {
                "技能": ["血脉觉醒", "兽化", "血脉技", "图腾之力"],
                "代价表现": [
                    "血脉燃烧",
                    "骨骼崩解",
                    "肌肉溶解",
                    "失去理智",
                    "血脉暴走",
                    "身体崩溃",
                    "理智丧失",
                    "血脉反噬",
                ],
                "恢复方式": ["血脉压制", "休养", "血脉传承"],
            },
            "AI力": {
                "技能": ["黑客", "控制", "入侵", "数据分析", "意识渗透"],
                "代价表现": [
                    "算力耗尽",
                    "系统过载",
                    "反应变慢",
                    "系统卡顿",
                    "数据损坏",
                    "逻辑混乱",
                    "意识分裂",
                ],
                "恢复方式": ["系统重启", "算力补充", "数据修复"],
            },
            "异能": {
                "技能": ["再生", "变形", "超感知", "元素操控", "精神控制"],
                "代价表现": [
                    "基因不稳定",
                    "身体异变",
                    "精神创伤",
                    "基因崩溃",
                    "身体变形",
                    "精神分裂",
                    "异能失控",
                ],
                "恢复方式": ["基因稳定剂", "休养", "精神治疗"],
            },
            # 通用代价（跨题材兜底）
            "通用": {
                "技能": [
                    "出手", "动手", "出招", "施展", "释放", "使用", "激活",
                    "攻击", "防御", "反击", "爆发", "全力",
                ],
                "代价表现": [
                    "脸色苍白", "喷血", "踉跄", "气息紊乱", "精神萎靡",
                    "身体颤抖", "嘴角溢血", "嘴角带血", "虚弱", "眩晕",
                    "昏迷", "摔倒", "跌落", "倒退", "跌退", "膝盖弯曲",
                    "力竭", "精疲力竭", "体力透支", "意志消磨",
                    "鲜血", "伤口", "骨折", "肌肉撕裂",
                    "眼眶泛红", "牙关咬紧", "冷汗", "汗水湿透",
                ],
                "恢复方式": ["休息", "疗伤", "休养", "调养", "恢复"],
            },
        }

        # 战斗场景关键词
        self.battle_keywords = [
            "战斗", "厮杀", "激战", "交锋", "对决",
            "攻击", "防御", "招式", "技能",
            "出手", "出招", "施展", "爆发", "反击",
            "伤势", "受伤", "喷血", "鲜血",
            "重创", "受创", "击中", "命中",
        ]

        # 代价触发词
        self.cost_triggers = [
            "付出",
            "代价",
            "燃烧",
            "透支",
            "消耗",
            "耗尽",
            "极限",
            "承受",
            "负担",
            "反噬",
        ]

    def _detect_power_type(self, text: str) -> str:
        """检测文本中的力量类型，找不到时返回'通用'"""
        scores = {}

        for power_type, keywords in self.power_keywords.items():
            if power_type == "通用":
                continue  # 通用类型最后兜底
            score = 0
            for skill in keywords.get("技能", []):
                if skill in text:
                    score += 2
            for cost in keywords.get("代价表现", []):
                if cost in text:
                    score += 3

            if score > 0:
                scores[power_type] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return "通用"  # 改为返回"通用"而非 None

    def _detect_cost_expression(self, text: str, power_type: str) -> List[str]:
        """检测代价表现"""
        found_costs = []

        keywords = self.power_keywords.get(power_type, {})
        cost_list = keywords.get("代价表现", [])

        for cost in cost_list:
            if cost in text:
                found_costs.append(cost)

        # 通用代价词（扩充版）
        general_costs = [
            "脸色苍白", "喷血", "踉跄", "气息紊乱", "精神萎靡",
            "身体颤抖", "嘴角溢血", "嘴角带血", "虚弱", "眩晕",
            "昏迷", "力竭", "精疲力竭", "体力透支", "冷汗",
            "牙关咬紧", "眼眶泛红", "骨折", "肌肉撕裂",
        ]
        for cost in general_costs:
            if cost in text and cost not in found_costs:
                found_costs.append(cost)

        return found_costs

    def _find_cost_context(self, content: str, cost: str) -> Tuple[str, str]:
        """查找代价的上下文和触发条件"""
        # 找到代价出现位置
        pos = content.find(cost)
        if pos == -1:
            return "", ""

        # 提取前后文（各200字）
        start = max(0, pos - 200)
        end = min(len(content), pos + len(cost) + 200)
        context = content[start:end]

        # 提取触发条件（代价前100字中的技能词）
        trigger_start = max(0, pos - 100)
        trigger_text = content[trigger_start:pos]

        trigger = ""
        for power_type, keywords in self.power_keywords.items():
            for skill in keywords.get("技能", []):
                if skill in trigger_text:
                    trigger = skill
                    break
            if trigger:
                break

        return context, trigger

    def _extract_battle_scenes(self, content: str) -> List[str]:
        """提取战斗场景"""
        # 简单按段落分割
        paragraphs = content.split("\n")

        battle_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para or len(para) < 100:
                continue

            # 检测是否是战斗场景
            battle_score = sum(1 for kw in self.battle_keywords if kw in para)
            if battle_score >= 1:
                battle_paragraphs.append(para)

        return battle_paragraphs

    def _extract_cost_pairs(self, content: str, power_type: str = None) -> List[PowerCost]:
        """提取力量使用-代价配对"""
        costs = []

        # 使用传入的力量类型，或从场景内容检测
        if power_type is None:
            power_type = self._detect_power_type(content)

        # 检测代价表现
        cost_expressions = self._detect_cost_expression(content, power_type)

        for cost_expr in cost_expressions:
            context, trigger = self._find_cost_context(content, cost_expr)

            if context:
                costs.append(
                    PowerCost(
                        power_type=power_type,
                        cost_type=self._classify_cost(cost_expr, power_type),
                        expression=cost_expr,
                        context=context,
                        trigger=trigger,
                    )
                )

        return costs

    def _classify_cost(self, cost_expr: str, power_type: str) -> str:
        """分类代价类型"""
        # 代价类型映射
        cost_types = {
            "身体代价": [
                "脸色苍白",
                "喷血",
                "踉跄",
                "虎口崩裂",
                "骨骼崩解",
                "肌肉溶解",
                "身体异变",
            ],
            "精神代价": ["精神萎靡", "神识涣散", "意识模糊", "精神创伤", "精神分裂"],
            "能量代价": ["真气耗尽", "魔力枯竭", "算力耗尽", "能源耗尽", "血脉燃烧"],
            "生命代价": ["生命", "燃烧生命", "寿命"],
            "理智代价": ["失去理智", "理智丧失", "血脉暴走"],
            "信仰代价": ["信仰动摇", "信念崩塌"],
        }

        for cost_type, keywords in cost_types.items():
            if any(kw in cost_expr for kw in keywords):
                return cost_type

        return "其他代价"

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取力量代价"""

        # 从全文检测力量类型（单个段落信号太弱）
        novel_power_type = self._detect_power_type(content)

        # 提取战斗场景
        battle_scenes = self._extract_battle_scenes(content)

        if not battle_scenes:
            return []

        # 从每个战斗场景提取代价，使用全文力量类型
        all_costs = []
        for scene in battle_scenes:
            costs = self._extract_cost_pairs(scene, power_type=novel_power_type)
            for cost in costs:
                cost.novel_id = novel_id
                cost.scene_type = "战斗场景"
            all_costs.extend(costs)

        return [c.__dict__ for c in all_costs]

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 按力量体系聚合"""
        # 按力量类型分组
        power_costs = defaultdict(lambda: defaultdict(list))

        for item in items:
            power_type = item.get("power_type")
            cost_type = item.get("cost_type")
            expression = item.get("expression")

            if power_type and expression:
                power_costs[power_type][cost_type].append(
                    {
                        "expression": expression,
                        "context": item.get("context", ""),
                        "trigger": item.get("trigger", ""),
                        "novel_id": item.get("novel_id", ""),
                    }
                )

        # 整合结果
        results = []
        for power_type, cost_types in power_costs.items():
            cost_summary = []
            for cost_type, expressions in cost_types.items():
                # 去重
                unique_exprs = list({e["expression"]: e for e in expressions}.values())

                cost_summary.append(
                    {
                        "cost_type": cost_type,
                        "expressions": [e["expression"] for e in unique_exprs[:20]],
                        "sample_contexts": [
                            e["context"][:200] for e in unique_exprs[:3]
                        ],
                        "common_triggers": self._get_common_triggers(expressions),
                    }
                )

            results.append(
                {
                    "power_type": power_type,
                    "cost_categories": cost_summary,
                    "total_expressions": sum(
                        len(ct["expressions"]) for ct in cost_summary
                    ),
                }
            )

        return results

    def _get_common_triggers(self, expressions: List[dict]) -> List[str]:
        """获取常见触发条件"""
        triggers = [e.get("trigger", "") for e in expressions if e.get("trigger")]
        trigger_counter = Counter(triggers)
        return [t for t, _ in trigger_counter.most_common(10)]


# ==================== 力量代价模板生成 ====================


def generate_cost_template(power_type: str, intensity: str = "medium") -> str:
    """
    生成力量代价描写模板

    Args:
        power_type: 力量类型
        intensity: 强度 (low/medium/high/extreme)

    Returns:
        代价描写模板
    """
    # 加载提取结果
    output_file = get_output_path("power_cost") / "power_cost_all.json"

    if not output_file.exists():
        return f"[未找到{power_type}代价数据，请先运行提取]"

    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 查找对应力量类型
    power_data = None
    for item in data:
        if item.get("power_type") == power_type:
            power_data = item
            break

    if not power_data:
        return f"[未找到{power_type}代价数据]"

    # 根据强度选择代价
    intensity_mapping = {
        "low": ["能量代价", "精神代价"],
        "medium": ["身体代价", "精神代价", "能量代价"],
        "high": ["身体代价", "理智代价", "生命代价"],
        "extreme": ["生命代价", "理智代价", "信仰代价"],
    }

    selected_types = intensity_mapping.get(intensity, intensity_mapping["medium"])

    # 组装模板
    template_parts = []
    for cost_cat in power_data.get("cost_categories", []):
        if cost_cat.get("cost_type") in selected_types:
            exprs = cost_cat.get("expressions", [])
            if exprs:
                template_parts.append(
                    f"- {cost_cat['cost_type']}：{' / '.join(exprs[:3])}"
                )

    return "\n".join(template_parts) if template_parts else "[暂无匹配代价模板]"


# ==================== 入口函数 ====================


def extract_power_costs(limit: int = None):
    """提取力量代价"""
    extractor = PowerCostExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="提取力量体系代价")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--template", type=str, help="生成代价模板")
    parser.add_argument("--intensity", type=str, default="medium", help="代价强度")

    args = parser.parse_args()

    if args.status:
        status = PowerCostExtractor().progress
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    elif args.template:
        print(generate_cost_template(args.template, args.intensity))
    else:
        extract_power_costs(limit=args.limit)
