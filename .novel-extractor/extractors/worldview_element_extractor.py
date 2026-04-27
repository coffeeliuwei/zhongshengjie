"""
世界观元素提取器 v3.0

改进版：彻底解决噪音问题
- 移除"道"作为组织后缀（会误匹配说道/笑道等对话词）
- 添加对话标记词排除列表
- 严格的上下文检查（前面不能是动词）
- 只提取高频元素（出现次数>=阈值）
- 跨小说去重合并

提取地点、组织、势力等世界观元素的命名规律
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from base_extractor import BaseExtractor


class WorldviewElementExtractor(BaseExtractor):
    """世界观元素提取器 v2.0"""

    name = "worldview_element_extractor"

    # 最小出现频次阈值（避免提取偶现词）
    MIN_FREQUENCY = 3

    # 命名模式（v3.0: 移除"道"作为组织后缀，避免匹配对话词；v4.0: 新增科幻/现代/历史模式）
    ELEMENT_PATTERNS = {
        "地点": [
            # 常见地点后缀，需要是独立词而非句子片段
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(城|市|都|港|湾|府|岛|州|山|峰|谷|洞|宫|殿)(?![\u4e00-\u9fa5])",
            # 新增：科幻/异世界地点
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(星球|星域|星系|空间站|基地|要塞|遗址|秘境|禁地|圣地)(?![\u4e00-\u9fa5])",
            # 新增：现代地点
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(区|县|镇|村|街|路|园|楼|厦|广场)(?![\u4e00-\u9fa5])",
        ],
        "组织": [
            # 注意：移除了"道"，因为会误匹配"说道"、"笑道"等对话词
            # 如果需要匹配道教组织，使用"道宗"、"道门"等完整词
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(宗|门|派|会|教|社|盟|学院|团|阁|楼)(?![\u4e00-\u9fa5])",
            # 道教相关组织（完整匹配，避免对话词误匹配）
            r"(?<![，。！？\s])(道)(宗|门|教|派|盟|会|阁|楼)(?![\u4e00-\u9fa5])",
            # 新增：现代组织
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(集团|公司|协会|委员会|研究所|研究院|实验室|部队|军团|警察局|局|厅)(?![\u4e00-\u9fa5])",
            # 新增：学校
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(大学|学院|中学|小学|学校)(?![\u4e00-\u9fa5])",
        ],
        "势力": [
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(国|帝国|王国|邦|联盟|王朝)(?![\u4e00-\u9fa5])",
            # 新增：现代/科幻势力
            r"(?<![，。！？\s])([\u4e00-\u9fa5]{2,4})(联邦|共和国|星际联盟|星盟|财团|势力)(?![\u4e00-\u9fa5])",
        ],
    }

    # 排除的常见词（非世界观元素）- v3.0 扩展版
    EXCLUDED_WORDS = {
        # 常用词误匹配
        "不会",
        "不能",
        "不可",
        "没有",
        "无法",
        "无数",
        "不同",
        "多么",
        "什么",
        "这个",
        "那个",
        "某个",
        "哪个",
        "何处",
        "何时",
        "我们",
        "他们",
        "你们",
        "咱们",
        "自己",
        "别人",
        "他人",
        "一处",
        "两处",
        "多处",
        "此处",
        "彼处",
        "何处",
        "那个城",
        "这个城",
        "一座城",
        "那座城",
        "这座城",
        "什么城",
        "某座城",
        "哪个城",
        "那座山",
        "这座山",
        # 动词+后缀误匹配
        "走出城",
        "进入城",
        "离开城",
        "来到城",
        "返回城",
        "走出山",
        "进入山",
        "离开山",
        "来到山",
        # v3.0新增：对话标记词排除（高频噪音）
        # 说道/笑道/问道等对话词（之前误匹配为组织）
        "说道",
        "笑道",
        "问道",
        "答道",
        "叫道",
        "喊道",
        "嚷道",
        "叹道",
        "叹道",
        "吟道",
        "唱道",
        "念道",
        "嘀咕道",
        "嘀咕",
        "传音",
        "神识传音",
        "灵魂传音",
        "心中暗道",
        "心底暗道",
        "默默道",
        "淡笑道",
        "微笑道",
        "冷笑道",
        "苦笑道",
        "嬉笑道",
        "笑呵呵",
        "开口道",
        "连道",
        "摇头道",
        "点头道",
        "感叹道",
        "皱眉道",
        "疑惑道",
        "追问道",
        "询问道",
        "疑惑询问",
        "说道道",
        "说道的话",
        "对我说",
        "对他说",
        # 其他高频噪音词
        "也不知道",
        "也不知道",
        "我知道",
        "我也不知道",
        "可知",
        "也知",
        "我知",
        "不知",
        # 新增现代常用词（避免误匹配）
        "这个公司",
        "那个公司",
        "什么公司",
        "大学校",
        "中学生",
        "小学生",
        "实验室里",
    }

    # v3.0新增：排除的动词前缀（如果元素名以这些动词开头，则排除）
    EXCLUDED_PREFIXES = {
        "说",
        "笑",
        "问",
        "答",
        "叫",
        "喊",
        "嚷",
        "叹",
        "吟",
        "唱",
        "念",
        "淡",
        "微",
        "冷",
        "苦",
        "嬉",
        "皱",
        "疑惑",
        "追",
        "询",
        "感叹",
        "摇",
        "点",
        "嘀咕",
        "传音",
        "神识",
        "灵魂",
    }

    def __init__(self):
        super().__init__("worldview_element")

    def extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[Dict]:
        """
        从小说提取世界观元素（频次统计模式）

        改进：统计元素出现频次，只返回高频元素
        """
        novel_source = novel_id

        # 统计各类元素频次
        element_counts: Dict[str, Counter] = defaultdict(Counter)

        for element_type, patterns in self.ELEMENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for m in matches:
                    base = m.group(1)
                    suffix = m.group(2)
                    full_name = f"{base}{suffix}"

                    # 过滤排除词
                    if full_name in self.EXCLUDED_WORDS:
                        continue

                    # v3.0新增：排除以动词开头的词（对话标记词）
                    if any(
                        full_name.startswith(prefix)
                        for prefix in self.EXCLUDED_PREFIXES
                    ):
                        continue

                    # 过滤过短或过长的base
                    if len(base) < 2 or len(base) > 6:
                        continue

                    # 过滤纯数字开头的
                    if base[0].isdigit():
                        continue

                    element_counts[element_type][full_name] += 1

        # 只返回高频元素
        results: List[Dict] = []
        # 对话动词过滤正则
        _DIALOGUE_VERBS = re.compile(
            r'(说道|笑道|问道|答道|叫道|喊道|低声|大喝|轻声|暗道|心道|想道|沉声|冷声|怒道|嘲道|嗤道|叹道)'
        )
        for element_type, counter in element_counts.items():
            for element_name, count in counter.items():
                # 过滤掉对话动词组合
                if _DIALOGUE_VERBS.search(element_name):
                    continue
                # 过滤纯数字/标点/长度不合理的词
                if len(element_name) < 2 or len(element_name) > 12:
                    continue
                if re.fullmatch(r'[\d\s\W]+', element_name):
                    continue
                # 只保留达到频次阈值的元素
                if count >= self.MIN_FREQUENCY:
                    results.append(
                        {
                            "element_type": element_type,
                            "element_name": element_name,
                            "frequency": count,
                            "naming_pattern": element_name[-1],  # 后缀作为模式
                            "novel_source": novel_source,
                        }
                    )

        return results

    def process_extracted(self, items: List[Dict]) -> List[Dict]:
        """
        处理提取结果 - 跨小说去重合并

        改进：合并相同元素，累加频次，记录来源小说数
        """
        # 按元素名聚合
        element_data: Dict[str, Dict] = defaultdict(
            lambda: {
                "total_frequency": 0,
                "novel_ids": [],
                "element_type": "",
                "naming_pattern": "",
            }
        )

        for item in items:
            element_name = item.get("element_name")
            if element_name:
                element_data[element_name]["total_frequency"] += item.get(
                    "frequency", 0
                )
                element_data[element_name]["novel_ids"].append(
                    item.get("novel_source", "")
                )
                element_data[element_name]["element_type"] = item.get(
                    "element_type", ""
                )
                element_data[element_name]["naming_pattern"] = item.get(
                    "naming_pattern", ""
                )

        # 转换为结果列表，按频次排序
        results: List[Dict] = []
        for element_name, data in sorted(
            element_data.items(), key=lambda x: x[1]["total_frequency"], reverse=True
        ):
            # 只保留跨小说高频或单小说高频的元素
            novel_count = len(set(data["novel_ids"]))

            # 过滤条件：单小说达到 MIN_FREQUENCY 即保留（process_extracted 是按小说调用的）
            total_freq = data["total_frequency"]
            if total_freq >= self.MIN_FREQUENCY:
                results.append(
                    {
                        "element_type": data["element_type"],
                        "element_name": element_name,
                        "total_frequency": total_freq,
                        "novel_count": novel_count,
                        "naming_pattern": data["naming_pattern"],
                        "is_cross_novel": novel_count >= 2,  # 标记跨小说出现
                    }
                )

        # 按 element_name 去重，保留 frequency 最高的一条
        seen: dict = {}
        for item in results:
            name = item.get("element_name", "")
            if name not in seen or item.get("total_frequency", 0) > seen[name].get("total_frequency", 0):
                seen[name] = item
        return list(seen.values())

    def _infer_type(self, name: str) -> str:
        """推断元素类型（兼容旧代码）"""
        if name.endswith(
            (
                "城",
                "市",
                "都",
                "港",
                "湾",
                "府",
                "岛",
                "州",
                "山",
                "峰",
                "谷",
                "洞",
                "宫",
                "殿",
            )
        ):
            return "地点"
        if name.endswith(
            ("宗", "门", "派", "会", "教", "社", "道", "盟", "学院", "团", "阁", "楼")
        ):
            return "组织"
        if name.endswith(("国", "帝国", "王国", "邦", "联盟", "王朝")):
            return "势力"
        return "组织"
