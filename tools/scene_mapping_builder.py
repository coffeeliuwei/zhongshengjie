#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
场景映射构建器
==============

帮助新用户构建场景-作家映射文件。

场景映射决定每种场景类型由哪位作家负责：
- 世界观场景 → novelist-canglan（苍澜）
- 剧情场景 → novelist-xuanyi（玄一）
- 人物场景 → novelist-moyan（墨言）
- 战斗场景 → novelist-jianchen（剑尘）
- 氛围场景 → novelist-yunxi（云溪）

用法：
    python scene_mapping_builder.py --init           # 初始化默认映射
    python scene_mapping_builder.py --show            # 显示当前映射
    python scene_mapping_builder.py --set "开篇场景" "canglan"  # 修改映射
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加项目路径
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档）

# 尝试导入统一配置加载器
try:
    from core.config_loader import get_scene_writer_mapping_path, get_vectorstore_dir

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False


# 默认场景-作家映射
DEFAULT_SCENE_MAPPING = {
    "scene_writer_mapping": {
        # 按维度划分
        "世界观": {
            "writer": "novelist-canglan",
            "scenes": ["世界观展开", "势力登场", "力量体系展示", "规则揭示"],
        },
        "剧情": {
            "writer": "novelist-xuanyi",
            "scenes": ["伏笔埋设", "悬念设置", "转折", "高潮", "剧情推进"],
        },
        "人物": {
            "writer": "novelist-moyan",
            "scenes": ["人物出场", "人物成长", "情感表达", "心理描写", "人物互动"],
        },
        "战斗": {
            "writer": "novelist-jianchen",
            "scenes": ["战斗", "修炼突破", "资源争夺", "冲突升级", "危机"],
        },
        "氛围": {
            "writer": "novelist-yunxi",
            "scenes": ["环境描写", "氛围营造", "意境渲染", "开篇", "结尾"],
        },
    },
    # 场景类型到作家的直接映射
    "scene_to_writer": {
        "开篇场景": "novelist-yunxi",
        "结尾场景": "novelist-yunxi",
        "人物出场": "novelist-moyan",
        "人物成长": "novelist-moyan",
        "情感场景": "novelist-moyan",
        "心理场景": "novelist-moyan",
        "战斗场景": "novelist-jianchen",
        "修炼突破": "novelist-jianchen",
        "资源获取": "novelist-jianchen",
        "悬念场景": "novelist-xuanyi",
        "转折场景": "novelist-xuanyi",
        "伏笔场景": "novelist-xuanyi",
        "高潮场景": "novelist-xuanyi",
        "打脸场景": "novelist-jianchen",
        "环境场景": "novelist-yunxi",
        "对话场景": "novelist-moyan",
        "势力登场": "novelist-canglan",
        "世界观展开": "novelist-canglan",
    },
    # 作家信息
    "writers": {
        "novelist-canglan": {
            "name": "苍澜",
            "specialty": "世界观架构师",
            "skills": ["宏大设定", "权力体系", "世界规则构建"],
            "style": "稳重理性，善于从大局思考",
        },
        "novelist-xuanyi": {
            "name": "玄一",
            "specialty": "剧情编织师",
            "skills": ["伏笔设计", "悬念布局", "反转策划"],
            "style": "善于制造戏剧张力",
        },
        "novelist-moyan": {
            "name": "墨言",
            "specialty": "人物刻画师",
            "skills": ["情感细腻", "心理描写", "人物成长"],
            "style": "情感表达真挚动人",
        },
        "novelist-jianchen": {
            "name": "剑尘",
            "specialty": "战斗设计师",
            "skills": ["热血战斗", "功法体系", "冲突张力"],
            "style": "节奏明快，热血沸腾",
        },
        "novelist-yunxi": {
            "name": "云溪",
            "specialty": "意境营造师",
            "skills": ["氛围描写", "诗意语言", "美学构建"],
            "style": "意境深远，画面感强",
        },
    },
    # 默认场景类型列表
    "scene_types": [
        "开篇场景",
        "结尾场景",
        "人物出场",
        "人物成长",
        "情感场景",
        "心理场景",
        "战斗场景",
        "修炼突破",
        "资源获取",
        "悬念场景",
        "转折场景",
        "伏笔场景",
        "高潮场景",
        "打脸场景",
        "环境场景",
        "对话场景",
        "势力登场",
        "世界观展开",
    ],
    # 元数据
    "metadata": {
        "created": "",
        "updated": "",
        "version": "1.0",
    },
}


class SceneMappingBuilder:
    """场景映射构建器"""

    def __init__(self, vectorstore_dir: Path = None):
        # 使用统一配置加载器
        if HAS_CONFIG_LOADER:
            self.vectorstore_dir = vectorstore_dir or get_vectorstore_dir()
            self.mapping_file = get_scene_writer_mapping_path()
        else:
            self.vectorstore_dir = vectorstore_dir or Path(".vectorstore")
            self.mapping_file = self.vectorstore_dir / "scene_writer_mapping.json"
        self.mapping = None

    def init_mapping(self):
        """初始化默认映射"""
        print("\n" + "=" * 60)
        print("初始化场景-作家映射")
        print("=" * 60)

        # 确保目录存在
        self.vectorstore_dir.mkdir(parents=True, exist_ok=True)

        if self.mapping_file.exists():
            print(f"    映射文件已存在: {self.mapping_file}")
            print("    如需重置，请先删除文件")
            return False

        # 创建默认映射
        today = datetime.now().strftime("%Y-%m-%d")
        mapping = DEFAULT_SCENE_MAPPING.copy()
        mapping["metadata"]["created"] = today
        mapping["metadata"]["updated"] = today

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        print(f"    ✓ 创建映射文件: {self.mapping_file}")
        print(f"\n    作家列表:")
        for writer_id, info in mapping["writers"].items():
            print(f"      - {info['name']} ({info['specialty']})")

        print(f"\n    场景类型: {len(mapping['scene_types'])} 种")

        return True

    def load_mapping(self) -> Dict:
        """加载映射"""
        if not self.mapping_file.exists():
            print(f"    ✗ 映射文件不存在: {self.mapping_file}")
            print("    请先运行: python scene_mapping_builder.py --init")
            return None

        with open(self.mapping_file, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)

        return self.mapping

    def show_mapping(self):
        """显示当前映射"""
        print("\n" + "=" * 60)
        print("场景-作家映射")
        print("=" * 60)

        mapping = self.load_mapping()
        if not mapping:
            return

        # 显示作家信息
        print("\n[作家列表]")
        for writer_id, info in mapping.get("writers", {}).items():
            print(f"\n    {info['name']} ({writer_id})")
            print(f"        专长: {info['specialty']}")
            print(f"        技能: {', '.join(info['skills'])}")

        # 显示场景映射
        print("\n[场景映射]")
        scene_to_writer = mapping.get("scene_to_writer", {})

        # 按作家分组
        writer_scenes = {}
        for scene, writer in scene_to_writer.items():
            if writer not in writer_scenes:
                writer_scenes[writer] = []
            writer_scenes[writer].append(scene)

        for writer, scenes in writer_scenes.items():
            writer_info = mapping.get("writers", {}).get(writer, {})
            name = writer_info.get("name", writer)
            print(f"\n    {name}:")
            for scene in scenes:
                print(f"        - {scene}")

        print("\n" + "=" * 60)

    def set_mapping(self, scene_type: str, writer_id: str):
        """设置场景映射"""
        mapping = self.load_mapping()
        if not mapping:
            return False

        # 验证作家
        if writer_id not in mapping.get("writers", {}):
            print(f"    ✗ 未知作家: {writer_id}")
            print(f"    可用作家: {list(mapping.get('writers', {}).keys())}")
            return False

        # 设置映射
        if "scene_to_writer" not in mapping:
            mapping["scene_to_writer"] = {}

        old_writer = mapping["scene_to_writer"].get(scene_type, "无")
        mapping["scene_to_writer"][scene_type] = writer_id
        mapping["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        print(f"    ✓ {scene_type}: {old_writer} → {writer_id}")
        return True

    def add_scene_type(self, scene_type: str, writer_id: str = None):
        """添加新场景类型"""
        mapping = self.load_mapping()
        if not mapping:
            return False

        if scene_type in mapping.get("scene_types", []):
            print(f"    ✗ 场景类型已存在: {scene_type}")
            return False

        mapping["scene_types"].append(scene_type)

        if writer_id:
            if writer_id not in mapping.get("writers", {}):
                print(f"    ✗ 未知作家: {writer_id}")
                return False
            mapping["scene_to_writer"][scene_type] = writer_id

        mapping["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        print(f"    ✓ 添加场景类型: {scene_type}")
        return True

    def add_writer(
        self, writer_id: str, name: str, specialty: str, skills: List[str], style: str
    ):
        """添加新作家"""
        mapping = self.load_mapping()
        if not mapping:
            return False

        if writer_id in mapping.get("writers", {}):
            print(f"    ✗ 作家已存在: {writer_id}")
            return False

        mapping["writers"][writer_id] = {
            "name": name,
            "specialty": specialty,
            "skills": skills,
            "style": style,
        }

        mapping["metadata"]["updated"] = datetime.now().strftime("%Y-%m-%d")

        with open(self.mapping_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)

        print(f"    ✓ 添加作家: {name} ({writer_id})")
        return True


def main():
    parser = argparse.ArgumentParser(description="场景映射构建器")
    parser.add_argument("--vectorstore-dir", default=None, help="向量库目录")

    # 命令
    parser.add_argument("--init", action="store_true", help="初始化默认映射")
    parser.add_argument("--show", action="store_true", help="显示当前映射")
    parser.add_argument(
        "--set", nargs=2, metavar=("SCENE", "WRITER"), help="设置场景映射"
    )
    parser.add_argument(
        "--add-scene", nargs="+", metavar=("SCENE", "WRITER"), help="添加场景类型"
    )
    parser.add_argument(
        "--add-writer",
        nargs=5,
        metavar=("ID", "NAME", "SPECIALTY", "SKILLS", "STYLE"),
        help="添加作家",
    )

    args = parser.parse_args()

    vectorstore_dir = Path(args.vectorstore_dir) if args.vectorstore_dir else None
    builder = SceneMappingBuilder(vectorstore_dir)

    if args.init:
        builder.init_mapping()
    elif args.show:
        builder.show_mapping()
    elif args.set:
        builder.set_mapping(args.set[0], args.set[1])
    elif args.add_scene:
        scene = args.add_scene[0]
        writer = args.add_scene[1] if len(args.add_scene) > 1 else None
        builder.add_scene_type(scene, writer)
    elif args.add_writer:
        builder.add_writer(
            args.add_writer[0],
            args.add_writer[1],
            args.add_writer[2],
            args.add_writer[3].split(","),
            args.add_writer[4],
        )
    else:
        parser.print_help()
        print("\n示例:")
        print("  python scene_mapping_builder.py --init")
        print("  python scene_mapping_builder.py --show")
        print('  python scene_mapping_builder.py --set "开篇场景" "novelist-yunxi"')


if __name__ == "__main__":
    main()
