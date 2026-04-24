# -*- coding: utf-8 -*-
"""
场景契约系统 - 一致性校验规则

功能：
1. 定义12大一致性校验规则
2. 提供自动冲突检测
3. 提供自动修复建议

规则分类：
- Critical（必须修复）: R001-G, R002, R004, R005-Q, R006, R007, R008, R009
- Warning（建议修复）: R001-T, R003, R005-S, R010, R011, R012

作者: Sisyphus
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .scene_contract import SceneContract, ConsistencyConflict, ConflictLevel
from core.config_loader import get_realm_order, get_skip_rules


class ConsistencyRules:
    """一致性校验规则集"""

    # ==================== 规则1：人物数量一致性 ====================

    @staticmethod
    def check_character_count_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R001：人物数量一致性

        场景A的数量必须与场景B的数量一致（针对同一群体）

        检查项：
        1. 总人数
        2. 各分组人数
        """
        conflicts = []

        count_a = contract_a.character_manifest["count"]
        count_b = contract_b.character_manifest["count"]

        # 检查总数
        if count_a.get("total", 0) != count_b.get("total", 0):
            conflicts.append(
                ConsistencyConflict(
                    rule_id="R001-T",
                    level=ConflictLevel.WARNING.value,  # 总数可能因场景不同而变化
                    message=f"人物总数不一致",
                    scene_a=contract_a.scene_id,
                    scene_b=contract_b.scene_id,
                    field="character_manifest.count.total",
                    value_a=count_a.get("total", 0),
                    value_b=count_b.get("total", 0),
                    suggestion=f"检查是否有人物离开/死亡，如有需在契约中标注",
                )
            )

        # 检查分组
        groups_a = {g["id"]: g for g in contract_a.character_manifest["groups"]}
        groups_b = {g["id"]: g for g in contract_b.character_manifest["groups"]}

        for group_id in set(groups_a.keys()) & set(groups_b.keys()):
            if groups_a[group_id]["count"] != groups_b[group_id]["count"]:
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R001-G",
                        level=ConflictLevel.CRITICAL.value,
                        message=f"分组[{groups_a[group_id]['description']}]人数不一致",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field=f"character_manifest.groups.{group_id}.count",
                        value_a=groups_a[group_id]["count"],
                        value_b=groups_b[group_id]["count"],
                        suggestion=f"统一为: {max(groups_a[group_id]['count'], groups_b[group_id]['count'])}人，或标注状态变化",
                    )
                )

        return conflicts

    # ==================== 规则2：时间因果性 ====================

    @staticmethod
    def check_timeline_causality(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R002：时间因果性

        事件必须在原因之后发生

        检查项：
        1. 阻塞事件是否完成
        2. 因果链是否完整
        """
        conflicts = []

        # 检查阻塞事件
        blocking_events = contract_a.dependencies.get("blocking_events", [])

        for blocking in blocking_events:
            event = blocking.get("event")
            must_complete_before = blocking.get("must_complete_before", [])

            # 检查场景B是否在等待场景A的事件
            if contract_b.scene_id in must_complete_before:
                # 查找事件状态
                event_status = None
                for e in contract_a.timeline.get("causal_chain", []):
                    if e.get("event") == event:
                        event_status = e.get("status")
                        break

                if event_status != "completed":
                    conflicts.append(
                        ConsistencyConflict(
                            rule_id="R002-B",
                            level=ConflictLevel.CRITICAL.value,
                            message=f"时间因果错误：[{event}]未完成，但场景已开始",
                            scene_a=contract_a.scene_id,
                            scene_b=contract_b.scene_id,
                            field="timeline.causal_chain",
                            value_a=f"{event}: {event_status}",
                            value_b=f"场景{contract_b.scene_id}已开始",
                            suggestion=f"确保[{event}]状态为completed后再开始场景{contract_b.scene_id}",
                        )
                    )

        return conflicts

    # ==================== 规则3：空间连续性 ====================

    @staticmethod
    def check_spatial_continuity(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R003：空间连续性

        场景转换必须经过必经路径

        检查项：
        1. 移动路径是否连续
        2. 空间跳转是否合理
        """
        conflicts = []

        path_a = contract_a.spatial.get("movement_path", [])
        path_b = contract_b.spatial.get("movement_path", [])

        if not path_a or not path_b:
            return conflicts

        # 检查场景B的起点是否与场景A的终点匹配
        end_a = path_a[-1] if path_a else None
        start_b = path_b[0] if path_b else None

        if end_a and start_b and end_a != start_b:
            conflicts.append(
                ConsistencyConflict(
                    rule_id="R003-P",
                    level=ConflictLevel.WARNING.value,
                    message=f"空间不连续：场景A终点({end_a}) ≠ 场景B起点({start_b})",
                    scene_a=contract_a.scene_id,
                    scene_b=contract_b.scene_id,
                    field="spatial.movement_path",
                    value_a=end_a,
                    value_b=start_b,
                    suggestion=f"添加过渡路径: {end_a} → {start_b}",
                )
            )

        return conflicts

    # ==================== 规则4：代词一致性 ====================

    @staticmethod
    def check_pronoun_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R004：代词一致性

        同一角色必须使用相同代词

        检查项：
        1. 命名角色的代词
        2. 性别与代词匹配
        """
        conflicts = []

        chars_a = {
            c["id"]: c
            for c in contract_a.character_manifest.get("named_characters", [])
        }
        chars_b = {
            c["id"]: c
            for c in contract_b.character_manifest.get("named_characters", [])
        }

        for char_id in set(chars_a.keys()) & set(chars_b.keys()):
            char_a = chars_a[char_id]
            char_b = chars_b[char_id]

            # 检查代词
            pronoun_a = char_a.get("pronoun")
            pronoun_b = char_b.get("pronoun")

            if pronoun_a and pronoun_b and pronoun_a != pronoun_b:
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R004-P",
                        level=ConflictLevel.CRITICAL.value,
                        message=f"角色[{char_a.get('name', char_id)}]代词不一致",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field=f"character_manifest.named_characters.{char_id}.pronoun",
                        value_a=pronoun_a,
                        value_b=pronoun_b,
                        suggestion=f"统一使用代词: {pronoun_a}",
                    )
                )

            # 检查性别
            gender_a = char_a.get("gender")
            gender_b = char_b.get("gender")

            if gender_a and gender_b and gender_a != gender_b:
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R004-G",
                        level=ConflictLevel.CRITICAL.value,
                        message=f"角色[{char_a.get('name', char_id)}]性别不一致",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field=f"character_manifest.named_characters.{char_id}.gender",
                        value_a=gender_a,
                        value_b=gender_b,
                        suggestion=f"统一性别为: {gender_a}",
                    )
                )

        return conflicts

    # ==================== 规则5：物体状态连续性 ====================

    @staticmethod
    def check_object_state_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R005：物体状态连续性

        物体状态必须在场景间保持一致

        检查项：
        1. 数量一致性
        2. 状态转换合理性
        """
        conflicts = []

        objs_a = {o["id"]: o for o in contract_a.object_states.get("objects", [])}
        objs_b = {o["id"]: o for o in contract_b.object_states.get("objects", [])}

        # 有效状态转换
        valid_transitions = {
            "intact": ["damaged", "broken", "dropped", "destroyed"],
            "dropped": ["picked_up", "moved", "used"],
            "hanging": ["dropped", "removed", "cut"],
            "alive": ["injured", "dead", "unconscious"],
            "dead": ["resurrected"],  # 特殊情况
            "hiding": ["emerging", "discovered", "escaped"],
        }

        for obj_id in set(objs_a.keys()) & set(objs_b.keys()):
            obj_a = objs_a[obj_id]
            obj_b = objs_b[obj_id]

            # 检查数量
            if obj_a.get("quantity") != obj_b.get("quantity"):
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R005-Q",
                        level=ConflictLevel.CRITICAL.value,
                        message=f"物体[{obj_a.get('name', obj_id)}]数量不一致",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field=f"object_states.objects.{obj_id}.quantity",
                        value_a=obj_a.get("quantity"),
                        value_b=obj_b.get("quantity"),
                        suggestion=f"统一数量为: {obj_a.get('quantity')}",
                    )
                )

            # 检查状态转换
            state_a = obj_a.get("state")
            state_b = obj_b.get("state")

            if state_a != state_b:
                valid_next = valid_transitions.get(state_a, [])
                if state_b not in valid_next:
                    conflicts.append(
                        ConsistencyConflict(
                            rule_id="R005-S",
                            level=ConflictLevel.WARNING.value,
                            message=f"物体[{obj_a.get('name', obj_id)}]状态转换不合理: {state_a} → {state_b}",
                            scene_a=contract_a.scene_id,
                            scene_b=contract_b.scene_id,
                            field=f"object_states.objects.{obj_id}.state",
                            value_a=state_a,
                            value_b=state_b,
                            suggestion=f"添加状态转换说明或调整为有效转换",
                        )
                    )

        return conflicts

    # ==================== 规则6：角色状态转换合理性 ====================

    @staticmethod
    def check_character_status_transition(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R006：角色状态转换合理性

        角色状态变化必须符合逻辑

        检查项：
        1. 死者不能复生（除非有特殊设定）
        2. 昏迷者不能主动行动
        """
        conflicts = []

        chars_a = {
            c["id"]: c
            for c in contract_a.character_manifest.get("named_characters", [])
        }
        chars_b = {
            c["id"]: c
            for c in contract_b.character_manifest.get("named_characters", [])
        }

        # 无效状态转换
        invalid_transitions = {
            "dead": ["alive", "fighting", "speaking", "running"],
            "unconscious": ["speaking", "fighting", "running"],
            "destroyed": ["intact", "working"],
        }

        for char_id in set(chars_a.keys()) & set(chars_b.keys()):
            char_a = chars_a[char_id]
            char_b = chars_b[char_id]

            status_a = char_a.get("status")
            status_b = char_b.get("status")

            if status_a != status_b:
                invalid_next = invalid_transitions.get(status_a, [])
                if status_b in invalid_next:
                    conflicts.append(
                        ConsistencyConflict(
                            rule_id="R006",
                            level=ConflictLevel.CRITICAL.value,
                            message=f"角色[{char_a.get('name', char_id)}]状态转换不合理: {status_a} → {status_b}",
                            scene_a=contract_a.scene_id,
                            scene_b=contract_b.scene_id,
                            field=f"character_manifest.named_characters.{char_id}.status",
                            value_a=status_a,
                            value_b=status_b,
                            suggestion=f"状态[{status_a}]不能转换为[{status_b}]，请调整",
                        )
                    )

        return conflicts

    # ==================== 规则7：势力攻击类型一致性 ====================

    @staticmethod
    def check_faction_attack_type_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R007：势力攻击类型一致性

        同一势力应该使用相同的攻击类型

        检查项：
        1. 修仙者使用飞剑
        2. 魔法师使用法术
        3. 科技战士使用脉冲武器
        4. 教廷骑士使用重剑
        """
        conflicts = []

        # 从依赖关系中提取势力信息
        factions_a = contract_a.dependencies.get("factions", {})
        factions_b = contract_b.dependencies.get("factions", {})

        if not factions_a or not factions_b:
            return conflicts

        # 标准攻击类型映射
        standard_attack_types = {
            "修仙者": ["飞剑", "剑气", "法术"],
            "魔法师": ["火球", "冰霜", "雷电", "法术"],
            "科技战士": ["脉冲", "激光", "电磁"],
            "教廷骑士": ["重剑", "圣光", "圣剑"],
            "机甲": ["炮火", "导弹", "激光"],
            "异能者": ["异能", "念力", "瞬移"],
        }

        # 检查同一势力的攻击类型是否一致
        for faction in set(factions_a.keys()) & set(factions_b.keys()):
            attack_a = factions_a[faction].get("attack_type")
            attack_b = factions_b[faction].get("attack_type")

            if attack_a and attack_b and attack_a != attack_b:
                # 检查是否都属于该势力的标准攻击类型
                valid_types = standard_attack_types.get(faction, [])
                if attack_a in valid_types and attack_b not in valid_types:
                    conflicts.append(
                        ConsistencyConflict(
                            rule_id="R007",
                            level=ConflictLevel.CRITICAL.value,
                            message=f"势力[{faction}]攻击类型不一致",
                            scene_a=contract_a.scene_id,
                            scene_b=contract_b.scene_id,
                            field=f"dependencies.factions.{faction}.attack_type",
                            value_a=attack_a,
                            value_b=attack_b,
                            suggestion=f"{faction}应使用标准攻击类型: {valid_types}",
                        )
                    )

        return conflicts

    # ==================== 规则8：天气环境一致性 ====================

    @staticmethod
    def check_weather_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R008：天气环境一致性

        同一时间段同一地点的天气应该一致

        检查项：
        1. 天气状态（晴/雨/雪）
        2. 光线条件（晨曦/正午/黄昏/夜晚）
        3. 温度描述
        """
        conflicts = []

        # 检查时间是否重叠
        time_a = contract_a.timeline.get("relative_time", {})
        time_b = contract_b.timeline.get("relative_time", {})

        # 如果时间不重叠，跳过检查
        if not _times_overlap(time_a, time_b):
            return conflicts

        # 检查空间是否重叠
        spatial_a = contract_a.spatial.get("location", {})
        spatial_b = contract_b.spatial.get("location", {})

        # 如果空间不重叠，跳过检查
        if spatial_a.get("name") != spatial_b.get("name"):
            return conflicts

        # 检查天气
        weather_a = contract_a.metadata.get("weather", {})
        weather_b = contract_b.metadata.get("weather", {})

        if weather_a and weather_b:
            # 检查天气状态
            state_a = weather_a.get("state")
            state_b = weather_b.get("state")

            if state_a and state_b and state_a != state_b:
                # 某些天气可以共存
                compatible_weather = {
                    "晴": ["晴", "多云"],
                    "多云": ["多云", "晴", "阴"],
                    "阴": ["阴", "多云"],
                    "雨": ["雨", "暴雨"],
                    "雪": ["雪", "暴雪"],
                }

                if state_b not in compatible_weather.get(state_a, [state_a]):
                    conflicts.append(
                        ConsistencyConflict(
                            rule_id="R008-W",
                            level=ConflictLevel.WARNING.value,
                            message=f"同一时间地点天气不一致: {state_a} vs {state_b}",
                            scene_a=contract_a.scene_id,
                            scene_b=contract_b.scene_id,
                            field="metadata.weather.state",
                            value_a=state_a,
                            value_b=state_b,
                            suggestion=f"统一天气状态",
                        )
                    )

        return conflicts

    # ==================== 规则9：角色特征一致性 ====================

    @staticmethod
    def check_character_trait_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R009：角色特征一致性

        同一角色的外貌特征应该一致

        检查项：
        1. 疤痕、纹身等显著特征
        2. 年龄描述
        3. 身高体型
        """
        conflicts = []

        chars_a = {
            c["id"]: c
            for c in contract_a.character_manifest.get("named_characters", [])
        }
        chars_b = {
            c["id"]: c
            for c in contract_b.character_manifest.get("named_characters", [])
        }

        for char_id in set(chars_a.keys()) & set(chars_b.keys()):
            char_a = chars_a[char_id]
            char_b = chars_b[char_id]

            # 检查特征
            traits_a = char_a.get("traits", {})
            traits_b = char_b.get("traits", {})

            if traits_a and traits_b:
                for trait_name in set(traits_a.keys()) & set(traits_b.keys()):
                    if traits_a[trait_name] != traits_b[trait_name]:
                        conflicts.append(
                            ConsistencyConflict(
                                rule_id="R009",
                                level=ConflictLevel.CRITICAL.value,
                                message=f"角色[{char_a.get('name', char_id)}]特征[{trait_name}]不一致",
                                scene_a=contract_a.scene_id,
                                scene_b=contract_b.scene_id,
                                field=f"character_manifest.named_characters.{char_id}.traits.{trait_name}",
                                value_a=traits_a[trait_name],
                                value_b=traits_b[trait_name],
                                suggestion=f"统一特征描述",
                            )
                        )

        return conflicts

    # ==================== 规则10：称呼一致性 ====================

    @staticmethod
    def check_appellation_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R010：称呼一致性

        同一角色应该使用相同的称呼

        检查项：
        1. 名字
        2. 代称
        3. 头衔
        """
        conflicts = []

        chars_a = {
            c["id"]: c
            for c in contract_a.character_manifest.get("named_characters", [])
        }
        chars_b = {
            c["id"]: c
            for c in contract_b.character_manifest.get("named_characters", [])
        }

        for char_id in set(chars_a.keys()) & set(chars_b.keys()):
            char_a = chars_a[char_id]
            char_b = chars_b[char_id]

            # 检查名字
            name_a = char_a.get("name")
            name_b = char_b.get("name")

            if name_a and name_b and name_a != name_b:
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R010-N",
                        level=ConflictLevel.WARNING.value,
                        message=f"角色称呼不一致: {name_a} vs {name_b}",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field=f"character_manifest.named_characters.{char_id}.name",
                        value_a=name_a,
                        value_b=name_b,
                        suggestion=f"统一称呼为: {name_a}",
                    )
                )

        return conflicts

    # ==================== 规则11：势力构成一致性 ====================

    @staticmethod
    def check_faction_composition_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R011：势力构成一致性

        同一势力的成员构成应该一致

        检查项：
        1. 势力类型列表
        2. 各类型数量
        """
        conflicts = []

        factions_a = contract_a.dependencies.get("factions", {})
        factions_b = contract_b.dependencies.get("factions", {})

        if not factions_a or not factions_b:
            return conflicts

        # 检查势力类型是否一致
        types_a = set(factions_a.keys())
        types_b = set(factions_b.keys())

        # 如果是同一场景序列，势力类型应该一致
        if contract_b.scene_id in contract_a.dependencies.get("post_scenes", []):
            missing_types = types_a - types_b
            if missing_types:
                conflicts.append(
                    ConsistencyConflict(
                        rule_id="R011-T",
                        level=ConflictLevel.WARNING.value,
                        message=f"势力构成不一致，缺少: {missing_types}",
                        scene_a=contract_a.scene_id,
                        scene_b=contract_b.scene_id,
                        field="dependencies.factions",
                        value_a=list(types_a),
                        value_b=list(types_b),
                        suggestion=f"确保势力构成一致",
                    )
                )

        return conflicts

    # ==================== 规则12：能力技能一致性 ====================

    @staticmethod
    def check_ability_consistency(
        contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        规则R012：能力技能一致性

        角色的能力使用应该符合设定

        检查项：
        1. 血脉能力
        2. 修炼境界
        3. 技能等级
        """
        conflicts = []

        chars_a = {
            c["id"]: c
            for c in contract_a.character_manifest.get("named_characters", [])
        }
        chars_b = {
            c["id"]: c
            for c in contract_b.character_manifest.get("named_characters", [])
        }

        for char_id in set(chars_a.keys()) & set(chars_b.keys()):
            char_a = chars_a[char_id]
            char_b = chars_b[char_id]

            abilities_a = char_a.get("abilities", {})
            abilities_b = char_b.get("abilities", {})

            if abilities_a and abilities_b:
                # 检查境界是否倒退
                realm_a = abilities_a.get("realm")
                realm_b = abilities_b.get("realm")

                if realm_a and realm_b:
                    # 从配置获取境界等级顺序
                    realm_order = get_realm_order()

                    # 如果配置为null，跳过境界检测
                    if realm_order is None:
                        return conflicts

                    try:
                        level_a = realm_order.index(realm_a)
                        level_b = realm_order.index(realm_b)

                        if level_b < level_a:
                            conflicts.append(
                                ConsistencyConflict(
                                    rule_id="R012-R",
                                    level=ConflictLevel.CRITICAL.value,
                                    message=f"角色[{char_a.get('name', char_id)}]境界倒退: {realm_a} → {realm_b}",
                                    scene_a=contract_a.scene_id,
                                    scene_b=contract_b.scene_id,
                                    field=f"character_manifest.named_characters.{char_id}.abilities.realm",
                                    value_a=realm_a,
                                    value_b=realm_b,
                                    suggestion=f"境界不能倒退，请调整",
                                )
                            )
                    except ValueError:
                        pass  # 自定义境界名，跳过检查

        return conflicts


# ==================== 辅助函数 ====================


def _times_overlap(time_a: Dict, time_b: Dict) -> bool:
    """检查两个时间范围是否重叠"""
    import re

    def parse_time(time_str: str) -> int:
        """将时间字符串转换为分钟数"""
        if not time_str:
            return 0

        # 解析 T+XXmin 格式
        match = re.match(r"T\+(\d+)(min|h)?", time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2) or "min"
            return value * (60 if unit == "h" else 1)

        return 0

    start_a = parse_time(time_a.get("start", "T+0"))
    end_a = parse_time(time_a.get("end", "T+999"))
    start_b = parse_time(time_b.get("start", "T+0"))
    end_b = parse_time(time_b.get("end", "T+999"))

    return start_a < end_b and start_b < end_a


class ContractValidator:
    """契约校验器"""

    def __init__(self):
        self.rules = [
            ("R001", ConsistencyRules.check_character_count_consistency),
            ("R002", ConsistencyRules.check_timeline_causality),
            ("R003", ConsistencyRules.check_spatial_continuity),
            ("R004", ConsistencyRules.check_pronoun_consistency),
            ("R005", ConsistencyRules.check_object_state_consistency),
            ("R006", ConsistencyRules.check_character_status_transition),
            # 新增规则
            ("R007", ConsistencyRules.check_faction_attack_type_consistency),
            ("R008", ConsistencyRules.check_weather_consistency),
            ("R009", ConsistencyRules.check_character_trait_consistency),
            ("R010", ConsistencyRules.check_appellation_consistency),
            ("R011", ConsistencyRules.check_faction_composition_consistency),
            ("R012", ConsistencyRules.check_ability_consistency),
        ]

    def validate_contracts(
        self, contracts: List[SceneContract], scene_order: Optional[List[str]] = None
    ) -> List[ConsistencyConflict]:
        """
        校验所有场景契约的一致性

        Args:
            contracts: 契约列表
            scene_order: 场景执行顺序（可选，用于确定依赖关系）

        Returns:
            冲突列表
        """
        conflicts = []

        # 建立契约映射
        contract_map = {c.scene_id: c for c in contracts}

        # 确定校验顺序
        if scene_order:
            order = scene_order
        else:
            order = list(contract_map.keys())

        # 两两校验相邻场景
        for i in range(len(order) - 1):
            scene_a_id = order[i]
            scene_b_id = order[i + 1]

            contract_a = contract_map.get(scene_a_id)
            contract_b = contract_map.get(scene_b_id)

            if not contract_a or not contract_b:
                continue

            # 执行所有校验规则
            for rule_id, rule_func in self.rules:
                rule_conflicts = rule_func(contract_a, contract_b)
                conflicts.extend(rule_conflicts)

        return conflicts

    def validate_contract_pair(
        self, contract_a: SceneContract, contract_b: SceneContract
    ) -> List[ConsistencyConflict]:
        """
        校验两个契约之间的一致性

        Args:
            contract_a: 契约A
            contract_b: 契约B

        Returns:
            冲突列表
        """
        conflicts = []

        for rule_id, rule_func in self.rules:
            rule_conflicts = rule_func(contract_a, contract_b)
            conflicts.extend(rule_conflicts)

        return conflicts

    def get_critical_conflicts(
        self, conflicts: List[ConsistencyConflict]
    ) -> List[ConsistencyConflict]:
        """获取关键冲突"""
        return [c for c in conflicts if c.level == ConflictLevel.CRITICAL.value]

    def get_warning_conflicts(
        self, conflicts: List[ConsistencyConflict]
    ) -> List[ConsistencyConflict]:
        """获取警告冲突"""
        return [c for c in conflicts if c.level == ConflictLevel.WARNING.value]

    def has_critical_conflicts(self, conflicts: List[ConsistencyConflict]) -> bool:
        """是否有关键冲突"""
        return len(self.get_critical_conflicts(conflicts)) > 0


class ConflictResolver:
    """冲突解决器"""

    @staticmethod
    def auto_resolve(conflict: ConsistencyConflict) -> Optional[Dict]:
        """
        自动解决冲突

        Args:
            conflict: 冲突对象

        Returns:
            解决方案，如果无法自动解决返回None
        """
        # R001: 数量不一致 → 取最大值（需确认）
        if conflict.rule_id == "R001-G":
            return {
                "resolution": "auto",
                "action": "suggest",
                "field": conflict.field,
                "suggested_value": max(conflict.value_a, conflict.value_b),
                "reason": "取较大值作为标准，或确认状态变化",
            }

        # R004: 代词不一致 → 取先出现的
        if conflict.rule_id == "R004-P":
            return {
                "resolution": "auto",
                "action": "update",
                "field": conflict.field,
                "new_value": conflict.value_a,
                "reason": "以先出现的场景为准",
            }

        # R004: 性别不一致 → 取先出现的
        if conflict.rule_id == "R004-G":
            return {
                "resolution": "auto",
                "action": "update",
                "field": conflict.field,
                "new_value": conflict.value_a,
                "reason": "以先出现的场景为准",
            }

        # R005: 物体数量不一致 → 取具体数值
        if conflict.rule_id == "R005-Q":
            # 如果一个是具体数字，一个是模糊数字，取具体数字
            if isinstance(conflict.value_a, int) and isinstance(conflict.value_b, int):
                return {
                    "resolution": "auto",
                    "action": "suggest",
                    "field": conflict.field,
                    "suggested_value": conflict.value_a,
                    "reason": "取先出现的具体数值",
                }

        # R007: 势力攻击类型不一致 → 使用标准类型
        if conflict.rule_id == "R007":
            return {
                "resolution": "auto",
                "action": "update",
                "field": conflict.field,
                "new_value": conflict.value_a,
                "reason": "以先出现的标准攻击类型为准",
            }

        # R008: 天气不一致 → 需要人工确认
        if conflict.rule_id == "R008-W":
            return {
                "resolution": "auto",
                "action": "suggest",
                "field": conflict.field,
                "suggested_value": conflict.value_a,
                "reason": "建议统一为较早场景的天气描述，或确认天气变化原因",
            }

        # R009: 角色特征不一致 → 以先出现的为准
        if conflict.rule_id == "R009":
            return {
                "resolution": "auto",
                "action": "update",
                "field": conflict.field,
                "new_value": conflict.value_a,
                "reason": "以先出现的角色特征描述为准",
            }

        # R010: 称呼不一致 → 以正式名字为准
        if conflict.rule_id == "R010-N":
            return {
                "resolution": "auto",
                "action": "update",
                "field": conflict.field,
                "new_value": conflict.value_a,
                "reason": "统一使用先出现的称呼",
            }

        # R011: 势力构成不一致 → 补充缺失类型
        if conflict.rule_id == "R011-T":
            return {
                "resolution": "auto",
                "action": "suggest",
                "field": conflict.field,
                "suggested_value": conflict.value_a,
                "reason": "建议补充缺失的势力类型以保持一致",
            }

        # R012: 能力/境界倒退 → 需要人工确认
        if conflict.rule_id == "R012-R":
            return {
                "resolution": "manual",
                "action": "confirm",
                "field": conflict.field,
                "reason": "境界倒退需要人工确认是否有特殊原因（如封印、转世等）",
            }

        # 无法自动解决
        return None

    @staticmethod
    def request_human_intervention(conflict: ConsistencyConflict) -> Dict:
        """
        请求人工介入

        Args:
            conflict: 冲突对象

        Returns:
            人工介入请求
        """
        return {
            "resolution": "manual",
            "conflict": conflict.to_dict(),
            "options": [
                {"value": conflict.value_a, "source": f"场景{conflict.scene_a}"},
                {"value": conflict.value_b, "source": f"场景{conflict.scene_b}"},
                {"value": "custom", "source": "自定义"},
            ],
            "suggestion": conflict.suggestion,
        }

    @staticmethod
    def resolve(conflict: ConsistencyConflict) -> Dict:
        """
        解决冲突

        Args:
            conflict: 冲突对象

        Returns:
            解决方案
        """
        # 尝试自动解决
        auto_solution = ConflictResolver.auto_resolve(conflict)
        if auto_solution:
            return auto_solution

        # 无法自动解决，请求人工介入
        return ConflictResolver.request_human_intervention(conflict)


# 导出
__all__ = ["ConsistencyRules", "ContractValidator", "ConflictResolver"]
