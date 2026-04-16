"""测试章节大纲解析器

基于实际大纲格式（如第一章-天裂大纲.md）编写测试
"""

from pathlib import Path
import pytest


# 模拟实际大纲格式（简化版，保留关键结构）
SAMPLE_OUTLINE = """# 《众生界》第一章：天裂

---

## 章节信息

| 项目 | 内容 |
|------|------|
| **章节名** | 天裂 |
| **视角** | 混血之民——血牙 |
| **身份** | 幸存者，复仇者，血脉抵抗体 |
| **核心情感** | 仇恨、痛苦、困惑、复仇决心 |
| **中文字数** | 8,667 |

---

## 核心逻辑

### 关键设定

| 项目 | 内容 |
|------|------|
| **血牙年龄** | 灭族时约10-13岁，现在约23岁（十年后） |
| **血牙父亲** | 铁牙，在山林中用血脉组成人墙，被打成筛子战死 |

---

## 详细场景设计

### 场景一：村口血战

> 黎明薄雾未散，村口已响惊雷。
>
> 佣兵联盟包围了青岩部落。

### 场景二：山林掩护

> 几个男人在战斗开始时被选中护送妇孺。
>
> 铁牙在其中。

### 场景三：妇孺诀别

> 妇孺逃进山林深处。
>
> 但她们知道，逃不掉。

---

## 写作要点

| 要点 | 说明 |
|------|------|
| **氛围** | 血月、雨夜、荒原，悲壮与仇恨交织 |
| **视角** | 儿童血牙——恐惧、无力、仇恨 |

---

## 章节结构

| 阶段 | 内容 | 时间线 |
|------|------|--------|
| **开篇** | 血月荒原，成年血牙独站悬崖 | 现在 |
| **村口血战** | 男人全部战死 | 过去 |
"""


def test_parser_returns_chapter_title():
    """解析器应提取章节标题"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)
    # 标题格式：# 《众生界》第一章：天裂
    assert "第一章" in result["chapter_title"]
    assert "天裂" in result["chapter_title"]


def test_parser_returns_chapter_info():
    """解析器应提取章节信息表格"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    info = result.get("chapter_info", {})
    assert info.get("章节名") == "天裂"
    assert info.get("视角") == "混血之民——血牙"
    assert info.get("核心情感") == "仇恨、痛苦、困惑、复仇决心"


def test_parser_returns_scenes():
    """解析器应提取详细场景设计"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    scenes = result.get("scenes", [])
    assert len(scenes) >= 3
    # 场景标题格式：### 场景X：场景名
    assert scenes[0]["title"] == "场景一：村口血战"
    assert scenes[1]["title"] == "场景二：山林掩护"
    assert scenes[2]["title"] == "场景三：妇孺诀别"


def test_parser_scene_has_content():
    """场景应包含引用块内容"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    scene = result["scenes"][0]
    content = scene.get("content", "")
    assert len(content) > 0
    assert "佣兵联盟" in content or "村口" in content


def test_parser_returns_key_settings():
    """解析器应提取关键设定表格"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    settings = result.get("key_settings", {})
    assert settings.get("血牙年龄") is not None
    assert "10-13岁" in settings["血牙年龄"]


def test_parser_returns_writing_notes():
    """解析器应提取写作要点表格"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    notes = result.get("writing_notes", {})
    assert notes.get("氛围") is not None
    assert "血月" in notes["氛围"]


def test_parser_returns_chapter_structure():
    """解析器应提取章节结构表格"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    structure = result.get("chapter_structure", [])
    assert len(structure) >= 2
    # 检查结构项包含阶段和内容
    assert any(s.get("阶段") == "开篇" for s in structure)
    assert any(s.get("阶段") == "村口血战" for s in structure)


def test_parser_returns_summary():
    """解析器应生成适合注入AI上下文的摘要"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse(SAMPLE_OUTLINE)

    summary = result.get("summary", "")
    assert len(summary) > 100  # 摘要应有足够长度
    # 摘要应包含关键信息
    assert "第一章" in summary or "天裂" in summary
    assert "场景" in summary


def test_parser_from_file(tmp_path):
    """解析器应能从文件读取"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    outline_file = tmp_path / "第一章-天裂大纲.md"
    outline_file.write_text(SAMPLE_OUTLINE, encoding="utf-8")

    parser = ChapterOutlineParser()
    result = parser.parse_file(outline_file)

    assert result is not None
    assert len(result.get("scenes", [])) >= 3


def test_parser_handles_empty_file():
    """空文件不应崩溃"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    parser = ChapterOutlineParser()
    result = parser.parse("")

    assert result is not None
    assert result.get("scenes", []) == []
    assert result.get("chapter_info", {}) == {}


def test_parser_handles_missing_sections():
    """缺少部分章节时应优雅降级"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    minimal_outline = """# 第二章大纲

## 详细场景设计

### 场景一：简单场景

这是一个简单的场景。
"""

    parser = ChapterOutlineParser()
    result = parser.parse(minimal_outline)

    assert "第二章" in result["chapter_title"]
    assert len(result.get("scenes", [])) >= 1
    # 缺失字段返回空值，不崩溃
    assert result.get("chapter_info", {}) == {}


def test_find_outline_file_by_chapter_number(tmp_path):
    """大纲查找应支持汉字章序和任意标题"""
    from core.parsing.chapter_outline_parser import ChapterOutlineParser

    # 创建模拟大纲文件（真实命名格式）
    (tmp_path / "第一章-天裂大纲.md").write_text("# 第一章大纲\n", encoding="utf-8")
    (tmp_path / "第二章-血脉大纲.md").write_text("# 第二章大纲\n", encoding="utf-8")

    parser = ChapterOutlineParser()

    # 按章序号查找（1 对应 第一章）
    found = parser.find_outline_file(1, tmp_path)
    assert found is not None, "应找到第一章大纲文件"
    assert found.name == "第一章-天裂大纲.md"

    found2 = parser.find_outline_file(2, tmp_path)
    assert found2 is not None, "应找到第二章大纲文件"

    found_none = parser.find_outline_file(99, tmp_path)
    assert found_none is None, "不存在的章节应返回 None"
