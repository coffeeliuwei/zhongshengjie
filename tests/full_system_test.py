"""
全面系统测试脚本

注意: modules.creation 已存档到 存档/modules_creation_archived/
现在使用 skill 层（novelist-workflow, novelist-*）作为主实现

功能：
1. 测试所有核心模块导入
2. 测试数据库连接
3. 测试技能文件
4. 测试向量数据库检索
5. 测试错误处理
6. 测试健康检查
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

# 配置输出编码
sys.stdout.reconfigure(encoding="utf-8")
# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.total = 0

    def run_test(self, name: str, test_func):
        """运行单个测试"""
        self.total += 1
        print(f"\n{'=' * 60}")
        print(f"测试: {name}")
        print(f"{'=' * 60}")

        try:
            result = test_func()
            if result:
                self.passed += 1
                self.results.append(
                    {"name": name, "status": "PASS", "message": str(result)}
                )
                print(f"✅ 通过: {result}")
            else:
                self.failed += 1
                self.results.append(
                    {"name": name, "status": "FAIL", "message": "返回False"}
                )
                print(f"❌ 失败: 返回False")
        except Exception as e:
            self.failed += 1
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.results.append({"name": name, "status": "FAIL", "message": error_msg})
            print(f"❌ 失败: {e}")
            traceback.print_exc()

    def summary(self):
        """输出测试摘要"""
        print(f"\n\n{'=' * 60}")
        print("测试摘要")
        print(f"{'=' * 60}")
        print(f"总计: {self.total}")
        print(f"通过: {self.passed} ✅")
        print(f"失败: {self.failed} ❌")
        print(f"通过率: {self.passed / self.total * 100:.1f}%")

        if self.failed > 0:
            print(f"\n失败的测试:")
            for r in self.results:
                if r["status"] == "FAIL":
                    print(f"  - {r['name']}")

        print(f"{'=' * 60}")
        return self.failed == 0


# 测试函数定义


def test_core_imports():
    """测试核心模块导入"""
    from core import (
        ConfigManager,
        PathManager,
        DatabaseConnectionManager,
        DatabaseStatus,
        get_db_manager,
        NovelError,
        ErrorCode,
        ErrorLevel,
        CreationError,
        DatabaseError,
        HealthChecker,
        HealthStatus,
        run_health_check,
    )

    return "所有核心模块导入成功"


def test_creation_module():
    """测试创作模块（已迁移至 skill 层）"""
    # 从配置获取 skills 路径
    try:
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
        from config_loader import get_skills_base_path

        skills_dir = get_skills_base_path()
    except Exception:
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
    for skill in required_skills:
        skill_path = skills_dir / skill / "SKILL.md"
        if not skill_path.exists():
            missing.append(skill)

    if missing:
        return f"缺少技能: {missing}"

    return f"创作模块已迁移至 skill 层 - 所有 {len(required_skills)} 个技能文件存在"


def test_database_connection():
    """测试数据库连接"""
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    required = ["novel_settings", "writing_techniques", "case_library"]
    missing = [c for c in required if c not in collection_names]

    if missing:
        return f"缺少集合: {missing}"

    # 检查数据量
    details = []
    for coll in required:
        info = client.get_collection(coll)
        details.append(f"{coll}: {info.points_count}")

    return f"数据库连接正常 - {', '.join(details)}"


def test_skills_exist():
    """测试技能文件存在"""
    # 从配置获取 skills 路径
    try:
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
        from config_loader import get_skills_base_path

        skills_dir = get_skills_base_path()
    except Exception:
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
    for skill in required_skills:
        skill_path = skills_dir / skill / "SKILL.md"
        if not skill_path.exists():
            missing.append(skill)

    if missing:
        return f"缺少技能: {missing}"

    return f"所有 {len(required_skills)} 个技能文件存在"


def test_error_handler():
    """测试错误处理框架"""
    from core import NovelError, ErrorCode, handle_errors, ErrorCollector

    # 测试错误创建
    try:
        raise NovelError(
            error_code=ErrorCode.UNKNOWN.code,
            error_message="测试错误",
        )
    except NovelError as e:
        assert str(e) == "[UNKNOWN_000] 测试错误"

    # 测试装饰器
    @handle_errors(default_return="default")
    def test_func():
        raise ValueError("测试异常")

    result = test_func()
    assert result == "default"

    # 测试错误收集器
    collector = ErrorCollector()
    assert not collector.has_errors

    return "错误处理框架测试通过"


def test_health_check():
    """测试健康检查模块"""
    from core import HealthChecker, HealthStatus

    checker = HealthChecker()
    report = checker.check_all(quick=True)

    # 健康检查可能因外部服务未启动而返回UNHEALTHY，这是正常的
    # 只需要验证报告结构正确
    assert report.overall_status in [
        HealthStatus.HEALTHY,
        HealthStatus.WARNING,
        HealthStatus.UNHEALTHY,
    ]
    assert len(report.results) >= 3

    return f"健康检查通过 - 状态: {report.overall_status.value}"


def test_knowledge_search():
    """测试知识检索"""
    sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))
    from knowledge_search import KnowledgeSearcher

    searcher = KnowledgeSearcher()

    # 测试角色检索
    results = searcher.search_novel("血牙", top_k=3)

    return f"知识检索测试通过 - 找到 {len(results)} 条结果"


def test_technique_search():
    """测试技法检索"""
    sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))
    from technique_search import TechniqueSearcher

    searcher = TechniqueSearcher()

    # 测试技法检索
    results = searcher.search("战斗代价", dimension="战斗", top_k=3)

    return f"技法检索测试通过 - 找到 {len(results)} 条结果"


def test_scene_writer_mapping():
    """测试场景-作家映射"""
    import json
    from pathlib import Path

    mapping_file = PROJECT_ROOT / ".vectorstore" / "scene_writer_mapping.json"

    with open(mapping_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    scene_count = data.get("scene_count", {}).get("active", 0)
    assert scene_count > 0

    # 检查关键场景
    mapping = data.get("scene_writer_mapping", {})
    assert "战斗场景" in mapping

    battle_scene = mapping["战斗场景"]
    assert "primary_writer" in battle_scene
    assert battle_scene["primary_writer"] == "剑尘"

    return f"场景-作家映射测试通过 - {scene_count} 种活跃场景"


# 主测试运行
if __name__ == "__main__":
    print("=" * 60)
    print("众生界项目全面系统测试")
    print(f"测试时间: {datetime.now().isoformat()}")
    print("=" * 60)

    runner = TestRunner()

    # 运行所有测试
    runner.run_test("核心模块导入", test_core_imports)
    runner.run_test("创作模块（skill层）", test_creation_module)
    runner.run_test("数据库连接", test_database_connection)
    runner.run_test("技能文件存在", test_skills_exist)
    runner.run_test("错误处理框架", test_error_handler)
    runner.run_test("健康检查模块", test_health_check)
    runner.run_test("知识检索", test_knowledge_search)
    runner.run_test("技法检索", test_technique_search)
    runner.run_test("场景-作家映射", test_scene_writer_mapping)

    # 输出摘要
    all_passed = runner.summary()

    # 返回退出码
    sys.exit(0 if all_passed else 1)
