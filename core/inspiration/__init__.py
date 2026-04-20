# core/inspiration/__init__.py
"""灵感引擎（Inspiration Engine）

意外性引擎，与现有评估系统并列的双引擎之一。
- 反模板约束库 + 多变体生成 = 制造多样性
- 鉴赏师 Agent = 选最活的
- 记忆点库 + 反馈回流 = 校准审美

设计文档：docs/superpowers/specs/2026-04-14-inspiration-engine-design.md
"""

__version__ = "0.1.0"

from core.inspiration.constraint_library import ConstraintLibrary
from core.inspiration.variant_generator import (
    generate_variant_specs,
    get_variant_count_from_config,
)
from core.inspiration.memory_point_sync import MemoryPointSync
from core.inspiration.structural_analyzer import analyze, RHYTHM_TEMPLATES
from core.inspiration.segment_locator import locate_segment
from core.inspiration.resonance_feedback import handle_reader_feedback, _extract_signal
from core.inspiration.appraisal_agent import (
    build_appraisal_spec,
    parse_appraisal_response,
    AppraisalResult,
    AppraisalParseError,
)
from core.inspiration.workflow_bridge import phase1_dispatch, _resolve_writer_skill
from core.inspiration.creative_contract import (
    Scope,
    Aspects,
    ExemptDimension,
    PreserveItem,
    RejectedItem,
    NegotiationTurn,
    WriterAssignment,
    CreativeContract,
    generate_contract_id,
    ContractValidationError,
)
from core.inspiration.dispatcher import (
    DispatchPackage,
    dispatch,
    DispatcherError,
)

# ===================== P1-7 追加:评估师豁免 =====================
from core.inspiration.evaluator_exemption import (
    ExemptionBuildError,
    ExemptionMap,
    build_exemption_map,
    is_exempt,
    format_exemption_report,
)

__all__ = [
    "ConstraintLibrary",
    "generate_variant_specs",
    "get_variant_count_from_config",
    "MemoryPointSync",
    "analyze",
    "RHYTHM_TEMPLATES",
    "locate_segment",
    "handle_reader_feedback",
    "_extract_signal",
    "build_appraisal_spec",
    "parse_appraisal_response",
    "AppraisalResult",
    "AppraisalParseError",
    "phase1_dispatch",
    "_resolve_writer_skill",
    "Scope",
    "Aspects",
    "ExemptDimension",
    "PreserveItem",
    "RejectedItem",
    "NegotiationTurn",
    "WriterAssignment",
    "CreativeContract",
    "generate_contract_id",
    "ContractValidationError",
    "DispatchPackage",
    "dispatch",
    "DispatcherError",
    # P1-7 追加
    "ExemptionBuildError",
    "ExemptionMap",
    "build_exemption_map",
    "is_exempt",
    "format_exemption_report",
]
