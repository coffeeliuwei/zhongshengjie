#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
入库校验器 (Ingestion Validator)
===============================

在数据入库前进行噪音检测和质量验证。

功能:
- 噪音阈值检测
- 批量数据验证
- 返回验证结果（不抛出异常）

用法:
    from ingestion_validator import IngestionValidator

    validator = IngestionValidator()
    result = validator.validate_batch(data_items)

    if result['can_ingest']:
        # 可以入库
        pass
    else:
        # 噪音过多，需要清洗
        print(result['noise_examples'])
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# 添加项目路径以支持 config_loader 导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 尝试导入 config_loader
config_loader_available = False
try:
    from core.config_loader import get_config

    config_loader_available = True
except ImportError:
    pass


@dataclass
class ValidationResult:
    """单条数据验证结果"""

    is_valid: bool
    noise_score: float
    noise_features: List[str]
    content_sample: str = ""


@dataclass
class BatchValidationResult:
    """批量验证结果"""

    can_ingest: bool
    noise_ratio: float
    total_count: int
    noise_count: int
    valid_items: List[Dict[str, Any]]
    noise_items: List[Dict[str, Any]]
    noise_examples: List[str] = field(default_factory=list)
    details: List[ValidationResult] = field(default_factory=list)


class IngestionValidator:
    """
    入库校验器

    在数据入库前进行噪音检测，确保数据质量。
    """

    # 默认噪音特征词
    DEFAULT_NOISE_FEATURES = [
        # 对话词误匹配
        "说道",
        "笑道",
        "问道",
        "答道",
        "大声道",
        "低声道",
        "叫道",
        "喊道",
        "喃喃道",
        "冷声道",
        "沉声道",
        # 目录页标记
        "目录",
        "章节目录",
        "第.*章",
        "第.*节",
        # 占位符
        "~~~",
        "………",
        "***",
        "---",
        "===",
        # 其他常见噪音
        "本章完",
        "未完待续",
        "作者的话",
        "起点中文网",
        "晋江文学城",
        "纵横中文网",
    ]

    # 默认噪音阈值
    DEFAULT_NOISE_THRESHOLD = 0.10

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化校验器

        Args:
            config_path: 配置文件路径，如果为 None 则自动检测
        """
        self.config = self._load_config(config_path)
        self.noise_features = self._load_noise_features()
        self.noise_threshold = self._load_noise_threshold()

        # 编译正则表达式以提高性能
        self._noise_patterns = [
            re.compile(pattern) for pattern in self._patterns_from_features()
        ]

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        加载配置

        优先使用 config_loader，如果不存在则使用默认配置
        """
        if config_loader_available:
            try:
                from core.config_loader import get_config

                return get_config()
            except Exception:
                pass

        # 尝试从指定路径加载
        if config_path:
            config_file = Path(config_path)
        else:
            # 尝试从项目根目录加载
            config_file = PROJECT_ROOT / "config.json"

        if config_file.exists():
            try:
                import json

                with open(config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return {}

    def _load_noise_features(self) -> List[str]:
        """
        加载噪音特征词列表

        从配置中加载，如果不存在则使用默认值
        """
        # 从配置中查找
        features = self.config.get("quality_thresholds", {}).get("noise_features")
        if features and isinstance(features, list):
            return features

        return self.DEFAULT_NOISE_FEATURES.copy()

    def _load_noise_threshold(self) -> float:
        """
        加载噪音阈值

        从配置中加载 quality_thresholds.noise_ratio_max
        默认值为 0.10 (10%)
        """
        thresholds = self.config.get("quality_thresholds", {})
        threshold = thresholds.get("noise_ratio_max")

        if threshold is not None and isinstance(threshold, (int, float)):
            return float(threshold)

        return self.DEFAULT_NOISE_THRESHOLD

    def _patterns_from_features(self) -> List[str]:
        """
        将噪音特征词转换为正则表达式模式
        """
        patterns = []
        for feature in self.noise_features:
            # 处理正则表达式特征（如 第.*章）
            if ".*" in feature or "^" in feature or "$" in feature:
                patterns.append(feature)
            else:
                # 转义特殊字符
                escaped = re.escape(feature)
                patterns.append(escaped)
        return patterns

    def _check_noise(self, text: str) -> ValidationResult:
        """
        单条数据噪音检测

        Args:
            text: 要检测的文本内容

        Returns:
            ValidationResult: 包含噪音评分和特征
        """
        if not text or not isinstance(text, str):
            return ValidationResult(
                is_valid=False,
                noise_score=1.0,
                noise_features=["empty_content"],
                content_sample="",
            )

        # 文本长度
        text_length = len(text)
        if text_length == 0:
            return ValidationResult(
                is_valid=False,
                noise_score=1.0,
                noise_features=["empty_content"],
                content_sample="",
            )

        # 检测噪音特征
        noise_features_found = []
        noise_positions = []

        for pattern in self._noise_patterns:
            for match in pattern.finditer(text):
                feature_text = match.group()
                if feature_text not in noise_features_found:
                    noise_features_found.append(feature_text)
                noise_positions.append((match.start(), match.end()))

        # 计算噪音字符总数（避免重复计算重叠部分）
        if noise_positions:
            # 合并重叠区间
            noise_positions.sort()
            merged_positions = [noise_positions[0]]
            for current in noise_positions[1:]:
                last = merged_positions[-1]
                if current[0] <= last[1]:  # 重叠
                    merged_positions[-1] = (last[0], max(last[1], current[1]))
                else:
                    merged_positions.append(current)

            # 计算总噪音字符数
            noise_char_count = sum(end - start for start, end in merged_positions)
        else:
            noise_char_count = 0

        # 计算噪音比例
        noise_score = noise_char_count / text_length

        # 如果包含大量数字（可能是ID、编号等），也视为噪音
        digit_ratio = len(re.findall(r"\d", text)) / text_length
        if digit_ratio > 0.3:  # 数字占比超过30%
            noise_features_found.append(f"high_digit_ratio:{digit_ratio:.2f}")
            noise_score = max(noise_score, digit_ratio * 0.5)

        # 如果包含大量英文字符（可能是乱码），也视为噪音
        eng_ratio = len(re.findall(r"[a-zA-Z]", text)) / text_length
        if eng_ratio > 0.3:  # 英文占比超过30%
            noise_features_found.append(f"high_english_ratio:{eng_ratio:.2f}")
            noise_score = max(noise_score, eng_ratio * 0.5)

        # 内容样本（用于调试）
        content_sample = text[:200] + "..." if len(text) > 200 else text

        return ValidationResult(
            is_valid=noise_score <= self.noise_threshold,
            noise_score=noise_score,
            noise_features=noise_features_found,
            content_sample=content_sample,
        )

    def validate_batch(
        self, data_items: List[Dict[str, Any]], content_key: str = "content"
    ) -> BatchValidationResult:
        """
        批量验证数据

        Args:
            data_items: 要验证的数据列表
            content_key: 内容字段名，默认为 "content"

        Returns:
            BatchValidationResult: 批量验证结果
        """
        if not data_items:
            return BatchValidationResult(
                can_ingest=True,
                noise_ratio=0.0,
                total_count=0,
                noise_count=0,
                valid_items=[],
                noise_items=[],
                noise_examples=[],
                details=[],
            )

        total_count = len(data_items)
        noise_count = 0
        valid_items = []
        noise_items = []
        noise_examples = []
        details = []

        for item in data_items:
            # 获取文本内容
            content = item.get(content_key, "")

            # 检测噪音
            result = self._check_noise(content)
            details.append(result)

            if result.is_valid:
                valid_items.append(item)
            else:
                noise_count += 1
                noise_items.append(item)
                # 记录噪音示例（最多5个）
                if len(noise_examples) < 5:
                    example = (
                        f"噪音评分: {result.noise_score:.2%} | "
                        f"特征: {', '.join(result.noise_features)} | "
                        f"样本: {result.content_sample[:100]}..."
                    )
                    noise_examples.append(example)

        # 计算整体噪音比例
        noise_ratio = noise_count / total_count if total_count > 0 else 0.0

        # 判断是否允许入库（噪音比例 <= 阈值）
        can_ingest = noise_ratio <= self.noise_threshold

        return BatchValidationResult(
            can_ingest=can_ingest,
            noise_ratio=noise_ratio,
            total_count=total_count,
            noise_count=noise_count,
            valid_items=valid_items,
            noise_items=noise_items,
            noise_examples=noise_examples,
            details=details,
        )

    def validate_single(self, content: str) -> ValidationResult:
        """
        验证单条数据

        Args:
            content: 要验证的文本内容

        Returns:
            ValidationResult: 单条验证结果
        """
        return self._check_noise(content)

    def get_config_info(self) -> Dict[str, Any]:
        """
        获取当前配置信息

        Returns:
            包含噪音特征、阈值等配置信息的字典
        """
        return {
            "noise_threshold": self.noise_threshold,
            "noise_features_count": len(self.noise_features),
            "noise_features_sample": self.noise_features[:10],
            "config_loader_available": config_loader_available,
        }


# 便捷函数
def validate_batch(
    data_items: List[Dict[str, Any]],
    content_key: str = "content",
    config_path: Optional[str] = None,
) -> BatchValidationResult:
    """
    便捷函数：批量验证数据

    Args:
        data_items: 要验证的数据列表
        content_key: 内容字段名
        config_path: 配置文件路径

    Returns:
        BatchValidationResult: 批量验证结果
    """
    validator = IngestionValidator(config_path=config_path)
    return validator.validate_batch(data_items, content_key)


def validate_single(
    content: str, config_path: Optional[str] = None
) -> ValidationResult:
    """
    便捷函数：验证单条数据

    Args:
        content: 要验证的文本内容
        config_path: 配置文件路径

    Returns:
        ValidationResult: 单条验证结果
    """
    validator = IngestionValidator(config_path=config_path)
    return validator.validate_single(content)


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("入库校验器测试")
    print("=" * 60)

    # 创建校验器
    validator = IngestionValidator()

    # 显示配置信息
    print("\n[配置信息]")
    config_info = validator.get_config_info()
    print(f"  噪音阈值: {config_info['noise_threshold']:.0%}")
    print(f"  噪音特征数量: {config_info['noise_features_count']}")
    print(f"  config_loader可用: {config_info['config_loader_available']}")

    # 测试数据
    test_data = [
        {"id": 1, "content": "这是一个正常的文本内容，不包含噪音特征。"},
        {"id": 2, "content": "他说道：'这怎么回事？'张三问道。目录：第一章"},
        {"id": 3, "content": "正常内容~~~这是占位符噪声。"},
        {"id": 4, "content": "纯正常的小说段落，描述场景和人物动作。"},
        {"id": 5, "content": "第1章 标题\n第2章 标题\n第3章 标题"},
    ]

    # 批量验证
    print("\n[批量验证]")
    result = validator.validate_batch(test_data)

    print(f"  总数: {result.total_count}")
    print(f"  噪音数: {result.noise_count}")
    print(f"  噪音比例: {result.noise_ratio:.2%}")
    print(f"  允许入库: {result.can_ingest}")

    if result.noise_examples:
        print(f"\n[噪音示例]")
        for i, example in enumerate(result.noise_examples, 1):
            print(f"  {i}. {example}")

    # 单条验证
    print("\n[单条验证]")
    single_result = validator.validate_single("张三说道：'你好！'李四笑道。")
    print(f"  内容: '张三说道：'你好！'李四笑道。'")
    print(f"  是否有效: {single_result.is_valid}")
    print(f"  噪音评分: {single_result.noise_score:.2%}")
    print(f"  噪音特征: {single_result.noise_features}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
