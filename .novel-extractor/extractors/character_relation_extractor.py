"""
Character relation extractor
Extracts co-occurrence relationships between characters from a novel/text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from base_extractor import BaseExtractor


_NER_MODEL = None  # spacy NER disabled by default

_STOPWORDS: frozenset = frozenset({
    # 方位/时间
    "之中", "之后", "之前", "之上", "之下",
    "之间", "之内", "之外", "之时", "之际",
    "其中", "其后", "其上", "其下", "其间",
    "以上", "以下", "以前", "以后", "以内", "以外",
    "此时", "此刻", "此处", "此地", "此后", "此前",
    "当时", "当下", "当初", "当年", "当日", "当场",
    "片刻", "顿时", "刹那", "瞬间",
    # 程度/频率副词
    "一般", "一直", "一共", "一切", "一起", "一同", "一旁",
    "一眼", "一声", "一步", "一口", "一手", "一身", "一脸",
    "一时", "一下", "一番", "一阵", "一丝", "一股",
    "不过", "不但", "不仅", "不只", "不由", "不禁", "不觉",
    "不得", "不能", "不会", "不是", "不知", "不见", "不少",
    "不断", "不停", "不住", "不敢", "不曾",
    "只是", "只有", "只见", "只能", "只好",
    "已经", "已然", "还是", "还有", "还未",
    "却是", "却又", "便是", "便有",
    "而是", "而且", "而后",
    "虽然", "虽是", "虽说", "但是", "但却",
    "因为", "因此", "所以", "所有", "所谓",
    "如果", "如此", "如同", "如今",
    "似乎", "好像", "好似",
    "突然", "忽然", "猛然", "蓦然",
    "终于", "终究", "竟然", "居然", "果然",
    "慢慢", "缓缓", "渐渐", "轻轻", "静静", "默默",
    # 代词
    "自己", "自身", "本人",
    "大家", "众人", "旁人", "他人", "别人",
    "这里", "那里", "这边", "那边",
    "这些", "那些", "这个", "那个", "哪个", "某个",
    "什么", "怎么", "如何", "为何", "哪里", "何处", "何时",
    # 感官/心理动词
    "知道", "看到", "听到", "感到", "想到",
    "心中", "心里", "心头", "脑海",
    "眼中", "眼里", "眼前", "眼神",
    "身上", "身旁", "身后", "身边", "身体",
    "手中", "手里", "手上", "脸上", "脸色",
    # 修炼相关
    "力量", "能力", "实力",
    "修炼", "修为", "修行",
    "境界", "层次", "等级",
    "气息", "气势", "气场",
    "神识", "灵识", "灵魂",
    # 序列
    "第一", "第二", "第三", "第四", "第五",
    "这一", "那一",
    # 杂项
    "按理", "事情", "问题", "东西", "时候",
    "地方", "办法", "样子", "开口", "开始",
    "上来", "下来", "出来", "进来", "回来",
    "上去", "下去", "出去", "进去", "回去",
    "仍然", "乃至", "以及", "甚至",
    "心翼翼", "翼翼",
    # 说话修饰词/状语（出现在"X 说道"位置但非人名）
    "忍不住", "忍不",
    "急忙", "赶忙", "连忙",
    "随即", "当即",
    "淡淡", "冷冷", "轻轻", "低声", "大声", "柔声",
    "暗暗", "闻言",
    "沉默", "沉吟", "沉思",
    "微微", "略微",
    "哈哈", "呵呵", "嘿嘿",
    "良久", "良久才",
    # 姿态/动作词（常出现在"X 道"前）
    "含笑", "拱手", "抱拳", "躬身", "欠身",
    "皱眉", "挑眉", "摇头", "点头",
    "冷哼", "嗤笑", "讪笑",
})

_BAD_START: frozenset = frozenset(
    "之一不没只而但却也都就又已更还"
    "因被对在于从到与和或如若虽即则"
    "以为可所其该此这那何谁哪"
    "是有无了啊哦呢吗吧"
    "他她它"  # 人称代词开头几乎不是名字
)

_BAD_END: frozenset = frozenset(
    "奇极尽皆然始止竟归终反"
    "了的地得着过吗呢吧"
    "疑惑翼识住"
)

# 说话动词：复合词排在简单词前，防止贪婪截断
_SAYING_VERBS = (
    "苦笑道|讪笑道|冷笑道|微笑道|大笑道|哈哈道"
    "|低声道|沉声道|轻声道|和声道|点头道|摇头道"
    "|冷冷道|淡淡道|缓缓道|慢慢道"
    "|说道|笑道|问道|答道|喝道|怒道|冷道|叫道|哼道"
)

_LEFT_BOUNDARY = r'(?:^|(?<=[，。！？、\s"\'（【「『]))'


def _is_valid_name(nm: str) -> bool:
    if not nm or len(nm) < 2:
        return False
    if nm in _STOPWORDS:
        return False
    if nm[0] in _BAD_START:
        return False
    if nm[-1] in _BAD_END:
        return False
    return True


def _detect_names(text: str) -> List[str]:
    """Extract character names from high-precision context patterns."""
    names = set()

    # Pattern 1: [boundary] X 说道/笑道/... — {2,3}? 非贪婪优先短名
    pat1 = _LEFT_BOUNDARY + r'([一-龥]{2,3}?)(?:' + _SAYING_VERBS + r')'
    for nm in re.findall(pat1, text, re.MULTILINE):
        if _is_valid_name(nm):
            names.add(nm)

    # Pattern 2: 叫做/名叫/名为/称为/唤作 X
    for nm in re.findall(
        r'(?:叫做|名叫|名为|称为|唤作)([一-龥]{2,3})',
        text
    ):
        if _is_valid_name(nm):
            names.add(nm)

    return sorted(names)[:50]


def _split_chapters(novel_text: str) -> Dict[int, str]:
    chapters: Dict[int, str] = {}
    cur = 0
    buf: List[str] = []
    for line in novel_text.splitlines():
        if re.search(
            r"第[一二三四五六七八九十百零\d]+章|第\d+章|Chapter\s*\d+",
            line
        ):
            if buf:
                chapters[cur] = "\n".join(buf).strip()
                buf = []
            cur += 1
        else:
            buf.append(line)
    if buf:
        chapters[cur] = "\n".join(buf).strip()
    return {k: v for k, v in chapters.items() if v}


def _sentences(text: str) -> List[str]:
    parts = re.split(r"[。？！.!?]", text)
    return [p.strip() for p in parts if p.strip()]


def _contexts_for_pair(chunk: str, a: str, b: str, chapter_id: int) -> List[str]:
    outs: List[str] = []
    for s in _sentences(chunk):
        if a in s and b in s:
            outs.append(f"[Chapter {chapter_id}] {s.strip()}")
    return outs


class CharacterRelationExtractor(BaseExtractor):
    """Builds a character co-occurrence graph from novel text."""

    name = "character_relation_extractor"

    def __init__(self):
        super().__init__("character_relation")

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]:
        chapters = _split_chapters(content)
        cooc_map: Dict[Tuple[str, str], Dict[str, object]] = {}

        for cid, chunk in chapters.items():
            names_in_chunk = _detect_names(chunk)
            for i in range(len(names_in_chunk)):
                for j in range(i + 1, len(names_in_chunk)):
                    c1, c2 = sorted([names_in_chunk[i], names_in_chunk[j]])
                    key = (c1, c2)
                    if key not in cooc_map:
                        cooc_map[key] = {"count": 0, "contexts": []}
                    cooc_map[key]["count"] += 1
                    ctxs = _contexts_for_pair(
                        chunk, names_in_chunk[i], names_in_chunk[j], cid
                    )
                    if ctxs:
                        cooc_map[key]["contexts"].extend(ctxs)

        records: List[Dict[str, object]] = []
        for (c1, c2), data in cooc_map.items():
            seen: set = set()
            ctxs_out: List[str] = []
            for ctxt in data["contexts"]:
                if ctxt not in seen:
                    ctxs_out.append(ctxt)
                    seen.add(ctxt)
            records.append({
                "character1": c1,
                "character2": c2,
                "cooccurrence_count": int(data["count"]),
                "cooccurrence_contexts": ctxs_out,
            })

        return records

    def process_extracted(self, items: List[dict]) -> List[dict]:
        if not items:
            return []
        min_count = self.config.extractor_config.get("min_cooccurrence", 2)
        filtered = [i for i in items if i.get("cooccurrence_count", 0) >= min_count]
        for item in filtered:
            item["cooccurrence_contexts"] = item.get("cooccurrence_contexts", [])[:5]
        return filtered
