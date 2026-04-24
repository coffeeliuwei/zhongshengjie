#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
众生界小说创作支持系统 - 环境初始化脚本
===========================================

在新环境中快速搭建完整系统，无需小说资源即可运行。

使用方法：
    python init_environment.py              # 完整初始化
    python init_environment.py --check      # 检查环境状态
    python init_environment.py --minimal    # 最小化初始化（仅核心结构）

功能：
    1. 创建目录结构
    2. 生成配置文件
    3. 初始化向量数据库
    4. 创建示例案例（用于测试）
    5. 安装依赖检查
"""

import os
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 获取项目根目录（支持相对路径，便于移植）
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent


class EnvironmentInitializer:
    """环境初始化器"""

    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or PROJECT_DIR
        self.case_library = self.project_dir / ".case-library"
        self.vectorstore = self.project_dir / ".vectorstore"
        self.logs = {}

    def init_all(self, minimal: bool = False):
        """完整初始化"""
        print("=" * 60)
        print("众生界小说创作支持系统 - 环境初始化")
        print("=" * 60)
        print(f"项目目录: {self.project_dir}")
        print()

        steps = [
            ("创建目录结构", self._create_directories),
            ("生成配置文件", self._create_configs),
            ("初始化向量数据库", self._init_vectorstore),
        ]

        if not minimal:
            steps.extend(
                [
                    ("创建示例案例", self._create_sample_cases),
                    ("创建使用指南", self._create_guide),
                ]
            )

        steps.append(("检查依赖", self._check_dependencies))

        for name, func in steps:
            print(f"\n[步骤] {name}...")
            try:
                result = func()
                self.logs[name] = {"status": "success", "result": result}
                print(f"  ✅ 完成")
            except Exception as e:
                self.logs[name] = {"status": "error", "error": str(e)}
                print(f"  ❌ 失败: {e}")

        self._save_init_log()
        self._print_summary()

    def _create_directories(self) -> Dict:
        """创建目录结构"""
        dirs = {
            # 案例库目录
            "case_library": self.case_library,
            "cases": self.case_library / "cases",
            "converted": self.case_library / "converted",
            "scripts": self.case_library / "scripts",
            "logs": self.case_library / "logs",
            # 向量存储目录
            "vectorstore": self.vectorstore,
            "qdrant": self.vectorstore / "qdrant",
            "embeddings": self.vectorstore / "embeddings",
            # 场景类型目录
            **{
                f"cases_{scene}": self.case_library / "cases" / scene
                for scene in [
                    "开篇场景",
                    "冲突升级",
                    "转折场景",
                    "高潮场景",
                    "结尾场景",
                    "人物出场",
                    "对话场景",
                    "心理场景",
                    "环境场景",
                    "情感场景",
                    "悬念场景",
                    "打脸场景",
                    "升级突破",
                    "战斗场景",
                    "获得场景",
                    "伏笔设置",
                    "伏笔回收",
                ]
            },
        }

        created = []
        for name, path in dirs.items():
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(name)

        return {"created_dirs": len(created), "total_dirs": len(dirs)}

    def _create_configs(self) -> Dict:
        """生成配置文件"""
        configs = {}

        # 1. 系统配置
        system_config = {
            "version": "2.0",
            "project_name": "众生界小说创作支持系统",
            "initialized_time": datetime.now().isoformat(),
            "paths": {
                "project_dir": str(self.project_dir),
                "case_library": str(self.case_library),
                "vectorstore": str(self.vectorstore),
                "cases": str(self.case_library / "cases"),
                "converted": str(self.case_library / "converted"),
            },
            "novel_resources": {
                "description": "小说资源路径配置",
                "note": "将小说资源放在以下目录，或修改config.json中的novel_sources.directories",
                "paths": ["请在config.json中配置novel_sources.directories"],
                "how_to_add": "在config.json中添加novel_sources.directories配置项，或使用--source-dirs参数",
            },
        }

        system_config_path = self.project_dir / "system_config.json"
        with open(system_config_path, "w", encoding="utf-8") as f:
            json.dump(system_config, f, ensure_ascii=False, indent=2)
        configs["system_config"] = str(system_config_path)

        # 2. 提取配置
        extraction_config = {
            "description": "案例提取配置",
            "version": "2.0",
            "resources": [],
            "converted_directory": str(self.case_library / "converted"),
            "output": {
                "cases_directory": str(self.case_library / "cases"),
                "index_file": str(self.case_library / "unified_index.json"),
                "stats_file": str(self.case_library / "unified_stats.json"),
            },
            "extraction_settings": {
                "chapters_to_process": 5,
                "include_last_chapter": True,
                "min_content_length": 300,
                "min_quality_score": 6.0,
                "max_cases_per_chapter": 3,
            },
            "how_to_use": {
                "step1": "将小说文件放入任意目录",
                "step2": "在resources数组中添加路径配置",
                "step3": "运行 python unified_case_extractor.py --extract",
            },
        }

        extraction_config_path = self.case_library / "extraction_config.json"
        with open(extraction_config_path, "w", encoding="utf-8") as f:
            json.dump(extraction_config, f, ensure_ascii=False, indent=2)
        configs["extraction_config"] = str(extraction_config_path)

        # 3. sources.json（资源索引）
        sources = {
            "sources": [],
            "source_template": {
                "id": "source_XXX",
                "name": "来源名称",
                "path": "来源路径",
                "status": "pending",
                "file_count": 0,
                "format": "txt|epub|mobi|mixed",
                "genres": [],
                "added_time": "",
                "extracted_time": None,
            },
            "notes": ["初始化完成，等待添加小说资源"],
        }

        sources_path = self.case_library / "sources.json"
        with open(sources_path, "w", encoding="utf-8") as f:
            json.dump(sources, f, ensure_ascii=False, indent=2)
        configs["sources"] = str(sources_path)

        # 4. 场景-作家映射
        scene_writer_mapping = {
            "version": "2.0",
            "description": "场景类型与作家协作映射",
            "writers": {
                "苍澜": {
                    "role": "世界观架构师",
                    "specialty": "宏大设定、权力体系、世界规则",
                },
                "剑尘": {
                    "role": "战斗设计师",
                    "specialty": "热血战斗、功法体系、冲突张力",
                },
                "墨言": {
                    "role": "人物刻画师",
                    "specialty": "情感细腻、心理描写、人物成长",
                },
                "玄一": {
                    "role": "剧情编织师",
                    "specialty": "伏笔设计、悬念布局、反转策划",
                },
                "云溪": {
                    "role": "意境营造师",
                    "specialty": "氛围描写、诗意语言、美学构建",
                },
            },
            "scene_mapping": {
                "开篇场景": {"primary": "云溪", "secondary": ["苍澜"]},
                "冲突升级": {"primary": "玄一", "secondary": ["剑尘"]},
                "转折场景": {"primary": "玄一", "secondary": []},
                "高潮场景": {"primary": "剑尘", "secondary": ["玄一"]},
                "结尾场景": {"primary": "云溪", "secondary": []},
                "人物出场": {"primary": "墨言", "secondary": []},
                "对话场景": {"primary": "墨言", "secondary": ["剑尘"]},
                "心理场景": {"primary": "墨言", "secondary": []},
                "环境场景": {"primary": "云溪", "secondary": []},
                "情感场景": {"primary": "墨言", "secondary": []},
                "悬念场景": {"primary": "玄一", "secondary": []},
                "打脸场景": {"primary": "剑尘", "secondary": ["苍澜"]},
                "升级突破": {"primary": "苍澜", "secondary": ["剑尘"]},
                "战斗场景": {"primary": "剑尘", "secondary": []},
                "获得场景": {"primary": "苍澜", "secondary": []},
                "伏笔设置": {"primary": "玄一", "secondary": []},
                "伏笔回收": {"primary": "玄一", "secondary": []},
            },
        }

        mapping_path = self.vectorstore / "scene_writer_mapping.json"
        with open(mapping_path, "w", encoding="utf-8") as f:
            json.dump(scene_writer_mapping, f, ensure_ascii=False, indent=2)
        configs["scene_writer_mapping"] = str(mapping_path)

        # 5. requirements.txt
        requirements = """# 众生界小说创作支持系统依赖
# 核心依赖
sentence-transformers>=2.2.0
qdrant-client>=1.4.0
numpy>=1.21.0

# 格式转换
ebooklib>=0.18
mobi>=0.3.3

# 可选依赖（按需安装）
# torch>=2.0.0
# transformers>=4.30.0
"""

        req_path = self.project_dir / "requirements.txt"
        with open(req_path, "w", encoding="utf-8") as f:
            f.write(requirements)
        configs["requirements"] = str(req_path)

        return {"created_configs": len(configs), "files": configs}

    def _init_vectorstore(self) -> Dict:
        """初始化向量数据库"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            qdrant_path = self.vectorstore / "qdrant"
            client = QdrantClient(path=str(qdrant_path))

            # 创建案例库集合
            collections = ["case_library", "techniques", "scenes"]
            created = []

            for collection in collections:
                try:
                    client.create_collection(
                        collection_name=collection,
                        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                    )
                    created.append(collection)
                except Exception:
                    pass  # 集合已存在

            return {"status": "initialized", "collections": created}

        except ImportError:
            return {"status": "skipped", "reason": "qdrant-client未安装"}

    def _create_sample_cases(self) -> Dict:
        """创建示例案例（用于测试系统）"""
        sample_cases = [
            {
                "scene_type": "开篇场景",
                "genre": "玄幻奇幻",
                "content": '第一章 天赋觉醒\n\n苍穹大陆，武道为尊。在这片浩瀚无垠的大陆上，强者为王，弱者为寇。每个人在十六岁时都会觉醒天赋，天赋的高低决定了他们一生的命运。\n\n"又是废物天赋！" 测试台前，长老冷漠的声音如同宣判死刑。台下，一个少年的脸色瞬间苍白如纸。\n\n"萧尘，灵气亲和度零，无天赋。"\n\n四周瞬间响起一阵嘲笑声。萧尘握紧拳头，指甲深深陷入掌心，鲜血顺着指缝滴落。他抬起头，眼中闪烁着不甘的光芒。',
                "quality_score": 7.5,
                "emotion_value": 6.5,
                "techniques": ["悬念设置", "代入感营造"],
                "keywords": ["天赋", "觉醒", "废物"],
            },
            {
                "scene_type": "战斗场景",
                "genre": "玄幻奇幻",
                "content": '"死！" 萧尘一声怒吼，体内灵气如江河奔涌，汇聚于右拳之上。金色的光芒照亮了整片夜空。\n\n对方显然没料到这个看似瘦弱的少年竟然蕴含着如此恐怖的力量，仓促间举起长剑格挡。\n\n"轰！"\n\n拳剑相撞，发出一声震耳欲聋的巨响。气浪翻滚，将周围十丈内的草木尽数摧毁。\n\n那人连退三步，脸上露出难以置信的神色："这...这怎么可能？你明明是废物天赋！"',
                "quality_score": 8.0,
                "emotion_value": 7.5,
                "techniques": ["节奏控制", "情绪强化"],
                "keywords": ["战斗", "实力", "震惊"],
            },
            {
                "scene_type": "情感场景",
                "genre": "女频言情",
                "content": '她站在雨中，任凭冰冷的雨水打湿衣裳。那个背影越走越远，终究是没有回头看她一眼。\n\n"原来，在他心里，我从来都不是那个特别的存在。" 她苦笑着，眼泪混着雨水滑落脸庞。\n\n身旁的丫鬟心疼地为她撑起伞："小姐，我们回去吧。"\n\n她轻轻摇头："再让我站一会儿。就一会儿。"\n\n雨势渐大，模糊了那个已经消失在街角的身影，也模糊了她最后的期盼。',
                "quality_score": 7.0,
                "emotion_value": 8.0,
                "techniques": ["环境烘托", "情感铺垫"],
                "keywords": ["雨", "离开", "心痛"],
            },
        ]

        created = 0
        for i, case_data in enumerate(sample_cases):
            scene_dir = (
                self.case_library
                / "cases"
                / case_data["scene_type"]
                / case_data["genre"]
            )
            scene_dir.mkdir(parents=True, exist_ok=True)

            case_id = f"sample_{i + 1:03d}"

            # 保存内容
            txt_path = scene_dir / f"{case_id}.txt"
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(case_data["content"])

            # 保存元数据
            metadata = {
                "case_id": case_id,
                "source": {"source_id": "sample", "novel_name": "示例案例"},
                "scene": {
                    "type": case_data["scene_type"],
                    "word_count": len(case_data["content"]),
                },
                "quality": {
                    "overall_score": case_data["quality_score"],
                    "emotion_value": case_data["emotion_value"],
                },
                "tags": {
                    "techniques": case_data["techniques"],
                    "keywords": case_data["keywords"],
                },
                "is_sample": True,
            }

            json_path = scene_dir / f"{case_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            created += 1

        return {"created_samples": created}

    def _create_guide(self) -> Dict:
        """创建使用指南"""
        guide = """# 众生界小说创作支持系统 - 使用指南

## 快速开始

### 1. 配置小说资源路径

在 `config.json` 中配置小说资源目录：

```json
{
  "novel_sources": {
    "directories": [
      "你的小说目录1",
      "你的小说目录2",
      "./novels"
    ]
  }
}
```

或者使用命令行参数：

```bash
python unified_case_extractor.py --source-dirs "你的小说目录1" "你的小说目录2"
```

### 2. 添加小说资源

将小说文件（txt/epub/mobi格式）放入配置的目录中。

### 3. 提取案例

```bash
# 扫描文件
python unified_case_extractor.py --scan

# 提取案例
python unified_case_extractor.py --extract

# 查看统计
python unified_case_extractor.py --stats
```

### 3. 同步到向量数据库

```bash
python sync_cases_to_qdrant.py
```

### 4. 使用工作流

```python
from workflow import NovelWorkflow

workflow = NovelWorkflow()
result = workflow.generate_chapter(
    scene_type="开篇场景",
    genre="玄幻奇幻",
    context={"protagonist": "萧尘", "setting": "苍穹大陆"}
)
```

## 目录结构

```
众生界/
├── .case-library/           # 案例库
│   ├── cases/               # 案例文件（按场景类型/题材组织）
│   ├── converted/           # 转换后的txt文件
│   ├── scripts/             # 处理脚本
│   ├── extraction_config.json  # 提取配置
│   └── sources.json         # 资源索引
│
├── .vectorstore/            # 向量存储
│   ├── qdrant/              # Qdrant数据库
│   └── scene_writer_mapping.json  # 场景-作家映射
│
├── system_config.json       # 系统配置
└── requirements.txt         # 依赖列表
```

## 场景类型（17种核心类型）

### 核心场景
- 开篇场景、冲突升级、转折场景、高潮场景、结尾场景

### 功能场景
- 人物出场、对话场景、心理场景、环境场景、情感场景、悬念场景

### 网文特色场景
- 打脸场景、升级突破、战斗场景、获得场景、伏笔设置、伏笔回收

## 作家协作

| 作家 | 专长 | 负责场景 |
|------|------|----------|
| 苍澜 | 世界观架构 | 升级突破、获得场景 |
| 剑尘 | 战斗设计 | 战斗场景、打脸场景、高潮场景 |
| 墨言 | 人物刻画 | 情感场景、心理场景、人物出场 |
| 玄一 | 剧情编织 | 转折场景、悬念场景、伏笔 |
| 云溪 | 意境营造 | 开篇场景、结尾场景、环境场景 |

## 注意事项

1. 首次使用需安装依赖：`pip install -r requirements.txt`
2. 案例提取会自动跳过已处理的文件
3. 质量分低于6.0的案例会被过滤
4. 支持增量添加新资源

---
初始化时间: {init_time}
""".format(init_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        guide_path = self.project_dir / "使用指南.md"
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide)

        return {"guide_path": str(guide_path)}

    def _check_dependencies(self) -> Dict:
        """检查依赖"""
        dependencies = {
            "qdrant-client": "qdrant_client",
            "sentence-transformers": "sentence_transformers",
            "ebooklib": "ebooklib",
            "mobi": "mobi",
            "numpy": "numpy",
        }

        status = {}
        for name, module in dependencies.items():
            try:
                __import__(module)
                status[name] = "✅ 已安装"
            except ImportError:
                status[name] = "❌ 未安装"

        return status

    def _save_init_log(self):
        """保存初始化日志"""
        log_path = self.case_library / "logs" / "init_log.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "init_time": datetime.now().isoformat(),
                    "project_dir": str(self.project_dir),
                    "logs": self.logs,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _print_summary(self):
        """打印摘要"""
        print("\n" + "=" * 60)
        print("初始化完成！")
        print("=" * 60)

        success = sum(1 for v in self.logs.values() if v["status"] == "success")
        total = len(self.logs)

        print(f"\n完成步骤: {success}/{total}")

        print("\n下一步操作:")
        print("1. 在 config.json 中配置 novel_sources.directories")
        print("2. 运行: python unified_case_extractor.py --scan")
        print("3. 运行: python unified_case_extractor.py --extract")

        print("\n配置文件位置:")
        print(f"  - 系统配置: {self.project_dir / 'system_config.json'}")
        print(f"  - 提取配置: {self.case_library / 'extraction_config.json'}")
        print(f"  - 使用指南: {self.project_dir / '使用指南.md'}")

    def check_environment(self) -> Dict:
        """检查环境状态"""
        print("检查环境状态...")
        print(f"项目目录: {self.project_dir}\n")

        checks = {
            "目录结构": self.case_library.exists(),
            "案例目录": (self.case_library / "cases").exists(),
            "转换目录": (self.case_library / "converted").exists(),
            "向量存储": self.vectorstore.exists(),
            "系统配置": (self.project_dir / "system_config.json").exists(),
            "提取配置": (self.case_library / "extraction_config.json").exists(),
            "场景映射": (self.vectorstore / "scene_writer_mapping.json").exists(),
        }

        for name, exists in checks.items():
            status = "✅" if exists else "❌"
            print(f"  {status} {name}")

        # 检查案例数量
        cases_dir = self.case_library / "cases"
        if cases_dir.exists():
            case_count = sum(1 for _ in cases_dir.rglob("*.json"))
            print(f"\n案例数量: {case_count}")
        else:
            print(f"\n案例数量: 0")

        return checks


def main():
    import argparse

    parser = argparse.ArgumentParser(description="众生界系统环境初始化")
    parser.add_argument("--check", action="store_true", help="检查环境状态")
    parser.add_argument("--minimal", action="store_true", help="最小化初始化")
    parser.add_argument("--project-dir", type=str, default=None, help="项目目录路径")

    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else None
    initializer = EnvironmentInitializer(project_dir)

    if args.check:
        initializer.check_environment()
    else:
        initializer.init_all(minimal=args.minimal)


if __name__ == "__main__":
    main()
