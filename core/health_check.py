"""
系统健康检查模块

功能：
1. 检查各组件状态（数据库、技能、文件、配置）
2. 启动时自动检查
3. 提供详细的健康报告
4. 支持快速诊断和深度检查

设计目的：
- 在系统启动时发现问题
- 预防运行时错误
- 便于快速诊断问题
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

# 从配置加载器导入路径获取函数
try:
    from .config_loader import get_project_root

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "healthy"  # 健康
    WARNING = "warning"  # 警告，可用但有风险
    UNHEALTHY = "unhealthy"  # 不健康，不可用
    UNKNOWN = "unknown"  # 未知，无法检查


@dataclass
class HealthCheckResult:
    """健康检查结果"""

    component: str
    status: HealthStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)
    check_time: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "suggestions": self.suggestions,
            "check_time": self.check_time,
        }


@dataclass
class HealthReport:
    """健康报告"""

    overall_status: HealthStatus
    results: List[HealthCheckResult]
    check_time: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        # 计算摘要
        self.summary = {
            "total": len(self.results),
            "healthy": sum(1 for r in self.results if r.status == HealthStatus.HEALTHY),
            "warning": sum(1 for r in self.results if r.status == HealthStatus.WARNING),
            "unhealthy": sum(
                1 for r in self.results if r.status == HealthStatus.UNHEALTHY
            ),
            "unknown": sum(1 for r in self.results if r.status == HealthStatus.UNKNOWN),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_status": self.overall_status.value,
            "check_time": self.check_time,
            "summary": self.summary,
            "results": [r.to_dict() for r in self.results],
        }

    def print_report(self) -> str:
        """打印报告"""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("系统健康检查报告")
        lines.append(f"检查时间: {self.check_time}")
        lines.append("=" * 60)

        # 总体状态
        status_icon = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.UNHEALTHY: "❌",
            HealthStatus.UNKNOWN: "❓",
        }
        lines.append(
            f"\n总体状态: {status_icon.get(self.overall_status, '❓')} {self.overall_status.value.upper()}"
        )

        # 摘要
        lines.append(
            f"\n摘要: {self.summary['healthy']}/{self.summary['total']} 组件健康"
        )

        # 各组件详情
        lines.append("\n" + "-" * 60)
        lines.append("组件详情:")
        lines.append("-" * 60)

        for result in self.results:
            icon = status_icon.get(result.status, "❓")
            lines.append(f"\n{icon} {result.component}")
            lines.append(f"   状态: {result.message}")
            if result.details:
                for key, value in result.details.items():
                    lines.append(f"   {key}: {value}")
            if result.suggestions:
                lines.append("   建议:")
                for s in result.suggestions:
                    lines.append(f"   - {s}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


class HealthChecker:
    """
    系统健康检查器

    Usage:
        checker = HealthChecker()
        report = checker.check_all()
        print(report.print_report())
    """

    def __init__(self, project_root: str = None):
        if HAS_CONFIG_LOADER:
            self.project_root = (
                Path(project_root) if project_root else get_project_root()
            )
        else:
            self.project_root = Path(project_root) if project_root else Path.cwd()
        self.checks: Dict[str, Callable] = {
            "数据库": self.check_database,
            "技能文件": self.check_skills,
            "配置文件": self.check_config,
            "设定文件": self.check_settings,
            "目录结构": self.check_directories,
        }

    def check_all(self, quick: bool = False) -> HealthReport:
        """
        执行所有健康检查

        Args:
            quick: 快速检查模式（只检查关键项）

        Returns:
            健康报告
        """
        results = []

        checks_to_run = self.checks.keys()
        if quick:
            # 快速模式只检查关键项
            checks_to_run = ["数据库", "技能文件", "配置文件"]

        for component in checks_to_run:
            check_func = self.checks[component]
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                results.append(
                    HealthCheckResult(
                        component=component,
                        status=HealthStatus.UNKNOWN,
                        message=f"检查失败: {str(e)}",
                        suggestions=["检查检查器本身是否有问题"],
                    )
                )

        # 确定总体状态
        overall = self._determine_overall_status(results)

        return HealthReport(overall_status=overall, results=results)

    def check_database(self) -> HealthCheckResult:
        """检查数据库状态"""
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(host="localhost", port=6333)

            # 检查连接
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]

            # 必需的集合
            required_collections = [
                "novel_settings",
                "writing_techniques",
                "case_library",
            ]
            missing = [c for c in required_collections if c not in collection_names]

            if missing:
                return HealthCheckResult(
                    component="数据库",
                    status=HealthStatus.WARNING,
                    message=f"缺少集合: {missing}",
                    details={"collections": collection_names},
                    suggestions=[
                        f"运行同步命令: python -m core kb --sync {missing[0].split('_')[0]}"
                    ],
                )

            # 检查集合数据量
            details = {}
            for coll in required_collections:
                try:
                    info = client.get_collection(coll)
                    details[coll] = info.points_count
                except:
                    details[coll] = "无法获取"

            return HealthCheckResult(
                component="数据库",
                status=HealthStatus.HEALTHY,
                message="数据库连接正常，所有必需集合存在",
                details=details,
            )

        except ImportError:
            return HealthCheckResult(
                component="数据库",
                status=HealthStatus.UNHEALTHY,
                message="qdrant-client 未安装",
                suggestions=["运行: pip install qdrant-client"],
            )
        except Exception as e:
            return HealthCheckResult(
                component="数据库",
                status=HealthStatus.UNHEALTHY,
                message=f"数据库连接失败: {str(e)}",
                suggestions=["检查 Qdrant 服务是否启动", "运行: docker start qdrant"],
            )

    def check_skills(self) -> HealthCheckResult:
        """检查技能文件"""
        # 从配置获取 skills 路径
        try:
            import sys

            sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
            from config_loader import get_skills_base_path

            skills_dir = get_skills_base_path()
        except Exception:
            # 回退到默认位置
            skills_dir = Path.home() / ".agents" / "skills"

        required_skills = [
            "novelist-canglan",
            "novelist-xuanyi",
            "novelist-moyan",
            "novelist-jianchen",
            "novelist-yunxi",
            "novelist-evaluator",
            "novelist-workflow",
            "novelist-shared",
        ]

        missing = []
        details = {}

        for skill in required_skills:
            skill_path = skills_dir / skill / "SKILL.md"
            if skill_path.exists():
                details[skill] = "✓"
            else:
                missing.append(skill)
                details[skill] = "✗"

        if missing:
            return HealthCheckResult(
                component="技能文件",
                status=HealthStatus.UNHEALTHY,
                message=f"缺少技能: {missing}",
                details=details,
                suggestions=["检查技能目录是否正确", f"确认 {skills_dir} 存在"],
            )

        return HealthCheckResult(
            component="技能文件",
            status=HealthStatus.HEALTHY,
            message="所有必需技能文件存在",
            details=details,
        )

    def check_config(self) -> HealthCheckResult:
        """检查配置文件"""
        config_files = {
            "CONFIG.md": self.project_root / "CONFIG.md",
            "system_config.json": self.project_root / "system_config.json",
            "config/scene_writer_mapping.json": self.project_root
            / "config"
            / "scene_writer_mapping.json",
        }

        missing = []
        details = {}

        for name, path in config_files.items():
            if path.exists():
                details[name] = "✓"
            else:
                missing.append(name)
                details[name] = "✗"

        if missing:
            return HealthCheckResult(
                component="配置文件",
                status=HealthStatus.WARNING,
                message=f"缺少配置: {missing}",
                details=details,
                suggestions=["检查项目根目录", "运行初始化命令"],
            )

        return HealthCheckResult(
            component="配置文件",
            status=HealthStatus.HEALTHY,
            message="所有配置文件存在",
            details=details,
        )

    def check_settings(self) -> HealthCheckResult:
        """检查设定文件"""
        settings_dir = self.project_root / "设定"
        outline_file = self.project_root / "总大纲.md"

        details = {}
        missing = []

        if not settings_dir.exists():
            missing.append("设定目录")
            details["设定目录"] = "✗"
        else:
            details["设定目录"] = "✓"
            # 检查关键设定文件
            key_files = ["人物谱.md", "十大势力.md"]
            for f in key_files:
                path = settings_dir / f
                details[f] = "✓" if path.exists() else "✗"

        if not outline_file.exists():
            missing.append("总大纲.md")
            details["总大纲.md"] = "✗"
        else:
            details["总大纲.md"] = "✓"

        if missing:
            return HealthCheckResult(
                component="设定文件",
                status=HealthStatus.WARNING,
                message=f"缺少: {missing}",
                details=details,
                suggestions=["创建基础设定文件", "从模板复制"],
            )

        return HealthCheckResult(
            component="设定文件",
            status=HealthStatus.HEALTHY,
            message="设定文件完整",
            details=details,
        )

    def check_directories(self) -> HealthCheckResult:
        """检查目录结构"""
        required_dirs = [
            "modules",
            "modules/creation",
            "modules/knowledge_base",
            "modules/validation",
            "modules/migration",
            ".vectorstore",
            "设定",
            "章节大纲",
            "正文",
            "创作技法",
        ]

        missing = []
        details = {}

        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                details[dir_name] = "✓"
            else:
                missing.append(dir_name)
                details[dir_name] = "✗"

        if missing:
            return HealthCheckResult(
                component="目录结构",
                status=HealthStatus.WARNING,
                message=f"缺少目录: {missing}",
                details=details,
                suggestions=["运行初始化: python -m core init"],
            )

        return HealthCheckResult(
            component="目录结构",
            status=HealthStatus.HEALTHY,
            message="目录结构完整",
            details=details,
        )

    def _determine_overall_status(
        self, results: List[HealthCheckResult]
    ) -> HealthStatus:
        """确定总体状态"""
        if any(r.status == HealthStatus.UNHEALTHY for r in results):
            return HealthStatus.UNHEALTHY
        elif any(r.status == HealthStatus.WARNING for r in results):
            return HealthStatus.WARNING
        elif any(r.status == HealthStatus.UNKNOWN for r in results):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    def add_check(self, name: str, check_func: Callable):
        """添加自定义检查"""
        self.checks[name] = check_func

    def quick_check(self) -> bool:
        """快速检查（返回布尔值）"""
        report = self.check_all(quick=True)
        return report.overall_status == HealthStatus.HEALTHY


# CLI 集成
def run_health_check(quick: bool = False):
    """运行健康检查（CLI 入口）"""
    checker = HealthChecker()
    report = checker.check_all(quick=quick)
    print(report.print_report())

    if report.overall_status != HealthStatus.HEALTHY:
        return 1  # 返回非零表示有问题
    return 0


# 使用示例
if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")

    # 运行完整检查
    exit_code = run_health_check(quick=False)
    sys.exit(exit_code)
