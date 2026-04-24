"""
向量化管理器 - 数据向量化处理
整合 knowledge_vectorizer.py、technique_vectorizer.py 的核心逻辑
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# [N14 2026-04-18] M2-β 后 config_loader 已迁移至 core/，
# 删除对 .archived/vectorstore_core_20260418/ 的 sys.path 注入
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from core.config_loader import get_project_root, get_vectorstore_dir

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


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


@dataclass
class TechniqueChunk:
    """技法分块"""

    id: str
    content: str
    metadata: Dict[str, Any]


class VectorizerManager:
    """
    向量化管理器

    支持向量化两类数据：
    - 知识单元（大纲、设定、角色、势力等）
    - 创作技法（技法笔记、分块处理）

    注意：此模块主要用于本地ChromaDB存储，
    主向量库建议使用Qdrant（通过SyncManager同步）
    """

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
    }

    def __init__(self, project_dir: Optional[Path] = None):
        """
        初始化向量化管理器

        Args:
            project_dir: 项目根目录（默认从配置加载）
        """
        self.project_dir = project_dir or (
            get_project_root() if HAS_CONFIG_LOADER else Path.cwd()
        )
        self.vectorstore_dir = (
            get_vectorstore_dir()
            if HAS_CONFIG_LOADER
            else self.project_dir / ".vectorstore"
        )

        # 数据源路径
        self.outline_dir = self.project_dir / "章节大纲"
        self.setting_dir = self.project_dir / "设定"
        self.total_outline_file = self.project_dir / "总大纲.md"
        self.techniques_dir = self.project_dir / "创作技法"

        # 统计
        self.stats = {
            "total": 0,
            "by_type": {},
        }

    def vectorize_knowledge(self, rebuild: bool = False) -> Dict[str, Any]:
        """
        向量化大纲/设定

        Args:
            rebuild: 是否重建数据库

        Returns:
            向量化结果统计
        """
        try:
            import chromadb
        except ImportError:
            raise ImportError("请安装 chromadb: pip install chromadb")

        print("=" * 60)
        print("知识库向量化")
        print("=" * 60)

        client = chromadb.PersistentClient(path=str(self.vectorstore_dir))

        # 重建数据库
        collection_name = "novelist_knowledge"
        if rebuild:
            try:
                client.delete_collection(collection_name)
                print(f"已删除现有集合: {collection_name}")
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "众生界大纲与设定知识库"},
        )

        # 处理各类文件
        self._process_outline_files(collection)
        self._process_setting_files(collection)
        self._process_total_outline(collection)

        # 打印统计
        self._print_stats("知识库")

        return {
            "total": self.stats["total"],
            "by_type": self.stats["by_type"],
            "collection": collection_name,
        }

    def vectorize_techniques(self, rebuild: bool = False) -> Dict[str, Any]:
        """
        向量化创作技法

        Args:
            rebuild: 是否重建数据库

        Returns:
            向量化结果统计
        """
        try:
            import chromadb
        except ImportError:
            raise ImportError("请安装 chromadb: pip install chromadb")

        print("=" * 60)
        print("创作技法向量化")
        print("=" * 60)

        client = chromadb.PersistentClient(path=str(self.vectorstore_dir))

        # 重建数据库
        collection_name = "novelist_techniques"
        if rebuild:
            try:
                client.delete_collection(collection_name)
                print(f"已删除现有集合: {collection_name}")
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "众生界创作技法向量数据库"},
        )

        # 处理技法文件
        chunks = self._process_technique_files()

        # 批量添加
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            collection.add(
                ids=[chunk.id for chunk in batch],
                documents=[chunk.content for chunk in batch],
                metadatas=[chunk.metadata for chunk in batch],
            )
            print(f"已添加 {min(i + batch_size, len(chunks))}/{len(chunks)} 个技法单元")

        print(f"\n向量化完成！总技法单元数: {len(chunks)}")

        return {
            "total": len(chunks),
            "collection": collection_name,
        }

    def _process_outline_files(self, collection):
        """处理章节大纲文件"""
        if not self.outline_dir.exists():
            print("章节大纲目录不存在")
            return

        print("\n[处理章节大纲]")

        for md_file in self.outline_dir.glob("*.md"):
            print(f"  解析: {md_file.name}")
            units = self._parse_outline(md_file)
            self._add_units(collection, units)
            print(f"    -> 生成 {len(units)} 个知识单元")

    def _process_setting_files(self, collection):
        """处理设定文件"""
        if not self.setting_dir.exists():
            print("设定目录不存在")
            return

        print("\n[处理设定文件]")

        for md_file in self.setting_dir.glob("*.md"):
            print(f"  解析: {md_file.name}")
            units = self._parse_setting(md_file)
            self._add_units(collection, units)
            print(f"    -> 生成 {len(units)} 个知识单元")

    def _process_total_outline(self, collection):
        """处理总大纲

        .. deprecated::
            此方法使用已废弃的 chromadb 路径。
            请使用 core.change_detector.sync_manager_adapter.SyncManagerAdapter
            的 sync_total_outline_to_qdrant() 方法将总大纲同步到 Qdrant。
        """
        print(
            "[DEPRECATED] _process_total_outline: chromadb 路径已废弃，"
            "总大纲 Qdrant 同步请使用 SyncManagerAdapter.sync_total_outline_to_qdrant()"
        )
        # 跳过，不向 chromadb collection 写入任何内容
        return

    def _process_technique_files(self) -> List[TechniqueChunk]:
        """处理技法文件"""
        if not self.techniques_dir.exists():
            print("技法目录不存在")
            return []

        print("\n[处理技法文件]")

        all_chunks = []
        skip_files = [
            "README.md",
            "01-创作检查清单.md",
            "00-学习路径规划.md",
        ]

        for md_file in self.techniques_dir.rglob("*.md"):
            if md_file.name in skip_files:
                continue

            print(f"  处理: {md_file.relative_to(self.techniques_dir)}")
            chunks = self._split_technique_file(md_file)
            all_chunks.extend(chunks)
            print(f"    -> 生成 {len(chunks)} 个技法单元")

        return all_chunks

    def _parse_outline(self, file_path: Path) -> List[KnowledgeUnit]:
        """解析章节大纲"""
        content = file_path.read_text(encoding="utf-8")
        units = []

        # 提取章节信息
        chapter_info = self._extract_chapter_info(content)

        # 提取场景
        scenes = self._extract_scenes(content)

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
            source_file=str(file_path.relative_to(self.project_dir)),
            source_section="章节信息",
            created_at=now,
            updated_at=now,
            content_hash=hashlib.md5(
                self._format_chapter_info(chapter_info).encode()
            ).hexdigest(),
        )
        units.append(chapter_unit)

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
                source_file=str(file_path.relative_to(self.project_dir)),
                source_section=f"场景{i}：{scene['name']}",
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(scene["content"].encode()).hexdigest(),
            )
            units.append(scene_unit)

        return units

    def _parse_setting(self, file_path: Path) -> List[KnowledgeUnit]:
        """解析设定文件"""
        content = file_path.read_text(encoding="utf-8")
        units = []
        now = datetime.now().isoformat()

        # 根据文件路径选择解析方式
        if "力量体系" in str(file_path):
            units = self._parse_power_system(content, file_path, now)
        elif "人物谱" in str(file_path):
            units = self._parse_characters(content, file_path, now)
        elif "势力" in str(file_path):
            units = self._parse_factions(content, file_path, now)
        else:
            units = self._parse_generic(content, file_path, now)

        return units

    def _parse_power_system(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]:
        """解析力量体系"""
        units = []

        sections = re.split(r"\n##\s+", content)

        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            title = lines[0].strip()
            section_content = "\n".join(lines[1:]).strip()

            if not section_content:
                continue

            power_name = title.replace("代价", "").replace("技法", "").strip()
            power_id = self._get_id(power_name, "power")

            unit = KnowledgeUnit(
                id=power_id,
                type="power",
                name=title,
                content=section_content,
                metadata={
                    "体系": power_name,
                    "类型": "代价" if "代价" in title else "技法",
                },
                source_file=str(file_path.relative_to(self.project_dir)),
                source_section=title,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(section_content.encode()).hexdigest(),
            )
            units.append(unit)

        return units

    def _parse_characters(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]:
        """解析人物谱"""
        units = []

        table_pattern = (
            r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        )

        for match in re.finditer(table_pattern, content):
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
                source_file=str(file_path.relative_to(self.project_dir)),
                source_section="主角阵容",
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(name.encode()).hexdigest(),
            )
            units.append(unit)

        return units

    def _parse_factions(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]:
        """解析势力"""
        units = []

        faction_pattern = r"###\s+(.+?势力|.+?联盟|.+?文明)"

        for match in re.finditer(faction_pattern, content):
            faction_name = match.group(1).strip()
            faction_id = self._get_id(faction_name, "faction")

            content_start = match.end()
            next_faction = content.find("### ", content_start)
            if next_faction == -1:
                faction_content = content[content_start:].strip()
            else:
                faction_content = content[content_start:next_faction].strip()

            if len(faction_content) < 50:
                continue

            unit = KnowledgeUnit(
                id=faction_id,
                type="faction",
                name=faction_name,
                content=faction_content,
                metadata={"势力名": faction_name},
                source_file=str(file_path.relative_to(self.project_dir)),
                source_section=faction_name,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(faction_content.encode()).hexdigest(),
            )
            units.append(unit)

        return units

    def _parse_generic(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]:
        """通用解析"""
        units = []

        sections = re.split(r"\n##\s+", content)

        for section in sections[1:]:
            lines = section.strip().split("\n")
            if not lines:
                continue

            title = lines[0].strip()
            section_content = "\n".join(lines[1:]).strip()

            if len(section_content) < 100:
                continue

            unit = KnowledgeUnit(
                id=self._get_id(title, "setting"),
                type="setting",
                name=title,
                content=section_content,
                metadata={},
                source_file=str(file_path.relative_to(self.project_dir)),
                source_section=title,
                created_at=now,
                updated_at=now,
                content_hash=hashlib.md5(section_content.encode()).hexdigest(),
            )
            units.append(unit)

        return units

    def _split_technique_file(self, file_path: Path) -> List[TechniqueChunk]:
        """将技法文件分割成多个技法单元"""
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        chunks = []

        # 获取维度信息
        parent_dir = file_path.parent.name
        dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
        writer = self.WRITER_MAP.get(dimension, "未知")

        # 按二级标题分割
        sections = re.split(r"\n(?=## [一二三四五六七八九十]、)", content)

        if len(sections) == 1:
            sections = re.split(r"\n(?=### 技法)", content)

        if len(sections) == 1:
            sections = re.split(r"\n(?=### )", content)

        chunk_id = 0
        for section in sections:
            if not section.strip():
                continue

            # 提取技法名称
            technique_name = self._extract_technique_name(section)
            if not technique_name:
                title_match = re.search(r"^##\s+(.+)$", section, re.MULTILINE)
                if title_match:
                    technique_name = title_match.group(1).strip()
                else:
                    technique_name = f"技法单元{chunk_id}"

            # 提取关键词
            keywords = self._extract_keywords(section)

            # 确定适用场景
            scenarios = self._determine_applicable_scenarios(section, dimension)

            # 确定适用阶段
            stages = []
            if any(kw in section for kw in ["检查", "检测", "评分", "标准"]):
                stages.append("Evaluator")
            stages.append("Generator")

            # 确定重要性
            priority = "P1"
            if "P0" in section or "核心" in section:
                priority = "P0"
            elif "P2" in section:
                priority = "P2"

            # 创建分块ID
            file_prefix = file_path.stem
            chunk_id_str = f"{dimension}_{file_prefix}_{chunk_id}"
            chunk_id_str = re.sub(r"[^\w\u4e00-\u9fff]", "_", chunk_id_str)
            if chunk_id_str[0].isdigit():
                chunk_id_str = f"t_{chunk_id_str}"

            keywords_str = ",".join(keywords) if keywords else ""
            scenarios_str = ",".join(scenarios) if scenarios else ""
            stages_str = ",".join(stages) if stages else ""

            chunk = TechniqueChunk(
                id=chunk_id_str,
                content=section.strip(),
                metadata={
                    "维度": dimension,
                    "技法名称": technique_name,
                    "来源文件": file_path.name,
                    "来源路径": str(file_path.relative_to(self.techniques_dir.parent)),
                    "关键词": keywords_str,
                    "适用场景": scenarios_str,
                    "适用阶段": stages_str,
                    "适用作家": writer,
                    "重要性": priority,
                    "字数": len(section),
                },
            )
            chunks.append(chunk)
            chunk_id += 1

        return chunks

    def _extract_chapter_info(self, content: str) -> Dict[str, Any]:
        """提取章节信息"""
        info = {"chapter": 1, "name": "未知"}

        title_match = re.search(r"# 《众生界》第(\d+)章[：:](.+)", content)
        if title_match:
            info["chapter"] = int(title_match.group(1))
            info["name"] = title_match.group(2).strip()

        table_pattern = r"\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|"
        for match in re.finditer(table_pattern, content):
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

    def _extract_scenes(self, content: str) -> List[Dict[str, str]]:
        """提取场景"""
        scenes = []

        scene_pattern = r"### 场景([一二三四五六七八九十]+)[：:](.+?)(?=\n>|$)"

        for match in re.finditer(scene_pattern, content, re.DOTALL):
            scene_name = match.group(2).strip()

            content_start = match.end()
            next_scene = content.find("### 场景", content_start)
            if next_scene == -1:
                scene_content = content[content_start:].strip()
            else:
                scene_content = content[content_start:next_scene].strip()

            scene_content = self._clean_scene_content(scene_content)
            scenes.append({"name": scene_name, "content": scene_content})

        return scenes

    def _clean_scene_content(self, content: str) -> str:
        """清理场景内容"""
        content = re.sub(r"^>\s*", "", content, flags=re.MULTILINE)
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

    def _extract_technique_name(self, content: str) -> str:
        """从内容中提取技法名称"""
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

        return ""

    def _extract_keywords(self, content: str) -> List[str]:
        """从内容中提取关键词"""
        keywords = []

        bold_matches = re.findall(r"\*\*([^*]+)\*\*", content)
        keywords.extend(bold_matches)

        table_matches = re.findall(r"\| \*\*([^*]+)\*\* \|", content)
        keywords.extend(table_matches)

        keywords = list(set(k.strip() for k in keywords if len(k.strip()) > 1))
        return keywords[:10]

    def _determine_applicable_scenarios(
        self, content: str, dimension: str
    ) -> List[str]:
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

        if "战斗" in content or "代价" in content:
            scenarios.append("战斗场景")
        if "伏笔" in content or "悬念" in content:
            scenarios.append("伏笔埋设")
        if "人物" in content and ("矛盾" in content or "成长" in content):
            scenarios.append("人物成长")
        if "氛围" in content or "意境" in content:
            scenarios.append("氛围渲染")

        return list(set(scenarios))

    def _get_id(self, name: str, type_prefix: str) -> str:
        """生成ID"""
        for cn, pinyin in self.PINYIN_MAP.items():
            if cn in name:
                return f"{type_prefix}_{pinyin}"

        clean_name = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "_", name)
        return f"{type_prefix}_{clean_name}"

    def _add_units(self, collection, units: List[KnowledgeUnit]):
        """添加知识单元到集合"""
        if not units:
            return

        for unit in units:
            doc = f"{unit.name}\n\n{unit.content}"

            collection.upsert(
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

            self.stats["total"] += 1
            self.stats["by_type"][unit.type] = (
                self.stats["by_type"].get(unit.type, 0) + 1
            )

    def _print_stats(self, title: str):
        """打印统计"""
        print("\n" + "=" * 60)
        print(f"{title}向量化完成")
        print("=" * 60)
        print(f"总知识单元: {self.stats['total']}")
        print("\n按类型分布:")
        for type_name, count in sorted(self.stats["by_type"].items()):
            print(f"  {type_name}: {count}条")
