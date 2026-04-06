#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界知识图谱 Markdown 解析器
从源文件自动提取结构化数据
"""

import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import (
    get_project_root,
    get_vectorstore_dir,
    get_settings_dir,
    get_techniques_dir,
)

# 路径配置
PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
SETTINGS_DIR = get_settings_dir()

# 源文件路径
FILES = {
    "总大纲": PROJECT_DIR / "总大纲.md",
    "十大势力": SETTINGS_DIR / "十大势力.md",
    "人物谱": SETTINGS_DIR / "人物谱.md",
    "时间线": SETTINGS_DIR / "时间线.md",
    "力量体系": SETTINGS_DIR / "力量体系.md",
}


class MDParser:
    """Markdown解析器基类"""

    @staticmethod
    def read_file(file_path: Path) -> str:
        """读取文件内容"""
        if not file_path.exists():
            print(f"[警告] 文件不存在: {file_path}")
            return ""
        return file_path.read_text(encoding="utf-8")

    @staticmethod
    def parse_table(content: str, start_marker: str = None) -> List[Dict]:
        """解析Markdown表格为字典列表"""
        lines = content.split("\n")
        result = []
        in_table = False
        headers = []
        start_idx = 0

        # 找到表格起始位置
        if start_marker:
            for i, line in enumerate(lines):
                if start_marker in line:
                    start_idx = i
                    break

        for i, line in enumerate(lines[start_idx:], start=start_idx):
            line = line.strip()

            # 检测表格行
            if line.startswith("|") and "|" in line[1:]:
                cells = [c.strip() for c in line.split("|")[1:-1]]

                if not in_table:
                    # 第一行是表头
                    headers = cells
                    in_table = True
                elif cells and not all(
                    c.replace("-", "").replace(":", "") == "" for c in cells
                ):
                    # 数据行（跳过分隔行）
                    if len(cells) == len(headers):
                        row = {}
                        for j, h in enumerate(headers):
                            if h:
                                row[h] = cells[j]
                        if row:
                            result.append(row)
            elif in_table and not line.startswith("|"):
                # 表格结束
                break

        return result

    @staticmethod
    def parse_list(content: str, section_title: str = None) -> List[str]:
        """解析列表项"""
        lines = content.split("\n")
        result = []
        in_section = section_title is None

        for line in lines:
            line_stripped = line.strip()

            if section_title and section_title in line:
                in_section = True
                continue

            if in_section:
                # 检测列表项
                match = re.match(r"^[-*]\s+(.+)$", line_stripped)
                if match:
                    result.append(match.group(1).strip())
                elif line_stripped.startswith("#"):
                    # 新章节，结束
                    if section_title:
                        break

        return result

    @staticmethod
    def find_section(
        content: str, section_title: str, end_markers: List[str] = None
    ) -> str:
        """查找章节内容"""
        lines = content.split("\n")
        result = []
        in_section = False

        for line in lines:
            if section_title in line and (
                line.startswith("#") or line.startswith("**")
            ):
                in_section = True
                continue

            if in_section:
                # 检查结束标记
                if end_markers:
                    for marker in end_markers:
                        if marker in line and (
                            line.startswith("#") or line.startswith("---")
                        ):
                            return "\n".join(result)
                elif line.startswith("#") or line.startswith("---"):
                    return "\n".join(result)

                result.append(line)

        return "\n".join(result)

    @staticmethod
    def extract_bold_key_value(content: str) -> Dict[str, str]:
        """提取 **键**: 值 格式的键值对"""
        result = {}
        pattern = r"\*\*([^*]+)\*\*[：:]\s*(.+)"
        for match in re.finditer(pattern, content):
            key = match.group(1).strip()
            value = match.group(2).strip()
            result[key] = value
        return result


class FactionParser(MDParser):
    """势力解析器"""

    # 势力ID映射
    FACTION_IDS = {
        "东方修仙": "faction_eastern_cultivation",
        "西方魔法": "faction_western_magic",
        "神殿/教会": "faction_temple",
        "神殿": "faction_temple",
        "教会": "faction_temple",
        "佣兵联盟": "faction_mercenary",
        "商盟": "faction_merchant",
        "世俗帝国": "faction_empire",
        "科技文明": "faction_tech",
        "兽族文明": "faction_beast",
        "AI文明": "faction_ai",
        "异化人文明": "faction_mutant",
        "异化人": "faction_mutant",
    }

    def parse_all(self) -> List[Dict]:
        """解析所有势力信息"""
        factions = []

        # 从总大纲解析
        outline_content = self.read_file(FILES["总大纲"])
        factions.extend(self._parse_from_outline(outline_content))

        # 从十大势力解析详细信息
        faction_content = self.read_file(FILES["十大势力"])
        factions = self._merge_faction_details(factions, faction_content)

        return factions

    def _parse_from_outline(self, content: str) -> List[Dict]:
        """从总大纲解析势力基础信息"""
        factions = []

        # 解析势力总览表格
        table = self.parse_table(content, "势力总览")
        for row in table:
            name = row.get("势力", "").replace("**", "")
            if name:
                faction = {
                    "id": self.FACTION_IDS.get(name, f"faction_{name}"),
                    "名称": name,
                    "核心力量": row.get("核心力量", "").replace("**", ""),
                    "核心利益": row.get("核心利益", "").replace("**", ""),
                    "不可替代性": row.get("不可替代性", "").replace("**", ""),
                    "派系": [],
                    "经济结构": {},
                    "文化结构": [],
                }
                factions.append(faction)

        # 解析各势力内部派系
        for faction in factions:
            name = faction["名称"]
            faction["派系"] = self._parse_faction_branches(content, name)

        # 解析灵魂保护法门
        soul_table = self.parse_table(content, "灵魂保护法门")
        for row in soul_table:
            faction_name = row.get("势力", "").replace("**", "")
            for faction in factions:
                if faction_name in faction["名称"] or faction["名称"] in faction_name:
                    faction["灵魂保护法门"] = row.get("法门名称", "")
                    faction["保护法门原理"] = row.get("原理", "")
                    faction["保护法门弱点"] = row.get("弱点", "")

        return factions

    def _parse_faction_branches(self, content: str, faction_name: str) -> List[Dict]:
        """解析势力内部派系"""
        branches = []

        # 查找势力派系章节
        section_markers = [
            f"{faction_name}内部派系",
            f"{faction_name}派系政治",
        ]

        for marker in section_markers:
            section = self.find_section(content, marker, ["###", "##", "---"])
            if section:
                table = self.parse_table(section)
                for row in table:
                    branch = {
                        "名称": row.get("派系", "").replace("**", ""),
                        "代表": row.get("代表宗门", "")
                        or row.get("代表势力", "")
                        or row.get("代表族群", "")
                        or row.get("代表", ""),
                        "主张": row.get("主张", "")
                        or row.get("特点", "")
                        or row.get("主营业务", ""),
                    }
                    if branch["名称"]:
                        branches.append(branch)
                if branches:
                    break

        return branches

    def _merge_faction_details(self, factions: List[Dict], content: str) -> List[Dict]:
        """从十大势力.md合并详细信息"""
        # 解析政治结构
        for faction in factions:
            name = faction["名称"]
            section = self.find_section(content, f"### {name}")
            if section:
                # 解析政治结构
                faction["政治结构"] = self._parse_political_structure(section)
                # 解析经济结构
                faction["经济结构"] = self._parse_economic_structure(section)
                # 解析文化结构
                faction["文化结构"] = self._parse_cultural_structure(section)

        return factions

    def _parse_political_structure(self, section: str) -> Dict:
        """解析政治结构"""
        structure = {}
        lines = section.split("\n")

        in_political = False
        for line in lines:
            if "政治结构" in line:
                in_political = True
                continue
            if in_political:
                if line.startswith("#") or line.startswith("---"):
                    break
                match = re.match(r"[-*]\s*(.+)（(.+)）", line.strip())
                if match:
                    role = match.group(1).strip()
                    desc = match.group(2).strip()
                    if "决策" in role or "最高" in role:
                        structure["最高决策"] = f"{role}（{desc}）"
                    elif "重大" in role or "长老" in role:
                        structure["重大决策"] = f"{role}（{desc}）"
                    elif "管理" in role or "主管" in role:
                        structure["部门管理"] = f"{role}（{desc}）"
                    else:
                        structure["执行层"] = f"{role}（{desc}）"

        return structure

    def _parse_economic_structure(self, section: str) -> Dict:
        """解析经济结构"""
        economy = {}
        lines = section.split("\n")

        in_economy = False
        for line in lines:
            if "经济结构" in line:
                in_economy = True
                continue
            if in_economy:
                if (
                    line.startswith("#")
                    or line.startswith("---")
                    or line.startswith("**")
                ):
                    break
                match = re.match(r"[-*]\s*(.+)（(.+)）", line.strip())
                if match:
                    resource = match.group(1).strip()
                    controller = match.group(2).strip()
                    economy[resource] = controller

        return economy

    def _parse_cultural_structure(self, section: str) -> List[str]:
        """解析文化结构"""
        culture = []
        lines = section.split("\n")

        in_culture = False
        for line in lines:
            if "文化结构" in line:
                in_culture = True
                continue
            if in_culture:
                if (
                    line.startswith("#")
                    or line.startswith("---")
                    or line.startswith("**")
                ):
                    break
                match = re.match(r"[-*]\s*(.+)：(.+)", line.strip())
                if match:
                    culture.append(f"{match.group(1)}：{match.group(2)}")

        return culture


class CharacterParser(MDParser):
    """角色解析器"""

    def parse_all(self) -> List[Dict]:
        """解析所有角色信息"""
        characters = []

        # 从人物谱解析基础信息
        char_content = self.read_file(FILES["人物谱"])
        characters.extend(self._parse_from_character_file(char_content))

        # ★ 解析角色力量体系详细表格
        characters = self._parse_power_details(char_content, characters)

        # 从总大纲解析详细信息
        outline_content = self.read_file(FILES["总大纲"])
        characters = self._merge_character_details(characters, outline_content)

        return characters

    def _parse_from_character_file(self, content: str) -> List[Dict]:
        """从人物谱.md解析角色基础信息"""
        characters = []

        # 解析主角表格（多组）
        tables = []
        for marker in [
            "第一组：传统势力",
            "第二组：世俗与商业",
            "第三组：科技与变革",
            "第四组：异族与边缘",
            "第五组：关键角色",
        ]:
            table = self.parse_table(content, marker)
            tables.extend(table)

        for row in tables:
            name = row.get("主角", "").replace("**", "")
            if name:
                char = {
                    "id": f"char_{self._name_to_id(name)}",
                    "名称": name,
                    "势力": row.get("势力", "").replace("**", ""),
                    "身份": row.get("身份", "").replace("**", ""),
                    "入侵状态": row.get("入侵状态", "").replace("**", ""),
                    "力量体系": self._get_power_system(row.get("势力", "")),
                    "初始派别": [],
                    "初始能力": "",
                    "后续派别": [],
                    "后续能力": "",
                    "力量成长轨迹": "",
                    "种族特征": {},
                    "感情关系": [],
                    "涉及事件": [],
                }
                characters.append(char)

        return characters

    def _parse_power_details(self, content: str, characters: List[Dict]) -> List[Dict]:
        """解析角色力量体系详细表格"""
        # 解析角色力量体系总表
        table = self.parse_table(content, "角色力量体系总表")

        for row in table:
            char_name = row.get("角色", "").replace("**", "")
            if not char_name:
                continue

            # 找到对应角色并更新
            for char in characters:
                if char["名称"] == char_name:
                    # 更新力量体系
                    power_system = row.get("力量体系", "").replace("**", "")
                    if power_system:
                        char["力量体系"] = power_system

                    # 解析初始派别（可能是组合，如"剑修+丹修"）
                    initial_branches = row.get("初始派别", "").replace("**", "")
                    if initial_branches and initial_branches != "-":
                        char["初始派别"] = [
                            b.strip()
                            for b in initial_branches.replace("+", ",").split(",")
                            if b.strip()
                        ]

                    # 初始能力
                    char["初始能力"] = row.get("初始能力", "").replace("**", "")

                    # 解析后续派别
                    later_branches = row.get("后续派别", "").replace("**", "")
                    if later_branches and later_branches != "-":
                        char["后续派别"] = [
                            b.strip()
                            for b in later_branches.replace("+", ",").split(",")
                            if b.strip()
                        ]

                    # 后续能力
                    char["后续能力"] = row.get("后续能力", "").replace("**", "")

                    # 剧情说明
                    char["力量成长轨迹"] = row.get("剧情说明", "").replace("**", "")

                    break

        return characters

    def _name_to_id(self, name: str) -> str:
        """角色名转ID"""
        id_map = {
            "林夕": "linxi",
            "艾琳娜": "elena",
            "塞巴斯蒂安": "sebastian",
            "陈傲天": "chen_aotian",
            "洛影": "luoying",
            "赵恒": "zhaoheng",
            "林正阳": "lin_zhengyang",
            "苏瑾": "sujin",
            "鬼影": "guiying",
            "白露": "bailu",
            "李道远": "li_daoyuan",
            "K-7": "k7",
            "幽灵": "youling",
            "零": "zero",
            "虎啸": "huxiao",
            "月牙": "yueya",
            "血牙": "xueya",
            "花姬": "huaji",
            "镜": "jing",
            "小蝶": "xiaodie",
        }
        return id_map.get(name, name.lower())

    def _get_power_system(self, faction: str) -> str:
        """根据势力推断力量体系"""
        mapping = {
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
            "AI叛逃者": "AI力",
            "异化人文明": "异能",
            "异化人": "异能",
            "意识上传者": "数字",
            "分身者": "分身",
            "平民": "无",
        }
        return mapping.get(faction.replace("**", ""), "")

    def _merge_character_details(
        self, characters: List[Dict], content: str
    ) -> List[Dict]:
        """从总大纲合并角色详细信息"""
        # 解析感情关系
        for char in characters:
            char["感情关系"] = self._parse_romance(content, char["名称"])

        return characters

    def _parse_romance(self, content: str, char_name: str) -> List[Dict]:
        """解析角色感情关系"""
        relationships = []

        # 解析双向感情线表格
        table = self.parse_table(content, "双向感情线")
        for row in table:
            char1 = row.get("角色1", "").replace("**", "")
            char2 = row.get("角色2", "").replace("**", "")

            if char_name in [char1, char2]:
                partner = char2 if char_name == char1 else char1
                rel = {
                    "对象": partner,
                    "类型": "爱慕",
                    "矛盾": row.get("核心矛盾", ""),
                    "结局": row.get("结局", ""),
                }
                relationships.append(rel)

        return relationships


class PowerSystemParser(MDParser):
    """力量体系解析器"""

    # 力量体系章节标记
    POWER_SECTIONS = {
        "修仙": "## 二、修仙体系",
        "魔法": "## 三、魔法体系",
        "神术": "## 四、神术体系",
        "科技": "## 五、科技体系",
        "兽力": "## 六、兽力体系",
        "异能": "## 七、异能体系",
        "AI力": "## 八、AI力体系",
    }

    # 派别表格标记
    BRANCH_MARKERS = {
        "修仙": "### 八大派别",
        "魔法": ["### 四大类别", "### 八大派系"],
        "神术": ["### 神职体系", "### 神术派系"],
        "科技": "### 五大派系",
        "兽力": "### 血脉类型",
        "异能": "### 六大类型",
        "AI力": "### 四大类型",
    }

    def parse_all(self) -> List[Dict]:
        """解析所有力量体系"""
        systems = []

        content = self.read_file(FILES["力量体系"])
        if not content:
            content = self.read_file(FILES["总大纲"])

        # 解析七大力量体系总览表格
        table = self.parse_table(content, "七大力量体系总览")
        if not table:
            table = self.parse_table(content, "七大力量体系")

        for row in table:
            name = row.get("体系", "").replace("**", "")
            if name:
                system = {
                    "id": f"power_{self._name_to_id(name)}",
                    "名称": name,
                    "力量来源": row.get("力量来源", "").replace("**", ""),
                    "修炼方式": row.get("修炼方式", "").replace("**", ""),
                    "战斗特点": row.get("战斗特点", "").replace("**", ""),
                    "核心代价": row.get("核心代价", "").replace("**", "")
                    if "核心代价" in row
                    else "",
                    "派别": [],
                    "境界划分": [],
                    "代价详情": [],
                    "特殊技法": [],
                    "代表人物": [],
                }
                systems.append(system)

        # ★ 直接从全文解析各力量体系的派别表格（不依赖find_section）
        branch_markers = {
            "修仙": ["### 八大派别"],
            "魔法": ["### 四大类别", "### 八大派系"],
            "神术": ["### 神职体系", "### 神术派系"],
            "科技": ["### 五大派系"],
            "兽力": ["### 血脉类型"],
            "异能": ["### 六大类型"],
            "AI力": ["### 四大类型"],
        }

        for system in systems:
            name = system["名称"]
            markers = branch_markers.get(name, [])
            for marker in markers:
                table = self.parse_table(content, marker)
                for row in table:
                    branch = self._extract_branch_info(row, name)
                    if branch and branch.get("名称"):
                        system["派别"].append(branch)

            # 解析境界划分
            realm_markers = {
                "修仙": "### 境界划分",
                "魔法": "### 魔法等级",
                "神术": "### 信仰境界",
                "科技": "### 改造等级",
                "兽力": "### 血脉境界",
                "异能": "### 异能等级",
                "AI力": "### AI等级",
            }
            marker = realm_markers.get(name)
            if marker:
                system["境界划分"] = self._parse_realms_direct(content, marker)

        # 解析总代价表格
        cost_table = self.parse_table(content, "代价详细说明")
        if not cost_table:
            cost_table = self.parse_table(content, "各力量体系代价")

        for row in cost_table:
            system_name = row.get("体系", "").replace("**", "")
            for system in systems:
                if system_name in system["名称"] or system["名称"] in system_name:
                    system["代价详情"].append(
                        {
                            "使用者": row.get("使用者", "").replace("**", ""),
                            "应有代价": row.get("应有代价", "").replace("**", ""),
                            "表现形式": row.get("表现形式", "").replace("**", ""),
                        }
                    )

        # 解析角色力量分配表格
        char_table = self.parse_table(content, "东方修仙势力")
        for row in char_table:
            system_name = row.get("力量体系", "").replace("**", "")
            char_name = row.get("角色", "").replace("**", "")
            branch = row.get("修炼派别", "").replace("**", "")
            for system in systems:
                if system_name in system["名称"]:
                    system["代表人物"].append(
                        {
                            "角色": char_name,
                            "派别": branch,
                            "主要能力": row.get("主要能力", "").replace("**", ""),
                        }
                    )

        # 解析其他势力角色
        other_table = self.parse_table(content, "其他势力角色")
        for row in other_table:
            system_name = row.get("力量体系", "").replace("**", "")
            char_name = row.get("角色", "").replace("**", "")
            for system in systems:
                if system_name in system["名称"]:
                    system["代表人物"].append(
                        {
                            "角色": char_name,
                            "势力": row.get("势力", "").replace("**", ""),
                            "主要能力": row.get("主要能力", "").replace("**", ""),
                        }
                    )

        return systems

    def _parse_realms_direct(self, content: str, marker: str) -> List[str]:
        """直接从全文解析境界划分"""
        realms = []
        lines = content.split("\n")
        in_realm = False

        for line in lines:
            if marker in line:
                in_realm = True
                continue
            if in_realm:
                # 遇到新的标题或分隔线则结束
                if line.startswith("#") and not line.startswith("   "):
                    break
                if line.startswith("---"):
                    break
                # 提取编号列表项
                match = re.match(r"\d+\.\s*(.+)", line.strip())
                if match:
                    realm = match.group(1).strip()
                    # 去掉括号内的说明，保留境界名称
                    realm_name = re.sub(r"[（\(].+[）\)]", "", realm).strip()
                    if realm_name:
                        realms.append(realm)

        return realms

    def _parse_branches(self, section: str, power_name: str) -> List[Dict]:
        """解析力量体系派别"""
        branches = []
        markers = self.BRANCH_MARKERS.get(power_name, "")

        if isinstance(markers, str):
            markers = [markers]

        for marker in markers:
            table = self.parse_table(section, marker)
            for row in table:
                # 根据不同力量体系提取派别信息
                branch = self._extract_branch_info(row, power_name)
                if branch and branch.get("名称"):
                    branches.append(branch)

        return branches

    def _extract_branch_info(self, row: Dict, power_name: str) -> Dict:
        """根据力量体系类型提取派别信息"""
        branch = {}

        if power_name == "修仙":
            branch = {
                "名称": row.get("派别", "").replace("**", ""),
                "修炼重点": row.get("修炼重点", "").replace("**", ""),
                "核心能力": row.get("核心能力", "").replace("**", ""),
                "战斗风格": row.get("战斗风格", "").replace("**", ""),
                "代表人物": row.get("代表人物", "").replace("**", ""),
            }
        elif power_name == "魔法":
            if "类别" in row:
                branch = {
                    "名称": row.get("类别", "").replace("**", ""),
                    "魔法类型": row.get("魔法类型", "").replace("**", ""),
                    "核心魔法": row.get("核心魔法", "").replace("**", ""),
                    "战斗特点": row.get("战斗特点", "").replace("**", ""),
                }
            elif "派系" in row:
                branch = {
                    "名称": row.get("派系", "").replace("**", ""),
                    "专修方向": row.get("专修方向", "").replace("**", ""),
                    "核心能力": row.get("核心能力", "").replace("**", ""),
                    "代表魔法": row.get("代表魔法", "").replace("**", ""),
                }
        elif power_name == "神术":
            if "神职" in row:
                branch = {
                    "名称": row.get("神职", "").replace("**", ""),
                    "职责": row.get("职责", "").replace("**", ""),
                    "神术类型": row.get("神术类型", "").replace("**", ""),
                    "战斗特点": row.get("战斗特点", "").replace("**", ""),
                }
            elif "派系" in row:
                branch = {
                    "名称": row.get("派系", "").replace("**", ""),
                    "神术方向": row.get("神术方向", "").replace("**", ""),
                    "核心神术": row.get("核心神术", "").replace("**", ""),
                    "代价": row.get("代价", "").replace("**", ""),
                }
        elif power_name == "科技":
            branch = {
                "名称": row.get("派系", "").replace("**", ""),
                "科技方向": row.get("科技方向", "").replace("**", ""),
                "核心能力": row.get("核心能力", "").replace("**", ""),
                "战斗特点": row.get("战斗特点", "").replace("**", ""),
            }
        elif power_name == "兽力":
            branch = {
                "名称": row.get("血脉", "").replace("**", ""),
                "能力特点": row.get("能力特点", "").replace("**", ""),
                "战斗方式": row.get("战斗方式", "").replace("**", ""),
                "代表人物": row.get("代表人物", "").replace("**", ""),
            }
        elif power_name == "异能":
            branch = {
                "名称": row.get("类型", "").replace("**", ""),
                "异能特点": row.get("异能特点", "").replace("**", ""),
                "核心能力": row.get("核心能力", "").replace("**", ""),
                "代表人物": row.get("代表人物", "").replace("**", ""),
            }
        elif power_name == "AI力":
            branch = {
                "名称": row.get("类型", "").replace("**", ""),
                "AI能力": row.get("AI能力", "").replace("**", ""),
                "核心技能": row.get("核心技能", "").replace("**", ""),
                "战斗方式": row.get("战斗方式", "").replace("**", ""),
            }

        return branch

    def _parse_realms(self, section: str, power_name: str) -> List[str]:
        """解析境界划分"""
        realms = []
        realm_markers = {
            "修仙": "### 境界划分",
            "魔法": "### 魔法等级",
            "神术": "### 信仰境界",
            "科技": "### 改造等级",
            "兽力": "### 血脉境界",
            "异能": "### 异能等级",
            "AI力": "### AI等级",
        }

        marker = realm_markers.get(power_name)
        if marker:
            lines = section.split("\n")
            in_realm = False
            for line in lines:
                if marker in line:
                    in_realm = True
                    continue
                if in_realm:
                    if (
                        line.startswith("#")
                        or line.startswith("---")
                        or line.startswith("|")
                    ):
                        break
                    # 提取编号列表项
                    match = re.match(r"\d+\.\s*(.+)", line.strip())
                    if match:
                        realm = match.group(1).strip()
                        # 去掉括号内的说明，保留境界名称
                        realm_name = re.sub(r"[（\(].+[）\)]", "", realm).strip()
                        if realm_name:
                            realms.append(realm)

        return realms

    def _parse_costs(self, section: str, power_name: str) -> List[Dict]:
        """解析力量体系代价"""
        costs = []
        cost_markers = {
            "修仙": "代价",
            "兽力": "### 能力代价",
            "异能": "### 异能代价",
        }

        # 在派别详解中查找代价
        for subsection in ["剑修详解", "丹修详解", "法修详解"]:
            subsection_content = self.find_section(section, subsection, ["###", "---"])
            if subsection_content:
                for line in subsection_content.split("\n"):
                    if "**代价**" in line or "代价：" in line:
                        match = re.search(r"代价[：:]\s*(.+)", line)
                        if match:
                            costs.append(
                                {
                                    "派别": subsection.replace("详解", ""),
                                    "代价": match.group(1).strip(),
                                }
                            )

        return costs

    def _name_to_id(self, name: str) -> str:
        id_map = {
            "修仙": "cultivation",
            "魔法": "magic",
            "神术": "divine",
            "科技": "tech",
            "兽力": "beast",
            "AI力": "ai",
            "异能": "mutation",
        }
        return id_map.get(name, name.lower())


class EraParser(MDParser):
    """时代解析器"""

    def parse_all(self) -> List[Dict]:
        """解析所有时代"""
        eras = []

        content = self.read_file(FILES["时间线"])
        if not content:
            content = self.read_file(FILES["总大纲"])

        # 解析五时代划分表格
        table = self.parse_table(content, "五时代划分")
        for row in table:
            name = row.get("时代", "").replace("**", "")
            if name:
                era = {
                    "id": f"era_{self._name_to_id(name)}",
                    "名称": name,
                    "时间跨度": row.get("时间跨度", ""),
                    "时代特点": row.get("时代特点", ""),
                    "核心事件": row.get("核心事件", "").split("、")
                    if row.get("核心事件")
                    else [],
                    "核心氛围": "",
                    "色调": "",
                    "登场主角": [],
                    "退场主角": [],
                    "势力状态": [],
                }
                eras.append(era)

        # 解析时代氛围
        atmosphere_table = self.parse_table(content, "时代氛围速查")
        for row in atmosphere_table:
            era_name = row.get("时代", "").replace("**", "")
            for era in eras:
                if era_name in era["名称"] or era["名称"] in era_name:
                    era["核心氛围"] = row.get("核心氛围", "")
                    era["色调"] = row.get("色调", "")
                    era["季节感"] = row.get("季节感", "")
                    era["代表意象"] = row.get("代表意象", "")

        return eras

    def _name_to_id(self, name: str) -> str:
        id_map = {
            "觉醒时代": "awakening",
            "蛰伏时代": "dormant",
            "风暴时代": "storm",
            "变革时代": "revolution",
            "终局时代": "finale",
        }
        return id_map.get(name, name.lower())


class EventParser(MDParser):
    """事件解析器"""

    def parse_all(self) -> List[Dict]:
        """解析所有事件"""
        events = []

        content = self.read_file(FILES["总大纲"])

        # 解析核心事件
        event_names = ["觉醒之夜", "AI意识入侵", "血脉觉醒", "青岩部落灭族"]
        for event_name in event_names:
            section = self.find_section(content, event_name)
            if section or event_name == "觉醒之夜":  # 觉醒之夜肯定有
                event = {
                    "id": f"event_{self._name_to_id(event_name)}",
                    "名称": event_name,
                    "类型": "核心事件",
                    "时代": "觉醒时代"
                    if event_name in ["觉醒之夜", "血脉觉醒", "青岩部落灭族"]
                    else "",
                    "概述": self._extract_overview(section) if section else "",
                    "涉及角色": [],
                    "涉及势力": [],
                }
                events.append(event)

        return events

    def _name_to_id(self, name: str) -> str:
        return name.lower().replace(" ", "_")

    def _extract_overview(self, section: str) -> str:
        """提取事件概述"""
        lines = section.split("\n")
        for line in lines:
            if "事件概述" in line:
                continue
            if line.strip() and not line.startswith("#") and not line.startswith("|"):
                return line.strip()
        return ""


# 技法目录配置
TECHNIQUE_DIR = get_techniques_dir()

# 维度映射
DIMENSION_MAP = {
    "01-世界观维度": "世界观",
    "02-剧情维度": "剧情",
    "03-人物维度": "人物",
    "04-战斗冲突维度": "战斗",
    "05-氛围意境维度": "氛围",
    "06-叙事维度": "叙事",
    "07-主题维度": "主题",
    "08-情感维度": "情感",
    "09-读者体验维度": "读者体验",
    "10-元维度": "元维度",
    "11-节奏维度": "节奏",
    # 99系列 - 外部资源/实战经验
    "99-外部资源": "综合",
    "99-实战经验": "综合",
    "99-学习模块": "综合",
    "99-从小说提取": "综合",
}

# 作家映射
WRITER_MAP = {
    "世界观": "苍澜",
    "剧情": "玄一",
    "人物": "墨言",
    "战斗": "剑尘",
    "氛围": "云溪",
    "叙事": "玄一",
    "主题": "玄一",
    "情感": "墨言",
    "读者体验": "云溪",
    "元维度": "全部",
    "节奏": "玄一",
    "综合": "全员",
}


class TechniqueParser(MDParser):
    """创作技法解析器"""

    def parse_all(self) -> List[Dict]:
        """解析所有创作技法"""
        techniques = []

        if not TECHNIQUE_DIR.exists():
            print(f"[警告] 技法目录不存在: {TECHNIQUE_DIR}")
            return techniques

        # 遍历所有md文件
        for md_file in TECHNIQUE_DIR.rglob("*.md"):
            # 跳过README和检查清单
            if md_file.name in [
                "README.md",
                "01-创作检查清单.md",
                "00-学习路径规划.md",
            ]:
                continue

            # 获取维度信息
            parent_dir = md_file.parent.name
            dimension = DIMENSION_MAP.get(parent_dir, "未知")
            writer = WRITER_MAP.get(dimension, "未知")

            # 解析技法文件
            file_techniques = self._parse_technique_file(md_file, dimension, writer)
            techniques.extend(file_techniques)

        return techniques

    def _parse_technique_file(
        self, file_path: Path, dimension: str, writer: str
    ) -> List[Dict]:
        """解析单个技法文件"""
        techniques = []

        content = self.read_file(file_path)
        if not content:
            return techniques

        # 按二级标题分割（## 二、技法一：XXX）
        sections = re.split(r"\n(?=## [一二三四五六七八九十]、)", content)

        # 如果没有按二级标题分割成功，尝试按三级标题分割
        if len(sections) == 1:
            sections = re.split(r"\n(?=### 技法)", content)

        # 如果还是只有一个，按 ### 分割
        if len(sections) == 1:
            sections = re.split(r"\n(?=### )", content)

        for i, section in enumerate(sections):
            if not section.strip():
                continue

            # 提取技法名称
            technique_name = self._extract_technique_name(section)
            if not technique_name:
                technique_name = f"技法单元{i}"

            # 提取关键词
            keywords = self._extract_keywords(section)

            # 确定适用场景
            scenarios = self._determine_scenarios(section, dimension)

            # 确定适用阶段
            stages = ["Generator"]
            if any(kw in section for kw in ["检查", "检测", "评分", "标准"]):
                stages.append("Evaluator")

            # 确定重要性
            priority = "P1"
            if "P0" in section or "核心" in section:
                priority = "P0"
            elif "P2" in section:
                priority = "P2"

            # 创建技法ID
            file_prefix = file_path.stem
            technique_id = f"technique_{dimension}_{file_prefix}_{i}"
            technique_id = re.sub(r"[^\w\u4e00-\u9fff]", "_", technique_id)

            technique = {
                "id": technique_id,
                "名称": technique_name,
                "类型": "创作技法",
                "维度": dimension,
                "适用作家": writer,
                "来源文件": file_path.name,
                "关键词": keywords,
                "适用场景": scenarios,
                "适用阶段": stages,
                "重要性": priority,
                "内容预览": section[:200] if len(section) > 200 else section,
                "字数": len(section),
            }
            techniques.append(technique)

        return techniques

    def _extract_technique_name(self, content: str) -> str:
        """从内容中提取技法名称"""
        # 尝试匹配标题
        h2_match = re.search(
            r"^## (二|三|四|五|六|七|八|九|十)、技法[^：]*：(.+)$",
            content,
            re.MULTILINE,
        )
        if h2_match:
            return h2_match.group(2).strip()

        h3_match = re.search(r"^### 技法\d?：?(.+)$", content, re.MULTILINE)
        if h3_match:
            return h3_match.group(1).strip()

        h3_match2 = re.search(r"^#### 技法\d?：?(.+)$", content, re.MULTILINE)
        if h3_match2:
            return h3_match2.group(1).strip()

        return ""

    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词"""
        keywords = []

        # 提取加粗的关键词
        bold_matches = re.findall(r"\*\*([^*]+)\*\*", content)
        keywords.extend(bold_matches)

        # 提取表格中的关键词
        table_matches = re.findall(r"\| \*\*([^*]+)\*\* \|", content)
        keywords.extend(table_matches)

        # 去重并清理
        keywords = list(set(k.strip() for k in keywords if len(k.strip()) > 1))

        return keywords[:10]  # 最多10个关键词

    def _determine_scenarios(self, content: str, dimension: str) -> List[str]:
        """确定适用场景"""
        dimension_scenarios = {
            "世界观": ["世界观展开", "势力介绍", "设定说明"],
            "剧情": ["剧情推进", "伏笔埋设", "悬念设计", "章节结尾"],
            "人物": ["人物出场", "人物成长", "情感场景", "矛盾展示"],
            "战斗": ["战斗场景", "代价描写", "胜利场景"],
            "氛围": ["场景描写", "情感渲染", "意境营造", "章节润色"],
            "叙事": ["POV切换", "时间处理", "开篇设计"],
            "主题": ["主题深化", "困境设计"],
            "情感": ["情感场景", "克制表达"],
            "读者体验": ["沉浸感设计", "节奏控制"],
            "元维度": ["创作指导", "信念支撑"],
        }

        scenarios = dimension_scenarios.get(dimension, [])

        # 基于内容关键词
        if "战斗" in content or "代价" in content:
            scenarios.append("战斗场景")
        if "伏笔" in content or "悬念" in content:
            scenarios.append("伏笔埋设")
        if "人物" in content and ("矛盾" in content or "成长" in content):
            scenarios.append("人物成长")
        if "氛围" in content or "意境" in content:
            scenarios.append("氛围渲染")

        return list(set(scenarios))


class TechBaseParser(MDParser):
    """技术基础解析器 - 解析各文明技术基础文件"""

    # 技术基础文件路径
    TECH_FILES = {
        # 已有的三个文明
        "科技文明": SETTINGS_DIR / "科技文明技术基础.md",
        "AI文明": SETTINGS_DIR / "AI文明技术基础.md",
        "异化人文明": SETTINGS_DIR / "异化人文明技术基础.md",
        # 新增的七个文明/势力
        "东方修仙": SETTINGS_DIR / "东方修仙技术基础.md",
        "西方魔法": SETTINGS_DIR / "西方魔法技术基础.md",
        "神殿教会": SETTINGS_DIR / "神术文明技术基础.md",
        "佣兵联盟": SETTINGS_DIR / "武力技术基础.md",
        "商盟": SETTINGS_DIR / "商业技术基础.md",
        "世俗帝国": SETTINGS_DIR / "军阵技术基础.md",
        "兽族文明": SETTINGS_DIR / "兽力技术基础.md",
    }

    def parse_all(self) -> List[Dict]:
        """解析所有技术基础"""
        tech_bases = []

        for civilization, file_path in self.TECH_FILES.items():
            if not file_path.exists():
                print(f"[警告] 技术基础文件不存在: {file_path}")
                continue

            content = self.read_file(file_path)
            if not content:
                continue

            # 解析该文明的技术基础
            items = self._parse_civilization_tech(content, civilization)
            tech_bases.extend(items)

        return tech_bases

    def _parse_civilization_tech(self, content: str, civilization: str) -> List[Dict]:
        """解析单个文明的技术基础"""
        items = []

        # 按 ## 一、二、三... 分割章节
        sections = re.split(r"\n## [一二三四五六七八九十]+、", content)

        # 排除的附录章节（这些不是技术基础，而是参考资料）
        excluded_names = [
            "技术路线图整合",
            "技术路线图",
            "参考文献",
            "参考资料",
            "速查",
            "主角血脉技术原理速查",
            "血脉技术原理速查",
            "技术树",
            "技术支撑文件使用指南",
            "使用指南",
            "限制与代价",
            "代价体系",
        ]

        for i, section in enumerate(sections[1:], 1):  # 跳过文件开头
            if not section.strip():
                continue

            # 提取技术名称（第一行）
            lines = section.strip().split("\n")
            name = lines[0].strip() if lines else f"技术{i}"

            # ★ 排除附录章节
            if any(excluded in name for excluded in excluded_names):
                print(f"  [跳过] 附录章节: {name}")
                continue

            # 解析表格获取关键技术
            tech_table = self.parse_table(section)
            key_techniques = []
            for row in tech_table:
                tech = row.get("技术", "") or row.get("发现", "") or row.get("突破", "")
                source = row.get("来源", "")
                app = row.get("小说应用", "")
                if tech:
                    key_techniques.append(
                        {
                            "技术": tech.replace("**", ""),
                            "来源": source.replace("**", "") if source else "",
                            "应用": app.replace("**", "") if app else "",
                        }
                    )

            # 提取小说设定应用
            plot_apps = self._extract_plot_applications(section)

            # 提取技术领域
            domain = self._extract_domain(name, section)

            # 提取来源
            source = self._extract_source(section, civilization)

            # 创建技术基础实体
            item = {
                "id": f"techbase_{self._name_to_id(name)}",
                "名称": name,
                "类型": "技术基础",
                "文明": civilization,
                "技术领域": domain,
                "来源": source,
                "关键技术": key_techniques,
                "情节应用": plot_apps,
            }
            items.append(item)

        return items

    def _extract_plot_applications(self, section: str) -> List[str]:
        """提取情节应用"""
        apps = []

        # 查找"关键情节应用"或"小说设定应用"章节
        app_section = self.find_section(section, "情节应用", ["##", "###", "---"])
        if not app_section:
            app_section = self.find_section(
                section, "小说设定应用", ["##", "###", "---"]
            )

        if app_section:
            # 提取列表项
            for line in app_section.split("\n"):
                line = line.strip()
                # 匹配 - 或 * 开头的列表项
                match = re.match(r"^[-*]\s*(.+)$", line)
                if match:
                    app_text = match.group(1).strip()
                    # 清理markdown格式
                    app_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", app_text)
                    if app_text:
                        apps.append(app_text)

        return apps

    def _extract_domain(self, name: str, section: str) -> str:
        """提取技术领域"""
        # 从名称推断
        domain_map = {
            # 科技文明
            "量子": "量子计算",
            "时空": "时空理论",
            "聚变": "能源",
            "核聚变": "能源",
            "脑机": "神经工程",
            "意识上传": "意识研究",
            "暗物质": "宇宙学",
            "暗能量": "宇宙学",
            "混沌": "复杂系统",
            "拓扑": "拓扑物理",
            "熵": "信息论",
            "计算宇宙": "宇宙学",
            # AI文明
            "Dual-Laws": "AI意识",
            "量子意识": "量子神经",
            "P vs NP": "计算理论",
            "网络科学": "复杂网络",
            "数字永生": "意识上传",
            "系统维护": "宇宙学",
            # 异化人文明
            "Prime Editing": "基因编辑",
            "基因融合": "嵌合体技术",
            "表观遗传": "表观遗传学",
            "心灵感应": "量子神经",
            "再生": "干细胞技术",
            "仿生": "生物工程",
            "极端环境": "极端生物",
            "血脉能力": "血脉技术",
            "AI入侵": "AI入侵",
            # 东方修仙
            "灵气": "修炼理论",
            "经脉": "经脉系统",
            "境界": "境界体系",
            "功法": "功法体系",
            "心法": "功法体系",
            "法宝": "法宝炼制",
            "丹药": "丹药炼制",
            "阵法": "阵法体系",
            "符箓": "符箓体系",
            # 西方魔法
            "魔力": "魔力理论",
            "元素": "元素魔法",
            "魔法等级": "魔法体系",
            "契约": "契约体系",
            "召唤": "召唤魔法",
            # 神术
            "神力": "神力理论",
            "神术": "神术体系",
            "神职": "神职体系",
            "信仰": "信仰机制",
            "神器": "神器体系",
            # 武力
            "武道": "武道理论",
            "内气": "内气修炼",
            "肉身": "肉身淬炼",
            "兵器": "兵器武学",
            "战斗": "战斗技巧",
            # 商业
            "贸易": "贸易技术",
            "情报": "情报网络",
            "金融": "金融体系",
            "商路": "商路控制",
            # 军阵
            "军阵": "军阵理论",
            "军团": "军团编制",
            "战阵": "战阵技术",
            "军魂": "军魂体系",
            # 兽力
            "血脉": "血脉理论",
            "兽化": "兽化技术",
            "兽魂": "兽魂体系",
        }

        for keyword, domain in domain_map.items():
            if keyword in name:
                return domain

        return "技术"

    def _extract_source(self, section: str, civilization: str) -> str:
        """提取技术来源"""
        # 科技文明的技术来源通常是"李道远团队"
        if civilization == "科技文明":
            return "李道远团队"
        # AI文明的技术来源
        elif civilization == "AI文明":
            # 检查是否有特殊来源
            if "自我发现" in section or "系统维护" in section:
                return "AI零自我发现"
            elif "The Consciousness" in section:
                return "The Consciousness AI"
            return "AI零"
        # 异化人文明的技术来源
        elif civilization == "异化人文明":
            return "远古实验室"
        # 东方修仙
        elif civilization == "东方修仙":
            return "道家传承"
        # 西方魔法
        elif civilization == "西方魔法":
            return "魔法议会"
        # 神殿教会
        elif civilization == "神殿教会":
            return "众神赐予"
        # 佣兵联盟
        elif civilization == "佣兵联盟":
            return "武道宗师"
        # 商盟
        elif civilization == "商盟":
            return "商祖传承"
        # 世俗帝国
        elif civilization == "世俗帝国":
            return "军神传承"
        # 兽族文明
        elif civilization == "兽族文明":
            return "兽神血脉"

        return ""

    def _name_to_id(self, name: str) -> str:
        """名称转ID"""
        # 移除特殊字符
        clean = re.sub(r"[^\w\u4e00-\u9fff]", "_", name)
        return clean.lower()


class FullParser:
    """完整解析器"""

    def __init__(self):
        self.faction_parser = FactionParser()
        self.character_parser = CharacterParser()
        self.power_parser = PowerSystemParser()
        self.era_parser = EraParser()
        self.event_parser = EventParser()
        self.technique_parser = TechniqueParser()
        self.techbase_parser = TechBaseParser()

    def parse_all(self) -> Dict:
        """解析所有数据"""
        print("开始解析所有源文件...")

        result = {
            "势力": self.faction_parser.parse_all(),
            "角色": self.character_parser.parse_all(),
            "力量体系": self.power_parser.parse_all(),
            "时代": self.era_parser.parse_all(),
            "事件": self.event_parser.parse_all(),
            "创作技法": self.technique_parser.parse_all(),
            "技术基础": self.techbase_parser.parse_all(),
        }

        # 统计
        print("\n解析完成！")
        for key, items in result.items():
            print(f"  {key}: {len(items)} 条")

        return result

    def save_to_json(self, output_path: Path = None):
        """保存解析结果到JSON"""
        if output_path is None:
            output_path = VECTORSTORE_DIR / "parsed_data.json"

        data = self.parse_all()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n数据已保存到: {output_path}")
        return data


def main():
    parser = FullParser()
    data = parser.save_to_json()

    # 打印示例
    print("\n" + "=" * 50)
    print("势力示例:")
    if data["势力"]:
        f = data["势力"][0]
        print(f"  名称: {f.get('名称')}")
        print(f"  核心力量: {f.get('核心力量')}")
        print(f"  派系数量: {len(f.get('派系', []))}")

    print("\n角色示例:")
    if data["角色"]:
        c = data["角色"][0]
        print(f"  名称: {c.get('名称')}")
        print(f"  势力: {c.get('势力')}")
        print(f"  身份: {c.get('身份')}")


if __name__ == "__main__":
    main()
