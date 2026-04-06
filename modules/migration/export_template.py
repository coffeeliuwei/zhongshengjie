"""
项目模板导出器
导出项目模板（保留目录结构和工具，清空数据）
"""

import shutil
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class TemplateExporter:
    """
    项目模板导出器

    功能：
    1. 导出项目目录结构
    2. 导出核心工具脚本
    3. 导出配置模板
    4. 清空具体数据（正文、设定、案例）
    5. 生成移植文档
    """

    # 保留的文件/目录（工具和结构）
    PRESERVE_ITEMS = [
        # 核心模块
        "core/",
        "modules/",
        # 系统工具
        ".vectorstore/workflow.py",
        ".vectorstore/verify_all.py",
        ".vectorstore/checklist_scorer.py",
        ".vectorstore/verification_history.py",
        ".vectorstore/scene_writer_mapping.json",
        # 案例库工具
        ".case-library/scripts/",
        # 配置文件
        "CONFIG.md",
        "PROJECT_GUIDE.md",
        "移植指南.md",
        "requirements.txt",
    ]

    # 清空的数据目录/文件
    CLEAR_DATA_ITEMS = [
        # 小说正文
        "正文/",
        "章节大纲/",
        # 设定文件（保留目录结构）
        "设定/*.md",
        # 案例数据（保留工具）
        ".case-library/cases/",
        ".case-library/converted/",
        ".case-library/logs/",
        ".case-library/sources.json",
        ".case-library/unified_index.json",
        ".case-library/unified_stats.json",
        # 向量数据库数据（保留工具）
        ".vectorstore/qdrant/",
        ".vectorstore/knowledge_graph.json",
        # 存档
        "存档/",
        # 缓存
        ".cache/",
        "logs/",
    ]

    # 创建的示例文件
    EXAMPLE_FILES = [
        (
            "设定/人物谱.md",
            "# 人物谱\n\n> 此文件为模板，请添加人物设定\n\n## 主角\n\n（待添加）\n",
        ),
        (
            "设定/十大势力.md",
            "# 十大势力\n\n> 此文件为模板，请添加势力设定\n\n## 势力列表\n\n（待添加）\n",
        ),
        (
            "正文/README.md",
            "# 正文目录\n\n> 此目录存放小说正文\n\n## 章节列表\n\n（待添加）\n",
        ),
        (
            "章节大纲/README.md",
            "# 章节大纲目录\n\n> 此目录存放章节规划\n\n（待添加）\n",
        ),
    ]

    def __init__(self, project_root: Path):
        """
        初始化模板导出器

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root

    def export_template(
        self,
        target_dir: Path,
        preserve_structure: bool = True,
        create_examples: bool = True,
    ) -> Dict[str, Any]:
        """
        导出项目模板

        Args:
            target_dir: 目标目录
            preserve_structure: 是否保留目录结构
            create_examples: 是否创建示例文件

        Returns:
            导出结果字典
        """
        print(f"🚀 开始导出项目模板到: {target_dir}")

        # 创建目标目录
        target_dir.mkdir(parents=True, exist_ok=True)

        # 统计信息
        stats = {
            "preserved_files": 0,
            "preserved_dirs": 0,
            "cleared_files": 0,
            "cleared_dirs": 0,
            "created_examples": 0,
            "errors": [],
        }

        # 1. 复制保留的文件/目录
        print("\n📁 复制核心文件和工具...")
        for item in self.PRESERVE_ITEMS:
            source_path = self.project_root / item

            if not source_path.exists():
                stats["errors"].append(f"保留项不存在: {item}")
                continue

            target_path = target_dir / item

            try:
                if source_path.is_dir():
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                    stats["preserved_dirs"] += 1
                    print(f"  ✅ 目录: {item}")
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    stats["preserved_files"] += 1
                    print(f"  ✅ 文件: {item}")
            except Exception as e:
                stats["errors"].append(f"复制失败 {item}: {e}")

        # 2. 创建清空的数据目录（保留结构）
        if preserve_structure:
            print("\n📂 创建数据目录结构（清空）...")
            for item in self.CLEAR_DATA_ITEMS:
                # 提取目录路径（去除通配符）
                if "*.md" in item:
                    dir_path = item.split("*.md")[0]
                else:
                    dir_path = item.rstrip("/")

                target_path = target_dir / dir_path

                try:
                    target_path.mkdir(parents=True, exist_ok=True)
                    stats["cleared_dirs"] += 1
                    print(f"  ✅ 目录: {dir_path}")
                except Exception as e:
                    stats["errors"].append(f"创建目录失败 {dir_path}: {e}")

        # 3. 创建示例文件
        if create_examples:
            print("\n📝 创建示例文件...")
            for file_path, content in self.EXAMPLE_FILES:
                target_path = target_dir / file_path

                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.write_text(content, encoding="utf-8")
                    stats["created_examples"] += 1
                    print(f"  ✅ 示例: {file_path}")
                except Exception as e:
                    stats["errors"].append(f"创建示例失败 {file_path}: {e}")

        # 4. 创建移植文档
        self._create_migration_document(target_dir, stats)

        # 5. 创建系统配置模板
        self._create_system_config_template(target_dir)

        print(f"\n✅ 模板导出完成！")
        print(f"📊 统计:")
        print(f"  - 保留文件: {stats['preserved_files']}")
        print(f"  - 保留目录: {stats['preserved_dirs']}")
        print(f"  - 创建示例: {stats['created_examples']}")
        print(f"  - 错误数: {len(stats['errors'])}")

        return stats

    def _create_migration_document(
        self, target_dir: Path, stats: Dict[str, Any]
    ) -> None:
        """
        创建移植文档

        Args:
            target_dir: 目标目录
            stats: 统计信息
        """
        migration_doc = target_dir / "MIGRATION.md"

        content = f"""# 众生界项目移植文档

## 移植时间

{datetime.now().isoformat()}

## 移植统计

| 类型 | 数量 |
|------|------|
| 保留文件 | {stats["preserved_files"]} |
| 保留目录 | {stats["preserved_dirs"]} |
| 创建示例 | {stats["created_examples"]} |
| 错误数 | {len(stats["errors"])} |

## 下一步操作

### 1. 初始化环境

```bash
python -m core config --init
```

### 2. 配置资源目录

编辑 `system_config.json`，添加你的小说资源目录：

```json
{
            "directories": {
                "custom_resources": {
                    "玄幻奇幻": "你的路径",
      "武侠仙侠": "你的路径"
    }
  }
}
```

或使用CLI：

```bash
python -m core config --add-resource 玄幻奇幻 "你的路径"
```

### 3. 提取案例（可选）

```bash
python -m core kb --sync case
```

### 4. 添加设定

编辑以下文件：
- `设定/人物谱.md` - 添加人物设定
- `设定/十大势力.md` - 添加势力设定
- `总大纲.md` - 创建总大纲

### 5. 开始创作

```bash
python -m core create --workflow
```

## 保留的核心工具

| 工具 | 路径 | 用途 |
|------|------|------|
| CLI入口 | `core/cli.py` | 统一命令行入口 |
| 工作流 | `.vectorstore/workflow.py` | 知识检索入口 |
| 验证入口 | `.vectorstore/verify_all.py` | 统一验证 |
| 案例提取 | `.case-library/scripts/` | 案例库工具 |

## 注意事项

1. 向量数据库需要重新初始化（Qdrant Docker）
2. 作家技能路径需要根据你的环境调整
3. 配置文件需要根据你的项目调整

---

*移植版本: 2.0*
*原始项目: 众生界*
"""

        migration_doc.write_text(content, encoding="utf-8")
        print(f"  ✅ 文档: MIGRATION.md")

    def _create_system_config_template(self, target_dir: Path) -> None:
        """
        创建系统配置模板

        Args:
            target_dir: 目标目录
        """
        config_template = target_dir / "system_config.json"

        template_content = {
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
                "skills_base_path": "C:\\Users\\你的用户名\\.agents\\skills",
                "writer_preferences": {
                    "世界观": "novelist-canglan",
                    "剧情": "novelist-xuanyi",
                    "人物": "novelist-moyan",
                    "战斗": "novelist-jianchen",
                    "氛围": "novelist-yunxi",
                },
            },
        }

        config_template.write_text(
            json.dumps(template_content, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  ✅ 配置模板: system_config.json")


# 使用示例
if __name__ == "__main__":
    from pathlib import Path

    # 导出模板
    exporter = TemplateExporter(Path("."))
    exporter.export_template(
        target_dir=Path("../众生界-template"),
        preserve_structure=True,
        create_examples=True,
    )
