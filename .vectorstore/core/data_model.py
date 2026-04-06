#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界知识图谱数据模型
定义所有实体的属性结构，确保数据完整性
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class EntityType(Enum):
    """实体类型枚举"""

    势力 = "势力"
    角色 = "角色"
    事件 = "事件"
    时代 = "时代"
    力量体系 = "力量体系"
    派系 = "派系"
    组织 = "组织"
    技法 = "技法"
    地点 = "地点"


# ==================== 势力详细属性 ====================


@dataclass
class PoliticalStructure:
    """政治结构"""

    最高决策: str = ""
    重大决策: str = ""
    部门管理: str = ""
    执行层: str = ""


@dataclass
class FactionInfo:
    """势力完整信息"""

    id: str
    名称: str
    核心力量: str = ""
    核心利益: str = ""
    不可替代性: str = ""

    # ★ 关联的力量体系（势力 → 力量体系）
    力量体系: str = ""  # 如：东方修仙 → 修仙

    # 政治结构
    政治结构: PoliticalStructure = field(default_factory=PoliticalStructure)

    # 派系政治
    派系: List[Dict] = field(default_factory=list)  # [{名称, 代表, 主张}]

    # 经济结构
    经济结构: Dict[str, str] = field(default_factory=dict)  # {资源类型: 描述}

    # 文化结构
    文化结构: List[str] = field(default_factory=list)  # [文化特点]

    # 建筑风格
    建筑风格: str = ""
    核心建筑: str = ""
    建筑特点: str = ""

    # AI入侵相关
    灵魂保护法门: str = ""
    保护法门原理: str = ""
    保护法门弱点: str = ""

    # 人才输出
    人才输出: Dict[str, str] = field(default_factory=dict)  # {目标势力: 人才类型}


# ==================== 角色详细属性 ====================


@dataclass
class RacialTraits:
    """种族特征"""

    外貌特征: List[str] = field(default_factory=list)
    心理特征: List[str] = field(default_factory=list)
    行为特征: List[str] = field(default_factory=list)


@dataclass
class CharacterInfo:
    """角色完整信息"""

    id: str
    名称: str
    势力: str = ""
    身份: str = ""
    入侵状态: str = ""
    力量体系: str = ""  # ★ 继承自势力的力量体系

    # ★ 个人能力（力量体系的子集）
    功法: List[str] = field(default_factory=list)  # 角色特有的功法
    技能: List[str] = field(default_factory=list)  # 角色特有的技能
    特殊能力: List[str] = field(default_factory=list)  # 角色特有的能力

    # 详细设定
    年龄: str = ""
    种族: str = ""
    所属组织: str = ""

    # 种族特征
    种族特征: RacialTraits = field(default_factory=RacialTraits)

    # 关系
    感情关系: List[Dict] = field(default_factory=list)
    仇恨关系: List[str] = field(default_factory=list)
    盟友关系: List[str] = field(default_factory=list)

    # 剧情线
    登场时代: List[str] = field(default_factory=list)
    退场时代: str = ""
    涉及事件: List[str] = field(default_factory=list)

    # 角色弧
    角色弧类型: str = ""  # 成长/悲剧/救赎/堕落
    核心冲突: str = ""
    主题承载: str = ""  # 承载什么主题


# ==================== 力量体系 ====================


@dataclass
class PowerCost:
    """力量代价"""

    使用者: str = ""
    应有代价: str = ""
    表现形式: str = ""


@dataclass
class PowerSystemInfo:
    """力量体系完整信息"""

    id: str
    名称: str
    力量来源: str = ""
    修炼方式: str = ""
    战斗特点: str = ""

    # 代价机制
    基础代价: PowerCost = field(default_factory=PowerCost)
    特殊技法: List[Dict] = field(default_factory=list)  # [{技法名, 代价, 表现}]

    # ★ 关联势力（力量体系 → 势力）
    主要势力: List[str] = field(default_factory=list)

    # ★ 技能/功法列表（角色从中选择）
    功法列表: List[str] = field(default_factory=list)
    技能列表: List[str] = field(default_factory=list)


# ==================== 时代 ====================


@dataclass
class EraFactionStatus:
    """时代势力状态"""

    势力: str
    状态: str = ""
    关键变化: str = ""


@dataclass
class EraInfo:
    """时代完整信息"""

    id: str
    名称: str
    时间跨度: str = ""  # 如 "第1-10年"
    时代特点: str = ""
    核心事件: List[str] = field(default_factory=list)

    # 氛围设定
    核心氛围: str = ""
    色调: str = ""
    季节感: str = ""
    代表意象: str = ""

    # 势力状态
    势力状态: List[EraFactionStatus] = field(default_factory=list)

    # 角色
    登场主角: List[str] = field(default_factory=list)
    退场主角: List[str] = field(default_factory=list)


# ==================== 事件 ====================


@dataclass
class EventInfo:
    """事件完整信息"""

    id: str
    名称: str
    类型: str = ""  # 战争/悲剧/转折/日常
    时代: str = ""

    # 事件详情
    概述: str = ""
    目的: List[str] = field(default_factory=list)
    规模: str = ""
    结果: str = ""

    # 涉及角色
    涉及角色: List[str] = field(default_factory=list)
    涉及势力: List[str] = field(default_factory=list)

    # 影响
    影响格局: str = ""
    后续事件: List[str] = field(default_factory=list)


# ==================== 派系 ====================


@dataclass
class FactionBranchInfo:
    """势力派系信息"""

    id: str
    名称: str
    所属势力: str
    代表组织: str = ""
    主张: str = ""
    特点: str = ""

    # 关系
    与其他派系关系: Dict[str, str] = field(default_factory=dict)


# ==================== 感情关系 ====================


@dataclass
class RomanceInfo:
    """感情关系"""

    角色1: str
    势力1: str
    角色2: str
    势力2: str
    关系类型: str = "双向"  # 双向/单向/三角
    核心矛盾: str = ""
    结局: str = ""

    # 详细阶段
    阶段发展: List[Dict] = field(default_factory=list)


# ==================== 知识图谱整体结构 ====================


@dataclass
class KnowledgeGraph:
    """知识图谱完整结构"""

    实体: Dict[str, Dict] = field(default_factory=dict)
    关系: List[Dict] = field(default_factory=list)

    # 统计
    实体统计: Dict[str, int] = field(default_factory=dict)
    关系统计: Dict[str, int] = field(default_factory=dict)

    # 元数据
    版本: str = "2.0"
    更新时间: str = ""
    数据来源: List[str] = field(default_factory=list)


# ==================== 数据模型验证 ====================


def validate_entity(entity: Dict, entity_type: EntityType) -> List[str]:
    """验证实体数据完整性，返回缺失字段列表"""
    missing = []

    required_fields = {
        EntityType.势力: ["id", "名称", "核心力量"],
        EntityType.角色: ["id", "名称", "势力"],
        EntityType.事件: ["id", "名称", "时代"],
        EntityType.时代: ["id", "名称", "时间跨度"],
        EntityType.力量体系: ["id", "名称", "力量来源"],
    }

    for field in required_fields.get(entity_type, []):
        if field not in entity or not entity.get(field):
            missing.append(field)

    return missing


# ==================== 示例数据结构 ====================

EXAMPLE_FACTION = {
    "id": "faction_eastern_cultivation",
    "名称": "东方修仙",
    "核心力量": "灵力修仙",
    "核心利益": "灵脉控制权",
    "不可替代性": "唯一产出高阶丹药、法宝",
    "政治结构": {
        "最高决策": "宗主/掌门",
        "重大决策": "长老会",
        "部门管理": "门主/殿主",
        "执行层": "弟子",
    },
    "派系": [
        {"名称": "正道联盟", "代表": "玄天宗、剑灵山", "主张": "维护秩序，对抗西方"},
        {"名称": "隐世宗门", "代表": "星罗阁、丹霞谷", "主张": "不问世事，专注修炼"},
        {"名称": "旁门左道", "代表": "血煞门、鬼谷", "主张": "不择手段追求力量"},
        {"名称": "散修联盟", "代表": "无固定宗门", "主张": "自由修行，不站队"},
    ],
    "经济结构": {
        "灵脉资源": "核心资源，宗门控制",
        "丹药产业": "丹霞谷垄断",
        "法宝产业": "炼器宗门垄断",
        "灵石贸易": "商盟介入",
    },
    "建筑风格": "仙山楼阁",
    "核心建筑": "宗门主殿、剑阁、丹阁",
    "建筑特点": "山巅建筑、飞檐斗拱、云雾缭绕",
    "灵魂保护法门": "神识封印",
    "保护法门原理": "修炼神识，形成精神屏障",
    "保护法门弱点": "境界不足者无效",
}

EXAMPLE_CHARACTER = {
    "id": "char_xueya",
    "名称": "血牙",
    "势力": "兽族文明",
    "身份": "青岩部落混血之民",
    "入侵状态": "未入侵",
    "力量体系": "兽力",
    "年龄": "约23岁（灭族时约10-13岁）",
    "种族": "兽族混血",
    "所属组织": "青岩部落",
    "种族特征": {
        "外貌特征": ["兽族混血外貌", "血脉觉醒后有兽纹"],
        "心理特征": ["血脉意识强", "复仇执念", "身份追问"],
        "行为特征": ["沉默寡言", "战斗本能", "血脉驱动"],
    },
    "感情关系": [{"对象": "花姬", "类型": "爱慕", "状态": "暗恋"}],
    "仇恨关系": ["佣兵联盟"],
    "登场时代": ["觉醒时代", "蛰伏时代", "风暴时代", "变革时代", "终局时代"],
    "涉及事件": ["觉醒之夜", "青岩部落灭族"],
    "角色弧类型": "复仇→救赎",
    "核心冲突": "身份认同与复仇",
    "主题承载": "「我是谁」身份追问",
}

EXAMPLE_POWER_SYSTEM = {
    "id": "power_beast",
    "名称": "兽力",
    "力量来源": "血脉觉醒",
    "修炼方式": "战斗吞噬",
    "战斗特点": "狂化、形态变化、血脉技",
    "基础代价": {
        "使用者": "兽族/异化人",
        "应有代价": "血脉燃烧、生命代价、理智丧失",
        "表现形式": "骨骼崩解、肌肉溶解、失去理智",
    },
    "特殊技法": [
        {"技法": "血脉觉醒", "代价": "基因不稳定", "表现": "身体开始异变"},
        {"技法": "血脉燃烧", "代价": "生命代价", "表现": "骨骼崩解、肌肉溶解"},
        {"技法": "血脉暴走", "代价": "失控+生命", "表现": "完全失去理智、身体崩溃"},
    ],
    "主要势力": ["兽族文明", "异化人文明"],
}

EXAMPLE_ERA = {
    "id": "era_awakening",
    "名称": "觉醒时代",
    "时间跨度": "第1-10年",
    "时代特点": "AI首次入侵、部落屠杀、血脉觉醒",
    "核心事件": ["觉醒之夜", "部落灭亡"],
    "核心氛围": "震惊、迷茫、愤怒、绝望",
    "色调": "血红、暗灰",
    "季节感": "寒冬",
    "代表意象": "屠杀、血、火",
    "势力状态": [
        {"势力": "东方修仙", "状态": "稳定", "关键变化": "开始研究AI防御"},
        {"势力": "AI文明", "状态": "崛起", "关键变化": "首次大规模入侵"},
    ],
    "登场主角": ["血牙", "林夕", "艾琳娜", "赵恒", "塞巴斯蒂安", "洛影", "苏瑾"],
    "退场主角": ["部分凡人角色"],
}


if __name__ == "__main__":
    print("数据模型定义完成")
    print(f"势力示例字段数: {len(EXAMPLE_FACTION)}")
    print(f"角色示例字段数: {len(EXAMPLE_CHARACTER)}")
    print(f"力量体系示例字段数: {len(EXAMPLE_POWER_SYSTEM)}")
    print(f"时代示例字段数: {len(EXAMPLE_ERA)}")
