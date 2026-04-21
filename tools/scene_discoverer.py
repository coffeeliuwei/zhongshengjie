#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
场景自动发现器
==============

从大量小说片段中自动发现新场景类型，并同步到所有相关配置文件。

功能：
1. 收集无法归类的片段
2. 关键词聚类发现模式
3. 生成新场景类型配置
4. 自动同步到：
   - case_builder.py (SCENE_TYPES)
   - scene_writer_mapping.json
   - novelist-workflow SKILL.md
   - 向量库scene_templates

用法：
    python scene_discoverer.py --discover          # 发现新场景
    python scene_discoverer.py --apply-all         # 应用所有发现
    python scene_discoverer.py --status            # 查看状态
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档）

# 尝试导入统一配置加载器
try:
    from core.config_loader import (
        get_project_root,
        get_scene_writer_mapping_path,
        get_case_library_dir,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False

# 配置路径（使用 config_loader 动态获取）
if HAS_CONFIG_LOADER:
    _root = get_project_root()
    CASE_BUILDER_PATH = _root / "tools" / "case_builder.py"
    SCENE_MAPPING_PATH = get_scene_writer_mapping_path()
    DISCOVERED_SCENES_PATH = get_case_library_dir() / "discovered_scenes.json"
else:
    CASE_BUILDER_PATH = PROJECT_ROOT / "tools" / "case_builder.py"
    SCENE_MAPPING_PATH = PROJECT_ROOT / ".vectorstore" / "scene_writer_mapping.json"
    DISCOVERED_SCENES_PATH = PROJECT_ROOT / ".case-library" / "discovered_scenes.json"

SKILL_PATH = Path.home() / ".agents" / "skills" / "novelist-workflow" / "SKILL.md"


@dataclass
class DiscoveredScene:
    """发现的场景类型"""

    name: str
    keywords: List[str]
    sample_count: int
    sample_sources: List[str]
    confidence: float  # 0-1
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"  # pending, approved, rejected

    def to_scene_config(self) -> Dict:
        """转换为SCENE_TYPES格式"""
        return {
            "keywords": self.keywords[:10],
            "position": "any",
            "min_len": 300,
            "max_len": 2000,
        }


class SceneDiscoverer:
    """场景自动发现器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.min_samples = self.config.get("min_samples", 50)  # 最少样本数
        self.min_confidence = self.config.get("min_confidence", 0.6)  # 最低置信度
        self.max_keywords = self.config.get("max_keywords", 10)  # 最大关键词数

        # 加载现有场景类型
        self.existing_scenes = self._load_existing_scenes()

        # 无法归类的片段
        self.unclassified_fragments: List[Dict] = []

        # 发现的新场景
        self.discovered_scenes: List[DiscoveredScene] = []

    def _load_existing_scenes(self) -> Set[str]:
        """加载现有场景类型"""
        try:
            from case_builder import SCENE_TYPES

            return set(SCENE_TYPES.keys())
        except ImportError:
            # 从文件解析
            content = CASE_BUILDER_PATH.read_text(encoding="utf-8")
            matches = re.findall(r'"([^"]+)":\s*\{', content)
            return set(matches)

    def collect_unclassified(
        self, paragraphs: List[str], novel_name: str
    ) -> List[Dict]:
        """
        收集无法归类到现有场景类型的片段

        Args:
            paragraphs: 段落列表
            novel_name: 小说名称

        Returns:
            无法归类的片段列表
        """
        from case_builder import SCENE_TYPES

        unclassified = []

        for para in paragraphs:
            if len(para) < 300 or len(para) > 3000:
                continue

            # 尝试匹配所有现有场景类型
            matched = False
            for scene_type, config in SCENE_TYPES.items():
                keywords = config.get("keywords", [])
                match_count = sum(1 for kw in keywords if kw in para)

                if match_count >= 2:
                    matched = True
                    break

            if not matched:
                # 提取高频词作为潜在关键词
                words = self._extract_keywords(para)
                unclassified.append(
                    {
                        "content": para[:500],
                        "keywords": words,
                        "novel": novel_name,
                        "length": len(para),
                    }
                )

        self.unclassified_fragments.extend(unclassified)
        return unclassified

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 停用词
        stopwords = set(
            [
                "的",
                "了",
                "是",
                "在",
                "我",
                "有",
                "和",
                "就",
                "不",
                "人",
                "都",
                "一",
                "一个",
                "上",
                "也",
                "很",
                "到",
                "说",
                "要",
                "去",
                "你",
                "会",
                "着",
                "没有",
                "看",
                "好",
                "自己",
                "这",
                "那",
                "他",
                "她",
                "它",
                "们",
                "这个",
                "那个",
                "什么",
                "怎么",
            ]
        )

        # 简单分词（按标点和空格）
        words = re.findall(r"[\u4e00-\u9fa5]{2,4}", text)

        # 过滤停用词
        words = [w for w in words if w not in stopwords and len(w) >= 2]

        # 统计词频
        counter = Counter(words)

        # 返回高频词
        return [w for w, _ in counter.most_common(10)]

    def discover_scenes(self) -> List[DiscoveredScene]:
        """
        从无法归类的片段中发现新场景类型

        Returns:
            发现的新场景列表
        """
        if len(self.unclassified_fragments) < self.min_samples:
            print(
                f"    样本不足 ({len(self.unclassified_fragments)} < {self.min_samples})，无法发现新场景"
            )
            return []

        print(f"\n    分析 {len(self.unclassified_fragments)} 个未归类片段...")

        # 关键词聚类
        keyword_clusters = self._cluster_by_keywords()

        # 生成场景类型
        for cluster_name, cluster_data in keyword_clusters.items():
            if cluster_data["count"] >= self.min_samples:
                scene = DiscoveredScene(
                    name=cluster_name,
                    keywords=cluster_data["keywords"],
                    sample_count=cluster_data["count"],
                    sample_sources=cluster_data["sources"][:5],
                    confidence=min(cluster_data["count"] / 100, 1.0),
                )
                self.discovered_scenes.append(scene)

        # 按置信度排序
        self.discovered_scenes.sort(key=lambda x: x.confidence, reverse=True)

        print(f"    发现 {len(self.discovered_scenes)} 个新场景类型")
        return self.discovered_scenes

    def _cluster_by_keywords(self) -> Dict[str, Dict]:
        """通过关键词聚类发现场景模式"""
        # 统计所有关键词共现
        keyword_pairs: Counter = Counter()
        keyword_to_fragments: Dict[str, List[Dict]] = defaultdict(list)

        for frag in self.unclassified_fragments:
            keywords = frag.get("keywords", [])

            # 记录每个关键词对应的片段
            for kw in keywords[:5]:
                keyword_to_fragments[kw].append(frag)

            # 记录关键词共现
            for i, kw1 in enumerate(keywords[:5]):
                for kw2 in keywords[i + 1 : 5]:
                    pair = tuple(sorted([kw1, kw2]))
                    keyword_pairs[pair] += 1

        # 找出高频共现关键词组
        clusters: Dict[str, Dict] = {}

        for (kw1, kw2), count in keyword_pairs.most_common(50):
            if count < 10:
                continue

            # 查找是否有相似聚类
            cluster_name = self._generate_scene_name(kw1, kw2)

            if cluster_name not in clusters:
                clusters[cluster_name] = {
                    "keywords": [kw1, kw2],
                    "count": count,
                    "sources": [],
                }
            else:
                if kw1 not in clusters[cluster_name]["keywords"]:
                    clusters[cluster_name]["keywords"].append(kw1)
                if kw2 not in clusters[cluster_name]["keywords"]:
                    clusters[cluster_name]["keywords"].append(kw2)
                clusters[cluster_name]["count"] += count

            # 收集来源
            for frag in keyword_to_fragments.get(kw1, [])[:3]:
                if frag["novel"] not in clusters[cluster_name]["sources"]:
                    clusters[cluster_name]["sources"].append(frag["novel"])

        return clusters

    def _generate_scene_name(self, kw1: str, kw2: str) -> str:
        """根据关键词生成场景名称"""
        # 场景名称映射规则
        name_patterns = {
            # 战斗相关
            ("攻击", "防御"): "战斗场景",
            ("招式", "灵力"): "战斗场景",
            ("击杀", "鲜血"): "杀戮场景",
            # 情感相关
            ("眼泪", "悲伤"): "悲伤场景",
            ("微笑", "温暖"): "温馨场景",
            ("愤怒", "吼道"): "愤怒场景",
            # 社交相关
            ("宴会", "宾客"): "宴会场景",
            ("交易", "价格"): "交易场景",
            # 修炼相关
            ("突破", "境界"): "修炼突破",
            ("丹药", "炼制"): "炼丹场景",
            # 探索相关
            ("发现", "秘密"): "发现场景",
            ("遗迹", "探索"): "探索场景",
        }

        pair = tuple(sorted([kw1, kw2]))
        if pair in name_patterns:
            return name_patterns[pair]

        # 自动生成名称
        if any(w in kw1 + kw2 for w in ["战斗", "攻击", "杀", "血"]):
            return f"{kw1}场景"
        elif any(w in kw1 + kw2 for w in ["修炼", "突破", "境界"]):
            return "修炼场景"
        elif any(w in kw1 + kw2 for w in ["交易", "购买", "价格"]):
            return "交易场景"
        else:
            return f"{kw1}{kw2}场景"

    def save_discovered(self) -> Path:
        """保存发现的场景到文件"""
        DISCOVERED_SCENES_PATH.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "updated_at": datetime.now().isoformat(),
            "total_fragments": len(self.unclassified_fragments),
            "discovered_scenes": [asdict(s) for s in self.discovered_scenes],
        }

        with open(DISCOVERED_SCENES_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"    已保存到: {DISCOVERED_SCENES_PATH}")
        return DISCOVERED_SCENES_PATH

    def load_discovered(self) -> List[DiscoveredScene]:
        """加载已发现的场景"""
        if not DISCOVERED_SCENES_PATH.exists():
            return []

        with open(DISCOVERED_SCENES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.discovered_scenes = [
            DiscoveredScene(**s) for s in data.get("discovered_scenes", [])
        ]
        return self.discovered_scenes

    # ==================== 同步到各配置文件 ====================

    def sync_to_case_builder(
        self, scenes: Optional[List[DiscoveredScene]] = None
    ) -> int:
        """
        同步新场景到case_builder.py的SCENE_TYPES

        Returns:
            成功同步的场景数量
        """
        scenes = scenes or [s for s in self.discovered_scenes if s.status == "approved"]
        if not scenes:
            print("    没有已批准的新场景需要同步")
            return 0

        content = CASE_BUILDER_PATH.read_text(encoding="utf-8")

        # 找到SCENE_TYPES字典的结束位置
        # 查找最后一个场景类型的定义
        last_scene_pattern = r'("环境场景":\s*\{[^}]+\})'

        synced = 0
        for scene in scenes:
            if scene.name in self.existing_scenes:
                print(f"    [SKIP] {scene.name} 已存在")
                continue

            # 生成场景配置字符串
            config_str = f''',
    "{scene.name}": {{
        "keywords": {json.dumps(scene.keywords[:10], ensure_ascii=False)},
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    }}'''

            # 在最后一个场景后插入
            content = re.sub(last_scene_pattern, r"\1" + config_str, content, count=1)

            self.existing_scenes.add(scene.name)
            synced += 1
            print(f"    [OK] 已添加 {scene.name} 到 case_builder.py")

        # 写回文件
        CASE_BUILDER_PATH.write_text(content, encoding="utf-8")
        return synced

    def sync_to_scene_mapping(
        self, scenes: Optional[List[DiscoveredScene]] = None
    ) -> int:
        """
        同步新场景到scene_writer_mapping.json

        Returns:
            成功同步的场景数量
        """
        scenes = scenes or [s for s in self.discovered_scenes if s.status == "approved"]
        if not scenes:
            return 0

        with open(SCENE_MAPPING_PATH, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        scene_map = mapping.get("scene_writer_mapping", {})
        synced = 0

        for scene in scenes:
            if scene.name in scene_map:
                print(f"    [SKIP] {scene.name} 已存在于mapping")
                continue

            # 生成默认的作家协作配置
            # 新发现的场景默认使用"动态"模式，由苍澜+玄一+墨言前置
            scene_map[scene.name] = {
                "description": f"自动发现的场景类型：{scene.name}",
                "status": "pending_activation",
                "collaboration": [
                    {
                        "writer": "苍澜",
                        "role": "世界观支撑",
                        "phase": "前置",
                        "contribution": ["场景世界观背景"],
                        "weight": 0.20,
                        "technique_dimension": "世界观维度",
                    },
                    {
                        "writer": "玄一",
                        "role": "剧情关联",
                        "phase": "前置",
                        "contribution": ["场景剧情关联"],
                        "weight": 0.20,
                        "technique_dimension": "剧情维度",
                    },
                    {
                        "writer": "墨言",
                        "role": "人物状态",
                        "phase": "前置",
                        "contribution": ["场景人物反应"],
                        "weight": 0.20,
                        "technique_dimension": "人物维度",
                    },
                    {
                        "writer": "云溪",
                        "role": "氛围营造",
                        "phase": "收尾",
                        "contribution": ["场景氛围渲染"],
                        "weight": 0.25,
                        "technique_dimension": "氛围意境维度",
                    },
                ],
                "workflow_order": ["苍澜", "玄一", "墨言", "云溪"],
                "primary_writer": "云溪",  # 默认主作家
                "case_library_filter": {
                    "scene_type": scene.name,
                    "reference_focus": scene.keywords[:3],
                },
                "auto_discovered": True,
                "discovered_at": scene.created_at,
            }

            synced += 1
            print(f"    [OK] 已添加 {scene.name} 到 scene_writer_mapping.json")

        # 更新统计
        mapping["scene_count"]["pending_activation"] = sum(
            1 for s in scene_map.values() if s.get("status") == "pending_activation"
        )
        mapping["scene_count"]["total"] = len(scene_map)
        mapping["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        with open(SCENE_MAPPING_PATH, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        return synced

    def sync_to_skill(self, scenes: Optional[List[DiscoveredScene]] = None) -> int:
        """
        同步新场景到novelist-workflow SKILL.md

        Returns:
            成功同步的场景数量
        """
        scenes = scenes or [s for s in self.discovered_scenes if s.status == "approved"]
        if not scenes:
            return 0

        if not SKILL_PATH.exists():
            print(f"    [WARN] SKILL.md 不存在: {SKILL_PATH}")
            return 0

        content = SKILL_PATH.read_text(encoding="utf-8")
        synced = 0

        # 查找场景类型表格位置（在作家调度矩阵部分）
        # 寻找 "| 开篇场景 |" 这样的标记

        for scene in scenes:
            # 检查是否已存在
            if f"| {scene.name} |" in content:
                print(f"    [SKIP] {scene.name} 已存在于SKILL.md")
                continue

            # 生成表格行
            table_row = f"| {scene.name} | 云溪 | 苍澜+玄一+墨言 | 自动发现场景 |\n"

            # 在表格末尾插入（找到最后一个表格行）
            # 查找 "场景类型与作家分配" 部分
            pattern = r"(\| [^\|]+ \| [^\|]+ \| [^\|]+ \| [^\|]+ \|\n)(?=##)"

            match = re.search(pattern, content)
            if match:
                content = content[: match.end()] + table_row + content[match.end() :]
                synced += 1
                print(f"    [OK] 已添加 {scene.name} 到 SKILL.md")

        if synced > 0:
            SKILL_PATH.write_text(content, encoding="utf-8")

        return synced

    def sync_all(
        self, scenes: Optional[List[DiscoveredScene]] = None, sync_qdrant: bool = False
    ) -> Dict[str, int]:
        """
        同步到所有配置文件

        Args:
            scenes: 要同步的场景列表
            sync_qdrant: 是否同步到向量库（新增）

        Returns:
            各文件的同步数量
        """
        print("\n" + "=" * 60)
        print("同步新场景到所有配置文件")
        print("=" * 60)

        results = {
            "case_builder": self.sync_to_case_builder(scenes),
            "scene_mapping": self.sync_to_scene_mapping(scenes),
            "skill": self.sync_to_skill(scenes),
        }

        # 新增：同步到向量库（可选）
        if sync_qdrant and results["case_builder"] > 0:
            synced_cases = self._sync_to_qdrant()
            results["qdrant"] = synced_cases
            if synced_cases > 0:
                print(f"  [OK] 已同步 {synced_cases} 个场景案例到向量库")

        print(f"\n同步完成: {results}")
        return results

    def _sync_to_qdrant(self) -> int:
        """
        同步场景案例到向量库

        Returns:
            成功同步的数量
        """
        try:
            # 导入同步管理器
            sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))
            from modules.knowledge_base.sync_manager import SyncManager

            sync_manager = SyncManager()
            # 触发案例库增量同步
            result = sync_manager.sync_cases()
            return result.get("synced_count", 0)
        except ImportError:
            # 回退：使用data_migrator
            try:
                import subprocess

                result = subprocess.run(
                    [
                        "python",
                        str(PROJECT_ROOT / "tools" / "data_migrator.py"),
                        "--collection",
                        "case",
                    ],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print("  [OK] 已通过data_migrator同步案例库")
                    return 1
            except Exception as e:
                print(f"  [WARN] 向量库同步失败: {e}")
                return 0
        except Exception as e:
            print(f"  [WARN] 向量库同步失败: {e}")
            return 0

    def approve_scene(self, scene_name: str) -> bool:
        """批准一个发现的场景"""
        for scene in self.discovered_scenes:
            if scene.name == scene_name:
                scene.status = "approved"
                self.save_discovered()
                print(f"    已批准: {scene_name}")
                return True
        return False

    def reject_scene(self, scene_name: str) -> bool:
        """拒绝一个发现的场景"""
        for scene in self.discovered_scenes:
            if scene.name == scene_name:
                scene.status = "rejected"
                self.save_discovered()
                print(f"    已拒绝: {scene_name}")
                return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """获取发现器状态"""
        return {
            "existing_scenes": len(self.existing_scenes),
            "unclassified_fragments": len(self.unclassified_fragments),
            "discovered_scenes": len(self.discovered_scenes),
            "pending": sum(1 for s in self.discovered_scenes if s.status == "pending"),
            "approved": sum(
                1 for s in self.discovered_scenes if s.status == "approved"
            ),
            "rejected": sum(
                1 for s in self.discovered_scenes if s.status == "rejected"
            ),
        }


def main():
    parser = argparse.ArgumentParser(description="场景自动发现器")
    parser.add_argument("--discover", action="store_true", help="从小说库发现新场景")
    parser.add_argument("--apply-all", action="store_true", help="应用所有已批准的场景")
    parser.add_argument("--approve", metavar="NAME", help="批准指定场景")
    parser.add_argument("--reject", metavar="NAME", help="拒绝指定场景")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--list", action="store_true", help="列出发现的场景")
    parser.add_argument("--scan", metavar="DIR", help="扫描小说目录收集未归类片段")
    parser.add_argument(
        "--sync-qdrant",
        action="store_true",
        help="同步到向量库（与--apply-all配合使用）",
    )

    args = parser.parse_args()

    discoverer = SceneDiscoverer()

    if args.status:
        status = discoverer.get_status()
        print("\n" + "=" * 60)
        print("场景发现器状态")
        print("=" * 60)
        print(f"  现有场景类型: {status['existing_scenes']}")
        print(f"  未归类片段: {status['unclassified_fragments']}")
        print(f"  发现的新场景: {status['discovered_scenes']}")
        print(f"    - 待审批: {status['pending']}")
        print(f"    - 已批准: {status['approved']}")
        print(f"    - 已拒绝: {status['rejected']}")
        return

    if args.list:
        discoverer.load_discovered()
        print("\n" + "=" * 60)
        print("发现的场景列表")
        print("=" * 60)
        for scene in discoverer.discovered_scenes:
            status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}[
                scene.status
            ]
            print(f"\n{status_icon} {scene.name}")
            print(f"  关键词: {', '.join(scene.keywords[:5])}")
            print(f"  样本数: {scene.sample_count}")
            print(f"  置信度: {scene.confidence:.0%}")
        return

    if args.approve:
        discoverer.load_discovered()
        discoverer.approve_scene(args.approve)
        return

    if args.reject:
        discoverer.load_discovered()
        discoverer.reject_scene(args.reject)
        return

    if args.apply_all:
        discoverer.load_discovered()
        approved = [s for s in discoverer.discovered_scenes if s.status == "approved"]
        if not approved:
            print("没有已批准的场景需要应用")
            print("请先使用 --approve NAME 批准场景")
            return
        discoverer.sync_all(approved, sync_qdrant=args.sync_qdrant)
        return

    if args.discover:
        print("\n" + "=" * 60)
        print("发现新场景类型")
        print("=" * 60)
        print("\n    请先使用 --scan DIR 扫描小说库收集未归类片段")
        print("    然后运行此命令发现新场景")
        return

    if args.scan:
        scan_dir = Path(args.scan)
        if not scan_dir.exists():
            print(f"目录不存在: {scan_dir}")
            return

        print("\n" + "=" * 60)
        print(f"扫描小说目录: {scan_dir}")
        print("=" * 60)

        from case_builder import SCENE_TYPES

        total_unclassified = 0
        for txt_file in scan_dir.rglob("*.txt"):
            try:
                content = txt_file.read_text(encoding="utf-8", errors="ignore")
                paragraphs = re.split(r"\n\s*\n", content)
                paragraphs = [
                    p.strip() for p in paragraphs if 100 <= len(p.strip()) <= 5000
                ]

                unclassified = discoverer.collect_unclassified(
                    paragraphs, txt_file.stem
                )
                total_unclassified += len(unclassified)

                if total_unclassified % 100 == 0:
                    print(f"    已收集 {total_unclassified} 个未归类片段")
            except Exception as e:
                pass

        print(f"\n总计收集 {total_unclassified} 个未归类片段")

        # 发现新场景
        discovered = discoverer.discover_scenes()

        if discovered:
            discoverer.save_discovered()
            print("\n发现的场景:")
            for scene in discovered:
                print(
                    f"  - {scene.name} (样本: {scene.sample_count}, 置信度: {scene.confidence:.0%})"
                )
            print("\n使用 --list 查看详情")
            print("使用 --approve NAME 批准场景")
            print("使用 --apply-all 应用所有已批准的场景")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
