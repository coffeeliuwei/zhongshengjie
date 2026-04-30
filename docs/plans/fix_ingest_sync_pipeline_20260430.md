# 计划：inspiration-ingest 同步管线全量修复
# 日期：2026-04-30 01:52 (Asia/Shanghai)
# 协议：docs/opencode_dev_protocol_20260420.md v1

---

## 问题背景

通过 `novel-inspiration-ingest` 新增的内容，存在三处断裂：

| # | 严重 | 问题 | 位置 |
|---|------|------|------|
| P1 | 🔴 | `hybrid_sync_manager` 对 `99-从小说提取/` 目录下的技法文件，`dimension` 字段写成 `"未知"`，写手 17 个维度专属检索方法全部找不到 | `modules/knowledge_base/hybrid_sync_manager.py` 第 406-407 行 |
| P2 | 🔴🔴 | `case_builder.py --sync` 的 `sync_to_vectorstore` 只 glob `*.json`、只遍历一层子目录，inspiration-ingest 写入的 `.md` 案例文件（两层深、非 JSON）永远进不了 `case_library_v2` | `tools/case_builder.py` 第 2130-2138 行 |
| P3 | 🟠 | `UnifiedRetrievalAPI` 缺少 5 个写手专属案例检索方法，skill 调用时 AttributeError | `core/retrieval/unified_retrieval_api.py` 第 615 行后 |

---

## 任务一：修复技法 dimension 映射（hybrid_sync_manager.py）

**文件**：`modules/knowledge_base/hybrid_sync_manager.py`

**问题代码**（第 405-408 行）：
```python
for md_file in md_files:
    try:
        parent_dir = md_file.parent.name
        dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
```

**修复**：当父目录是 `99-从小说提取` 时，改用**文件名（stem）**作为 dimension，因为 inspiration-ingest 用维度名命名文件（如 `战斗冲突维度.md`）。

把第 406-408 行替换为：
```python
        parent_dir = md_file.parent.name
        if parent_dir == "99-从小说提取":
            # inspiration-ingest 以维度名命名文件：战斗冲突维度.md → "战斗冲突维度"
            dimension = md_file.stem
        else:
            dimension = self.DIMENSION_MAP.get(parent_dir, "未知")
```

其余代码不变。

---

## 任务二：修复案例 sync 读取 .md 文件（case_builder.py）

**文件**：`tools/case_builder.py`

**问题代码**（第 2128-2138 行）：
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

**问题**：
1. 只读 `*.json`，inspiration-ingest 写的是 `.md`
2. 只遍历一层，`99-从小说提取/{维度名}/{slug}.md` 在两层深
3. `.md` 案例的 `scene_type` 字段值是维度名（如 `"战斗冲突维度"`），与写手 skill 过滤用的场景类型（如 `"战斗"`）不一致

**修复**：在收集 JSON 案例的循环之后，追加读取 `.md` 案例的逻辑。把整个"收集所有案例"块替换为：

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

        def _parse_md_case(md_file: Path) -> dict:
            """解析 inspiration-ingest 写入的 .md 案例（frontmatter + 正文）"""
            text = md_file.read_text(encoding="utf-8")
            # 解析 YAML frontmatter（--- 到 --- 之间）
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
            # 规范化 scene_type：维度名 → 场景类型
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

        # 路径一：原有 JSON 案例（一层子目录，*.json）
        for scene_dir in self.cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue
            for meta_file in scene_dir.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        all_cases.append(json.load(f))
                except Exception:
                    continue

        # 路径二：inspiration-ingest 写入的 .md 案例（两层子目录）
        # 结构：cases/99-从小说提取/{维度名}/{slug}-a.md
        ingest_dir = self.cases_dir / "99-从小说提取"
        if ingest_dir.exists():
            for md_file in ingest_dir.rglob("*.md"):
                try:
                    all_cases.append(_parse_md_case(md_file))
                except Exception as e:
                    print(f"    [跳过 md] {md_file.name}: {e}")
                    continue
```

注意：`_parse_md_case` 和 `_DIMENSION_TO_SCENE_TYPE` 定义在 `sync_to_vectorstore` 方法内部，不需要改类接口。

---

## 任务三：补全 5 个写手专属案例检索方法（unified_retrieval_api.py）

**文件**：`core/retrieval/unified_retrieval_api.py`

**插入位置**：第 615 行（`search_cases` 结束的 `)`）和第 617 行（`def search_novel(`）之间的空行处。

插入内容：
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

---

## 任务四：新建测试文件 `tests/test_ingest_sync_pipeline.py`

完整文件内容：

```python
"""
测试 inspiration-ingest 同步管线修复：
  1. hybrid_sync_manager 对 99-从小说提取 目录的 dimension 映射
  2. case_builder sync_to_vectorstore 读取 .md 案例
  3. UnifiedRetrievalAPI 5 个写手专属案例检索方法
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import tempfile
import json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


# ==================== Task 1: dimension 映射 ====================

class TestHybridSyncDimensionMapping:
    """99-从小说提取 目录下的技法文件应以文件名作为 dimension"""

    def test_normal_dir_still_uses_map(self):
        """原有维度目录仍用 DIMENSION_MAP"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {
            "01-世界观维度": "世界观维度",
            "04-战斗冲突维度": "战斗冲突维度",
        }
        # 模拟文件在 04-战斗冲突维度/ 下
        md = MagicMock()
        md.parent.name = "04-战斗冲突维度"
        md.stem = "战斗技法汇总"

        parent_dir = md.parent.name
        if parent_dir == "99-从小说提取":
            dimension = md.stem
        else:
            dimension = mgr.DIMENSION_MAP.get(parent_dir, "未知")

        assert dimension == "战斗冲突维度"

    def test_99_dir_uses_filename_as_dimension(self):
        """99-从小说提取 目录下的文件应以文件名（stem）作为 dimension"""
        from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
        mgr = HybridSyncManager.__new__(HybridSyncManager)
        mgr.DIMENSION_MAP = {"01-世界观维度": "世界观维度"}

        md = MagicMock()
        md.parent.name = "99-从小说提取"
        md.stem = "战斗冲突维度"

        parent_dir = md.parent.name
        if parent_dir == "99-从小说提取":
            dimension = md.stem
        else:
            dimension = mgr.DIMENSION_MAP.get(parent_dir, "未知")

        assert dimension == "战斗冲突维度"
        assert dimension != "未知"

    def test_various_dimension_files(self):
        """所有维度名文件都能正确映射"""
        dims = [
            "世界观维度", "剧情维度", "人物维度",
            "战斗冲突维度", "氛围意境维度", "叙事维度",
        ]
        for dim in dims:
            md = MagicMock()
            md.parent.name = "99-从小说提取"
            md.stem = dim
            parent_dir = md.parent.name
            dimension = md.stem if parent_dir == "99-从小说提取" else "未知"
            assert dimension == dim, f"dimension 应为 {dim}，实际 {dimension}"


# ==================== Task 2: .md 案例读取 ====================

class TestCaseBuilderMdSync:
    """sync_to_vectorstore 应读取 99-从小说提取 下的 .md 案例"""

    def _make_md_content(self, case_id="test-a", scene_type="战斗冲突维度",
                          body="这是一段战斗描写，山崩地裂，剑气纵横。" * 20):
        return f"""---
case_id: {case_id}
scene_type: {scene_type}
source: 素材库/test/source.md
why_good: 战斗节奏感强
---

{body}"""

    def test_parse_md_frontmatter(self):
        """能正确解析 frontmatter 和正文"""
        content = self._make_md_content()
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
        assert meta.get("case_id") == "test-a"
        assert meta.get("scene_type") == "战斗冲突维度"
        assert len(body) > 50

    def test_dimension_to_scene_type_mapping(self):
        """维度名应被映射为写手 skill 使用的场景类型"""
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

    def test_md_cases_collected_in_sync(self):
        """sync_to_vectorstore 收集案例时应包含 .md 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir) / "cases"
            # 创建 JSON 案例（原有路径）
            json_dir = cases_dir / "战斗"
            json_dir.mkdir(parents=True)
            (json_dir / "case_001.json").write_text(
                json.dumps({"case_id": "j1", "scene_type": "战斗", "content": "json内容" * 20,
                            "genre": "玄幻", "novel_name": "test", "word_count": 100,
                            "quality_score": 6.0, "emotion_value": 0.0,
                            "techniques": [], "keywords": [], "source_file": "a.txt"}),
                encoding="utf-8"
            )
            # 创建 .md 案例（inspiration-ingest 路径）
            md_dir = cases_dir / "99-从小说提取" / "战斗冲突维度"
            md_dir.mkdir(parents=True)
            (md_dir / "novel-slug-a.md").write_text(
                "---\ncase_id: md-001\nscene_type: 战斗冲突维度\n---\n\n" + "战斗内容" * 50,
                encoding="utf-8"
            )

            # 模拟收集逻辑
            all_cases = []
            for scene_dir in cases_dir.iterdir():
                if not scene_dir.is_dir():
                    continue
                for f in scene_dir.glob("*.json"):
                    all_cases.append(json.loads(f.read_text(encoding="utf-8")))

            ingest_dir = cases_dir / "99-从小说提取"
            if ingest_dir.exists():
                for md_file in ingest_dir.rglob("*.md"):
                    all_cases.append({"case_id": md_file.stem, "scene_type": "战斗", "content": "x"})

            assert len(all_cases) == 2, f"应有 2 条案例，实际 {len(all_cases)}"
            ids = {c["case_id"] for c in all_cases}
            assert "j1" in ids
            assert "novel-slug-a" in ids


# ==================== Task 3: 写手专属案例方法 ====================

class TestCaseSearchMethodsExist:
    @pytest.fixture
    def api(self):
        mock_sm = MagicMock()
        mock_sm.search_case.return_value = [{"id": "c1", "content": "内容", "score": 0.8}]
        mock_sm.search_novel.return_value = []
        mock_sm.search_technique.return_value = []
        with patch("core.retrieval.unified_retrieval_api.HybridSearchManager", return_value=mock_sm):
            from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
            a = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
            a._search_manager = mock_sm
            return a, mock_sm

    def test_all_five_methods_exist(self, api):
        a, _ = api
        for m in ["search_worldview_cases", "search_plot_cases",
                  "search_poetry_cases", "search_character_cases", "search_battle_cases"]:
            assert hasattr(a, m), f"缺失 {m}"

    def test_methods_delegate_to_search_case(self, api):
        a, mock_sm = api
        a.search_battle_cases("修仙战斗", scene_type="战斗", limit=5)
        mock_sm.search_case.assert_called_once()

    def test_positional_query_works(self, api):
        a, mock_sm = api
        result = a.search_battle_cases("战斗描写")
        assert isinstance(result, list)
```

---

## 验证步骤（4阶段）

### 阶段1：新增测试
```bash
cd D:/动画/众生界
python -m pytest tests/test_ingest_sync_pipeline.py -v 2>&1 | tee logs/test_ingest_sync_$(date +%Y%m%d_%H%M%S).log
```
预期：全部通过。

### 阶段2：回归
```bash
python -m pytest tests/ -x --ignore=tests/test_unified_retrieval.py -q 2>&1 | tee logs/test_regression_$(date +%Y%m%d_%H%M%S).log
```
预期：无新增 FAILED。

### 阶段3：dimension 冒烟（手工验证修复代码路径）
```bash
python -c "
import sys; sys.path.insert(0, '.')
from unittest.mock import MagicMock
from modules.knowledge_base.hybrid_sync_manager import HybridSyncManager
mgr = HybridSyncManager.__new__(HybridSyncManager)
mgr.DIMENSION_MAP = {'99-从小说提取': None}

md = MagicMock()
md.parent.name = '99-从小说提取'
md.stem = '战斗冲突维度'
parent_dir = md.parent.name
dimension = md.stem if parent_dir == '99-从小说提取' else mgr.DIMENSION_MAP.get(parent_dir, '未知')
assert dimension == '战斗冲突维度', f'期望 战斗冲突维度，实际 {dimension}'
print('dimension 映射修复 ✓')
" 2>&1
```

### 阶段4：.md 案例收集冒烟
```bash
python -c "
import sys, tempfile, json
from pathlib import Path
sys.path.insert(0, '.')
with tempfile.TemporaryDirectory() as d:
    cases = Path(d) / 'cases'
    (cases / '99-从小说提取' / '战斗冲突维度').mkdir(parents=True)
    (cases / '99-从小说提取' / '战斗冲突维度' / 'slug-a.md').write_text(
        '---\ncase_id: md-001\nscene_type: 战斗冲突维度\n---\n\n内容' * 20, encoding='utf-8')
    found = list((cases / '99-从小说提取').rglob('*.md'))
    assert len(found) == 1
    print(f'.md 案例收集 ✓，找到 {len(found)} 条')
" 2>&1
```
