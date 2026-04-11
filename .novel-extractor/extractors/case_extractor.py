"""
场景案例提取器

封装 .case-library 的场景案例提取功能
支持22种场景类型的标杆案例提取

底层调用：
    .case-library/scripts/unified_case_extractor.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加案例库脚本路径
CASE_LIBRARY_DIR = Path(__file__).parent.parent.parent / ".case-library"
sys.path.insert(0, str(CASE_LIBRARY_DIR / "scripts"))

from unified_config import (
    CASE_OUTPUT_DIR,
    CONVERTED_DIR,
    NOVEL_SOURCE_DIR,
    get_output_path,
    get_progress_path,
)


@dataclass
class CaseExtractionProgress:
    """案例提取进度"""

    status: str = "pending"
    total_novels: int = 0
    processed_novels: int = 0
    total_cases: int = 0
    last_novel: str = ""
    last_update: str = ""


class CaseExtractor:
    """
    场景案例提取器

    封装现有案例库提取系统，提供统一接口
    """

    # 场景类型定义
    SCENE_TYPES = [
        "开篇场景",
        "人物出场",
        "战斗场景",
        "对话场景",
        "情感场景",
        "悬念场景",
        "转折场景",
        "结尾场景",
        "环境场景",
        "心理场景",
        "修炼突破",
        "势力登场",
        "资源获取",
        "探索发现",
        "伏笔回收",
        "危机降临",
        "成长蜕变",
        "情报揭示",
        "社交场景",
        "阴谋揭露",
        "冲突升级",
        "团队组建",
        "打脸场景",
        "高潮场景",
    ]

    # 题材类型
    GENRES = [
        "玄幻奇幻",
        "武侠仙侠",
        "现代都市",
        "历史军事",
        "科幻灵异",
        "青春校园",
        "游戏竞技",
        "女频言情",
    ]

    def __init__(self):
        self.output_dir = CASE_OUTPUT_DIR
        self.converted_dir = CONVERTED_DIR
        self.source_dir = NOVEL_SOURCE_DIR
        self.progress = self._load_progress()

    def _load_progress(self) -> CaseExtractionProgress:
        """加载进度"""
        progress_file = get_progress_path("case")
        if progress_file.exists():
            with open(progress_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return CaseExtractionProgress(**data)
        return CaseExtractionProgress()

    def _save_progress(self):
        """保存进度"""
        progress_file = get_progress_path("case")
        progress_file.parent.mkdir(parents=True, exist_ok=True)

        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress.__dict__, f, ensure_ascii=False, indent=2)

    def _get_stats(self) -> Dict[str, Any]:
        """获取当前统计"""
        stats_file = Path(CASE_LIBRARY_DIR) / "unified_stats.json"
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"total_cases": 0, "by_scene": {}}

    def run(
        self,
        limit: int = None,
        scene_types: List[str] = None,
        genres: List[str] = None,
        resume: bool = True,
    ) -> Dict[str, Any]:
        """
        运行场景案例提取

        Args:
            limit: 限制处理小说数量
            scene_types: 只提取指定场景类型
            genres: 只提取指定题材
            resume: 是否续接上次

        Returns:
            提取结果统计
        """
        print("\n" + "=" * 60)
        print("场景案例提取器")
        print("=" * 60)
        print(f"数据源: {self.source_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"场景类型: {len(self.SCENE_TYPES)}种")
        print(f"题材类型: {len(self.GENRES)}种")
        print("=" * 60)

        # 获取当前状态
        stats = self._get_stats()
        current_cases = stats.get("total_cases", 0)

        print(f"\n当前状态:")
        print(f"  已提取案例: {current_cases}")

        # 显示各场景类型统计
        by_scene = stats.get("by_scene", {})
        if by_scene:
            print(f"\n场景分布:")
            for scene, count in sorted(by_scene.items(), key=lambda x: -x[1]):
                if count > 0:
                    print(f"  {scene}: {count}")

        # 调用底层提取脚本
        extractor_script = CASE_LIBRARY_DIR / "scripts" / "unified_case_extractor.py"

        if extractor_script.exists():
            print(f"\n[调用] {extractor_script}")
            print("提示: 实际提取需要运行:")
            print("  cd .case-library/scripts")
            print("  python unified_case_extractor.py --extract")
        else:
            print(f"[警告] 提取脚本不存在: {extractor_script}")

        # 更新进度
        self.progress.status = "running"
        self._save_progress()

        return {
            "dimension": "case",
            "status": "ready",
            "current_cases": current_cases,
            "output_dir": str(self.output_dir),
            "script": str(extractor_script),
            "command": "cd .case-library/scripts && python unified_case_extractor.py --extract",
        }

    def get_status(self) -> Dict[str, Any]:
        """获取提取状态"""
        stats = self._get_stats()

        return {
            "dimension": "case",
            "category": "core",
            "total_cases": stats.get("total_cases", 0),
            "scene_types": self.SCENE_TYPES,
            "genres": self.GENRES,
            "output_dir": str(self.output_dir),
            "by_scene": stats.get("by_scene", {}),
        }

    def extract_for_scene(self, scene_type: str, top_k: int = 10) -> List[Dict]:
        """
        获取指定场景类型的案例

        Args:
            scene_type: 场景类型
            top_k: 返回数量

        Returns:
            案例列表
        """
        cases = []
        scene_dir = self.output_dir / scene_type

        if not scene_dir.exists():
            return []

        # 遍历题材子目录
        for genre_dir in scene_dir.iterdir():
            if not genre_dir.is_dir():
                continue

            for case_file in genre_dir.glob("*.json"):
                if len(cases) >= top_k:
                    break

                try:
                    with open(case_file, "r", encoding="utf-8") as f:
                        case_data = json.load(f)

                    cases.append(
                        {
                            "id": case_file.stem,
                            "scene_type": scene_type,
                            "genre": genre_dir.name,
                            "novel": case_data.get("novel_name", ""),
                            "content": case_data.get("content", "")[:500],
                            "quality": case_data.get("quality_score", 0),
                        }
                    )
                except:
                    continue

            if len(cases) >= top_k:
                break

        return cases


# 便捷函数
def extract_cases(**kwargs) -> Dict[str, Any]:
    """提取场景案例"""
    extractor = CaseExtractor()
    return extractor.run(**kwargs)


def get_case_stats() -> Dict[str, Any]:
    """获取案例统计"""
    extractor = CaseExtractor()
    return extractor.get_status()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="场景案例提取")
    parser.add_argument("--status", action="store_true", help="查看状态")
    parser.add_argument("--scene", type=str, help="获取指定场景案例")
    parser.add_argument("--top-k", type=int, default=10, help="返回数量")

    args = parser.parse_args()

    extractor = CaseExtractor()

    if args.status:
        status = extractor.get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    elif args.scene:
        cases = extractor.extract_for_scene(args.scene, args.top_k)
        print(f"找到 {len(cases)} 个 {args.scene} 案例")
        for c in cases[:3]:
            print(f"\n- {c['novel']} (质量: {c['quality']})")
            print(f"  {c['content'][:200]}...")
    else:
        extractor.run()
