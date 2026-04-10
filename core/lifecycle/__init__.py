"""
生命周期管理模块 - Lifecycle

提供技法追踪、配置版本控制、契约生命周期管理。

功能模块：
1. TechniqueTracker - 技法追踪器
   - 追踪技法使用情况
   - 分析效果评分
   - 推荐合适技法

2. ConfigVersionControl - 配置版本控制
   - 创建配置快照
   - 恢复快照
   - 对比快照差异
   - 自动快照检测

3. ContractLifecycle - 契约生命周期
   - 创建场景契约（12大一致性规则）
   - 验证契约合规性
   - 检查内容合规
   - 解决契约冲突

存储位置：
- 技法使用：.cache/technique_usage.json
- 配置快照：.cache/config_snapshots/
- 场景契约：scene_contracts/

12大一致性规则：
1. 角色一致性：性格、能力、外貌不突变
2. 时间线一致性：事件顺序、时代背景一致
3. 力量体系一致性：境界、能力、代价符合设定
4. 地理位置一致性：地点、距离、环境一致
5. 情报边界一致性：角色知道什么不知道什么明确
6. 资源追踪一致性：物品、金钱、能力消耗追踪
7. 伏笔追踪一致性：伏笔埋设、推进、回收一致
8. 承诺追踪一致性：角色承诺、兑现、违背追踪
9. 语言风格一致性：角色对话风格不突变
10. 术语一致性：世界观术语使用一致
11. 主题一致性：章节主题贯穿一致
12. 基调一致性：整体氛围、情绪基调一致
"""

# 技法追踪器
from .technique_tracker import (
    TechniqueTracker,
    TechniqueUsage,
    TechniqueStats,
    get_technique_tracker,
)

# 配置版本控制
from .config_version_control import (
    ConfigVersionControl,
    ConfigSnapshot,
    SnapshotDiff,
    get_config_version_control,
)

# 契约生命周期
from .contract_lifecycle import (
    ContractLifecycle,
    SceneContract,
    ContractRule,
    Violation,
    ConsistencyRule,
    ViolationSeverity,
    get_contract_lifecycle,
)


__all__ = [
    # 技法追踪器
    "TechniqueTracker",
    "TechniqueUsage",
    "TechniqueStats",
    "get_technique_tracker",
    # 配置版本控制
    "ConfigVersionControl",
    "ConfigSnapshot",
    "SnapshotDiff",
    "get_config_version_control",
    # 契约生命周期
    "ContractLifecycle",
    "SceneContract",
    "ContractRule",
    "Violation",
    "ConsistencyRule",
    "ViolationSeverity",
    "get_contract_lifecycle",
]
