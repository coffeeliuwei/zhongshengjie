"""
验证模块 - 入口文件

⚠️ 状态说明：扩展备用，当前不启用

当前章节评估通过 novelist-evaluator Skill 在对话中执行，
无需通过本 Python 模块。本模块为未来扩展预留：
  - Web 界面评估报告
  - CLI 批量验证命令
  - 自动化质量检查

对话形式使用时，Evaluator Skill 直接评估，无需此模块。

功能清单（预留）：
  1. ValidationManager - 统一验证入口，运行所有验证
  2. CheckerManager - 检查功能集合（案例库、知识图谱等）
  3. ScorerManager - 评分功能（11维度评分体系）
  4. ValidationHistory - 验证历史管理
"""

from .validation_manager import ValidationManager, ValidationHistory
from .checker_manager import CheckerManager
from .scorer_manager import ScorerManager, DIMENSIONS, RATINGS, VALIDATION_THRESHOLDS

# CLI适配接口
from .validation_manager import run_validation_cli
from .scorer_manager import run_scorer_cli

__all__ = [
    # 核心类
    "ValidationManager",
    "ValidationHistory",
    "CheckerManager",
    "ScorerManager",
    # 配置常量
    "DIMENSIONS",
    "RATINGS",
    "VALIDATION_THRESHOLDS",
    # CLI接口
    "run_validation_cli",
    "run_scorer_cli",
]


# ============================================================
# 模块级便捷函数
# ============================================================


def validate_all(quick: bool = False) -> dict:
    """
    运行所有验证（便捷函数）

    Args:
        quick: 快速模式

    Returns:
        验证报告
    """
    manager = ValidationManager()
    return manager.run_all(quick=quick)


def validate_chapter(chapter_path: str) -> dict:
    """
    验证章节（便捷函数）

    Args:
        chapter_path: 章节路径

    Returns:
        验证结果
    """
    manager = ValidationManager()
    return manager.validate_chapter(chapter_path)


def check_all() -> dict:
    """
    运行所有检查（便捷函数）

    Returns:
        检查结果
    """
    checker = CheckerManager()
    return checker.check_all()


def score_chapter(chapter_path: str, scores: dict) -> str:
    """
    评分章节（便捷函数）

    Args:
        chapter_path: 章节路径
        scores: 维度评分

    Returns:
        评分报告
    """
    scorer = ScorerManager()
    scorer.load_chapter(chapter_path)
    scorer.set_scores(scores)
    return scorer.generate_report()


# 添加便捷函数到导出
__all__.extend(
    [
        "validate_all",
        "validate_chapter",
        "check_all",
        "score_chapter",
    ]
)
