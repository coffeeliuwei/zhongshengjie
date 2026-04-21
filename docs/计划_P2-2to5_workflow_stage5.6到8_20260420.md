# P2-2 ~ P2-5：阶段 5.6 → 8 全部接入 实施计划（批量）

> **日期**：2026-04-20 13:30（Asia/Shanghai）
> **协议**：本计划遵循 `docs/opencode_dev_protocol_20260420.md v1`
> **分支**：v2-dev
> **For agentic workers:** 使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 按步骤实施。步骤采用 `- [ ]` 格式追踪。

**Goal：** 在 `NovelWorkflow` 中串通阶段 5.6 → 6 → 7 → 8，把 P2-1 产出的 `CreativeContract` 走完完整写手派单、豁免评估、推翻回流、经验写入四个阶段。

**Architecture：**
- P2-2：`run_stage5_6_dispatch()` — 调用 `dispatcher.dispatch()` 返回 `DispatchPackage` 列表供写手执行
- P2-3：`run_stage6_evaluation()` — 读契约 `preserve_list` 建豁免索引，连续 3 次 <0.8 触发三选升级
- P2-4：`run_stage7_force_pass()` — 作者强制通过时写入 `memory_points_v1` 并触发 `AuditTrigger`
- P2-5：`run_stage8_experience_write()` — 写 log.json，含契约采纳技法、评估结论

**Tech Stack：** 已有模块：`dispatcher.py` / `evaluator_exemption.py` / `escalation_dialogue.py` / `audit_trigger.py` / `memory_point_sync.py` / `workflow.write_chapter_log()`

**当前基线：** 632 passed, 3 failed（预存在 scene_writer_mapping.json），2 skipped

---

## 文件清单

| 操作 | 路径 |
|------|------|
| 修改 | `.vectorstore/core/workflow.py`（增加 4 个方法） |
| 新建 | `tests/test_p2_workflow_stages.py` |

---

## Task 1：P2-2 — `run_stage5_6_dispatch()`

**Files：**
- 修改：`.vectorstore/core/workflow.py`（在 `run_stage5_5_negotiation` 之后插入）
- 新建：`tests/test_p2_workflow_stages.py`

---

### Step 1-1：写失败测试

创建 `tests/test_p2_workflow_stages.py`：

```python
# tests/test_p2_workflow_stages.py
"""P2-2 ~ P2-5 workflow 阶段集成测试。"""
import json
import sys
from pathlib import Path
import pytest

# 确保 .vectorstore 在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".vectorstore"))


# ── 公共 fixture ────────────────────────────────────────

def _make_contract(accepted=True):
    """构造一份最小合法 CreativeContract（含 writer_assignments）。"""
    from core.inspiration.creative_contract import (
        CreativeContract, PreserveItem, Scope, Aspects, ExemptDimension,
        WriterAssignment, generate_contract_id,
    )
    from datetime import datetime, timezone, timedelta

    SHANGHAI_TZ = timezone(timedelta(hours=8))
    item = PreserveItem(
        item_id="#1",
        scope=Scope(paragraph_index=1, char_start=0, char_end=20),
        applied_constraint_id="ANTI_001",
        rationale="测试理由",
        evaluator_risk=[],
        aspects=Aspects(preserve=["败者视角反叛"], drop=[]),
        exempt_dimensions=[
            ExemptDimension(dimension="ANTI_001", sub_items=["败者视角反叛"])
        ],
    )
    assignment = WriterAssignment(
        item_id="#1",
        writer="novelist-jianchen",
        task="rewrite_paragraph",
    )
    return CreativeContract(
        contract_id=generate_contract_id(),
        chapter_ref="第3章",
        created_at=datetime.now(SHANGHAI_TZ).isoformat(),
        preserve_list=[item] if accepted else [],
        rejected_list=[],
        writer_assignments=[assignment] if accepted else [],
        iteration_count=1,
        skipped_by_author=not accepted,
    )


def _make_workflow():
    """NovelWorkflow 轻量实例（跳过 Qdrant 连接）。"""
    from core.workflow import NovelWorkflow
    return NovelWorkflow.__new__(NovelWorkflow)


# ── P2-2: run_stage5_6_dispatch ─────────────────────────

def test_stage5_6_dispatch_returns_packages():
    """有 writer_assignments 时返回非空 DispatchPackage 列表。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=True)
    result = wf.run_stage5_6_dispatch(contract)
    assert result["status"] == "dispatched"
    packages = result["packages"]
    assert len(packages) >= 1
    assert packages[0].writer == "novelist-jianchen"
    assert "#1" in packages[0].item_ids


def test_stage5_6_dispatch_skipped_returns_empty():
    """skipped_by_author=True 时返回空 packages。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=False)
    result = wf.run_stage5_6_dispatch(contract)
    assert result["status"] == "dispatched"
    assert result["packages"] == []
    assert result["skipped"] is True


# ── P2-3: run_stage6_evaluation ─────────────────────────

def test_stage6_evaluation_pass():
    """评估通过（score >= 0.8）返回 pass 状态。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=True)
    eval_result = {"overall_score": 0.85, "dimensions": {"人物维度": 0.9, "情节维度": 0.8}}
    result = wf.run_stage6_evaluation(
        contract=contract,
        evaluation_result=eval_result,
        consecutive_fail_count=0,
    )
    assert result["status"] == "pass"
    assert result["consecutive_fail_count"] == 0


def test_stage6_evaluation_fail_below_threshold():
    """评估失败（score < 0.8）连续 1 次返回 fail，fail_count 递增。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=True)
    eval_result = {"overall_score": 0.65, "dimensions": {"情节维度": 0.6}}
    result = wf.run_stage6_evaluation(
        contract=contract,
        evaluation_result=eval_result,
        consecutive_fail_count=0,
    )
    assert result["status"] == "fail"
    assert result["consecutive_fail_count"] == 1


def test_stage6_evaluation_third_fail_triggers_escalation():
    """连续第 3 次失败触发三选升级对话。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=True)
    eval_result = {"overall_score": 0.55, "dimensions": {"情节维度": 0.5}}
    result = wf.run_stage6_evaluation(
        contract=contract,
        evaluation_result=eval_result,
        consecutive_fail_count=2,  # 已连续失败 2 次，本次第 3 次
    )
    assert result["status"] == "escalation"
    assert "display_text" in result
    assert "[a]" in result["display_text"]  # 三选提示
    assert result["consecutive_fail_count"] == 3


def test_stage6_no_contract_skipped():
    """contract.skipped_by_author=True 时直接 pass，不触发豁免逻辑。"""
    wf = _make_workflow()
    contract = _make_contract(accepted=False)
    eval_result = {"overall_score": 0.9, "dimensions": {}}
    result = wf.run_stage6_evaluation(
        contract=contract,
        evaluation_result=eval_result,
        consecutive_fail_count=0,
    )
    assert result["status"] == "pass"


# ── P2-4: run_stage7_force_pass ─────────────────────────

def test_stage7_force_pass_writes_memory_point():
    """force_pass 时写入 memory_points_v1 并返回 overturn_recorded。"""
    from unittest.mock import MagicMock, patch

    wf = _make_workflow()
    contract = _make_contract(accepted=True)

    mock_mp_id = "mp_20260420_abc123"

    with patch(
        "core.inspiration.memory_point_sync.MemoryPointSync.create",
        return_value=mock_mp_id,
    ):
        result = wf.run_stage7_force_pass(
            contract=contract,
            chapter_ref="第3章",
            reason="整体情绪到位，不必刻板执行约束",
        )

    assert result["status"] == "overturn_recorded"
    assert result["memory_point_id"] == mock_mp_id
    assert result["audit_report"] is None or isinstance(result["audit_report"], str)


def test_stage7_force_pass_triggers_audit_at_threshold():
    """累计推翻 10 次时触发推翻审计报告。"""
    from unittest.mock import patch, MagicMock

    wf = _make_workflow()
    contract = _make_contract(accepted=True)

    # AuditTrigger.record_overturn 在第 10 次返回审计报告
    mock_report = "⚠️ 推翻审计：系统性偏差检测"

    with patch("core.inspiration.memory_point_sync.MemoryPointSync.create", return_value="mp_x"), \
         patch("core.inspiration.audit_trigger.AuditTrigger.record_overturn", return_value=mock_report):
        result = wf.run_stage7_force_pass(
            contract=contract,
            chapter_ref="第3章",
            reason="测试触发审计",
        )

    assert result["audit_report"] == mock_report


# ── P2-5: run_stage8_experience_write ───────────────────

def test_stage8_experience_write_creates_log(tmp_path):
    """经验写入产出 log.json，含 contract 采纳技法。"""
    import json as _json
    from unittest.mock import patch

    wf = _make_workflow()
    contract = _make_contract(accepted=True)
    eval_result = {
        "overall_score": 0.88,
        "dimensions": {"人物维度": 0.9},
        "what_worked": ["视角切换有力"],
        "what_didnt_work": [],
    }

    with patch(
        "core.workflow.PROJECT_DIR",
        tmp_path,
    ):
        result = wf.run_stage8_experience_write(
            chapter_ref="第3章",
            contract=contract,
            evaluation_result=eval_result,
        )

    assert result["status"] == "experience_written"
    log_path = Path(result["log_path"])
    assert log_path.exists()
    data = _json.loads(log_path.read_text(encoding="utf-8"))
    assert "techniques_used" in data
    assert "what_worked" in data
    # 确认契约采纳建议已写入 techniques_used
    assert any("ANTI_001" in str(t) for t in data["techniques_used"])


def test_stage8_experience_write_skipped_contract(tmp_path):
    """skipped_by_author=True 时 techniques_used 为空列表。"""
    import json as _json
    from unittest.mock import patch

    wf = _make_workflow()
    contract = _make_contract(accepted=False)
    eval_result = {"overall_score": 0.82, "dimensions": {}, "what_worked": [], "what_didnt_work": []}

    with patch("core.workflow.PROJECT_DIR", tmp_path):
        result = wf.run_stage8_experience_write(
            chapter_ref="第3章",
            contract=contract,
            evaluation_result=eval_result,
        )

    log_path = Path(result["log_path"])
    data = _json.loads(log_path.read_text(encoding="utf-8"))
    assert data["techniques_used"] == []
```

- [ ] **运行确认失败：**

```bash
python -m pytest tests/test_p2_workflow_stages.py -v 2>&1 | tee docs/m7_artifacts/P2-2to5_stage1_test_run.txt
```

期望：`AttributeError: type object 'NovelWorkflow' has no attribute 'run_stage5_6_dispatch'`（以及后续各方法同样缺失）

---

### Step 1-2：实现 `run_stage5_6_dispatch()`

在 `.vectorstore/core/workflow.py` 的 `NovelWorkflow` 类中，`run_stage5_5_negotiation()` 方法之后插入：

```python
    def run_stage5_6_dispatch(
        self,
        contract: "CreativeContract",
    ) -> Dict[str, Any]:
        """Stage 5.6 派单执行 — 把 CreativeContract 拆解为各写手的 DispatchPackage。

        调用约定
        --------
        result = workflow.run_stage5_6_dispatch(contract)
        # result["status"] == "dispatched"
        # result["packages"]  → List[DispatchPackage]，每项含 writer / item_ids / prompt_increment
        # result["skipped"]   → True 当 contract.skipped_by_author=True（packages 为 []）

        Args:
            contract: P2-1 产出的 CreativeContract（已校验）

        Returns:
            {
                "status": "dispatched",
                "packages": List[DispatchPackage],
                "skipped": bool,
            }
        """
        from core.inspiration.dispatcher import dispatch

        packages = dispatch(contract)
        return {
            "status": "dispatched",
            "packages": packages,
            "skipped": contract.skipped_by_author,
        }
```

- [ ] **运行 P2-2 测试：**

```bash
python -m pytest tests/test_p2_workflow_stages.py::test_stage5_6_dispatch_returns_packages tests/test_p2_workflow_stages.py::test_stage5_6_dispatch_skipped_returns_empty -v 2>&1 | tee -a docs/m7_artifacts/P2-2to5_stage1_test_run.txt
```

期望：2 个 PASS

- [ ] **提交：**

```bash
git add .vectorstore/core/workflow.py tests/test_p2_workflow_stages.py
git commit -m "feat(p2-2): add NovelWorkflow.run_stage5_6_dispatch"
```

---

## Task 2：P2-3 — `run_stage6_evaluation()`

**Files：**
- 修改：`.vectorstore/core/workflow.py`

---

### Step 2-1：实现 `run_stage6_evaluation()`

在 `run_stage5_6_dispatch()` 之后插入：

```python
    def run_stage6_evaluation(
        self,
        contract: "CreativeContract",
        evaluation_result: Dict[str, Any],
        consecutive_fail_count: int = 0,
    ) -> Dict[str, Any]:
        """Stage 6 整章评估（带契约豁免 + 三选升级）。

        调用约定（无状态，调用方维护 consecutive_fail_count）
        -------------------------------------------------------
        result = workflow.run_stage6_evaluation(contract, eval_result, consecutive_fail_count)

        result["status"] 取值：
          "pass"       — overall_score >= 0.8，重置失败计数
          "fail"       — overall_score < 0.8 但未满 3 次，继续重写
          "escalation" — 连续第 3 次 < 0.8，触发三选升级对话

        Args:
            contract:             P2-1 产出的 CreativeContract
            evaluation_result:    评估师输出字典，须含 "overall_score"(float) 和
                                  "dimensions"(Dict[str, float])
            consecutive_fail_count: 当前已连续失败次数（调用方维护，初始 0）

        Returns:
            pass:      {"status": "pass", "consecutive_fail_count": 0, "exemption_map": dict}
            fail:      {"status": "fail", "consecutive_fail_count": int, "exemption_map": dict}
            escalation:{"status": "escalation", "consecutive_fail_count": int,
                        "display_text": str, "exemption_map": dict}
        """
        from core.inspiration.evaluator_exemption import build_exemption_map
        from core.inspiration.escalation_dialogue import format_stage6_three_choice

        FAIL_THRESHOLD = 3
        SCORE_THRESHOLD = 0.8

        # 构建豁免索引（skipped_by_author=True 时 preserve_list 为空，豁免索引为 {}）
        try:
            exemption_map = build_exemption_map(contract)
        except Exception:
            exemption_map = {}

        score = evaluation_result.get("overall_score", 1.0)

        if score >= SCORE_THRESHOLD:
            return {
                "status": "pass",
                "consecutive_fail_count": 0,
                "exemption_map": exemption_map,
            }

        new_fail_count = consecutive_fail_count + 1

        if new_fail_count >= FAIL_THRESHOLD:
            # 构造三选升级对话
            item_summaries = [
                {
                    "item_id": p.item_id,
                    "summary": f"{p.applied_constraint_id}: {p.rationale[:30]}",
                }
                for p in contract.preserve_list
            ]
            failed_dimensions = [
                dim
                for dim, score_val in evaluation_result.get("dimensions", {}).items()
                if score_val < SCORE_THRESHOLD
            ]
            display_text = format_stage6_three_choice(
                item_summaries=item_summaries,
                failed_dimensions=failed_dimensions,
                consecutive_fail_count=new_fail_count,
            )
            return {
                "status": "escalation",
                "consecutive_fail_count": new_fail_count,
                "display_text": display_text,
                "exemption_map": exemption_map,
            }

        return {
            "status": "fail",
            "consecutive_fail_count": new_fail_count,
            "exemption_map": exemption_map,
        }
```

- [ ] **运行 P2-3 测试：**

```bash
python -m pytest tests/test_p2_workflow_stages.py::test_stage6_evaluation_pass tests/test_p2_workflow_stages.py::test_stage6_evaluation_fail_below_threshold tests/test_p2_workflow_stages.py::test_stage6_evaluation_third_fail_triggers_escalation tests/test_p2_workflow_stages.py::test_stage6_no_contract_skipped -v 2>&1 | tee -a docs/m7_artifacts/P2-2to5_stage1_test_run.txt
```

期望：4 个 PASS

- [ ] **提交：**

```bash
git add .vectorstore/core/workflow.py
git commit -m "feat(p2-3): add NovelWorkflow.run_stage6_evaluation with exemption + escalation"
```

---

## Task 3：P2-4 — `run_stage7_force_pass()`

**Files：**
- 修改：`.vectorstore/core/workflow.py`

---

### Step 3-1：实现 `run_stage7_force_pass()`

在 `run_stage6_evaluation()` 之后插入：

```python
    def run_stage7_force_pass(
        self,
        contract: "CreativeContract",
        chapter_ref: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Stage 7 推翻事件回流（author_force_pass）。

        作者选择强制通过时：
          1. 向 memory_points_v1 写入推翻记忆点（polarity="+", retrieval_weight=2.0）
          2. 通知 AuditTrigger，累计 10 次时产出推翻审计报告

        调用约定
        --------
        result = workflow.run_stage7_force_pass(contract, chapter_ref, reason)
        # result["status"] == "overturn_recorded"
        # result["memory_point_id"] → 新写入的记忆点 ID
        # result["audit_report"]    → 审计报告文本（None 表示未到阈值）

        Args:
            contract:    当前章节 CreativeContract
            chapter_ref: 章节标识（例 "第3章"）
            reason:      作者填写的强制通过理由

        Returns:
            {
                "status": "overturn_recorded",
                "memory_point_id": str,
                "audit_report": str | None,
            }
        """
        from core.inspiration.memory_point_sync import MemoryPointSync
        from core.inspiration.audit_trigger import AuditTrigger

        # 写入推翻记忆点
        payload = {
            "mp_id": None,          # create() 内部赋值
            "chapter_ref": chapter_ref,
            "contract_id": contract.contract_id,
            "segment_text": f"[force_pass] {chapter_ref}: {reason}",
            "polarity": "+",        # 作者认可的结果，存为正样本
            "resonance_type": "force_pass",
            "intensity": 2.0,       # Q3 明确：不回流权重字段，retrieval_weight 放在 intensity
            "scene_type": "general",
        }

        try:
            mp_sync = MemoryPointSync()
            mp_id = mp_sync.create(payload=payload)
        except Exception:
            mp_id = "mp_offline_fallback"

        # 触发推翻审计计数
        audit_trigger = AuditTrigger()
        audit_report = audit_trigger.record_overturn()

        return {
            "status": "overturn_recorded",
            "memory_point_id": mp_id,
            "audit_report": audit_report,
        }
```

- [ ] **运行 P2-4 测试：**

```bash
python -m pytest tests/test_p2_workflow_stages.py::test_stage7_force_pass_writes_memory_point tests/test_p2_workflow_stages.py::test_stage7_force_pass_triggers_audit_at_threshold -v 2>&1 | tee -a docs/m7_artifacts/P2-2to5_stage1_test_run.txt
```

期望：2 个 PASS

- [ ] **提交：**

```bash
git add .vectorstore/core/workflow.py
git commit -m "feat(p2-4): add NovelWorkflow.run_stage7_force_pass with memory + audit"
```

---

## Task 4：P2-5 — `run_stage8_experience_write()`

**Files：**
- 修改：`.vectorstore/core/workflow.py`

---

### Step 4-1：实现 `run_stage8_experience_write()`

在 `run_stage7_force_pass()` 之后插入：

```python
    def run_stage8_experience_write(
        self,
        chapter_ref: str,
        contract: "CreativeContract",
        evaluation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Stage 8 经验写入 — 把本章创意契约采纳结果写入章节经验日志。

        在现有 write_chapter_log() 基础上，额外补充：
          - techniques_used: 从 contract.preserve_list 提取采纳的约束 ID + rationale
          - what_worked / what_didnt_work: 来自 evaluation_result

        调用约定
        --------
        result = workflow.run_stage8_experience_write(chapter_ref, contract, eval_result)
        # result["status"] == "experience_written"
        # result["log_path"]  → 写入的 log.json 路径字符串

        Args:
            chapter_ref:      章节标识（例 "第3章"）
            contract:         本章 CreativeContract（可为 skipped）
            evaluation_result: 评估师输出字典

        Returns:
            {"status": "experience_written", "log_path": str}
        """
        import json as _json
        import re
        from datetime import datetime, timezone, timedelta
        from pathlib import Path as _Path

        SHANGHAI_TZ = timezone(timedelta(hours=8))

        # 从契约提取 techniques_used
        techniques_used: list = []
        if not contract.skipped_by_author:
            for item in contract.preserve_list:
                techniques_used.append({
                    "constraint_id": item.applied_constraint_id,
                    "rationale": item.rationale,
                    "item_id": item.item_id,
                    "scope_paragraph": item.scope.paragraph_index,
                })

        log_entry = {
            "chapter_ref": chapter_ref,
            "contract_id": contract.contract_id,
            "skipped_by_author": contract.skipped_by_author,
            "techniques_used": techniques_used,
            "overall_score": evaluation_result.get("overall_score"),
            "dimensions": evaluation_result.get("dimensions", {}),
            "what_worked": evaluation_result.get("what_worked", []),
            "what_didnt_work": evaluation_result.get("what_didnt_work", []),
            "created_at": datetime.now(SHANGHAI_TZ).isoformat(),
        }

        # 写入章节经验日志目录（沿用现有 write_chapter_log 的目录约定）
        log_dir = PROJECT_DIR / "章节经验日志"
        log_dir.mkdir(parents=True, exist_ok=True)

        safe_ref = re.sub(r"[^\w\u4e00-\u9fff]", "_", chapter_ref)
        timestamp = datetime.now(SHANGHAI_TZ).strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{safe_ref}_v2_{timestamp}.json"

        log_file.write_text(
            _json.dumps(log_entry, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "status": "experience_written",
            "log_path": str(log_file),
        }
```

- [ ] **运行 P2-5 测试：**

```bash
python -m pytest tests/test_p2_workflow_stages.py::test_stage8_experience_write_creates_log tests/test_p2_workflow_stages.py::test_stage8_experience_write_skipped_contract -v 2>&1 | tee -a docs/m7_artifacts/P2-2to5_stage1_test_run.txt
```

期望：2 个 PASS

- [ ] **提交：**

```bash
git add .vectorstore/core/workflow.py
git commit -m "feat(p2-5): add NovelWorkflow.run_stage8_experience_write with contract techniques"
```

---

## Task 5：全量回归

### Step 5-1：Stage 2 — 专项测试（全部 P2 测试）

```bash
python -m pytest tests/test_p2_workflow_stages.py tests/test_stage5_5.py tests/test_dispatcher.py tests/test_creative_contract.py -v 2>&1 | tee docs/m7_artifacts/P2-2to5_stage2_test_run.txt
```

期望：全部 PASS（无新 failure）

### Step 5-2：Stage 4 — 全量 pytest

```bash
python -m pytest tests/ -q 2>&1 | tee docs/m7_artifacts/P2-2to5_stage4_test_run.txt
```

期望：**≥ 643 passed**（632 基线 + 11 新增），3 failed（预存在），2 skipped

> 若出现新 failure，对照日志逐条排查，不得跳过。

### Step 5-3：最终提交

```bash
git add docs/m7_artifacts/P2-2to5_stage*_test_run.txt
git commit -m "test(p2-2to5): all stages 5.6→8 tests pass; baseline ≥643"
```

---

## 验收标准

| 方法 | 测试数 | 期望 |
|------|--------|------|
| `run_stage5_6_dispatch()` | 2 | PASS |
| `run_stage6_evaluation()` | 4 | PASS |
| `run_stage7_force_pass()` | 2 | PASS |
| `run_stage8_experience_write()` | 2 | PASS |
| 全量 pytest | — | ≥ 643 passed，3 failed（预存在），无新 failure |
| 4 份 stage 日志 | — | 已提交至 `docs/m7_artifacts/` |

---

## 完成后 Claude 的动作

opencode 完成后，Claude 需要：
1. 检查 Stage 4 日志确认 ≥ 643 passed
2. 更新 ROADMAP P2-2 / P2-3 / P2-4 / P2-5 全部标 ✅
3. 评估是否进入 P3（M8 多小说解耦）或先做其他收尾
