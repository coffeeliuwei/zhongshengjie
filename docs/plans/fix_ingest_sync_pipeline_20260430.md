# 计划：inspiration-ingest 同步管线全量修复
# 日期：2026-04-30（Asia/Shanghai）
# 协议：docs/opencode_dev_protocol_20260420.md v1
# 执行者：opencode(GLM5)

---

## 总览

本计划修复三处独立 Bug，分别改三个文件，最后新建一个测试文件。

| 任务 | 文件 | 改动说明 |
|------|------|---------|
| 任务一 | `modules/knowledge_base/hybrid_sync_manager.py` | 修复第 406-407 行：`99-从小说提取` 目录下的技法文件 dimension 字段写成 `"未知"` |
| 任务二 | `tools/case_builder.py` | 修复第 2128-2138 行：sync 只读 JSON/只遍历一层，ingest 写的 .md 案例永远进不了数据库 |
| 任务三 | `core/retrieval/unified_retrieval_api.py` | 在第 615-616 行之间插入 5 个写手专属案例检索方法 |
| 任务四 | `tests/test_ingest_sync_pipeline.py` | 新建测试文件，覆盖上述三处修复 |

---

## 任务一：修复 hybrid_sync_manager.py（第 406-407 行）

### 背景

`inspiration-ingest` 把新增技法保存到 `创作技法/99-从小说提取/{维度名}.md`，例如：
- `创作技法/99-从小说提取/战斗冲突维度.md`
- `创作技法/99-从小说提取/世界观维度.md`

但 `hybrid_sync_manager.py` 用**父目录名**查 `DIMENSION_MAP`：
```python
parent_dir = md_file.parent.name          # → "99-从小说提取"
dimension = self.DIMENSION_MAP.get(parent_dir, "未知")   # → "未知"（不在 MAP 里）
```

结果所有 ingest 新增技法进库后 `dimension="未知"`，写手的17个维度专属检索方法全部找不到。

### 修改方法

打开 `modules/knowledge_base/hybrid_sync_manager.py`，找到第 **406-407 行**：

```python
                parent_dir = md_file.parent.name
                dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
```

**把这两行替换为以下三行**（注意缩进与原代码一致，均为16个空格）：

```python
                parent_dir = md_file.parent.name
                if parent_dir == "99-从小说提取":
                    dimension = md_file.stem
                else:
                    dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
```

> 说明：`md_file.stem` 取的是文件名去掉扩展名，例如 `战斗冲突维度.md` → `"战斗冲突维度"`，恰好就是 dimension 值。

第 408 行（`writer = self.WRITER_MAP.get(dimension, "未知")`）及之后**不需要改动**。

---

## 任务二：修复 case_builder.py（第 2128-2138 行）

### 背景

`inspiration-ingest` 把案例保存到：
```
E:/case-library/cases/99-从小说提取/{维度名}/{slug}-a.md
```
例如：
```
E:/case-library/cases/99-从小说提取/战斗冲突维度/novel-slug-a.md
```

文件格式（YAML frontmatter + 正文）：
```markdown
---
case_id: novel-slug-a
scene_type: 战斗冲突维度
source: 素材库/2026-04-30-xxx/source.md
why_good: 战斗节奏感强
---

这是原文段落内容，200-800字...
```

但 `case_builder.py` 的 `sync_to_vectorstore` 方法（第 2128-2138 行）只做了：
```python
        all_cases = []
        for scene_dir in self.cases_dir.iterdir():      # 只遍历一层
            if not scene_dir.is_dir():
                continue
            for meta_file in scene_dir.glob("*.json"):  # 只读 JSON
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        all_cases.append(json.load(f))
                except Exception:
                    continue
```

两个问题：
1. 只 glob `*.json`，`.md` 完全跳过
2. 只遍历一层 `cases/`，`99-从小说提取/战斗冲突维度/` 是两层深，进不去

### 修改方法

打开 `tools/case_builder.py`，找到第 **2128-2138 行**（从 `# 收集所有案例` 注释开始，到 `continue` 结束的块）：

```python
        # 收集所有案例
        all_cases = []
        for scene_dir in self.cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue
            for meta_file in scene_dir.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        all_cases.append(json.load(f))
                except Exception:
                    continue
```

**把上面这段完整替换为下面的代码**（缩进与原代码一致，均为8个空格）：

```python
        # 维度名 → 场景类型映射（inspiration-ingest 用维度名，写手 skill 用场景类型）
        _DIMENSION_TO_SCENE_TYPE = {
            "世界观维度": "世界观展示",
            "剧情维度": "剧情",
            "人物维度": "心理",
            "战斗冲突维度": "战斗",
            "氛围意境维度": "意境营造",
            "叙事维度": "信息传递",
            "主题维度": "内省",
            "情感维度": "情感",
            "读者体验维度": "内省",
            "元维度": "信息传递",
            "节奏维度": "日常",
        }

        def _parse_md_case(md_file):
            """解析 inspiration-ingest 写入的 .md 案例（YAML frontmatter + 正文）"""
            text = md_file.read_text(encoding="utf-8")
            meta = {}
            body = text
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    fm = text[3:end].strip()
                    for line in fm.splitlines():
                        if ":" in line:
                            k, _, v = line.partition(":")
                            meta[k.strip()] = v.strip()
                    body = text[end + 3:].strip()
            raw_scene = meta.get("scene_type", md_file.parent.name)
            scene_type = _DIMENSION_TO_SCENE_TYPE.get(raw_scene, raw_scene)
            return {
                "case_id": meta.get("case_id", md_file.stem),
                "scene_type": scene_type,
                "genre": meta.get("genre", "未分类"),
                "novel_name": meta.get("source", md_file.stem),
                "content": body,
                "word_count": len(body),
                "quality_score": 5.0,
                "emotion_value": 0.0,
                "techniques": [],
                "keywords": [],
                "source_file": str(md_file),
            }

        # 收集所有案例
        all_cases = []

        # 路径一：原有 JSON 案例（cases/{场景类型}/*.json，一层子目录）
        for scene_dir in self.cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue
            for meta_file in scene_dir.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        all_cases.append(json.load(f))
                except Exception:
                    continue

        # 路径二：inspiration-ingest 写入的 .md 案例（cases/99-从小说提取/{维度名}/*.md，两层子目录）
        ingest_dir = self.cases_dir / "99-从小说提取"
        if ingest_dir.exists():
            for md_file in ingest_dir.rglob("*.md"):
                try:
                    all_cases.append(_parse_md_case(md_file))
                except Exception as e:
                    print(f"    [跳过 md] {md_file.name}: {e}")
                    continue
```

> 注意：`_DIMENSION_TO_SCENE_TYPE` 和 `_parse_md_case` 定义在 `sync_to_vectorstore` 方法**内部**，不要放到类或模块级别。`_parse_md_case` 的参数类型是 `pathlib.Path`（已在方法上下文中 import）。

---

## 任务三：unified_retrieval_api.py 插入 5 个方法（第 615-616 行之间）

### 背景

5 位写手 skill 调用了以下方法，均不存在于 `UnifiedRetrievalAPI`，调用时 `AttributeError`：

| 写手 | 缺失方法 | skill 文件调用示例 |
|------|---------|-----------------|
| 苍澜 | `search_worldview_cases` | `api.search_worldview_cases(query="世界观设定", scene_type="世界观", limit=5)` |
| 玄一 | `search_plot_cases` | `api.search_plot_cases(query="伏笔埋设", scene_type="剧情", limit=5)` |
| 云溪 | `search_poetry_cases` | `api.search_poetry_cases(query="意境营造", scene_type="意境营造", limit=5)` |
| 墨言 | `search_character_cases` | `api.search_character_cases(query="人物成长", scene_type="人物", limit=5)` |
| 剑尘 | `search_battle_cases` | `api.search_battle_cases(query="修仙战斗", scene_type="战斗", limit=5)` |

底层 `search_cases()` 已存在（第 585 行），5 个新方法全部委托给它。

### 修改方法

打开 `core/retrieval/unified_retrieval_api.py`，找到第 **615 行** 和 **617 行**：

```python
        )                    # ← 第615行，search_cases 方法的最后一行

    def search_novel(        # ← 第617行
```

在第 615 行和第 617 行之间（即第 616 行的空行处），**插入以下代码块**（4个空格缩进，与类中其他方法一致）：

```python

    # ==================== 写手专属案例检索 ====================

    def search_worldview_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """世界观/势力案例检索（苍澜专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_plot_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """剧情/伏笔案例检索（玄一专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_poetry_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """意境/诗意案例检索（云溪专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_character_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """人物/情感案例检索（墨言专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

    def search_battle_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """战斗/力量案例检索（剑尘专用）"""
        return self.search_cases(query=query, scene_type=scene_type, top_k=limit)

```

插入后第 617 行（原 `def search_novel`）变成更靠后的行号，不影响功能。

---

## 任务四：新建测试文件 tests/test_ingest_sync_pipeline.py

**直接创建新文件** `tests/test_ingest_sync_pipeline.py`，内容如下（完整复制，不要改动）：

```python
"""
测试 inspiration-ingest 同步管线三处修复：
  1. hybrid_sync_manager: 99-从小说提取 目录技法 dimension 映射
  2. case_builder: sync_to_vectorstore 读取 .md 案例文件
  3. UnifiedRetrievalAPI: 5 个写手专属案例检索方法
"""
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


# ==================== 任务一：dimension 映射 ====================

class TestHybridSyncDimensionMapping:

    def test_normal_dir_uses_dimension_map(self):
        """原有维度目录（01-世界观维度 等）仍使用 DIMENSION_MAP"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {
            "01-世界观维度": "世界观维度",
            "04-战斗冲突维度": "战斗冲突维度",
        }
        md = MagicMock()
        md.parent.name = "04-战斗冲突维度"
        md.stem = "战斗技法汇总"

        parent_dir = md.parent.name
        dimension = md.stem if parent_dir == "99-从小说提取" else mgr.DIMENSION_MAP.get(parent_dir, "未知")
        assert dimension == "战斗冲突维度"

    def test_99_dir_uses_file_stem_as_dimension(self):
        """99-从小说提取 目录下的文件以 stem 作为 dimension，不再返回 '未知'"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {"01-世界观维度": "世界观维度"}

        for dim in ["战斗冲突维度", "世界观维度", "剧情维度", "人物维度", "氛围意境维度"]:
            md = MagicMock()
            md.parent.name = "99-从小说提取"
            md.stem = dim

            parent_dir = md.parent.name
            dimension = md.stem if parent_dir == "99-从小说提取" else mgr.DIMENSION_MAP.get(parent_dir, "未知")
            assert dimension == dim, f"期望 {dim}，实际 {dimension}"
            assert dimension != "未知"

    def test_unknown_dir_still_returns_unknown(self):
        """其他未知目录仍返回 '未知'"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {}

        md = MagicMock()
        md.parent.name = "99-其他目录"
        md.stem = "某文件"

        parent_dir = md.parent.name
        dimension = md.stem if parent_dir == "99-从小说提取" else mgr.DIMENSION_MAP.get(parent_dir, "未知")
        assert dimension == "未知"


# ==================== 任务二：.md 案例读取 ====================

class TestCaseBuilderMdSync:

    def test_parse_md_frontmatter_and_body(self):
        """能正确解析 YAML frontmatter 中的 case_id、scene_type 以及正文"""
        content = (
            "---\n"
            "case_id: slug-a\n"
            "scene_type: 战斗冲突维度\n"
            "source: 素材库/test/source.md\n"
            "---\n\n"
            "这是一段战斗描写内容。" * 30
        )
        meta = {}
        body = content
        if content.startswith("---"):
            end = content.find("---", 3)
            if end != -1:
                fm = content[3:end].strip()
                for line in fm.splitlines():
                    if ":" in line:
                        k, _, v = line.partition(":")
                        meta[k.strip()] = v.strip()
                body = content[end + 3:].strip()

        assert meta.get("case_id") == "slug-a"
        assert meta.get("scene_type") == "战斗冲突维度"
        assert "战斗描写内容" in body

    def test_dimension_mapped_to_scene_type(self):
        """维度名应映射为写手 skill 使用的场景类型字符串"""
        mapping = {
            "世界观维度": "世界观展示",
            "剧情维度": "剧情",
            "人物维度": "心理",
            "战斗冲突维度": "战斗",
            "氛围意境维度": "意境营造",
        }
        assert mapping["战斗冲突维度"] == "战斗"
        assert mapping["氛围意境维度"] == "意境营造"
        assert mapping["世界观维度"] == "世界观展示"
        assert mapping["剧情维度"] == "剧情"
        assert mapping["人物维度"] == "心理"

    def test_md_cases_collected_alongside_json(self):
        """sync 收集案例时应同时包含 JSON 和 .md 两种来源"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir) / "cases"

            # JSON 案例（原有路径：cases/战斗/*.json）
            json_dir = cases_dir / "战斗"
            json_dir.mkdir(parents=True)
            (json_dir / "case_001.json").write_text(
                json.dumps({
                    "case_id": "json-001", "scene_type": "战斗",
                    "content": "json内容" * 30, "genre": "玄幻",
                    "novel_name": "test", "word_count": 100,
                    "quality_score": 6.0, "emotion_value": 0.0,
                    "techniques": [], "keywords": [], "source_file": "a.txt"
                }),
                encoding="utf-8"
            )

            # .md 案例（ingest 路径：cases/99-从小说提取/战斗冲突维度/*.md）
            md_dir = cases_dir / "99-从小说提取" / "战斗冲突维度"
            md_dir.mkdir(parents=True)
            (md_dir / "novel-slug-a.md").write_text(
                "---\ncase_id: md-001\nscene_type: 战斗冲突维度\n---\n\n" + "战斗内容。" * 60,
                encoding="utf-8"
            )

            # 模拟修复后的收集逻辑
            all_cases = []
            for scene_dir in cases_dir.iterdir():
                if not scene_dir.is_dir():
                    continue
                for f in scene_dir.glob("*.json"):
                    all_cases.append(json.loads(f.read_text(encoding="utf-8")))

            ingest_dir = cases_dir / "99-从小说提取"
            if ingest_dir.exists():
                for md_file in ingest_dir.rglob("*.md"):
                    all_cases.append({"case_id": md_file.stem, "scene_type": "战斗"})

            assert len(all_cases) == 2, f"应有 2 条，实际 {len(all_cases)}"
            ids = {c["case_id"] for c in all_cases}
            assert "json-001" in ids
            assert "novel-slug-a" in ids

    def test_no_md_dir_does_not_crash(self):
        """99-从小说提取 目录不存在时不报错"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir) / "cases"
            cases_dir.mkdir()
            ingest_dir = cases_dir / "99-从小说提取"
            # 不创建该目录
            all_cases = []
            if ingest_dir.exists():
                for md_file in ingest_dir.rglob("*.md"):
                    all_cases.append({"case_id": md_file.stem})
            assert all_cases == []


# ==================== 任务三：写手专属案例方法 ====================

@pytest.fixture
def mock_api():
    mock_sm = MagicMock()
    mock_sm.search_case.return_value = [{"id": "c1", "content": "内容", "score": 0.85}]
    mock_sm.search_novel.return_value = []
    mock_sm.search_technique.return_value = []
    with patch("core.retrieval.unified_retrieval_api.HybridSearchManager", return_value=mock_sm):
        from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
        api = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
        api._search_manager = mock_sm
        yield api, mock_sm


class TestCaseSearchMethodsExist:

    def test_all_five_methods_exist(self, mock_api):
        """5 个写手专属案例方法必须存在"""
        api, _ = mock_api
        methods = [
            "search_worldview_cases",
            "search_plot_cases",
            "search_poetry_cases",
            "search_character_cases",
            "search_battle_cases",
        ]
        for m in methods:
            assert hasattr(api, m), f"UnifiedRetrievalAPI 缺失方法：{m}"

    def test_methods_call_search_case(self, mock_api):
        """每个方法调用后必须触发底层 _search_manager.search_case"""
        api, mock_sm = mock_api
        calls = [
            (api.search_worldview_cases, "世界观设定 势力冲突"),
            (api.search_plot_cases, "伏笔埋设"),
            (api.search_poetry_cases, "意境营造"),
            (api.search_character_cases, "人物成长"),
            (api.search_battle_cases, "修仙战斗"),
        ]
        for method, query in calls:
            mock_sm.search_case.reset_mock()
            method(query)
            mock_sm.search_case.assert_called_once(), f"{method.__name__} 未调用 search_case"

    def test_limit_parameter_passed_as_top_k(self, mock_api):
        """limit=5 应转换为 top_k=5 传给底层"""
        api, mock_sm = mock_api
        api.search_battle_cases("战斗", scene_type="战斗", limit=5)
        call_kwargs = mock_sm.search_case.call_args
        # top_k 可能在 args 或 kwargs 中
        top_k_val = call_kwargs.kwargs.get("top_k") or (call_kwargs.args[2] if len(call_kwargs.args) > 2 else None)
        assert top_k_val == 5, f"top_k 应为 5，实际 {top_k_val}"

    def test_positional_query_works(self, mock_api):
        """skill 里有直接位置参数调用的场景：api.search_battle_cases('xxx')"""
        api, mock_sm = mock_api
        result = api.search_battle_cases("战斗描写")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["score"] == 0.85

    def test_returns_list(self, mock_api):
        """所有方法返回值类型为 list"""
        api, _ = mock_api
        for m in ["search_worldview_cases", "search_plot_cases",
                  "search_poetry_cases", "search_character_cases", "search_battle_cases"]:
            result = getattr(api, m)("测试")
            assert isinstance(result, list), f"{m} 返回值不是 list"
```

---

## 验证步骤（4阶段，按顺序执行）

### 阶段1：新测试
```bash
cd D:/动画/众生界
python -m pytest tests/test_ingest_sync_pipeline.py -v 2>&1 | tee logs/test_ingest_sync_pipeline.log
```
预期：**全部通过**（共约15个测试）。

### 阶段2：回归（排除 mock 模拟测试文件）
```bash
python -m pytest tests/ -x --ignore=tests/test_unified_retrieval.py -q 2>&1 | tee logs/test_regression_ingest.log
```
预期：**无新增 FAILED**。

### 阶段3：dimension 冒烟
```bash
python -c "
import sys; sys.path.insert(0, '.')
from unittest.mock import MagicMock
from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
mgr = HybridSyncManager.__new__(HybridSyncManager)
mgr.DIMENSION_MAP = {'01-世界观维度': '世界观维度'}
md = MagicMock()
md.parent.name = '99-从小说提取'
md.stem = '战斗冲突维度'
parent_dir = md.parent.name
dimension = md.stem if parent_dir == '99-从小说提取' else mgr.DIMENSION_MAP.get(parent_dir, '未知')
assert dimension == '战斗冲突维度', f'期望战斗冲突维度，实际{dimension}'
print('dimension 映射修复 OK')
" 2>&1
```

### 阶段4：案例方法冒烟
```bash
python -c "
import sys; sys.path.insert(0, '.')
from unittest.mock import MagicMock, patch
mock_sm = MagicMock()
mock_sm.search_case.return_value = []
mock_sm.search_novel.return_value = []
mock_sm.search_technique.return_value = []
with patch('core.retrieval.unified_retrieval_api.HybridSearchManager', return_value=mock_sm):
    from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
    api = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
    api._search_manager = mock_sm
    for m in ['search_worldview_cases','search_plot_cases','search_poetry_cases','search_character_cases','search_battle_cases']:
        assert hasattr(api, m), f'缺失 {m}'
        getattr(api, m)('测试')
    print('5个案例方法全部存在且可调用 OK')
" 2>&1
```
