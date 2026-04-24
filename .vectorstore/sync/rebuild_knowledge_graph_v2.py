#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界知识图谱构建器 v2.0
从解析数据自动生成知识图谱
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

# 导入解析器
from md_parser import (
    FullParser,
    FactionParser,
    CharacterParser,
    PowerSystemParser,
    EraParser,
    EventParser,
    TechniqueParser,
    TechBaseParser,
)

# 配置
PROJECT_DIR = Path(__file__).parent.parent
VECTORSTORE_DIR = Path(__file__).parent
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"


# 势力-力量体系映射
FACTION_POWER_MAP = {
    "东方修仙": "修仙",
    "西方魔法": "魔法",
    "神殿/教会": "神术",
    "神殿": "神术",
    "教会": "神术",
    "佣兵联盟": "武力",
    "商盟": "商业",
    "世俗帝国": "军阵",
    "科技文明": "科技",
    "兽族文明": "兽力",
    "兽族": "兽力",
    "AI文明": "AI力",
    "异化人文明": "异能",
    "异化人": "异能",
    "意识上传者": "数字",
    "分身者": "分身",
    "平民": "无",
}


class KnowledgeGraphBuilder:
    """知识图谱构建器"""

    def __init__(self):
        self.parser = FullParser()
        self.entities: Dict[str, Dict] = {}
        self.relations: List[Dict] = []
        self.entity_names: Dict[str, str] = {}  # 名称 -> ID 映射
        self.relation_set: Set[tuple] = set()  # 关系去重

    def build_all(self):
        """构建完整知识图谱"""
        print("开始构建知识图谱 v2.0...")
        print("=" * 50)

        # 解析源数据
        data = self.parser.parse_all()

        # 构建实体（仅小说设定，不含创作技法）
        print("\n[仅包含小说设定，创作技法存储在独立的技法向量库]")
        self._build_factions(data["势力"])
        self._build_characters(data["角色"])
        self._build_power_systems(data["力量体系"])
        self._build_eras(data["时代"])
        self._build_events(data["事件"])
        # ★ 构建技术基础实体
        self._build_tech_bases(data.get("技术基础", []))
        # ★ 不再将创作技法加入知识图谱
        # self._build_techniques(data.get("创作技法", []))

        # 构建关系
        self._build_relations(data)

        # 统计
        self._print_stats()

        # 保存
        self._save()

    def _build_factions(self, factions: List[Dict]):
        """构建势力实体"""
        print("\n构建势力实体...")

        for f in factions:
            entity_id = f.get("id", f"faction_{len(self.entities)}")
            name = f.get("名称", "")

            # ★ 获取势力对应的力量体系
            power_system = FACTION_POWER_MAP.get(name, "")

            # 构建属性
            attrs = {
                "核心力量": f.get("核心力量", ""),
                "核心利益": f.get("核心利益", ""),
                "不可替代性": f.get("不可替代性", ""),
                "力量体系": power_system,  # ★ 添加力量体系
            }

            # 添加详细属性
            if f.get("政治结构"):
                attrs["政治结构"] = f["政治结构"]
            if f.get("派系"):
                attrs["派系"] = f["派系"]
            if f.get("经济结构"):
                attrs["经济结构"] = f["经济结构"]
            if f.get("文化结构"):
                attrs["文化结构"] = f["文化结构"]
            if f.get("建筑风格"):
                attrs["建筑风格"] = f["建筑风格"]
            if f.get("核心建筑"):
                attrs["核心建筑"] = f["核心建筑"]
            if f.get("灵魂保护法门"):
                attrs["灵魂保护法门"] = f["灵魂保护法门"]
            if f.get("保护法门原理"):
                attrs["保护法门原理"] = f["保护法门原理"]
            if f.get("保护法门弱点"):
                attrs["保护法门弱点"] = f["保护法门弱点"]

            entity = {"id": entity_id, "名称": name, "类型": "势力", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id
            print(f"  + {name} (力量: {power_system})")

            # ★ 建立势力→力量体系关系
            if power_system:
                self._add_relation(name, "使用力量", power_system)

        # 构建势力派系为独立实体
        for f in factions:
            faction_id = f.get("id")
            faction_name = f.get("名称", "")
            for branch in f.get("派系", []):
                branch_name = branch.get("名称", "")
                if branch_name:
                    branch_id = f"branch_{faction_id}_{branch_name}"
                    self.entities[branch_id] = {
                        "id": branch_id,
                        "名称": branch_name,
                        "类型": "派系",
                        "属性": {
                            "所属势力": faction_name,
                            "代表": branch.get("代表", ""),
                            "主张": branch.get("主张", ""),
                        },
                    }
                    self.entity_names[branch_name] = branch_id
                    # 派系-势力关系
                    self._add_relation(branch_name, "属于", faction_name)

    def _build_characters(self, characters: List[Dict]):
        """构建角色实体"""
        print("\n构建角色实体...")

        for c in characters:
            entity_id = c.get("id", f"char_{len(self.entities)}")
            name = c.get("名称", "")
            faction = c.get("势力", "")

            # ★ 力量体系：优先使用角色指定的，否则从势力继承
            power_system = c.get("力量体系", "")
            if not power_system and faction:
                power_system = FACTION_POWER_MAP.get(faction, "")

            attrs = {
                "势力": faction,
                "身份": c.get("身份", ""),
                "入侵状态": c.get("入侵状态", ""),
                "力量体系": power_system,  # ★ 继承自势力或角色指定
            }

            # 添加详细属性
            if c.get("年龄"):
                attrs["年龄"] = c["年龄"]
            if c.get("种族"):
                attrs["种族"] = c["种族"]
            if c.get("所属组织"):
                attrs["所属组织"] = c["所属组织"]
            if c.get("种族特征"):
                attrs["种族特征"] = c["种族特征"]
            if c.get("登场时代"):
                attrs["登场时代"] = c["登场时代"]
            if c.get("退场时代"):
                attrs["退场时代"] = c["退场时代"]
            if c.get("涉及事件"):
                attrs["涉及事件"] = c["涉及事件"]
            if c.get("角色弧类型"):
                attrs["角色弧类型"] = c["角色弧类型"]
            if c.get("核心冲突"):
                attrs["核心冲突"] = c["核心冲突"]
            if c.get("主题承载"):
                attrs["主题承载"] = c["主题承载"]

            # ★ 个人能力（力量体系子集）- 后续从大纲中提取
            if c.get("功法"):
                attrs["功法"] = c["功法"]
            if c.get("技能"):
                attrs["技能"] = c["技能"]
            if c.get("特殊能力"):
                attrs["特殊能力"] = c["特殊能力"]

            # ★ 详细力量体系信息
            if c.get("初始派别"):
                attrs["初始派别"] = c["初始派别"]
            if c.get("初始能力"):
                attrs["初始能力"] = c["初始能力"]
            if c.get("后续派别"):
                attrs["后续派别"] = c["后续派别"]
            if c.get("后续能力"):
                attrs["后续能力"] = c["后续能力"]
            if c.get("力量成长轨迹"):
                attrs["力量成长轨迹"] = c["力量成长轨迹"]

            entity = {"id": entity_id, "名称": name, "类型": "角色", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id

            # 打印力量体系详情
            initial_branches = c.get("初始派别", [])
            if initial_branches:
                print(
                    f"  + {name} (力量: {power_system}, 初始派别: {'+'.join(initial_branches)})"
                )
            else:
                print(f"  + {name} (力量: {power_system})")

            # 角色-势力关系
            if faction:
                self._add_relation(name, "属于势力", faction)

            # ★ 角色-力量体系关系
            if power_system:
                self._add_relation(name, "使用力量", power_system)

            # ★ 角色-派别关系（初始派别）
            for branch in initial_branches:
                if branch and branch != "-":
                    self._add_relation(name, "初始修炼派别", branch)

            # ★ 角色-派别关系（后续派别）
            for branch in c.get("后续派别", []):
                if branch and branch != "-":
                    self._add_relation(name, "后续修炼派别", branch)

            # 入侵状态关系
            invasion = c.get("入侵状态", "")
            if invasion and "入侵" in invasion:
                self._add_relation(name, "被入侵", "AI文明", {"程度": invasion})

    def _build_power_systems(self, systems: List[Dict]):
        """构建力量体系实体"""
        print("\n构建力量体系实体...")

        for s in systems:
            entity_id = s.get("id", f"power_{len(self.entities)}")
            name = s.get("名称", "")

            attrs = {
                "力量来源": s.get("力量来源", ""),
                "修炼方式": s.get("修炼方式", ""),
                "战斗特点": s.get("战斗特点", ""),
                "核心代价": s.get("核心代价", ""),
            }

            if s.get("境界划分"):
                attrs["境界划分"] = s["境界划分"]
            if s.get("代价详情"):
                attrs["代价详情"] = s["代价详情"]
            if s.get("特殊技法"):
                attrs["特殊技法"] = s["特殊技法"]
            if s.get("主要势力"):
                attrs["主要势力"] = s["主要势力"]
            if s.get("派别"):
                attrs["派别数量"] = len(s["派别"])

            entity = {"id": entity_id, "名称": name, "类型": "力量体系", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id
            print(f"  + {name} (派别: {len(s.get('派别', []))}个)")

            # 力量体系-势力关系
            for faction in s.get("主要势力", []):
                self._add_relation(name, "主要势力", faction)

            # ★ 构建派别实体
            for branch in s.get("派别", []):
                branch_name = branch.get("名称", "")
                if branch_name:
                    branch_id = f"branch_power_{name}_{branch_name}"
                    self.entities[branch_id] = {
                        "id": branch_id,
                        "名称": branch_name,
                        "类型": "力量派别",
                        "属性": {
                            "所属力量体系": name,
                            **{k: v for k, v in branch.items() if k != "名称"},
                        },
                    }
                    self.entity_names[branch_name] = branch_id
                    # 派别-力量体系关系
                    self._add_relation(branch_name, "属于力量体系", name)

                    # ★ 代表人物-派别关系
                    rep_chars = branch.get("代表人物", "")
                    if rep_chars:
                        # 可能有多个人物，用逗号分隔
                        for char in rep_chars.replace("**", "").split(","):
                            char = char.strip()
                            if char:
                                self._add_relation(char, "修炼派别", branch_name)

            # ★ 角色力量分配关系
            for char_info in s.get("代表人物", []):
                char_name = char_info.get("角色", "")
                char_branch = char_info.get("派别", "")
                if char_name and char_branch:
                    self._add_relation(char_name, "修炼派别", char_branch)
                if char_name and name:
                    self._add_relation(char_name, "使用力量", name)

    def _build_eras(self, eras: List[Dict]):
        """构建时代实体"""
        print("\n构建时代实体...")

        for e in eras:
            entity_id = e.get("id", f"era_{len(self.entities)}")
            name = e.get("名称", "")

            attrs = {
                "时间跨度": e.get("时间跨度", ""),
                "时代特点": e.get("时代特点", ""),
            }

            if e.get("核心事件"):
                attrs["核心事件"] = e["核心事件"]
            if e.get("核心氛围"):
                attrs["核心氛围"] = e["核心氛围"]
            if e.get("色调"):
                attrs["色调"] = e["色调"]
            if e.get("季节感"):
                attrs["季节感"] = e["季节感"]
            if e.get("代表意象"):
                attrs["代表意象"] = e["代表意象"]
            if e.get("登场主角"):
                attrs["登场主角"] = e["登场主角"]
            if e.get("退场主角"):
                attrs["退场主角"] = e["退场主角"]

            entity = {"id": entity_id, "名称": name, "类型": "时代", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id
            print(f"  + {name}")

            # 登场角色关系
            for char in e.get("登场主角", []):
                self._add_relation(char, "登场于", name)
            for char in e.get("退场主角", []):
                self._add_relation(char, "退场于", name)

    def _build_events(self, events: List[Dict]):
        """构建事件实体"""
        print("\n构建事件实体...")

        for ev in events:
            entity_id = ev.get("id", f"event_{len(self.entities)}")
            name = ev.get("名称", "")

            attrs = {
                "类型": ev.get("类型", ""),
                "时代": ev.get("时代", ""),
                "概述": ev.get("概述", ""),
            }

            if ev.get("涉及角色"):
                attrs["涉及角色"] = ev["涉及角色"]
            if ev.get("涉及势力"):
                attrs["涉及势力"] = ev["涉及势力"]

            entity = {"id": entity_id, "名称": name, "类型": "事件", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id
            print(f"  + {name}")

            # 事件-时代关系
            era = ev.get("时代", "")
            if era:
                self._add_relation(name, "发生在", era)

            # 事件-角色关系
            for char in ev.get("涉及角色", []):
                self._add_relation(name, "涉及", char)

    def _build_tech_bases(self, tech_bases: List[Dict]):
        """构建技术基础实体"""
        print("\n构建技术基础实体...")

        for tb in tech_bases:
            entity_id = tb.get("id", f"techbase_{len(self.entities)}")
            name = tb.get("名称", "")
            civilization = tb.get("文明", "")
            domain = tb.get("技术领域", "")
            source = tb.get("来源", "")

            # 构建属性
            attrs = {
                "文明": civilization,
                "技术领域": domain,
                "来源": source,
            }

            # 添加关键技术
            if tb.get("关键技术"):
                attrs["关键技术"] = tb["关键技术"]

            # 添加情节应用
            if tb.get("情节应用"):
                attrs["情节应用"] = tb["情节应用"]

            entity = {"id": entity_id, "名称": name, "类型": "技术基础", "属性": attrs}

            self.entities[entity_id] = entity
            self.entity_names[name] = entity_id
            print(f"  + {name} (文明: {civilization}, 来源: {source})")

            # ★ 提取关系：技术基础 -> 来源
            if source:
                self._add_relation(name, "来源于", source)

            # ★ 提取关系：技术基础 -> 涉及领域
            if domain:
                self._add_relation(name, "涉及领域", domain)

            # ★ 提取关系：技术基础 -> 涉及势力（文明）
            if civilization:
                # 映射文明名称到势力名称
                civ_to_faction = {
                    "科技文明": "科技文明",
                    "AI文明": "AI文明",
                    "异化人文明": "异化人文明",
                }
                faction_name = civ_to_faction.get(civilization, civilization)
                self._add_relation(name, "涉及势力", faction_name)

    def _build_techniques(self, techniques: List[Dict]):
        """构建创作技法实体"""
        print("\n构建创作技法实体...")

        # 创建技法维度实体
        dimension_entities = {}
        for t in techniques:
            dimension = t.get("维度", "未知")
            if dimension not in dimension_entities:
                dim_id = f"technique_dimension_{dimension}"
                writer = t.get("适用作家", "未知")
                dimension_entities[dimension] = {
                    "id": dim_id,
                    "名称": f"{dimension}技法",
                    "类型": "技法维度",
                    "属性": {
                        "适用作家": writer,
                        "技法数量": 0,
                    },
                }
                self.entities[dim_id] = dimension_entities[dimension]
                self.entity_names[f"{dimension}技法"] = dim_id
                print(f"  + {dimension}技法 (作家: {writer})")
            dimension_entities[dimension]["属性"]["技法数量"] += 1

        # 创建技法实体
        for t in techniques:
            entity_id = t.get("id", f"technique_{len(self.entities)}")
            name = t.get("名称", "")
            dimension = t.get("维度", "未知")

            attrs = {
                "维度": dimension,
                "适用作家": t.get("适用作家", ""),
                "来源文件": t.get("来源文件", ""),
                "关键词": t.get("关键词", []),
                "适用场景": t.get("适用场景", []),
                "适用阶段": t.get("适用阶段", []),
                "重要性": t.get("重要性", "P1"),
                "字数": t.get("字数", 0),
            }

            entity = {"id": entity_id, "名称": name, "类型": "创作技法", "属性": attrs}

            self.entities[entity_id] = entity
            # 技法名称可能重复，只在名称唯一时添加到entity_names
            if name not in self.entity_names:
                self.entity_names[name] = entity_id

            # 技法-维度关系
            if dimension:
                self._add_relation(name, "属于维度", f"{dimension}技法")

            # 技法-作家关系
            writer = t.get("适用作家", "")
            if writer and writer != "未知" and writer != "全部":
                self._add_relation(name, "适用作家", writer)

        print(f"  共构建 {len(techniques)} 个技法实体")

    def _build_relations(self, data: Dict):
        """构建关系"""
        print("\n构建关系...")

        # 角色感情关系
        for c in data["角色"]:
            name = c.get("名称", "")
            for rel in c.get("感情关系", []):
                partner = rel.get("对象", "")
                if partner:
                    self._add_relation(
                        name,
                        "爱慕",
                        partner,
                        {
                            "矛盾": rel.get("矛盾", ""),
                            "结局": rel.get("结局", ""),
                        },
                    )

        # 势力敌对关系（从总大纲提取）
        enemy_relations = [
            ("东方修仙", "敌对", "西方魔法", {"性质": "意识形态冲突"}),
            ("东方修仙", "敌对", "AI文明", {"性质": "AI是异端"}),
            ("西方魔法", "敌对", "AI文明", {"性质": "AI是威胁"}),
            ("神殿/教会", "敌对", "科技文明", {"性质": "信仰vs技术"}),
            ("神殿/教会", "敌对", "AI文明", {"性质": "AI是魔鬼造物"}),
            ("异化人文明", "敌对", "人类势力", {"性质": "被抛弃"}),
            ("异化人文明", "敌对", "兽族文明", {"性质": "基因冲突"}),
        ]
        for src, rel_type, tgt, attrs in enemy_relations:
            self._add_relation(src, rel_type, tgt, attrs)

        # 商盟交易关系
        trade_relations = [
            ("商盟", "交易", "东方修仙", {"性质": "灵石贸易"}),
            ("商盟", "交易", "西方魔法", {"性质": "魔法材料"}),
            ("商盟", "交易", "科技文明", {"性质": "技术贸易"}),
            ("商盟", "交易", "异化人文明", {"性质": "能量矿"}),
            ("商盟", "交易", "兽族文明", {"性质": "图腾资源"}),
        ]
        for src, rel_type, tgt, attrs in trade_relations:
            self._add_relation(src, rel_type, tgt, attrs)

    def _add_relation(
        self, source: str, relation_type: str, target: str, attributes: dict = None
    ):
        """添加关系"""
        key = (source, relation_type, target)
        if key in self.relation_set:
            return
        self.relation_set.add(key)

        self.relations.append(
            {
                "源实体": source,
                "关系类型": relation_type,
                "目标实体": target,
                "属性": attributes or {},
            }
        )

    def _print_stats(self):
        """打印统计"""
        print("\n" + "=" * 50)
        print("知识图谱构建完成！")

        # 实体统计
        type_counts = {}
        for e in self.entities.values():
            t = e.get("类型", "未知")
            type_counts[t] = type_counts.get(t, 0) + 1

        print("\n实体类型分布:")
        for t, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")

        # 关系统计
        rel_counts = {}
        for r in self.relations:
            t = r.get("关系类型", "未知")
            rel_counts[t] = rel_counts.get(t, 0) + 1

        print("\n关系类型分布:")
        for t, count in sorted(rel_counts.items(), key=lambda x: -x[1])[:10]:
            print(f"  {t}: {count}")

        print(f"\n总实体数: {len(self.entities)}")
        print(f"总关系数: {len(self.relations)}")

    def _save(self):
        """保存知识图谱"""
        graph = {
            "实体": self.entities,
            "关系": self.relations,
            "元数据": {
                "版本": "2.0",
                "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "数据来源": [
                    "总大纲.md",
                    "十大势力.md",
                    "人物谱.md",
                    "时间线.md",
                    "力量体系.md",
                ],
                "实体统计": {e.get("类型", "未知"): 0 for e in self.entities.values()},
                "关系统计": {},
            },
        }

        # 更新统计
        for e in self.entities.values():
            t = e.get("类型", "未知")
            graph["元数据"]["实体统计"][t] = graph["元数据"]["实体统计"].get(t, 0) + 1

        for r in self.relations:
            t = r.get("关系类型", "未知")
            graph["元数据"]["关系统计"][t] = graph["元数据"]["关系统计"].get(t, 0) + 1

        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)

        print(f"\n知识图谱已保存到: {GRAPH_FILE}")


def main():
    builder = KnowledgeGraphBuilder()
    builder.build_all()


if __name__ == "__main__":
    main()
