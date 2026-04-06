#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大纲/设定向量化脚本
将章节大纲、角色设定、势力设定等向量化存入数据库

使用方法：
    python knowledge_vectorizer.py --rebuild
"""

import os
import re
import json
import hashlib
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    import chromadb
except ImportError:
    print("请安装 chromadb: pip install chromadb")
    exit(1)

# 添加项目根目录到 sys.path
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import (
    get_project_root,
    get_vectorstore_dir,
    get_settings_dir,
    get_techniques_dir,
)

# ============================================================
# 配置
# ============================================================

PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
COLLECTION_NAME = "novelist_knowledge"

# 数据类型
DATA_TYPES = {
    "outline": "大纲",
    "character": "角色",
    "faction": "势力",
    "power": "力量体系",
    "event": "事件",
    "setting": "设定",
    "worldview": "世界观",
}

# 拼音映射表（常用名称）
PINYIN_MAP = {
    # 角色
    "血牙": "xueya",
    "铁牙": "tieya",
    "林夕": "linxi",
    "艾琳娜": "elina",
    "塞巴斯蒂安": "sebastian",
    "陈傲天": "chenotian",
    "洛影": "luoying",
    "赵恒": "zhaoheng",
    "林正阳": "linzhengyang",
    "苏瑾": "sujin",
    "鬼影": "guiying",
    "白露": "bailu",
    "李道远": "lidaoyuan",
    "虎啸": "huxiao",
    "月牙": "yueya",
    "花姬": "huaji",
    "镜": "jing",
    "小蝶": "xiaodie",
    # 势力
    "佣兵联盟": "mercenary",
    "青岩部落": "qingyan",
    "东方修仙": "eastern_cultivation",
    "西方魔法": "western_magic",
    "神殿教会": "temple",
    "商盟": "merchant",
    "世俗帝国": "empire",
    "科技文明": "tech_civilization",
    "兽族文明": "beast_civilization",
    "AI文明": "ai_civilization",
    "异化人文明": "mutant_civilization",
    # 力量体系
    "修仙": "cultivation",
    "魔法": "magic",
    "神术": "divine",
    "科技": "tech",
    "兽力": "bloodline",
    "血脉": "bloodline",
    "异能": "ability",
}


# ============================================================
# 数据单元类
# ============================================================


@dataclass
class KnowledgeUnit:
    """知识单元"""

    id: str
    type: str  # outline, character, faction, power, event, setting, worldview
    name: str
    content: str
    metadata: Dict[str, Any]
    source_file: str
    source_section: str
    created_at: str
    updated_at: str
    content_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 解析器
# ============================================================


class OutlineParser:
    """章节大纲解析器"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding="utf-8")
        self.units: List[KnowledgeUnit] = []

    def parse(self) -> List[KnowledgeUnit]:
        """解析章节大纲"""
        # 提取章节信息
        chapter_info = self._extract_chapter_info()

        # 提取场景
        scenes = self._extract_scenes()

        # 生成单元
        now = datetime.now().isoformat()

        # 章节信息单元
        chapter_unit = KnowledgeUnit(
            id=f"outline_chapter_{chapter_info['chapter']:03d}",
            type="outline",
            name=f"第{chapter_info['chapter']}章：{chapter_info['name']}",
            content=self._format_chapter_info(chapter_info),
            metadata={
                "章节": chapter_info["chapter"],
                "章节名": chapter_info["name"],
                "视角": chapter_info.get("视角", ""),
                "身份": chapter_info.get("身份", ""),
                "核心情感": chapter_info.get("核心情感", []),
                "字数": chapter_info.get("字数", 0),
            },
            source_file=str(self.file_path.relative_to(PROJECT_DIR)),
            source_section="章节信息",
            created_at=now,
            updated_at=now,
            content_hash=self._hash_content(self._format_chapter_info(chapter_info)),
        )
        self.units.append(chapter_unit)

        # 场景单元
        for i, scene in enumerate(scenes, 1):
            scene_unit = KnowledgeUnit(
                id=f"outline_chapter_{chapter_info['chapter']:03d}_scene_{i:02d}",
                type="outline",
                name=f"第{chapter_info['chapter']}章 场景{i}：{scene['name']}",
                content=scene["content"],
                metadata={
                    "章节": chapter_info["chapter"],
                    "场景序号": i,
                    "场景名": scene["name"],
                },
                source_file=str(self.file_path.relative_to(PROJECT_DIR)),
                source_section=f"场景{i}：{scene['name']}",
                created_at=now,
                updated_at=now,
                content_hash=self._hash_content(scene["content"]),
            )
            self.units.append(scene_unit)

        return self.units

    def _extract_chapter_info(self) -> Dict[str, Any]:
        """提取章节信息"""
        info = {"chapter": 1, "name": "未知"}

        # 提取章节名
        title_match = re.search(r"# 《众生界》第(\d+)章[：:](.+)", self.content)
        if title_match:
            info["chapter"] = int(title_match.group(1))
            info["name"] = title_match.group(2).strip()

        # 提取表格信息
        table_pattern = r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|"
        for match in re.finditer(table_pattern, self.content):
            key = match.group(1).strip()
            value = match.group(2).strip()

            if key == "视角":
                info["视角"] = value
            elif key == "身份":
                info["身份"] = value
            elif key == "核心情感":
                info["核心情感"] = [v.strip() for v in value.split("、")]
            elif key == "中文字数":
                info["字数"] = int(value.replace(",", ""))

        return info

    def _extract_scenes(self) -> List[Dict[str, str]]:
        """提取场景"""
        scenes = []

        # 按 ### 场景 分割
        scene_pattern = r"### 场景([一二三四五六七八九十]+)[：:](.+?)(?=\n>|$)"

        for match in re.finditer(scene_pattern, self.content, re.DOTALL):
            scene_num = match.group(1)
            scene_name = match.group(2).strip()

            # 提取场景内容（引用块）
            content_start = match.end()
            next_scene = self.content.find("### 场景", content_start)
            if next_scene == -1:
                scene_content = self.content[content_start:].strip()
            else:
                scene_content = self.content[content_start:next_scene].strip()

            # 清理内容
            scene_content = self._clean_scene_content(scene_content)

            scenes.append(
                {
                    "name": scene_name,
                    "content": scene_content,
                }
            )

        return scenes

    def _clean_scene_content(self, content: str) -> str:
        """清理场景内容"""
        # 移除 markdown 引用符号
        content = re.sub(r"^>\s*", "", content, flags=re.MULTILINE)
        # 移除多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()

    def _format_chapter_info(self, info: Dict[str, Any]) -> str:
        """格式化章节信息"""
        lines = [f"# 第{info['chapter']}章：{info['name']}"]

        if "视角" in info:
            lines.append(f"视角：{info['视角']}")
        if "身份" in info:
            lines.append(f"身份：{info['身份']}")
        if "核心情感" in info:
            lines.append(f"核心情感：{'、'.join(info['核心情感'])}")

        return "\n".join(lines)

    def _hash_content(self, content: str) -> str:
        """计算内容hash"""
        return hashlib.md5(content.encode()).hexdigest()


class SettingParser:
    """设定文件解析器"""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding="utf-8")
        self.units: List[KnowledgeUnit] = []

    def parse(self) -> List[KnowledgeUnit]:
        """解析设定文件"""
        now = datetime.now().isoformat()
        file_name = self.file_path.stem

        # 根据文件名选择解析方式
        if "力量体系" in str(self.file_path):
            return self._parse_power_system(now)
        elif "人物谱" in str(self.file_path):
            return self._parse_characters(now)
        elif "势力" in str(self.file_path):
            return self._parse_factions(now)
        else:
            return self._parse_generic(now)

    def _parse_power_system(self, now: str) -> List[KnowledgeUnit]:
        """解析力量体系"""
        units = []

        # 按 ## 或 ### 分割
        sections = re.split(r"\n##\s+", self.content)

        for section in sections[1:]:  # 跳过文件开头
            lines = section.strip().split("\n")
            if not lines:
                continue

            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()

            if not content:
                continue

            # 生成ID
            power_name = title.replace("代价", "").replace("技法", "").strip()
            power_id = self._get_id(power_name, "power")

            unit = KnowledgeUnit(
                id=power_id,
                type="power",
                name=title,
                content=content,
                metadata={
                    "体系": power_name,
                    "类型": "代价" if "代价" in title else "技法",
                },
                source_file=str(self.file_path.relative_to(PROJECT_DIR)),
                source_section=title,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(content.encode()).hexdigest(),
            )
            units.append(unit)

        self.units = units
        return units

    def _parse_characters(self, now: str) -> List[KnowledgeUnit]:
        """解析人物谱"""
        units = []

        # 提取主角表格
        table_pattern = (
            r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        )

        for match in re.finditer(table_pattern, self.content):
            name = match.group(1).strip()
            faction = match.group(2).strip()
            identity = match.group(3).strip()
            invasion = match.group(4).strip()

            char_id = self._get_id(name, "char")

            unit = KnowledgeUnit(
                id=char_id,
                type="character",
                name=name,
                content=f"{name}，{faction}{identity}，入侵状态：{invasion}",
                metadata={
                    "姓名": name,
                    "势力": faction,
                    "身份": identity,
                    "入侵状态": invasion,
                },
                source_file=str(self.file_path.relative_to(PROJECT_DIR)),
                source_section="主角阵容",
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(name.encode()).hexdigest(),
            )
            units.append(unit)

        self.units = units
        return units

    def _parse_factions(self, now: str) -> List[KnowledgeUnit]:
        """解析势力"""
        units = []

        # 按势力名称分割
        faction_pattern = r"###\s+(.+?势力|.+?联盟|.+?文明)"

        for match in re.finditer(faction_pattern, self.content):
            faction_name = match.group(1).strip()
            faction_id = self._get_id(faction_name, "faction")

            # 提取势力内容
            content_start = match.end()
            next_faction = self.content.find("### ", content_start)
            if next_faction == -1:
                faction_content = self.content[content_start:].strip()
            else:
                faction_content = self.content[content_start:next_faction].strip()

            if len(faction_content) < 50:
                continue

            unit = KnowledgeUnit(
                id=faction_id,
                type="faction",
                name=faction_name,
                content=faction_content,
                metadata={
                    "势力名": faction_name,
                },
                source_file=str(self.file_path.relative_to(PROJECT_DIR)),
                source_section=faction_name,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(faction_content.encode()).hexdigest(),
            )
            units.append(unit)

        self.units = units
        return units

    def _parse_generic(self, now: str) -> List[KnowledgeUnit]:
        """通用解析"""
        units = []

        # 按 ## 分割
        sections = re.split(r"\n##\s+", self.content)

        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            title = lines[0].strip()
            content = "\n".join(lines[1:]).strip()

            if len(content) < 100:
                continue

            unit = KnowledgeUnit(
                id=self._get_id(title, "setting"),
                type="setting",
                name=title,
                content=content,
                metadata={},
                source_file=str(self.file_path.relative_to(PROJECT_DIR)),
                source_section=title,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(content.encode()).hexdigest(),
            )
            units.append(unit)

        self.units = units
        return units

    def _get_id(self, name: str, type_prefix: str) -> str:
        """生成ID"""
        # 查找映射表
        for cn, pinyin in PINYIN_MAP.items():
            if cn in name:
                return f"{type_prefix}_{pinyin}"

        # 无映射则清理名称
        clean_name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "_", name)
        return f"{type_prefix}_{clean_name}"


# ============================================================
# 向量化器
# ============================================================


class KnowledgeVectorizer:
    """知识向量化器"""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
        self.collection = None
        self.stats = {
            "total": 0,
            "by_type": {},
        }

    def create_collection(self, rebuild: bool = False):
        """创建/获取集合"""
        if rebuild:
            try:
                self.client.delete_collection(COLLECTION_NAME)
                print(f"已删除现有集合: {COLLECTION_NAME}")
            except:
                pass

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"description": "众生界大纲与设定知识库"}
        )

    def add_units(self, units: List[KnowledgeUnit]):
        """添加知识单元"""
        if not units:
            return

        for unit in units:
            # 准备数据
            doc = f"{unit.name}\n\n{unit.content}"

            # 添加到集合
            self.collection.upsert(
                ids=[unit.id],
                documents=[doc],
                metadatas=[
                    {
                        "类型": unit.type,
                        "名称": unit.name,
                        "来源文件": unit.source_file,
                        "来源章节": unit.source_section,
                        "内容hash": unit.content_hash,
                        "创建时间": unit.created_at,
                        "更新时间": unit.updated_at,
                        **{k: str(v) for k, v in unit.metadata.items()},
                    }
                ],
            )

            # 更新统计
            self.stats["total"] += 1
            self.stats["by_type"][unit.type] = (
                self.stats["by_type"].get(unit.type, 0) + 1
            )

    def process_outline_files(self):
        """处理章节大纲文件"""
        outline_dir = PROJECT_DIR / "章节大纲"

        if not outline_dir.exists():
            print("章节大纲目录不存在")
            return

        print("\n[处理章节大纲]")

        for md_file in outline_dir.glob("*.md"):
            print(f"  解析: {md_file.name}")

            parser = OutlineParser(md_file)
            units = parser.parse()

            self.add_units(units)
            print(f"    -> 生成 {len(units)} 个知识单元")

    def process_setting_files(self):
        """处理设定文件"""
        setting_dir = PROJECT_DIR / "设定"

        if not setting_dir.exists():
            print("设定目录不存在")
            return

        print("\n[处理设定文件]")

        for md_file in setting_dir.glob("*.md"):
            print(f"  解析: {md_file.name}")

            parser = SettingParser(md_file)
            units = parser.parse()

            self.add_units(units)
            print(f"    -> 生成 {len(units)} 个知识单元")

    def process_total_outline(self):
        """处理总大纲"""
        total_outline = PROJECT_DIR / "总大纲.md"

        if not total_outline.exists():
            print("总大纲文件不存在")
            return

        print("\n[处理总大纲]")
        print(f"  解析: {total_outline.name}")

        # 使用设定解析器处理总大纲
        parser = SettingParser(total_outline)
        units = parser.parse()

        self.add_units(units)
        print(f"    -> 生成 {len(units)} 个知识单元")

    def print_stats(self):
        """打印统计"""
        print("\n" + "=" * 60)
        print("向量化完成")
        print("=" * 60)
        print(f"总知识单元: {self.stats['total']}")
        print("\n按类型分布:")
        for type_name, count in sorted(self.stats["by_type"].items()):
            type_cn = DATA_TYPES.get(type_name, type_name)
            print(f"  {type_cn}: {count}条")

    def verify(self):
        """验证"""
        count = self.collection.count()
        print(f"\n验证: 集合中共有 {count} 条记录")

        # 显示一个示例
        if count > 0:
            result = self.collection.get(limit=1)
            print(f"\n示例条目:")
            print(f"  ID: {result['ids'][0]}")
            print(f"  类型: {result['metadatas'][0].get('类型', '未知')}")
            print(f"  名称: {result['metadatas'][0].get('名称', '未知')}")


# ============================================================
# 主函数
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="大纲/设定向量化脚本")
    parser.add_argument("--rebuild", action="store_true", help="重建数据库")
    args = parser.parse_args()

    print("=" * 60)
    print("众生界知识库向量化")
    print("=" * 60)

    # 创建向量化器
    vectorizer = KnowledgeVectorizer()
    vectorizer.create_collection(rebuild=args.rebuild)

    # 处理各类文件
    vectorizer.process_outline_files()
    vectorizer.process_setting_files()
    vectorizer.process_total_outline()

    # 打印统计
    vectorizer.print_stats()
    vectorizer.verify()

    print("\n" + "=" * 60)
    print("完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
