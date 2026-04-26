"""
势力对话风格提取器

从小说中提取各势力的对话风格特征：
- 用词特征
- 句式特征
- 语气特征

用于Generator生成符合势力风格的角色对话
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter

from base_extractor import BaseExtractor
from config import (
    GENRE_TO_FACTION,
    FACTION_DIALOGUE_TRAITS,
    get_output_path,
    EXTRACTION_DIMENSIONS,
)


class DialogueStyleExtractor(BaseExtractor):
    """势力对话风格提取器"""

    def __init__(self):
        super().__init__("dialogue_style")

        # 对话提取正则
        self.dialogue_patterns = [
            r'"([^"]+)"',  # 双引号
            r"「([^」]+)」",  # 中文引号
            r"“([^”]+)”",  # 中文双引号
            r"『([^』]+)』",  # 书名号
        ]

        # 说话人识别正则
        self.speaker_patterns = [
            r'([^\s，。！？]+)[说道问答喊叫吼低沉]道[：:]?"',
            r'"([^"]+)"[，,]([^\s，。！？]+)[说道问答]',
            r"([^\s，。！？]+)[说道问答]：",
        ]

        # 加载已提取的案例库题材映射
        self.genre_novels = self._load_genre_mapping()

    def _load_genre_mapping(self) -> Dict[str, List[str]]:
        """加载题材-小说映射（从案例库）"""
        mapping = defaultdict(list)

        # 从案例库的sources.json加载（路径从 PROJECT_DIR 推导，不硬编码）
        from config import PROJECT_DIR
        sources_path = PROJECT_DIR / ".case-library" / "sources.json"
        if sources_path.exists():
            with open(sources_path, "r", encoding="utf-8") as f:
                sources = json.load(f)
            for source in sources.get("sources", []):
                genre = source.get("name", "")
                for path in source.get("novel_paths", []):
                    mapping[genre].append(path)

        return mapping

    def _detect_genre(self, novel_path: Path) -> Optional[str]:
        """检测小说题材（路径匹配）"""
        path_str = str(novel_path)

        for genre, keywords in [
            ("玄幻奇幻", ["玄幻", "奇幻", "东方玄幻", "异世大陆", "魔法"]),
            ("武侠仙侠", ["武侠", "仙侠", "修真", "洪荒"]),
            ("现代都市", ["都市", "现代", "职场", "娱乐"]),
            ("历史军事", ["历史", "军事", "架空", "战争"]),
            ("科幻灵异", ["科幻", "灵异", "末世", "时空"]),
            ("游戏竞技", ["游戏", "电竞", "网游"]),
            ("青春校园", ["校园", "青春", "恋爱"]),
            ("女频言情", ["言情", "古言", "现言", "穿越"]),
        ]:
            if any(kw in path_str for kw in keywords):
                return genre

        return "Z未分类"

    def _detect_genre_from_content(self, content: str) -> str:
        """从内容关键词检测题材（路径无法识别时的兜底）"""
        sample = content[:10000]
        genre_keywords = {
            "玄幻奇幻": ["修炼", "灵气", "魔力", "魔法", "境界", "宗门", "剑气", "元婴", "丹药", "异界"],
            "武侠仙侠": ["江湖", "内力", "武功", "侠客", "武林", "真气", "仙人", "渡劫", "飞升"],
            "现代都市": ["公司", "老板", "手机", "微信", "警察", "医院", "大学", "股票"],
            "历史军事": ["将军", "皇帝", "太子", "朝廷", "大臣", "圣旨", "皇宫", "兵马"],
            "科幻灵异": ["星球", "飞船", "机器人", "基因", "纳米", "星际", "AI", "量子"],
            "游戏竞技": ["玩家", "副本", "BOSS", "经验值", "装备", "NPC", "技能点"],
        }
        scores = {}
        for genre, keywords in genre_keywords.items():
            score = sum(1 for kw in keywords if kw in sample)
            if score > 0:
                scores[genre] = score
        if not scores:
            return "Z未分类"
        return max(scores.items(), key=lambda x: x[1])[0]

    def _extract_dialogues(self, content: str) -> List[Dict[str, Any]]:
        """提取对话片段"""
        dialogues = []

        for pattern in self.dialogue_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                dialogue = match.group(1).strip()
                if len(dialogue) > 5:  # 过滤太短的
                    # 尝试识别说话人
                    context_start = max(0, match.start() - 50)
                    context = content[context_start : match.start()]

                    speaker = self._extract_speaker(context)

                    dialogues.append(
                        {
                            "text": dialogue,
                            "speaker": speaker,
                            "length": len(dialogue),
                        }
                    )

        return dialogues

    def _extract_speaker(self, context: str) -> Optional[str]:
        """从上下文提取说话人"""
        for pattern in self.speaker_patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        return None

    def _analyze_dialogue_style(
        self, dialogues: List[Dict], faction: str
    ) -> Dict[str, Any]:
        """分析对话风格"""
        if not dialogues:
            return {}

        # 合并所有对话文本
        all_text = " ".join([d["text"] for d in dialogues])

        # 1. 用词特征提取
        word_features = self._extract_word_features(all_text, faction)

        # 2. 句式特征提取
        sentence_features = self._extract_sentence_features(all_text)

        # 3. 语气特征提取
        tone_features = self._extract_tone_features(all_text, dialogues)

        return {
            "faction": faction,
            "dialogue_count": len(dialogues),
            "word_features": word_features,
            "sentence_features": sentence_features,
            "tone_features": tone_features,
            "sample_dialogues": [d["text"][:200] for d in dialogues[:3]],
        }

    def _extract_word_features(self, text: str, faction: str) -> Dict[str, Any]:
        """提取用词特征"""
        # 已知的势力特征词
        known_traits = FACTION_DIALOGUE_TRAITS.get(faction, {})
        known_words = known_traits.get("用词特征", [])

        # 统计已知特征词出现频率
        word_freq = {}
        for word in known_words:
            count = text.count(word)
            if count > 0:
                word_freq[word] = count

        # 发现新的高频词（2-4字）
        # 简单分词
        words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)
        word_counter = Counter(words)

        # 过滤常用词
        common_words = {"的话", "只是", "一个", "不是", "没有", "这样", "什么", "怎么"}
        new_high_freq = [
            {"word": w, "count": c}
            for w, c in word_counter.most_common(50)
            if w not in common_words and c > 5 and w not in known_words
        ][:20]

        return {
            "known_word_frequency": word_freq,
            "new_high_frequency_words": new_high_freq,
        }

    def _extract_sentence_features(self, text: str) -> Dict[str, Any]:
        """提取句式特征"""
        # 按句号分割
        sentences = re.split(r"[。！？]", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return {}

        # 句长分布
        lengths = [len(s) for s in sentences]
        avg_length = sum(lengths) / len(lengths) if lengths else 0

        # 检测倒装句（简单规则）
        inverted_count = sum(1 for s in sentences if "之" in s or "者" in s)

        # 检测省略主语
        no_subject_count = sum(
            1 for s in sentences if not re.match(r"^[你我他她它咱]", s)
        )

        # 感叹句比例
        exclamation_ratio = text.count("！") / len(text) * 100 if text else 0

        return {
            "avg_sentence_length": round(avg_length, 1),
            "inverted_sentence_ratio": round(inverted_count / len(sentences) * 100, 1),
            "no_subject_ratio": round(no_subject_count / len(sentences) * 100, 1),
            "exclamation_ratio": round(exclamation_ratio, 2),
        }

    def _extract_tone_features(
        self, text: str, dialogues: List[Dict]
    ) -> Dict[str, Any]:
        """提取语气特征"""
        # 语气词统计
        tone_words = {
            "坚定": ["定要", "必定", "一定", "必然"],
            "疑问": ["吗", "呢", "何", "怎", "难道"],
            "感叹": ["啊", "呀", "哇", "哪"],
            "命令": ["给我", "快", "立刻", "马上"],
            "请求": ["请", "求", "望", "恳请"],
            "谦虚": ["在下", "鄙人", "不才", "愚见"],
        }

        tone_stats = {}
        for tone, words in tone_words.items():
            count = sum(text.count(w) for w in words)
            tone_stats[tone] = count

        # 对话长度分布
        dialogue_lengths = [d["length"] for d in dialogues]
        short_ratio = (
            sum(1 for l in dialogue_lengths if l < 20) / len(dialogue_lengths) * 100
        )
        long_ratio = (
            sum(1 for l in dialogue_lengths if l > 100) / len(dialogue_lengths) * 100
        )

        return {
            "tone_distribution": tone_stats,
            "short_dialogue_ratio": round(short_ratio, 1),  # <20字
            "long_dialogue_ratio": round(long_ratio, 1),  # >100字
        }

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        """从小说提取对话风格"""

        # 检测题材（路径优先，内容兜底）
        genre = self._detect_genre(novel_path)
        if genre == "Z未分类":
            genre = self._detect_genre_from_content(content)
        if genre == "Z未分类":
            return []

        # 映射到势力
        factions = GENRE_TO_FACTION.get(genre, [])
        if not factions:
            return []

        # 提取对话
        dialogues = self._extract_dialogues(content)
        if len(dialogues) < 50:  # 对话太少，跳过
            return []

        # 为每个势力分析风格
        results = []
        for faction in factions:
            style = self._analyze_dialogue_style(dialogues, faction)
            if style:
                style["novel_id"] = novel_id
                style["novel_path"] = str(novel_path)
                style["genre"] = genre
                results.append(style)

        return results

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 合并同一势力的风格"""
        # 按势力分组
        faction_styles = defaultdict(list)
        for item in items:
            faction = item.get("faction")
            if faction:
                faction_styles[faction].append(item)

        # 合并风格
        merged = []
        for faction, styles in faction_styles.items():
            merged_style = self._merge_faction_styles(faction, styles)
            merged.append(merged_style)

        return merged

    def _merge_faction_styles(self, faction: str, styles: List[dict]) -> dict:
        """合并同一势力的多个风格样本"""
        # 聚合用词频率
        all_word_freq = defaultdict(int)
        all_new_words = defaultdict(int)

        for s in styles:
            for word, count in (
                s.get("word_features", {}).get("known_word_frequency", {}).items()
            ):
                all_word_freq[word] += count

            for item in s.get("word_features", {}).get("new_high_frequency_words", []):
                all_new_words[item["word"]] += item["count"]

        # 计算平均句式特征
        avg_sentence_length = (
            sum(
                s.get("sentence_features", {}).get("avg_sentence_length", 0)
                for s in styles
            )
            / len(styles)
            if styles
            else 0
        )

        # 聚合语气分布
        tone_sum = defaultdict(int)
        for s in styles:
            for tone, count in (
                s.get("tone_features", {}).get("tone_distribution", {}).items()
            ):
                tone_sum[tone] += count

        # 合并示例对话
        all_samples = []
        for s in styles:
            all_samples.extend(s.get("sample_dialogues", []))

        return {
            "faction": faction,
            "novel_count": len(styles),
            "total_dialogues": sum(s.get("dialogue_count", 0) for s in styles),
            "word_features": {
                "known_word_frequency": dict(all_word_freq),
                "discovered_words": sorted(
                    [{"word": w, "count": c} for w, c in all_new_words.items()],
                    key=lambda x: x["count"],
                    reverse=True,
                )[:30],
            },
            "sentence_features": {
                "avg_sentence_length": round(avg_sentence_length, 1),
            },
            "tone_features": {
                "tone_distribution": dict(tone_sum),
            },
            "sample_dialogues": all_samples[:10],
            "style_summary": self._generate_style_summary(
                faction, all_word_freq, tone_sum
            ),
        }

    def _generate_style_summary(
        self, faction: str, word_freq: Dict[str, int], tone_dist: Dict[str, int]
    ) -> str:
        """生成风格摘要"""
        traits = FACTION_DIALOGUE_TRAITS.get(faction, {})

        # 基于数据生成摘要
        summary_parts = []

        # 用词特征
        if word_freq:
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:3]
            summary_parts.append(f"常用称呼：{', '.join([w[0] for w in top_words])}")

        # 语气特征
        if tone_dist:
            top_tone = max(tone_dist.items(), key=lambda x: x[1])
            summary_parts.append(f"语气倾向：{top_tone[0]}")

        # 已知特征
        if traits.get("语气特征"):
            summary_parts.append(f"风格：{traits['语气特征'][0]}")

        return "；".join(summary_parts) if summary_parts else "待分析"


# ==================== 入口函数 ====================


def extract_dialogue_styles(limit: int = None):
    """提取对话风格"""
    extractor = DialogueStyleExtractor()
    return extractor.run(limit=limit)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="提取势力对话风格")
    parser.add_argument("--limit", type=int, help="限制处理小说数量")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    if args.status:
        status = DialogueStyleExtractor().progress
        print(json.dumps(asdict(status), ensure_ascii=False, indent=2))
    else:
        extract_dialogue_styles(limit=args.limit)
