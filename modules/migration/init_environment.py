"""
环境初始化器
初始化新环境，创建目录结构和配置文件

注意:
    - 本模块为模板生成器，包含的路径示例仅供用户参考配置
    - 生成的配置文件中包含占位符（如 "你的用户名"），需用户自行修改
    - 初始化后的 system_config.json 中的路径应根据实际环境调整
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


class EnvironmentInitializer:
    """
    环境初始化器

    功能：
    1. 创建目录结构
    2. 创建配置文件
    3. 初始化向量数据库
    4. 创建示例数据
    5. 生成初始化文档
    """

    # 必须创建的目录
    REQUIRED_DIRS = [
        # 核心目录
        "core",
        "modules/knowledge_base",
        "modules/validation",
        "modules/creation",
        "modules/visualization",
        "modules/migration",
        # 内容目录
        "设定",
        "创作技法",
        "章节大纲",
        "正文",
        # 系统目录
        ".vectorstore",
        ".case-library/scripts",
        ".case-library/cases",
        ".case-library/converted",
        ".case-library/logs",
        # 输出目录
        "logs",
        ".cache",
        "存档",
    ]

    # 必须创建的配置文件
    REQUIRED_CONFIG_FILES = {
        "CONFIG.md": """# 众生界 - 项目配置

## 基本信息

| 项目 | 内容 |
|------|------|
| 小说名称 | 众生界（请修改） |
| 类型 | 玄幻/科幻融合 |
| 预计篇幅 | 超长篇 |
| 当前状态 | 规划中 |

---

## 文风配置

| 配置项 | 值 |
|--------|-----|
| 文风基调 | 平实厚重 |
| 禁止风格 | 古龙式极简风格 |
| 字数规则 | 上不封顶，情节优先 |

---

## 评估阈值

| 维度 | 阈值 |
|------|------|
| 世界自洽 | ≥7 |
| 人物立体 | ≥6 |
| 情感真实 | ≥6 |
| 战斗逻辑 | ≥6 |
| 文风克制 | ≥6 |
| 剧情张力 | ≥6 |

---

*配置版本: 2.0*
*更新时间: {timestamp}*
""",
        "requirements.txt": """# 众生界依赖库

# 向量数据库
qdrant-client>=1.3.0
sentence-transformers>=2.2.0

# 文本处理
jieba>=0.42.1

# 可视化
pyvis>=0.3.0

# 文件处理
ebooklib>=0.18
mobi>=0.3.3

# 工具库
click>=8.0.0
rich>=13.0.0
""",
        "PROJECT_GUIDE.md": """# 众生界项目指南

> 本文档为项目总纲，整合所有层级README和文档

---

## 一、项目概述

| 项目 | 内容 |
|------|------|
| 小说名称 | 众生界（请修改） |
| 类型 | 玄幻/科幻融合 |
| 当前状态 | 规划中 |

---

## 二、项目结构

```
众生界/
├── core/                 # 核心模块（CLI、配置、路径管理）
├── modules/              # 功能模块
│   ├── knowledge_base/   # 知识入库模块
│   ├── validation/       # 验证模块
│   ├── creation/         # 创作模块
│   ├── visualization/    # 可视化模块
│   └── migration/        # 移植模块
├── 设定/                 # 世界观设定
├── 创作技法/             # 技法体系
├── 章节大纲/             # 章节规划
├── 正文/                 # 小说正文
├── .vectorstore/         # 向量数据库
├── .case-library/        # 案例库
├── CONFIG.md             # 项目配置
└── PROJECT_GUIDE.md      # 项目指南（本文档）
```

---

## 三、快速开始

### 1. 初始化环境

```bash
python -m core config --init
```

### 2. 配置资源目录

```bash
python -m core config --add-resource 玄幻奇幻 "E:\\小说资源\\玄幻奇幻"
```

### 3. 添加设定

编辑 `设定/人物谱.md`、`设定/十大势力.md` 等文件。

### 4. 开始创作

```bash
python -m core create --workflow
```

---

*创建时间: {timestamp}*
""",
    }

    # 示例设定文件
    EXAMPLE_SETTING_FILES = {
        "设定/人物谱.md": """# 人物谱

> 此文件存放人物设定，将自动同步到向量数据库

---

## 主角

### 姓名：待添加

| 属性 | 值 |
|------|-----|
| 姓名 | （待添加） |
| 年龄 | （待添加） |
| 势力 | （待添加） |
| 血脉 | （待添加） |

---

*创建时间: {timestamp}*
""",
        "设定/十大势力.md": """# 十大势力

> 此文件存放势力设定，将自动同步到向量数据库

---

## 势力列表

### 势力1：待添加

| 属性 | 值 |
|------|-----|
| 名称 | （待添加） |
| 立场 | （待添加） |
| 力量体系 | （待添加） |

---

*创建时间: {timestamp}*
""",
        "正文/README.md": """# 正文目录

> 此目录存放小说正文

---

## 章节列表

（待添加）

---

*创建时间: {timestamp}*
""",
        "章节大纲/README.md": """# 章节大纲目录

> 此目录存放章节规划

---

## 章节列表

（待添加）

---

*创建时间: {timestamp}*
""",
    }

    def __init__(self, project_root: Path):
        """
        初始化环境初始化器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root

    def initialize(
        self, create_examples: bool = True, init_vectorstore: bool = False
    ) -> Dict[str, Any]:
        """
        初始化环境

        Args:
            create_examples: 是否创建示例文件
            init_vectorstore: 是否初始化向量数据库

        Returns:
            初始化结果字典
        """
        print(f"🚀 开始初始化环境: {self.project_root}")

        timestamp = datetime.now().isoformat()

        stats = {
            "created_dirs": 0,
            "created_config_files": 0,
            "created_examples": 0,
            "init_vectorstore": init_vectorstore,
            "errors": [],
        }

        # 1. 创建目录结构
        print("\n📂 创建目录结构...")
        for dir_path in self.REQUIRED_DIRS:
            full_path = self.project_root / dir_path

            try:
                full_path.mkdir(parents=True, exist_ok=True)
                stats["created_dirs"] += 1
                print(f"  ✅ {dir_path}")
            except Exception as e:
                stats["errors"].append(f"创建目录失败 {dir_path}: {e}")

        # 2. 创建配置文件
        print("\n📝 创建配置文件...")
        for file_name, content_template in self.REQUIRED_CONFIG_FILES.items():
            file_path = self.project_root / file_name

            try:
                content = content_template.format(timestamp=timestamp)
                file_path.write_text(content, encoding="utf-8")
                stats["created_config_files"] += 1
                print(f"  ✅ {file_name}")
            except Exception as e:
                stats["errors"].append(f"创建配置失败 {file_name}: {e}")

        # 3. 创建示例文件
        if create_examples:
            print("\n📝 创建示例文件...")
            for file_name, content_template in self.EXAMPLE_SETTING_FILES.items():
                file_path = self.project_root / file_name

                try:
                    content = content_template.format(timestamp=timestamp)
                    file_path.write_text(content, encoding="utf-8")
                    stats["created_examples"] += 1
                    print(f"  ✅ {file_name}")
                except Exception as e:
                    stats["errors"].append(f"创建示例失败 {file_name}: {e}")

        # 4. 创建system_config.json
        self._create_system_config(timestamp)

        # 5. 初始化向量数据库（可选）
        if init_vectorstore:
            print("\n💾 初始化向量数据库...")
            self._init_vectorstore()

        # 6. 创建初始化文档
        self._create_init_document(timestamp, stats)

        print(f"\n✅ 环境初始化完成！")
        print(f"📊 统计:")
        print(f"  - 创建目录: {stats['created_dirs']}")
        print(f"  - 创建配置: {stats['created_config_files']}")
        print(f"  - 创建示例: {stats['created_examples']}")
        print(f"  - 错误数: {len(stats['errors'])}")

        print(f"\n📖 下一步:")
        print(f"  1. 编辑 CONFIG.md 配置基本信息")
        print(f"  2. 编辑 system_config.json 配置资源目录")
        print(f"  3. 编辑设定文件（人物谱、势力等）")
        print(f"  4. 运行 `python -m core kb --sync novel` 同步设定")
        print(f"  5. 运行 `python -m core create --workflow` 开始创作")

        return stats

    def _create_system_config(self, timestamp: str) -> None:
        """
        创建system_config.json

        Args:
            timestamp: 时间戳
        """
        config_path = self.project_root / "system_config.json"

        template = {
            "database": {
                "host": "localhost",
                "port": 6333,
                "collections": {
                    "novel_settings": "novel_settings",
                    "writing_techniques": "writing_techniques",
                    "case_library": "case_library",
                    "creation_context": "creation_context",
                },
            },
            "directories": {
                "root": ".",
                "settings_dir": "设定",
                "techniques_dir": "创作技法",
                "chapters_dir": "章节大纲",
                "content_dir": "正文",
                "vectorstore_dir": ".vectorstore",
                "case_library_dir": ".case-library",
                "modules_dir": "modules",
                "logs_dir": "logs",
                "cache_dir": ".cache",
                "archive_dir": "存档",
                "custom_resources": {},
            },
            "modules": {
                "knowledge_base_enabled": True,
                "knowledge_base_auto_sync": False,
                "validation_enabled": True,
                "creation_enabled": True,
                "creation_max_iterations": 3,
                "creation_parallel_enabled": True,
                "visualization_enabled": True,
            },
            "writers": {
                "scene_writer_mapping_file": "scene_writer_mapping.json",
                # 注意: skills_base_path 为模板占位符，用户初始化后需修改为实际路径
                "skills_base_path": "C:\\Users\\你的用户名\\.agents\\skills",
                "writer_preference": {},
            },
            "metadata": {"created_at": timestamp, "version": "2.0"},
        }

        config_path.write_text(
            json.dumps(template, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  ✅ system_config.json")

    def _init_vectorstore(self) -> None:
        """
        初始化向量数据库

        注意：需要Qdrant Docker运行
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            client = QdrantClient(host="localhost", port=6333)

            # 创建集合
            from sentence_transformers import SentenceTransformer

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            vector_size = embedder.get_sentence_embedding_dimension()

            collections = [
                "novel_settings",
                "writing_techniques",
                "case_library",
                "creation_context",
            ]

            for collection_name in collections:
                try:
                    client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=vector_size, distance=Distance.COSINE
                        ),
                    )
                    print(f"  ✅ 创建集合: {collection_name}")
                except Exception:
                    print(f"  ⚠️ 集合已存在: {collection_name}")

        except ImportError:
            print("  ⚠️ qdrant-client未安装，跳过向量数据库初始化")
        except Exception as e:
            print(f"  ❌ 向量数据库初始化失败: {e}")

    def _create_init_document(self, timestamp: str, stats: Dict[str, Any]) -> None:
        """
        创建初始化文档

        Args:
            timestamp: 时间戳
            stats: 统计信息
        """
        init_doc = self.project_root / "INIT_LOG.md"

        content = f"""# 环境初始化日志

## 初始化时间

{timestamp}

## 初始化统计

| 类型 | 数量 |
|------|------|
| 创建目录 | {stats["created_dirs"]} |
| 创建配置 | {stats["created_config_files"]} |
| 创建示例 | {stats["created_examples"]} |
| 错误数 | {len(stats["errors"])} |

## 目录结构

```
众生界/
├── core/                 ✅ 核心模块
├── modules/              ✅ 功能模块
├── 设定/                 ✅ 设定目录（已创建示例）
├── 正文/                 ✅ 正文目录
├── .vectorstore/         ✅ 向量数据库目录
├── .case-library/        ✅ 案例库目录
└── CONFIG.md             ✅ 项目配置
```

## 下一步

1. 编辑 `CONFIG.md` - 配置小说基本信息
2. 编辑 `system_config.json` - 配置资源目录和作家路径
3. 编辑设定文件 - 添加人物、势力设定
4. 启动Qdrant Docker - 运行向量数据库
5. 同步设定到向量库 - `python -m core kb --sync novel`
6. 开始创作 - `python -m core create --workflow`

---

*初始化版本: 2.0*
"""

        init_doc.write_text(content, encoding="utf-8")
        print(f"  ✅ INIT_LOG.md")


# 使用示例
if __name__ == "__main__":
    from pathlib import Path

    # 初始化环境
    initializer = EnvironmentInitializer(Path("."))
    initializer.initialize(create_examples=True, init_vectorstore=False)
