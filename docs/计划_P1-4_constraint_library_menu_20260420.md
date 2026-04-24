# 计划 P1-4:反模板约束库菜单化(语义改造,纯追加)

- **创建时间**:2026-04-20 (Asia/Shanghai)
- **执行者**:opencode (GLM5)
- **路线图位置**:[ROADMAP_众生界v2实施_20260419.md](./ROADMAP_众生界v2实施_20260419.md) §3.2 P1-4
- **依据设计**:[2026-04-19-inspiration-engine-design-v2.md](./superpowers/specs/2026-04-19-inspiration-engine-design-v2.md) §2 差异表(反模板约束库:从硬注入→鉴赏师菜单) + §3 组件命运表
- **上游依赖**:无(本计划仅改 `constraint_library.py`,与 P1-2 无交叉,可并行实施)
- **Python**:3.12.7(stdlib-only)
- **Shell**:bash

---

## 0. 本计划的目的 — 必读

v1 的反模板约束库是"生成端硬注入":`pick_for_variants` 随机抽 n 条,丢给变体生成器强制写手套用。
v2 的语义是"鉴赏师创意菜单":鉴赏师**浏览整库**,按场景过滤,结合记忆点库挑选**建议采纳**的条目注入到 prompt。

本计划**只追加 4 个新方法**到 `ConstraintLibrary`,**不删除**任何现有方法(老 API 仍服务于 variant_generator 直到 P1-5 删除)。数据文件 `anti_template_constraints.json` 结构不变。

### 0.1 范围边界(不得扩张)

- ✅ 修改 `core/inspiration/constraint_library.py`(仅追加 4 个方法,不改已有方法)
- ✅ 修改 `tests/test_constraint_library.py`(仅追加测试,不改已有测试)
- ❌ 不改 `config/dimensions/anti_template_constraints.json`(数据结构 + 内容保持)
- ❌ 不改 `core/inspiration/` 其他任何 `.py`(特别是 `variant_generator.py` / `workflow_bridge.py` / `__init__.py`)
- ❌ 不改 `tests/test_variant_generator.py`、`tests/test_workflow_integration.py`
- ❌ 不动 SKILL.md(鉴赏师 SKILL 的改造是 P1-3 的事)
- ❌ 不删老方法(`pick_for_variants` / `filter_by_scene_type` 等)— P1-5 会统一清理
- ❌ 不引入第三方依赖
- ❌ 不 git commit
- ❌ dispatcher / creative_contract 模块不得被触碰(P1-2 产物)

### 0.2 产出清单

| 文件 | 类型 | 验收 |
|------|------|------|
| `core/inspiration/constraint_library.py` | 修改(仅追加) | 4 个新方法通过所有新测试 |
| `tests/test_constraint_library.py` | 修改(仅追加) | 新增 ≥ 13 个用例全 PASS,既有用例 0 回归 |

### 0.3 新方法一览(API 契约,不得偏离)

```python
class ConstraintLibrary:
    # —— 以下为 P1-4 新增 ——

    def as_menu(self, scene_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """返回活跃约束列表(无随机化),用于鉴赏师浏览。

        Args:
            scene_type: 若给出,只返回 trigger_scene_types 包含它的条目;
                        None 则返回全部活跃条目。
        Returns:
            列表,每项为 dict,含 id / category / trigger_scene_types /
            constraint_text / intensity 五个字段(不含 status,已被筛为 active)。
            按 (category, id) 字典序排序。
        """

    def count_by_category(self) -> Dict[str, int]:
        """按类别统计活跃约束数。"""

    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """对活跃约束的 constraint_text 做 case-insensitive 子串搜索。

        空/纯空白 keyword → ValueError(不允许返回全库)。
        """

    def format_menu_text(self, scene_type: Optional[str] = None) -> str:
        """生成中文 Markdown 菜单,供鉴赏师 prompt 直接注入。

        格式示例:
            ## 反模板约束菜单(场景:战斗,共 12 条)

            ### 视角反叛 (3)
            - ANTI_001 [hard]:本场必须从败者视角
            - ANTI_005 [soft]:...

            ### 词汇剥夺 (2)
            - ...

        scene_type=None 时,标题改为"全部场景,共 N 条"。
        空(无匹配)时返回 "无可用约束"。
        """
```

---

## 1. 执行前真实状态

### 1.1 当前 `constraint_library.py` 公共 API

```
ConstraintLibrary.__init__(path=None)
ConstraintLibrary._load()            [内部]
ConstraintLibrary.list_active()
ConstraintLibrary.filter_by_scene_type(scene_type)
ConstraintLibrary.pick_for_variants(scene_type, n, seed=None)
ConstraintLibrary.get_by_id(constraint_id)
ConstraintLibrary.get_version()
ConstraintLibrary.count_total()
ConstraintLibrary.count_active()
ConstraintLibrary.list_categories()
```

**P1-4 后追加**(保持上述 10 个不变):

```
ConstraintLibrary.as_menu(scene_type=None)
ConstraintLibrary.count_by_category()
ConstraintLibrary.search_by_keyword(keyword)
ConstraintLibrary.format_menu_text(scene_type=None)
```

### 1.2 `anti_template_constraints.json` 真实结构(不改)

每条约束含 6 字段:`id` / `category` / `trigger_scene_types` / `constraint_text` / `intensity` / `status`。
当前 45 条全 `status="active"`。

### 1.3 pytest 基线

- **若 P1-2 已完成**:基线 `548 passed / 1 skipped`(506 + 42)
- **若 P1-2 未做或与本计划并行**:基线 `506 passed / 1 skipped`

本计划完成后应 `+N`,N ≥ 13。

---

## 2. opencode 执行规则(不可违反)

### 2.1 允许

1. Edit 工具在 `core/inspiration/constraint_library.py` **现有类最后一个方法 `list_categories` 之后**追加 4 个新方法(纯追加,不改前面任何行)
2. Edit 工具在 `tests/test_constraint_library.py` **文件末尾追加**新的测试函数(不改前面任何行)
3. 每个新方法按 TDD:先写测试 → 跑测试见 FAIL → 写实现 → 跑测试见 PASS

### 2.2 禁止

- ❌ 不改既有方法(`list_active` / `filter_by_scene_type` / `pick_for_variants` 等保持 100% 原样)
- ❌ 不动 `__init__.py` 的 `__all__`(鉴赏师是否导出 4 个新方法由 P1-3 决定)
- ❌ 不改 JSON 数据文件
- ❌ 不引第三方库
- ❌ 不 git commit
- ❌ 不跳步(6 Task 全做)

### 2.3 TDD 严格执行

每个 Task 内部按 "先写测试 → 跑测试见 FAIL → 写实现 → 跑测试见 PASS"。

---

## 3. 执行步骤

### Task 1:扩展测试 fixture(复用现有 `sample_constraints_file` + 增加多类别版本)

**现有 fixture** `sample_constraints_file`(tests/test_constraint_library.py 第 19-54 行)只有 3 条约束且 category 不够多。本 Task 追加一个多类别 fixture,为 as_menu / count_by_category / format_menu_text 测试使用。

#### 步骤

- [ ] **1.1 打开 `tests/test_constraint_library.py`,在文件末尾追加**:

```python
# =========================================================================
# P1-4 新增:反模板约束库菜单化(as_menu / count_by_category /
#           search_by_keyword / format_menu_text)
# =========================================================================


@pytest.fixture
def multi_category_constraints_file(tmp_path):
    """P1-4 专用 fixture:覆盖 3 类别、多场景、含 disabled 条目。"""
    data = {
        "version": "1.0",
        "created_at": "2026-04-20",
        "constraints": [
            {
                "id": "ANTI_001",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗", "高潮"],
                "constraint_text": "本场必须从败者视角写,禁止全知视角",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_002",
                "category": "视角反叛",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "全程从旁观者视角描写",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_010",
                "category": "词汇剥夺",
                "trigger_scene_types": ["战斗", "情感"],
                "constraint_text": "禁用任何力量/强度类形容词",
                "intensity": "hard",
                "status": "active",
            },
            {
                "id": "ANTI_011",
                "category": "词汇剥夺",
                "trigger_scene_types": ["情感"],
                "constraint_text": "禁用色彩词",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_020",
                "category": "情绪逆压",
                "trigger_scene_types": ["情感"],
                "constraint_text": "克制冷静笔调,禁止情绪化描写",
                "intensity": "soft",
                "status": "active",
            },
            {
                "id": "ANTI_099",
                "category": "已弃用",
                "trigger_scene_types": ["战斗"],
                "constraint_text": "不应出现在任何 menu 中",
                "intensity": "hard",
                "status": "disabled",
            },
        ],
    }
    path = tmp_path / "multi_category.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path
```

- [ ] **1.2 跑**(应 0 新测、0 失败):

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_constraint_library.py -v
```

预期:既有用例全 PASS(等同于基线)。此 Task 只加 fixture,不加用例。

---

### Task 2:`as_menu()` 基本路径(无筛选)

#### 步骤

- [ ] **2.1 追加测试**:

```python
def test_as_menu_no_filter_returns_all_active(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    assert isinstance(menu, list)
    # 5 active(跳过 ANTI_099 disabled)
    assert len(menu) == 5
    ids = {c["id"] for c in menu}
    assert ids == {"ANTI_001", "ANTI_002", "ANTI_010", "ANTI_011", "ANTI_020"}


def test_as_menu_items_contain_expected_fields(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    item = menu[0]
    # 5 字段齐全(status 不含,因为已筛为 active)
    for f in ("id", "category", "trigger_scene_types", "constraint_text", "intensity"):
        assert f in item, f"缺字段 {f}"
    assert "status" not in item  # 不对外暴露筛选字段


def test_as_menu_sorted_by_category_then_id(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    keys = [(c["category"], c["id"]) for c in menu]
    assert keys == sorted(keys)


def test_as_menu_skips_disabled(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu()
    ids = {c["id"] for c in menu}
    assert "ANTI_099" not in ids
```

- [ ] **2.2 跑测试**:`python -m pytest tests/test_constraint_library.py -v`。
  预期:4 个新用例 FAIL(`as_menu` 未定义)。

- [ ] **2.3 追加实现**(到 `core/inspiration/constraint_library.py` 末尾,`list_categories` 之后):

```python
    # ============================================================
    # P1-4 新增:菜单化语义(鉴赏师浏览 API)
    # ============================================================

    def as_menu(self, scene_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """返回活跃约束的菜单视图(不随机、不采样)。

        Args:
            scene_type: None 返回全部活跃条目;否则只含 trigger_scene_types 包含该场景的条目。
        Returns:
            List[dict],每项 5 字段:id / category / trigger_scene_types /
            constraint_text / intensity(不含 status)。
            按 (category, id) 字典序排序。
        """
        if scene_type is None:
            pool = self.list_active()
        else:
            pool = self.filter_by_scene_type(scene_type)
        items = [
            {
                "id": c["id"],
                "category": c["category"],
                "trigger_scene_types": list(c.get("trigger_scene_types", [])),
                "constraint_text": c["constraint_text"],
                "intensity": c["intensity"],
            }
            for c in pool
        ]
        items.sort(key=lambda c: (c["category"], c["id"]))
        return items
```

- [ ] **2.4 跑测试**:4 个用例 PASS。

---

### Task 3:`as_menu(scene_type)` 场景过滤

#### 步骤

- [ ] **3.1 追加测试**:

```python
def test_as_menu_filtered_by_battle(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu(scene_type="战斗")
    ids = {c["id"] for c in menu}
    # ANTI_001, ANTI_002, ANTI_010 触发场景含"战斗";ANTI_099 disabled 排除
    assert ids == {"ANTI_001", "ANTI_002", "ANTI_010"}


def test_as_menu_filtered_by_emotion(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    menu = lib.as_menu(scene_type="情感")
    ids = {c["id"] for c in menu}
    # ANTI_010, ANTI_011, ANTI_020 触发场景含"情感"
    assert ids == {"ANTI_010", "ANTI_011", "ANTI_020"}


def test_as_menu_filtered_by_unknown_scene_empty(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    assert lib.as_menu(scene_type="不存在的场景") == []
```

- [ ] **3.2 跑测试**:预期全 PASS(Task 2 的实现已覆盖 scene_type 分支)。

若 FAIL:检查 Task 2.3 `as_menu` 是否正确调用 `filter_by_scene_type`。

累计 Task 2+3 新增 7 用例。

---

### Task 4:`count_by_category()`

#### 步骤

- [ ] **4.1 追加测试**:

```python
def test_count_by_category_basic(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    counts = lib.count_by_category()
    # 视角反叛: 2 (ANTI_001, ANTI_002)
    # 词汇剥夺: 2 (ANTI_010, ANTI_011)
    # 情绪逆压: 1 (ANTI_020)
    # 已弃用:   0 (ANTI_099 disabled,不计入)
    assert counts == {"视角反叛": 2, "词汇剥夺": 2, "情绪逆压": 1}
    assert "已弃用" not in counts


def test_count_by_category_returns_dict(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    counts = lib.count_by_category()
    assert isinstance(counts, dict)


def test_count_by_category_empty_on_all_disabled(tmp_path):
    """所有约束 disabled → 空 dict。"""
    data = {
        "version": "1.0",
        "constraints": [
            {"id": "X1", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "t", "intensity": "soft",
             "status": "disabled"},
        ],
    }
    path = tmp_path / "all_disabled.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    lib = ConstraintLibrary(path)
    assert lib.count_by_category() == {}
```

- [ ] **4.2 跑测试**:预期 3 个 FAIL。

- [ ] **4.3 追加实现**(到 `as_menu` 之后):

```python
    def count_by_category(self) -> Dict[str, int]:
        """按类别统计活跃约束数(disabled 不计入)。"""
        counts: Dict[str, int] = {}
        for c in self.list_active():
            cat = c.get("category", "")
            counts[cat] = counts.get(cat, 0) + 1
        return counts
```

- [ ] **4.4 跑测试**:3 个 PASS。累计 10。

---

### Task 5:`search_by_keyword(keyword)`

#### 步骤

- [ ] **5.1 追加测试**:

```python
def test_search_by_keyword_substring(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    results = lib.search_by_keyword("视角")
    ids = {c["id"] for c in results}
    # ANTI_001 "败者视角"、ANTI_002 "旁观者视角" 命中;其他不含"视角"
    assert ids == {"ANTI_001", "ANTI_002"}


def test_search_by_keyword_no_match_returns_empty(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    assert lib.search_by_keyword("没有这个词") == []


def test_search_by_keyword_case_insensitive(tmp_path):
    """英文大小写不敏感。"""
    data = {
        "version": "1.0",
        "constraints": [
            {"id": "X1", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "FOO bar baz",
             "intensity": "hard", "status": "active"},
            {"id": "X2", "category": "A",
             "trigger_scene_types": ["X"],
             "constraint_text": "没有关键词",
             "intensity": "hard", "status": "active"},
        ],
    }
    path = tmp_path / "case.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    lib = ConstraintLibrary(path)
    for kw in ("foo", "FOO", "Foo", "fOo"):
        results = lib.search_by_keyword(kw)
        assert {c["id"] for c in results} == {"X1"}, f"keyword {kw!r} 未命中"


def test_search_by_keyword_skips_disabled(multi_category_constraints_file):
    """disabled 条目不进入搜索结果,即使内容命中。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    # ANTI_099 的 constraint_text "不应出现在任何 menu 中" 含"不应"
    results = lib.search_by_keyword("不应")
    assert results == []


def test_search_by_keyword_empty_raises():
    from core.inspiration.constraint_library import ConstraintLibrary, DEFAULT_CONSTRAINTS_PATH
    lib = ConstraintLibrary(DEFAULT_CONSTRAINTS_PATH)
    with pytest.raises(ValueError, match="keyword"):
        lib.search_by_keyword("")
    with pytest.raises(ValueError, match="keyword"):
        lib.search_by_keyword("   ")


def test_search_by_keyword_returns_full_fields(multi_category_constraints_file):
    """返回项字段 = as_menu 的 5 字段(统一对外形状)。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    results = lib.search_by_keyword("视角")
    for r in results:
        for f in ("id", "category", "trigger_scene_types",
                  "constraint_text", "intensity"):
            assert f in r
        assert "status" not in r
```

- [ ] **5.2 跑测试**:6 个 FAIL。

- [ ] **5.3 追加实现**:

```python
    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """对活跃约束的 constraint_text 做 case-insensitive 子串搜索。

        Args:
            keyword: 非空字符串,纯空白视为非法。
        Returns:
            与 as_menu 字段一致的 dict 列表(不含 status)。
        Raises:
            ValueError: keyword 为空或纯空白。
        """
        if not keyword or not keyword.strip():
            raise ValueError("search_by_keyword.keyword 必须非空")
        needle = keyword.lower()
        out: List[Dict[str, Any]] = []
        for c in self.list_active():
            if needle in c.get("constraint_text", "").lower():
                out.append(
                    {
                        "id": c["id"],
                        "category": c["category"],
                        "trigger_scene_types": list(c.get("trigger_scene_types", [])),
                        "constraint_text": c["constraint_text"],
                        "intensity": c["intensity"],
                    }
                )
        return out
```

- [ ] **5.4 跑测试**:6 个 PASS。累计 16。

---

### Task 6:`format_menu_text(scene_type)`

#### 步骤

- [ ] **6.1 追加测试**:

```python
def test_format_menu_text_header_all_scenes(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    assert text.startswith("## 反模板约束菜单")
    assert "全部场景" in text
    assert "共 5 条" in text


def test_format_menu_text_header_scene_specific(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="战斗")
    assert "场景:战斗" in text
    assert "共 3 条" in text


def test_format_menu_text_category_grouping(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # 3 个分类标题都出现
    assert "### 视角反叛" in text
    assert "### 词汇剥夺" in text
    assert "### 情绪逆压" in text
    # 分类计数
    assert "视角反叛 (2)" in text
    assert "词汇剥夺 (2)" in text
    assert "情绪逆压 (1)" in text


def test_format_menu_text_item_lines(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # 每条: "- ANTI_XXX [intensity]: constraint_text"
    assert "- ANTI_001 [hard]:本场必须从败者视角写" in text
    assert "- ANTI_002 [soft]:全程从旁观者视角描写" in text
    assert "- ANTI_020 [soft]:克制冷静笔调" in text


def test_format_menu_text_filtered_category_omitted(multi_category_constraints_file):
    """场景过滤后空的 category 不出现。"""
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="情感")
    # 情感场景:ANTI_010(词汇剥夺) + ANTI_011(词汇剥夺) + ANTI_020(情绪逆压)= 3 条
    # "视角反叛" 不匹配"情感",应缺席
    assert "### 视角反叛" not in text
    assert "### 词汇剥夺" in text
    assert "### 情绪逆压" in text


def test_format_menu_text_empty_returns_no_items_marker(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text(scene_type="不存在")
    assert "无可用约束" in text
    assert "共 0 条" in text


def test_format_menu_text_disabled_excluded(multi_category_constraints_file):
    lib = ConstraintLibrary(multi_category_constraints_file)
    text = lib.format_menu_text()
    # ANTI_099 是 disabled,constraint_text 不得出现
    assert "ANTI_099" not in text
    assert "不应出现在任何 menu 中" not in text
```

- [ ] **6.2 跑测试**:7 个 FAIL。

- [ ] **6.3 追加实现**:

```python
    def format_menu_text(self, scene_type: Optional[str] = None) -> str:
        """生成中文 Markdown 菜单,供鉴赏师 prompt 注入。

        标题:`## 反模板约束菜单(场景:XXX | 全部场景,共 N 条)`
        分组:按 category,小节 `### {category} ({n})`
        条目:`- {id} [{intensity}]:{constraint_text}`
        无匹配:追加一行 `无可用约束`。
        """
        items = self.as_menu(scene_type=scene_type)
        scene_label = f"场景:{scene_type}" if scene_type else "全部场景"
        lines: List[str] = [f"## 反模板约束菜单({scene_label},共 {len(items)} 条)"]
        if not items:
            lines.append("")
            lines.append("无可用约束")
            return "\n".join(lines)

        # 保持 as_menu 已按 (category, id) 排序的顺序
        from itertools import groupby
        for category, group in groupby(items, key=lambda c: c["category"]):
            group_list = list(group)
            lines.append("")
            lines.append(f"### {category} ({len(group_list)})")
            for c in group_list:
                lines.append(
                    f"- {c['id']} [{c['intensity']}]:{c['constraint_text']}"
                )
        return "\n".join(lines)
```

- [ ] **6.4 跑测试**:7 个 PASS。累计 23。

---

### Task 7:回归确认 + 全量

#### 步骤

- [ ] **7.1 跑本模块**:

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_constraint_library.py -v
```

预期:新增用例 ≥ 13 全 PASS(Task 2+3+4+5+6 = 4+3+3+6+7 = 23),既有用例 0 回归。

- [ ] **7.2 跑全量**:

```bash
python -m pytest tests/ -v --tb=short 2>&1 | tee docs/m7_artifacts/p1-4_test_log_20260420.txt | tail -30
```

- [ ] **7.3 最后一行应是 `N passed, 1 skipped`**(N = P1-2 后基线 + 本计划 23 ≈ 548 + 23 = 571,或 P1-2 未做时 506 + 23 = 529)。若出现 failed → **停止报告**。

---

## 4. 文件最终结构

`constraint_library.py` 完成后:

```
原有内容(1-115 行,保持不变)
    class ConstraintLibrary:
        __init__ / _load / list_active / filter_by_scene_type /
        pick_for_variants / get_by_id / get_version /
        count_total / count_active / list_categories
    # =========== P1-4 新增(追加在 list_categories 之后)===========
        as_menu / count_by_category / search_by_keyword / format_menu_text
```

---

## 5. 自检命令

```bash
cd "D:/动画/众生界"

echo "===== P1-4 自检开始 ====="

# 文件存在且语法 OK
python -c "import ast; ast.parse(open('core/inspiration/constraint_library.py', encoding='utf-8').read())" \
  && echo "PASS-S1 impl 语法 OK" || echo "FAIL-S1"

# 4 个新方法存在
python -c "
from core.inspiration.constraint_library import ConstraintLibrary
for m in ('as_menu', 'count_by_category', 'search_by_keyword', 'format_menu_text'):
    assert hasattr(ConstraintLibrary, m), f'{m} 缺失'
print('4 新方法存在')
" && echo "PASS-M1 新方法齐全" || echo "FAIL-M1"

# 既有方法未被误删
python -c "
from core.inspiration.constraint_library import ConstraintLibrary
for m in ('list_active', 'filter_by_scene_type', 'pick_for_variants',
         'get_by_id', 'get_version', 'count_total', 'count_active',
         'list_categories'):
    assert hasattr(ConstraintLibrary, m), f'{m} 被误删'
print('8 旧方法保留')
" && echo "PASS-M2 旧方法保留" || echo "FAIL-M2"

# 真实约束库 smoke(45 条)
python -c "
from core.inspiration.constraint_library import ConstraintLibrary
lib = ConstraintLibrary()
menu = lib.as_menu()
text = lib.format_menu_text()
assert len(menu) >= 30, f'活跃约束过少: {len(menu)}'
assert '反模板约束菜单' in text
print(f'真实库: {len(menu)} 活跃条, {len(lib.count_by_category())} 类')
" && echo "PASS-R0 真实库 smoke" || echo "FAIL-R0"

# 模块测试
python -m pytest tests/test_constraint_library.py --tb=short 2>&1 | tail -5
if python -m pytest tests/test_constraint_library.py --tb=no -q 2>&1 | tail -1 | grep -qE "failed"; then
  echo "FAIL-T1 有 failed"
else
  echo "PASS-T1 模块全 PASS"
fi

# 新测试数量
count=$(python -m pytest tests/test_constraint_library.py --collect-only -q 2>&1 | grep -c "::test_")
echo "模块总测试数:$count"

# 保护性:其他文件未动
for f in variant_generator.py workflow_bridge.py appraisal_agent.py creative_contract.py dispatcher.py __init__.py; do
  # dispatcher.py 可能不存在(P1-2 未做),用 -f 检查
  path="core/inspiration/$f"
  if [ ! -f "$path" ] && [ "$f" = "dispatcher.py" ]; then
    echo "SKIP-P $f 尚未创建(P1-2 未做)"
    continue
  fi
  status=$(git status --short "$path" | head -1)
  if [ -z "$status" ]; then
    echo "PASS-P $f 未动"
  else
    echo "FAIL-P $f 被改动: $status"
  fi
done

# JSON 数据不得改
status=$(git status --short "config/dimensions/anti_template_constraints.json" | head -1)
if [ -z "$status" ]; then
  echo "PASS-J1 JSON 数据未动"
else
  echo "FAIL-J1 JSON 被改:$status"
fi

# 全量
python -m pytest tests/ --tb=no -q 2>&1 | tail -1 | tee /tmp/p1-4_summary.txt
if grep -qE "^[0-9]+ passed.*[0-9]+ skipped" /tmp/p1-4_summary.txt; then
  echo "PASS-R1 全量跑通"
else
  echo "FAIL-R1"
fi

hash=$(git log -1 --format=%h)
echo "HEAD=$hash"
[ "$hash" = "8365fe21a" ] && echo "PASS-G1 HEAD 未动" || echo "FAIL-G1 HEAD 改变"

echo "===== P1-4 自检结束 ====="
```

任一 `FAIL-` → **立即停止,不得声称完成**,报告 Claude。

---

## 6. 完成判据

- [x] 7 个 Task 全部 TDD 完成
- [x] 23+ 新测试全 PASS
- [x] `core/inspiration/constraint_library.py` 仅追加 4 个方法,前 115 行原样保留
- [x] 既有 10 个方法无改动,既有测试 0 回归
- [x] `anti_template_constraints.json` 未动
- [x] 其他 `core/inspiration/*.py` 未动(dispatcher.py 不在此限,由 P1-2 负责)
- [x] 全量 pytest 0 failed
- [x] 无 git commit
- [x] §5 所有 `PASS-` 标记,无 `FAIL-`

---

## 7. 完成后更新 ROADMAP

1. §3.2 P1-4 行改 ✅,备注 "4 新方法,23 新用例全 PASS"
2. §5 时间线追加:

```
| 2026-04-20 | Claude | 写 P1-4 计划 | docs/计划_P1-4_constraint_library_menu_20260420.md |
| 2026-04-20 | opencode | P1-4 约束库菜单化完成 | as_menu/count_by_category/search_by_keyword/format_menu_text + 23 新用例全 PASS |
| 2026-04-20 | Claude | P1-4 §5 自检(全 PASS,HEAD 未 commit) | - |
```

3. §3 "★ 当前任务指针" 按批量计划的下一项更新(见 `计划_overnight_batch_20260420.md`)

---

## 8. 下一步

- Claude 核验 §5 自检 → 全 PASS → 写 P1-3 / P1-5 / P1-6 / P1-7 计划(按 overnight 调度器指示)
- FAIL → 报告作者,不改 ROADMAP

---

**计划结束。opencode 按 Task 1 → Task 7 顺序 TDD 执行。**
