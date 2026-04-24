#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置同步器 - 统一管理所有维度配置的同步

功能：
1. 统一读取配置
2. 发现新类型后自动同步
3. 通知工作流配置更新

使用：
    from config import get_scene_types, get_power_types

    scene_types = get_scene_types()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class ConfigUpdate:
    """配置更新记录"""

    config_type: str
    action: str  # add, update, delete
    key: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    timestamp: str = ""


class DimensionSync:
    """维度配置同步器"""

    CONFIG_DIR = Path(__file__).parent / "dimensions"

    def __init__(self):
        """初始化同步器"""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict] = {}
        self._update_log: List[ConfigUpdate] = []

    # ==================== 读取接口 ====================

    @classmethod
    def get_scene_types(cls) -> Dict:
        """
        获取场景类型配置

        Returns:
            Dict: 场景类型配置字典
        """
        data = cls._load_config("scene_types.json")
        return data.get("scene_types", {})

    @classmethod
    def get_power_types(cls) -> Dict:
        """
        获取力量类型配置

        Returns:
            Dict: 力量类型配置字典
        """
        data = cls._load_config("power_types.json")
        return data.get("power_types", {})

    @classmethod
    def get_faction_types(cls) -> Dict:
        """
        获取势力类型配置

        Returns:
            Dict: 势力类型配置字典
        """
        data = cls._load_config("faction_types.json")
        return data.get("faction_types", {})

    @classmethod
    def get_technique_types(cls) -> Dict:
        """
        获取技法类型配置

        Returns:
            Dict: 技法类型配置字典
        """
        data = cls._load_config("technique_types.json")
        return data.get("technique_types", {})

    # ==================== 写入接口 ====================

    def add_scene_type(self, scene_type: str, config: Dict) -> bool:
        """
        添加新场景类型

        Args:
            scene_type: 场景类型名称
            config: 场景配置

        Returns:
            bool: 是否成功
        """
        data = self._load_config("scene_types.json")

        if scene_type in data.get("scene_types", {}):
            print(f"[警告] 场景类型 '{scene_type}' 已存在")
            return False

        data["scene_types"][scene_type] = config
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        success = self._save_config("scene_types.json", data)

        if success:
            self._log_update("scene_types", "add", scene_type, None, config)

        return success

    def add_power_type(self, power_type: str, config: Dict) -> bool:
        """
        添加新力量类型

        Args:
            power_type: 力量类型名称
            config: 力量配置

        Returns:
            bool: 是否成功
        """
        data = self._load_config("power_types.json")

        if power_type in data.get("power_types", {}):
            print(f"[警告] 力量类型 '{power_type}' 已存在")
            return False

        data["power_types"][power_type] = config
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        success = self._save_config("power_types.json", data)

        if success:
            self._log_update("power_types", "add", power_type, None, config)

        return success

    def add_faction_type(self, faction_type: str, config: Dict) -> bool:
        """
        添加新势力类型

        Args:
            faction_type: 势力类型名称
            config: 势力配置

        Returns:
            bool: 是否成功
        """
        data = self._load_config("faction_types.json")

        if faction_type in data.get("faction_types", {}):
            print(f"[警告] 势力类型 '{faction_type}' 已存在")
            return False

        data["faction_types"][faction_type] = config
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d")

        success = self._save_config("faction_types.json", data)

        if success:
            self._log_update("faction_types", "add", faction_type, None, config)

        return success

    # ==================== 底层操作 ====================

    @classmethod
    def _load_config(cls, filename: str) -> Dict:
        """
        加载配置文件

        Args:
            filename: 配置文件名

        Returns:
            Dict: 配置数据
        """
        config_path = cls.CONFIG_DIR / filename

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[错误] 加载配置文件失败: {filename}, {e}")
                return {}

        # 返回默认结构
        config_key = filename.replace(".json", "")
        return {
            "version": "1.0",
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            config_key: {},
        }

    @classmethod
    def _save_config(cls, filename: str, data: Dict) -> bool:
        """
        保存配置文件

        Args:
            filename: 配置文件名
            data: 配置数据

        Returns:
            bool: 是否成功
        """
        config_path = cls.CONFIG_DIR / filename

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[错误] 保存配置文件失败: {filename}, {e}")
            return False

    def _log_update(
        self, config_type: str, action: str, key: str, old_value: Any, new_value: Any
    ):
        """记录配置更新"""
        update = ConfigUpdate(
            config_type=config_type,
            action=action,
            key=key,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now().isoformat(),
        )
        self._update_log.append(update)

    # ==================== 同步功能 ====================

    def sync_all(self) -> Dict[str, int]:
        """
        同步所有配置

        Returns:
            Dict[str, int]: 各配置类型的更新数量
        """
        results = {
            "scene_types": 0,
            "power_types": 0,
            "faction_types": 0,
            "technique_types": 0,
        }

        # TODO: 实现从各来源同步配置的逻辑
        # 1. 从 case_builder.py 同步场景类型
        # 2. 从 power_cost_extractor.py 同步力量类型
        # 3. 从设定文件同步势力类型
        # 4. 从创作技法目录同步技法类型

        print("[同步] 配置同步完成")
        return results

    def get_update_log(self, limit: int = 10) -> List[Dict]:
        """
        获取配置更新日志

        Args:
            limit: 返回条数限制

        Returns:
            List[Dict]: 更新记录列表
        """
        return [asdict(log) for log in self._update_log[-limit:]]

    # ==================== 验证功能 ====================

    def validate_all(self) -> Dict[str, bool]:
        """
        验证所有配置文件

        Returns:
            Dict[str, bool]: 各配置文件的验证结果
        """
        results = {}

        for filename in [
            "scene_types.json",
            "power_types.json",
            "faction_types.json",
            "technique_types.json",
        ]:
            config_path = self.CONFIG_DIR / filename

            if not config_path.exists():
                results[filename] = False
                continue

            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 检查基本结构
                has_version = "version" in data
                has_updated_at = "updated_at" in data
                config_key = filename.replace(".json", "")
                has_data = config_key in data

                results[filename] = has_version and has_updated_at and has_data
            except:
                results[filename] = False

        return results


# ==================== 便捷函数 ====================


def get_scene_types() -> Dict:
    """获取场景类型配置"""
    return DimensionSync.get_scene_types()


def get_power_types() -> Dict:
    """获取力量类型配置"""
    return DimensionSync.get_power_types()


def get_faction_types() -> Dict:
    """获取势力类型配置"""
    return DimensionSync.get_faction_types()


def get_technique_types() -> Dict:
    """获取技法类型配置"""
    return DimensionSync.get_technique_types()


# ==================== 命令行接口 ====================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="维度配置同步器")
    parser.add_argument("--status", action="store_true", help="查看配置状态")
    parser.add_argument("--validate", action="store_true", help="验证配置文件")
    parser.add_argument("--sync", action="store_true", help="同步所有配置")

    args = parser.parse_args()

    sync = DimensionSync()

    if args.status:
        print("\n[配置状态]")
        print(f"  配置目录: {sync.CONFIG_DIR}")
        print(f"  场景类型: {len(sync.get_scene_types())} 种")
        print(f"  力量类型: {len(sync.get_power_types())} 种")
        print(f"  势力类型: {len(sync.get_faction_types())} 种")
        print(f"  技法类型: {len(sync.get_technique_types())} 种")

    elif args.validate:
        print("\n[配置验证]")
        results = sync.validate_all()
        for filename, valid in results.items():
            status = "[OK]" if valid else "[FAIL]"
            print(f"  {status} {filename}")

    elif args.sync:
        print("\n[配置同步]")
        results = sync.sync_all()
        for config_type, count in results.items():
            print(f"  {config_type}: {count} 条更新")

    else:
        parser.print_help()
