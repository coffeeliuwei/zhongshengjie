#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库构建器
============

帮助新用户构建小说设定和知识图谱。

支持构建：
1. 小说设定（世界观、人物、势力等）
2. 知识图谱（人物关系、势力关系、事件链）
3. 追踪系统（伏笔追踪、承诺追踪、信息边界）

用法：
    python knowledge_builder.py --init              # 初始化知识库目录
    python knowledge_builder.py --create-setting    # 创建设定模板
    python knowledge_builder.py --create-graph      # 创建知识图谱模板
    python knowledge_builder.py --parse DIR         # 解析设定目录
    python knowledge_builder.py --sync              # 同步到向量库
    python knowledge_builder.py --build-graph       # 从设定构建知识图谱
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目路径
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# [N15 2026-04-18] 删除 .vectorstore/core sys.path 注入（已归档）

# 尝试导入统一配置加载器
try:
    from core.config_loader import (
        get_config,
        get_qdrant_url,
        get_model_path,
        get_collection_name,
        get_knowledge_graph_path,
        get_project_root,
    )

    HAS_CONFIG_LOADER = True
except ImportError:
    HAS_CONFIG_LOADER = False
    print("[knowledge_builder] 警告: 未找到 config_loader，使用默认配置")


# 设定模板
SETTING_TEMPLATES = {
    "总大纲": """# 总大纲

## 第一卷：{卷名}

### 核心主线
[描述本卷核心主线剧情]

### 关键转折
1. [第一个关键转折点]
2. [第二个关键转折点]
3. [第三个关键转折点]

### 预期节奏
- 第1-5章：{阶段1内容}
- 第6-10章：{阶段2内容}
- 第11-15章：{阶段3内容}

## 第二卷：{卷名}

[同上结构]

## 世界观概要

### 力量体系
[力量体系简介]

### 势力分布
[势力分布简介]

### 核心冲突
[核心矛盾冲突]

---

> 创建时间：{日期}
> 最后更新：{日期}
""",
    "人物谱": """# 人物谱

## 主角

### 基本信息
- **姓名**：{姓名}
- **年龄**：{年龄}
- **身份**：{身份}
- **性格关键词**：{关键词1}、{关键词2}、{关键词3}

### 人物弧光
- **起点**：[初始状态/性格/立场]
- **转折点1**：[第一次重大变化]
- **转折点2**：[第二次重大变化]
- **终点**：[目标状态]

### 能力设定
- **主能力**：[主要能力描述]
- **副能力**：[次要能力描述]
- **限制条件**：[能力限制]

### 关系网络
- **阵营**：[所属势力/阵营]
- **盟友**：[盟友列表]
- **敌人**：[敌人列表]

---

## 重要配角1

### 基本信息
- **姓名**：{姓名}
- **身份**：{身份}
- **功能定位**：[在故事中的作用]

### 与主角关系
[关系描述]

---

> 创建时间：{日期}
""",
    "十大势力": """# 十大势力

## 势力1：{势力名}

### 基本信息
- **类型**：{势力类型}
- **立场**：{立场倾向}
- **实力等级**：{等级}

### 核心特点
- **理念**：[势力核心理念]
- **风格**：[势力行事风格]
- **资源**：[势力主要资源]

### 关系网络
- **盟友**：[盟友势力]
- **敌人**：[敌对势力]
- **中立**：[中立关系]

### 关键人物
- **领袖**：[领袖名称及简介]
- **核心成员**：[核心成员列表]

### 在故事中的作用
[该势力在主线剧情中的作用]

---

## 势力2：{势力名}

[同上结构]

---

> 创建时间：{日期}
""",
    "力量体系": """# 力量体系

## 等级划分

| 等级 | 名称 | 特征 | 代表人物 |
|------|------|------|----------|
| Lv.1 | {等级1名} | {特征} | {人物} |
| Lv.2 | {等级2名} | {特征} | {人物} |
| Lv.3 | {等级3名} | {特征} | {人物} |

## 能力类型

### 类型1：{能力类型名}
- **特点**：[能力特点]
- **限制**：[使用限制]
- **代表**：[代表人物/势力]

### 类型2：{能力类型名}
[同上结构]

## 资源设定

### 资源1：{资源名}
- **获取方式**：[获取途径]
- **稀缺程度**：[稀缺等级]
- **核心用途**：[主要用途]

## 自洽规则

1. {规则1}
2. {规则2}
3. {规则3}

---

> 创建时间：{日期}
""",
    "时间线": """# 时间线

## 主线时间线

| 时间节点 | 事件 | 影响 | 涉及人物 |
|----------|------|------|----------|
| T0 | {事件1} | {影响} | {人物} |
| T1 | {事件2} | {影响} | {人物} |
| T2 | {事件3} | {影响} | {人物} |

## 各势力时间线

### 势力A时间线
| 时间 | 内部事件 | 外部影响 |
|------|----------|----------|
| T0 | {事件} | {影响} |

### 势力B时间线
[同上结构]

## 关键时间节点说明

### T0：{节点名}
[详细说明]

### T1：{节点名}
[详细说明]

---

> 创建时间：{日期}
""",
    "hook_ledger": """# 伏笔追踪表

## 当前活跃伏笔

| ID | 伏笔内容 | 埋设位置 | 预期回收 | 状态 |
|------|----------|----------|----------|------|
| H001 | {伏笔内容} | 第1章 | 第10章 | pending |
| H002 | {伏笔内容} | 第5章 | 第20章 | pending |

## 已回收伏笔

| ID | 伏笔内容 | 埋设位置 | 回收位置 | 效果 |
|------|----------|----------|----------|------|
| H003 | {伏笔内容} | 第1章 | 第8章 | {效果评价} |

## 伏笔规则

1. 每章至少埋设1个新伏笔
2. 每5章至少回收1个旧伏笔
3. 延迟回收的伏笔效果加成

---

> 创建时间：{日期}
""",
    "payoff_tracking": """# 承诺追踪表

## 对读者的承诺

| ID | 承诺类型 | 承诺内容 | 预期兑现 | 状态 |
|------|----------|----------|----------|------|
| P001 | {类型} | {承诺内容} | 第10章 | pending |

## 承诺类型说明

- **剧情承诺**：主线事件的预期发展
- **人物承诺**：人物命运的预期走向
- **悬念承诺**：悬念的预期揭秘

## 承诺兑现规则

1. 承诺必须兑现，否则读者信任度下降
2. 兑现方式可以创新，但不能违背承诺核心
3. 延迟兑现需要提供补偿（更精彩的揭秘）

---

> 创建时间：{日期}
""",
    "information_boundary": """# 信息边界管理

## 主角信息边界

### 已知信息
- [主角已知的信息列表]

### 未知信息（可揭示）
- [主角未知但读者已知的悬念]

### 未知信息（暂不揭示）
- [主角和读者都未知的核心秘密]

## 各势力信息边界

### 势力A信息边界
| 信息类型 | 势力A知晓 | 主角知晓 | 读者知晓 |
|----------|----------|----------|----------|
| {信息} | ✓ | ✗ | ✓ |

## 信息揭示策略

1. 信息差驱动悬念
2. 信息同步触发转折
3. 核心信息延迟揭示

---

> 创建时间：{日期}
""",
}

# 知识图谱模板
KNOWLEDGE_GRAPH_TEMPLATE = {
    "人物": {
        "nodes": [],
        "edges": [],
    },
    "势力": {
        "nodes": [],
        "edges": [],
    },
    "事件": {
        "nodes": [],
        "edges": [],
    },
    "伏笔": {
        "nodes": [],
        "edges": [],
    },
}


class KnowledgeBuilder:
    """知识库构建器"""

    def __init__(self, settings_dir: Path, config: Optional[Dict] = None):
        self.settings_dir = settings_dir
        self.config = config or {}

        # 使用统一配置加载器
        if HAS_CONFIG_LOADER:
            self.qdrant_url = get_qdrant_url()
            self.collection_name = get_collection_name("novel_settings")
            self.knowledge_graph_file = get_knowledge_graph_path()
        else:
            # 回退到旧方式
            import os
            self.qdrant_url = self.config.get("qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333"))
            self.collection_name = self.config.get("collections", {}).get(
                "novel_settings", "novel_settings_v2"
            )
            self.knowledge_graph_file = (
                settings_dir.parent / ".vectorstore" / "knowledge_graph.json"
            )

    def init_structure(self):
        """初始化知识库目录结构"""
        print("\n" + "=" * 60)
        print("初始化知识库目录结构")
        print("=" * 60)

        # 创建设定目录
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        print(f"    ✓ {self.settings_dir}")

        # 创建核心设定文件模板
        for name, template in SETTING_TEMPLATES.items():
            file_path = self.settings_dir / f"{name}.md"
            if not file_path.exists():
                # 替换模板变量
                today = datetime.now().strftime("%Y-%m-%d")
                content = template.replace("{日期}", today)
                content = re.sub(r"\{[^}]+\}", "[请补充]", content)
                file_path.write_text(content, encoding="utf-8")
                print(f"    ✓ {name}.md")
            else:
                print(f"    ○ {name}.md (已存在)")

        # 创建README
        readme = self.settings_dir / "README.md"
        readme_content = """# 小说设定库

设定库存储小说的世界观、人物、势力等核心信息。

## 设定文件说明

| 文件 | 内容 | 用途 |
|------|------|------|
| 总大纲.md | 全书剧情规划 | 剧情走向参考 |
| 人物谱.md | 人物设定 | 人物描写参考 |
| 十大势力.md | 势力设定 | 势力相关章节参考 |
| 力量体系.md | 能力等级设定 | 战斗/修炼描写参考 |
| 时间线.md | 事件时间顺序 | 时间线一致性检查 |
| hook_ledger.md | 伏笔追踪表 | 伏笔埋设与回收管理 |
| payoff_tracking.md | 承诺追踪表 | 对读者承诺的兑现管理 |
| information_boundary.md | 信息边界管理 | 信息差悬念管理 |

## 快速构建

```bash
# 初始化设定目录
python knowledge_builder.py --init

# 创建知识图谱
python knowledge_builder.py --build-graph

# 同步到向量库
python knowledge_builder.py --sync
```

## 设定写入规范

1. 每个设定文件使用标准Markdown格式
2. 设定内容必须前后一致
3. 更新设定时同步更新知识图谱
4. 定期检查设定一致性
"""
        readme.write_text(readme_content, encoding="utf-8")
        print(f"    ✓ README.md")

        print("\n知识库目录初始化完成!")
        print(f"目录位置: {self.settings_dir}")
        return True

    def create_setting(self, setting_type: str, name: str):
        """创建单个设定文件"""
        if setting_type not in SETTING_TEMPLATES:
            print(f"    ✗ 未知设定类型: {setting_type}")
            print(f"    可用类型: {list(SETTING_TEMPLATES.keys())}")
            return False

        template = SETTING_TEMPLATES[setting_type]
        today = datetime.now().strftime("%Y-%m-%d")
        content = template.replace("{日期}", today)
        content = re.sub(r"\{[^}]+\}", "[请补充]", content)

        file_path = self.settings_dir / f"{name}.md"
        file_path.write_text(content, encoding="utf-8")
        print(f"    ✓ {file_path}")
        return True

    def parse_settings(self) -> List[Dict]:
        """解析所有设定文件"""
        settings = []

        for md_file in self.settings_dir.glob("*.md"):
            if md_file.name in ["README.md", "index.md"]:
                continue

            content = md_file.read_text(encoding="utf-8")

            # 提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1) if title_match else md_file.stem

            # 自动分类
            category = self._classify_setting(md_file.stem, title, content)

            # 提取关键实体
            entities = self._extract_entities(content)

            settings.append(
                {
                    "id": md_file.stem,
                    "name": title,
                    "category": category,
                    "content": content[:500],
                    "full_content": content,
                    "word_count": len(content),
                    "source": md_file.name,
                    "entities": entities,
                }
            )

        return settings

    def _classify_setting(self, filename: str, title: str, content: str) -> str:
        """自动分类设定"""
        filename_lower = filename.lower()
        title_lower = title.lower()

        categories = {
            "世界观": ["世界", "世界观", "力量", "势力", "规则", "体系", "时间线"],
            "人物": ["人物", "角色", "主角", "配角", "人物谱", "性格", "人物弧光"],
            "剧情": ["大纲", "剧情", "主线", "转折", "章节"],
            "追踪": ["伏笔", "承诺", "信息", "追踪", "ledger", "tracking"],
            "其他": [],
        }

        for category, keywords in categories.items():
            if category == "其他":
                continue
            for kw in keywords:
                if kw in filename_lower or kw in title_lower:
                    return category

        return "其他"

    def _extract_entities(self, content: str) -> Dict:
        """提取实体"""
        entities = {
            "人物": [],
            "势力": [],
            "地点": [],
            "物品": [],
        }

        # 简化提取：从标题和列表提取
        # 人物
        person_pattern = re.compile(r"[-*]\s+[\*]*姓名[\*]*[：:]\s*(.+)", re.IGNORECASE)
        for match in person_pattern.finditer(content):
            entities["人物"].append(match.group(1).strip())

        # 势力
        faction_pattern = re.compile(r"势力\d+[：:]\s*(.+)", re.IGNORECASE)
        for match in faction_pattern.finditer(content):
            entities["势力"].append(match.group(1).strip())

        return entities

    def build_knowledge_graph(self):
        """从设定构建知识图谱"""
        print("\n" + "=" * 60)
        print("构建知识图谱")
        print("=" * 60)

        # 解析所有设定
        settings = self.parse_settings()

        if not settings:
            print("    ✗ 未找到设定文件")
            return False

        # 初始化图谱
        graph = {
            "人物": {"nodes": [], "edges": []},
            "势力": {"nodes": [], "edges": []},
            "事件": {"nodes": [], "edges": []},
            "伏笔": {"nodes": [], "edges": []},
            "关系": {"edges": []},
            "metadata": {
                "created": datetime.now().strftime("%Y-%m-%d"),
                "version": "1.0",
                "source_count": len(settings),
            },
        }

        # 从设定提取实体和关系
        for setting in settings:
            entities = setting.get("entities", {})

            # 人物节点
            for person in entities.get("人物", []):
                if person:
                    graph["人物"]["nodes"].append(
                        {
                            "id": person,
                            "name": person,
                            "source": setting["source"],
                            "category": "人物",
                        }
                    )

            # 势力节点
            for faction in entities.get("势力", []):
                if faction:
                    graph["势力"]["nodes"].append(
                        {
                            "id": faction,
                            "name": faction,
                            "source": setting["source"],
                            "category": "势力",
                        }
                    )

        # 去重
        for node_type in ["人物", "势力"]:
            seen = set()
            unique_nodes = []
            for node in graph[node_type]["nodes"]:
                if node["id"] not in seen:
                    seen.add(node["id"])
                    unique_nodes.append(node)
            graph[node_type]["nodes"] = unique_nodes

        # 写入知识图谱文件
        graph_path = self.knowledge_graph_file
        graph_path.parent.mkdir(parents=True, exist_ok=True)

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

        print(f"\n    ✓ 人物节点: {len(graph['人物']['nodes'])}")
        print(f"    ✓ 势力节点: {len(graph['势力']['nodes'])}")
        print(f"    ✓ 知识图谱: {graph_path}")

        return True

    def sync_to_vectorstore(self):
        """同步设定到向量库"""
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import (
            PointStruct,
            VectorParams,
            Distance,
            SparseVectorParams,
        )
        from FlagEmbedding import BGEM3FlagModel

        print("\n" + "=" * 60)
        print("同步设定到向量库")
        print("=" * 60)

        # 解析设定
        settings = self.parse_settings()

        if not settings:
            print("    ✗ 未找到设定文件")
            return False

        print(f"    找到 {len(settings)} 条设定")

        # 连接Qdrant
        client = QdrantClient(url=self.qdrant_url)

        # 检查collection
        try:
            info = client.get_collection(self.collection_name)
            print(f"    {self.collection_name} 已存在 ({info.points_count:,} 条)")
        except:
            print(f"    创建 {self.collection_name}...")
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "dense": VectorParams(size=1024, distance=Distance.COSINE)
                },
                sparse_vectors_config={"sparse": SparseVectorParams()},
            )

        # 加载模型
        print("\n加载BGE-M3模型...")
        model_path = self.config.get("model_path")
        if model_path:
            model = BGEM3FlagModel(model_path, use_fp16=True)
        else:
            import os

            cache_path = os.environ.get("BGE_M3_MODEL_PATH")
            if cache_path:
                model = BGEM3FlagModel(cache_path, use_fp16=True)
            else:
                model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        print("    模型加载完成")

        # 同步
        print("\n同步到向量库...")
        batch_size = 20

        for i in range(0, len(settings), batch_size):
            batch = settings[i : i + batch_size]

            texts = [s["content"] for s in batch]
            out = model.encode(texts, return_dense=True, return_sparse=True)

            points = []
            for j, setting in enumerate(batch):
                point = PointStruct(
                    id=int(hash(setting["id"]) % (2**31)),
                    vector={
                        "dense": out["dense_vecs"][j].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][j].keys()),
                            "values": list(out["lexical_weights"][j].values()),
                        },
                    },
                    payload={
                        "name": setting["name"],
                        "category": setting["category"],
                        "content": setting["content"],
                        "word_count": setting["word_count"],
                        "source": setting["source"],
                        "entities": setting.get("entities", {}),
                    },
                )
                points.append(point)

            client.upsert(self.collection_name, points)
            progress = min(i + batch_size, len(settings))
            print(f"    [{progress}/{len(settings)}]")

        # 验证
        info = client.get_collection(self.collection_name)
        print(f"\n✓ {self.collection_name}: {info.points_count:,} 条")

        return True

    def get_status(self):
        """获取知识库状态"""
        print("\n" + "=" * 60)
        print("知识库状态")
        print("=" * 60)

        # 设定文件
        print("\n[设定文件]")
        for md_file in self.settings_dir.glob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            print(f"    {md_file.name}: {len(content)} 字")

        # 知识图谱
        if self.knowledge_graph_file.exists():
            with open(self.knowledge_graph_file, "r", encoding="utf-8") as f:
                graph = json.load(f)

            print("\n[知识图谱]")
            print(f"    人物节点: {len(graph.get('人物', {}).get('nodes', []))}")
            print(f"    势力节点: {len(graph.get('势力', {}).get('nodes', []))}")
        else:
            print("\n[知识图谱] 未创建")

        return True


def main():
    parser = argparse.ArgumentParser(description="知识库构建器")
    parser.add_argument("--settings-dir", default="设定", help="设定目录路径")
    parser.add_argument("--config", help="配置文件路径")

    # 命令
    parser.add_argument("--init", action="store_true", help="初始化知识库目录")
    parser.add_argument(
        "--create-setting", nargs=2, metavar=("TYPE", "NAME"), help="创建设定文件"
    )
    parser.add_argument("--parse", action="store_true", help="解析所有设定")
    parser.add_argument("--build-graph", action="store_true", help="构建知识图谱")
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--status", action="store_true", help="查看状态")

    args = parser.parse_args()

    # 加载配置
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    # 设定目录
    settings_dir = Path(args.settings_dir)
    builder = KnowledgeBuilder(settings_dir, config)

    # 执行命令
    if args.init:
        builder.init_structure()
    elif args.create_setting:
        builder.create_setting(args.create_setting[0], args.create_setting[1])
    elif args.parse:
        settings = builder.parse_settings()
        print(f"\n解析到 {len(settings)} 条设定")
        for s in settings:
            print(f"    {s['name']} ({s['category']})")
    elif args.build_graph:
        builder.build_knowledge_graph()
    elif args.sync:
        builder.sync_to_vectorstore()
    elif args.status:
        builder.get_status()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python knowledge_builder.py --init")
        print("  python knowledge_builder.py --build-graph")
        print("  python knowledge_builder.py --sync")


if __name__ == "__main__":
    main()
