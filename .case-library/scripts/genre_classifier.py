#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题材自动分类器 v1.0
=====================================

自动识别小说题材类型，支持：
- 基于文件名/目录名推断
- 基于内容关键词分析
- 混合策略（优先级：目录 > 文件名 > 内容）

使用方法：
    from genre_classifier import GenreClassifier

    classifier = GenreClassifier()
    genre = classifier.classify("盘龙.txt", content)
    # 返回: "玄幻奇幻"
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from collections import Counter


class GenreClassifier:
    """题材自动分类器"""

    # 题材关键词特征
    GENRE_KEYWORDS = {
        "玄幻奇幻": {
            "核心词": [
                "灵气",
                "修炼",
                "境界",
                "丹药",
                "法宝",
                "灵石",
                "元婴",
                "金丹",
                "神识",
                "渡劫",
                "飞升",
                "仙界",
                "魔修",
                "妖兽",
                "灵根",
                "斗气",
                "魂力",
                "血脉",
                "天赋",
                "觉醒",
                "传承",
                "秘境",
                "位面",
                "神格",
                "神域",
                "法则",
                "道韵",
                "造化",
            ],
            "文件名特征": [
                "斗破",
                "盘龙",
                "莽荒",
                "遮天",
                "完美",
                "圣墟",
                "永生",
                "仙逆",
                "凡人",
                "修仙",
                "修真",
                "仙侠",
                "玄幻",
                "神墓",
                "武动",
                "大主宰",
                "斗罗",
                "星辰",
                "武神",
                "战神",
            ],
        },
        "武侠仙侠": {
            "核心词": [
                "内力",
                "武功",
                "江湖",
                "门派",
                "剑法",
                "刀法",
                "拳法",
                "轻功",
                "点穴",
                "经脉",
                "丹田",
                "真气",
                "侠客",
                "侠义",
                "飞剑",
                "剑修",
                "筑基",
                "结丹",
                "化神",
                "炼气",
                "御剑",
                "符箓",
                "阵法",
                "灵兽",
                "洞府",
                "宗门",
                "长老",
                "弟子",
            ],
            "文件名特征": [
                "武侠",
                "江湖",
                "剑神",
                "剑仙",
                "刀神",
                "神雕",
                "天龙",
                "笑傲",
                "倚天",
                "射雕",
                "武林",
                "少林",
                "武当",
                "峨眉",
            ],
        },
        "现代都市": {
            "核心词": [
                "公司",
                "总裁",
                "董事长",
                "投资",
                "股市",
                "商业",
                "职场",
                "都市",
                "白领",
                "咖啡",
                "地铁",
                "公寓",
                "别墅",
                "豪车",
                "网红",
                "直播",
                "流量",
                "粉丝",
                "娱乐圈",
                "明星",
                "歌手",
                "医生",
                "律师",
                "警察",
                "记者",
                "设计师",
                "程序员",
            ],
            "文件名特征": [
                "都市",
                "总裁",
                "豪门",
                "娱乐",
                "明星",
                "重生之都市",
                "都市仙医",
                "都市最强",
                "超级都市",
            ],
        },
        "历史军事": {
            "核心词": [
                "朝代",
                "皇帝",
                "将军",
                "战争",
                "军队",
                "骑兵",
                "步兵",
                "攻城",
                "谋略",
                "兵法",
                "战役",
                "疆场",
                "边疆",
                "朝堂",
                "科举",
                "状元",
                "丞相",
                "尚书",
                "将军",
                "都督",
                "太守",
                "三国",
                "唐宋",
                "明清",
                "战国",
                "春秋",
                "乱世",
                "起义",
            ],
            "文件名特征": [
                "三国",
                "大明",
                "大唐",
                "大宋",
                "战国",
                "秦朝",
                "汉末",
                "历史",
                "穿越之",
                "重生之",
                "军事",
                "战争",
                "铁血",
            ],
        },
        "科幻灵异": {
            "核心词": [
                "星际",
                "宇宙",
                "飞船",
                "外星",
                "科技",
                "机甲",
                "虫族",
                "光年",
                "黑洞",
                "跃迁",
                "基地",
                "联邦",
                "帝国",
                "文明",
                "鬼魂",
                "灵异",
                "诡异",
                "僵尸",
                "妖怪",
                "阴阳",
                "风水",
                "诅咒",
                "封印",
                "驱魔",
                "捉鬼",
                "道士",
                "和尚",
                "佛法",
            ],
            "文件名特征": [
                "星际",
                "机甲",
                "科幻",
                "末世",
                "废土",
                "灵异",
                "鬼吹灯",
                "盗墓",
                "茅山",
                "阴阳",
                "诡异",
            ],
        },
        "青春校园": {
            "核心词": [
                "学校",
                "班级",
                "同学",
                "老师",
                "考试",
                "高考",
                "大学",
                "校园",
                "宿舍",
                "食堂",
                "操场",
                "篮球",
                "运动会",
                "社团",
                "暗恋",
                "初恋",
                "表白",
                "情侣",
                "男朋友",
                "女朋友",
                "青春",
                "毕业",
                "回忆",
                "成长",
                "友情",
            ],
            "文件名特征": [
                "校园",
                "青春",
                "校花",
                "校草",
                "学霸",
                "同桌",
                "同学",
                "班级",
                "高中",
                "大学",
                "青春校园",
            ],
        },
        "游戏竞技": {
            "核心词": [
                "游戏",
                "玩家",
                "副本",
                "装备",
                "等级",
                "技能",
                "BOSS",
                "公会",
                "团队",
                "PK",
                "竞技",
                "电竞",
                "职业",
                "主播",
                "直播",
                "战队",
                "比赛",
                "冠军",
                "选手",
                "教练",
                "网游",
                "页游",
                "手游",
                "VR",
                "AR",
                "元宇宙",
            ],
            "文件名特征": [
                "网游",
                "游戏",
                "电竞",
                "全职高手",
                "竞技",
                "副本",
                "职业玩家",
                "从零开始",
            ],
        },
        "女频言情": {
            "核心词": [
                "王爷",
                "王妃",
                "皇后",
                "宫斗",
                "宅斗",
                "嫡女",
                "庶女",
                "宠文",
                "甜文",
                "虐文",
                "穿越女",
                "重生女",
                "总裁",
                "豪门",
                "千金",
                "少爷",
                "少爷",
                "婚恋",
                "闺蜜",
                "姐妹",
                "婆婆",
                "妯娌",
                "婆媳",
            ],
            "文件名特征": [
                "王妃",
                "皇后",
                "嫡女",
                "庶女",
                "宫斗",
                "宅斗",
                "重生之",
                "穿越之",
                "豪门",
                "总裁",
                "甜宠",
                "言情小说",
            ],
        },
    }

    # 题材列表
    GENRES = list(GENRE_KEYWORDS.keys())

    def __init__(self):
        # 预编译正则
        self._compile_patterns()

    def _compile_patterns(self):
        """预编译正则模式"""
        self.genre_patterns = {}
        for genre, keywords in self.GENRE_KEYWORDS.items():
            core_words = keywords.get("核心词", [])
            file_features = keywords.get("文件名特征", [])

            # 编译内容匹配模式
            core_pattern = "|".join(re.escape(w) for w in core_words)
            self.genre_patterns[genre] = {
                "content": re.compile(core_pattern, re.IGNORECASE),
                "filename": file_features,
            }

    def classify_by_path(self, file_path: Path) -> Optional[str]:
        """
        基于路径推断题材

        优先级：目录名 > 文件名
        """
        path_str = str(file_path).lower()
        filename = file_path.name.lower()

        # 检查路径中的目录名
        for genre, patterns in self.genre_patterns.items():
            for feature in patterns["filename"]:
                if feature.lower() in path_str:
                    return genre

        return None

    def classify_by_content(
        self, content: str, top_n: int = 2000
    ) -> Tuple[str, Dict[str, int]]:
        """
        基于内容关键词统计推断题材

        Returns:
            (题材, 各题材得分)
        """
        if not content or len(content) < 500:
            return "玄幻奇幻", {}  # 默认

        # 只分析前N字符（提高效率）
        sample = content[:top_n]

        scores = {}
        for genre, patterns in self.genre_patterns.items():
            matches = patterns["content"].findall(sample)
            scores[genre] = len(matches)

        # 返回得分最高的题材
        if scores:
            best_genre = max(scores, key=scores.get)
            if scores[best_genre] > 0:
                return best_genre, scores

        return "玄幻奇幻", scores  # 默认

    def classify(
        self, file_path: Path, content: str = None, source_genre: str = None
    ) -> Tuple[str, str]:
        """
        综合分类（优先级：数据源 > 目录名 > 文件名 > 内容）

        Args:
            file_path: 文件路径
            content: 文件内容（可选）
            source_genre: 数据源定义的题材（可选）

        Returns:
            (题材, 分类依据)
        """
        # 1. 最高优先级：数据源定义
        if source_genre and source_genre in self.GENRES:
            return source_genre, "数据源定义"

        # 2. 次优先级：路径推断
        path_genre = self.classify_by_path(file_path)
        if path_genre:
            return path_genre, "路径推断"

        # 3. 兜底：内容分析
        if content:
            content_genre, scores = self.classify_by_content(content)
            return content_genre, "内容分析"

        # 4. 最终默认
        return "玄幻奇幻", "默认值"

    def get_genre_confidence(self, content: str, claimed_genre: str) -> float:
        """
        验证题材置信度

        Returns:
            0.0-1.0 的置信度分数
        """
        if not content or claimed_genre not in self.genre_patterns:
            return 0.5

        sample = content[:3000]
        pattern = self.genre_patterns[claimed_genre]["content"]
        matches = pattern.findall(sample)

        # 关键词密度
        density = len(matches) / len(sample) * 1000

        # 归一化到0-1
        confidence = min(density / 10, 1.0)
        return round(confidence, 2)

    def suggest_genres(
        self, file_path: Path, content: str = None
    ) -> List[Tuple[str, float]]:
        """
        建议可能的题材列表

        Returns:
            [(题材, 置信度), ...]
        """
        suggestions = []

        # 路径推断
        path_genre = self.classify_by_path(file_path)
        if path_genre:
            suggestions.append((path_genre, 0.8))

        # 内容分析
        if content:
            _, scores = self.classify_by_content(content)
            total = sum(scores.values()) or 1
            for genre, score in sorted(scores.items(), key=lambda x: -x[1]):
                if score > 0:
                    confidence = score / total
                    suggestions.append((genre, confidence))

        # 去重并排序
        seen = set()
        unique = []
        for genre, conf in suggestions:
            if genre not in seen:
                seen.add(genre)
                unique.append((genre, conf))

        return unique[:3]


def main():
    """测试"""
    import argparse

    parser = argparse.ArgumentParser(description="题材分类器")
    parser.add_argument("--file", "-f", type=str, help="文件路径")
    parser.add_argument("--content", "-c", type=str, help="测试内容")

    args = parser.parse_args()

    classifier = GenreClassifier()

    if args.file:
        path = Path(args.file)
        content = None

        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except:
                try:
                    with open(path, "r", encoding="gbk") as f:
                        content = f.read()
                except:
                    pass

        genre, basis = classifier.classify(path, content)
        print(f"文件: {path.name}")
        print(f"题材: {genre}")
        print(f"依据: {basis}")

        suggestions = classifier.suggest_genres(path, content)
        print(f"\n建议:")
        for g, conf in suggestions:
            print(f"  {g}: {conf:.0%}")

    elif args.content:
        genre, scores = classifier.classify_by_content(args.content)
        print(f"题材: {genre}")
        print(f"得分: {scores}")


if __name__ == "__main__":
    main()
