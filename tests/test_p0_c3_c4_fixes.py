"""P0 修复测试：C3（假维度修复）+ C4（pause_workflow 路由）"""

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


# ============================================================
# C3: sync_manager.py 必须使用 BGE-M3 而不是 SentenceTransformer
# ============================================================
def test_sync_manager_uses_bge_m3():
    """sync_manager.py 必须加载 BGE-M3 模型（不是 MiniLM）"""
    path = PROJECT_ROOT / "modules" / "knowledge_base" / "sync_manager.py"
    content = path.read_text(encoding="utf-8")

    # 必须导入 BGEM3FlagModel
    assert "from FlagEmbedding import BGEM3FlagModel" in content, (
        "sync_manager.py 必须 from FlagEmbedding import BGEM3FlagModel"
    )

    # 不能再用 MiniLM
    assert "paraphrase-multilingual-MiniLM-L12-v2" not in content, (
        "sync_manager.py 仍引用旧的 MiniLM 模型"
    )


def test_sync_manager_vector_size_is_1024():
    """sync_manager.py VECTOR_SIZE 必须是 1024"""
    path = PROJECT_ROOT / "modules" / "knowledge_base" / "sync_manager.py"
    content = path.read_text(encoding="utf-8")
    assert re.search(r"VECTOR_SIZE\s*=\s*1024", content), "VECTOR_SIZE 必须是 1024"


# ============================================================
# C3: sync_to_qdrant.py 必须使用 BGE-M3
# ============================================================
def test_sync_to_qdrant_uses_bge_m3():
    """.case-library/scripts/sync_to_qdrant.py 必须加载 BGE-M3"""
    path = PROJECT_ROOT / ".case-library" / "scripts" / "sync_to_qdrant.py"
    content = path.read_text(encoding="utf-8")

    assert "from FlagEmbedding import BGEM3FlagModel" in content, (
        "sync_to_qdrant.py 必须 from FlagEmbedding import BGEM3FlagModel"
    )

    assert "paraphrase-multilingual-MiniLM-L12-v2" not in content, (
        "sync_to_qdrant.py 仍引用旧的 MiniLM 模型"
    )


def test_sync_to_qdrant_vector_size_is_1024():
    """.case-library/scripts/sync_to_qdrant.py VECTOR_SIZE 必须是 1024"""
    path = PROJECT_ROOT / ".case-library" / "scripts" / "sync_to_qdrant.py"
    content = path.read_text(encoding="utf-8")
    assert re.search(r"VECTOR_SIZE\s*=\s*1024", content), "VECTOR_SIZE 必须是 1024"


# ============================================================
# C4: pause_workflow 必须归类到 WORKFLOW_CONTROL
# ============================================================
def test_pause_workflow_category_is_workflow_control():
    """intent_classifier.py 中 pause_workflow 的 category 必须是 WORKFLOW_CONTROL"""
    from core.conversation.intent_classifier import (
        IntentClassifier,
        IntentCategory,
    )

    pause_def = IntentClassifier.CORE_INTENTS.get("pause_workflow")
    assert pause_def is not None, "CORE_INTENTS 中必须有 pause_workflow"
    assert pause_def["category"] == IntentCategory.WORKFLOW_CONTROL, (
        f"pause_workflow.category 必须是 WORKFLOW_CONTROL，当前为 {pause_def['category']}"
    )


def test_pause_workflow_routes_to_execute_workflow_control():
    """'暂停' 输入应该能走到 _execute_workflow_control 而不是 IntentRouter"""
    from core.conversation.conversation_entry_layer import (
        ConversationEntryLayer,
    )
    from core.conversation.intent_classifier import IntentCategory

    layer = ConversationEntryLayer(session_id="test_p0_c4")
    intent_result = layer.intent_classifier.classify("暂停")

    assert intent_result.intent == "pause_workflow"
    assert intent_result.category == IntentCategory.WORKFLOW_CONTROL, (
        f"'暂停' 的 category 应为 WORKFLOW_CONTROL，当前为 {intent_result.category}"
    )
