"""
契约生命周期管理 - ContractLifecycle

管理场景契约的创建、验证、合规检查和冲突解决。

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

功能：
- create_contract(): 创建契约
- validate_contract(): 验证契约
- check_contract_compliance(): 检查合规
- resolve_conflicts(): 解决冲突

存储位置：scene_contracts/
"""

import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum

# 尝试导入配置管理器
_project_root = Path(__file__).parent.parent.parent
_validation_config: Dict[str, Any] = {}

try:
    from core.config_loader import get_project_root

    _project_root = Path(get_project_root())
except ImportError:
    pass

PROJECT_ROOT = _project_root
VALIDATION_CONFIG = _validation_config


class ConsistencyRule(Enum):
    """12大一致性规则"""

    CHARACTER = "角色一致性"
    TIMELINE = "时间线一致性"
    POWER_SYSTEM = "力量体系一致性"
    GEOGRAPHY = "地理位置一致性"
    INFORMATION_BOUNDARY = "情报边界一致性"
    RESOURCE_TRACKING = "资源追踪一致性"
    FORESHADOW_TRACKING = "伏笔追踪一致性"
    PROMISE_TRACKING = "承诺追踪一致性"
    LANGUAGE_STYLE = "语言风格一致性"
    TERMINOLOGY = "术语一致性"
    THEME = "主题一致性"
    TONE = "基调一致性"


class ViolationSeverity(Enum):
    """违规严重程度"""

    CRITICAL = "critical"  # 严重：必须修复
    WARNING = "warning"  # 警告：建议修复
    INFO = "info"  # 信息：可忽略


@dataclass
class ContractRule:
    """契约规则"""

    rule_type: ConsistencyRule
    constraint: Dict[str, Any]  # 规则约束
    description: Optional[str] = None
    priority: int = 1  # 优先级 (1-5)


@dataclass
class Violation:
    """违规记录"""

    rule_type: ConsistencyRule
    severity: ViolationSeverity
    location: str  # 位置描述
    message: str  # 错误信息
    suggestion: Optional[str] = None  # 修复建议
    context: Optional[str] = None  # 违规上下文


@dataclass
class SceneContract:
    """场景契约"""

    contract_id: str
    scene_id: str  # 场景ID
    chapter: int  # 章节
    scene_type: str  # 场景类型
    writer: str  # 负责作家

    # 契约规则
    rules: List[ContractRule] = field(default_factory=list)

    # 角色约束
    characters_involved: List[str] = field(default_factory=list)
    character_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 时间约束
    timeline_position: Optional[str] = None
    time_constraints: Dict[str, Any] = field(default_factory=dict)

    # 力量体系约束
    power_constraints: Dict[str, Any] = field(default_factory=dict)

    # 地理约束
    location: Optional[str] = None
    geography_constraints: Dict[str, Any] = field(default_factory=dict)

    # 情报约束
    information_state: Dict[str, Set[str]] = field(default_factory=dict)

    # 资源约束
    resource_state: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # 伏笔约束
    foreshadows_active: List[str] = field(default_factory=list)
    foreshadows_to_resolve: List[str] = field(default_factory=list)

    # 承诺约束
    promises_active: List[str] = field(default_factory=list)

    # 风格约束
    style_constraints: Dict[str, str] = field(default_factory=dict)

    # 术语约束
    terminology: Dict[str, str] = field(default_factory=dict)

    # 元信息
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: Optional[str] = None
    is_validated: bool = False
    violations: List[Dict[str, Any]] = field(default_factory=list)


class ContractLifecycle:
    """契约生命周期管理"""

    STORAGE_DIR = "scene_contracts"
    INDEX_FILE = "scene_contracts/index.json"

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化契约生命周期

        Args:
            project_root: 项目根目录，默认自动检测
        """
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.storage_dir = self.project_root / self.STORAGE_DIR
        self.index_path = self.project_root / self.INDEX_FILE
        self._ensure_storage()

        # 加载世界观设定（用于验证）
        self.worldview_settings = self._load_worldview_settings()

        # 加载所有力量体系的境界配置
        self._realm_orders = self._load_realm_orders()

    def _load_realm_orders(self) -> Dict[str, list]:
        """加载所有力量体系的境界配置"""
        try:
            from core.config_loader import get_all_realm_orders

            return get_all_realm_orders()
        except ImportError:
            # 向后兼容：使用单一境界配置
            return {"default": VALIDATION_CONFIG.get("realm_order", [])}

    def get_realm_order_for_character(self, character_name: str) -> list:
        """
        根据角色的力量体系获取对应的境界顺序

        Args:
            character_name: 角色名称

        Returns:
            该角色的境界顺序列表
        """
        # 从世界观设定中获取角色的力量体系
        characters = self.worldview_settings.get("characters", {})
        character_info = characters.get(character_name, {})

        # 获取角色的力量体系
        power_system = character_info.get("power_system", "default")

        # 返回对应的境界顺序
        return self._realm_orders.get(
            power_system, self._realm_orders.get("default", [])
        )

    def _ensure_storage(self) -> None:
        """确保存储目录和索引文件存在"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        if not self.index_path.exists():
            self._save_index(
                {
                    "contracts": [],
                    "active_contracts": {},
                    "resolved_contracts": [],
                }
            )

    def _load_index(self) -> Dict[str, Any]:
        """加载契约索引"""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "contracts": [],
                "active_contracts": {},
                "resolved_contracts": [],
            }

    def _save_index(self, index: Dict[str, Any]) -> None:
        """保存契约索引"""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _load_worldview_settings(self) -> Dict[str, Any]:
        """加载世界观设定"""
        settings = {}

        # 尝试加载人物谱
        character_path = self.project_root / "设定" / "人物谱.md"
        if character_path.exists():
            settings["characters"] = self._parse_character_file(character_path)

        # 尝试加载力量体系
        power_path = self.project_root / "设定" / "力量体系.md"
        if power_path.exists():
            settings["power_system"] = self._parse_power_file(power_path)

        # 尝试加载时间线
        timeline_path = self.project_root / "设定" / "时间线.md"
        if timeline_path.exists():
            settings["timeline"] = self._parse_timeline_file(timeline_path)

        # 尝试加载十大势力
        faction_path = self.project_root / "设定" / "十大势力.md"
        if faction_path.exists():
            settings["factions"] = self._parse_faction_file(faction_path)

        return settings

    def _parse_character_file(self, file_path: Path) -> Dict[str, Any]:
        """解析人物文件"""
        # 简化实现：提取角色名和能力
        characters = {}
        content = file_path.read_text(encoding="utf-8")

        # 提取角色名（假设格式：### 角色名）
        for match in re.finditer(r"###\s+([^\n]+)", content):
            char_name = match.group(1).strip()
            characters[char_name] = {"abilities": [], "realm": None}

        return characters

    def _parse_power_file(self, file_path: Path) -> Dict[str, Any]:
        """解析力量体系文件"""
        power_system = {"realms": self.REALM_ORDER, "types": []}
        content = file_path.read_text(encoding="utf-8")

        # 提取力量类型（假设格式：## 力量类型）
        for match in re.finditer(r"##\s+([^\n]+)", content):
            power_type = match.group(1).strip()
            power_system["types"].append(power_type)

        return power_system

    def _parse_timeline_file(self, file_path: Path) -> Dict[str, Any]:
        """解析时间线文件"""
        eras: List[str] = []
        events: Dict[str, Any] = {}
        content = file_path.read_text(encoding="utf-8")

        # 提取时代（假设格式：## 时代名）
        for match in re.finditer(r"##\s+([^\n]+)", content):
            era_name = match.group(1).strip()
            eras.append(era_name)

        return {"eras": eras, "events": events}

    def _parse_faction_file(self, file_path: Path) -> Dict[str, Any]:
        """解析势力文件"""
        factions = {}
        content = file_path.read_text(encoding="utf-8")

        # 提取势力名（假设格式：### 势力名）
        for match in re.finditer(r"###\s+([^\n]+)", content):
            faction_name = match.group(1).strip()
            factions[faction_name] = {"members": [], "style": None}

        return factions

    def create_contract(
        self,
        scene_id: str,
        contract_data: Dict[str, Any],
        auto_validate: bool = True,
    ) -> SceneContract:
        """
        创建场景契约

        Args:
            scene_id: 场景ID
            contract_data: 契约数据
            auto_validate: 是否自动验证

        Returns:
            SceneContract 契约对象
        """
        # 生成契约ID
        contract_id = hashlib.md5(
            f"{scene_id}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        # 构建契约规则
        rules = self._build_rules(contract_data)

        # 创建契约对象
        contract = SceneContract(
            contract_id=contract_id,
            scene_id=scene_id,
            chapter=contract_data.get("chapter", 1),
            scene_type=contract_data.get("scene_type", "unknown"),
            writer=contract_data.get("writer", "unknown"),
            rules=rules,
            characters_involved=contract_data.get("characters_involved", []),
            character_states=contract_data.get("character_states", {}),
            timeline_position=contract_data.get("timeline_position"),
            time_constraints=contract_data.get("time_constraints", {}),
            power_constraints=contract_data.get("power_constraints", {}),
            location=contract_data.get("location"),
            geography_constraints=contract_data.get("geography_constraints", {}),
            information_state=contract_data.get("information_state", {}),
            resource_state=contract_data.get("resource_state", {}),
            foreshadows_active=contract_data.get("foreshadows_active", []),
            foreshadows_to_resolve=contract_data.get("foreshadows_to_resolve", []),
            promises_active=contract_data.get("promises_active", []),
            style_constraints=contract_data.get("style_constraints", {}),
            terminology=contract_data.get("terminology", {}),
        )

        # 自动验证
        if auto_validate:
            violations = self.validate_contract(contract)
            contract.violations = [asdict(v) for v in violations]
            contract.is_validated = len(violations) == 0

        # 保存契约
        self._save_contract(contract)

        # 更新索引
        self._update_index(contract)

        return contract

    def _build_rules(self, contract_data: Dict[str, Any]) -> List[ContractRule]:
        """根据契约数据构建规则"""
        rules = []

        # 角色一致性规则
        if contract_data.get("characters_involved"):
            for char in contract_data["characters_involved"]:
                rules.append(
                    ContractRule(
                        rule_type=ConsistencyRule.CHARACTER,
                        constraint={"character": char},
                        description=f"角色 {char} 状态一致性",
                        priority=5,
                    )
                )

        # 时间线一致性规则
        if contract_data.get("timeline_position"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.TIMELINE,
                    constraint={"position": contract_data["timeline_position"]},
                    description="时间线位置一致性",
                    priority=4,
                )
            )

        # 力量体系一致性规则
        if contract_data.get("power_constraints"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.POWER_SYSTEM,
                    constraint=contract_data["power_constraints"],
                    description="力量体系一致性",
                    priority=5,
                )
            )

        # 地理位置一致性规则
        if contract_data.get("location"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.GEOGRAPHY,
                    constraint={"location": contract_data["location"]},
                    description="地理位置一致性",
                    priority=3,
                )
            )

        # 情报边界一致性规则
        if contract_data.get("information_state"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.INFORMATION_BOUNDARY,
                    constraint=contract_data["information_state"],
                    description="情报边界一致性",
                    priority=4,
                )
            )

        # 资源追踪一致性规则
        if contract_data.get("resource_state"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.RESOURCE_TRACKING,
                    constraint=contract_data["resource_state"],
                    description="资源追踪一致性",
                    priority=3,
                )
            )

        # 伏笔追踪一致性规则
        if contract_data.get("foreshadows_active") or contract_data.get(
            "foreshadows_to_resolve"
        ):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.FORESHADOW_TRACKING,
                    constraint={
                        "active": contract_data.get("foreshadows_active", []),
                        "to_resolve": contract_data.get("foreshadows_to_resolve", []),
                    },
                    description="伏笔追踪一致性",
                    priority=4,
                )
            )

        # 承诺追踪一致性规则
        if contract_data.get("promises_active"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.PROMISE_TRACKING,
                    constraint={"promises": contract_data["promises_active"]},
                    description="承诺追踪一致性",
                    priority=3,
                )
            )

        # 语言风格一致性规则
        if contract_data.get("style_constraints"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.LANGUAGE_STYLE,
                    constraint=contract_data["style_constraints"],
                    description="语言风格一致性",
                    priority=2,
                )
            )

        # 术语一致性规则
        if contract_data.get("terminology"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.TERMINOLOGY,
                    constraint=contract_data["terminology"],
                    description="术语一致性",
                    priority=2,
                )
            )

        # 主题一致性规则（默认添加）
        if contract_data.get("theme"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.THEME,
                    constraint={"theme": contract_data["theme"]},
                    description="主题一致性",
                    priority=2,
                )
            )

        # 基调一致性规则（默认添加）
        if contract_data.get("tone"):
            rules.append(
                ContractRule(
                    rule_type=ConsistencyRule.TONE,
                    constraint={"tone": contract_data["tone"]},
                    description="基调一致性",
                    priority=2,
                )
            )

        return rules

    def validate_contract(self, contract: SceneContract) -> List[Violation]:
        """
        验证契约

        Args:
            contract: 契约对象

        Returns:
            违规列表
        """
        violations = []

        for rule in contract.rules:
            # 根据规则类型验证
            rule_violations = self._validate_rule(contract, rule)
            violations.extend(rule_violations)

        return violations

    def _validate_rule(
        self,
        contract: SceneContract,
        rule: ContractRule,
    ) -> List[Violation]:
        """验证单个规则"""
        violations = []

        rule_type = rule.rule_type
        constraint = rule.constraint

        # 根据规则类型调用对应验证器
        validators = {
            ConsistencyRule.CHARACTER: self._validate_character,
            ConsistencyRule.TIMELINE: self._validate_timeline,
            ConsistencyRule.POWER_SYSTEM: self._validate_power_system,
            ConsistencyRule.GEOGRAPHY: self._validate_geography,
            ConsistencyRule.INFORMATION_BOUNDARY: self._validate_information,
            ConsistencyRule.RESOURCE_TRACKING: self._validate_resource,
            ConsistencyRule.FORESHADOW_TRACKING: self._validate_foreshadow,
            ConsistencyRule.PROMISE_TRACKING: self._validate_promise,
            ConsistencyRule.LANGUAGE_STYLE: self._validate_language_style,
            ConsistencyRule.TERMINOLOGY: self._validate_terminology,
            ConsistencyRule.THEME: self._validate_theme,
            ConsistencyRule.TONE: self._validate_tone,
        }

        validator = validators.get(rule_type)
        if validator:
            violations = validator(contract, constraint)

        return violations

    def _validate_character(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证角色一致性"""
        violations = []
        character = constraint.get("character")

        if not character:
            return violations

        # 检查角色是否存在于世界观
        if self.worldview_settings.get("characters"):
            if character not in self.worldview_settings["characters"]:
                violations.append(
                    Violation(
                        rule_type=ConsistencyRule.CHARACTER,
                        severity=ViolationSeverity.WARNING,
                        location=f"契约角色列表",
                        message=f"角色 '{character}' 未在人物谱中定义",
                        suggestion="请确认角色名或添加到人物谱",
                    )
                )

        # 检查角色状态是否突变
        char_state = contract.character_states.get(character, {})

        # 检查境界是否倒退（如果配置了境界顺序）
        if self.REALM_ORDER and char_state.get("realm"):
            # 这里只是静态检查，实际场景创作时需要更细致的检查
            pass

        return violations

    def _validate_timeline(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证时间线一致性"""
        violations = []
        position = constraint.get("position")

        if not position:
            return violations

        # 检查时间线位置是否有效
        if self.worldview_settings.get("timeline"):
            eras = self.worldview_settings["timeline"].get("eras", [])
            if eras and position not in eras:
                # 可能是具体时间点，不一定是时代名
                # 这里简化处理，实际需要更智能的时间解析
                pass

        return violations

    def _validate_power_system(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证力量体系一致性"""
        violations = []

        # 检查境界是否在允许范围内
        realm = constraint.get("realm")
        if realm and self.REALM_ORDER:
            if realm not in self.REALM_ORDER:
                violations.append(
                    Violation(
                        rule_type=ConsistencyRule.POWER_SYSTEM,
                        severity=ViolationSeverity.WARNING,
                        location=f"力量约束",
                        message=f"境界 '{realm}' 不在标准境界列表中",
                        suggestion=f"建议使用标准境界：{self.REALM_ORDER}",
                    )
                )

        # 检查力量类型是否有效
        power_type = constraint.get("power_type")
        if power_type and self.worldview_settings.get("power_system"):
            types = self.worldview_settings["power_system"].get("types", [])
            if types and power_type not in types:
                violations.append(
                    Violation(
                        rule_type=ConsistencyRule.POWER_SYSTEM,
                        severity=ViolationSeverity.INFO,
                        location=f"力量约束",
                        message=f"力量类型 '{power_type}' 可能不在定义的体系中",
                        suggestion=f"请确认力量类型或添加到力量体系",
                    )
                )

        return violations

    def _validate_geography(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证地理位置一致性"""
        violations = []
        # 地理验证需要更详细的地图数据，这里简化处理
        return violations

    def _validate_information(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证情报边界一致性"""
        violations = []
        # 情报边界验证需要在创作内容时动态检查
        return violations

    def _validate_resource(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证资源追踪一致性"""
        violations = []
        # 资源验证需要在创作内容时动态检查数值变化
        return violations

    def _validate_foreshadow(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证伏笔追踪一致性"""
        violations = []

        # 检查要回收的伏笔是否确实在活动伏笔中
        to_resolve = constraint.get("to_resolve", [])
        active = constraint.get("active", [])

        for foreshadow in to_resolve:
            if foreshadow not in active:
                violations.append(
                    Violation(
                        rule_type=ConsistencyRule.FORESHADOW_TRACKING,
                        severity=ViolationSeverity.WARNING,
                        location=f"伏笔约束",
                        message=f"伏笔 '{foreshadow}' 未在前文埋设，无法回收",
                        suggestion=f"请确认伏笔ID或先埋设该伏笔",
                    )
                )

        return violations

    def _validate_promise(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证承诺追踪一致性"""
        violations = []
        # 承诺验证需要追踪历史承诺
        return violations

    def _validate_language_style(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证语言风格一致性"""
        violations = []
        # 语言风格需要在创作内容时动态检查
        return violations

    def _validate_terminology(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证术语一致性"""
        violations = []
        # 术语一致性需要在创作内容时动态检查用词
        return violations

    def _validate_theme(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证主题一致性"""
        violations = []
        # 主题一致性需要在创作内容后检查内容是否符合主题
        return violations

    def _validate_tone(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]:
        """验证基调一致性"""
        violations = []
        # 基调一致性需要在创作内容后检查氛围描写
        return violations

    def check_contract_compliance(
        self,
        scene_id: str,
        content: str,
    ) -> List[Violation]:
        """
        检查内容是否符合契约

        Args:
            scene_id: 场景ID
            content: 场景内容

        Returns:
            违规列表
        """
        # 加载契约
        contract = self._load_contract(scene_id)
        if not contract:
            return []

        violations = []

        # 动态检查内容合规性
        for rule in contract.rules:
            rule_violations = self._check_content_rule(content, contract, rule)
            violations.extend(rule_violations)

        return violations

    def _check_content_rule(
        self,
        content: str,
        contract: SceneContract,
        rule: ContractRule,
    ) -> List[Violation]:
        """检查内容是否符合规则"""
        violations = []

        rule_type = rule.rule_type

        # 角色一致性：检查角色是否出场，性格描写是否符合
        if rule_type == ConsistencyRule.CHARACTER:
            character = rule.constraint.get("character")
            if character and character not in content:
                # 角色未出场
                pass  # 可能是合理情况，不强制报错

        # 力量体系一致性：检查境界倒退
        if rule_type == ConsistencyRule.POWER_SYSTEM and self.REALM_ORDER:
            # 检查境界变化是否合理
            realm_pattern = "|".join(self.REALM_ORDER)
            matches = re.findall(f"({realm_pattern})", content)

            if len(matches) > 1:
                # 发现多个境界词，检查是否有倒退
                for i in range(len(matches) - 1):
                    old_idx = (
                        self.REALM_ORDER.index(matches[i])
                        if matches[i] in self.REALM_ORDER
                        else -1
                    )
                    new_idx = (
                        self.REALM_ORDER.index(matches[i + 1])
                        if matches[i + 1] in self.REALM_ORDER
                        else -1
                    )

                    if old_idx > new_idx and old_idx >= 0 and new_idx >= 0:
                        violations.append(
                            Violation(
                                rule_type=ConsistencyRule.POWER_SYSTEM,
                                severity=ViolationSeverity.CRITICAL,
                                location=f"内容第{i}处境界描述",
                                message=f"境界倒退：'{matches[i]}' -> '{matches[i + 1]}'",
                                suggestion=f"请确认境界变化是否有合理原因（如力量被压制）",
                                context=f"原文：{matches[i]}...{matches[i + 1]}",
                            )
                        )

        # 时间线一致性：检查时间描述
        if rule_type == ConsistencyRule.TIMELINE:
            # 检查是否有时间矛盾（如白天黑夜同时出现）
            time_keywords = ["白天", "夜晚", "黎明", "黄昏", "正午", "午夜"]
            found_times = [kw for kw in time_keywords if kw in content]

            if len(found_times) > 2:
                # 可能时间矛盾
                violations.append(
                    Violation(
                        rule_type=ConsistencyRule.TIMELINE,
                        severity=ViolationSeverity.WARNING,
                        location=f"内容时间描述",
                        message=f"发现多个时间关键词：{found_times}",
                        suggestion=f"请确认时间描述是否一致",
                    )
                )

        # 地理位置一致性：检查地点描写
        if rule_type == ConsistencyRule.GEOGRAPHY:
            expected_location = contract.location
            if expected_location:
                # 检查是否有其他地点名称（简单检查）
                pass  # 需要更详细的地理知识库

        # 情报边界一致性：检查角色是否透露不应知的信息
        if rule_type == ConsistencyRule.INFORMATION_BOUNDARY:
            # 检查角色是否透露超出其情报范围的信息
            pass  # 需要详细的角色情报图谱

        # 资源追踪一致性：检查资源数值变化
        if rule_type == ConsistencyRule.RESOURCE_TRACKING:
            # 检查是否有资源数值变化（如消耗灵石）
            # 查找数字+单位模式
            resource_pattern = r"(\d+)\s*(灵石|金币|元气|丹药)"
            resource_matches = re.findall(resource_pattern, content)

            if resource_matches:
                # 有资源消耗描写，需要记录
                pass  # 实际需要追踪 Ledger

        # 伏笔追踪一致性：检查伏笔是否被埋设或回收
        if rule_type == ConsistencyRule.FORESHADOW_TRACKING:
            to_resolve = rule.constraint.get("to_resolve", [])
            for foreshadow in to_resolve:
                if foreshadow in content:
                    # 伏笔被回收，记录
                    pass  # 需要更新伏笔状态

        # 承诺追踪一致性：检查承诺是否兑现
        if rule_type == ConsistencyRule.PROMISE_TRACKING:
            # 检查是否有承诺兑现描写
            pass  # 需要追踪承诺状态

        return violations

    def resolve_conflicts(
        self,
        contracts: List[SceneContract],
    ) -> Dict[str, Any]:
        """
        解决契约冲突

        Args:
            contracts: 契约列表

        Returns:
            解决结果 {
                "resolved": bool,
                "conflicts": List[Dict],
                "resolution_plan": Dict,
            }
        """
        conflicts = []

        # 检查契约之间的冲突
        for i, contract1 in enumerate(contracts):
            for j, contract2 in enumerate(contracts[i + 1 :], i + 1):
                # 检查角色冲突
                char_conflict = self._check_character_conflict(contract1, contract2)
                if char_conflict:
                    conflicts.append(
                        {
                            "type": "character",
                            "contracts": [contract1.contract_id, contract2.contract_id],
                            "detail": char_conflict,
                        }
                    )

                # 检查时间冲突
                time_conflict = self._check_time_conflict(contract1, contract2)
                if time_conflict:
                    conflicts.append(
                        {
                            "type": "timeline",
                            "contracts": [contract1.contract_id, contract2.contract_id],
                            "detail": time_conflict,
                        }
                    )

                # 检查地理冲突
                geo_conflict = self._check_geography_conflict(contract1, contract2)
                if geo_conflict:
                    conflicts.append(
                        {
                            "type": "geography",
                            "contracts": [contract1.contract_id, contract2.contract_id],
                            "detail": geo_conflict,
                        }
                    )

        # 生成解决方案
        resolution_plan = self._generate_resolution_plan(conflicts, contracts)

        return {
            "resolved": len(conflicts) == 0,
            "conflicts": conflicts,
            "resolution_plan": resolution_plan,
        }

    def _check_character_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]:
        """检查角色状态冲突"""
        # 检查共同角色的状态是否冲突
        common_chars = set(contract1.characters_involved) & set(
            contract2.characters_involved
        )

        for char in common_chars:
            state1 = contract1.character_states.get(char, {})
            state2 = contract2.character_states.get(char, {})

            # 检查境界是否一致
            realm1 = state1.get("realm")
            realm2 = state2.get("realm")

            if realm1 and realm2 and realm1 != realm2:
                return {
                    "character": char,
                    "reason": f"境界不一致：'{realm1}' vs '{realm2}'",
                    "severity": "critical",
                }

        return None

    def _check_time_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]:
        """检查时间冲突"""
        # 检查时间线位置是否冲突
        if contract1.timeline_position and contract2.timeline_position:
            if contract1.timeline_position != contract2.timeline_position:
                # 如果在同一章节但不同时代，冲突
                if contract1.chapter == contract2.chapter:
                    return {
                        "positions": [
                            contract1.timeline_position,
                            contract2.timeline_position,
                        ],
                        "reason": "同一章节存在不同时代",
                        "severity": "critical",
                    }

        return None

    def _check_geography_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]:
        """检查地理冲突"""
        # 检查地点是否冲突
        if contract1.location and contract2.location:
            if contract1.location != contract2.location:
                # 如果角色在两个场景同时出现，但地点不同，可能冲突
                common_chars = set(contract1.characters_involved) & set(
                    contract2.characters_involved
                )

                if common_chars and contract1.chapter == contract2.chapter:
                    return {
                        "locations": [contract1.location, contract2.location],
                        "characters": list(common_chars),
                        "reason": f"角色 {common_chars} 在同章节出现在不同地点",
                        "severity": "warning",
                    }

        return None

    def _generate_resolution_plan(
        self,
        conflicts: List[Dict[str, Any]],
        contracts: List[SceneContract],
    ) -> Dict[str, Any]:
        """生成冲突解决方案"""
        plan = {"actions": []}

        for conflict in conflicts:
            conflict_type = conflict["type"]

            if conflict_type == "character":
                # 角色冲突：建议统一角色状态
                char = conflict["detail"]["character"]
                plan["actions"].append(
                    {
                        "type": "update_character_state",
                        "character": char,
                        "suggestion": "统一角色状态，选择最合理的设定",
                    }
                )

            elif conflict_type == "timeline":
                # 时间冲突：建议调整时间线
                plan["actions"].append(
                    {
                        "type": "adjust_timeline",
                        "suggestion": "调整场景顺序或修改时间线描述",
                    }
                )

            elif conflict_type == "geography":
                # 地理冲突：建议添加转移描写
                chars = conflict["detail"]["characters"]
                plan["actions"].append(
                    {
                        "type": "add_transition",
                        "characters": chars,
                        "suggestion": f"为角色 {chars} 添加地点转移描写",
                    }
                )

        return plan

    def _save_contract(self, contract: SceneContract) -> None:
        """保存契约"""
        contract_file = self.storage_dir / f"{contract.contract_id}.json"

        # 转换 information_state 的 Set 为 List（JSON兼容）
        contract_dict = asdict(contract)
        if contract_dict.get("information_state"):
            for key, value in contract_dict["information_state"].items():
                if isinstance(value, set):
                    contract_dict["information_state"][key] = list(value)

        with open(contract_file, "w", encoding="utf-8") as f:
            json.dump(contract_dict, f, ensure_ascii=False, indent=2)

    def _load_contract(self, scene_id: str) -> Optional[SceneContract]:
        """加载契约"""
        index = self._load_index()

        # 查找契约ID
        contract_id = index.get("active_contracts", {}).get(scene_id)
        if not contract_id:
            return None

        contract_file = self.storage_dir / f"{contract_id}.json"
        if not contract_file.exists():
            return None

        with open(contract_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 恢复 information_state 的 List 为 Set
        if data.get("information_state"):
            for key, value in data["information_state"].items():
                if isinstance(value, list):
                    data["information_state"][key] = set(value)

        # 恢复 rules
        rules = []
        for rule_data in data.get("rules", []):
            rule = ContractRule(
                rule_type=ConsistencyRule(rule_data["rule_type"]),
                constraint=rule_data["constraint"],
                description=rule_data.get("description"),
                priority=rule_data.get("priority", 1),
            )
            rules.append(rule)

        return SceneContract(
            contract_id=data["contract_id"],
            scene_id=data["scene_id"],
            chapter=data["chapter"],
            scene_type=data["scene_type"],
            writer=data["writer"],
            rules=rules,
            characters_involved=data.get("characters_involved", []),
            character_states=data.get("character_states", {}),
            timeline_position=data.get("timeline_position"),
            time_constraints=data.get("time_constraints", {}),
            power_constraints=data.get("power_constraints", {}),
            location=data.get("location"),
            geography_constraints=data.get("geography_constraints", {}),
            information_state=data.get("information_state", {}),
            resource_state=data.get("resource_state", {}),
            foreshadows_active=data.get("foreshadows_active", []),
            foreshadows_to_resolve=data.get("foreshadows_to_resolve", []),
            promises_active=data.get("promises_active", []),
            style_constraints=data.get("style_constraints", {}),
            terminology=data.get("terminology", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_validated=data.get("is_validated", False),
            violations=data.get("violations", []),
        )

    def _update_index(self, contract: SceneContract) -> None:
        """更新契约索引"""
        index = self._load_index()

        # 添加到契约列表
        index["contracts"].append(contract.contract_id)

        # 更新活动契约映射
        index["active_contracts"][contract.scene_id] = contract.contract_id

        self._save_index(index)

    def complete_contract(self, scene_id: str) -> bool:
        """
        完成契约（场景创作完成）

        Args:
            scene_id: 场景ID

        Returns:
            是否成功
        """
        index = self._load_index()

        contract_id = index.get("active_contracts", {}).get(scene_id)
        if not contract_id:
            return False

        # 移动到已解决列表
        index["active_contracts"].pop(scene_id, None)
        index["resolved_contracts"].append(contract_id)

        self._save_index(index)

        return True

    def get_contract(self, scene_id: str) -> Optional[SceneContract]:
        """
        获取场景契约

        Args:
            scene_id: 场景ID

        Returns:
            契约对象
        """
        return self._load_contract(scene_id)

    def list_active_contracts(self) -> List[SceneContract]:
        """
        列出所有活动契约

        Returns:
            契约列表
        """
        index = self._load_index()
        contracts = []

        for scene_id in index.get("active_contracts", {}).keys():
            contract = self._load_contract(scene_id)
            if contract:
                contracts.append(contract)

        return contracts


# 便捷函数
def get_contract_lifecycle(project_root: Optional[Path] = None) -> ContractLifecycle:
    """获取契约生命周期管理实例"""
    return ContractLifecycle(project_root)
