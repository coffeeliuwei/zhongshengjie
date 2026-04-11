"""
力量体系词汇提取器

从小说中提取修仙/魔法/科技等专有名词：
- 境界名称
- 功法名称
- 技能名称
- 物品名称
- 组织名称

用于扩充词汇库，增强生成一致性
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass

from base_extractor import BaseExtractor
from config import EXTRACTION_DIMENSIONS


@dataclass
class Vocabulary:
    """词汇项"""

    term: str
    category: str  # 境界/功法/技能/物品/组织
    power_type: str  # 力量类型
    frequency: int  # 出现频率
    contexts: List[str]  # 上下文示例
    novel_ids: List[str]  # 来源小说


class VocabularyExtractor(BaseExtractor):
    """力量体系词汇提取器 v2.0"""

    # 排除的常见词（非专有名词）
    EXCLUDED_TERMS = {
        # 常用词误匹配
        "的方法",
        "的功",
        "无法",
        "没法",
        "有法",
        "用法",
        "用法",
        "做法",
        "想法",
        "什么法",
        "怎么法",
        "这个法",
        "那个法",
        "斩杀",
        "斩断",
        "斩首",
        "斩去",
        "斩下",  # 动词而非技能名
        "击中",
        "击打",
        "击破",
        "击败",
        "击杀",
        "一阵",
        "阵阵",
        "这阵",
        "那阵",  # 量词而非阵法
        "丹心",
        "丹田",
        "丹红",  # 非丹药名
        "玉石",
        "玉手",
        "玉体",
        "玉颜",
        "玉肌",  # 形容词而非物品
        "石头",
        "石块",
        "石板",  # 普通名词
        "药方",
        "药材",
        "药丸",
        "药物",  # 泛指而非专有
        "金牌",
        "银牌",
        "铜牌",
        "铁牌",  # 普通名词
        "符文",
        "符纸",
        "符号",  # 泛指
        "家族人",
        "家族中",
        "家族里",  # 句子片段
        "联盟军",
        "联盟中",  # 句子片段
        # 界限词
        "境界",
        "境界上",
        "境界下",
        "境界中",
        "阶位",
        "阶下",
        "阶上",
    }

    # 最小频次阈值
    MIN_FREQUENCY = 5

    def __init__(self):
        super().__init__("power_vocabulary")

        # 已知词汇（从设定加载）
        self.known_vocabulary = self._load_known_vocabulary()

        # 词汇模式（更精确的匹配，添加前后文约束）
        self.term_patterns = {
            "境界": [
                r"(?<![，。！？\s])(炼气期|筑基期|金丹期|元婴期|化神期|渡劫期|大乘期)(?![\u4e00-\u9fa5])",
                r"(?<![，。！？\s])(炼气境|筑基境|金丹境|元婴境|化神境)(?![\u4e00-\u9fa5])",
                r"(?<![，。！？\s])([一二三四五六七八九十])[重天](?![\u4e00-\u9fa5])",
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,3})(境界|阶段)(?![\u4e00-\u9fa5])",
            ],
            "功法": [
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(剑诀|心法|功法|秘术)(?![\u4e00-\u9fa5])",
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,5})(诀|法|功|经|典)(?![\u4e00-\u9fa5境界阶])",
            ],
            "技能": [
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(斩|击|刃|爆|盾|术|阵)(?![\u4e00-\u9fa5])",
            ],
            "物品": [
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(灵石|法宝|神兵|神器)(?![\u4e00-\u9fa5])",
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,5})(丹|药|剑|刀|符|牌)(?![\u4e00-\u9fa5心田红])",
            ],
            "组织": [
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(宗|门|派|阁|殿|院|楼)(?![\u4e00-\u9fa5人])",
                r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(家族|联盟)(?![\u4e00-\u9fa5中里人])",
            ],
        }

        # 力量类型关键词
        self.power_indicators = {
            "修仙": [
                "灵气",
                "真气",
                "境界",
                "修炼",
                "宗门",
                "剑",
                "丹",
                "符",
                "道友",
                "师尊",
            ],
            "魔法": ["魔力", "元素", "魔法", "法师", "禁咒", "魔杖", "魔晶"],
            "神术": ["圣光", "信仰", "神殿", "教会", "神恩", "祈祷", "信徒"],
            "科技": ["芯片", "机甲", "能源", "改造", "系统", "程序", "AI", "算力"],
            "兽力": ["血脉", "图腾", "部落", "兽化", "狩猎", "觉醒"],
            "异能": ["异能", "基因", "变异", "进化", "觉醒"],
        }

    def _load_known_vocabulary(self) -> Dict[str, Dict[str, List[str]]]:
        """加载已知词汇"""
        # 从设定文件加载
        vocab = {
            "修仙": {
                "境界": ["炼气期", "筑基期", "金丹期", "元婴期", "化神期", "渡劫期"],
                "功法": ["剑诀", "法术", "阵法", "符咒"],
                "物品": ["灵石", "法宝", "丹药"],
            },
            "魔法": {
                "等级": ["一级魔法", "二级魔法", "三级魔法", "禁咒"],
                "元素": [
                    "火系",
                    "水系",
                    "风系",
                    "土系",
                    "雷系",
                    "冰系",
                    "光系",
                    "暗系",
                ],
            },
            "科技": {
                "改造": ["机甲", "芯片", "能源核心"],
                "等级": ["一级改造", "二级改造", "三级改造"],
            },
        }
        return vocab

    def _detect_power_type(self, text: str) -> Optional[str]:
        """检测文本中的力量类型"""
        scores = {}

        for power_type, indicators in self.power_indicators.items():
            score = sum(1 for ind in indicators if ind in text)
            if score > 0:
                scores[power_type] = score

        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return None

    def _extract_terms(
        self, content: str, category: str, patterns: List[str]
    ) -> Dict[str, int]:
        """提取特定类别的词汇"""
        terms = Counter()

        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    term = "".join(match)
                else:
                    term = match

                # 过滤太短或太长的
                if len(term) < 3 or len(term) > 10:
                    continue

                # 过滤排除词
                if term in self.EXCLUDED_TERMS:
                    continue

                # 过滤包含否定词的
                if any(
                    w in term
                    for w in [
                        "无法",
                        "没有",
                        "不是",
                        "什么",
                        "怎么",
                        "这个",
                        "那个",
                        "一阵",
                        "玉石",
                        "石头",
                    ]
                ):
                    continue

                # 过滤纯数字开头的
                if term[0].isdigit() and not term.endswith(("重天", "阶", "级")):
                    continue

                terms[term] += 1

        return dict(terms)

    def _get_term_context(self, content: str, term: str) -> List[str]:
        """获取词汇上下文"""
        contexts = []

        pos = 0
        while len(contexts) < 3:
            idx = content.find(term, pos)
            if idx == -1:
                break

            start = max(0, idx - 30)
            end = min(len(content), idx + len(term) + 30)
            context = content[start:end]

            contexts.append(context)
            pos = idx + len(term)

        return contexts

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取词汇"""

        # 检测主要力量类型
        power_type = self._detect_power_type(content)
        if not power_type:
            return []

        results = []

        for category, patterns in self.term_patterns.items():
            terms = self._extract_terms(content, category, patterns)

            for term, frequency in terms.items():
                # 跳过已知词汇
                known = self.known_vocabulary.get(power_type, {}).get(category, [])
                is_known = term in known

                # 只保留高频词
                if frequency < 3:
                    continue

                contexts = self._get_term_context(content, term)

                results.append(
                    {
                        "term": term,
                        "category": category,
                        "power_type": power_type,
                        "frequency": frequency,
                        "contexts": contexts,
                        "novel_id": novel_id,
                        "is_known": is_known,
                    }
                )

        return results

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 去重合并"""
        # 按词汇聚合
        term_data = defaultdict(
            lambda: {
                "total_frequency": 0,
                "novel_ids": [],
                "all_contexts": [],
            }
        )

        for item in items:
            term = item.get("term")
            if term:
                term_data[term]["total_frequency"] += item.get("frequency", 0)
                term_data[term]["novel_ids"].append(item.get("novel_id", ""))
                term_data[term]["all_contexts"].extend(item.get("contexts", []))
                term_data[term]["category"] = item.get("category", "")
                term_data[term]["power_type"] = item.get("power_type", "")
                term_data[term]["is_known"] = item.get("is_known", False)

        # 排序输出
        results = []
        for term, data in sorted(
            term_data.items(), key=lambda x: x[1]["total_frequency"], reverse=True
        ):
            results.append(
                {
                    "term": term,
                    "category": data["category"],
                    "power_type": data["power_type"],
                    "total_frequency": data["total_frequency"],
                    "novel_count": len(set(data["novel_ids"])),
                    "sample_contexts": data["all_contexts"][:3],
                    "is_known": data["is_known"],
                }
            )

        return results


def extract_vocabulary(limit: int = None):
    """提取力量词汇"""
    extractor = VocabularyExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse
    from dataclasses import asdict

    parser = argparse.ArgumentParser(description="提取力量体系词汇")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.status:
        status = VocabularyExtractor().progress
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    else:
        extract_vocabulary(limit=args.limit)
