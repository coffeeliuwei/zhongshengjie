"""P2-2 ~ P2-5 workflow 阶段集成测试。"""
import json
import sys
from pathlib import Path
import pytest

# 先确保项目根在 sys.path（供 root core/* 使用）
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _import_vector_workflow_module():
    """使用 importlib 加载 .vectorstore/core/workflow.py，避免与 root core 包冲突。"""
    import importlib.util as _util
    import sys as _sys
    from types import ModuleType as _ModuleType
    wf_path = PROJECT_ROOT / ".vectorstore" / "core" / "workflow.py"
    spec = _util.spec_from_file_location("vector_core.workflow", str(wf_path))
    module = _util.module_from_spec(spec)
    assert spec and spec.loader
    # 在 sys.modules 中预注册父包与子模块，便于 patch 通过字符串路径导入
    if "vector_core" not in _sys.modules:
        pkg = _ModuleType("vector_core")
        pkg.__path__ = []  # 声明为包
        _sys.modules["vector_core"] = pkg
    _sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    # 将子模块挂到父包属性上，支持 from vector_core import workflow
    _sys.modules["vector_core"].workflow = module  # type: ignore[attr-defined]
    return module


# —— 公共 fixture ————————————————————————————————————————————————

def _make_contract(accepted=True):
    """构造一份最小合法 CreativeContract（含 writer_assignments）。"""
    from core.inspiration.creative_contract import (
        CreativeContract,
        PreserveItem,
        Scope,
        Aspects,
        ExemptDimension,
        WriterAssignment,
        generate_contract_id,
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
        chapter_ref="第三章",
        created_at=datetime.now(SHANGHAI_TZ).isoformat(),
        preserve_list=[item] if accepted else [],
        rejected_list=[],
        writer_assignments=[assignment] if accepted else [],
        iteration_count=1,
        skipped_by_author=not accepted,
    )


def _make_workflow():
    """NovelWorkflow 轻量实例（跳过 Qdrant 连接）。"""
    _mod = _import_vector_workflow_module()
    NovelWorkflow = getattr(_mod, "NovelWorkflow")
    return NovelWorkflow.__new__(NovelWorkflow)


# —— P2-2: run_stage5_6_dispatch ————————————————————————————————

def test_stage5_6_dispatch_returns_packages():
    """
    有 writer_assignments 时返回非空 DispatchPackage 列表。
    """
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


# —— P2-3: run_stage6_evaluation ————————————————————————————————

def test_stage6_evaluation_pass():
    """
    评价通过（score >= 0.8）返回 pass 状态。
    """
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
    """
    评价失败（score < 0.8）连续 1 次返回 fail，fail_count 递增。
    """
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


# —— P2-4: run_stage7_force_pass ————————————————————————————————

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
            chapter_ref="第三章",
            reason="整体情绪到位，不必刻板执行约束",
        )

    assert result["status"] == "overturn_recorded"
    assert result["memory_point_id"] == mock_mp_id
    assert result["audit_report"] is None or isinstance(result["audit_report"], str)


def test_stage7_force_pass_triggers_audit_at_threshold():
    """
    累计推翻 10 次时触发推翻审计报告。
    """
    from unittest.mock import patch, MagicMock

    wf = _make_workflow()
    contract = _make_contract(accepted=True)

    # AuditTrigger.record_overturn 在第 10 次返回审计报告
    mock_report = "⚠️ 推翻审计：系统性偏差检测"

    with patch("core.inspiration.memory_point_sync.MemoryPointSync.create", return_value="mp_x"), \
         patch("core.inspiration.audit_trigger.AuditTrigger.record_overturn", return_value=mock_report):
        result = wf.run_stage7_force_pass(
            contract=contract,
            chapter_ref="第三章",
            reason="测试触发审计",
        )

    assert result["audit_report"] == mock_report


# —— P2-5: run_stage8_experience_write ————————————————————————————

def test_stage8_experience_write_creates_log(tmp_path):
    """
    经验写入产出 log.json，含 contract 采纳技法。
    """
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
        "vector_core.workflow.PROJECT_DIR",
        tmp_path,
    ):
        result = wf.run_stage8_experience_write(
            chapter_ref="第三章",
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

    with patch("vector_core.workflow.PROJECT_DIR", tmp_path):
        result = wf.run_stage8_experience_write(
            chapter_ref="第三章",
            contract=contract,
            evaluation_result=eval_result,
        )

    log_path = Path(result["log_path"])
    data = _json.loads(log_path.read_text(encoding="utf-8"))
    assert data["techniques_used"] == []
