#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
技法库构建器
============

帮助新用户从外部写作资源导入技法，构建自己的技法库。

支持来源：
1. 写作技法书籍/教程（MD/TXT格式）
2. 网络写作资源（复制粘贴）
3. 个人技法总结（自定义格式）

用法：
    python technique_builder.py --init              # 初始化技法目录结构
    python technique_builder.py --import FILE       # 导入技法文件
    python technique_builder.py --parse DIR         # 解析目录下的所有技法
    python technique_builder.py --sync              # 同步到向量库
    python technique_builder.py --from-url URL      # 从网络资源导入
    python technique_builder.py --template          # 生成技法模板
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


# 技法维度定义
DIMENSIONS = [
    "01-世界观维度",
    "02-剧情维度",
    "03-人物维度",
    "04-战斗冲突维度",
    "05-氛围意境维度",
    "06-情感维度",
    "07-叙事维度",
    "08-对话维度",
    "09-描写维度",
    "10-开篇维度",
    "11-高潮维度",
    "99-外部资源",
]

# 技法模板
TECHNIQUE_TEMPLATE = """# {技法名称}

**技法编号**：{编号}

**技法名称**：{技法名称}

**适用场景**：
- {场景1}
- {场景2}
- {场景3}

**核心原理**：
{原理描述}

**具体示例**：
```
{示例内容}
```

**注意事项**：
1. {注意1}
2. {注意2}
3. {注意3}

**相关技法**：
- {相关技法1}
- {相关技法2}

---
"""


class TechniqueBuilder:
    """技法库构建器"""

    def __init__(self, techniques_dir: Path, config: Optional[Dict] = None):
        self.techniques_dir = techniques_dir
        self.config = config or {}
        # 尝试从统一配置加载器获取 Qdrant URL
        try:
            from core.config_loader import get_qdrant_url
            self.qdrant_url = self.config.get("qdrant_url", get_qdrant_url())
        except ImportError:
            self.qdrant_url = self.config.get("qdrant_url", os.environ.get("QDRANT_URL", "http://localhost:6333"))
        self.collection_name = self.config.get("collections", {}).get(
            "writing_techniques", "writing_techniques_v2"
        )

    def init_structure(self):
        """初始化技法目录结构"""
        print("\n" + "=" * 60)
        print("初始化技法目录结构")
        print("=" * 60)

        # 创建维度目录
        for dim in DIMENSIONS:
            dim_dir = self.techniques_dir / dim
            dim_dir.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ {dim}")

        # 创建README
        readme = self.techniques_dir / "README.md"
        readme_content = """# 创作技法库

技法库按维度组织，每个维度一个子目录。

## 维度说明

| 维度 | 覆盖范围 | 典型技法 |
|------|----------|----------|
| 世界观维度 | 世界构建、力量体系、势力架构 | 体系自洽、势力登场、世界观植入 |
| 剧情维度 | 剧情设计、伏笔悬念、反转 | 黄金三章、伏笔设计、悬念布局 |
| 人物维度 | 人物塑造、成长弧光、关系 | 人物弧光、对比塑造、人物出场 |
| 战斗冲突维度 | 战斗描写、冲突升级 | 战斗节奏、招式命名、冲突张力 |
| 氛围意境维度 | 氛围营造、场景渲染 | 写意手法、环境烘托、意境塑造 |
| 情感维度 | 情感表达、情感转折 | 情感层次、情感爆发、情感铺垫 |
| 叙事维度 | 叙事技巧、节奏控制 | 多线叙事、视角切换、节奏调节 |
| 对话维度 | 对话技巧、潜台词 | 潜台词、对话节奏、对话推动剧情 |
| 描写维度 | 描写技巧、细节刻画 | 五感描写、细节伏笔、侧面描写 |
| 开篇维度 | 开篇设计、吸引读者 | 黄金开篇、悬念开局、世界观植入 |
| 高潮维度 | 高潮设计、情绪顶点 | 高潮铺垫、情绪爆发、高潮节奏 |

## 技法文件格式

每个技法文件应包含：

```markdown
# 技法名称

**技法编号**：技法001

**技法名称**：伏笔设计

**适用场景**：
- 章节结尾悬念设置
- 人物命运暗示
- 势力走向预示

**核心原理**：
伏笔是"埋在读者心中的种子"，需要三个条件...

**具体示例**：
[示例片段]

**注意事项**：
1. 不要过于刻意
2. 保持一致性

---
```

## 快速构建

```bash
# 导入技法文件
python technique_builder.py --import "写作技法大全.md"

# 解析目录下所有技法
python technique_builder.py --parse "外部技法资源/"

# 同步到向量库
python technique_builder.py --sync
```
"""
        readme.write_text(readme_content, encoding="utf-8")
        print(f"    ✓ README.md")

        # 创建示例技法
        self._create_sample_techniques()

        print("\n技法目录初始化完成!")
        print(f"目录位置: {self.techniques_dir}")
        return True

    def _create_sample_techniques(self):
        """创建示例技法文件"""
        samples = [
            {
                "dim": "02-剧情维度",
                "name": "伏笔设计",
                "content": """# 伏笔设计

**技法编号**：技法001

**技法名称**：伏笔设计

**适用场景**：
- 章节结尾悬念设置
- 人物命运暗示
- 势力走向预示
- 关键物品埋线

**核心原理**：
伏笔是"埋在读者心中的种子"，需要三个条件：
1. 不显眼但不违和 - 读者注意到但不觉得刻意
2. 有后续呼应 - 在后续章节有明确回收
3. 延迟揭秘产生冲击 - 距离埋设越远，揭秘效果越强

伏笔类型：
- 物品伏笔：关键物品的早期出现
- 人物伏笔：人物言行暗示未来命运
- 环境伏笔：环境描写暗示后续事件
- 对话伏笔：对话中的双关含义

**具体示例**：
```
【埋设】第一章主角随手捡起一块黑色石头，觉得"有些奇怪"。
【呼应】第十章主角发现黑色石头是上古神器的碎片。
【揭秘】第三十章揭示神器是反派势力觊觎之物。
```

**注意事项**：
1. 不要过于刻意，避免读者一眼看出
2. 保持一致性，伏笔内容不能与后续矛盾
3. 揭秘时机要恰当，太早效果弱，太晚读者遗忘
4. 伏笔要有价值，不能是无意义的细节

**相关技法**：
- 悬念布局
- 反转设计
- 信息差利用

---
""",
            },
            {
                "dim": "10-开篇维度",
                "name": "黄金开篇",
                "content": """# 黄金开篇

**技法编号**：技法010

**技法名称**：黄金开篇（黄金三章）

**适用场景**：
- 小说第一章开篇
- 新卷开篇
- 重要转折点重启

**核心原理**：
黄金开篇的核心目标：让读者在前三章内产生强烈阅读欲望。

三大要素：
1. 爽点植入 - 开篇立即给予读者期待感
2. 悬念设置 - 建立未解决的疑问或冲突
3. 世界观速览 - 快速展示小说核心设定

节奏控制：
- 第一章：吸引注意力，建立主角形象
- 第二章：展开核心设定，暗示主线
- 第三章：强化期待，给读者"继续读"的理由

**具体示例**：
```
第一章开篇：
- 主角处于劣势/困境（引发同情）
- 暗示主角有特殊之处（引发期待）
- 快速进入第一个事件（抓住注意力）

示例结构：
主角林雷是家族"废物" → 暗示隐藏天赋 → 发现神秘戒指 → 章节结尾悬念
```

**注意事项**：
1. 开篇不要过长，500-1000字完成核心铺垫
2. 主角必须在第一章出现并建立形象
3. 避免过早展开复杂世界观，循序渐进
4. 给读者明确的期待方向（升级/复仇/探索等）

**相关技法**：
- 世界观植入
- 悬念布局
- 人物出场

---
""",
            },
            {
                "dim": "03-人物维度",
                "name": "人物弧光",
                "content": """# 人物弧光

**技法编号**：技法003

**技法名称**：人物弧光

**适用场景**：
- 主角成长设计
- 重要配角塑造
- 反派蜕变设计

**核心原理**：
人物弧光指角色在故事中的心理/性格/立场变化轨迹。

弧光结构：
起点 → 转折点 → 终点

三种类型：
1. 正向弧光：从缺陷到完善（主角常见）
2. 负向弧光：从完善到堕落（反派常见）
3. 平坦弧光：性格稳定，影响他人（导师/助手常见）

关键转折点：
- 触发事件：改变角色的契机
- 重大选择：角色主动做出的关键决定
- 意识觉醒：角色内心认知的转变

**具体示例**：
```
正向弧光示例：
起点：自卑懦弱的少年
转折点1：被迫承担责任（触发）
转折点2：主动选择冒险（选择）
转折点3：认识到自身价值（觉醒）
终点：自信坚定的领袖
```

**注意事项**：
1. 弧光要有内在逻辑，不能突变
2. 转折点需要外部事件触发+内在认知改变
3. 弧光终点要与故事主题呼应
4. 配角也可以有弧光，增加立体感

**相关技法**：
- 对比塑造
- 人物出场
- 情感层次

---
""",
            },
        ]

        for sample in samples:
            dim_dir = self.techniques_dir / sample["dim"]
            file_path = dim_dir / f"{sample['name']}.md"
            file_path.write_text(sample["content"], encoding="utf-8")
            print(f"    ✓ {sample['dim']}/{sample['name']}.md")

    def import_technique_file(
        self, file_path: Path, target_dimension: Optional[str] = None
    ):
        """导入单个技法文件"""
        print(f"\n导入技法文件: {file_path}")

        if not file_path.exists():
            print(f"    ✗ 文件不存在")
            return False

        content = file_path.read_text(encoding="utf-8")

        # 自动解析或手动指定维度
        techniques = self._parse_technique_content(content, file_path.stem)

        if not techniques:
            print(f"    ✗ 无法解析技法内容")
            return False

        # 写入技法目录
        for tech in techniques:
            dim = target_dimension or tech.get("dimension", "99-外部资源")
            if not dim.endswith("维度") and dim != "99-外部资源":
                dim = f"{dim}维度"

            # 匹配维度目录
            dim_dir = None
            for d in DIMENSIONS:
                if dim in d or d.endswith(dim.replace("维度", "")):
                    dim_dir = self.techniques_dir / d
                    break

            if not dim_dir:
                dim_dir = self.techniques_dir / "99-外部资源"

            dim_dir.mkdir(parents=True, exist_ok=True)

            # 写入技法文件
            tech_file = dim_dir / f"{tech['name']}.md"
            tech_file.write_text(tech["content"], encoding="utf-8")
            print(f"    ✓ {dim_dir.name}/{tech['name']}.md")

        print(f"\n导入完成: {len(techniques)} 条技法")
        return True

    def parse_directory(self, source_dir: Path):
        """解析目录下的所有技法文件"""
        print(f"\n解析技法目录: {source_dir}")

        if not source_dir.exists():
            print(f"    ✗ 目录不存在")
            return False

        # 扫描所有文件
        all_techniques = []

        for file_path in source_dir.rglob("*"):
            if file_path.suffix in [".md", ".txt"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    techniques = self._parse_technique_content(content, file_path.stem)
                    all_techniques.extend(techniques)
                    print(f"    ✓ {file_path.name} ({len(techniques)} 条)")
                except Exception as e:
                    print(f"    ✗ {file_path.name}: {e}")

        if not all_techniques:
            print(f"    ✗ 未找到技法")
            return False

        # 写入技法库
        print(f"\n写入技法库...")
        for tech in all_techniques:
            dim = tech.get("dimension", "99-外部资源")

            dim_dir = self.techniques_dir / dim
            if not dim_dir.exists():
                for d in DIMENSIONS:
                    if dim in d:
                        dim_dir = self.techniques_dir / d
                        break
                if not dim_dir.exists():
                    dim_dir = self.techniques_dir / "99-外部资源"

            tech_file = dim_dir / f"{tech['name']}.md"
            tech_file.write_text(tech["content"], encoding="utf-8")

        print(f"\n解析完成: {len(all_techniques)} 条技法")
        return True

    def _parse_technique_content(self, content: str, default_name: str) -> List[Dict]:
        """解析技法内容"""
        techniques = []

        # 尝试解析标准格式
        # 格式1: ### 技法001：伏笔设计 - 悬念布局
        tech_pattern = re.compile(
            r"### 技法(\d+)[：:]\s*(.+?)(?:\s*-\s*(.+))?$", re.MULTILINE
        )

        matches = list(tech_pattern.finditer(content))

        if matches:
            # 批量技法格式
            for match in matches:
                tech_num = match.group(1)
                tech_name = match.group(2).strip()
                tech_subtitle = match.group(3) or ""

                # 提取该技法的内容（到下一个技法或章节）
                start = match.end()
                end = len(content)
                for next_match in matches:
                    if next_match.start() > match.start():
                        end = next_match.start()
                        break

                tech_content = content[start:end].strip()

                # 提取维度
                dimension = None
                dim_pattern = re.compile(r"## (.+维度)", re.MULTILINE)
                dim_match = dim_pattern.search(content[: match.start()])
                if dim_match:
                    dimension = dim_match.group(1)

                techniques.append(
                    {
                        "id": f"tech_{tech_num}",
                        "name": tech_name,
                        "dimension": dimension or "99-外部资源",
                        "content": self._format_technique(
                            tech_name, tech_subtitle, tech_content
                        ),
                        "source": default_name,
                    }
                )
        else:
            # 单个技法格式（整个文件是一个技法）
            # 提取标题
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            name = title_match.group(1) if title_match else default_name

            # 提取维度（从目录路径或内容）
            dimension = None

            techniques.append(
                {
                    "id": default_name,
                    "name": name,
                    "dimension": dimension or "99-外部资源",
                    "content": content,
                    "source": default_name,
                }
            )

        return techniques

    def _format_technique(self, name: str, subtitle: str, content: str) -> str:
        """格式化技法内容"""
        # 如果内容已经是完整格式，直接返回
        if "**技法名称**" in content:
            return content

        # 否则包装成标准格式
        return TECHNIQUE_TEMPLATE.format(
            技法名称=name,
            编号="自定义",
            场景1="请补充适用场景",
            场景2="",
            场景3="",
            原理描述=content[:500] if content else "请补充核心原理",
            示例内容="请补充具体示例",
            注意1="请补充注意事项",
            注意2="",
            注意3="",
            相关技法1="",
            相关技法2="",
        )

    def sync_to_vectorstore(self):
        """同步技法到向量库"""
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import (
            PointStruct,
            VectorParams,
            Distance,
            SparseVectorParams,
        )
        from FlagEmbedding import BGEM3FlagModel

        print("\n" + "=" * 60)
        print("同步技法到向量库")
        print("=" * 60)

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
        from core.config_loader import get_device
        device = get_device()
        model_path = self.config.get("model_path")
        if model_path:
            model = BGEM3FlagModel(model_path, use_fp16=True, device=device)
        else:
            import os

            cache_path = os.environ.get("BGE_M3_MODEL_PATH")
            if cache_path:
                model = BGEM3FlagModel(cache_path, use_fp16=True, device=device)
            else:
                model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device=device)
        print("    模型加载完成")

        # 收集所有技法
        print("\n收集技法文件...")
        techniques = []
        for md_file in self.techniques_dir.rglob("*.md"):
            if md_file.name in ["README.md", "index.md"]:
                continue

            content = md_file.read_text(encoding="utf-8")

            # 提取维度
            dimension = None
            for part in md_file.parts:
                if any(
                    d in part
                    for d in [
                        "维度",
                        "世界观",
                        "剧情",
                        "人物",
                        "战斗",
                        "氛围",
                        "情感",
                        "叙事",
                        "对话",
                        "描写",
                        "开篇",
                        "高潮",
                    ]
                ):
                    dimension = part
                    break

            # 提取名称
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            name = title_match.group(1) if title_match else md_file.stem

            techniques.append(
                {
                    "id": md_file.stem,
                    "name": name,
                    "dimension": dimension or "通用",
                    "content": content[:3000],
                    "word_count": len(content),
                    "source": md_file.name,
                }
            )

        print(f"    找到 {len(techniques)} 条技法")

        if not techniques:
            print("    ✗ 未找到技法文件")
            return False

        # 同步到向量库
        print("\n同步到向量库...")
        batch_size = 20

        for i in range(0, len(techniques), batch_size):
            batch = techniques[i : i + batch_size]

            texts = [t["content"] for t in batch]
            out = model.encode(texts, return_dense=True, return_sparse=True)

            points = []
            for j, tech in enumerate(batch):
                point = PointStruct(
                    id=int(hash(tech["id"]) % (2**31)),
                    vector={
                        "dense": out["dense_vecs"][j].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][j].keys()),
                            "values": list(out["lexical_weights"][j].values()),
                        },
                    },
                    payload={
                        "name": tech["name"],
                        "dimension": tech["dimension"],
                        "content": tech["content"][:500],
                        "word_count": tech["word_count"],
                        "source": tech["source"],
                    },
                )
                points.append(point)

            client.upsert(self.collection_name, points)
            progress = min(i + batch_size, len(techniques))
            print(f"    [{progress}/{len(techniques)}]")

        # 验证
        info = client.get_collection(self.collection_name)
        print(f"\n✓ {self.collection_name}: {info.points_count:,} 条")

        return True

    def generate_template(self):
        """生成技法模板文件"""
        template_file = self.techniques_dir / "技法模板.md"
        template_file.write_text(TECHNIQUE_TEMPLATE, encoding="utf-8")
        print(f"\n生成模板: {template_file}")
        return template_file


def main():
    parser = argparse.ArgumentParser(description="技法库构建器")
    parser.add_argument("--techniques-dir", default="创作技法", help="技法目录路径")
    parser.add_argument("--config", help="配置文件路径")

    # 命令
    parser.add_argument("--init", action="store_true", help="初始化技法目录结构")
    parser.add_argument("--import", dest="import_file", help="导入技法文件")
    parser.add_argument("--parse", dest="parse_dir", help="解析目录下的所有技法")
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--template", action="store_true", help="生成技法模板")
    parser.add_argument("--dimension", help="指定导入技法的维度")

    args = parser.parse_args()

    # 加载配置
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    # 技法目录
    techniques_dir = Path(args.techniques_dir)
    builder = TechniqueBuilder(techniques_dir, config)

    # 执行命令
    if args.init:
        builder.init_structure()
    elif args.import_file:
        builder.import_technique_file(Path(args.import_file), args.dimension)
    elif args.parse_dir:
        builder.parse_directory(Path(args.parse_dir))
    elif args.sync:
        builder.sync_to_vectorstore()
    elif args.template:
        builder.generate_template()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python technique_builder.py --init")
        print("  python technique_builder.py --import 写作技法大全.md")
        print("  python technique_builder.py --sync")


if __name__ == "__main__":
    main()
