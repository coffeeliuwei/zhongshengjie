#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
M8 世界观无关性测试
=================

验收目标：新机器只改 config.json 即可运行 — skill 文件无机器专属路径。

测试分组：
  TestSkillFileHygiene   — skill 文件无绝对路径
  TestWorldLoader        — core.world_loader 功能正确
  TestWorldSwitch        — switch_world 切换逻辑
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

# ── 路径常量 ────────────────────────────────────────────────
SKILLS_DIR = Path.home() / ".agents" / "skills"
PROJECT_ROOT = Path(__file__).parent.parent


# ══════════════════════════════════════════════════════════════
# Group 1: Skill 文件卫生检查
# ══════════════════════════════════════════════════════════════

class TestSkillFileHygiene:
    """skill 文件不应包含机器专属绝对路径"""

    FORBIDDEN_PATTERNS = [
        # Windows 绝对路径（驱动器字母）
        r"D:/动画/众生界",
        r"D:\\动画\\众生界",
        r"E:/Users/",
        r"E:\\Users\\",
        r"C:/Users/39477",
        r"C:\\Users\\39477",
        # 旧式硬编码（任何用户名下的 .agents 绝对路径）
        r"C:/Users/\w+/\.agents",
    ]

    def _get_skill_files(self):
        if not SKILLS_DIR.exists():
            pytest.skip(f"Skills 目录不存在: {SKILLS_DIR}")
        files = list(SKILLS_DIR.rglob("SKILL.md"))
        if not files:
            pytest.skip("未找到 SKILL.md 文件")
        return files

    @pytest.mark.parametrize("pattern", FORBIDDEN_PATTERNS)
    def test_no_forbidden_pattern(self, pattern):
        """每个 skill 文件都不应包含该 forbidden pattern"""
        import re
        skill_files = self._get_skill_files()
        violations = []
        regex = re.compile(pattern)
        for sf in skill_files:
            text = sf.read_text(encoding="utf-8")
            matches = [(i + 1, line.strip()) for i, line in enumerate(text.splitlines())
                       if regex.search(line)]
            if matches:
                violations.append(f"\n  {sf.name}: {matches[:3]}")

        assert not violations, (
            f"发现 forbidden pattern '{pattern}' in skill files:\n"
            + "".join(violations)
        )

    def test_experience_log_uses_config(self):
        """novel-workflow SKILL.md 中的 experience_dir 应通过 config 读取"""
        wf_skill = SKILLS_DIR / "novel-workflow" / "SKILL.md"
        if not wf_skill.exists():
            pytest.skip("novel-workflow/SKILL.md 不存在")
        text = wf_skill.read_text(encoding="utf-8")
        # 不应有旧式硬编码
        assert 'Path("D:/动画/众生界/章节经验日志")' not in text, \
            "novel-workflow SKILL.md 仍有旧式路径硬编码"
        # 新式应包含 config 读取逻辑
        assert 'experience_dir' in text, \
            "novel-workflow SKILL.md 未使用 experience_dir 配置键"

    def test_evaluator_techniques_path_uses_placeholder(self):
        """novelist-evaluator SKILL.md 中的技法路径应使用占位符"""
        ev_skill = SKILLS_DIR / "novelist-evaluator" / "SKILL.md"
        if not ev_skill.exists():
            pytest.skip("novelist-evaluator/SKILL.md 不存在")
        text = ev_skill.read_text(encoding="utf-8")
        assert r'D:\动画\众生界\创作技法' not in text, \
            "novelist-evaluator SKILL.md 仍有旧式技法路径"

    def test_inspiration_meta_template_no_user_path(self):
        """novel-inspiration-ingest SKILL.md 的 meta.yml 模板不含用户路径"""
        ingest_skill = SKILLS_DIR / "novel-inspiration-ingest" / "SKILL.md"
        if not ingest_skill.exists():
            pytest.skip("novel-inspiration-ingest/SKILL.md 不存在")
        text = ingest_skill.read_text(encoding="utf-8")
        assert "E:/Users/39477" not in text, \
            "novel-inspiration-ingest SKILL.md 仍有用户路径"


# ══════════════════════════════════════════════════════════════
# Group 2: WorldLoader 功能测试
# ══════════════════════════════════════════════════════════════

class TestWorldLoader:
    """core.world_loader 基础功能"""

    def test_import_world_loader(self):
        """能正常导入 world_loader"""
        from core.world_loader import (
            get_current_world_name,
            get_world_config,
            list_available_worlds,
            switch_world,
        )
        assert callable(get_current_world_name)
        assert callable(get_world_config)
        assert callable(list_available_worlds)
        assert callable(switch_world)

    def test_get_current_world_name_default(self):
        """从项目根目录读取当前世界观名称"""
        from core.world_loader import get_current_world_name
        name = get_current_world_name(PROJECT_ROOT)
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_current_world_name_is_zhongshengjie(self):
        """当前世界观应为众生界（默认配置）"""
        from core.world_loader import get_current_world_name
        name = get_current_world_name(PROJECT_ROOT)
        assert name == "众生界", f"当前世界观不是众生界，而是 '{name}'"

    def test_get_world_config_returns_dict(self):
        """get_world_config 返回字典"""
        from core.world_loader import get_world_config
        cfg = get_world_config(project_root=PROJECT_ROOT)
        assert isinstance(cfg, dict)
        assert "world_name" in cfg

    def test_get_world_config_has_power_systems(self):
        """众生界配置包含 power_systems"""
        from core.world_loader import get_world_config
        cfg = get_world_config(project_root=PROJECT_ROOT)
        assert "power_systems" in cfg, "众生界配置缺少 power_systems"

    def test_get_world_config_explicit_name(self):
        """可以显式指定世界观名称加载"""
        from core.world_loader import get_world_config
        cfg = get_world_config("众生界", project_root=PROJECT_ROOT)
        assert cfg["world_name"] == "众生界"

    def test_get_world_config_nonexistent_raises(self):
        """不存在的世界观应抛出 FileNotFoundError"""
        from core.world_loader import get_world_config
        with pytest.raises(FileNotFoundError):
            get_world_config("不存在的世界观_xyz", project_root=PROJECT_ROOT)

    def test_list_available_worlds(self):
        """list_available_worlds 返回非空列表"""
        from core.world_loader import list_available_worlds
        worlds = list_available_worlds(PROJECT_ROOT)
        assert isinstance(worlds, list)
        assert len(worlds) > 0
        assert "众生界" in worlds

    def test_list_includes_sample_worlds(self):
        """示例世界观文件都能被列出"""
        from core.world_loader import list_available_worlds
        worlds = list_available_worlds(PROJECT_ROOT)
        expected = {"众生界", "修仙世界示例", "星海纪元"}
        missing = expected - set(worlds)
        assert not missing, f"以下示例世界观不在列表中: {missing}"


# ══════════════════════════════════════════════════════════════
# Group 3: switch_world 切换测试（使用临时目录隔离，不污染真实配置）
# ══════════════════════════════════════════════════════════════

class TestWorldSwitch:
    """switch_world 切换逻辑（沙盒测试，不改真实 config.json）"""

    def _make_sandbox(self, world_name="众生界"):
        """创建临时项目目录作为沙盒"""
        tmpdir = Path(tempfile.mkdtemp())
        # 复制 config.json
        src_config = PROJECT_ROOT / "config.json"
        if src_config.exists():
            shutil.copy(src_config, tmpdir / "config.json")
        else:
            (tmpdir / "config.json").write_text(
                json.dumps({"worldview": {"current_world": world_name}}),
                encoding="utf-8"
            )
        # 复制 worlds 目录
        src_worlds = PROJECT_ROOT / "config" / "worlds"
        if src_worlds.exists():
            shutil.copytree(src_worlds, tmpdir / "config" / "worlds")
        return tmpdir

    def test_switch_world_changes_config(self):
        """switch_world 正确修改沙盒 config.json"""
        from core.world_loader import switch_world, get_current_world_name
        sandbox = self._make_sandbox("众生界")
        try:
            # 切换到示例世界
            switch_world("修仙世界示例", project_root=sandbox)
            # 验证
            new_name = get_current_world_name(sandbox)
            assert new_name == "修仙世界示例", \
                f"切换后应为 '修仙世界示例'，实际为 '{new_name}'"
        finally:
            shutil.rmtree(sandbox)

    def test_switch_world_nonexistent_raises(self):
        """切换到不存在的世界观应 raise FileNotFoundError"""
        from core.world_loader import switch_world
        sandbox = self._make_sandbox("众生界")
        try:
            with pytest.raises(FileNotFoundError):
                switch_world("不存在的世界观_xyz", project_root=sandbox)
        finally:
            shutil.rmtree(sandbox)

    def test_switch_world_same_raises_value_error(self):
        """切换到相同世界观应 raise ValueError"""
        from core.world_loader import switch_world
        sandbox = self._make_sandbox("众生界")
        try:
            with pytest.raises(ValueError):
                switch_world("众生界", project_root=sandbox)
        finally:
            shutil.rmtree(sandbox)

    def test_switch_world_can_switch_back(self):
        """能从 A 切换到 B，再切换回 A"""
        from core.world_loader import switch_world, get_current_world_name
        sandbox = self._make_sandbox("众生界")
        try:
            switch_world("修仙世界示例", project_root=sandbox)
            switch_world("众生界", project_root=sandbox)
            assert get_current_world_name(sandbox) == "众生界"
        finally:
            shutil.rmtree(sandbox)