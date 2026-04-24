"""
移植模块 - 入口文件

⚠️ 状态说明：扩展备用，当前不启用

当前项目迁移需求可在对话中通过 AI 直接处理，
无需通过本 Python 模块。本模块为未来扩展预留：
  - CLI 项目模板导出
  - 自动化环境初始化
  - 批量数据迁移

对话形式使用时，AI 直接协助迁移操作，无需此模块。

功能清单（预留）：
  - TemplateExporter - 项目模板导出
  - EnvironmentInitializer - 环境初始化
"""

from .export_template import TemplateExporter
from .init_environment import EnvironmentInitializer

__all__ = ["TemplateExporter", "EnvironmentInitializer"]
