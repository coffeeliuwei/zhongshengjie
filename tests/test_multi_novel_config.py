# tests/test_multi_novel_config.py
"""验证多小说配置切换逻辑（P5 多小说解耦）。"""
import json
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_get_current_world_returns_string():
    """get_current_world() 返回非空字符串"""
    from core.config_loader import get_current_world
    world = get_current_world()
    assert isinstance(world, str)
    assert len(world) > 0


def test_world_config_file_exists_for_current_world():
    """当前世界观对应的 config/worlds/*.json 文件存在"""
    from core.config_loader import get_current_world
    world = get_current_world()
    world_config_path = PROJECT_ROOT / "config" / "worlds" / f"{world}.json"
    assert world_config_path.exists(), (
        f"config/worlds/{world}.json 不存在，请先创建或检查 config.json worldview.current_world"
    )


def test_world_config_has_required_fields():
    """world config JSON 包含必要字段"""
    from core.config_loader import get_current_world
    world = get_current_world()
    path = PROJECT_ROOT / "config" / "worlds" / f"{world}.json"
    if not path.exists():
        pytest.skip(f"world config {world}.json not found")
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ["world_name", "world_type", "power_systems", "factions", "core_principles"]:
        assert field in data, f"world config 缺少字段: {field}"


def test_example_world_configs_are_valid_json():
    """config/worlds/ 下所有 JSON 文件均可正常解析"""
    worlds_dir = PROJECT_ROOT / "config" / "worlds"
    json_files = list(worlds_dir.glob("*.json"))
    assert len(json_files) > 0, "config/worlds/ 目录为空"
    for f in json_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        assert "world_name" in data, f"{f.name} 缺少 world_name 字段"


def test_init_novel_script_exists():
    """tools/init_novel.py 存在且可运行"""
    script_path = PROJECT_ROOT / "tools" / "init_novel.py"
    assert script_path.exists(), "tools/init_novel.py 不存在"
    # 验证 --list-templates 参数可用
    import subprocess
    result = subprocess.run(
        [sys.executable, str(script_path), "--list-templates"],
        capture_output=True, text=True, timeout=10
    )
    assert "可用" in result.stdout or "模板" in result.stdout or result.returncode == 0
