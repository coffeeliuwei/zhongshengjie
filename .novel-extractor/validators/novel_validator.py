"""
小说内容验证器模块

用于验证小说文件的质量和合规性：
1. 语言检测 - 确保中文内容占比达标
2. 内容验证 - 检测小说特征词，确保是小说内容而非其他类型文档
3. 综合验证 - 整合多项检测，返回完整验证报告

使用方法:
    from validators.novel_validator import NovelValidator

    validator = NovelValidator()
    result = validator.validate(text_content)

    if result.is_valid:
        print("验证通过")
    else:
        print(f"验证失败: {result.reason}")
"""

import re
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    验证结果数据类

    属性:
        is_valid: 是否通过验证
        reason: 失败原因（验证通过时为None）
        chinese_ratio: 中文比例检测结果
        feature_count: 小说特征词检测结果
        details: 详细检测数据字典
    """

    is_valid: bool
    reason: Optional[str] = None
    chinese_ratio: float = 0.0
    feature_count: int = 0
    details: Optional[dict[str, Any]] = None


class NovelValidator:
    """
    小说内容验证器

    提供多种验证方法用于检测小说文件的质量：
    - 中文比例检测：确保内容是中文小说
    - 小说特征词检测：确保内容是小说而非其他文档
    - 综合验证：执行所有检测并返回详细报告

    配置来源:
        从项目根目录的 config.json 中的 quality_thresholds 字段读取阈值配置
    """

    # 小说特征词库 - 用于识别小说内容
    # 包含人物称呼、动作、场景、情绪等小说常用词汇
    NOVEL_FEATURES: set[str] = {
        # 人物称呼
        "道友",
        "师兄",
        "师弟",
        "师姐",
        "师妹",
        "师傅",
        "师父",
        "徒弟",
        "长老",
        "掌门",
        "宗主",
        "弟子",
        "门人",
        "前辈",
        "晚辈",
        "陛下",
        "大人",
        "属下",
        "臣",
        "将军",
        "士兵",
        "士兵们",
        "阁下",
        "先生",
        "女士",
        "导师",
        "学徒",
        "雇主",
        "搭档",
        # 动作描写
        "冷哼",
        "冷喝",
        "怒喝",
        "暴喝",
        "大喝",
        "娇喝",
        "一掌",
        "一拳",
        "一剑",
        "一刀",
        "一枪",
        "一棍",
        "身形",
        "身影",
        "身影一闪",
        "身形一动",
        "身形暴退",
        "猛地",
        "骤然",
        "突然",
        "瞬间",
        "刹那",
        "眨眼间",
        # 修炼/力量相关
        "真气",
        "灵气",
        "元气",
        "内力",
        "功力",
        "修为",
        "境界",
        "突破",
        "瓶颈",
        "感悟",
        "领悟",
        "修炼",
        "丹田",
        "经脉",
        "穴道",
        "识海",
        "神识",
        "精神力",
        "法术",
        "法诀",
        "法宝",
        "灵器",
        "仙器",
        "神器",
        "魔力",
        "斗气",
        "魂力",
        "精神",
        "信仰",
        "圣光",
        # 战斗场景
        "战斗",
        "厮杀",
        "激战",
        "大战",
        "对决",
        "交手",
        "败退",
        "败走",
        "身亡",
        "陨落",
        "重创",
        "击伤",
        "防御",
        "攻击",
        "躲避",
        "闪避",
        "格挡",
        "反击",
        # 情绪描写
        "愤怒",
        "愤怒",
        "惊恐",
        "惊讶",
        "震惊",
        "骇然",
        "冷笑",
        "狞笑",
        "苦笑",
        "微笑",
        "大笑",
        "狂笑",
        "脸色",
        "面色",
        "神情",
        "表情",
        "目光",
        "眼神",
        # 叙事常用
        "只见",
        "但见",
        "只见得",
        "只见那",
        "但见那",
        "此时",
        "此刻",
        "这时",
        "当下",
        "当下里",
        "忽地",
        "蓦地",
        "蓦地",
        "猛然",
        "骤然",
        "随即",
        "接着",
        "然后",
        "紧接着",
        "随后",
        # 章节标记
        "第",
        "章",
        "节",
        "回",
        "卷",
        "部",
        # 对话相关
        "说道",
        "说",
        "问",
        "问道",
        "回答",
        "答道",
        "大笑",
        "苦笑",
        "冷哼",
        "冷喝",
        "怒道",
        "叫道",
        # 玄幻/仙侠特有
        "仙",
        "神",
        "魔",
        "妖",
        "鬼",
        "怪",
        "兽",
        "灵",
        "天",
        "地",
        "玄",
        "黄",
        "宇",
        "宙",
        "洪荒",
        "宗门",
        "门派",
        "家族",
        "世家",
        "王朝",
        "帝国",
        "大陆",
        "世界",
        "位面",
        "空间",
        "秘境",
        "遗迹",
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化验证器

        从配置文件加载阈值设置，如果加载失败则使用默认配置

        Args:
            config_path: 配置文件路径，默认为 None（自动从项目根目录查找）
        """
        self.config: dict[str, Any] = self._load_config(config_path)

    def _load_config(self, config_path: Optional[str] = None) -> dict[str, Any]:
        """
        加载配置文件

        优先使用 config_loader 模块加载统一配置，
        如果失败则从 config.json 直接读取

        Args:
            config_path: 配置文件路径

        Returns:
            包含 quality_thresholds 的配置字典
        """
        # 尝试使用项目的 config_loader 加载配置
        try:
            import sys

            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from core.config_loader import get_config

            config = get_config()
            if config and "quality_thresholds" in config:
                return config["quality_thresholds"]
        except Exception:
            pass

        # 如果 config_loader 失败，直接读取 config.json
        try:
            import json

            if config_path is None:
                project_root = Path(__file__).parent.parent.parent
                config_file_path = project_root / "config.json"
            else:
                config_file_path = Path(config_path)

            with open(config_file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("quality_thresholds", {})
        except Exception:
            pass

        # 如果都失败，返回默认配置
        return {
            "chinese_ratio_min": 0.6,
            "novel_features_min": 10,
        }

    def check_chinese_ratio(self, text: str) -> dict[str, Any]:
        """
        检测文本中的中文比例

        通过统计中文字符占总字符的比例，判断是否为中文内容。
        用于过滤掉非中文小说（如英文、日文等）。

        Args:
            text: 待检测的文本内容

        Returns:
            检测结果字典，包含：
            - passed: 是否通过检测（比例 >= 阈值）
            - ratio: 中文比例（0.0-1.0）
            - chinese_chars: 中文字符数量
            - total_chars: 总字符数量
            - threshold: 使用的阈值
        """
        if not text:
            return {
                "passed": False,
                "ratio": 0.0,
                "chinese_chars": 0,
                "total_chars": 0,
                "threshold": self.config.get("chinese_ratio_min", 0.6),
                "message": "文本为空或格式错误",
            }

        # 统计中文字符数量
        # 匹配所有中文字符（包括简体和繁体）
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))

        # 统计总字符数量（排除空白字符）
        total_chars = len(re.sub(r"\s", "", text))

        if total_chars == 0:
            return {
                "passed": False,
                "ratio": 0.0,
                "chinese_chars": 0,
                "total_chars": 0,
                "threshold": self.config.get("chinese_ratio_min", 0.6),
                "message": "文本无有效字符",
            }

        # 计算中文比例
        ratio = chinese_chars / total_chars

        # 获取阈值
        threshold = self.config.get("chinese_ratio_min", 0.6)

        # 判断是否通过
        passed = ratio >= threshold

        return {
            "passed": passed,
            "ratio": round(ratio, 4),
            "chinese_chars": chinese_chars,
            "total_chars": total_chars,
            "threshold": threshold,
            "message": f"中文比例 {ratio:.2%}，阈值 {threshold:.0%}"
            + ("" if passed else " - 未达标"),
        }

    def check_novel_features(self, text: str) -> dict[str, Any]:
        """
        检测文本中的小说特征词数量

        通过匹配预定义的小说特征词库，统计出现的特征词数量。
        用于识别文本是否为小说内容，过滤掉非小说文档（如说明文档、代码等）。

        Args:
            text: 待检测的文本内容

        Returns:
            检测结果字典，包含：
            - passed: 是否通过检测（特征词数量 >= 阈值）
            - count: 找到的特征词总数
            - unique_count: 不重复的特征词数量
            - matched_features: 匹配到的特征词列表
            - threshold: 使用的阈值
        """
        if not text:
            return {
                "passed": False,
                "count": 0,
                "unique_count": 0,
                "matched_features": [],
                "threshold": self.config.get("novel_features_min", 10),
                "message": "文本为空或格式错误",
            }

        # 统计特征词出现次数
        matched_features = []
        total_count = 0

        for feature in self.NOVEL_FEATURES:
            # 使用正则表达式匹配整个词
            # 避免部分匹配（如"道"匹配"道路"）
            pattern = re.escape(feature)
            matches = re.findall(pattern, text)
            if matches:
                matched_features.append({"word": feature, "count": len(matches)})
                total_count += len(matches)

        # 获取阈值
        threshold = self.config.get("novel_features_min", 10)

        # 判断是否通过（使用总出现次数，而非不重复词数）
        passed = total_count >= threshold

        return {
            "passed": passed,
            "count": total_count,
            "unique_count": len(matched_features),
            "matched_features": matched_features[:20],  # 限制返回数量
            "threshold": threshold,
            "message": f"特征词出现 {total_count} 次（{len(matched_features)}种），"
            + f"阈值 {threshold} 次"
            + ("" if passed else " - 未达标"),
        }

    def validate(self, text: str) -> ValidationResult:
        """
        执行综合验证

        同时执行中文比例检测和小说特征词检测，
        返回完整的验证结果。

        Args:
            text: 待验证的文本内容

        Returns:
            ValidationResult 对象，包含：
            - is_valid: 是否通过所有检测
            - reason: 失败原因（如有）
            - chinese_ratio: 中文比例数值
            - feature_count: 特征词数量
            - details: 详细检测数据

        示例:
            >>> validator = NovelValidator()
            >>> result = validator.validate("第一章 修仙问道...")
            >>> if result.is_valid:
            ...     print("验证通过，可以入库")
            ... else:
            ...     print(f"验证失败: {result.reason}")
        """
        # 执行各项检测
        chinese_result = self.check_chinese_ratio(text)
        features_result = self.check_novel_features(text)

        # 判断是否通过所有检测
        is_valid = chinese_result["passed"] and features_result["passed"]

        # 构建失败原因
        reasons = []
        if not chinese_result["passed"]:
            reasons.append(
                f"中文比例不足 ({chinese_result['ratio']:.1%} < {chinese_result['threshold']:.0%})"
            )
        if not features_result["passed"]:
            reasons.append(
                f"特征词数量不足 ({features_result['count']} < {features_result['threshold']})"
            )

        reason = "; ".join(reasons) if reasons else None

        # 构建详细数据
        details = {
            "chinese_check": chinese_result,
            "features_check": features_result,
        }

        return ValidationResult(
            is_valid=is_valid,
            reason=reason,
            chinese_ratio=chinese_result["ratio"],
            feature_count=features_result["count"],
            details=details,
        )

    def validate_file(self, file_path: str) -> ValidationResult:
        """
        验证文件内容

        读取指定文件并执行综合验证。
        支持 txt、md 等文本文件格式。

        Args:
            file_path: 待验证的文件路径

        Returns:
            ValidationResult 对象

        Raises:
            FileNotFoundError: 文件不存在时抛出
            IOError: 文件读取失败时抛出
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 读取文件内容
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(path, "r", encoding="gbk", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"读取文件失败: {e}")

        return self.validate(content)

    def get_config_info(self) -> dict[str, Any]:
        """
        获取当前配置信息

        返回验证器使用的配置参数，用于调试和日志记录。

        Returns:
            配置信息字典，包含：
            - chinese_ratio_min: 中文比例阈值
            - novel_features_min: 特征词数量阈值
        """
        return {
            "chinese_ratio_min": self.config.get("chinese_ratio_min", 0.6),
            "novel_features_min": self.config.get("novel_features_min", 10),
            "feature_library_size": len(self.NOVEL_FEATURES),
        }


# 便捷函数 - 快速验证


def validate_novel(text: str, config_path: Optional[str] = None) -> ValidationResult:
    """
    快速验证函数

    无需实例化 NovelValidator，直接验证文本内容。

    Args:
        text: 待验证的文本内容
        config_path: 配置文件路径（可选）

    Returns:
        ValidationResult 验证结果

    示例:
        >>> from validators.novel_validator import validate_novel
        >>> result = validate_novel("第一章 修仙问道...")
        >>> print(result.is_valid)
    """
    validator = NovelValidator(config_path)
    return validator.validate(text)


def validate_novel_file(
    file_path: str, config_path: Optional[str] = None
) -> ValidationResult:
    """
    快速验证文件函数

    无需实例化 NovelValidator，直接验证文件内容。

    Args:
        file_path: 待验证的文件路径
        config_path: 配置文件路径（可选）

    Returns:
        ValidationResult 验证结果

    示例:
        >>> from validators.novel_validator import validate_novel_file
        >>> result = validate_novel_file("novel.txt")
        >>> print(result.is_valid)
    """
    validator = NovelValidator(config_path)
    return validator.validate_file(file_path)
