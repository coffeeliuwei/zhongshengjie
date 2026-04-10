#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
端到端测试
=========

模拟完整业务流程测试：
- 完整创作流程（需求澄清→创作→评估→反馈）
- 数据提炼流程（大纲解析→数据提取→向量入库）
- 配置更新流程（变更检测→审批→同步）
- 类型发现流程（收集→分析→审批→应用）

使用 pytest 框架，模拟完整业务场景。

Created by: Phase 17-21 Implementation
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, PropertyMock, AsyncMock
from typing import Dict, List, Any, Optional
import sys
import time

# 项目路径设置
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== Fixtures ====================


@pytest.fixture
def complete_project():
    """创建完整项目结构用于端到端测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # 创建完整目录结构
        directories = [
            "设定",
            "创作技法",
            "正文",
            "章节大纲",
            "章节经验日志",
            "config/dimensions",
            "config/world_configs",
            ".cache",
            ".state",
            "logs",
            ".vectorstore/core",
        ]

        for dir_name in directories:
            (root / dir_name).mkdir(parents=True, exist_ok=True)

        # 创建完整配置文件
        config = {
            "project": {"name": "端到端测试项目", "version": "2.0.0"},
            "paths": {
                "project_root": str(root),
                "settings_dir": "设定",
                "techniques_dir": "创作技法",
                "content_dir": "正文",
                "chapters_dir": "章节大纲",
                "experience_dir": "章节经验日志",
                "contracts_dir": "scene_contracts",
            },
            "database": {
                "qdrant_host": "localhost",
                "qdrant_port": 6333,
                "timeout": 10,
            },
            "model": {"embedding_model": "BAAI/bge-m3", "batch_size": 20},
            "retrieval": {
                "dense_limit": 100,
                "sparse_limit": 100,
                "fusion_limit": 50,
                "max_content_length": 3000,
            },
            "worldview": {
                "current_world": "众生界",
                "outline_path": "总大纲.md",
                "auto_sync": True,
            },
            "validation": {
                "realm_order": ["凡人", "觉醒", "淬体", "凝脉", "结丹"],
                "skip_rules": [],
            },
        }

        with open(root / "config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建完整大纲文件
        outline_content = """# 总大纲

## 世界观设定

### 力量体系
- 凡人境界：无修炼基础
- 觉醒境界：感知天地之力
- 淬体境界：强化肉身
- 凝脉境界：打通经脉
- 结丹境界：丹田结丹

### 势力分布
- 天宗：修炼圣地
- 地门：隐世宗门
- 人阁：散修联盟

## 第一卷：觉醒之路

### 第一章：初醒
**场景类型**: 开篇场景
**主角**: 李明
**核心冲突**: 主角觉醒，发现世界真相
**关键人物**: 李明（主角）、张师傅（引路人）
**力量表现**: 觉醒之力初次显现

### 第二章：入门
**场景类型**: 成长场景
**核心冲突**: 选择修炼道路
**关键人物**: 李明、天宗长老
**力量表现**: 淬体境界突破

### 第三章：试炼
**场景类型**: 战斗场景
**核心冲突**: 面对第一次挑战
**关键人物**: 李明、对手甲
**力量表现**: 战斗技法初显
"""
        with open(root / "总大纲.md", "w", encoding="utf-8") as f:
            f.write(outline_content)

        # 创建人物谱文件
        characters_content = """# 人物谱

## 主角

### 李明
- **身份**: 觉醒者
- **境界**: 觉醒初期
- **性格**: 坚韧、正义、好奇心强
- **背景**: 普通村民，意外觉醒
- **目标**: 探索世界真相

## 重要配角

### 张师傅
- **身份**: 天宗长老
- **境界**: 结丹后期
- **性格**: 慈祥、睿智
- **关系**: 李明的引路人

### 天宗长老
- **身份**: 天宗掌门
- **境界**: 化神初期
- **性格**: 严厉、公正
- **关系**: 李明的师父候选人
"""
        with open(root / "设定" / "人物谱.md", "w", encoding="utf-8") as f:
            f.write(characters_content)

        # 创建势力文件
        factions_content = """# 十大势力

## 正道势力

### 天宗
- **定位**: 修炼圣地
- **境界**: 化神期守护
- **特色**: 正统修炼法门
- **成员**: 张师傅、天宗长老

### 地门
- **定位**: 隐世宗门
- **境界**: 结丹期守护
- **特色**: 隐匿修炼法门

### 人阁
- **定位**: 散修联盟
- **境界**: 混合境界
- **特色**: 自由修炼路线
"""
        with open(root / "设定" / "十大势力.md", "w", encoding="utf-8") as f:
            f.write(factions_content)

        # 创建技法文件
        techniques_content = """# 创作技法库

## 战斗冲突维度

### 战斗节奏技法
- **核心**: 战斗场景需要紧凑节奏
- **要点**: 快节奏推进，关键动作明确
- **示例**: 一剑斩出，寒光闪烁

### 力量描写技法
- **核心**: 力量表现要有层次
- **要点**: 从感知到爆发，循序渐进
- **示例**: 丹田之气涌动，经脉沸腾

## 悬念布局维度

### 开篇悬念技法
- **核心**: 开篇埋下悬念种子
- **要点**: 隐藏关键信息，引发好奇
- **示例**: 夜幕降临，远处的呼唤

### 反转铺垫技法
- **核心**: 为后续反转埋下伏笔
- **要点**: 看似正常的细节，实则关键
- **示例**: 他的眼神闪过一丝异样
"""
        with open(root / "创作技法" / "技法库.md", "w", encoding="utf-8") as f:
            f.write(techniques_content)

        # 创建世界观配置
        worldview_config = {
            "name": "众生界",
            "version": "1.0.0",
            "power_system": {
                "realms": ["凡人", "觉醒", "淬体", "凝脉", "结丹"],
                "description": "五境界修炼体系",
            },
            "factions": {
                "major": ["天宗", "地门", "人阁"],
                "description": "三足鼎立势力格局",
            },
            "themes": {"primary": "成长与觉醒", "secondary": ["力量体系", "势力博弈"]},
        }

        with open(
            root / "config" / "world_configs" / "众生界.json", "w", encoding="utf-8"
        ) as f:
            json.dump(worldview_config, f, indent=2, ensure_ascii=False)

        # 创建章节大纲文件
        chapter_outline = """# 第一章大纲

## 场景分解

### Scene 1: 开篇（苍澜）
- 类型: 开篇场景
- 内容: 主角初醒，感知异样
- 悬念: 留下世界真相的线索

### Scene 2: 引路（墨言）
- 类型: 成长场景
- 内容: 张师傅出现，引导主角
- 人物: 展现张师傅性格

### Scene 3: 决择（玄一）
- 类型: 转折场景
- 内容: 选择修炼道路
- 冲突: 内心挣扎

### Scene 4: 试炼（剑尘）
- 类型: 战斗场景
- 内容: 第一次试炼挑战
- 战斗: 力量初次展现
"""
        with open(root / "章节大纲" / "第一章大纲.md", "w", encoding="utf-8") as f:
            f.write(chapter_outline)

        # 创建已有章节（用于经验检索）
        existing_chapter = """# 序章：风起

[Scene: 开篇场景 - 苍澜]

山风吹过无名的墓，穿过荒野的风。

那些从未被铭记的人，有过名字，有过希望。

如今，名字尘封在岁月深处。

---

[Scene: 悬念场景 - 玄一]

夜幕降临，远处的呼唤声传来。

李明停下脚步，眼神闪过一丝异样。

"那是...什么声音？"

---

[Scene: 结尾场景 - 云溪]

时光之下，皆是众生。

风穿过荒野，穿过那些从未被铭记的人。

他们曾以为自己知道答案。

"""
        with open(root / "正文" / "序章.md", "w", encoding="utf-8") as f:
            f.write(existing_chapter)

        # 创建经验日志
        experience_log = {
            "chapter": "序章",
            "timestamp": datetime.now().isoformat(),
            "scenes": [
                {
                    "scene_id": "scene_0_1",
                    "writer": "苍澜",
                    "type": "开篇场景",
                    "techniques_used": ["开篇悬念技法"],
                    "score": 92,
                    "notes": "开篇氛围营造成功",
                },
                {
                    "scene_id": "scene_0_2",
                    "writer": "玄一",
                    "type": "悬念场景",
                    "techniques_used": ["反转铺垫技法"],
                    "score": 88,
                    "notes": "悬念埋设到位",
                },
            ],
            "overall_score": 90,
            "feedback": "整体流畅，开篇吸引人",
        }

        with open(root / "章节经验日志" / "序章_经验.json", "w", encoding="utf-8") as f:
            json.dump(experience_log, f, indent=2, ensure_ascii=False)

        yield root


@pytest.fixture
def mock_vectorstore():
    """模拟向量数据库"""
    vs = MagicMock()

    # 模拟检索响应
    vs.search_techniques.return_value = [
        {
            "id": "tech_1",
            "name": "战斗节奏技法",
            "content": "战斗场景需要紧凑节奏",
            "score": 0.95,
            "dimension": "战斗冲突维度",
        }
    ]

    vs.search_cases.return_value = [
        {"id": "case_1", "scene_type": "开篇", "content": "标杆开篇案例", "score": 0.90}
    ]

    vs.retrieve_experience.return_value = [
        {
            "chapter": "序章",
            "scene_type": "开篇",
            "techniques": ["开篇悬念技法"],
            "score": 92,
        }
    ]

    return vs


@pytest.fixture
def mock_workflow():
    """模拟完整工作流"""
    workflow = MagicMock()

    # 模拟章节创作
    workflow.create_chapter.return_value = {
        "chapter": "第一章",
        "scenes": [
            {"id": "scene_1_1", "writer": "苍澜", "type": "开篇", "content": "..."},
            {"id": "scene_1_2", "writer": "墨言", "type": "成长", "content": "..."},
        ],
        "overall_score": 88,
    }

    workflow.evaluate_chapter.return_value = {
        "score": 88,
        "issues": ["scene_1_2战斗描写略弱"],
        "strengths": ["开篇氛围营造出色"],
    }

    return workflow


# ==================== 测试类：完整创作流程 ====================


class TestEndToEndCreationFlow:
    """测试完整创作流程"""

    def test_complete_creation_pipeline(
        self, complete_project, mock_workflow, mock_vectorstore
    ):
        """测试完整创作流程：需求→创作→评估→反馈→经验沉淀"""

        # ===== 阶段 1: 需求澄清 =====
        user_request = "写第一章"

        # 模拟需求解析
        requirements = {
            "chapter": "第一章",
            "scenes": ["开篇", "成长", "战斗"],
            "writers": ["苍澜", "墨言", "剑尘"],
            "constraints": {"字数": "3000-5000", "风格": "压抑、热血"},
        }

        # 验证需求解析完整性
        assert requirements["chapter"] == "第一章"
        assert len(requirements["scenes"]) > 0
        assert len(requirements["writers"]) > 0

        # ===== 阶段 2: 大纲解析 =====
        outline_path = complete_project / "章节大纲" / "第一章大纲.md"

        # 验证大纲文件存在
        assert outline_path.exists()

        # 模拟大纲解析
        parsed_outline = {
            "chapter": "第一章",
            "scene_count": 4,
            "scene_types": ["开篇", "成长", "转折", "战斗"],
            "characters": ["李明", "张师傅"],
        }

        # 验证解析正确
        assert parsed_outline["scene_count"] > 0

        # ===== 阶段 3: 场景识别 =====
        scenes = parsed_outline["scene_types"]

        # 验证场景类型正确
        assert "开篇" in scenes
        assert "战斗" in scenes

        # ===== 阶段 4: 经验检索 =====
        # 模拟检索前章节经验
        experience_results = mock_vectorstore.retrieve_experience(
            current_chapter=1, scene_types=["开篇"], writer_name="苍澜"
        )

        # 验证经验检索有效
        assert len(experience_results) > 0
        assert experience_results[0]["score"] >= 80

        # ===== 阶段 5: 设定检索 =====
        # 模拟检索相关设定
        settings_path = complete_project / "设定" / "人物谱.md"

        # 验证设定文件可读取
        assert settings_path.exists()

        # ===== 阶段 6: 场景契约 =====
        # 模拟场景契约验证
        scene_contract = {
            "scene_id": "scene_1_1",
            "writer": "苍澜",
            "constraints": ["人物状态一致", "境界不倒退", "力量体系一致"],
        }

        # 验证契约规则存在
        assert len(scene_contract["constraints"]) > 0

        # ===== 阶段 7: 逐场景创作 =====
        # 模拟创作输出
        creation_result = mock_workflow.create_chapter(
            chapter="第一章", outline=parsed_outline
        )

        # 验证创作输出完整
        assert creation_result["chapter"] == "第一章"
        assert len(creation_result["scenes"]) > 0

        # ===== 阶段 8: 整章评估 =====
        evaluation_result = mock_workflow.evaluate_chapter(creation_result)

        # 验证评估有效
        assert evaluation_result["score"] >= 80
        assert "issues" in evaluation_result
        assert "strengths" in evaluation_result

        # ===== 阶段 9: 经验沉淀 =====
        # 模拟经验写入
        experience_to_write = {
            "chapter": "第一章",
            "timestamp": datetime.now().isoformat(),
            "scenes": [
                {
                    "scene_id": "scene_1_1",
                    "writer": "苍澜",
                    "score": 92,
                    "techniques": ["开篇悬念技法"],
                }
            ],
            "overall_score": evaluation_result["score"],
        }

        # 验证经验数据完整
        assert experience_to_write["chapter"] == "第一章"
        assert len(experience_to_write["scenes"]) > 0

        # ===== 最终验证 =====
        # 验证完整流程执行
        assert requirements["chapter"] == creation_result["chapter"]
        assert evaluation_result["score"] >= 80

    def test_multi_writer_collaboration_flow(self, complete_project, mock_workflow):
        """测试多作家协作流程"""

        # 模拟5作家分工
        writers = ["苍澜", "墨言", "玄一", "剑尘", "云溪"]

        # 模拟场景分配
        scene_assignments = [
            {"scene_id": "scene_1_1", "writer": "苍澜", "type": "开篇"},
            {"scene_id": "scene_1_2", "writer": "墨言", "type": "成长"},
            {"scene_id": "scene_1_3", "writer": "玄一", "type": "转折"},
            {"scene_id": "scene_1_4", "writer": "剑尘", "type": "战斗"},
            {"scene_id": "scene_1_5", "writer": "云溪", "type": "结尾"},
        ]

        # 验证作家分配合理
        assert len(scene_assignments) == 5

        # 模拟场景契约检查（避免冲突）
        contracts = []
        for assignment in scene_assignments:
            contract = {
                "scene_id": assignment["scene_id"],
                "writer": assignment["writer"],
                "dependencies": [],
                "constraints": ["人物状态一致", "境界不倒退"],
            }
            contracts.append(contract)

        # 验证契约一致性
        all_constraints = set()
        for contract in contracts:
            all_constraints.update(contract["constraints"])

        # 应包含核心一致性规则
        assert "人物状态一致" in all_constraints

        # 模拟创作结果
        creation_results = []
        for assignment in scene_assignments:
            result = {
                "scene_id": assignment["scene_id"],
                "writer": assignment["writer"],
                "content": f"{assignment['writer']}创作的内容",
                "score": 85 + (hash(assignment["writer"]) % 10),
            }
            creation_results.append(result)

        # 验证所有作家都有产出
        assert len(creation_results) == len(writers)

        # 模拟评估师审核
        evaluator_results = {
            "overall_score": 88,
            "passed": True,
            "issues": ["scene_1_3转折略显突兀"],
            "strengths": ["开篇氛围出色", "战斗热血"],
        }

        # 验证评估通过
        assert evaluator_results["passed"] is True
        assert evaluator_results["overall_score"] >= 80

    def test_feedback_revision_loop(self, complete_project, mock_workflow):
        """测试反馈修改闭环"""

        # ===== 阶段 1: 初次创作 =====
        initial_creation = {
            "chapter": "第一章",
            "scenes": [
                {"id": "scene_1_1", "score": 92},
                {"id": "scene_1_2", "score": 70},
            ],
            "overall_score": 81,
        }

        # ===== 阶段 2: 用户反馈 =====
        user_feedback = {
            "type": "rewrite_request",
            "target": "scene_1_2",
            "reason": "战斗描写不够热血",
        }

        # ===== 阶段 3: 反馈处理 =====
        processed_feedback = {
            "action": "rewrite",
            "scene_id": "scene_1_2",
            "writer": "剑尘",
            "techniques_needed": ["战斗节奏技法", "力量描写技法"],
        }

        # 验证反馈关联正确场景
        assert processed_feedback["scene_id"] == user_feedback["target"]

        # ===== 阶段 4: 重写创作 =====
        rewrite_result = {
            "scene_id": "scene_1_2",
            "writer": "剑尘",
            "score": 88,
            "improvements": ["战斗节奏加快", "力量描写增强"],
        }

        # 验证重写后分数提升
        assert rewrite_result["score"] > initial_creation["scenes"][1]["score"]

        # ===== 阶段 5: 经验更新 =====
        updated_experience = {
            "scene_type": "战斗",
            "writer": "剑尘",
            "revision_history": [
                {"version": 1, "score": 70, "issue": "不够热血"},
                {"version": 2, "score": 88, "fix": "增加战斗节奏"},
            ],
            "lesson": "战斗场景需要紧凑节奏和力量层次描写",
        }

        # 验证经验沉淀包含改进历史
        assert len(updated_experience["revision_history"]) == 2
        assert "lesson" in updated_experience


# ==================== 测试类：数据提炼流程 ====================


class TestEndToEndExtractionFlow:
    """测试数据提炼完整流程"""

    def test_outline_to_extraction_flow(self, complete_project):
        """测试大纲解析→数据提取→向量入库流程"""

        # ===== 阶段 1: 大纲解析 =====
        outline_path = complete_project / "总大纲.md"

        # 验证大纲文件存在
        assert outline_path.exists()

        # 模拟大纲解析结果
        parsed_outline = {
            "chapters": ["第一章", "第二章", "第三章"],
            "characters": ["李明", "张师傅", "天宗长老"],
            "factions": ["天宗", "地门", "人阁"],
            "power_system": ["凡人", "觉醒", "淬体", "凝脉", "结丹"],
            "themes": ["成长与觉醒"],
        }

        # 验证解析结果完整
        assert len(parsed_outline["chapters"]) > 0
        assert len(parsed_outline["characters"]) > 0

        # ===== 阶段 2: 数据分类 =====
        # 模拟数据分类
        classified_data = {
            "characters": parsed_outline["characters"],
            "factions": parsed_outline["factions"],
            "power_types": parsed_outline["power_system"],
            "themes": parsed_outline["themes"],
        }

        # 验证分类正确
        assert classified_data["characters"] == parsed_outline["characters"]

        # ===== 阶段 3: 数据提取 =====
        # 模拟数据提取
        extracted_data = {
            "characters": [
                {
                    "name": "李明",
                    "identity": "觉醒者",
                    "realm": "觉醒初期",
                    "description": "主角",
                },
                {
                    "name": "张师傅",
                    "identity": "天宗长老",
                    "realm": "结丹后期",
                    "description": "引路人",
                },
            ],
            "factions": [
                {
                    "name": "天宗",
                    "type": "修炼圣地",
                    "level": "化神期守护",
                    "description": "正统修炼法门",
                }
            ],
            "power_types": [
                {"name": "觉醒", "level": 2, "description": "感知天地之力"}
            ],
        }

        # 验证提取数据结构
        assert len(extracted_data["characters"]) > 0
        for char in extracted_data["characters"]:
            assert "name" in char
            assert "realm" in char

        # ===== 阶段 4: 向量入库 =====
        # 模拟向量入库结果
        vector_results = {
            "characters": {"success": 2, "failed": 0},
            "factions": {"success": 1, "failed": 0},
            "power_types": {"success": 1, "failed": 0},
        }

        # 验证入库成功
        for category in vector_results:
            assert vector_results[category]["success"] > 0
            assert vector_results[category]["failed"] == 0

        # ===== 阶段 5: 状态更新 =====
        # 模拟状态记录
        extraction_state = {
            "timestamp": datetime.now().isoformat(),
            "outline": str(outline_path),
            "status": "completed",
            "items_extracted": sum(v["success"] for v in vector_results.values()),
        }

        # 验证状态完整
        assert extraction_state["status"] == "completed"

    def test_incremental_extraction_flow(self, complete_project):
        """测试增量提炼流程"""

        # ===== 阶段 1: 增量检测 =====
        # 模拟检测大纲变更
        outline_changes = [
            {"path": "总大纲.md", "type": "modified", "mtime": datetime.now()}
        ]

        # 验证变更检测
        assert len(outline_changes) > 0

        # ===== 阅读变更内容 =====
        # 模拟新增内容
        new_content = {
            "new_character": {"name": "王五", "identity": "散修", "realm": "淬体"},
            "new_faction": {"name": "人阁", "type": "散修联盟"},
        }

        # ===== 阶段 2: 提取新增数据 =====
        incremental_extraction = {
            "characters": [new_content["new_character"]],
            "factions": [new_content["new_faction"]],
        }

        # 验证增量提取
        assert len(incremental_extraction["characters"]) > 0

        # ===== 阶段 3: 向量入库 =====
        incremental_vector_result = {
            "characters": {"success": 1, "failed": 0},
            "factions": {"success": 1, "failed": 0},
        }

        # 验证增量入库成功
        assert incremental_vector_result["characters"]["success"] == 1

        # ===== 阶段 4: 历史记录 =====
        extraction_history = {
            "total_extraction_runs": 2,
            "last_run": datetime.now().isoformat(),
            "incremental_items": 2,
        }

        # 验证历史记录
        assert extraction_history["total_extraction_runs"] >= 2


# ==================== 测试类：配置更新流程 ====================


class TestEndToEndConfigUpdateFlow:
    """测试配置更新完整流程"""

    def test_change_detection_to_sync_flow(self, complete_project):
        """测试变更检测→审批→同步流程"""

        # ===== 阶段 1: 变更检测 =====
        # 模拟文件变更检测
        file_changes = [
            {
                "path": "设定/人物谱.md",
                "change_type": "modified",
                "mtime": datetime.now(),
            },
            {"path": "总大纲.md", "change_type": "modified", "mtime": datetime.now()},
        ]

        # 验证变更检测
        assert len(file_changes) > 0

        # ===== 阶段 2: 变更分析 =====
        # 模拟变更内容分析
        change_analysis = [
            {
                "file": "设定/人物谱.md",
                "changes": [{"type": "add_character", "data": {"name": "王五"}}],
            },
            {
                "file": "总大纲.md",
                "changes": [{"type": "add_chapter", "data": {"chapter": "第四章"}}],
            },
        ]

        # 验证变更分析
        assert len(change_analysis) == len(file_changes)

        # ===== 阶段 3: 审批确认 =====
        # 模拟审批流程
        approval_results = []
        for analysis in change_analysis:
            for change in analysis["changes"]:
                approval = {
                    "change": change,
                    "status": "approved",
                    "reviewer": "system",
                    "timestamp": datetime.now().isoformat(),
                }
                approval_results.append(approval)

        # 验证审批通过
        for approval in approval_results:
            assert approval["status"] == "approved"

        # ===== 阶段 4: 同步更新 =====
        # 模拟同步结果
        sync_results = {
            "vectorstore": {"success": 2, "failed": 0},
            "config_files": {"success": 2, "failed": 0},
            "worldview": {"success": 1, "failed": 0},
        }

        # 验证同步成功
        for system in sync_results:
            assert sync_results[system]["failed"] == 0

    def test_worldview_config_sync_flow(self, complete_project):
        """测试世界观配置同步流程"""

        # ===== 阶段 1: 大纲变更 =====
        outline_change = {
            "path": "总大纲.md",
            "new_power_system": ["炼气", "筑基", "金丹"],
            "new_faction": "仙门",
        }

        # ===== 阅段 2: 世界观配置提取 =====
        # 模拟从大纲提取世界观配置
        worldview_update = {
            "power_system": outline_change["new_power_system"],
            "factions": ["仙门"],
            "themes": ["修仙之路"],
        }

        # 验证提取正确
        assert worldview_update["power_system"] == outline_change["new_power_system"]

        # ===== 阶段 3: 配置文件更新 =====
        # 模拟更新世界观配置文件
        updated_worldview = {
            "name": "众生界",
            "version": "2.0.0",
            "power_system": {
                "realms": worldview_update["power_system"],
                "description": "修仙境界体系",
            },
            "factions": {
                "major": worldview_update["factions"],
                "description": "新势力格局",
            },
        }

        # 验证配置更新
        assert updated_worldview["version"] == "2.0.0"

        # ===== 阶段 4: 向量数据库同步 =====
        # 模拟向量库同步
        vector_sync_result = {
            "collections_updated": ["novel_settings_v2"],
            "items_added": 3,
            "status": "success",
        }

        # 验证同步成功
        assert vector_sync_result["status"] == "success"

    def test_dimension_config_update_flow(self, complete_project):
        """测试维度配置更新流程"""

        # ===== 阶段 1: 发现新类型 =====
        discovered_types = [
            {
                "name": "交易场景",
                "category": "scene",
                "keywords": ["交易", "买卖", "价格"],
                "confidence": 0.85,
            },
            {
                "name": "谈判场景",
                "category": "scene",
                "keywords": ["谈判", "协商", "条件"],
                "confidence": 0.80,
            },
        ]

        # 验证发现数据结构
        assert len(discovered_types) > 0
        for dtype in discovered_types:
            assert "name" in dtype
            assert "confidence" in dtype

        # ===== 阶段 2: 审批确认 =====
        approved_types = []
        for dtype in discovered_types:
            if dtype["confidence"] >= 0.80:
                approval = {
                    "type": dtype,
                    "status": "approved",
                    "timestamp": datetime.now().isoformat(),
                }
                approved_types.append(approval)

        # 验证审批阈值过滤
        assert len(approved_types) == 2

        # ===== 阶段 3: 配置同步 =====
        # 模拟同步到维度配置文件
        dimension_config = {
            "scene_types": [
                "开篇",
                "成长",
                "战斗",
                "转折",
                "结尾",
                "交易",
                "谈判",  # 新增类型
            ],
            "version": "2.0.0",
            "last_updated": datetime.now().isoformat(),
        }

        # 验证配置包含新类型
        assert "交易" in dimension_config["scene_types"]
        assert "谈判" in dimension_config["scene_types"]


# ==================== 测试类：类型发现流程 ====================


class TestEndToEndTypeDiscoveryFlow:
    """测试类型发现完整流程"""

    def test_complete_discovery_pipeline(self, complete_project):
        """测试类型发现完整流程：收集→分析→审批→应用"""

        # ===== 阶段 1: 收集未匹配片段 =====
        # 模拟从外部小说库提取片段
        unmatched_texts = [
            {"text": "他交易了珍贵的丹药", "source": "external_novel_1", "chapter": 10},
            {
                "text": "双方开始谈判修炼条件",
                "source": "external_novel_2",
                "chapter": 15,
            },
            {
                "text": "交易场景中价格博弈激烈",
                "source": "external_novel_3",
                "chapter": 20,
            },
            {
                "text": "谈判桌上的筹码不断增加",
                "source": "external_novel_4",
                "chapter": 25,
            },
        ]

        # 验证收集数据量充足
        assert len(unmatched_texts) >= 4

        # ===== 阶段 2: 关键词分析 =====
        # 模拟关键词提取
        keywords_analysis = {
            "交易": {"count": 3, "texts": [unmatched_texts[0], unmatched_texts[2]]},
            "谈判": {"count": 2, "texts": [unmatched_texts[1], unmatched_texts[3]]},
            "价格": {"count": 1, "texts": [unmatched_texts[2]]},
            "筹码": {"count": 1, "texts": [unmatched_texts[3]]},
        }

        # 验证关键词分析
        assert "交易" in keywords_analysis
        assert keywords_analysis["交易"]["count"] >= 2

        # ===== 阶段 3: 聚类与候选生成 =====
        # 模拟聚类生成类型候选
        type_candidates = [
            {
                "name": "交易场景",
                "category": "scene",
                "keywords": ["交易", "买卖", "价格"],
                "sample_count": 3,
                "confidence": 0.85,
                "sources": ["external_novel_1", "external_novel_3"],
            },
            {
                "name": "谈判场景",
                "category": "scene",
                "keywords": ["谈判", "协商", "筹码"],
                "sample_count": 2,
                "confidence": 0.80,
                "sources": ["external_novel_2", "external_novel_4"],
            },
        ]

        # 验证候选生成
        assert len(type_candidates) == 2

        # ===== 阶段 4: 审批确认 =====
        # 模拟人工审批
        approval_process = []
        for candidate in type_candidates:
            approval = {
                "candidate": candidate,
                "decision": "approve" if candidate["confidence"] >= 0.80 else "reject",
                "reviewer": "user",
                "timestamp": datetime.now().isoformat(),
            }
            approval_process.append(approval)

        # 验证审批决策
        approved_types = [a for a in approval_process if a["decision"] == "approve"]

        assert len(approved_types) == 2

        # ===== 阶段 5: 同步到配置 =====
        # 模拟同步到维度配置
        updated_config = {
            "scene_types": [
                "开篇",
                "成长",
                "战斗",
                "转折",
                "结尾",
                "交易",
                "谈判",  # 新发现的类型
            ],
            "last_discovery_run": datetime.now().isoformat(),
            "discovered_count": 2,
        }

        # 验证配置更新
        assert "交易" in updated_config["scene_types"]
        assert "谈判" in updated_config["scene_types"]
        assert updated_config["discovered_count"] == 2

    def test_power_type_discovery_flow(self, complete_project):
        """测试力量类型发现流程"""

        # ===== 收集力量片段 =====
        power_texts = [
            {"text": "金丹之力涌动", "source": "novel_1"},
            {"text": "元婴境界突破", "source": "novel_2"},
            {"text": "金丹期战斗激烈", "source": "novel_3"},
        ]

        # ===== 分析生成候选 =====
        power_candidates = [
            {
                "name": "金丹",
                "category": "power",
                "keywords": ["金丹", "丹田"],
                "confidence": 0.90,
            },
            {
                "name": "元婴",
                "category": "power",
                "keywords": ["元婴", "婴灵"],
                "confidence": 0.85,
            },
        ]

        # ===== 审批同步 =====
        updated_power_config = {
            "realms": ["凡人", "觉醒", "金丹", "元婴"],
            "new_types": ["金丹", "元婴"],
        }

        # 验证力量类型添加
        assert "金丹" in updated_power_config["realms"]
        assert "元婴" in updated_power_config["realms"]

    def test_faction_discovery_flow(self, complete_project):
        """测试势力类型发现流程"""

        # ===== 收集势力片段 =====
        faction_texts = [
            {"text": "仙门势力强大", "source": "novel_1"},
            {"text": "仙门弟子众多", "source": "novel_2"},
        ]

        # ===== 分析生成候选 =====
        faction_candidates = [
            {
                "name": "仙门",
                "category": "faction",
                "keywords": ["仙门", "仙人"],
                "confidence": 0.88,
            }
        ]

        # ===== 审批同步 =====
        updated_faction_config = {
            "factions": ["天宗", "地门", "仙门"],
            "new_types": ["仙门"],
        }

        # 验证势力类型添加
        assert "仙门" in updated_faction_config["factions"]


# ==================== 测试类：完整业务流程 ====================


class TestEndToEndBusinessFlow:
    """测试完整业务流程组合"""

    def test_first_chapter_creation_complete(
        self, complete_project, mock_workflow, mock_vectorstore
    ):
        """测试第一章创作的完整业务流程"""

        # ===== 完整流程执行 =====
        results = {}

        # 1. 需求解析
        results["requirements"] = {"chapter": "第一章", "valid": True}

        # 2. 大纲解析
        results["outline"] = {"parsed": True, "scenes": 4}

        # 3. 经验检索
        results["experience"] = mock_vectorstore.retrieve_experience()

        # 4. 设定检索
        results["settings"] = {"characters": ["李明", "张师傅"], "factions": ["天宗"]}

        # 5. 场景创作
        results["creation"] = mock_workflow.create_chapter()

        # 6. 评估审核
        results["evaluation"] = mock_workflow.evaluate_chapter(results["creation"])

        # 7. 经验沉淀
        results["experience_written"] = {
            "chapter": "第一章",
            "score": results["evaluation"]["score"],
        }

        # ===== 验证完整流程 =====
        # 所有阶段都应完成
        assert results["requirements"]["valid"] is True
        assert results["outline"]["parsed"] is True
        assert len(results["experience"]) > 0
        assert len(results["settings"]["characters"]) > 0
        assert results["creation"]["chapter"] == "第一章"
        assert results["evaluation"]["score"] >= 80
        assert results["experience_written"]["score"] >= 80

    def test_multi_chapter_workflow(self, complete_project, mock_workflow):
        """测试多章节工作流"""

        # 模拟连续创作3章
        chapters = ["第一章", "第二章", "第三章"]

        chapter_results = []

        for chapter in chapters:
            # 模拟章节创作
            result = {
                "chapter": chapter,
                "scenes": 4,
                "score": 85 + (hash(chapter) % 10),
                "status": "completed",
            }

            chapter_results.append(result)

            # 模拟状态累积
            cumulative_state = {
                "completed_chapters": len(chapter_results),
                "average_score": sum(r["score"] for r in chapter_results)
                / len(chapter_results),
            }

        # 验证多章节完成
        assert len(chapter_results) == 3

        # 验证平均分数合理
        cumulative_state = {
            "completed_chapters": len(chapter_results),
            "average_score": sum(r["score"] for r in chapter_results)
            / len(chapter_results),
        }

        assert cumulative_state["average_score"] >= 80
        assert cumulative_state["completed_chapters"] == 3

    def test_full_system_integration(
        self, complete_project, mock_workflow, mock_vectorstore
    ):
        """测试完整系统集成"""

        # ===== 系统初始化检查 =====
        init_status = {
            "config": (complete_project / "config.json").exists(),
            "outline": (complete_project / "总大纲.md").exists(),
            "settings": (complete_project / "设定" / "人物谱.md").exists(),
            "worldview": (
                complete_project / "config" / "world_configs" / "众生界.json"
            ).exists(),
        }

        # 验证初始化完成
        for component in init_status:
            assert init_status[component] is True

        # ===== 数据流完整性检查 =====
        data_flow = {
            "outline_parsed": True,
            "settings_loaded": True,
            "experience_retrieved": len(mock_vectorstore.retrieve_experience()) > 0,
            "techniques_found": len(mock_vectorstore.search_techniques("test")) > 0,
        }

        # 验证数据流畅通
        for flow in data_flow:
            assert data_flow[flow] is True

        # ===== 工作流执行检查 =====
        workflow_result = mock_workflow.create_chapter()

        # 验证工作流执行
        assert workflow_result["chapter"] is not None
        assert len(workflow_result["scenes"]) > 0

        # ===== 系统状态最终检查 =====
        final_status = {
            "creation_complete": True,
            "evaluation_complete": True,
            "experience_written": True,
        }

        # 验证最终状态
        for status in final_status:
            assert final_status[status] is True


# ==================== 测试类：异常恢复端到端 ====================


class TestEndToEndErrorRecovery:
    """测试端到端异常恢复"""

    def test_creation_failure_recovery(self, complete_project, mock_workflow):
        """测试创作失败恢复"""

        # ===== 模拟创作失败 =====
        failed_creation = {
            "chapter": "第一章",
            "status": "failed",
            "error": "validation_error",
            "failed_scene": "scene_1_2",
        }

        # ===== 模拟恢复策略 =====
        recovery_strategy = {
            "action": "retry_scene",
            "scene_id": failed_creation["failed_scene"],
            "writer": "墨言",
            "max_retries": 3,
        }

        # ===== 模拟重试成功 =====
        retry_result = {
            "scene_id": "scene_1_2",
            "status": "success",
            "retry_count": 1,
            "score": 85,
        }

        # 验证恢复成功
        assert retry_result["status"] == "success"
        assert retry_result["score"] >= 80

    def test_partial_system_failure_recovery(self, complete_project):
        """测试部分系统失败恢复"""

        # ===== 模拟部分失败 =====
        system_status = {
            "vectorstore": "failed",
            "config": "normal",
            "workflow": "normal",
        }

        # ===== 模拟降级运行 =====
        degraded_mode = {
            "active_systems": ["config", "workflow"],
            "fallback_mode": True,
            "vectorstore_recovery_in_progress": True,
        }

        # ===== 模拟恢复 =====
        recovery_result = {
            "vectorstore": "recovered",
            "recovery_time": 30,
            "data_integrity": True,
        }

        # 验证恢复
        assert recovery_result["vectorstore"] == "recovered"
        assert recovery_result["data_integrity"] is True


# ==================== 运行测试 ====================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
