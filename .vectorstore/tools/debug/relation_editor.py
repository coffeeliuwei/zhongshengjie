#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识图谱关系编辑器
用于检查、添加、修改、删除关系

修改后自动同步：
1. knowledge_graph.json
2. chroma.sqlite3
3. 源文件（总大纲.md、人物谱.md等）
4. knowledge_graph.html
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目根目录到 sys.path 以导入配置加载器
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_project_root, get_vectorstore_dir

# 配置
PROJECT_DIR = get_project_root()
VECTORSTORE_DIR = get_vectorstore_dir()
GRAPH_FILE = VECTORSTORE_DIR / "knowledge_graph.json"


class KnowledgeGraphEditor:
    """知识图谱编辑器"""

    def __init__(self):
        self.data = None
        self.entities = {}
        self.relations = []
        self.modified = False

    def load(self):
        """加载图谱"""
        with open(GRAPH_FILE, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.entities = self.data.get("实体", {})
        self.relations = self.data.get("关系", [])
        print(f"已加载: {len(self.entities)} 实体, {len(self.relations)} 关系")

    def save(self):
        """保存图谱"""
        if not self.modified:
            print("无修改，跳过保存")
            return

        self.data["实体"] = self.entities
        self.data["关系"] = self.relations
        self.data["元数据"]["更新时间"] = datetime.now().isoformat()

        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

        print(f"已保存: {GRAPH_FILE}")
        self.modified = False

    def list_relations(self, filter_type: str = None, filter_entity: str = None):
        """列出关系"""
        print("\n" + "=" * 80)
        print("关系列表")
        print("=" * 80)

        count = 0
        for i, rel in enumerate(self.relations):
            source = rel.get("源实体", "")
            target = rel.get("目标实体", "")
            rel_type = rel.get("关系类型", "")

            # 过滤
            if filter_type and rel_type != filter_type:
                continue
            if (
                filter_entity
                and filter_entity not in source
                and filter_entity not in target
            ):
                continue

            attrs = rel.get("属性", {})
            attr_str = ", ".join(f"{k}:{v}" for k, v in attrs.items()) if attrs else ""

            print(f"[{i:3d}] {source} --[{rel_type}]--> {target}")
            if attr_str:
                print(f"      属性: {attr_str}")
            count += 1

        print(f"\n共 {count} 条关系")

    def list_entities(self, filter_type: str = None):
        """列出实体"""
        print("\n" + "=" * 80)
        print("实体列表")
        print("=" * 80)

        count = 0
        for eid, entity in self.entities.items():
            name = entity.get("名称", "")
            etype = entity.get("类型", "")

            if filter_type and etype != filter_type:
                continue

            print(f"  {name} [{etype}]")
            count += 1

        print(f"\n共 {count} 个实体")

    def add_relation(self, source: str, rel_type: str, target: str, attrs: Dict = None):
        """添加关系"""
        self.relations.append(
            {
                "源实体": source,
                "关系类型": rel_type,
                "目标实体": target,
                "属性": attrs or {},
                "来源": "手动添加",
            }
        )
        self.modified = True
        print(f"已添加: {source} --[{rel_type}]--> {target}")

    def remove_relation(self, index: int):
        """删除关系（按索引）"""
        if 0 <= index < len(self.relations):
            rel = self.relations.pop(index)
            print(f"已删除: {rel['源实体']} --[{rel['关系类型']}]--> {rel['目标实体']}")
            self.modified = True
        else:
            print(f"无效索引: {index}")

    def modify_relation(
        self,
        index: int,
        source: str = None,
        rel_type: str = None,
        target: str = None,
        attrs: Dict = None,
    ):
        """修改关系"""
        if 0 <= index < len(self.relations):
            rel = self.relations[index]
            if source:
                rel["源实体"] = source
            if rel_type:
                rel["关系类型"] = rel_type
            if target:
                rel["目标实体"] = target
            if attrs is not None:
                rel["属性"] = attrs
            self.modified = True
            print(f"已修改关系 [{index}]")
        else:
            print(f"无效索引: {index}")

    def find_errors(self):
        """查找可能错误的关系"""
        print("\n" + "=" * 80)
        print("可能错误的关系检查")
        print("=" * 80)

        # 获取所有实体名称
        entity_names = set()
        for eid, entity in self.entities.items():
            entity_names.add(entity.get("名称", ""))

        errors = []

        for i, rel in enumerate(self.relations):
            source = rel.get("源实体", "")
            target = rel.get("目标实体", "")
            rel_type = rel.get("关系类型", "")

            # 检查1: 实体不存在
            if source not in entity_names:
                errors.append((i, f"源实体不存在: {source}"))
            if target not in entity_names:
                errors.append((i, f"目标实体不存在: {target}"))

            # 检查2: 重复关系
            for j, other in enumerate(self.relations):
                if i < j:
                    if (
                        other["源实体"] == source
                        and other["目标实体"] == target
                        and other["关系类型"] == rel_type
                    ):
                        errors.append(
                            (i, f"重复关系: {source} --[{rel_type}]--> {target}")
                        )

            # 检查3: 自引用
            if source == target:
                errors.append((i, f"自引用: {source} --[{rel_type}]--> {target}"))

        if errors:
            for idx, msg in errors:
                rel = self.relations[idx]
                print(f"[{idx:3d}] {msg}")
                print(
                    f"      {rel['源实体']} --[{rel['关系类型']}]--> {rel['目标实体']}"
                )
            print(f"\n发现 {len(errors)} 个潜在问题")
        else:
            print("未发现明显错误")

        return errors

    def sync_all(self):
        """同步到所有存储"""
        self.save()

        # 同步到向量数据库
        print("\n同步到向量数据库...")
        import subprocess

        result = subprocess.run(
            ["python", str(VECTORSTORE_DIR / "sync_to_vectorstore.py")],
            cwd=str(VECTORSTORE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("向量数据库同步成功")
        else:
            print(f"向量数据库同步失败: {result.stderr}")

        # 同步到源文件
        print("\n同步到源文件...")
        result = subprocess.run(
            ["python", str(VECTORSTORE_DIR / "sync_to_source_files.py")],
            cwd=str(VECTORSTORE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("源文件同步成功")
        else:
            print(f"源文件同步失败: {result.stderr}")

        # 重新生成可视化
        print("\n重新生成可视化...")
        result = subprocess.run(
            ["python", str(VECTORSTORE_DIR / "graph_visualizer.py")],
            cwd=str(VECTORSTORE_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("可视化生成成功")
        else:
            print(f"可视化生成失败: {result.stderr}")

        print("\n" + "=" * 80)
        print("全部同步完成!")
        print("=" * 80)


def interactive_mode():
    """交互模式"""
    editor = KnowledgeGraphEditor()
    editor.load()

    while True:
        print("\n" + "-" * 40)
        print("命令:")
        print("  list [类型]        - 列出所有关系（可选类型过滤）")
        print("  entities [类型]    - 列出实体")
        print("  check              - 检查错误")
        print("  add 源 关系 目标   - 添加关系")
        print("  del 索引           - 删除关系")
        print("  save               - 保存并同步")
        print("  quit               - 退出")
        print("-" * 40)

        try:
            cmd = input("> ").strip().split()
            if not cmd:
                continue

            if cmd[0] == "list":
                filter_type = cmd[1] if len(cmd) > 1 else None
                editor.list_relations(filter_type=filter_type)

            elif cmd[0] == "entities":
                filter_type = cmd[1] if len(cmd) > 1 else None
                editor.list_entities(filter_type=filter_type)

            elif cmd[0] == "check":
                editor.find_errors()

            elif cmd[0] == "add" and len(cmd) >= 4:
                source, rel_type, target = cmd[1], cmd[2], cmd[3]
                editor.add_relation(source, rel_type, target)

            elif cmd[0] == "del" and len(cmd) >= 2:
                editor.remove_relation(int(cmd[1]))

            elif cmd[0] == "save":
                editor.sync_all()

            elif cmd[0] == "quit":
                if editor.modified:
                    ans = input("有未保存的修改，是否保存? (y/n): ")
                    if ans.lower() == "y":
                        editor.sync_all()
                break

            else:
                print("未知命令")

        except KeyboardInterrupt:
            print("\n退出")
            break
        except Exception as e:
            print(f"错误: {e}")


if __name__ == "__main__":
    interactive_mode()
