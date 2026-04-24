#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审核维度迁移工具
================

将 novelist-evaluator SKILL.md 中的硬编码审核标准迁移到 evaluation_criteria_v1 Collection。

迁移内容：
1. 禁止项检测项（6类）
2. 技法评估标准（5大类×多个技法）
3. 技法评估阈值（~15个阈值）

参考：evaluation-criteria-extension-design.md 第4节
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / ".vectorstore") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore"))


@dataclass
class EvaluationCriteria:
    """审核标准"""

    id: str
    dimension_type: str  # prohibition / technique_criteria / threshold
    dimension_name: str
    name: str
    pattern: Optional[str] = None
    examples: List[str] = None
    threshold: Optional[str] = None
    technique_name: Optional[str] = None
    technique_description: Optional[str] = None
    reference_file: Optional[str] = None
    threshold_score: Optional[int] = None
    source: str = "migrated_from_skill"
    created_at: str = ""
    updated_at: str = ""
    is_active: bool = True

    def __post_init__(self):
        if self.examples is None:
            self.examples = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class EvaluationCriteriaMigrator:
    """审核维度迁移器"""

    SKILL_PATH = Path.home() / ".agents" / "skills" / "novelist-evaluator" / "SKILL.md"

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else PROJECT_ROOT
        self.criteria_list: List[EvaluationCriteria] = []

    def migrate_all(self) -> Dict[str, int]:
        """
        迁移所有审核标准

        Returns:
            各类型的迁移数量
        """
        print("\n" + "=" * 60)
        print("审核维度迁移")
        print("=" * 60)

        # 读取 SKILL.md
        skill_content = self._read_skill_file()

        if not skill_content:
            print("[ERROR] 无法读取 SKILL.md")
            return {}

        # 1. 揁移禁止项
        prohibitions = self._migrate_prohibitions(skill_content)
        print(f"  [OK] 禁止项: {len(prohibitions)} 条")

        # 2. 迁移技法评估标准
        technique_criteria = self._migrate_technique_criteria(skill_content)
        print(f"  [OK] 技法标准: {len(technique_criteria)} 条")

        # 3. 迁移阈值配置
        thresholds = self._migrate_thresholds(skill_content)
        print(f"  [OK] 阈值配置: {len(thresholds)} 条")

        # 合并
        self.criteria_list = prohibitions + technique_criteria + thresholds

        return {
            "prohibition": len(prohibitions),
            "technique_criteria": len(technique_criteria),
            "threshold": len(thresholds),
            "total": len(self.criteria_list),
        }

    def _read_skill_file(self) -> Optional[str]:
        """读取 SKILL.md 文件"""
        if not self.SKILL_PATH.exists():
            print(f"[WARN] SKILL.md 不存在: {self.SKILL_PATH}")
            return None

        try:
            return self.SKILL_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[ERROR] 读取失败: {e}")
            return None

    def _migrate_prohibitions(self, content: str) -> List[EvaluationCriteria]:
        """
        从 SKILL.md 揁移禁止项

        Args:
            content: SKILL.md 内容

        Returns:
            禁止项列表
        """
        criteria = []

        # 禁止项定义（从 SKILL.md 提取）
        prohibition_defs = [
            {
                "name": "AI味表达",
                "pattern": "眼中闪过一丝{emotion}|心中涌起一股{emotion}|嘴角勾起一抹{emotion}|不禁{action}",
                "examples": [
                    "眼中闪过一丝冷意",
                    "心中涌起一股暖流",
                    "嘴角勾起一抹微笑",
                    "不禁感叹",
                ],
                "threshold": "出现1个即失败",
            },
            {
                "name": "古龙式极简",
                "pattern": "{single_word}。|{single_word}！",
                "examples": ["痒。", "疼。", "痛。"],
                "threshold": "出现1个即失败",
            },
            {
                "name": "时间连接词",
                "pattern": "然后|就在这时|过了一会儿",
                "examples": ["然后他转身离开", "就在这时门开了", "过了一会儿她回来了"],
                "threshold": "出现≥3个即失败",
            },
            {
                "name": "抽象统计词",
                "pattern": "无数|成千上万",
                "examples": ["无数人", "成千上万"],
                "threshold": "出现≥2个即失败",
            },
            {
                "name": "精确年龄",
                "pattern": "{number}岁的{character}",
                "examples": ["十八岁的少年", "二十五岁的女子"],
                "threshold": "出现≥2个即失败",
            },
            {
                "name": "Markdown加粗",
                "pattern": "**{content}**",
                "examples": ["**重要**", "**关键**"],
                "threshold": "出现1个即失败",
            },
        ]

        for i, def_ in enumerate(prohibition_defs):
            criteria.append(
                EvaluationCriteria(
                    id=f"eval_prohibition_{i + 1:03d}",
                    dimension_type="prohibition",
                    dimension_name="禁止项检测",
                    name=def_["name"],
                    pattern=def_["pattern"],
                    examples=def_["examples"],
                    threshold=def_["threshold"],
                )
            )

        return criteria

    def _migrate_technique_criteria(self, content: str) -> List[EvaluationCriteria]:
        """
        从 SKILL.md 迁移技法评估标准

        Args:
            content: SKILL.md 内容

        Returns:
            技法标准列表
        """
        criteria = []

        # 技法评估标准定义
        technique_defs = [
            # 世界观技法
            {
                "dimension": "世界观",
                "techniques": [
                    {
                        "name": "历史纵深",
                        "description": "有断层、遗忘、回响",
                        "threshold": 6,
                    },
                    {
                        "name": "内在逻辑一致性",
                        "description": "规则绝对不可破坏",
                        "threshold": 7,
                    },
                    {
                        "name": "世界观自生长",
                        "description": "从公理推导而非硬设定",
                        "threshold": 5,
                    },
                ],
            },
            # 剧情技法
            {
                "dimension": "剧情",
                "techniques": [
                    {
                        "name": "命运驱动",
                        "description": "格局决定事件，角色有限选择",
                        "threshold": 6,
                    },
                    {
                        "name": "历史回响",
                        "description": "过去在现在中显现",
                        "threshold": 5,
                    },
                    {"name": "伏笔跨度", "description": "有跨卷伏笔", "threshold": 5},
                ],
            },
            # 人物技法
            {
                "dimension": "人物",
                "techniques": [
                    {
                        "name": "群像塑造",
                        "description": "多主角/多POV，每个有独立命运线",
                        "threshold": 6,
                    },
                    {
                        "name": "道德灰色",
                        "description": "立场分明而非正邪分明",
                        "threshold": 5,
                    },
                    {
                        "name": "选择代价",
                        "description": "选择有不可逆后果",
                        "threshold": 6,
                    },
                ],
            },
            # 战斗技法
            {
                "dimension": "战斗",
                "techniques": [
                    {
                        "name": "有代价胜利",
                        "description": "胜利伴随重大牺牲",
                        "threshold": 7,
                    },
                    {
                        "name": "群体牺牲有姓名",
                        "description": "具体姓名而非'无数人'",
                        "threshold": 8,
                    },
                ],
            },
            # 氛围技法
            {
                "dimension": "氛围",
                "techniques": [
                    {
                        "name": "历史沉淀感",
                        "description": "时间痕迹可见",
                        "threshold": 5,
                    },
                    {
                        "name": "静默叙述",
                        "description": "平静叙述重大事件",
                        "threshold": 5,
                    },
                    {
                        "name": "语言重量感",
                        "description": "每句话落地有声",
                        "threshold": 6,
                    },
                ],
            },
        ]

        criteria_id = 1
        for dim_def in technique_defs:
            dimension = dim_def["dimension"]
            for tech in dim_def["techniques"]:
                criteria.append(
                    EvaluationCriteria(
                        id=f"eval_technique_{criteria_id:03d}",
                        dimension_type="technique_criteria",
                        dimension_name=f"{dimension}技法评估",
                        name=tech["name"],
                        technique_name=tech["name"],
                        technique_description=tech["description"],
                        threshold_score=tech["threshold"],
                        reference_file=f"创作技法/{dimension}维度/*.md",
                    )
                )
                criteria_id += 1

        return criteria

    def _migrate_thresholds(self, content: str) -> List[EvaluationCriteria]:
        """
        从 SKILL.md 迁移阈值配置

        Args:
            content: SKILL.md 内容

        Returns:
            阈值列表
        """
        criteria = []

        # 阈值配置
        threshold_defs = [
            {"name": "情节完整性", "weight": 20},
            {"name": "人物一致性", "weight": 20},
            {"name": "文风统一性", "weight": 20},
            {"name": "读者体验", "weight": 20},
            {"name": "技法应用", "weight": 20},
            {"name": "综合评分", "threshold": 7},
        ]

        for i, def_ in enumerate(threshold_defs):
            criteria.append(
                EvaluationCriteria(
                    id=f"eval_threshold_{i + 1:03d}",
                    dimension_type="threshold",
                    dimension_name="整体质量评估",
                    name=def_["name"],
                    threshold=json.dumps(def_),
                )
            )

        return criteria

    def save_to_file(self) -> Path:
        """
        保存迁移结果到文件

        Returns:
            文件路径
        """
        output_path = self.project_root / "tools" / "evaluation_criteria_migrated.json"

        data = {
            "migrated_at": datetime.now().isoformat(),
            "source": str(self.SKILL_PATH),
            "count": len(self.criteria_list),
            "criteria": [asdict(c) for c in self.criteria_list],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 已保存到: {output_path}")
        return output_path

    def sync_to_qdrant(self) -> Dict[str, Any]:
        """
        同步到 Qdrant 向量库

        Returns:
            同步结果
        """
        print("\n" + "=" * 60)
        print("同步到向量库")
        print("=" * 60)

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct, VectorParams, Distance
            from core.config_loader import get_qdrant_url

            client = QdrantClient(url=get_qdrant_url())

            # 检查/创建 Collection
            collection_name = "evaluation_criteria_v1"
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if collection_name not in collection_names:
                # 创建 Collection
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
                )
                print(f"  [OK] 创建 Collection: {collection_name}")

            # 生成向量并上传
            # 注意：实际实现需要调用嵌入模型
            # 这里简化处理，仅上传 payload

            points = []
            for criteria in self.criteria_list:
                # TODO: 实际需要生成嵌入向量
                # 这里暂时不上传向量，只记录
                pass

            print(f"  [WARN] 向量生成未实现，仅保存文件")
            print(f"  请使用 data_migrator.py 同步向量")

            return {
                "status": "file_saved",
                "collection": collection_name,
                "count": len(self.criteria_list),
            }

        except ImportError:
            print("[WARN] qdrant_client 未安装")
            return {"status": "error", "message": "qdrant_client 未安装"}
        except Exception as e:
            print(f"[ERROR] 同步失败: {e}")
            return {"status": "error", "message": str(e)}


def main():
    import argparse

    parser = argparse.ArgumentParser(description="审核维度迁移工具")
    parser.add_argument("--migrate", action="store_true", help="执行迁移")
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    migrator = EvaluationCriteriaMigrator()

    if args.migrate:
        result = migrator.migrate_all()
        migrator.save_to_file()

        if args.sync:
            migrator.sync_to_qdrant()

    elif args.status:
        output_path = (
            migrator.project_root / "tools" / "evaluation_criteria_migrated.json"
        )
        if output_path.exists():
            with open(output_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"\n[迁移状态]")
            print(f"  文件: {output_path}")
            print(f"  时间: {data.get('migrated_at', 'N/A')}")
            print(f"  数量: {data.get('count', 0)}")
            print(
                f"  禁止项: {sum(1 for c in data['criteria'] if c['dimension_type'] == 'prohibition')}"
            )
            print(
                f"  技法标准: {sum(1 for c in data['criteria'] if c['dimension_type'] == 'technique_criteria')}"
            )
            print(
                f"  阈值: {sum(1 for c in data['criteria'] if c['dimension_type'] == 'threshold')}"
            )
        else:
            print(f"\n[状态] 未迁移，使用 --migrate 执行迁移")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
