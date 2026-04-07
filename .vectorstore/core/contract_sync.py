# -*- coding: utf-8 -*-
"""
场景契约系统 - 同步管理器

功能：
1. 管理并行场景间的契约同步
2. 提供依赖等待机制
3. 提供契约检查点

作者: Sisyphus
"""

import time
from typing import Dict, List, Optional
from datetime import datetime

from .scene_contract import SceneContract, SceneContractStore
from .contract_validator import ContractValidator, ConsistencyConflict


class ContractSyncManager:
    """契约同步管理器（用于并行场景协调）"""

    def __init__(self, chapter_id: str, store: Optional[SceneContractStore] = None):
        self.chapter_id = chapter_id
        self.store = store or SceneContractStore(chapter_id)
        self.validator = ContractValidator()

        # 活跃场景追踪
        self.active_scenes: Dict[str, dict] = {}

        # 检查点记录
        self.checkpoints: List[dict] = []

    # ==================== 场景注册 ====================

    def register_scene_start(self, scene_id: str, timeout: int = 300) -> Dict:
        """
        注册场景开始

        Args:
            scene_id: 场景ID
            timeout: 超时时间（秒）

        Returns:
            注册结果
        """
        # 检查契约是否存在
        contract = self.store.load_contract(scene_id)
        if not contract:
            return {
                "success": False,
                "reason": "契约不存在",
                "suggestion": "请先执行阶段3.5契约提取",
            }

        # 等待依赖场景完成
        if not self._wait_for_dependencies(scene_id, timeout):
            pending = self._get_pending_dependencies(scene_id)
            return {
                "success": False,
                "reason": "依赖场景未完成",
                "pending_dependencies": pending,
                "suggestion": f"等待以下场景完成: {pending}",
            }

        # 检查与依赖场景的契约一致性
        conflicts = self._check_dependencies_consistency(scene_id)
        critical_conflicts = self.validator.get_critical_conflicts(conflicts)

        if critical_conflicts:
            return {
                "success": False,
                "reason": "契约冲突",
                "conflicts": [c.to_dict() for c in conflicts],
                "suggestion": "请修复冲突后再继续",
            }

        # 注册活跃场景
        self.active_scenes[scene_id] = {
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "warnings": [c.to_dict() for c in conflicts if c.level == "warning"],
        }

        return {
            "success": True,
            "contract": contract.to_dict(),
            "warnings": [c.to_dict() for c in conflicts if c.level == "warning"],
        }

    def register_scene_complete(
        self, scene_id: str, updated_contract: Optional[SceneContract] = None
    ) -> Dict:
        """
        注册场景完成

        Args:
            scene_id: 场景ID
            updated_contract: 更新后的契约（可选）

        Returns:
            完成结果
        """
        contract = updated_contract or self.store.load_contract(scene_id)

        if not contract:
            return {"success": False, "reason": "契约不存在"}

        # 更新契约状态
        contract.update_status("completed")
        self.store.save_contract(contract)

        # 记录检查点
        checkpoint = {
            "scene_id": scene_id,
            "timestamp": datetime.now().isoformat(),
            "status": "completed",
        }
        self.checkpoints.append(checkpoint)

        # 移除活跃状态
        if scene_id in self.active_scenes:
            del self.active_scenes[scene_id]

        return {"success": True, "contract": contract.to_dict()}

    # ==================== 依赖管理 ====================

    def _wait_for_dependencies(self, scene_id: str, timeout: int) -> bool:
        """等待依赖场景完成"""
        contract = self.store.load_contract(scene_id)
        if not contract:
            return False

        pre_scenes = contract.dependencies.get("pre_scenes", [])
        if not pre_scenes:
            return True

        start_time = time.time()
        while time.time() - start_time < timeout:
            all_ready = True

            for pre_scene_id in pre_scenes:
                pre_contract = self.store.load_contract(pre_scene_id)
                if (
                    not pre_contract
                    or pre_contract.metadata.get("status") != "completed"
                ):
                    all_ready = False
                    break

            if all_ready:
                return True

            time.sleep(1)

        return False

    def _get_pending_dependencies(self, scene_id: str) -> List[str]:
        """获取未完成的依赖场景"""
        contract = self.store.load_contract(scene_id)
        if not contract:
            return []

        pending = []
        for pre_scene_id in contract.dependencies.get("pre_scenes", []):
            pre_contract = self.store.load_contract(pre_scene_id)
            if not pre_contract or pre_contract.metadata.get("status") != "completed":
                pending.append(pre_scene_id)

        return pending

    def _check_dependencies_consistency(
        self, scene_id: str
    ) -> List[ConsistencyConflict]:
        """检查与依赖场景的契约一致性"""
        contract = self.store.load_contract(scene_id)
        if not contract:
            return []

        conflicts = []
        pre_scenes = contract.dependencies.get("pre_scenes", [])

        for pre_scene_id in pre_scenes:
            pre_contract = self.store.load_contract(pre_scene_id)
            if not pre_contract:
                continue

            # 执行一致性校验
            scene_conflicts = self.validator.validate_contract_pair(
                pre_contract, contract
            )
            conflicts.extend(scene_conflicts)

        return conflicts

    # ==================== 检查点 ====================

    def create_checkpoint(
        self,
        scene_id: str,
        checkpoint_type: str = "after_creation",
        data: Optional[Dict] = None,
    ) -> Dict:
        """
        创建检查点

        Args:
            scene_id: 场景ID
            checkpoint_type: 检查点类型
            data: 检查点数据

        Returns:
            检查点信息
        """
        checkpoint = {
            "scene_id": scene_id,
            "type": checkpoint_type,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        }

        self.checkpoints.append(checkpoint)

        return checkpoint

    def get_checkpoints(self, scene_id: Optional[str] = None) -> List[Dict]:
        """获取检查点列表"""
        if scene_id:
            return [c for c in self.checkpoints if c.get("scene_id") == scene_id]
        return self.checkpoints

    # ==================== 状态查询 ====================

    def get_active_scenes(self) -> Dict[str, dict]:
        """获取活跃场景列表"""
        return self.active_scenes.copy()

    def is_scene_active(self, scene_id: str) -> bool:
        """检查场景是否活跃"""
        return scene_id in self.active_scenes

    def get_scene_status(self, scene_id: str) -> Optional[str]:
        """获取场景状态"""
        contract = self.store.load_contract(scene_id)
        if contract:
            return contract.metadata.get("status")

        if scene_id in self.active_scenes:
            return "active"

        return None

    # ==================== 批量操作 ====================

    def batch_validate(self) -> Dict:
        """
        批量校验所有契约

        Returns:
            校验结果
        """
        contracts = self.store.load_all_contracts()
        scene_order = self.store.get_scene_order()

        conflicts = self.validator.validate_contracts(contracts, scene_order)

        return {
            "total_contracts": len(contracts),
            "total_conflicts": len(conflicts),
            "critical_count": len(self.validator.get_critical_conflicts(conflicts)),
            "warning_count": len(self.validator.get_warning_conflicts(conflicts)),
            "conflicts": [c.to_dict() for c in conflicts],
            "scene_order": scene_order,
        }

    def get_execution_plan(self) -> Dict:
        """
        获取场景执行计划

        Returns:
            执行计划
        """
        dependency_graph = self.store.get_dependency_graph()
        scene_order = self.store.get_scene_order()

        # 分析可并行执行的场景
        parallel_groups = self._analyze_parallel_groups()

        return {
            "scene_order": scene_order,
            "dependency_graph": dependency_graph,
            "parallel_groups": parallel_groups,
        }

    def _analyze_parallel_groups(self) -> List[List[str]]:
        """分析可并行执行的场景组"""
        contracts = self.store.load_all_contracts()

        # 按依赖层级分组
        levels = {}

        for contract in contracts:
            # 计算依赖深度
            depth = self._calculate_depth(contract.scene_id, contracts)

            if depth not in levels:
                levels[depth] = []

            levels[depth].append(contract.scene_id)

        # 转换为列表
        result = []
        for depth in sorted(levels.keys()):
            result.append(levels[depth])

        return result

    def _calculate_depth(self, scene_id: str, contracts: List[SceneContract]) -> int:
        """计算场景的依赖深度"""
        contract_map = {c.scene_id: c for c in contracts}

        if scene_id not in contract_map:
            return 0

        contract = contract_map[scene_id]
        pre_scenes = contract.dependencies.get("pre_scenes", [])

        if not pre_scenes:
            return 0

        max_depth = 0
        for pre_scene in pre_scenes:
            depth = self._calculate_depth(pre_scene, contracts)
            max_depth = max(max_depth, depth + 1)

        return max_depth


# ==================== 便捷函数 ====================


def create_sync_manager(chapter_id: str) -> ContractSyncManager:
    """创建同步管理器"""
    return ContractSyncManager(chapter_id)


def validate_chapter_contracts(chapter_id: str) -> Dict:
    """
    校验章节契约

    Args:
        chapter_id: 章节ID

    Returns:
        校验结果
    """
    manager = ContractSyncManager(chapter_id)
    return manager.batch_validate()


# 导出
__all__ = ["ContractSyncManager", "create_sync_manager", "validate_chapter_contracts"]
