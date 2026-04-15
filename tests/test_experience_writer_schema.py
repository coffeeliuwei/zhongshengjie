import pytest
import json
from pathlib import Path


def test_write_valid_experience_succeeds(tmp_path):
    """格式正确的经验日志写入成功"""
    from core.feedback.experience_writer import ExperienceWriter

    writer = ExperienceWriter(log_dir=str(tmp_path))
    result = writer.write_chapter_experience(
        chapter=1,
        experience={
            "chapter": "第1章",
            "scene_types": ["战斗"],
            "what_worked": [{"content": "断臂作为代价有冲击力", "scene_type": "战斗"}],
            "what_didnt_work": [
                {"content": "群体牺牲缺少具体姓名", "scene_type": "战斗"}
            ],
            "for_next_chapter": ["配角牺牲必须有姓名"],
        },
    )
    assert result["success"] is True


def test_write_missing_required_field_raises(tmp_path):
    """缺少必填字段 chapter 时抛出 ValueError"""
    from core.feedback.experience_writer import ExperienceWriter

    writer = ExperienceWriter(log_dir=str(tmp_path))
    with pytest.raises(ValueError, match="经验日志格式错误"):
        writer.write_chapter_experience(
            chapter=1,
            experience={
                # 缺少 chapter 字段
                "scene_types": ["战斗"],
                "what_worked": [],
                "what_didnt_work": [],
                "for_next_chapter": [],
            },
        )


def test_write_wrong_item_structure_raises(tmp_path):
    """what_worked 内缺少 scene_type 字段时抛出 ValueError"""
    from core.feedback.experience_writer import ExperienceWriter

    writer = ExperienceWriter(log_dir=str(tmp_path))
    with pytest.raises(ValueError, match="经验日志格式错误"):
        writer.write_chapter_experience(
            chapter=1,
            experience={
                "chapter": "第1章",
                "scene_types": ["战斗"],
                "what_worked": [{"content": "某做法"}],  # 缺 scene_type
                "what_didnt_work": [],
                "for_next_chapter": [],
            },
        )
