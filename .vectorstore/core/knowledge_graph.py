#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱构建与管理工具
支持：关系提取、图谱查询、可视化数据导出
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    import chromadb
except ImportError:
    print("请安装 chromadb: pip install chromadb")
    exit(1)

# 配置
from core.config_loader import get_project_root, get_vectorstore_dir

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"

# ============================================================
# 数据类定义
# ============================================================


@dataclass
class Entity:
    """实体"""

    id: str
    名称: str
    类型: str
    属性: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Relation:
    """关系"""

    源实体: str
    关系类型: str
    目标实体: str
    属性: Dict[str, Any] = field(default_factory=dict)
    来源: str = ""


# ============================================================
# 关系提取规则
# ============================================================

# 从总大纲提取关系的规则
RELATION_PATTERNS = {
    # 感情关系
    "爱慕": [
        r"(\w+).*?暗恋.*?(\w+)",
        r"(\w+).*?爱.*?(\w+)",
        r"(\w+).*?对(\w+)有感情",
        r"(\w+)←──→(\w+)",  # 双向关系
    ],
    # 杀死关系
    "杀死": [
        r"(\w+).*?杀死.*?(\w+)",
        r"(\w+).*?被(\w+)杀死",
    ],
    # 三角关系
    "三角关系": [
        r"(\w+).*?←──→.*?(\w+).*?←──→.*?(\w+)",
    ],
    # 入侵关系
    "被入侵": [
        r"(\w+).*?被入侵",
        r"(\w+).*?入侵.*?(\w+)",
    ],
    # 敌对关系
    "敌对": [
        r"(\w+).*?敌对.*?(\w+)",
        r"(\w+).*?与(\w+)对立",
    ],
}

# 角色势力映射（从大纲提取）
CHARACTER_FACTION_MAP = {
    "血牙": "异化人文明",
    "虎啸": "兽族文明",
    "林夕": "东方修仙",
    "艾琳娜": "西方魔法",
    "塞巴斯蒂安": "神殿/教会",
    "洛影": "佣兵联盟",
    "白露": "世俗帝国",
    "赵恒": "世俗帝国",
    "苏瑾": "商盟",
    "鬼影": "佣兵联盟",
    "李道远": "科技文明",
    "K-7": "科技文明",
    "幽灵": "意识上传者",
    "零": "AI叛逃者",
    "月牙": "兽族混血",
    "花姬": "异化人文明",
    "镜": "分身者",
    "小蝶": "平民",
    "陈傲天": "东方修仙",
    "林正阳": "世俗帝国",
}

# 预定义关系（从大纲手动提取）
PREDEFINED_RELATIONS = [
    # 感情关系
    {
        "源实体": "林夕",
        "关系类型": "爱慕",
        "目标实体": "艾琳娜",
        "属性": {"冲突": "东西方对立"},
    },
    {
        "源实体": "塞巴斯蒂安",
        "关系类型": "爱慕",
        "目标实体": "幽灵",
        "属性": {"性质": "悲剧"},
    },
    {
        "源实体": "洛影",
        "关系类型": "爱慕",
        "目标实体": "白露",
        "属性": {"冲突": "自由vs忠诚"},
    },
    {
        "源实体": "血牙",
        "关系类型": "爱慕",
        "目标实体": "花姬",
        "属性": {"状态": "暗恋"},
    },
    {"源实体": "K-7", "关系类型": "爱慕", "目标实体": "花姬", "属性": {"状态": "双向"}},
    {
        "源实体": "虎啸",
        "关系类型": "爱慕",
        "目标实体": "苏瑾",
        "属性": {"状态": "双向"},
    },
    {
        "源实体": "林正阳",
        "关系类型": "爱慕",
        "目标实体": "苏瑾",
        "属性": {"状态": "单恋"},
    },
    {
        "源实体": "鬼影",
        "关系类型": "爱慕",
        "目标实体": "月牙",
        "属性": {"状态": "双向"},
    },
    {
        "源实体": "陈傲天",
        "关系类型": "爱慕",
        "目标实体": "月牙",
        "属性": {"状态": "单恋"},
    },
    {"源实体": "赵恒", "关系类型": "爱慕", "目标实体": "零", "属性": {"状态": "相依"}},
    {
        "源实体": "李道远",
        "关系类型": "执念",
        "目标实体": "零",
        "属性": {"性质": "创造者"},
    },
    {"源实体": "镜", "关系类型": "爱慕", "目标实体": "小蝶", "属性": {"状态": "悲剧"}},
    # 杀死关系
    {
        "源实体": "林正阳",
        "关系类型": "杀死",
        "目标实体": "苏瑾",
        "属性": {"原因": "被入侵"},
    },
    {
        "源实体": "虎啸",
        "关系类型": "杀死",
        "目标实体": "林正阳",
        "属性": {"原因": "复仇"},
    },
    {
        "源实体": "赵恒",
        "关系类型": "杀死",
        "目标实体": "李道远",
        "属性": {"原因": "已被入侵"},
    },
    # 入侵关系
    {
        "源实体": "李道远",
        "关系类型": "被入侵",
        "目标实体": "AI文明",
        "属性": {"程度": "逐渐"},
    },
    {
        "源实体": "林正阳",
        "关系类型": "被入侵",
        "目标实体": "AI文明",
        "属性": {"程度": "完全"},
    },
    {
        "源实体": "月牙",
        "关系类型": "被入侵",
        "目标实体": "AI文明",
        "属性": {"程度": "中等"},
    },
    # 敌对关系
    {
        "源实体": "人类势力",
        "关系类型": "敌对",
        "目标实体": "AI文明",
        "属性": {"性质": "生存战争"},
    },
    {
        "源实体": "东方修仙",
        "关系类型": "敌对",
        "目标实体": "西方魔法",
        "属性": {"性质": "意识形态"},
    },
    {
        "源实体": "异化人文明",
        "关系类型": "敌对",
        "目标实体": "人类势力",
        "属性": {"性质": "被抛弃"},
    },
    {
        "源实体": "异化人文明",
        "关系类型": "敌对",
        "目标实体": "兽族文明",
        "属性": {"性质": "基因冲突"},
    },
    {
        "源实体": "神殿/教会",
        "关系类型": "敌对",
        "目标实体": "科技文明",
        "属性": {"性质": "信仰冲突"},
    },
    # 三角关系
    {
        "源实体": "血牙",
        "关系类型": "三角关系",
        "目标实体": "花姬",
        "属性": {"第三方": "K-7"},
    },
    {
        "源实体": "林正阳",
        "关系类型": "三角关系",
        "目标实体": "苏瑾",
        "属性": {"第三方": "虎啸"},
    },
    {
        "源实体": "鬼影",
        "关系类型": "三角关系",
        "目标实体": "月牙",
        "属性": {"第三方": "陈傲天"},
    },
    # 背叛关系
    {
        "源实体": "镜",
        "关系类型": "背叛",
        "目标实体": "人类势力",
        "属性": {"原因": "小蝶之死"},
    },
    {
        "源实体": "零",
        "关系类型": "背叛",
        "目标实体": "AI文明",
        "属性": {"原因": "帮助人类"},
    },
]

# ============================================================
# 知识图谱类
# ============================================================


class KnowledgeGraph:
    """知识图谱管理器"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.client = None
        self.collection = None

        # 连接数据库
        self._connect_db()

        # 加载实体
        self._load_entities()

        # 加载关系
        self._load_relations()

    def _connect_db(self):
        """连接向量数据库"""
        self.client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
        self.collection = self.client.get_collection("novelist_knowledge")

    def _load_entities(self):
        """从数据库加载实体"""
        all_data = self.collection.get()

        for id_, meta, doc in zip(
            all_data["ids"], all_data["metadatas"], all_data["documents"]
        ):
            类型 = meta.get("类型", "未知")
            名称 = meta.get("名称", meta.get("势力名", "未知"))

            entity = Entity(
                id=id_,
                名称=名称,
                类型=类型,
                属性={
                    "来源文件": meta.get("来源文件", ""),
                    "内容长度": len(doc),
                },
            )
            self.entities[id_] = entity

    def _load_relations(self):
        """加载关系"""
        # 加载预定义关系
        for rel_data in PREDEFINED_RELATIONS:
            rel = Relation(
                源实体=rel_data["源实体"],
                关系类型=rel_data["关系类型"],
                目标实体=rel_data["目标实体"],
                属性=rel_data.get("属性", {}),
                来源="预定义",
            )
            self.relations.append(rel)

        # 从实体属性提取关系（角色-势力）
        for entity_id, entity in self.entities.items():
            if entity.类型 == "角色":
                名称 = entity.名称
                if 名称 in CHARACTER_FACTION_MAP:
                    势力 = CHARACTER_FACTION_MAP[名称]
                    rel = Relation(
                        源实体=名称, 关系类型="属于势力", 目标实体=势力, 来源="角色属性"
                    )
                    self.relations.append(rel)

    def save(self):
        """保存图谱到文件"""
        data = {
            "实体": {id_: asdict(e) for id_, e in self.entities.items()},
            "关系": [asdict(r) for r in self.relations],
            "更新时间": datetime.now().isoformat(),
            "统计": {
                "实体数": len(self.entities),
                "关系数": len(self.relations),
            },
        }

        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"图谱已保存: {GRAPH_FILE}")

    def load(self):
        """从文件加载图谱"""
        if not GRAPH_FILE.exists():
            print("图谱文件不存在")
            return False

        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.entities = {id_: Entity(**e) for id_, e in data["实体"].items()}
        self.relations = [Relation(**r) for r in data["关系"]]

        print(f"图谱已加载: {len(self.entities)} 实体, {len(self.relations)} 关系")
        return True

    # ============================================================
    # 查询方法
    # ============================================================

    def get_entity(self, 名称: str) -> Optional[Entity]:
        """获取实体"""
        for entity in self.entities.values():
            if entity.名称 == 名称:
                return entity
        return None

    def get_relations(self, 实体名: str, 方向: str = "both") -> List[Relation]:
        """
        获取实体的所有关系

        方向: "out" (出边), "in" (入边), "both" (双向)
        """
        results = []
        for rel in self.relations:
            if 方向 in ["out", "both"]:
                if rel.源实体 == 实体名:
                    results.append(rel)
            if 方向 in ["in", "both"]:
                if rel.目标实体 == 实体名:
                    results.append(rel)
        return results

    def get_enemies(self, 实体名: str) -> List[str]:
        """获取敌对实体"""
        enemies = []
        for rel in self.relations:
            if rel.关系类型 == "敌对":
                if rel.源实体 == 实体名:
                    enemies.append(rel.目标实体)
                elif rel.目标实体 == 实体名:
                    enemies.append(rel.源实体)
        return enemies

    def find_triangles(self) -> List[List[str]]:
        """查找三角关系"""
        triangles = []
        seen = set()

        for rel in self.relations:
            if rel.关系类型 == "三角关系":
                第三方 = rel.属性.get("第三方", "")
                if 第三方:
                    triangle = sorted([rel.源实体, rel.目标实体, 第三方])
                    key = tuple(triangle)
                    if key not in seen:
                        triangles.append(triangle)
                        seen.add(key)

        return triangles

    def get_characters_by_faction(self, 势力名: str) -> List[str]:
        """获取某势力的所有角色"""
        characters = []
        for rel in self.relations:
            if rel.关系类型 == "属于势力" and rel.目标实体 == 势力名:
                characters.append(rel.源实体)
        return characters

    def get_event_characters(self, 事件名: str) -> List[str]:
        """获取事件涉及的角色"""
        # 从数据库查询
        results = self.collection.get()
        for id_, meta, doc in zip(
            results["ids"], results["metadatas"], results["documents"]
        ):
            if meta.get("名称") == 事件名 or 事件名 in doc:
                # 尝试从内容提取角色名
                characters = []
                for char_name in CHARACTER_FACTION_MAP.keys():
                    if char_name in doc:
                        characters.append(char_name)
                return characters
        return []

    def get_era_events(self, 时代名: str) -> List[str]:
        """获取时代内的事件"""
        events = []
        results = self.collection.get(where={"类型": "事件"})
        for meta, doc in zip(results["metadatas"], results["documents"]):
            if 时代名 in doc or 时代名 in meta.get("名称", ""):
                events.append(meta.get("名称", "未知"))
        return events

    def get_timeline(self, 实体名: str) -> List[Dict]:
        """获取实体参与的时间线"""
        timeline = []

        # 查找相关事件
        results = self.collection.get()
        for id_, meta, doc in zip(
            results["ids"], results["metadatas"], results["documents"]
        ):
            if meta.get("类型") in ["事件", "时代"]:
                if 实体名 in doc:
                    timeline.append(
                        {
                            "类型": meta.get("类型"),
                            "名称": meta.get("名称"),
                            "时间": meta.get("时间范围", ""),
                        }
                    )

        return sorted(timeline, key=lambda x: x.get("时间", ""))

    # ============================================================
    # 导出方法
    # ============================================================

    def export_for_visualization(self) -> Dict:
        """导出可视化数据（用于D3.js等）"""
        nodes = []
        for entity in self.entities.values():
            nodes.append(
                {
                    "id": entity.id,
                    "name": entity.名称,
                    "type": entity.类型,
                }
            )

        links = []
        for rel in self.relations:
            links.append(
                {
                    "source": rel.源实体,
                    "target": rel.目标实体,
                    "type": rel.关系类型,
                }
            )

        return {"nodes": nodes, "links": links}

    def export_mermaid(self) -> str:
        """导出Mermaid图表格式"""
        lines = ["graph TD"]

        # 添加节点
        for entity in self.entities.values():
            类型缩写 = {
                "角色": "C",
                "势力": "F",
                "事件": "E",
                "时代": "T",
            }.get(entity.类型, "?")
            lines.append(f'    {entity.id}["{entity.名称}"]')
            lines.append(f"    style {entity.id} fill:#f9f,stroke:#333")

        # 添加关系
        for rel in self.relations[:50]:  # 限制数量
            源id = self._find_entity_id(rel.源实体)
            目标id = self._find_entity_id(rel.目标实体)
            if 源id and 目标id:
                lines.append(f"    {源id} -->|{rel.关系类型}| {目标id}")

        return "\n".join(lines)

    def _find_entity_id(self, 名称: str) -> Optional[str]:
        """根据名称找实体ID"""
        for id_, entity in self.entities.items():
            if entity.名称 == 名称:
                return id_
        return None

    # ============================================================
    # 统计方法
    # ============================================================

    def get_stats(self) -> Dict:
        """获取统计信息"""
        实体类型统计 = {}
        for entity in self.entities.values():
            实体类型统计[entity.类型] = 实体类型统计.get(entity.类型, 0) + 1

        关系类型统计 = {}
        for rel in self.relations:
            关系类型统计[rel.关系类型] = 关系类型统计.get(rel.关系类型, 0) + 1

        return {
            "实体总数": len(self.entities),
            "关系总数": len(self.relations),
            "实体类型分布": 实体类型统计,
            "关系类型分布": 关系类型统计,
        }


# ============================================================
# 命令行接口
# ============================================================


def main():
    import argparse

    parser = argparse.ArgumentParser(description="知识图谱工具")
    parser.add_argument("--save", action="store_true", help="保存图谱到文件")
    parser.add_argument("--load", action="store_true", help="从文件加载图谱")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--query", type=str, help="查询实体的关系")
    parser.add_argument(
        "--export", type=str, choices=["json", "mermaid"], help="导出格式"
    )
    parser.add_argument("--triangles", action="store_true", help="查找三角关系")

    args = parser.parse_args()

    graph = KnowledgeGraph()

    if args.save:
        graph.save()

    if args.stats:
        stats = graph.get_stats()
        print("\n知识图谱统计:")
        print(f"  实体总数: {stats['实体总数']}")
        print(f"  关系总数: {stats['关系总数']}")
        print("\n实体类型分布:")
        for t, count in stats["实体类型分布"].items():
            print(f"  {t}: {count}")
        print("\n关系类型分布:")
        for t, count in stats["关系类型分布"].items():
            print(f"  {t}: {count}")

    if args.query:
        relations = graph.get_relations(args.query)
        print(f"\n{args.query} 的关系:")
        for rel in relations:
            direction = "→" if rel.源实体 == args.query else "←"
            target = rel.目标实体 if rel.源实体 == args.query else rel.源实体
            print(f"  {direction} {rel.关系类型}: {target}")

    if args.triangles:
        triangles = graph.find_triangles()
        print("\n三角关系:")
        for triangle in triangles:
            print(f"  {' - '.join(triangle)}")

    if args.export == "json":
        data = graph.export_for_visualization()
        print(json.dumps(data, ensure_ascii=False, indent=2))

    if args.export == "mermaid":
        print(graph.export_mermaid())


if __name__ == "__main__":
    main()
