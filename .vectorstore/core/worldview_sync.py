#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观同步工具 - 检测大纲变更并同步世界观配置
============================================

功能：
- 检测大纲文件修改时间
- 与世界观配置对比，识别变更
- 增量更新世界观配置（智能合并）
- 备份旧配置
- 变更追踪与回滚

使用：
python worldview_sync.py --status    # 查看同步状态
python worldview_sync.py --sync      # 执行同步
python worldview_sync.py --validate  # 验证配置
python worldview_sync.py --diff      # 查看变更差异
python worldview_sync.py --rollback  # 回滚到上一版本
"""

import os
import sys
import json
import hashlib
import difflib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from copy import deepcopy

# 添加core目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from worldview_generator import WorldviewGenerator


class ChangeTracker:
    """变更追踪器 - 记录和分析世界观变更"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "changes"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.changes_file = self.cache_dir / "change_history.json"
        self._load_history()

    def _load_history(self):
        """加载变更历史"""
        if self.changes_file.exists():
            with open(self.changes_file, "r", encoding="utf-8") as f:
                self.history = json.load(f)
        else:
            self.history = {"changes": [], "current_version": 0}

    def _save_history(self):
        """保存变更历史"""
        with open(self.changes_file, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def record_change(
        self,
        world_name: str,
        change_type: str,
        changes: Dict[str, Any],
        backup_path: str = None,
    ) -> int:
        """记录变更

        Args:
            world_name: 世界观名称
            change_type: 变更类型 (full_sync/incremental/manual)
            changes: 变更详情
            backup_path: 备份文件路径

        Returns:
            新版本号
        """
        self.history["current_version"] += 1
        change_record = {
            "version": self.history["current_version"],
            "world_name": world_name,
            "change_type": change_type,
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "backup_path": backup_path,
        }
        self.history["changes"].append(change_record)
        self._save_history()
        return self.history["current_version"]

    def get_last_change(self, world_name: str = None) -> Optional[Dict]:
        """获取最近一次变更"""
        if not self.history["changes"]:
            return None

        if world_name:
            for change in reversed(self.history["changes"]):
                if change["world_name"] == world_name:
                    return change
            return None

        return self.history["changes"][-1]

    def get_rollback_info(self, version: int = None) -> Optional[Dict]:
        """获取回滚信息"""
        if version:
            for change in self.history["changes"]:
                if change["version"] == version:
                    return change
            return None

        # 返回上一个版本
        if len(self.history["changes"]) >= 2:
            return self.history["changes"][-2]
        return None


class IncrementalSync:
    """增量同步处理器 - 智能检测和合并变更"""

    # 关键字段定义 - 这些字段的变更会触发增量更新
    POWER_SYSTEM_KEYS = {"source", "cultivation", "combat_style", "costs", "realms"}
    FACTION_KEYS = {"structure", "political", "economy", "culture", "architecture"}
    CHARACTER_KEYS = {"faction", "power", "subtype", "abilities", "invasion_status"}
    ERA_KEYS = {"mood", "color", "symbols"}

    @classmethod
    def compute_hash(cls, data: Dict) -> str:
        """计算数据哈希"""
        return hashlib.md5(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16]

    @classmethod
    def _detect_changes_generic(
        cls, old: Dict, new: Dict, key_fields: Set[str] = None, use_hash: bool = True
    ) -> Dict[str, Any]:
        """通用变更检测模板方法

        Args:
            old: 旧配置字典
            new: 新配置字典
            key_fields: 需要检测的关键字段集合（可选）
            use_hash: 是否使用哈希比较（简单数据可不使用）

        Returns:
            变更字典 {"added": {}, "removed": {}, "modified": {}}
        """
        changes = {"added": {}, "removed": {}, "modified": {}}

        old_keys = set(old.keys())
        new_keys = set(new.keys())

        # 新增的元素
        for key in new_keys - old_keys:
            changes["added"][key] = new[key]

        # 删除的元素
        for key in old_keys - new_keys:
            changes["removed"][key] = old[key]

        # 修改的元素
        for key in old_keys & new_keys:
            if use_hash:
                if cls.compute_hash(old[key]) != cls.compute_hash(new[key]):
                    if key_fields:
                        # 检测具体修改的字段
                        field_changes = {}
                        for field in key_fields:
                            old_val = old[key].get(field)
                            new_val = new[key].get(field)
                            if old_val != new_val:
                                field_changes[field] = {"old": old_val, "new": new_val}
                        if field_changes:
                            changes["modified"][key] = field_changes
                    else:
                        changes["modified"][key] = {"old": old[key], "new": new[key]}
            else:
                # 简单比较（用于 era 等简单数据）
                if old[key] != new[key]:
                    changes["modified"][key] = {"old": old[key], "new": new[key]}

        return changes

    @classmethod
    def detect_power_system_changes(cls, old: Dict, new: Dict) -> Dict[str, Any]:
        """检测力量体系变更"""
        return cls._detect_changes_generic(old, new, cls.POWER_SYSTEM_KEYS)

    @classmethod
    def detect_faction_changes(cls, old: Dict, new: Dict) -> Dict[str, Any]:
        """检测势力变更"""
        return cls._detect_changes_generic(old, new, cls.FACTION_KEYS)

    @classmethod
    def detect_character_changes(cls, old: Dict, new: Dict) -> Dict[str, Any]:
        """检测角色变更"""
        return cls._detect_changes_generic(old, new, cls.CHARACTER_KEYS)

    @classmethod
    def detect_era_changes(cls, old: Dict, new: Dict) -> Dict[str, Any]:
        """检测时代变更"""
        return cls._detect_changes_generic(old, new, use_hash=False)

    @classmethod
    def compute_all_changes(cls, old_config: Dict, new_config: Dict) -> Dict[str, Any]:
        """计算所有变更"""
        return {
            "power_systems": cls.detect_power_system_changes(
                old_config.get("power_systems", {}), new_config.get("power_systems", {})
            ),
            "factions": cls.detect_faction_changes(
                old_config.get("factions", {}), new_config.get("factions", {})
            ),
            "key_characters": cls.detect_character_changes(
                old_config.get("key_characters", {}),
                new_config.get("key_characters", {}),
            ),
            "eras": cls.detect_era_changes(
                old_config.get("eras", {}), new_config.get("eras", {})
            ),
            "timestamp": datetime.now().isoformat(),
        }

    @classmethod
    def has_meaningful_changes(cls, changes: Dict) -> bool:
        """判断是否有实质性变更"""
        for category in ["power_systems", "factions", "key_characters", "eras"]:
            cat_changes = changes.get(category, {})
            if (
                cat_changes.get("added")
                or cat_changes.get("removed")
                or cat_changes.get("modified")
            ):
                return True
        return False

    @classmethod
    def merge_configs(cls, old_config: Dict, new_config: Dict, changes: Dict) -> Dict:
        """智能合并配置 - 保留旧配置中未变更的自定义内容

        Args:
            old_config: 旧配置
            new_config: 新配置
            changes: 变更检测结果

        Returns:
            合并后的配置
        """
        merged = deepcopy(old_config)

        # 处理力量体系
        for key in changes["power_systems"]["added"]:
            merged["power_systems"][key] = new_config["power_systems"][key]

        for key in changes["power_systems"]["removed"]:
            del merged["power_systems"][key]

        for key, field_changes in changes["power_systems"]["modified"].items():
            for field, vals in field_changes.items():
                merged["power_systems"][key][field] = vals["new"]

        # 处理势力
        for key in changes["factions"]["added"]:
            merged["factions"][key] = new_config["factions"][key]

        for key in changes["factions"]["removed"]:
            del merged["factions"][key]

        for key, field_changes in changes["factions"]["modified"].items():
            for field, vals in field_changes.items():
                merged["factions"][key][field] = vals["new"]

        # 处理角色
        for key in changes["key_characters"]["added"]:
            merged["key_characters"][key] = new_config["key_characters"][key]

        for key in changes["key_characters"]["removed"]:
            del merged["key_characters"][key]

        for key, field_changes in changes["key_characters"]["modified"].items():
            for field, vals in field_changes.items():
                merged["key_characters"][key][field] = vals["new"]

        # 处理时代
        for key in changes["eras"]["added"]:
            merged["eras"][key] = new_config["eras"][key]

        for key in changes["eras"]["removed"]:
            del merged["eras"][key]

        for key, vals in changes["eras"]["modified"].items():
            merged["eras"][key] = vals["new"]

        # 更新描述
        merged["description"] = new_config.get(
            "description", merged.get("description", "")
        )

        return merged


class WorldviewSync:
    """世界观同步管理器"""

    def __init__(self, project_root: Path = None):
        """初始化

        Args:
            project_root: 项目根目录
        """
        if project_root is None:
            try:
                from config_loader import get_project_root

                project_root = get_project_root()
            except Exception:
                project_root = Path(__file__).parent.parent

        self.project_root = Path(project_root)
        self.cache_dir = self.project_root / ".cache" / "worldview_backup"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.generator = WorldviewGenerator(self.project_root)
        self.change_tracker = ChangeTracker(self.cache_dir)

    def get_outline_info(self) -> Dict[str, Any]:
        """获取大纲文件信息"""
        try:
            from config_loader import get_outline_path, get_current_world

            outline_path = get_outline_path()
            current_world = get_current_world()

            if not outline_path:
                return {"exists": False, "error": "未配置大纲路径"}

            outline_file = Path(outline_path)

            if not outline_file.exists():
                return {"exists": False, "error": f"大纲文件不存在: {outline_path}"}

            stat = outline_file.stat()

            # 计算文件hash
            with open(outline_file, "r", encoding="utf-8") as f:
                content = f.read()
            file_hash = hashlib.md5(content.encode()).hexdigest()[:16]

            return {
                "exists": True,
                "path": outline_path,
                "current_world": current_world,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size,
                "hash": file_hash,
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def get_worldview_info(self) -> Dict[str, Any]:
        """获取世界观配置信息"""
        try:
            from config_loader import get_current_world
            from world_config_loader import load_world_config, validate_world_config

            current_world = get_current_world()
            config_file = (
                self.project_root
                / ".vectorstore"
                / "core"
                / "world_configs"
                / f"{current_world}.json"
            )

            if not config_file.exists():
                return {"exists": False, "error": f"世界观配置不存在: {current_world}"}

            stat = config_file.stat()

            # 加载配置
            config = load_world_config(current_world)

            # 验证配置
            errors = validate_world_config(current_world)

            return {
                "exists": True,
                "world_name": current_world,
                "path": str(config_file),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "power_systems_count": len(config.get("power_systems", {})),
                "factions_count": len(config.get("factions", {})),
                "characters_count": len(config.get("key_characters", {})),
                "errors": errors,
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def check_sync_status(self) -> Dict[str, Any]:
        """检查同步状态

        Returns:
            同步状态信息
        """
        outline_info = self.get_outline_info()
        worldview_info = self.get_worldview_info()

        result = {
            "outline": outline_info,
            "worldview": worldview_info,
            "sync_needed": False,
            "reason": None,
        }

        if not outline_info.get("exists"):
            result["reason"] = "大纲文件不存在"
            return result

        if not worldview_info.get("exists"):
            result["sync_needed"] = True
            result["reason"] = "世界观配置不存在，需要生成"
            return result

        # 比较修改时间
        try:
            outline_time = datetime.fromisoformat(outline_info["modified_time"])
            worldview_time = datetime.fromisoformat(worldview_info["modified_time"])

            if outline_time > worldview_time:
                result["sync_needed"] = True
                result["reason"] = "大纲比世界观配置更新"
            else:
                result["reason"] = "世界观配置已是最新"
        except Exception:
            result["reason"] = "无法比较修改时间"

        # 检查验证错误
        if worldview_info.get("errors"):
            result["sync_needed"] = True
            result["reason"] = (
                f"世界观配置有{len(worldview_info['errors'])}个问题需要修复"
            )

        return result

    def backup_worldview(self, world_name: str) -> Optional[Path]:
        """备份世界观配置

        Args:
            world_name: 世界观名称

        Returns:
            备份文件路径
        """
        from world_config_loader import load_world_config

        config = load_world_config(world_name)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.cache_dir / f"{world_name}_{timestamp}.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return backup_file

    def sync(self, force: bool = False, incremental: bool = True) -> Dict[str, Any]:
        """同步世界观配置

        Args:
            force: 是否强制覆盖
            incremental: 是否使用增量同步（智能合并）

        Returns:
            同步结果
        """
        status = self.check_sync_status()

        result = {
            "success": False,
            "synced": False,
            "backup_path": None,
            "message": None,
            "changes": [],
            "sync_type": "none",
            "version": None,
        }

        if not status["sync_needed"] and not force:
            result["success"] = True
            result["message"] = "无需同步，世界观配置已是最新"
            return result

        outline_info = status["outline"]
        if not outline_info.get("exists"):
            result["message"] = f"无法同步: {outline_info.get('error')}"
            return result

        try:
            world_name = outline_info["current_world"]

            # 加载旧配置
            old_config = None
            if status["worldview"].get("exists"):
                from world_config_loader import load_world_config

                old_config = load_world_config(world_name)
                backup_path = self.backup_worldview(world_name)
                result["backup_path"] = str(backup_path)

            # 从大纲生成新配置
            gen_result = self.generator.generate_from_outline(
                outline_info["path"], world_name, save=False
            )
            new_config = gen_result["config"]

            # 决定同步策略
            if incremental and old_config:
                # 增量同步
                changes = IncrementalSync.compute_all_changes(old_config, new_config)

                if IncrementalSync.has_meaningful_changes(changes):
                    # 智能合并
                    merged_config = IncrementalSync.merge_configs(
                        old_config, new_config, changes
                    )

                    # 保存合并后的配置
                    file_path = self.generator.save_config(merged_config, world_name)

                    # 记录变更
                    version = self.change_tracker.record_change(
                        world_name, "incremental", changes, result.get("backup_path")
                    )

                    result["success"] = True
                    result["synced"] = True
                    result["sync_type"] = "incremental"
                    result["version"] = version
                    result["message"] = f"增量同步完成: {file_path}"
                    result["changes"] = self._format_changes(changes)
                    result["file_path"] = str(file_path)
                else:
                    result["success"] = True
                    result["message"] = "检测到变更但无实质性修改"
            else:
                # 全量同步
                file_path = self.generator.save_config(new_config, world_name)

                # 记录变更
                version = self.change_tracker.record_change(
                    world_name,
                    "full_sync",
                    {"reason": "full_sync", "backup": result.get("backup_path")},
                    result.get("backup_path"),
                )

                result["success"] = True
                result["synced"] = True
                result["sync_type"] = "full"
                result["version"] = version
                result["message"] = f"全量同步完成: {file_path}"
                result["changes"] = [
                    f"力量体系: {len(new_config['power_systems'])}个",
                    f"势力: {len(new_config['factions'])}个",
                    f"角色: {len(new_config['key_characters'])}个",
                ]
                result["file_path"] = str(file_path)

        except Exception as e:
            result["message"] = f"同步失败: {e}"

        return result

    def _format_changes(self, changes: Dict) -> List[str]:
        """格式化变更信息"""
        formatted = []

        for category in ["power_systems", "factions", "key_characters", "eras"]:
            cat_changes = changes.get(category, {})
            cat_name = {
                "power_systems": "力量体系",
                "factions": "势力",
                "key_characters": "角色",
                "eras": "时代",
            }.get(category, category)

            if cat_changes.get("added"):
                formatted.append(f"{cat_name}新增: {len(cat_changes['added'])}个")
            if cat_changes.get("removed"):
                formatted.append(f"{cat_name}删除: {len(cat_changes['removed'])}个")
            if cat_changes.get("modified"):
                formatted.append(f"{cat_name}修改: {len(cat_changes['modified'])}个")

        return formatted if formatted else ["无变更"]

    def diff(self) -> Dict[str, Any]:
        """查看大纲与世界观配置的差异

        Returns:
            差异详情
        """
        outline_info = self.get_outline_info()
        worldview_info = self.get_worldview_info()

        result = {
            "outline_exists": outline_info.get("exists", False),
            "worldview_exists": worldview_info.get("exists", False),
            "diff": None,
            "message": None,
        }

        if not outline_info.get("exists"):
            result["message"] = "大纲文件不存在"
            return result

        if not worldview_info.get("exists"):
            result["message"] = "世界观配置不存在，需要首次同步"
            return result

        try:
            # 加载当前配置
            from world_config_loader import load_world_config

            old_config = load_world_config(outline_info["current_world"])

            # 从大纲生成新配置
            gen_result = self.generator.generate_from_outline(
                outline_info["path"], outline_info["current_world"], save=False
            )
            new_config = gen_result["config"]

            # 计算差异
            changes = IncrementalSync.compute_all_changes(old_config, new_config)

            result["diff"] = changes
            result["has_changes"] = IncrementalSync.has_meaningful_changes(changes)
            result["message"] = "发现变更" if result["has_changes"] else "无变更"

        except Exception as e:
            result["message"] = f"差异计算失败: {e}"

        return result

    def rollback(self, version: int = None) -> Dict[str, Any]:
        """回滚到指定版本

        Args:
            version: 目标版本号，None表示上一版本

        Returns:
            回滚结果
        """
        rollback_info = self.change_tracker.get_rollback_info(version)

        result = {
            "success": False,
            "message": None,
            "rolled_back": False,
            "version": None,
        }

        if not rollback_info:
            result["message"] = "没有可回滚的版本"
            return result

        backup_path = rollback_info.get("backup_path")
        if not backup_path or not Path(backup_path).exists():
            result["message"] = f"备份文件不存在: {backup_path}"
            return result

        try:
            world_name = rollback_info["world_name"]

            # 从备份恢复
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_config = json.load(f)

            # 保存恢复的配置
            file_path = self.generator.save_config(backup_config, world_name)

            # 记录回滚操作
            new_version = self.change_tracker.record_change(
                world_name,
                "rollback",
                {"rolled_back_to": rollback_info["version"]},
                backup_path,
            )

            result["success"] = True
            result["rolled_back"] = True
            result["version"] = new_version
            result["message"] = f"已回滚到版本 {rollback_info['version']}"
            result["file_path"] = str(file_path)

        except Exception as e:
            result["message"] = f"回滚失败: {e}"

        return result

    def get_change_history(self, world_name: str = None, limit: int = 10) -> List[Dict]:
        """获取变更历史

        Args:
            world_name: 世界观名称（可选）
            limit: 返回数量限制

        Returns:
            变更历史列表
        """
        all_changes = self.change_tracker.history.get("changes", [])

        if world_name:
            filtered = [c for c in all_changes if c["world_name"] == world_name]
        else:
            filtered = all_changes

        return filtered[-limit:] if limit else filtered

    def validate(self) -> Dict[str, Any]:
        """验证世界观配置

        Returns:
            验证结果
        """
        from world_config_loader import validate_world_config, get_current_world

        current_world = get_current_world()
        errors = validate_world_config(current_world)

        return {
            "world_name": current_world,
            "valid": len(errors) == 0,
            "errors": errors,
            "message": "验证通过" if not errors else f"发现{len(errors)}个问题",
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="世界观同步工具")
    parser.add_argument("--status", "-s", action="store_true", help="查看同步状态")
    parser.add_argument("--sync", action="store_true", help="执行同步")
    parser.add_argument("--diff", "-d", action="store_true", help="查看变更差异")
    parser.add_argument("--validate", "-v", action="store_true", help="验证配置")
    parser.add_argument("--force", "-f", action="store_true", help="强制覆盖")
    parser.add_argument("--full", action="store_true", help="全量同步（不使用增量）")
    parser.add_argument("--rollback", "-r", action="store_true", help="回滚到上一版本")
    parser.add_argument("--version", type=int, help="指定回滚版本")
    parser.add_argument("--history", action="store_true", help="查看变更历史")

    args = parser.parse_args()

    sync = WorldviewSync()

    if args.status:
        status = sync.check_sync_status()
        print("=" * 60)
        print("世界观同步状态")
        print("=" * 60)
        print(f"\n大纲文件:")
        if status["outline"].get("exists"):
            print(f"  路径: {status['outline']['path']}")
            print(f"  修改时间: {status['outline']['modified_time']}")
            print(f"  大小: {status['outline']['size']} bytes")
            print(f"  Hash: {status['outline']['hash']}")
        else:
            print(f"  错误: {status['outline'].get('error')}")

        print(f"\n世界观配置:")
        if status["worldview"].get("exists"):
            print(f"  名称: {status['worldview']['world_name']}")
            print(f"  修改时间: {status['worldview']['modified_time']}")
            print(f"  力量体系: {status['worldview']['power_systems_count']}个")
            print(f"  势力: {status['worldview']['factions_count']}个")
            print(f"  角色: {status['worldview']['characters_count']}个")
        else:
            print(f"  错误: {status['worldview'].get('error')}")

        print(f"\n同步状态:")
        print(f"  需要同步: {'是' if status['sync_needed'] else '否'}")
        print(f"  原因: {status['reason']}")

    elif args.sync:
        result = sync.sync(force=args.force, incremental=not args.full)
        print("=" * 60)
        print("世界观同步结果")
        print("=" * 60)
        print(f"\n状态: {'成功' if result['success'] else '失败'}")
        print(f"同步类型: {result.get('sync_type', 'none')}")
        print(f"消息: {result['message']}")
        if result.get("version"):
            print(f"版本: {result['version']}")
        if result.get("backup_path"):
            print(f"备份: {result['backup_path']}")
        if result.get("changes"):
            print("\n变更:")
            for change in result["changes"]:
                print(f"  - {change}")

    elif args.diff:
        diff_result = sync.diff()
        print("=" * 60)
        print("世界观差异分析")
        print("=" * 60)
        print(f"\n消息: {diff_result.get('message', '未知')}")

        if diff_result.get("diff"):
            changes = diff_result["diff"]
            for category, cat_changes in changes.items():
                if category == "timestamp":
                    continue

                cat_name = {
                    "power_systems": "力量体系",
                    "factions": "势力",
                    "key_characters": "角色",
                    "eras": "时代",
                }.get(category, category)

                if cat_changes.get("added"):
                    print(f"\n{cat_name}新增:")
                    for key in cat_changes["added"]:
                        print(f"  + {key}")

                if cat_changes.get("removed"):
                    print(f"\n{cat_name}删除:")
                    for key in cat_changes["removed"]:
                        print(f"  - {key}")

                if cat_changes.get("modified"):
                    print(f"\n{cat_name}修改:")
                    for key, fields in cat_changes["modified"].items():
                        print(f"  ~ {key}:")
                        for field, vals in fields.items():
                            print(f"      {field}: {vals['old']} -> {vals['new']}")

    elif args.rollback:
        result = sync.rollback(version=args.version)
        print("=" * 60)
        print("世界观回滚结果")
        print("=" * 60)
        print(f"\n状态: {'成功' if result['success'] else '失败'}")
        print(f"消息: {result['message']}")
        if result.get("version"):
            print(f"新版本: {result['version']}")

    elif args.history:
        history = sync.get_change_history(limit=10)
        print("=" * 60)
        print("变更历史（最近10条）")
        print("=" * 60)
        if not history:
            print("\n暂无变更历史")
        else:
            for change in history:
                print(f"\n版本 {change['version']}:")
                print(f"  世界观: {change['world_name']}")
                print(f"  类型: {change['change_type']}")
                print(f"  时间: {change['timestamp']}")

    elif args.validate:
        result = sync.validate()
        print("=" * 60)
        print("世界观验证结果")
        print("=" * 60)
        print(f"\n世界观: {result['world_name']}")
        print(f"状态: {result['message']}")
        if result["errors"]:
            print("\n错误:")
            for error in result["errors"]:
                print(f"  - {error}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
