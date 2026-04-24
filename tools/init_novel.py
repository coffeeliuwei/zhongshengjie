#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化新小说项目
===============

创建小说创作系统所需的目录结构和配置文件。
支持从模板创建世界观配置。

用法：
    # 创建完整项目结构
    python init_novel.py --name "我的小说" --path "D:/小说数据"
    
    # 从模板创建世界观配置（P5 多小说解耦）
    python init_novel.py --name "我的玄幻" --template 修仙世界示例
    python init_novel.py --list-templates
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

# P5 多小说解耦：世界配置路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORLDS_DIR = PROJECT_ROOT / "config" / "worlds"
CONFIG_PATH = PROJECT_ROOT / "config.json"


def list_templates() -> list[str]:
    """列出可用世界配置模板"""
    templates = []
    for p in WORLDS_DIR.glob("*.json"):
        if "示例" in p.stem:
            templates.append(p.stem)
    return templates


def create_world_config(novel_name: str, template: str) -> Path:
    """从模板创建世界配置文件"""
    template_path = WORLDS_DIR / f"{template}.json"
    target_path = WORLDS_DIR / f"{novel_name}.json"

    if not template_path.exists():
        print(f"[错误] 模板文件不存在: {template_path}")
        return None

    if target_path.exists():
        print(f"[跳过] 世界配置已存在: {target_path}")
        return target_path

    data = json.loads(template_path.read_text(encoding="utf-8"))
    data["world_name"] = novel_name
    data["description"] = f"{novel_name} — 请在此填写世界观描述"

    target_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[创建] 世界配置: {target_path}")
    return target_path


def update_config_json(novel_name: str) -> None:
    """更新 config.json 的 worldview.current_world"""
    if not CONFIG_PATH.exists():
        print(f"[警告] config.json 不存在，请先复制 config.example.json")
        return

    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    old_world = data.get("worldview", {}).get("current_world", "未设置")

    if "worldview" not in data:
        data["worldview"] = {}
    data["worldview"]["current_world"] = novel_name

    CONFIG_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[更新] config.json worldview.current_world: {old_world!r} → {novel_name!r}")


def create_directory_structure(base_path: Path):
    """创建目录结构"""
    directories = {
        "正文": "已发布章节",
        "章节大纲": "章节规划",
        "设定": "世界观/角色设定",
        "创作技法": "技法库（按维度组织）",
        "章节经验日志": "经验沉淀",
        "写作标准积累": "用户修改要求",
        ".vectorstore": "向量数据库配置",
        ".case-library": "标杆案例库（可选）",
        "logs": "日志",
        ".cache": "缓存",
        "存档": "存档",
        "core": "核心模块（预留）",
        "modules": "功能模块（预留）",
        "tools": "工具脚本",
        "tests": "测试",
        "docs": "文档",
    }

    created = []
    for name, desc in directories.items():
        dir_path = base_path / name
        dir_path.mkdir(parents=True, exist_ok=True)
        created.append((name, desc))

    return created


def create_config_template(base_path: Path, novel_name: str):
    """创建配置模板"""
    config = {
        "project": {
            "name": novel_name,
            "version": "1.0.0",
            "created": datetime.now().strftime("%Y-%m-%d"),
        },
        "paths": {
            "data_base_path": str(base_path),
            "chapters": "正文",
            "outlines": "章节大纲",
            "settings": "设定",
            "experience_logs": "章节经验日志",
            "writing_standards": "写作标准积累",
            "techniques": "创作技法",
            "vectorstore": ".vectorstore",
            "case_library": ".case-library",
        },
        "database": {
            "qdrant_host": "localhost",
            "qdrant_port": 6333,
            "collections": {
                "novel_settings": "novel_settings_v2",
                "writing_techniques": "writing_techniques_v2",
                "case_library": "case_library_v2",
            },
        },
        "model": {
            "embedding_model": "BAAI/bge-m3",
            "vector_size": 1024,
        },
        "modules": {
            "knowledge_base_enabled": True,
            "validation_enabled": True,
            "creation_enabled": True,
            "creation_max_iterations": 3,
        },
    }

    config_file = base_path / "config.example.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return config_file


def create_gitignore(base_path: Path):
    """创建 .gitignore"""
    content = """# 小说机密数据
正文/
章节大纲/
设定/
章节经验日志/
写作标准积累/
存档/

# 提炼数据
创作技法/
.case-library/

# 向量数据库
.vectorstore/

# 配置
config.json
config.local.json
.env

# 运行时
.state/
logs/
.cache/
*.log

# Python
__pycache__/
*.py[cod]
*.egg-info/

# IDE
.vscode/
.idea/
"""

    gitignore_file = base_path / ".gitignore"
    gitignore_file.write_text(content, encoding="utf-8")
    return gitignore_file


def create_sample_technique(base_path: Path):
    """创建示例技法文件"""
    sample = """# 创作技法库

技法库按维度组织，每个维度一个子目录。

## 目录结构

```
创作技法/
├── 01-世界观维度/
│   ├── 力量体系设计.md
│   └── 势力架构.md
├── 02-剧情维度/
│   ├── 伏笔设计.md
│   └── 反转技巧.md
├── 03-人物维度/
│   ├── 人物弧光.md
│   └── 对比塑造.md
├── 04-战斗冲突维度/
├── 05-氛围意境维度/
├── 06-情感维度/
├── 07-叙事维度/
├── 08-对话维度/
├── 09-描写维度/
├── 10-开篇维度/
├── 11-高潮维度/
└── 99-外部资源/
    └── 高级写作技法大全.md
```

## 技法格式示例

### 技法001：伏笔设计 - 悬念布局

**技法名称**：伏笔设计

**适用场景**：
- 章节结尾悬念设置
- 人物命运暗示
- 势力走向预示

**核心原理**：
伏笔是"埋在读者心中的种子"，需要三个条件：
1. 不显眼但不违和
2. 有后续呼应
3. 延迟揭秘产生冲击

**具体示例**：
[示例内容]

**注意事项**：
1. 不要过于刻意
2. 保持一致性
3. 揭秘时机要恰当

---
"""

    # 创建技法目录
    tech_dir = base_path / "创作技法"

    # 创建维度目录
    dimensions = [
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

    for dim in dimensions:
        (tech_dir / dim).mkdir(exist_ok=True)

    # 创建示例文件
    readme_file = tech_dir / "README.md"
    readme_file.write_text(sample, encoding="utf-8")

    return tech_dir


def create_sample_settings(base_path: Path):
    """创建示例设定文件"""
    settings_dir = base_path / "设定"

    sample_outline = """# 总大纲

## 第一卷：觉醒

### 核心主线
[描述核心主线]

### 关键转折
1. [第一个转折]
2. [第二个转折]

## 世界观概要
[世界观简述]

## 人物主线
[主要人物成长轨迹]
"""

    sample_characters = """# 人物谱

## 主角

### 基本信息卡片
- 姓名：[角色名]
- 年龄：[年龄]
- 身份：[身份]
- 性格关键词：[关键词1]、[关键词2]

### 人物弧光
- 起点：[初始状态]
- 转折点：[关键变化]
- 终点：[目标状态]

### 与其他人物关系
- [关系1]
- [关系2]

## 配角

[配角信息]
"""

    (settings_dir / "总大纲.md").write_text(sample_outline, encoding="utf-8")
    (settings_dir / "人物谱.md").write_text(sample_characters, encoding="utf-8")

    return settings_dir


def main():
    parser = argparse.ArgumentParser(description="初始化新小说项目")
    parser.add_argument("--name", help="小说名称")
    parser.add_argument("--path", help="项目路径（创建完整项目结构时需要）")
    parser.add_argument("--template", default="修仙世界示例", help="使用哪个世界配置模板")
    parser.add_argument("--list-templates", action="store_true", help="列出可用世界配置模板")
    parser.add_argument("--skip-sample", action="store_true", help="跳过示例文件创建")

    args = parser.parse_args()

    # --list-templates 模式
    if args.list_templates:
        templates = list_templates()
        print("可用世界配置模板：")
        for t in templates:
            print(f"  {t}")
        return

    # --template 模式：创建世界配置 + 更新 config.json
    if args.name and not args.path:
        novel_name = args.name.strip()
        if not novel_name:
            print("[错误] 小说名称不能为空")
            return

        print(f"\n=== 初始化小说世界观：{novel_name} ===\n")
        world_path = create_world_config(novel_name, args.template)
        if world_path:
            update_config_json(novel_name)
            print(f"""
=== 初始化完成 ===

下一步：
1. 编辑世界观配置：
   {world_path}

2. 填写以下字段（基于你的小说设定）：
   - power_systems   力量体系（修仙/魔法/科技等）
   - factions        主要势力
   - key_characters  核心角色
   - core_principles 世界核心原则

3. 开始创作（对话方式）：
   "写第一章"
""")
        return

    # --path 模式：创建完整项目结构
    if args.name and args.path:
        base_path = Path(args.path)

        print("=" * 60)
        print(f"初始化小说项目: {args.name}")
        print("=" * 60)

        # 创建目录结构
        print("\n[1] 创建目录结构...")
        created = create_directory_structure(base_path)
        for name, desc in created:
            print(f"    ✓ {name} - {desc}")

        # 创建配置文件
        print("\n[2] 创建配置文件...")
        config_file = create_config_template(base_path, args.name)
        print(f"    ✓ {config_file}")

        # 创建 .gitignore
        print("\n[3] 创建 .gitignore...")
        gitignore = create_gitignore(base_path)
        print(f"    ✓ {gitignore}")

        # 创建示例文件
        if not args.skip_sample:
            print("\n[4] 创建示例文件...")
            tech_dir = create_sample_technique(base_path)
            print(f"    ✓ {tech_dir}")
            settings_dir = create_sample_settings(base_path)
            print(f"    ✓ {settings_dir}")

        print("\n" + "=" * 60)
        print("初始化完成!")
        print("=" * 60)
        print("\n下一步:")
        print("1. 编辑 config.example.json -> config.json")
        print("2. 在 '设定/' 目录创建世界观、人物设定")
        print("3. 在 '创作技法/' 目录添加技法（或运行 sync_techniques.py）")
        print("4. 运行 sync_settings.py 同步设定到向量库")
        print("5. 如需案例库，运行 build_case_library.py")
        return

    # 无参数时显示帮助
    parser.print_help()
    print("\n示例:")
    print("  python init_novel.py --list-templates              # 列出可用模板")
    print("  python init_novel.py --name \"我的玄幻\" --template 修仙世界示例  # 创建世界配置")
    print("  python init_novel.py --name \"我的小说\" --path \"D:/小说数据\"  # 创建完整项目结构")


if __name__ == "__main__":
    main()
