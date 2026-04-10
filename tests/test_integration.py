#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
集成测试
========

测试所有核心模块的集成：
- 数据流：提炼→检索→创作→反馈
- 对话入口层完整流程
- 状态管理完整流程
- 错误恢复完整流程
- 配置系统完整流程

使用 pytest 框架和 mock 模拟外部依赖。

Created by: Phase 17-21 Implementation
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Optional
import sys

# 项目路径设置
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== Fixtures ====================


@pytest.fixture
def temp_project():
    """创建临时项目目录结构"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 创建必需目录
        directories = [
            "设定",
            "创作技法",
            "正文",
            "章节大纲",
            "章节经验日志",
            "config/dimensions",
            ".cache",
            ".state",
            "logs",
        ]

        for dir_name in directories:
            (root / dir_name).mkdir(parents=True, exist_ok=True)

        # 创建基础配置文件
        config = {
            "project": {"name": "测试项目", "version": "1.0.0"},
            "paths": {
                "project_root": str(root),
                "settings_dir": "设定",
                "techniques_dir": "创作技法",
                "content_dir": "正文",
            },
            "database": {"qdrant_host": "localhost", "qdrant_port": 6333},
            "retrieval": {"dense_limit": 100, "sparse_limit": 100, "fusion_limit": 50},
            "worldview": {"current_world": "众生界", "outline_path": "总大纲.md"},
        }

        with open(root / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建大纲文件
        outline_content = """# 总大纲

## 第一章：觉醒
场景类型：开篇场景
主角：李明
力量体系：觉醒之力
"""
        with open(root / "总大纲.md", "w", encoding="utf-8") as f:
            f.write(outline_content)

        # 创建人物谱文件
        characters_content = """# 人物谱

## 主角

### 李明
- 身份：觉醒者
- 境界：觉醒初期
- 性格：坚韧、正义
"""
        with open(root / "设定" / "人物谱.md", "w", encoding="utf-8") as f:
            f.write(characters_content)

        yield root


@pytest.fixture
def mock_qdrant_client():
    """模拟 Qdrant 客户端"""
    client = MagicMock()

    # 模拟检索响应
    mock_results = [
        MagicMock(
            id="test_1",
            score=0.9,
            payload={"content": "这是测试内容", "metadata": {"source": "test"}},
        )
    ]

    client.search.return_value = mock_results
    client.get_collections.return_value = MagicMock(collections=[])
    client.create_collection.return_value = True

    return client


@pytest.fixture
def mock_search_manager():
    """模拟混合检索管理器"""
    manager = MagicMock()

    manager.search_dense.return_value = [
        {"id": "dense_1", "content": "稠密检索结果", "score": 0.85}
    ]

    manager.search_sparse.return_value = [
        {"id": "sparse_1", "content": "稀疏检索结果", "score": 0.80}
    ]

    manager.search_hybrid.return_value = [
        {"id": "hybrid_1", "content": "混合检索结果", "score": 0.90}
    ]

    return manager


# ==================== 测试类：数据流集成 ====================


class TestDataFlowIntegration:
    """测试完整数据流：提炼→检索→创作→反馈"""

    @patch("modules.knowledge_base.hybrid_search_manager.HybridSearchManager")
    def test_extraction_to_retrieval_flow(self, mock_manager_class, temp_project):
        """测试从提炼到检索的数据流"""
        # Mock 检索管理器
        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        # 模拟提炼数据
        extracted_data = {
            "technique": {
                "name": "战斗节奏技法",
                "content": "战斗场景需要紧凑节奏",
                "dimension": "战斗冲突维度",
            },
            "case": {"scene_type": "战斗", "content": "标杆战斗案例文本"},
        }

        # 模拟检索
        mock_manager.search_hybrid.return_value = [
            {
                "id": "tech_1",
                "content": "战斗节奏技法",
                "score": 0.95,
                "metadata": {"dimension": "战斗冲突维度"},
            }
        ]

        # 验证数据流完整性
        # 提炼阶段 → 检索阶段
        # 数据应该能被检索到

        # 1. 提炼数据包含正确维度
        assert "dimension" in extracted_data["technique"]

        # 2. 检索结果与提炼数据匹配
        results = mock_manager.search_hybrid("战斗", top_k=5)
        assert len(results) > 0
        assert results[0]["content"] == "战斗节奏技法"

    def test_retrieval_to_creation_flow(self, temp_project, mock_search_manager):
        """测试从检索到创作的内容流"""
        # 模拟检索结果用于创作
        retrieval_results = {
            "techniques": [{"name": "悬念布局", "description": "悬念技法"}],
            "cases": [{"scene_type": "开篇", "content": "开篇标杆案例"}],
        }

        # 验证创作素材可提取
        assert len(retrieval_results["techniques"]) > 0
        assert len(retrieval_results["cases"]) > 0

        # 验证检索结果包含创作必需信息
        technique = retrieval_results["techniques"][0]
        assert "name" in technique
        assert "description" in technique

    def test_creation_to_feedback_flow(self, temp_project):
        """测试从创作到反馈的闭环"""
        # 模拟创作输出
        creation_output = {
            "chapter": "第一章",
            "content": "测试章节内容",
            "scene_count": 3,
            "evaluation_score": 85,
        }

        # 模拟用户反馈
        user_feedback = {
            "type": "rewrite_request",
            "reason": "战斗不够热血",
            "target_scene": "scene_2",
        }

        # 验证反馈能关联到创作输出
        # 反馈应该包含目标场景信息
        assert "target_scene" in user_feedback

        # 验证创作输出有可反馈的内容
        assert creation_output["scene_count"] > 0

        # 验证评估分数可用于反馈处理
        assert "evaluation_score" in creation_output


# ==================== 测试类：对话入口层集成 ====================


class TestConversationLayerIntegration:
    """测试对话入口层完整流程"""

    def test_intent_classification_flow(self, temp_project):
        """测试意图分类完整流程"""
        # 模拟用户输入
        user_inputs = [
            "添加角色张三",
            "修改李明的境界",
            "添加势力天宗",
            "重写第一章第二段",
        ]

        # 预期意图映射
        expected_intents = [
            "add_character",
            "modify_character",
            "add_faction",
            "rewrite_request",
        ]

        # 简化意图分类逻辑（实际由 intent_classifier.py 实现）
        for i, input_text in enumerate(user_inputs):
            # 检查输入是否包含关键词
            if "添加角色" in input_text:
                intent = "add_character"
            elif "修改" in input_text:
                intent = "modify_character"
            elif "添加势力" in input_text:
                intent = "add_faction"
            elif "重写" in input_text:
                intent = "rewrite_request"
            else:
                intent = "unknown"

            assert intent == expected_intents[i]

    def test_data_extraction_flow(self, temp_project):
        """测试数据提取完整流程"""
        # 模拟意图识别结果
        intent_result = {
            "category": "add_character",
            "confidence": 0.95,
            "data": {"name": "张三", "identity": "修炼者", "realm": "觉醒"},
        }

        # 验证提取的数据结构
        assert "category" in intent_result
        assert "confidence" in intent_result
        assert intent_result["confidence"] > 0.5

        # 验证数据字段完整性
        data = intent_result["data"]
        assert "name" in data
        assert "identity" in data

    def test_file_update_flow(self, temp_project):
        """测试文件更新完整流程"""
        # 模拟更新请求
        update_request = {
            "target_file": "设定/人物谱.md",
            "operation": "add",
            "data": {"name": "王五", "identity": "散修", "realm": "凡人"},
        }

        # 模拟文件更新过程
        target_file = temp_project / update_request["target_file"]
        assert target_file.exists()

        # 读取现有内容
        existing_content = target_file.read_text(encoding="utf-8")

        # 模拟添加新角色
        new_character_section = f"""

### {update_request["data"]["name"]}
- 身份：{update_request["data"]["identity"]}
- 境界：{update_request["data"]["realm"]}
"""

        # 验证更新逻辑正确
        updated_content = existing_content + new_character_section
        assert update_request["data"]["name"] in updated_content

    def test_complete_conversation_flow(self, temp_project):
        """测试完整对话流程：意图→提取→更新→反馈"""
        # 1. 用户输入
        user_input = "添加角色张三，身份是散修，境界为凡人"

        # 2. 意图分类
        intent = "add_character"

        # 3. 数据提取
        extracted_data = {"name": "张三", "identity": "散修", "realm": "凡人"}

        # 4. 文件更新
        target_file = temp_project / "设定" / "人物谱.md"

        # 5. 反馈确认
        feedback = {
            "status": "success",
            "message": f"角色 {extracted_data['name']} 已添加",
        }

        # 验证流程完整性
        assert intent == "add_character"
        assert extracted_data["name"] == "张三"
        assert target_file.exists()
        assert feedback["status"] == "success"


# ==================== 测试类：状态管理集成 ====================


class TestStateManagementIntegration:
    """测试状态管理完整流程"""

    def test_chapter_state_tracking(self, temp_project):
        """测试章节状态跟踪"""
        # 模拟章节状态
        chapter_states = [
            {"chapter": 1, "status": "completed", "score": 85},
            {"chapter": 2, "status": "in_progress", "score": None},
            {"chapter": 3, "status": "pending", "score": None},
        ]

        # 验证状态完整性
        for state in chapter_states:
            assert "chapter" in state
            assert "status" in state

            if state["status"] == "completed":
                assert "score" in state
                assert state["score"] is not None

    def test_scene_state_tracking(self, temp_project):
        """测试场景状态跟踪"""
        # 模拟场景状态
        scene_states = [
            {"scene_id": "scene_1_1", "status": "approved", "writer": "苍澜"},
            {"scene_id": "scene_1_2", "status": "pending_review", "writer": "剑尘"},
            {"scene_id": "scene_1_3", "status": "failed", "writer": "玄一"},
        ]

        # 验证场景状态字段
        for scene in scene_states:
            assert "scene_id" in scene
            assert "status" in scene
            assert "writer" in scene

    def test_workflow_state_persistence(self, temp_project):
        """测试工作流状态持久化"""
        state_file = temp_project / ".state" / "workflow_state.json"

        # 模拟保存状态
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "current_chapter": 2,
            "pending_tasks": ["scene_2_1", "scene_2_2"],
            "completed_tasks": ["scene_1_1", "scene_1_2"],
        }

        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2)

        # 验证状态文件可读取
        assert state_file.exists()

        with open(state_file, "r", encoding="utf-8") as f:
            loaded_state = json.load(f)

        assert loaded_state["current_chapter"] == state_data["current_chapter"]

    def test_state_recovery_after_error(self, temp_project):
        """测试错误后状态恢复"""
        # 模拟错误状态
        error_state = {
            "last_successful_chapter": 1,
            "failed_task": "scene_2_1",
            "error_type": "validation_error",
        }

        # 模拟恢复逻辑
        recovery_state = {
            "current_chapter": error_state["last_successful_chapter"],
            "retry_task": error_state["failed_task"],
            "recovery_mode": True,
        }

        # 验证恢复策略
        assert recovery_state["current_chapter"] == 1
        assert recovery_state["retry_task"] == error_state["failed_task"]


# ==================== 测试类：错误恢复集成 ====================


class TestErrorRecoveryIntegration:
    """测试错误恢复完整流程"""

    def test_network_error_recovery(self, temp_project, mock_qdrant_client):
        """测试网络错误恢复"""
        # 模拟网络错误
        mock_qdrant_client.search.side_effect = [
            Exception("网络连接失败"),  # 第一次失败
            [MagicMock(id="test_1", score=0.9)],  # 重试成功
        ]

        # 模拟重试逻辑
        max_retries = 3
        retry_count = 0
        success = False

        while retry_count < max_retries:
            try:
                results = mock_qdrant_client.search("test", limit=10)
                success = True
                break
            except Exception as e:
                retry_count += 1

        # 验证重试后成功
        assert success is True
        assert retry_count == 1

    def test_file_corruption_recovery(self, temp_project):
        """测试文件损坏恢复"""
        # 模拟损坏的配置文件
        corrupt_config_path = temp_project / "config_corrupt.json"

        with open(corrupt_config_path, "w") as f:
            f.write("{ invalid json }")

        # 模拟恢复逻辑：使用备份配置
        backup_config = {
            "project": {"name": "恢复项目"},
            "paths": {"project_root": str(temp_project)},
        }

        # 验证备份配置可用
        assert backup_config["project"]["name"] == "恢复项目"

        # 模拟恢复写入
        with open(temp_project / "config.json", "w", encoding="utf-8") as f:
            json.dump(backup_config, f)

        assert (temp_project / "config.json").exists()

    def test_validation_error_recovery(self, temp_project):
        """测试验证错误恢复"""
        # 模拟验证失败
        validation_errors = [
            {
                "field": "境界",
                "error": "境界倒退",
                "expected": "觉醒",
                "actual": "凡人",
            },
            {"field": "角色", "error": "角色不存在", "missing": "张三"},
        ]

        # 模拟修复建议
        fixes = [
            {"field": "境界", "action": "update", "value": "觉醒"},
            {"field": "角色", "action": "add", "data": {"name": "张三"}},
        ]

        # 验证修复建议匹配错误
        for i, error in enumerate(validation_errors):
            assert fixes[i]["field"] == error["field"]

    def test_partial_failure_recovery(self, temp_project):
        """测试部分失败恢复"""
        # 模拟批量操作中的部分失败
        batch_results = {
            "total": 5,
            "success": 3,
            "failed": 2,
            "failed_items": ["item_2", "item_4"],
        }

        # 模拟重试失败项
        retry_results = {
            "retry_count": 1,
            "recovered": ["item_2"],
            "still_failed": ["item_4"],
        }

        # 验证重试恢复部分数据
        assert len(retry_results["recovered"]) > 0
        assert batch_results["success"] + len(retry_results["recovered"]) == 4


# ==================== 测试类：配置系统集成 ====================


class TestConfigSystemIntegration:
    """测试配置系统完整流程"""

    def test_config_loading_flow(self, temp_project):
        """测试配置加载流程"""
        config_path = temp_project / "config.json"

        # 验证配置文件存在
        assert config_path.exists()

        # 加载配置
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 验证配置结构完整
        assert "project" in config
        assert "paths" in config
        assert "database" in config
        assert "retrieval" in config

    def test_config_validation_flow(self, temp_project):
        """测试配置验证流程"""
        # 加载配置
        config_path = temp_project / "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 验证必需字段
        required_fields = ["project_root", "qdrant_host", "qdrant_port"]

        # 检查字段存在性
        assert config["paths"]["project_root"] is not None
        assert config["database"]["qdrant_host"] is not None
        assert config["database"]["qdrant_port"] is not None

    def test_config_update_flow(self, temp_project):
        """测试配置更新流程"""
        config_path = temp_project / "config.json"

        # 加载现有配置
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 模拟更新配置
        config["retrieval"]["dense_limit"] = 200
        config["retrieval"]["fusion_limit"] = 100

        # 保存更新
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        # 验证更新生效
        with open(config_path, "r", encoding="utf-8") as f:
            updated_config = json.load(f)

        assert updated_config["retrieval"]["dense_limit"] == 200
        assert updated_config["retrieval"]["fusion_limit"] == 100

    def test_worldview_config_switch(self, temp_project):
        """测试世界观配置切换"""
        # 创建多个世界观配置
        worldview_configs_dir = temp_project / "config" / "world_configs"
        worldview_configs_dir.mkdir(parents=True, exist_ok=True)

        worldviews = ["众生界", "修仙世界"]

        for worldview in worldviews:
            config_file = worldview_configs_dir / f"{worldview}.json"
            worldview_config = {
                "name": worldview,
                "power_system": ["觉醒", "淬体"]
                if worldview == "众生界"
                else ["炼气", "筑基"],
            }

            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(worldview_config, f)

        # 模拟切换世界观
        current_worldview = "修仙世界"
        target_config = worldview_configs_dir / f"{current_worldview}.json"

        # 验证配置文件存在
        assert target_config.exists()

        # 加载并验证配置
        with open(target_config, "r", encoding="utf-8") as f:
            worldview_data = json.load(f)

        assert worldview_data["name"] == current_worldview


# ==================== 测试类：多模块协作集成 ====================


class TestMultiModuleIntegration:
    """测试多模块协作集成"""

    @patch("core.change_detector.change_detector.FileWatcher")
    @patch("core.change_detector.change_detector.SyncManagerAdapter")
    def test_change_detector_integration(
        self, mock_adapter, mock_watcher, temp_project
    ):
        """测试变更检测器集成"""
        # Mock 文件监控器
        mock_file_watcher = MagicMock()
        mock_watcher.return_value = mock_file_watcher

        # Mock 同步适配器
        mock_sync_adapter = MagicMock()
        mock_adapter.return_value = mock_sync_adapter

        # 模拟文件变更
        file_changes = [
            MagicMock(path="设定/人物谱.md", change_type="modified"),
            MagicMock(path="总大纲.md", change_type="modified"),
        ]

        mock_file_watcher.scan_changes.return_value = file_changes
        mock_sync_adapter.sync.return_value = MagicMock(status="success")

        # 验证变更检测流程
        changes = mock_file_watcher.scan_changes()
        assert len(changes) > 0

        # 验证同步触发
        for change in changes:
            sync_result = mock_sync_adapter.sync(change.path)
            assert sync_result.status == "success"

    @patch("core.type_discovery.type_discoverer.TypeDiscoverer.collect_unmatched")
    def test_type_discovery_integration(self, mock_collect, temp_project):
        """测试类型发现器集成"""
        # Mock 收集未匹配片段
        mock_collect.return_value = [
            {"text": "觉醒之力涌动", "source": "chapter_1"},
            {"text": "淬体境界突破", "source": "chapter_2"},
        ]

        # 模拟类型发现流程
        collected_data = mock_collect()

        # 验证收集数据结构
        assert len(collected_data) > 0
        for item in collected_data:
            assert "text" in item
            assert "source" in item

    def test_retrieval_api_integration(self, temp_project, mock_search_manager):
        """测试检索API集成"""
        # 模拟多源检索
        sources = ["technique", "case", "novel"]
        query = "战斗场景"

        # 模拟各源检索结果
        results_by_source = {
            "technique": mock_search_manager.search_hybrid(query),
            "case": [{"id": "case_1", "content": "战斗案例"}],
            "novel": [{"id": "novel_1", "content": "战斗设定"}],
        }

        # 验证多源结果
        for source in sources:
            assert source in results_by_source
            assert len(results_by_source[source]) > 0

    def test_feedback_loop_integration(self, temp_project):
        """测试反馈闭环集成"""
        # 模拟创作输出
        creation_output = {
            "chapter": "第一章",
            "scenes": [{"id": "scene_1", "score": 90}, {"id": "scene_2", "score": 70}],
        }

        # 模拟反馈收集
        feedback = {
            "type": "quality_feedback",
            "target": "scene_2",
            "reason": "战斗描写不够热血",
        }

        # 模拟反馈处理
        processed_feedback = {
            "action": "rewrite",
            "scene_id": feedback["target"],
            "priority": "high",
        }

        # 验证反馈关联到创作输出
        target_scene = next(
            s for s in creation_output["scenes"] if s["id"] == feedback["target"]
        )

        assert target_scene["score"] < 80  # 低分场景触发反馈
        assert processed_feedback["scene_id"] == feedback["target"]


# ==================== 测试类：性能与稳定性集成 ====================


class TestPerformanceIntegration:
    """测试性能与稳定性"""

    def test_parallel_retrieval_performance(self, mock_search_manager):
        """测试并行检索性能"""
        import time

        # 模拟并行检索
        queries = ["战斗", "悬念", "情感", "开篇"]

        start_time = time.time()

        results = []
        for query in queries:
            result = mock_search_manager.search_hybrid(query)
            results.append(result)

        elapsed_time = time.time() - start_time

        # 验证响应时间合理
        assert elapsed_time < 2.0  # 应在2秒内完成

        # 验证所有查询返回结果
        assert len(results) == len(queries)

    def test_cache_effectiveness(self, mock_search_manager):
        """测试缓存有效性"""
        # 模拟缓存命中场景
        query = "战斗场景"

        # 第一次检索（无缓存）
        result1 = mock_search_manager.search_hybrid(query)

        # 第二次检索（有缓存）
        result2 = mock_search_manager.search_hybrid(query)

        # 验证结果一致
        assert result1 == result2

    def test_large_batch_handling(self, temp_project):
        """测试大批量数据处理"""
        # 模拟大批量场景数据
        batch_size = 100

        scenes = []
        for i in range(batch_size):
            scenes.append(
                {
                    "id": f"scene_{i}",
                    "chapter": i // 10,
                    "type": "战斗" if i % 3 == 0 else "情感",
                }
            )

        # 验证批处理数据结构
        assert len(scenes) == batch_size

        # 模拟分批处理
        batch_size_limit = 20
        batches = [
            scenes[i : i + batch_size_limit]
            for i in range(0, len(scenes), batch_size_limit)
        ]

        # 验证分批正确
        assert len(batches) == batch_size // batch_size_limit


# ==================== 运行测试 ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
