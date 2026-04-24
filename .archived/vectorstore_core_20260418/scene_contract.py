# -*- coding: utf-8 -*-
"""
场景契约系统 - 数据结构与存储管理

功能：
1. 定义场景契约数据结构
2. 提供契约存储与加载接口
3. 管理契约生命周期

作者: Sisyphus
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from core.config_loader import get_project_root


class ConflictLevel(Enum):
    """冲突级别"""

    CRITICAL = "critical"  # 必须修复
    WARNING = "warning"  # 建议修复
    INFO = "info"  # 可选修复


@dataclass
class ConsistencyConflict:
    """一致性冲突"""

    rule_id: str
    level: str
    message: str
    scene_a: str
    scene_b: str
    field: str
    value_a: Any
    value_b: Any
    suggestion: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CharacterEntry:
    """角色条目"""

    id: str
    name: str
    gender: str = "unknown"
    age: str = "unknown"
    status: str = "unknown"
    pronoun: Optional[str] = None
    first_appearance: bool = False


@dataclass
class GroupEntry:
    """群体条目"""

    id: str
    description: str
    count: int
    status: str = "unknown"


@dataclass
class TimelineEvent:
    """时间线事件"""

    event: str
    time: str
    status: str  # completed, ongoing, pending


@dataclass
class ObjectEntry:
    """物体条目"""

    id: str
    name: str
    type: str
    quantity: int
    state: str
    location: str
    owner: Optional[str] = None
    description: str = ""


class SceneContract:
    """场景契约"""

    CONTRACT_VERSION = "1.0"

    def __init__(self, scene_id: str, chapter_id: str, scene_type: str = "unknown"):
        self.contract_version = self.CONTRACT_VERSION
        self.scene_id = scene_id
        self.chapter_id = chapter_id

        # 元数据
        self.metadata = {
            "scene_type": scene_type,
            "word_count_target": "unknown",
            "created_at": datetime.now().isoformat(),
            "created_by": "system",
            "last_modified": datetime.now().isoformat(),
            "status": "draft",
        }

        # 人物清单
        self.character_manifest = {
            "count": {"male": 0, "female": 0, "child": 0, "total": 0},
            "named_characters": [],
            "groups": [],
        }

        # 时间线
        self.timeline = {
            "relative_time": {
                "start": "T+0",
                "end": "T+?",
                "reference_event": "章节开始",
            },
            "absolute_time": {"hour": None, "minute": None, "period": "unknown"},
            "causal_chain": [],
        }

        # 空间信息
        self.spatial = {
            "location": {
                "name": "unknown",
                "coordinates": {
                    "region": "unknown",
                    "sub_region": "unknown",
                    "specific": "unknown",
                },
            },
            "spatial_relationships": [],
            "movement_path": [],
        }

        # 物体状态
        self.object_states = {"objects": []}

        # 依赖关系
        self.dependencies = {
            "pre_scenes": [],
            "post_scenes": [],
            "blocking_events": [],
            "character_continuity": [],
        }

        # 校验和
        self.consistency_checksum = ""

    def add_named_character(
        self,
        name: str,
        gender: str = "unknown",
        age: str = "unknown",
        status: str = "unknown",
        pronoun: Optional[str] = None,
        first_appearance: bool = False,
    ) -> str:
        """添加命名角色"""
        char_id = f"char_{name}"

        char_entry = {
            "id": char_id,
            "name": name,
            "gender": gender,
            "age": age,
            "status": status,
            "first_appearance": first_appearance,
        }

        if pronoun:
            char_entry["pronoun"] = pronoun

        self.character_manifest["named_characters"].append(char_entry)

        # 更新计数
        if gender == "male":
            self.character_manifest["count"]["male"] += 1
        elif gender == "female":
            self.character_manifest["count"]["female"] += 1

        if age == "child":
            self.character_manifest["count"]["child"] += 1

        self.character_manifest["count"]["total"] += 1

        return char_id

    def add_group(self, description: str, count: int, status: str = "unknown") -> str:
        """添加群体"""
        group_id = f"group_{len(self.character_manifest['groups']) + 1}"

        self.character_manifest["groups"].append(
            {
                "id": group_id,
                "description": description,
                "count": count,
                "status": status,
            }
        )

        return group_id

    def add_timeline_event(self, event: str, time: str, status: str = "pending"):
        """添加时间线事件"""
        self.timeline["causal_chain"].append(
            {"event": event, "time": time, "status": status}
        )

    def add_object(
        self,
        name: str,
        obj_type: str,
        quantity: int,
        state: str,
        location: str,
        owner: Optional[str] = None,
        description: str = "",
    ) -> str:
        """添加物体"""
        obj_id = f"obj_{name}"

        obj_entry = {
            "id": obj_id,
            "name": name,
            "type": obj_type,
            "quantity": quantity,
            "state": state,
            "location": location,
            "description": description,
        }

        if owner:
            obj_entry["owner"] = owner

        self.object_states["objects"].append(obj_entry)

        return obj_id

    def add_dependency(
        self,
        pre_scene: Optional[str] = None,
        post_scene: Optional[str] = None,
        blocking_event: Optional[Dict] = None,
    ):
        """添加依赖关系"""
        if pre_scene:
            self.dependencies["pre_scenes"].append(pre_scene)

        if post_scene:
            self.dependencies["post_scenes"].append(post_scene)

        if blocking_event:
            self.dependencies["blocking_events"].append(blocking_event)

    def update_status(self, status: str):
        """更新状态"""
        self.metadata["status"] = status
        self.metadata["last_modified"] = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "contract_version": self.contract_version,
            "scene_id": self.scene_id,
            "chapter_id": self.chapter_id,
            "metadata": self.metadata,
            "character_manifest": self.character_manifest,
            "timeline": self.timeline,
            "spatial": self.spatial,
            "object_states": self.object_states,
            "dependencies": self.dependencies,
            "consistency_checksum": self._compute_checksum(),
        }

    def _compute_checksum(self) -> str:
        """计算校验和"""
        content = json.dumps(self.to_dict(), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @classmethod
    def from_dict(cls, data: Dict) -> "SceneContract":
        """从字典创建契约"""
        contract = cls(
            scene_id=data["scene_id"],
            chapter_id=data["chapter_id"],
            scene_type=data.get("metadata", {}).get("scene_type", "unknown"),
        )

        contract.metadata = data.get("metadata", contract.metadata)
        contract.character_manifest = data.get(
            "character_manifest", contract.character_manifest
        )
        contract.timeline = data.get("timeline", contract.timeline)
        contract.spatial = data.get("spatial", contract.spatial)
        contract.object_states = data.get("object_states", contract.object_states)
        contract.dependencies = data.get("dependencies", contract.dependencies)
        contract.consistency_checksum = data.get("consistency_checksum", "")

        return contract


class SceneContractStore:
    """场景契约存储管理器"""

    def __init__(self, chapter_id: str, store_dir: Optional[Path] = None):
        self.chapter_id = chapter_id

        if store_dir:
            self.store_dir = store_dir
        else:
            # 使用配置加载器获取项目根目录
            project_root = get_project_root()
            self.store_dir = project_root / ".cache" / "scene_contracts" / chapter_id

        self.store_dir.mkdir(parents=True, exist_ok=True)

    def _get_contract_path(self, scene_id: str) -> Path:
        """获取契约文件路径"""
        return self.store_dir / f"{scene_id}_contract.json"

    def save_contract(self, contract: SceneContract) -> Path:
        """保存场景契约"""
        contract.metadata["last_modified"] = datetime.now().isoformat()
        contract.consistency_checksum = contract._compute_checksum()

        contract_path = self._get_contract_path(contract.scene_id)

        with open(contract_path, "w", encoding="utf-8") as f:
            json.dump(contract.to_dict(), f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_contract_index(contract)

        return contract_path

    def load_contract(self, scene_id: str) -> Optional[SceneContract]:
        """加载场景契约"""
        contract_path = self._get_contract_path(scene_id)

        if not contract_path.exists():
            return None

        with open(contract_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return SceneContract.from_dict(data)

    def load_all_contracts(self) -> List[SceneContract]:
        """加载所有场景契约"""
        contracts = []

        for contract_file in self.store_dir.glob("*_contract.json"):
            with open(contract_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            contracts.append(SceneContract.from_dict(data))

        return contracts

    def delete_contract(self, scene_id: str) -> bool:
        """删除场景契约"""
        contract_path = self._get_contract_path(scene_id)

        if contract_path.exists():
            contract_path.unlink()
            return True

        return False

    def _update_contract_index(self, contract: SceneContract):
        """更新契约索引"""
        index_file = self.store_dir / "contract_index.json"

        index = {}
        if index_file.exists():
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

        index[contract.scene_id] = {
            "status": contract.metadata["status"],
            "last_modified": contract.metadata["last_modified"],
            "scene_type": contract.metadata["scene_type"],
            "pre_scenes": contract.dependencies.get("pre_scenes", []),
            "post_scenes": contract.dependencies.get("post_scenes", []),
        }

        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def get_contract_index(self) -> Dict:
        """获取契约索引"""
        index_file = self.store_dir / "contract_index.json"

        if not index_file.exists():
            return {}

        with open(index_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_dependency_graph(self) -> Dict:
        """获取场景依赖图"""
        contracts = self.load_all_contracts()

        graph = {"nodes": [], "edges": []}

        for contract in contracts:
            graph["nodes"].append(
                {
                    "id": contract.scene_id,
                    "type": contract.metadata["scene_type"],
                    "status": contract.metadata["status"],
                }
            )

            for pre_scene in contract.dependencies.get("pre_scenes", []):
                graph["edges"].append(
                    {"from": pre_scene, "to": contract.scene_id, "type": "dependency"}
                )

        return graph

    def get_scene_order(self) -> List[str]:
        """获取场景执行顺序（拓扑排序）"""
        contracts = self.load_all_contracts()

        # 构建依赖图
        in_degree = {}
        graph = {}

        for contract in contracts:
            scene_id = contract.scene_id
            in_degree[scene_id] = 0
            graph[scene_id] = []

        for contract in contracts:
            scene_id = contract.scene_id
            for pre_scene in contract.dependencies.get("pre_scenes", []):
                if pre_scene in graph:
                    graph[pre_scene].append(scene_id)
                    in_degree[scene_id] += 1

        # 拓扑排序
        queue = [s for s in in_degree if in_degree[s] == 0]
        result = []

        while queue:
            scene = queue.pop(0)
            result.append(scene)

            for next_scene in graph[scene]:
                in_degree[next_scene] -= 1
                if in_degree[next_scene] == 0:
                    queue.append(next_scene)

        return result

    def get_contract_snapshot(self, scene_ids: List[str]) -> Dict[str, SceneContract]:
        """获取多个场景的契约快照"""
        snapshot = {}

        for scene_id in scene_ids:
            contract = self.load_contract(scene_id)
            if contract:
                snapshot[scene_id] = contract

        return snapshot

    def has_contract(self, scene_id: str) -> bool:
        """检查契约是否存在"""
        return self._get_contract_path(scene_id).exists()

    def get_contract_count(self) -> int:
        """获取契约数量"""
        return len(list(self.store_dir.glob("*_contract.json")))


def create_contract_from_outline(scene_outline: Dict, chapter_id: str) -> SceneContract:
    """
    从场景大纲创建契约

    Args:
        scene_outline: 场景大纲数据
        chapter_id: 章节ID

    Returns:
        场景契约
    """
    contract = SceneContract(
        scene_id=scene_outline.get("scene_id", "scene_001"),
        chapter_id=chapter_id,
        scene_type=scene_outline.get("scene_type", "unknown"),
    )

    # 提取人物信息
    characters = scene_outline.get("characters", [])
    for char in characters:
        contract.add_named_character(
            name=char.get("name", "unknown"),
            gender=char.get("gender", "unknown"),
            age=char.get("age", "unknown"),
            status=char.get("status", "unknown"),
            pronoun=char.get("pronoun"),
            first_appearance=char.get("first_appearance", False),
        )

    # 提取群体信息
    groups = scene_outline.get("groups", [])
    for group in groups:
        contract.add_group(
            description=group.get("description", "unknown"),
            count=group.get("count", 0),
            status=group.get("status", "unknown"),
        )

    # 提取时间线
    events = scene_outline.get("events", [])
    for event in events:
        contract.add_timeline_event(
            event=event.get("event", "unknown"),
            time=event.get("time", "T+0"),
            status=event.get("status", "pending"),
        )

    # 提取空间信息
    location = scene_outline.get("location", {})
    if location:
        contract.spatial["location"] = location

    movement_path = scene_outline.get("movement_path", [])
    if movement_path:
        contract.spatial["movement_path"] = movement_path

    # 提取物体信息
    objects = scene_outline.get("objects", [])
    for obj in objects:
        contract.add_object(
            name=obj.get("name", "unknown"),
            obj_type=obj.get("type", "unknown"),
            quantity=obj.get("quantity", 1),
            state=obj.get("state", "unknown"),
            location=obj.get("location", "unknown"),
            owner=obj.get("owner"),
            description=obj.get("description", ""),
        )

    # 提取依赖关系
    dependencies = scene_outline.get("dependencies", {})
    for pre_scene in dependencies.get("pre_scenes", []):
        contract.add_dependency(pre_scene=pre_scene)

    for post_scene in dependencies.get("post_scenes", []):
        contract.add_dependency(post_scene=post_scene)

    for blocking_event in dependencies.get("blocking_events", []):
        contract.add_dependency(blocking_event=blocking_event)

    return contract


# 导出
__all__ = [
    "ConflictLevel",
    "ConsistencyConflict",
    "SceneContract",
    "SceneContractStore",
    "create_contract_from_outline",
]
