"""
创作技法精炼提取器

从原始小说库中精炼提取创作技法：
- 方法1: 从案例库反推技法（分析256,083条案例的共性模式）
- 方法2: 从高质量小说直接提取技法

提取后的技法合并到 众生界/创作技法/ 目录
"""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))
from base_extractor import BaseExtractor

# 技法维度（与现有技法库对齐）
TECHNIQUE_DIMENSIONS = [
    "世界观维度",
    "剧情维度",
    "人物维度",
    "战斗冲突维度",
    "氛围意境维度",
    "叙事维度",
    "主题维度",
    "情感维度",
    "读者体验维度",
    "元维度",
    "节奏维度",
]

# 场景到技法的映射（扩展版）
SCENE_TO_TECHNIQUE = {
    "打脸场景": ["冲突升级", "情绪转折", "对比强化", "节奏控制", "期待反转"],
    "高潮场景": ["情绪爆发", "多线汇聚", "伏笔回收", "张力释放", "节奏加速"],
    "开篇场景": ["悬念设置", "世界观植入", "人物出场", "黄金三章", "钩子设计"],
    "战斗场景": ["动作描写", "节奏控制", "力量展示", "代价设计", "战术逻辑"],
    "对话场景": ["潜台词", "性格展示", "信息传递", "冲突表达", "节奏调节"],
    "情感场景": ["情感铺垫", "情绪渲染", "细节描写", "心理刻画", "氛围营造"],
    "悬念场景": ["信息遮蔽", "伏笔设置", "节奏控制", "期待管理", "谜题设计"],
    "转折场景": ["意外设计", "情绪转折", "伏笔回收", "认知反转", "节奏突变"],
    "心理场景": ["内心独白", "情感层次", "动机揭示", "性格深化", "意识流"],
    "环境场景": ["氛围营造", "情景交融", "象征暗示", "感官描写", "意境渲染"],
    "人物出场": ["第一印象", "性格暗示", "背景铺垫", "关系预设", "形象塑造"],
    "修炼突破": ["铺垫设计", "顿悟描写", "代价付出", "实力展示", "节奏把控"],
    "势力登场": ["势力塑造", "冲突预设", "利益展示", "人物群像", "信息铺垫"],
    "资源获取": ["机缘设计", "竞争描写", "价值展示", "后续铺垫", "爽感营造"],
}

# 技法关键词识别（扩展版）
TECHNIQUE_KEYWORDS = {
    # 冲突类
    "冲突升级": ["矛盾", "冲突", "对峙", "压制", "反弹", "激化", "升级", "恶化"],
    "期待反转": ["没想到", "出乎意料", "竟然", "原来", "却不知"],
    # 情绪类
    "情绪转折": ["突然", "猛然", "怔住", "沉默", "变化", "愣住", "一愣"],
    "情绪爆发": ["怒吼", "咆哮", "颤抖", "崩溃", "爆发", "失控", "发泄"],
    "情绪渲染": ["心头一震", "心中涌起", "感到一阵", "莫名地", "不禁"],
    # 对比类
    "对比强化": ["不屑", "嘲讽", "震惊", "不可思议", "目瞪口呆", "难以置信"],
    # 节奏类
    "节奏控制": ["缓缓", "骤然", "瞬间", "良久", "片刻", "渐渐", "猛地"],
    "节奏加速": ["紧接着", "随即", "立刻", "马上", "转眼间"],
    "节奏突变": ["忽然", "陡然", "霎时", "刹那", "一瞬"],
    "节奏调节": ["稍微", "略微", "稍微停顿", "顿了顿"],
    # 伏笔类
    "伏笔设置": ["暗示", "提及", "想起", "记得", "回忆", "似乎", "仿佛"],
    "伏笔回收": ["原来", "之所以", "难怪", "终于明白", "这才明白", "终于知道"],
    # 悬念类
    "悬念设置": ["未知", "神秘", "疑惑", "不解", "猜测", "谜团", "困惑"],
    "信息遮蔽": ["没有说", "并未提及", "不得而知", "无从得知"],
    "谜题设计": ["谜底", "真相", "答案", "解开"],
    # 代价类
    "代价设计": ["代价", "损伤", "消耗", "透支", "反噬", "牺牲", "付出"],
    "代价付出": ["脸色苍白", "嘴角溢血", "身受重伤", "元气大伤"],
    # 对话类
    "潜台词": ["话中有话", "意有所指", "弦外之音"],
    "信息传递": ["透露", "告知", "说明", "解释"],
    # 心理类
    "内心独白": ["心想", "思量", "暗道", "心中", "内心", "暗想"],
    "情感层次": ["先是", "继而", "最后", "先是疑惑继而"],
    "动机揭示": ["之所以", "是因为", "原因在于"],
    # 环境类
    "氛围营造": ["空气中", "四周", "弥漫着", "笼罩"],
    "感官描写": ["看到", "听到", "闻到", "感受到", "触到"],
    "意境渲染": ["宛如", "仿佛", "如同", "好像"],
    # 人物类
    "第一印象": ["首先", "第一眼", "初次", "第一次看到"],
    "性格暗示": ["性格", "脾气", "行事风格", "为人"],
    # 战斗类
    "动作描写": ["挥动", "劈向", "刺出", "闪避", "格挡"],
    "战术逻辑": ["判断", "分析", "计算", "策略"],
    # 世界观类
    "世界观植入": ["传说", "据说", "记载", "自古以来"],
    "力量展示": ["施展", "催动", "运转", "激发"],
    # 结构类
    "黄金三章": ["开篇", "悬念", "钩子", "吸引"],
    "钩子设计": ["为什么", "如何", "什么"],
    "多线汇聚": ["与此同时", "另一边", "与此同时"],
    "张力释放": ["终于", "成功", "解决", "突破"],
}


@dataclass
class ExtractedTechnique:
    """提取的技法"""

    name: str
    dimension: str
    description: str
    source_scene: str
    example_count: int
    examples: List[str]
    keywords: List[str]
    source_novels: List[str]


class TechniqueExtractor(BaseExtractor):
    """创作技法精炼提取器"""

    def __init__(self):
        super().__init__("technique")
        self.case_library_dir = (
            Path(__file__).parent.parent.parent / ".case-library" / "cases"
        )
        self.technique_dir = Path(__file__).parent.parent.parent / "创作技法"
        self.extracted_techniques: Dict[str, ExtractedTechnique] = {}

    def extract_from_novel(self, content: str, novel_id: str, novel_path) -> List[dict]:
        """从单本小说提取技法线索"""
        techniques = []

        # 识别场景类型
        for scene_type, tech_list in SCENE_TO_TECHNIQUE.items():
            # 检测是否包含该场景的关键词
            if self._detect_scene(content, scene_type):
                for tech_name in tech_list:
                    # 检测技法关键词
                    keywords = TECHNIQUE_KEYWORDS.get(tech_name, [])
                    matches = []
                    for kw in keywords:
                        if kw in content:
                            matches.append(kw)

                    if matches:
                        # 提取上下文示例
                        examples = self._extract_examples(
                            content, matches, max_examples=3
                        )

                        techniques.append(
                            {
                                "technique_name": tech_name,
                                "scene_type": scene_type,
                                "keywords_matched": matches,
                                "examples": examples,
                                "novel_id": novel_id,
                                "novel_path": str(novel_path),
                            }
                        )

        return techniques

    def _detect_scene(self, content: str, scene_type: str) -> bool:
        """检测内容是否包含特定场景"""
        scene_keywords = {
            "打脸场景": ["不屑", "嘲讽", "废物", "震惊", "不可思议"],
            "高潮场景": ["决战", "终极", "生死", "爆发", "巅峰"],
            "开篇场景": [],  # 通常在开头
            "战斗场景": ["攻击", "防御", "招式", "力量", "击中"],
            "对话场景": ['"', "「", "道", "说", "问"],
            "情感场景": ["心", "情", "爱", "恨", "泪"],
            "悬念场景": ["为何", "究竟", "难道", "难道说", "未知"],
            "转折场景": ["突然", "没想到", "竟然", "居然", "原来"],
            "心理场景": ["心想", "思量", "暗道", "心中", "内心"],
            "环境场景": ["天空", "大地", "山峰", "森林", "河流"],
        }

        keywords = scene_keywords.get(scene_type, [])
        return any(kw in content for kw in keywords)

    def _extract_examples(
        self, content: str, keywords: List[str], max_examples: int = 3
    ) -> List[str]:
        """提取包含关键词的上下文示例"""
        examples = []

        for kw in keywords:
            # 找到关键词位置
            idx = content.find(kw)
            if idx != -1:
                # 提取前后各100字的上下文
                start = max(0, idx - 100)
                end = min(len(content), idx + len(kw) + 100)
                context = content[start:end].strip()

                if len(context) > 50:
                    examples.append(context)

                if len(examples) >= max_examples:
                    break

        return examples

    def process_extracted(self, items: List[dict]) -> List[dict]:
        """处理提取结果 - 合并同类技法"""
        # 按技法名称分组
        technique_groups = defaultdict(list)

        for item in items:
            tech_name = item.get("technique_name", "")
            if tech_name:
                technique_groups[tech_name].append(item)

        # 合并处理
        results = []
        for tech_name, tech_items in technique_groups.items():
            if len(tech_items) < 2:  # 至少2次出现才认为是有效技法
                continue

            # 聚合信息
            all_examples = []
            all_novels = []
            all_keywords = set()
            scene_types = set()

            for item in tech_items:
                all_examples.extend(item.get("examples", []))
                all_novels.append(item.get("novel_id", ""))
                all_keywords.update(item.get("keywords_matched", []))
                scene_types.add(item.get("scene_type", ""))

            # 去重
            unique_examples = list(dict.fromkeys(all_examples))[:5]
            unique_novels = list(dict.fromkeys(all_novels))[:10]

            # 确定技法维度
            dimension = self._infer_dimension(tech_name, list(scene_types))

            # 生成技法描述
            description = self._generate_description(
                tech_name, dimension, unique_examples
            )

            results.append(
                {
                    "technique_name": tech_name,
                    "dimension": dimension,
                    "description": description,
                    "keywords": list(all_keywords),
                    "example_count": len(unique_examples),
                    "examples": unique_examples[:3],
                    "source_novels": unique_novels,
                    "source_scenes": list(scene_types),
                    "occurrence_count": len(tech_items),
                }
            )

        # 按出现次数排序
        results.sort(key=lambda x: x["occurrence_count"], reverse=True)

        return results

    def _infer_dimension(self, tech_name: str, scene_types: List[str]) -> str:
        """推断技法所属维度"""
        # 基于技法名称推断
        if any(kw in tech_name for kw in ["冲突", "战斗", "代价"]):
            return "战斗冲突维度"
        elif any(kw in tech_name for kw in ["情绪", "情感"]):
            return "情感维度"
        elif any(kw in tech_name for kw in ["悬念", "伏笔", "转折"]):
            return "剧情维度"
        elif any(kw in tech_name for kw in ["节奏", "控制"]):
            return "节奏维度"
        elif any(kw in tech_name for kw in ["氛围", "环境"]):
            return "氛围意境维度"
        elif any(kw in tech_name for kw in ["对比", "强化"]):
            return "叙事维度"
        else:
            # 基于场景类型推断
            if "打脸" in scene_types or "高潮" in scene_types:
                return "剧情维度"
            elif "战斗" in scene_types:
                return "战斗冲突维度"
            elif "对话" in scene_types:
                return "人物维度"
            else:
                return "叙事维度"

    def _generate_description(
        self, tech_name: str, dimension: str, examples: List[str]
    ) -> str:
        """生成技法描述"""
        templates = {
            "冲突升级": "通过层层递进的矛盾冲突，逐步提升故事张力",
            "情绪转折": "利用突发的情节变化，实现情绪的剧烈转折",
            "对比强化": "通过前后对比，强化情节的冲击力",
            "节奏控制": "精准把控叙事节奏，张弛有度",
            "伏笔设置": "巧妙埋下线索，为后续情节发展铺垫",
            "伏笔回收": "在关键时刻揭示前文伏笔，产生顿悟感",
            "悬念设置": "通过信息遮蔽，激发读者的好奇心",
            "情绪爆发": "积累情绪后集中释放，形成高潮",
            "代价设计": "让角色付出代价，增强真实感和代入感",
        }

        return templates.get(tech_name, f"{tech_name}技法，{dimension}的重要组成部分")

    def extract_from_case_library(self, limit: int = None) -> List[dict]:
        """从案例库反推技法"""
        results = []

        if not self.case_library_dir.exists():
            return results

        # 遍历场景目录
        for scene_dir in self.case_library_dir.iterdir():
            if not scene_dir.is_dir():
                continue

            scene_type = scene_dir.name
            if scene_type not in SCENE_TO_TECHNIQUE:
                continue

            # 读取案例文件
            case_files = list(scene_dir.glob("*.txt"))
            if limit:
                case_files = case_files[:limit]

            for case_file in case_files:
                try:
                    with open(case_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 分析案例中的技法痕迹
                    techniques = SCENE_TO_TECHNIQUE.get(scene_type, [])
                    for tech_name in techniques:
                        keywords = TECHNIQUE_KEYWORDS.get(tech_name, [])
                        matches = [kw for kw in keywords if kw in content]

                        if matches:
                            results.append(
                                {
                                    "technique_name": tech_name,
                                    "scene_type": scene_type,
                                    "keywords_matched": matches,
                                    "source": str(case_file),
                                    "source_type": "case_library",
                                }
                            )
                except Exception:
                    continue

        return results

    def save_to_technique_library(self, techniques: List[dict]) -> int:
        """保存技法到技法库"""
        output_dir = self.technique_dir / "99-从小说提取"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 按维度分组保存
        by_dimension = defaultdict(list)
        for tech in techniques:
            by_dimension[tech["dimension"]].append(tech)

        saved_count = 0
        for dimension, tech_list in by_dimension.items():
            # 创建维度文件
            safe_dim_name = dimension.replace("/", "-")
            output_file = output_dir / f"{safe_dim_name}.md"

            lines = [f"# {dimension} - 从小说提取的技法\n\n"]
            lines.append(f"> 自动提取自 E:\\小说资源 (6,245本小说)\n\n")
            lines.append(f"## 技法列表 ({len(tech_list)}个)\n\n")

            for tech in tech_list:
                lines.append(f"### {tech['technique_name']}\n\n")
                lines.append(f"{tech['description']}\n\n")
                lines.append(f"- **出现次数**: {tech['occurrence_count']}\n")
                lines.append(f"- **关键词**: {', '.join(tech['keywords'][:5])}\n")
                lines.append(f"- **关联场景**: {', '.join(tech['source_scenes'])}\n")

                if tech.get("examples"):
                    lines.append(
                        f"\n**示例**:\n```\n{tech['examples'][0][:200]}...\n```\n"
                    )

                lines.append("\n---\n\n")

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("".join(lines))

            saved_count += len(tech_list)

        # 保存JSON汇总
        summary_file = output_dir / "extracted_techniques.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(techniques, f, ensure_ascii=False, indent=2)

        return saved_count


def extract_techniques_from_novels(limit: int = None):
    """从小说提取技法"""
    extractor = TechniqueExtractor()
    return extractor.run(limit=limit)


def extract_techniques_from_cases(limit: int = None):
    """从案例库反推技法"""
    extractor = TechniqueExtractor()
    cases_data = extractor.extract_from_case_library(limit=limit)
    processed = extractor.process_extracted(cases_data)
    return processed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="创作技法精炼提取")
    parser.add_argument("--from-novels", action="store_true", help="从原始小说提取")
    parser.add_argument("--from-cases", action="store_true", help="从案例库反推")
    parser.add_argument("--limit", type=int, help="限制处理数量")
    parser.add_argument("--save", action="store_true", help="保存到技法库")

    args = parser.parse_args()

    extractor = TechniqueExtractor()

    if args.from_cases:
        print("从案例库提取技法...")
        data = extractor.extract_from_case_library(limit=args.limit)
        techniques = extractor.process_extracted(data)
        print(f"提取技法: {len(techniques)} 种")

        if args.save:
            count = extractor.save_to_technique_library(techniques)
            print(f"保存技法: {count} 条")

    elif args.from_novels:
        print("从小说提取技法...")
        techniques = extractor.run(limit=args.limit)
        print(f"提取技法: {len(techniques)} 种")

        if args.save:
            count = extractor.save_to_technique_library(techniques)
            print(f"保存技法: {count} 条")

    else:
        print("请指定 --from-novels 或 --from-cases")
