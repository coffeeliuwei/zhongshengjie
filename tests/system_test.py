"""
全面系统测试脚本（简化版）

注意: modules.creation 已存档到 存档/modules_creation_archived/
现在使用 skill 层（novelist-workflow, novelist-*）作为主实现

此文件为手动运行的集成测试，需要 Qdrant 等外部服务。
pytest 会自动跳过此文件，请使用 python tests/system_test.py 手动执行。
"""

import sys
import traceback
from pathlib import Path
from datetime import datetime

import pytest

pytestmark = pytest.mark.skip(reason="集成测试需手动运行: python tests/system_test.py")

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 配置输出编码
sys.stdout.reconfigure(encoding="utf-8")

print("=" * 60)
print("众生界项目全面系统测试")
print(f"测试时间: {datetime.now().isoformat()}")
print("=" * 60)

results = {"pass": 0, "fail": 0, "tests": []}


def test(name, func):
    """运行测试"""
    print(f"\n测试: {name}")
    try:
        result = func()
        results["pass"] += 1
        results["tests"].append({"name": name, "status": "PASS"})
        print(f"  ✅ 通过: {result}")
        return True
    except Exception as e:
        results["fail"] += 1
        results["tests"].append({"name": name, "status": "FAIL", "error": str(e)})
        print(f"  ❌ 失败: {e}")
        return False


# ============================================
# 测试 1: 数据库连接
# ============================================
def test_database():
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)
    collections = client.get_collections()
    names = [c.name for c in collections.collections]
    required = ["novel_settings", "writing_techniques", "case_library"]
    for r in required:
        if r not in names:
            raise Exception(f"缺少集合: {r}")
    return f"数据库连接正常，{len(names)} 个集合"


# ============================================
# 测试 2: 技能文件
# ============================================
def test_skills():
    # 从配置获取 skills 路径
    try:
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
        from config_loader import get_skills_base_path

        skills_dir = get_skills_base_path()
    except Exception:
        skills_dir = Path.home() / ".agents" / "skills"

    required = [
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
    for s in required:
        if not (skills_dir / s / "SKILL.md").exists():
            missing.append(s)
    if missing:
        raise Exception(f"缺少技能: {missing}")
    return f"所有 {len(required)} 个技能文件存在"


# ============================================
# 测试 3: 核心模块导入
# ============================================
def test_core_imports():
    from core import ConfigManager, PathManager, DatabaseConnectionManager
    from core import NovelError, ErrorCode, HealthChecker

    return "核心模块导入成功"


# ============================================
# 测试 4: 创作模块（已迁移至 skill 层）
# ============================================
def test_creation_module():
    # modules.creation 已存档，现在使用 skill 层
    # 从配置获取 skills 路径
    try:
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent / ".vectorstore"))
        from config_loader import get_skills_base_path

        skills_dir = get_skills_base_path()
    except Exception:
        skills_dir = Path.home() / ".agents" / ".agents" / "skills"

    # 检查 novelist-workflow skill
    workflow_skill = skills_dir / "novelist-workflow" / "SKILL.md"
    if not workflow_skill.exists():
        raise Exception("novelist-workflow skill 不存在")

    # 检查 novel-workflow skill
    novel_workflow_skill = skills_dir / "novel-workflow" / "SKILL.md"
    if not novel_workflow_skill.exists():
        raise Exception("novel-workflow skill 不存在")

    return "创作模块已迁移至 skill 层（novelist-workflow, novel-workflow）"


# ============================================
# 测试 5: 错误处理
# ============================================
def test_error_handler():
    from core import NovelError, ErrorCode, handle_errors, ErrorCollector

    # 测试错误创建
    try:
        raise NovelError(error_code=ErrorCode.UNKNOWN.code, error_message="测试")
    except NovelError as e:
        assert str(e) == "[UNKNOWN_000] 测试"

    # 测试装饰器
    @handle_errors(default_return="default")
    def test_func():
        raise ValueError("测试")

    assert test_func() == "default"
    return "错误处理框架测试通过"


# ============================================
# 测试 6: 健康检查
# ============================================
def test_health_check():
    from core import HealthChecker, HealthStatus

    checker = HealthChecker()
    report = checker.check_all(quick=True)
    assert report.overall_status in [HealthStatus.HEALTHY, HealthStatus.WARNING]
    return f"健康检查通过 - 状态: {report.overall_status.value}"


# ============================================
# 测试 7: 场景-作家映射
# ============================================
def test_scene_mapping():
    import json
    from pathlib import Path

    mapping_file = project_root / ".vectorstore" / "scene_writer_mapping.json"
    with open(mapping_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    scene_count = data.get("scene_count", {}).get("active", 0)
    mapping = data.get("scene_writer_mapping", {})

    assert "战斗场景" in mapping
    assert mapping["战斗场景"]["primary_writer"] == "剑尘"

    return f"场景-作家映射通过 - {scene_count} 种活跃场景"


# ============================================
# 测试 8: 向量数据库检索
# ============================================
def test_vector_search():
    sys.path.insert(0, str(project_root / ".vectorstore"))
    from knowledge_search import KnowledgeSearcher

    searcher = KnowledgeSearcher()
    results = searcher.search_novel("血牙", top_k=3)

    return f"向量数据库检索通过 - 找到 {len(results)} 条结果"


# ============================================
# 测试 9: 技法检索
# ============================================
def test_technique_search():
    sys.path.insert(0, str(project_root / ".vectorstore"))
    from technique_search import TechniqueSearcher

    searcher = TechniqueSearcher()
    results = searcher.search("战斗代价", dimension="战斗", top_k=3)

    return f"技法检索通过 - 找到 {len(results)} 条结果"


# ============================================
# 运行所有测试
# ============================================
if __name__ == "__main__":
    test("数据库连接", test_database)
    test("技能文件", test_skills)
    test("核心模块导入", test_core_imports)
    test("创作模块（skill层）", test_creation_module)
    test("错误处理框架", test_error_handler)
    test("健康检查模块", test_health_check)
    test("场景-作家映射", test_scene_mapping)
    test("向量数据库检索", test_vector_search)
    test("技法检索", test_technique_search)

    # 输出摘要
    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"总计: {results['pass'] + results['fail']}")
    print(f"通过: {results['pass']} ✅")
    print(f"失败: {results['fail']} ❌")
    print(f"通过率: {results['pass'] / (results['pass'] + results['fail']) * 100:.1f}%")

    if results["fail"] > 0:
        print("\n失败的测试:")
        for t in results["tests"]:
            if t["status"] == "FAIL":
                print(f"  - {t['name']}: {t.get('error', '')}")

    print("=" * 60)
    sys.exit(0 if results["fail"] == 0 else 1)
