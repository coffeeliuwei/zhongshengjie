#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件更新器
==========

处理设定文件的更新和向量数据库同步。

核心功能：
- Markdown文件更新（追踪系统文件）
- JSON配置文件更新
- 向量数据库同步
- 变更日志记录

参考：统一提炼引擎重构方案.md 第9.8节
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class UpdateResult:
    """更新结果"""

    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    backup_created: bool = False
    lines_added: int = 0


class FileUpdater:
    """文件更新器"""

    # 追踪系统文件的意图映射（意图名 -> 文件名）
    TRACKING_INTENT_MAP = {
        "add_hook": "hook_ledger.md",
        "advance_hook": "hook_ledger.md",
        "resolve_hook": "hook_ledger.md",
        "add_resource": "resource_ledger.md",
        "consume_resource": "resource_ledger.md",
        "add_injury": "resource_ledger.md",
        "add_character_info": "information_boundary.md",
        "share_info": "information_boundary.md",
        "add_payoff": "payoff_tracking.md",
        "deliver_payoff": "payoff_tracking.md",
    }

    def __init__(self, project_root: Optional[str] = None):
        """
        初始化文件更新器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.logs_dir = self.project_root / "logs" / "conversation_updates"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "tools", "设定"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent

        return Path.cwd()

    def update_markdown(
        self, file_path: str, intent: str, data: Dict[str, Any]
    ) -> bool:
        """
        更新Markdown文件

        Args:
            file_path: 文件路径
            intent: 意图类型
            data: 数据内容

        Returns:
            是否成功更新
        """
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            # 创建新文件
            return self._create_new_file(path, intent, data)

        # 读取现有内容
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return False

        # 创建备份
        backup_path = self._create_backup(path)
        backup_created = backup_path is not None

        # 根据文件类型选择更新方法
        filename = path.name
        updated_content = None

        # 检查是否是追踪系统文件
        if intent in self.TRACKING_INTENT_MAP:
            # 追踪系统文件
            updated_content = self._handle_tracking_file(path, content, intent, data)
        elif filename == "人物谱.md":
            if intent in ("add_character_ability", "add_character_relation"):
                # 直接文件修改，不需要返回内容
                self._update_character_profile(path, content, data, intent)
                updated_content = path.read_text(encoding="utf-8")
            else:
                updated_content = self._update_character_profile(
                    path, content, data, intent
                )
        elif filename == "十大势力.md":
            updated_content = self._update_faction_profile(content, data, intent)
        elif filename == "力量体系.md":
            self._update_power_system(path, data)
            updated_content = path.read_text(encoding="utf-8")
        elif filename == "时间线.md":
            updated_content = self._update_timeline(content, data, intent)
        else:
            # 默认追加到文件末尾
            updated_content = self._append_to_file(content, data, intent)

        if updated_content is None:
            return False

        # 写入更新后的内容
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(updated_content)
            return True
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")
            return False

    def update_json(self, file_path: str, intent: str, data: Dict[str, Any]) -> bool:
        """
        更新JSON文件

        Args:
            file_path: 文件路径
            intent: 意图类型
            data: 数据内容

        Returns:
            是否成功更新
        """
        path = Path(file_path)

        # 读取现有内容
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}
        except Exception as e:
            print(f"Error reading JSON file {file_path}: {e}")
            return False

        # 更新数据
        updated_data = self._merge_json_data(existing_data, data, intent)

        # 写入
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error writing JSON file {file_path}: {e}")
            return False

    def sync_to_vectorstore(self, collection: str, data: Dict[str, Any]) -> bool:
        """
        同步到向量数据库

        Args:
            collection: Collection名称
            data: 数据内容

        Returns:
            是否成功同步
        """
        try:
            # 导入向量数据库客户端和嵌入模型
            import sys
            from pathlib import Path

            # 添加.vectorstore路径
            vectorstore_path = self.project_root / ".vectorstore"
            if str(vectorstore_path) not in sys.path:
                sys.path.insert(0, str(vectorstore_path))

            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct
            from FlagEmbedding import BGEM3FlagModel

            # 从配置获取连接信息
            from core.config_loader import get_qdrant_url, get_model_path

            client = QdrantClient(url=get_qdrant_url())

            # 检查collection是否存在
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection not in collection_names:
                print(f"[WARN] Collection {collection} 不存在，跳过同步")
                return False

            # 生成文本内容用于嵌入
            text_content = self._generate_embedding_text(collection, data)

            if not text_content:
                print(f"[WARN] 无法生成嵌入文本，跳过同步")
                return False

            # 加载嵌入模型（懒加载）
            model_path = get_model_path()
            if not model_path:
                print(f"[WARN] 模型路径未配置，跳过向量同步")
                # 仍然记录日志，只是不做实际同步
                self._log_vectorstore_update(collection, data)
                return True

            try:
                model = BGEM3FlagModel(model_path, use_fp16=True)

                # 生成嵌入向量
                embedding = model.encode(
                    [text_content], return_dense=True, return_sparse=False
                )
                dense_vecs = embedding.get("dense_vecs")

                if dense_vecs is not None and len(dense_vecs) > 0:
                    import numpy as np

                    dense_vector = np.array(dense_vecs[0]).tolist()

                    # 创建数据点
                    import uuid

                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector={"dense": dense_vector},
                        payload={
                            "content": text_content,
                            "source": "conversation_update",
                            "timestamp": datetime.now().isoformat(),
                            **data,
                        },
                    )

                    # 上传
                    client.upsert(collection_name=collection, points=[point])
                    print(f"[OK] 已同步到 {collection}")
                else:
                    print(f"[WARN] 嵌入生成返回空结果")

            except Exception as embed_error:
                print(f"[WARN] 嵌入生成失败: {embed_error}，记录日志但不同步")

            # 记录日志
            self._log_vectorstore_update(collection, data)

            return True

        except ImportError as e:
            print(f"[WARN] 缺少依赖: {e}")
            self._log_vectorstore_update(collection, data)
            return False
        except Exception as e:
            print(f"[ERROR] 向量同步失败: {e}")
            self._log_vectorstore_update(collection, data)
            return False

    def _generate_embedding_text(self, collection: str, data: Dict[str, Any]) -> str:
        """
        根据Collection类型生成嵌入文本

        Args:
            collection: Collection名称
            data: 数据内容

        Returns:
            用于生成嵌入的文本
        """
        if collection == "novel_settings_v2":
            # 设定类数据
            name = data.get("name", "")
            type_ = data.get("type", "")
            description = data.get("description", "")
            return f"{type_}: {name}\n{description}"

        elif collection == "writing_techniques_v2":
            # 技法类数据
            name = data.get("name", data.get("技法名称", ""))
            dimension = data.get("dimension", data.get("维度", ""))
            content = data.get("content", data.get("内容", ""))
            return f"技法: {name}\n维度: {dimension}\n{content}"

        elif collection == "case_library_v2":
            # 案例类数据
            scene_type = data.get("scene_type", "")
            content = data.get("content", "")
            return f"场景: {scene_type}\n{content}"

        elif collection == "novel_plot_v1":
            # 总大纲 / 剧情变更 (I19)
            content = data.get("content", "")
            type_ = data.get("type", "plot_change")
            return f"剧情变更 [{type_}]:\n{content}"

        elif collection == "chapter_outlines":
            # 章节大纲 (I18)
            chapter_num = data.get("chapter_num", "")
            chapter_title = data.get("chapter_title", "")
            content = data.get("content", "")
            source = data.get("source_file", "")
            return f"第{chapter_num}章 {chapter_title}\n来源: {source}\n{content}"

        else:
            # 默认格式
            return json.dumps(data, ensure_ascii=False)

    def _create_new_file(self, path: Path, intent: str, data: Dict[str, Any]) -> bool:
        """创建新文件"""
        try:
            # 创建目录
            path.parent.mkdir(parents=True, exist_ok=True)

            # 生成初始内容
            content = self._generate_initial_content(path.name, intent, data)

            # 写入
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"Error creating file {path}: {e}")
            return False

    def _create_backup(self, path: Path) -> Optional[Path]:
        """创建文件备份"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_suffix(f".{timestamp}.bak")
            with open(path, "r", encoding="utf-8") as src:
                content = src.read()
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(content)
            return backup_path
        except Exception:
            return None

    def _generate_initial_content(
        self, filename: str, intent: str, data: Dict[str, Any]
    ) -> str:
        """生成初始文件内容"""
        if filename.endswith(".md"):
            return self._generate_markdown_header(
                filename
            ) + self._format_data_as_markdown(data, intent)
        elif filename.endswith(".json"):
            return json.dumps(data, ensure_ascii=False, indent=2)
        return ""

    def _generate_markdown_header(self, filename: str) -> str:
        """生成Markdown文件头部"""
        title = filename.replace(".md", "").replace("_", " ")
        return f"""# {title}

> 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

"""

    def _format_data_as_markdown(self, data: Dict[str, Any], intent: str) -> str:
        """将数据格式化为Markdown"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [f"\n## [{timestamp}] {intent}\n"]

        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            lines.append(f"- **{key}**: {value}")

        lines.append("\n---\n")
        return "\n".join(lines)

    # ===== 追踪系统文件处理 =====

    def _handle_tracking_file(
        self, path: Path, content: str, intent: str, data: Dict[str, Any]
    ) -> Optional[str]:
        """
        处理追踪系统文件

        Args:
            path: 文件路径（Path对象）
            content: 文件现有内容
            intent: 意图类型
            data: 数据内容

        Returns:
            更新后的内容，或None表示失败
        """
        # 直接文件修改的意图（修改已有条目）
        direct_file_intents = {
            "advance_hook": self._update_hook_status,
            "resolve_hook": self._update_hook_status,
            "deliver_payoff": self._update_payoff_status,
        }

        # 内容追加的意图（添加新条目）
        content_handlers = {
            "add_hook": self._format_hook_entry,
            "add_resource": self._format_resource_entry,
            "consume_resource": self._format_resource_entry,
            "add_injury": self._format_injury_entry,
            "add_character_info": self._format_info_entry,
            "share_info": self._format_share_entry,
            "add_payoff": self._format_payoff_entry,
        }

        # 处理直接文件修改
        if intent in direct_file_intents:
            handler = direct_file_intents[intent]
            handler(path, data)
            # 重新读取更新后的内容
            return path.read_text(encoding="utf-8")

        # 处理内容追加
        handler = content_handlers.get(intent)
        if handler:
            return handler(content, data, intent)

        return None

    # ===== 追踪系统文件的格式化方法 =====

    def _format_hook_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化伏笔条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hook_content = data.get("content", "")
        entry = f"""
### 🪝 伏笔 [{timestamp}]

**内容**: {hook_content}
**状态**: 🌱 已埋下
**章节**: 待填写
**回收章节**: 待填写

---
"""
        return content + entry

    def _update_hook_status(self, file_path: Path, data: Dict[str, Any]) -> None:
        """更新伏笔状态（触发/解决）

        Args:
            file_path: 伏笔台账文件路径
            data: {"hook_id": str, "new_status": str, "chapter": str}
        """
        hook_id = data.get("hook_id", "")
        new_status = data.get("new_status", "")
        chapter = data.get("chapter", "")
        if not hook_id or not new_status:
            return

        content = file_path.read_text(encoding="utf-8")

        # 找到伏笔块，替换其状态行
        pattern = rf"(## {re.escape(hook_id)}.*?)\*\*状态\*\*: [^\n]+"
        replacement = rf"\1**状态**: {new_status}"
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        if new_content == content:
            return  # 未找到目标，不写入

        if chapter:
            # 同时更新触发章节（若有"**触发章节**"字段）
            pattern2 = rf"(## {re.escape(hook_id)}.*?)\*\*触发章节\*\*: [^\n]+"
            new_content = re.sub(
                pattern2, rf"\1**触发章节**: {chapter}", new_content, flags=re.DOTALL
            )

        file_path.write_text(new_content, encoding="utf-8")

    def _format_resource_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化资源条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        character = data.get("character", "")
        resource = data.get("resource", "")
        action = data.get("action", "acquired")
        emoji = "📥" if action == "acquired" else "📤"

        entry = f"""
### {emoji} 资源变更 [{timestamp}]

**角色**: {character}
**资源**: {resource}
**操作**: {action}

---
"""
        return content + entry

    def _format_injury_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化伤害条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        character = data.get("character", "")
        injury = data.get("injury", "")

        entry = f"""
### 🩹 伤害记录 [{timestamp}]

**角色**: {character}
**伤害**: {injury}

---
"""
        return content + entry

    def _format_info_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化信息条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        character = data.get("character", "")
        info = data.get("info", "")

        entry = f"""
### 📝 信息获取 [{timestamp}]

**角色**: {character}
**信息**: {info}

---
"""
        return content + entry

    def _format_share_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化信息分享条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        char1 = data.get("character1", "")
        char2 = data.get("character2", "")
        info = data.get("info", "")

        entry = f"""
### 🔄 信息传递 [{timestamp}]

**发送者**: {char1}
**接收者**: {char2}
**信息**: {info}

---
"""
        return content + entry

    def _format_payoff_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """格式化承诺条目"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        character = data.get("character", "")
        promise = data.get("promise", "")

        entry = f"""
### ⚡ 承诺 [{timestamp}]

**角色**: {character}
**承诺**: {promise}
**状态**: ⏳ 待兑现
**兑现章节**: 待填写

---
"""
        return content + entry

    def _update_payoff_status(self, file_path: Path, data: Dict[str, Any]) -> None:
        """更新承诺状态（已兑现）

        Args:
            file_path: 承诺台账文件路径
            data: {"payoff_id": str, "new_status": str, "chapter": str}
        """
        payoff_id = data.get("payoff_id", "")
        new_status = data.get("new_status", "")
        chapter = data.get("chapter", "")
        if not payoff_id or not new_status:
            return

        content = file_path.read_text(encoding="utf-8")

        pattern = rf"(## {re.escape(payoff_id)}.*?)\*\*状态\*\*: [^\n]+"
        replacement = rf"\1**状态**: {new_status}"
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        if new_content == content:
            return  # 未找到目标，不写入

        if chapter:
            pattern2 = rf"(## {re.escape(payoff_id)}.*?)\*\*兑现章节\*\*: [^\n]+"
            new_content = re.sub(
                pattern2,
                rf"\1**兑现章节**: {chapter}",
                new_content,
                flags=re.DOTALL,
            )

        file_path.write_text(new_content, encoding="utf-8")

    # ===== 设定文件更新方法 =====

    def _update_character_profile(
        self, path: Path, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """更新人物谱

        Args:
            path: 文件路径
            content: 文件内容
            data: 数据
            intent: 意图类型

        Returns:
            更新后的内容（对于直接文件修改的意图，返回None，实际文件已修改）
        """
        if intent == "add_character":
            return self._append_new_character(content, data)
        elif intent == "add_character_ability":
            self._add_character_ability(path, data)
            return None  # 文件已直接修改
        elif intent == "add_character_relation":
            self._add_character_relation(path, data)
            return None  # 文件已直接修改
        return content

    def _append_new_character(self, content: str, data: Dict[str, Any]) -> str:
        """追加新角色"""
        name = data.get("name", "")
        entry = f"""
### {name}

**简介**: 待填写
**势力**: 待填写
**能力**: 待填写
**状态**: 活跃

---
"""
        return content + entry

    def _add_character_ability(self, file_path: Path, data: Dict[str, Any]) -> None:
        """在角色条目的"能力"小节追加新能力

        Args:
            file_path: 人物档案文件路径
            data: {"character_name": str, "ability": str}
        """
        character_name = data.get("character_name", "")
        ability = data.get("ability", "")
        if not character_name or not ability:
            return

        content = file_path.read_text(encoding="utf-8")
        ability_line = f"- {ability}"

        # 找到角色块中的"### 能力"小节，在其后追加
        pattern = rf"(## {re.escape(character_name)}.*?### 能力\n)(.*?)(\n###|\n##|\Z)"

        def replacer(m):
            abilities = m.group(2).rstrip("\n")
            return f"{m.group(1)}{abilities}\n{ability_line}\n{m.group(3)}"

        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        if new_content == content:
            # 角色不存在或无"能力"小节，直接追加到文件末尾
            new_content = (
                content.rstrip()
                + f"\n\n## {character_name}\n### 能力\n{ability_line}\n"
            )

        file_path.write_text(new_content, encoding="utf-8")

    def _add_character_relation(self, file_path: Path, data: Dict[str, Any]) -> None:
        """在角色条目的"关系"小节追加新关系

        Args:
            file_path: 人物档案文件路径
            data: {"character_name": str, "relation": str}
        """
        character_name = data.get("character_name", "")
        relation = data.get("relation", "")
        if not character_name or not relation:
            return

        content = file_path.read_text(encoding="utf-8")
        relation_line = f"- {relation}"

        pattern = rf"(## {re.escape(character_name)}.*?### 关系\n)(.*?)(\n###|\n##|\Z)"

        def replacer(m):
            relations = m.group(2).rstrip("\n")
            return f"{m.group(1)}{relations}\n{relation_line}\n{m.group(3)}"

        new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        if new_content == content:
            new_content = (
                content.rstrip()
                + f"\n\n## {character_name}\n### 关系\n{relation_line}\n"
            )

        file_path.write_text(new_content, encoding="utf-8")

    def _update_faction_profile(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str:
        """更新势力档案"""
        if intent == "add_faction":
            name = data.get("name", "")
            entry = f"""
### {name}

**简介**: 待填写
**成员**: 待填写
**力量类型**: 待填写

---
"""
            return content + entry
        return content

    def _update_power_system(self, file_path: Path, data: Dict[str, Any]) -> None:
        """更新力量体系条目

        Args:
            file_path: 力量体系文件路径
            data: {"system_name": str, "field": str, "value": str}
                  field 为子节名（如"境界列表"/"代价"），value 为追加内容
        """
        system_name = data.get("system_name", "")
        field = data.get("field", "")
        value = data.get("value", "")
        if not system_name or not value:
            return

        content = file_path.read_text(encoding="utf-8")
        value_line = f"- {value}"

        if field:
            # 在指定 field 小节追加
            pattern = rf"(## {re.escape(system_name)}.*?### {re.escape(field)}\n)(.*?)(\n###|\n##|\Z)"

            def replacer(m):
                items = m.group(2).rstrip("\n")
                return f"{m.group(1)}{items}\n{value_line}\n{m.group(3)}"

            new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
        else:
            new_content = content

        if new_content == content:
            # 体系不存在或字段不存在，追加新体系块
            new_section = f"\n## {system_name}\n"
            if field:
                new_section += f"### {field}\n{value_line}\n"
            else:
                new_section += f"{value_line}\n"
            new_content = content.rstrip() + new_section

        file_path.write_text(new_content, encoding="utf-8")

    def _update_timeline(self, content: str, data: Dict[str, Any], intent: str) -> str:
        """更新时间线"""
        if intent == "add_era":
            name = data.get("name", "")
            entry = f"""
## {name}

**时代简介**: 待填写

### 重大事件
- 待填写

---
"""
            return content + entry
        return content

    def _append_to_file(self, content: str, data: Dict[str, Any], intent: str) -> str:
        """默认追加到文件"""
        return content + self._format_data_as_markdown(data, intent)

    def _merge_json_data(
        self, existing: Dict[str, Any], new_data: Dict[str, Any], intent: str
    ) -> Dict[str, Any]:
        """合并JSON数据"""
        result = existing.copy()

        # 根据意图类型决定合并方式
        if "entries" not in result:
            result["entries"] = []

        # 添加新条目
        entry = {
            **new_data,
            "timestamp": datetime.now().isoformat(),
            "intent": intent,
        }
        result["entries"].append(entry)

        return result

    def _log_vectorstore_update(self, collection: str, data: Dict[str, Any]):
        """记录向量数据库更新日志"""
        log_file = (
            self.logs_dir / f"vectorstore_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )
        entry = {
            "timestamp": datetime.now().isoformat(),
            "collection": collection,
            "data": data,
        }
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass


# 测试代码
if __name__ == "__main__":
    updater = FileUpdater()

    # 测试更新Markdown
    test_file = "test_tracking.md"
    test_data = {
        "character": "血牙",
        "resource": "三颗灵石",
        "action": "acquired",
    }

    print("=" * 60)
    print("文件更新器测试")
    print("=" * 60)

    # 注意：这只是演示，实际测试需要真实文件
    print("\n测试数据:")
    print(json.dumps(test_data, ensure_ascii=False, indent=2))
