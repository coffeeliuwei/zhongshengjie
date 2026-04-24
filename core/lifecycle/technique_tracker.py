"""
技法追踪器 - TechniqueTracker

追踪技法使用情况，分析效果评分，推荐合适技法。

功能：
- track_usage(): 追踪技法使用
- get_usage_stats(): 获取使用统计
- get_effectiveness_score(): 获取效果评分
- recommend_techniques(): 推荐技法

存储位置：.cache/technique_usage.json
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

# 尝试导入配置管理器
try:
    from core.config_loader import get_project_root

    _project_root = Path(get_project_root())
except ImportError:
    _project_root = Path(__file__).parent.parent.parent

PROJECT_ROOT = _project_root


@dataclass
class TechniqueUsage:
    """技法使用记录"""

    technique_id: str  # 技法ID
    context: Dict[str, Any]  # 使用上下文
    timestamp: str  # 使用时间
    scene_type: Optional[str] = None  # 场景类型
    writer: Optional[str] = None  # 使用作家
    chapter: Optional[int] = None  # 章节号
    effectiveness: Optional[float] = None  # 效果评分 (0-1)
    feedback: Optional[str] = None  # 用户反馈
    success: Optional[bool] = None  # 是否成功应用


@dataclass
class TechniqueStats:
    """技法统计信息"""

    technique_id: str
    total_usage: int = 0
    success_rate: float = 0.0
    avg_effectiveness: float = 0.0
    last_used: Optional[str] = None
    common_contexts: List[Dict[str, Any]] = field(default_factory=list)
    by_writer: Dict[str, int] = field(default_factory=dict)
    by_scene: Dict[str, int] = field(default_factory=dict)


class TechniqueTracker:
    """技法追踪器"""

    STORAGE_FILE = ".cache/technique_usage.json"

    # 技法维度分类 - 28种场景类型映射
    DIMENSIONS = {
        # 核心战斗类
        "战斗": ["节奏控制", "力量描写", "代价设计", "心理博弈"],
        "打脸": ["情绪反差", "铺垫设计", "震撼效果", "身份揭示"],
        "高潮": ["情绪引爆", "多线汇聚", "悬念揭晓", "震撼呈现"],
        # 人物情感类
        "人物出场": ["形象塑造", "气质刻画", "背景暗示", "神秘感营造"],
        "情感": ["情感弧线", "微表情", "内心独白", "情感转折"],
        "心理": ["心理刻画", "内心冲突", "动机揭示", "情绪变化"],
        "成长蜕变": ["能力提升", "心态转变", "认知突破", "身份跃迁"],
        # 悬念剧情类
        "悬念": ["信息withholding", "伏笔设计", "悬念布局", "反转策划"],
        "伏笔设置": ["细节植入", "线索铺垫", "暗示设计", "呼应预埋"],
        "伏笔回收": ["线索回收", "前呼后应", "震撼揭晓", "逻辑闭环"],
        "转折": ["转折设计", "意外性", "合理性", "情绪冲击"],
        "阴谋揭露": ["真相呈现", "阴谋拆解", "震撼反转", "权力斗争"],
        # 对话社交类
        "对话": ["对话风格", "潜台词", "语气节奏", "信息传递"],
        "社交": ["社交博弈", "关系构建", "权力展示", "利益交换"],
        # 世界观类
        "开篇": ["开篇钩子", "世界观植入", "人物引出", "悬念设置"],
        "势力登场": ["势力介绍", "实力展示", "立场暗示", "威胁营造"],
        "世界观": ["设定一致性", "体系构建", "规则呈现", "背景融合"],
        "环境": ["场景渲染", "环境描写", "氛围营造", "细节刻画"],
        # 修炼资源类
        "修炼突破": ["瓶颈刻画", "突破过程", "境界跃升", "力量蜕变"],
        "资源获取": ["资源描述", "争夺过程", "价值呈现", "用途暗示"],
        # 探索发现类
        "探索发现": ["探索过程", "环境描写", "未知揭示", "惊喜营造"],
        "情报揭示": ["情报呈现", "信息层次", "真相揭露", "误导设计"],
        # 其他类
        "危机降临": ["危机营造", "压迫感", "紧迫感", "生死威胁"],
        "冲突升级": ["矛盾激化", "张力提升", "局势变化", "压力累积"],
        "团队组建": ["成员招募", "能力互补", "信任建立", "团队磨合"],
        "反派出场": ["威胁感", "实力展示", "动机暗示", "对立营造"],
        "恢复休养": ["伤势恢复", "实力巩固", "关系缓和", "情报整理"],
        "回忆场景": ["回忆切入", "过去呈现", "情感触动", "信息补充"],
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化技法追踪器

        Args:
            project_root: 项目根目录，默认自动检测
        """
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.storage_path = self.project_root / self.STORAGE_FILE
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """确保存储文件存在"""
        if not self.storage_path.exists():
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_data({"usages": [], "stats": {}})

    def _load_data(self) -> Dict[str, Any]:
        """加载存储数据"""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"usages": [], "stats": {}}

    def _save_data(self, data: Dict[str, Any]) -> None:
        """保存存储数据"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def track_usage(
        self,
        technique_id: str,
        context: Dict[str, Any],
        scene_type: Optional[str] = None,
        writer: Optional[str] = None,
        chapter: Optional[int] = None,
        effectiveness: Optional[float] = None,
        feedback: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> str:
        """
        追踪技法使用

        Args:
            technique_id: 技法ID
            context: 使用上下文
            scene_type: 场景类型
            writer: 使用作家
            chapter: 章节号
            effectiveness: 效果评分 (0-1)
            feedback: 用户反馈
            success: 是否成功应用

        Returns:
            使用记录ID
        """
        # 创建使用记录
        usage = TechniqueUsage(
            technique_id=technique_id,
            context=context,
            timestamp=datetime.now().isoformat(),
            scene_type=scene_type,
            writer=writer,
            chapter=chapter,
            effectiveness=effectiveness,
            feedback=feedback,
            success=success,
        )

        # 生成记录ID
        usage_id = hashlib.md5(
            f"{technique_id}_{usage.timestamp}".encode()
        ).hexdigest()[:12]

        # 加载并更新数据
        data = self._load_data()
        data["usages"].append({"id": usage_id, **asdict(usage)})

        # 更新统计
        self._update_stats(data, technique_id, usage)

        # 保存
        self._save_data(data)

        return usage_id

    def _update_stats(
        self, data: Dict[str, Any], technique_id: str, usage: TechniqueUsage
    ) -> None:
        """更新技法统计"""
        stats = data["stats"]

        if technique_id not in stats:
            stats[technique_id] = {
                "technique_id": technique_id,
                "total_usage": 0,
                "success_count": 0,
                "effectiveness_sum": 0.0,
                "last_used": None,
                "by_writer": {},
                "by_scene": {},
                "contexts": [],
            }

        stat = stats[technique_id]
        stat["total_usage"] += 1

        # 更新成功率
        if usage.success is not None:
            if usage.success:
                stat["success_count"] += 1

        # 更新效果评分
        if usage.effectiveness is not None:
            stat["effectiveness_sum"] += usage.effectiveness

        # 更新最后使用时间
        stat["last_used"] = usage.timestamp

        # 按作家统计
        if usage.writer:
            stat["by_writer"][usage.writer] = stat["by_writer"].get(usage.writer, 0) + 1

        # 按场景统计
        if usage.scene_type:
            stat["by_scene"][usage.scene_type] = (
                stat["by_scene"].get(usage.scene_type, 0) + 1
            )

        # 收集上下文（最多保留10个）
        if len(stat["contexts"]) < 10:
            stat["contexts"].append(usage.context)

    def get_usage_stats(self, technique_id: str) -> TechniqueStats:
        """
        获取技法使用统计

        Args:
            technique_id: 技法ID

        Returns:
            TechniqueStats 统计信息
        """
        data = self._load_data()
        stats_data = data["stats"].get(technique_id, {})

        if not stats_data:
            return TechniqueStats(technique_id=technique_id)

        # 计算成功率
        success_rate = 0.0
        if stats_data.get("total_usage", 0) > 0:
            success_rate = (
                stats_data.get("success_count", 0) / stats_data["total_usage"]
            )

        # 计算平均效果评分
        avg_effectiveness = 0.0
        if (
            stats_data.get("total_usage", 0) > 0
            and stats_data.get("effectiveness_sum", 0) > 0
        ):
            avg_effectiveness = (
                stats_data["effectiveness_sum"] / stats_data["total_usage"]
            )

        return TechniqueStats(
            technique_id=technique_id,
            total_usage=stats_data.get("total_usage", 0),
            success_rate=success_rate,
            avg_effectiveness=avg_effectiveness,
            last_used=stats_data.get("last_used"),
            common_contexts=stats_data.get("contexts", []),
            by_writer=stats_data.get("by_writer", {}),
            by_scene=stats_data.get("by_scene", {}),
        )

    def get_effectiveness_score(self, technique_id: str) -> float:
        """
        获取技法效果评分

        Args:
            technique_id: 技法ID

        Returns:
            效果评分 (0-1)，无数据返回0.5作为默认值
        """
        stats = self.get_usage_stats(technique_id)

        if stats.total_usage == 0:
            return 0.5  # 未使用过的技法，默认中等评分

        # 综合评分：成功率权重0.6，平均效果权重0.4
        score = stats.success_rate * 0.6 + stats.avg_effectiveness * 0.4

        return round(score, 2)

    def recommend_techniques(
        self,
        context: Dict[str, Any],
        dimension: Optional[str] = None,
        scene_type: Optional[str] = None,
        top_k: int = 5,
        min_effectiveness: float = 0.3,
    ) -> List[Tuple[str, float, TechniqueStats]]:
        """
        推荐技法

        Args:
            context: 当前上下文
            dimension: 技法维度（可选）
            scene_type: 场景类型（可选）
            top_k: 推荐数量
            min_effectiveness: 最小效果评分

        Returns:
            推荐技法列表 [(technique_id, score, stats)]
        """
        data = self._load_data()
        stats_data = data["stats"]

        # 获取候选技法
        candidates = []

        for technique_id, stat in stats_data.items():
            # 计算评分
            score = self._calculate_recommendation_score(
                technique_id, stat, context, scene_type
            )

            # 过滤条件
            if score >= min_effectiveness:
                candidates.append((technique_id, score, stat))

        # 如果有维度约束，优先该维度的技法
        if dimension:
            dimension_techniques = self.DIMENSIONS.get(dimension, [])
            # 给维度匹配的技法加分
            candidates = [
                (
                    tid,
                    score + 0.2
                    if any(kw in tid for kw in dimension_techniques)
                    else score,
                    stat,
                )
                for tid, score, stat in candidates
            ]

        # 按评分排序
        candidates.sort(key=lambda x: x[1], reverse=True)

        # 返回前K个
        results = []
        for technique_id, score, stat in candidates[:top_k]:
            stats = TechniqueStats(
                technique_id=technique_id,
                total_usage=stat.get("total_usage", 0),
                success_rate=stat.get("success_count", 0) / stat.get("total_usage", 1)
                if stat.get("total_usage") > 0
                else 0.0,
                avg_effectiveness=stat.get("effectiveness_sum", 0)
                / stat.get("total_usage", 1)
                if stat.get("total_usage") > 0
                else 0.0,
                last_used=stat.get("last_used"),
                common_contexts=stat.get("contexts", []),
                by_writer=stat.get("by_writer", {}),
                by_scene=stat.get("by_scene", {}),
            )
            results.append((technique_id, round(score, 2), stats))

        return results

    def _calculate_recommendation_score(
        self,
        technique_id: str,
        stat: Dict[str, Any],
        context: Dict[str, Any],
        scene_type: Optional[str] = None,
    ) -> float:
        """
        计算技法推荐评分

        综合考虑：
        1. 效果评分 (40%)
        2. 使用频率 (20%)
        3. 场景匹配度 (20%)
        4. 上下文相似度 (20%)
        """
        # 效果评分
        effectiveness_score = self.get_effectiveness_score(technique_id)

        # 使用频率评分（使用次数越多，可信度越高）
        usage_count = stat.get("total_usage", 0)
        frequency_score = min(usage_count / 10, 1.0)  # 最多10次以上满分

        # 场景匹配度
        scene_score = 0.0
        if scene_type:
            scene_usage = stat.get("by_scene", {}).get(scene_type, 0)
            total_scene_usage = sum(stat.get("by_scene", {}).values())
            if total_scene_usage > 0:
                scene_score = scene_usage / total_scene_usage

        # 上下文相似度（简单实现：关键词匹配）
        context_score = 0.0
        if stat.get("contexts"):
            # 检查历史上下文是否包含当前上下文的关键词
            for historical_context in stat.get("contexts", []):
                overlap = self._context_overlap(context, historical_context)
                context_score = max(context_score, overlap)

        # 综合评分
        total_score = (
            effectiveness_score * 0.4
            + frequency_score * 0.2
            + scene_score * 0.2
            + context_score * 0.2
        )

        return total_score

    def _context_overlap(
        self, context1: Dict[str, Any], context2: Dict[str, Any]
    ) -> float:
        """计算两个上下文的相似度"""
        # 获取关键特征
        keys1 = set(context1.keys())
        keys2 = set(context2.keys())

        # 共同key数量
        common_keys = keys1 & keys2

        if not common_keys:
            return 0.0

        # 计算值匹配度
        match_count = 0
        for key in common_keys:
            if context1[key] == context2[key]:
                match_count += 1

        return match_count / len(common_keys)

    def get_dimension_stats(self, dimension: str) -> Dict[str, TechniqueStats]:
        """
        获取某个维度的所有技法统计

        Args:
            dimension: 维度名称

        Returns:
            维度技法统计字典
        """
        techniques = self.DIMENSIONS.get(dimension, [])
        results = {}

        for technique_keyword in techniques:
            # 查找包含该关键词的技法
            data = self._load_data()
            for technique_id in data["stats"].keys():
                if technique_keyword in technique_id:
                    results[technique_id] = self.get_usage_stats(technique_id)

        return results

    def clear_old_records(self, days: int = 30) -> int:
        """
        清理旧记录

        Args:
            days: 保留天数

        Returns:
            清理的记录数量
        """
        data = self._load_data()
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

        # 过滤使用记录
        original_count = len(data["usages"])
        data["usages"] = [
            u
            for u in data["usages"]
            if datetime.fromisoformat(u["timestamp"]).timestamp() > cutoff_time
        ]

        cleaned_count = original_count - len(data["usages"])

        if cleaned_count > 0:
            self._save_data(data)

        return cleaned_count


# 便捷函数
def get_technique_tracker(project_root: Optional[Path] = None) -> TechniqueTracker:
    """获取技法追踪器实例"""
    return TechniqueTracker(project_root)
