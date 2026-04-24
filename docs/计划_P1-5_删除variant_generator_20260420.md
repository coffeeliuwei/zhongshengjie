# 计划 P1-5：删除多变体生成器（variant_generator）

- **创建时间**：2026-04-20 (Asia/Shanghai)
- **执行者**：opencode (GLM5)
- **参考协议**：docs/opencode_dev_protocol_20260420.md v1
- **分支**：v2-dev
- **预计时长**：20-30 分钟
- **预计 pytest 变化**：629 passed 3 failed → ≥ 622 passed 0 failed（移除 7 个 test_variant_generator 测试 + 修复 1 个 integration 测试 + 跳过 1 个 orchestration 测试）

---

## 背景

`core/inspiration/variant_generator.py` 是 v1 灵感引擎的核心——它生成 N 个约束变体供鉴赏师选择。
v2 设计彻底废弃这条路：v2 不生成变体，而是阶段 5.5 三方协商后由派单器分发创意契约给写手。

本任务将：
1. 把 `variant_generator.py` 归档到 `.archived/`
2. 把 `tests/test_variant_generator.py` 归档到 `.archived/`
3. 清理两个调用文件（`workflow_bridge.py`、`__init__.py`）
4. 更新两个测试文件以消除对已删模块的引用
5. 全量 pytest 通过

---

## 步骤 0：前置核验（必须全 PASS 才继续）

```bash
cd "D:/动画/众生界"

echo "=== 步骤 0 前置核验 ==="

# 0.1 分支
git branch --show-current | grep -q "v2-dev" && echo "PASS-0.1 分支 v2-dev" || { echo "FAIL-0.1 不在 v2-dev"; exit 1; }

# 0.2 HEAD
git log -1 --format="%h" | grep -qE "0e89b5221|[0-9a-f]{9}" && echo "PASS-0.2 HEAD=$(git log -1 --format='%h %s')" || echo "WARN-0.2 HEAD 非预期,但继续"

# 0.3 variant_generator.py 存在
test -f "core/inspiration/variant_generator.py" && echo "PASS-0.3 variant_generator.py 存在" || { echo "FAIL-0.3 文件不存在"; exit 1; }

# 0.4 test_variant_generator.py 存在
test -f "tests/test_variant_generator.py" && echo "PASS-0.4 test_variant_generator.py 存在" || { echo "FAIL-0.4 文件不存在"; exit 1; }

# 0.5 .archived 目录存在或可创建
mkdir -p .archived && echo "PASS-0.5 .archived 目录就绪"

# 0.6 pytest 基线（只跑关键模块，快速确认）
python -m pytest tests/test_variant_generator.py tests/test_workflow_integration.py --tb=no -q 2>&1 | tee /tmp/p1_5_baseline.txt
grep -E "passed|failed" /tmp/p1_5_baseline.txt | tail -1

echo "=== 步骤 0 完成，进入实施 ==="
```

---

## 步骤 1：归档 variant_generator.py

```bash
cd "D:/动画/众生界"

# 归档（保留原文件内容，移到 .archived）
cp core/inspiration/variant_generator.py .archived/variant_generator_v1_20260420.py
rm core/inspiration/variant_generator.py

test -f ".archived/variant_generator_v1_20260420.py" && echo "PASS-1.1 归档成功"
test ! -f "core/inspiration/variant_generator.py" && echo "PASS-1.2 原文件已删除"
```

---

## 步骤 2：归档 tests/test_variant_generator.py

```bash
cd "D:/动画/众生界"

cp tests/test_variant_generator.py .archived/test_variant_generator_v1_20260420.py
rm tests/test_variant_generator.py

test -f ".archived/test_variant_generator_v1_20260420.py" && echo "PASS-2.1 测试归档成功"
test ! -f "tests/test_variant_generator.py" && echo "PASS-2.2 原测试已删除"
```

---

## 步骤 3：修改 core/inspiration/workflow_bridge.py

**目标**：移除对 `variant_generator` 和 `ConstraintLibrary` 的依赖，简化 `phase1_dispatch()`。

### 3.1 移除两行 import

找到文件中这两行：

```python
from core.inspiration.constraint_library import ConstraintLibrary
from core.inspiration.variant_generator import generate_variant_specs
```

**删除这两行**（整行删除，不留空行）。

### 3.2 替换 phase1_dispatch 函数体

找到现有的 `phase1_dispatch` 函数（从 `def phase1_dispatch(` 到函数结束），**完整替换**为：

```python
def phase1_dispatch(
    scene_type: str,
    scene_context: Dict[str, Any],
    original_writers: List[str],
    config: Dict[str, Any],
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Stage 4 Phase 1 分发器（v2：变体模式已移除，始终返回原始写手列表）

    v1 多变体生成逻辑已由 P1-5 删除（variant_generator.py 已归档至 .archived/）。
    v2 创意注入由阶段 5.5 三方协商完成（P2-1 接入）。

    Args:
        scene_type: 场景类型（保留参数兼容旧调用方，暂未使用）
        scene_context: 场景上下文（保留参数兼容旧调用方，暂未使用）
        original_writers: 原始写手列表（中文名）
        config: 配置字典（保留参数兼容旧调用方，暂未使用）
        seed: 随机种子（保留参数兼容旧调用方，暂未使用）

    Returns:
        {"mode": "original", "writers": original_writers}
    """
    return {"mode": "original", "writers": original_writers}
```

### 3.3 验证 workflow_bridge.py

```bash
cd "D:/动画/众生界"

# 确认 variant_generator 引用已消失
grep -n "variant_generator\|generate_variant_specs\|ConstraintLibrary" core/inspiration/workflow_bridge.py && echo "FAIL-3.1 还有残留引用" || echo "PASS-3.1 无残留引用"

# 确认 phase1_dispatch 可 import
python -c "from core.inspiration.workflow_bridge import phase1_dispatch; r = phase1_dispatch('战斗', {}, ['剑尘'], {}); assert r == {'mode': 'original', 'writers': ['剑尘']}, r; print('PASS-3.2 phase1_dispatch 返回正确')"
```

---

## 步骤 4：修改 core/inspiration/__init__.py

**目标**：从导出表中移除 `generate_variant_specs` 和 `get_variant_count_from_config`。

### 4.1 删除 import 块

找到这两行：

```python
from core.inspiration.variant_generator import (
    generate_variant_specs,
    get_variant_count_from_config,
)
```

**整块删除**（3 行全删）。

### 4.2 删除 __all__ 中的两个条目

找到 `__all__` 列表中的这两行：

```python
    "generate_variant_specs",
    "get_variant_count_from_config",
```

**删除这两行**。

### 4.3 更新模块 docstring（可选但推荐）

找到文件头部的 docstring：

```python
"""灵感引擎（Inspiration Engine）

意外性引擎，与现有评估系统并列的双引擎之一。
- 反模板约束库 + 多变体生成 = 制造多样性
- 鉴赏师 Agent = 选最活的
- 记忆点库 + 反馈回流 = 校准审美
```

替换为：

```python
"""灵感引擎（Inspiration Engine）v2

v2 双引擎：意外性引擎 + 质量评估引擎并列。
- 反模板约束库 + 鉴赏师菜单查询 = 制造多样性（v2）
- 三方协商（作者 + 鉴赏师 + 评估师）= 达成创意契约
- 派单器 = 把创意契约分发给对应写手重写
- 记忆点库 + 反馈回流 = 校准审美

v1 多变体生成（variant_generator）已由 P1-5 移除。
"""
```

### 4.4 验证 __init__.py

```bash
cd "D:/动画/众生界"

# 确认无残留引用
grep -n "variant_generator\|generate_variant_specs\|get_variant_count" core/inspiration/__init__.py && echo "FAIL-4.1 还有残留" || echo "PASS-4.1 无残留"

# 确认整个 inspiration 包可 import
python -c "import core.inspiration; print('PASS-4.2 包 import 成功'); print('导出符号数:', len(core.inspiration.__all__))"
```

---

## 步骤 5：修改 tests/test_workflow_integration.py

**目标**：移除 `test_integration_chain` 中对 `variant_generator` 的调用，并修正断言。

找到 `test_integration_chain` 函数中的 **"# 2. variant_generator"** 代码块：

```python
    # 2. variant_generator
    from core.inspiration.variant_generator import generate_variant_specs

    specs = generate_variant_specs(
        scene_type="战斗",
        scene_context={"outline": "X"},
        writer_agent="novelist-jianchen",
        n=3,
        constraint_library=lib,
        seed=42,
    )
    assert len(specs) == 3

    # 3. workflow_bridge
    from core.inspiration.workflow_bridge import phase1_dispatch
    from core.config_loader import DEFAULT_CONFIG

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "X"},
        original_writers=["剑尘"],
        config=DEFAULT_CONFIG,
        seed=42,
    )
    assert result["mode"] == "variants"
    assert len(result["variant_specs"]) == 3
```

**替换为**：

```python
    # 2. workflow_bridge（v2：phase1_dispatch 始终返回 original 模式）
    from core.inspiration.workflow_bridge import phase1_dispatch
    from core.config_loader import DEFAULT_CONFIG

    result = phase1_dispatch(
        scene_type="战斗",
        scene_context={"outline": "X"},
        original_writers=["剑尘"],
        config=DEFAULT_CONFIG,
        seed=42,
    )
    assert result["mode"] == "original"
    assert result["writers"] == ["剑尘"]
```

**注意**：注释编号从 "# 3." 变成 "# 2."（因为原来的 2 被删了，现在合并）。

### 验证：

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_workflow_integration.py --tb=short -q 2>&1 | tail -5
```

---

## 步骤 6：修改 tests/test_inspiration_orchestration.py

**目标**：`test_stage4_full_flow_with_mocks` 测试的是 v1 Stage 4 全流程（phase1_dispatch 生成变体 → execute_variants → select_winner → record_winner）。v2 已废弃此路径，需要跳过该测试。

找到函数定义行：

```python
def test_stage4_full_flow_with_mocks():
    """Stage 4 完整流程：specs → 变体生成 → 鉴赏师 → 记录"""
```

**在函数定义行的前一行**插入装饰器：

```python
@pytest.mark.skip(reason="v2 P1-5: variant flow 已移除；v2 Stage 4 全流程待 P2 集成后重写")
def test_stage4_full_flow_with_mocks():
    """Stage 4 完整流程：specs → 变体生成 → 鉴赏师 → 记录"""
```

**确认文件顶部有 `import pytest`**（通常已有）。如果没有，在文件第一行或 import 块中添加 `import pytest`。

### 验证：

```bash
cd "D:/动画/众生界"
python -m pytest tests/test_inspiration_orchestration.py --tb=short -q 2>&1 | tail -5
```

---

## 步骤 7：全量 pytest 验证

```bash
cd "D:/动画/众生界"

python -m pytest tests/ --tb=short -q 2>&1 | tee /tmp/p1_5_final.txt

# 验收标准：
# - test_variant_generator.py 的 7 个测试已消失（归档）
# - test_stage4_full_flow_with_mocks 变为 SKIPPED
# - 其余全 passed
# - failed 数量 ≤ 3（预存在的 scene_writer_mapping.json 缺陷，非本任务引入）
tail -3 /tmp/p1_5_final.txt

# 核心断言：failed 不超过预存在的 3 个
FAIL_COUNT=$(grep -oP "\d+ failed" /tmp/p1_5_final.txt | grep -oP "\d+")
[ -z "$FAIL_COUNT" ] && FAIL_COUNT=0
[ "$FAIL_COUNT" -le 3 ] && echo "PASS-7.1 failed 数量 $FAIL_COUNT ≤ 3" || { echo "FAIL-7.1 新增了 failed：$FAIL_COUNT"; exit 1; }

grep -qE "passed" /tmp/p1_5_final.txt && echo "PASS-7.2 有通过的测试"
```

---

## 步骤 8：commit

```bash
cd "D:/动画/众生界"

git add \
  .archived/variant_generator_v1_20260420.py \
  .archived/test_variant_generator_v1_20260420.py \
  core/inspiration/workflow_bridge.py \
  core/inspiration/__init__.py \
  tests/test_workflow_integration.py \
  tests/test_inspiration_orchestration.py

git status --short

git commit -m "feat(p1-5): remove variant_generator; simplify phase1_dispatch to original-only

v2 不再生成多变体——创意注入改由阶段 5.5 三方协商完成（P2-1 接入）。

变更：
- core/inspiration/variant_generator.py → .archived/（7 函数归档）
- tests/test_variant_generator.py → .archived/（7 tests 归档）
- workflow_bridge.py: 移除 generate_variant_specs/ConstraintLibrary 导入；
  phase1_dispatch() 始终返回 {mode: original, writers: ...}
- __init__.py: 移除 generate_variant_specs / get_variant_count_from_config 导出
- tests/test_workflow_integration.py: 移除 variant 调用，断言改为 mode=original
- tests/test_inspiration_orchestration.py: skip test_stage4_full_flow_with_mocks

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 步骤 9：最终自检清单

```bash
cd "D:/动画/众生界"

echo "=== P1-5 最终自检 ==="

# 9.1 归档文件存在
test -f ".archived/variant_generator_v1_20260420.py" && echo "PASS-9.1 variant_generator 已归档" || echo "FAIL-9.1"
test -f ".archived/test_variant_generator_v1_20260420.py" && echo "PASS-9.2 test_variant_generator 已归档" || echo "FAIL-9.2"

# 9.2 原文件不存在
test ! -f "core/inspiration/variant_generator.py" && echo "PASS-9.3 原文件已删除" || echo "FAIL-9.3 原文件仍存在"
test ! -f "tests/test_variant_generator.py" && echo "PASS-9.4 原测试已删除" || echo "FAIL-9.4"

# 9.3 无残留引用（生产代码中）
grep -rn "variant_generator\|generate_variant_specs\|get_variant_count_from_config" \
  core/ --include="*.py" | grep -v __pycache__ && echo "FAIL-9.5 生产代码有残留" || echo "PASS-9.5 生产代码无残留"

# 9.4 phase1_dispatch 行为正确
python -c "
from core.inspiration.workflow_bridge import phase1_dispatch
r = phase1_dispatch('战斗', {}, ['剑尘'], {'inspiration_engine': {'enabled': True}})
assert r == {'mode': 'original', 'writers': ['剑尘']}, f'返回值错误: {r}'
r2 = phase1_dispatch('情感', {}, ['云溪'], {'inspiration_engine': {'enabled': False}})
assert r2 == {'mode': 'original', 'writers': ['云溪']}, f'返回值错误: {r2}'
print('PASS-9.6 phase1_dispatch enabled=True/False 均返回 original')
"

# 9.5 commit 已落
git log -1 --format="%h %s" | grep -q "p1-5\|P1-5\|variant_generator" && echo "PASS-9.7 commit 已落" || echo "FAIL-9.7 未 commit"

echo "=== P1-5 自检完成 ==="
```

---

## opencode 权限边界

- ✅ 可以：修改上述 6 个文件，创建 `.archived/` 下的文件
- ✅ 可以：commit 到 v2-dev
- ❌ 不可以：修改任何其他 skill 文件
- ❌ 不可以：修改 `core/inspiration/dispatcher.py`、`creative_contract.py`（P1-2/1/7 成果）
- ❌ 不可以：push 到 remote

---

## 完成后状态

P1-5 完成后，P1 阶段全部 ✅，进入 P2 workflow 集成阶段。
下一步：Claude 写 P2-1 计划（阶段 5.5 三方协商接入 workflow.py）。
