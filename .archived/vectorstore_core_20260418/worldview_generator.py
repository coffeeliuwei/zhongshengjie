#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
世界观生成器 - 从小说大纲自动生成世界观配置
============================================

解析大纲文件，提取力量体系、势力、角色、时代等元素，
自动生成世界观配置文件。

使用方式：
1. 作为Python模块：
   from worldview_generator import WorldviewGenerator
   generator = WorldviewGenerator()
   generator.generate_from_outline("总大纲.md", "我的世界")

2. 作为命令行工具：
   python worldview_generator.py --outline "总大纲.md" --name "我的世界"

3. 作为AI技能：
   在AI对话中说：根据大纲生成世界观配置
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加core目录到路径
sys.path.insert(0, str(Path(__file__).parent))


class WorldviewGenerator:
    """世界观生成器"""

    def __init__(self, project_root: Optional[Path] = None):
        """初始化

        Args:
            project_root: 项目根目录（可选，自动检测）
        """
        if project_root is None:
            try:
                from config_loader import get_project_root

                project_root = get_project_root()
            except Exception as e:
                logging.warning(f"无法获取项目根目录，使用默认路径: {e}")
                project_root = Path(__file__).parent.parent.parent

        self.project_root = Path(project_root)

        # 优先从 config_loader 获取世界观配置目录（统一路径 config/worlds/）
        try:
            from config_loader import get_world_configs_dir

            self.configs_dir = get_world_configs_dir()
        except Exception as e:
            logging.warning(f"无法从配置获取世界观目录，使用回退路径: {e}")
            self.configs_dir = self.project_root / "config" / "worlds"

        self.configs_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 大纲解析方法
    # ============================================================

    def parse_outline(self, outline_path: str) -> Dict[str, Any]:
        """解析大纲文件，提取世界观元素

        Args:
            outline_path: 大纲文件路径

        Returns:
            提取的世界观元素字典
        """
        outline_file = self.project_root / outline_path
        if not outline_file.exists():
            raise FileNotFoundError(f"大纲文件不存在: {outline_file}")

        with open(outline_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取各元素
        result = {
            "world_name": self._extract_world_name(content),
            "power_systems": self._extract_power_systems(content),
            "factions": self._extract_factions(content),
            "key_characters": self._extract_characters(content),
            "eras": self._extract_eras(content),
            "core_principles": self._extract_core_principles(content),
            "relationships": self._extract_relationships(content),
        }

        return result

    def _extract_world_name(self, content: str) -> str:
        """提取世界观名称"""
        # 尝试从标题提取
        match = re.search(r"^#\s+(.+?)(?:\n|$)", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "未命名世界"

    def _extract_power_systems(self, content: str) -> Dict[str, Any]:
        """提取力量体系"""
        power_systems = {}

        # 力量体系关键词映射
        power_keywords = {
            "修仙": {
                "source": "天地灵气",
                "cultivation": "打坐炼气",
                "combat_style": "法术、剑诀",
            },
            "魔法": {
                "source": "魔力源泉",
                "cultivation": "冥想咒语",
                "combat_style": "元素、召唤",
            },
            "神术": {
                "source": "神明赐予",
                "cultivation": "祷告信仰",
                "combat_style": "神迹、圣光",
            },
            "科技": {
                "source": "能源核心",
                "cultivation": "改造升级",
                "combat_style": "机甲、武器",
            },
            "兽力": {
                "source": "血脉觉醒",
                "cultivation": "战斗吞噬",
                "combat_style": "兽化、血脉技",
            },
            "AI力": {
                "source": "数据算力",
                "cultivation": "升级迭代",
                "combat_style": "黑客、控制",
            },
            "异能": {
                "source": "基因变异",
                "cultivation": "进化适应",
                "combat_style": "再生、变形",
            },
            "灵能": {
                "source": "宇宙能量共鸣",
                "cultivation": "精神冥想",
                "combat_style": "心灵感应、念力",
            },
            "基因改造": {
                "source": "基因序列编辑",
                "cultivation": "生物工程",
                "combat_style": "超强体质、再生",
            },
            "机械融合": {
                "source": "纳米机械植入",
                "cultivation": "技术升级",
                "combat_style": "机械臂、神经接口",
            },
        }

        # 尝试从表格提取力量体系
        table_pattern = r"\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        matches = re.findall(table_pattern, content)
        for match in matches:
            power_name = match[0].strip()
            if power_name in power_keywords:
                power_systems[power_name] = {
                    "source": match[1].strip()
                    if match[1].strip()
                    else power_keywords[power_name]["source"],
                    "cultivation": match[2].strip()
                    if match[2].strip()
                    else power_keywords[power_name]["cultivation"],
                    "combat_style": match[3].strip()
                    if match[3].strip()
                    else power_keywords[power_name]["combat_style"],
                    "costs": ["待补充"],
                    "subtypes": {},
                }
            else:
                power_systems[power_name] = {
                    "source": match[1].strip(),
                    "cultivation": match[2].strip(),
                    "combat_style": match[3].strip(),
                    "costs": ["待补充"],
                    "subtypes": {},
                }

        # 如果表格提取失败，尝试关键词匹配
        if not power_systems:
            for keyword, defaults in power_keywords.items():
                if keyword in content:
                    power_systems[keyword] = {
                        "source": defaults["source"],
                        "cultivation": defaults["cultivation"],
                        "combat_style": defaults["combat_style"],
                        "costs": ["待补充"],
                        "subtypes": {},
                    }

        return power_systems

    def _extract_factions(self, content: str) -> Dict[str, Any]:
        """提取势力"""
        factions = {}

        # 尝试从势力相关章节提取
        faction_patterns = [
            r"###\s*(.+?)\n([\s\S]*?)(?=###|$)",
            r"\*\*(.+?)\*\*\n-?\s*\*\*政体\*\*[：:]\s*(.+?)(?:\n|$)",
            r"\*\*(.+?)\*\*\n-?\s*\*\*核心利益\*\*[：:]\s*(.+?)(?:\n|$)",
        ]

        # 匹配势力名称和描述
        faction_block_pattern = r"###\s*(.+?)\n([\s\S]*?)(?=\n###|\n##|$)"
        matches = re.findall(faction_block_pattern, content)

        for match in matches:
            faction_name = match[0].strip()
            faction_content = match[1]

            # 跳过非势力标题
            skip_keywords = [
                "时代",
                "力量",
                "感情",
                "主题",
                "原则",
                "角色",
                "设定",
                "概况",
            ]
            if any(kw in faction_name for kw in skip_keywords):
                continue

            # 提取政体
            structure = "待补充"
            structure_match = re.search(
                r"\*\*政体\*\*[：:]\s*(.+?)(?:\n|$)", faction_content
            )
            if structure_match:
                structure = structure_match.group(1).strip()

            # 提取核心利益
            core_interest = "待补充"
            interest_match = re.search(
                r"\*\*核心利益\*\*[：:]\s*(.+?)(?:\n|$)", faction_content
            )
            if interest_match:
                core_interest = interest_match.group(1).strip()

            # 提取特色
            feature = "待补充"
            feature_match = re.search(
                r"\*\*特色\*\*[：:]\s*(.+?)(?:\n|$)", faction_content
            )
            if feature_match:
                feature = feature_match.group(1).strip()

            if faction_name and faction_name not in factions:
                factions[faction_name] = {
                    "structure": structure,
                    "political": [],
                    "economy": [core_interest],
                    "culture": [],
                    "architecture": feature,
                }

        # 备用模式：匹配势力表格
        if not factions:
            faction_patterns = [
                r"势力[：:]\s*(.+?)(?:\n|$)",
                r"宗门[：:]\s*(.+?)(?:\n|$)",
                r"组织[：:]\s*(.+?)(?:\n|$)",
                r"阵营[：:]\s*(.+?)(?:\n|$)",
            ]

            for pattern in faction_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    faction_name = match.strip()
                    if faction_name and faction_name not in factions:
                        factions[faction_name] = {
                            "structure": "待补充",
                            "culture": [],
                            "architecture": "待补充",
                        }

        return factions

    def _extract_characters(self, content: str) -> Dict[str, Any]:
        """提取角色"""
        characters = {}

        # 匹配角色表格
        table_pattern = r"\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|"
        matches = re.findall(table_pattern, content)

        for match in matches:
            char_name = match[0].strip()
            # 跳过表头
            if char_name in ["角色", "角色1", "势力", "能力", "性格", "动机"]:
                continue

            faction = match[1].strip() if len(match) > 1 else "待补充"
            power = match[2].strip() if len(match) > 2 else "待补充"

            if char_name and len(char_name) < 20:
                characters[char_name] = {
                    "faction": faction,
                    "power": power,
                    "subtype": "待补充",
                    "abilities": [],
                }

        # 备用模式：匹配角色章节
        if not characters:
            patterns = [
                r"【(.+?)】",
                r"角色[：:]\s*(.+?)(?:\n|$)",
                r"主角[：:]\s*(.+?)(?:\n|$)",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    char_name = match.strip()
                    if char_name and len(char_name) < 20:
                        characters[char_name] = {
                            "faction": "待补充",
                            "power": "待补充",
                            "abilities": [],
                        }

        return characters

    def _extract_eras(self, content: str) -> Dict[str, Any]:
        """提取时代"""
        eras = {}

        # 匹配时代章节
        era_block_pattern = (
            r"###\s*(.+?时代|.+(?:纪元|时期|年代))\n([\s\S]*?)(?=\n###|\n##|$)"
        )
        matches = re.findall(era_block_pattern, content)

        for match in matches:
            era_name = match[0].strip()
            era_content = match[1]

            # 提取氛围
            mood = "待补充"
            mood_match = re.search(r"氛围[：:]\s*(.+?)(?:\n|$)", era_content)
            if mood_match:
                mood = mood_match.group(1).strip()

            if era_name and len(era_name) < 30:
                eras[era_name] = {
                    "mood": mood,
                    "color": "待补充",
                    "symbols": "待补充",
                }

        # 备用模式：匹配时代关键词
        if not eras:
            era_keywords = ["时代", "纪元", "时期", "年代"]

            for keyword in era_keywords:
                pattern = rf"###?\s*(.+?{keyword})"
                matches = re.findall(pattern, content)
                for match in matches:
                    era_name = match.strip()
                    if era_name and len(era_name) < 30:
                        eras[era_name] = {
                            "mood": "待补充",
                            "color": "待补充",
                            "symbols": "待补充",
                        }

        return eras

    def _extract_core_principles(self, content: str) -> Dict[str, Any]:
        """提取核心原则"""
        principles = {
            "moral_view": "待补充",
            "core_theme": "待补充",
            "romance_rule": "待补充",
        }

        # 尝试从主题相关内容提取
        theme_patterns = [
            r"主题[：:]\s*(.+?)(?:\n|$)",
            r"核心[：:]\s*(.+?)(?:\n|$)",
            r"主题思想[：:]\s*(.+?)(?:\n|$)",
        ]

        for pattern in theme_patterns:
            match = re.search(pattern, content)
            if match:
                principles["core_theme"] = match.group(1).strip()
                break

        return principles

    def _extract_relationships(self, content: str) -> Dict[str, Any]:
        """提取关系网络"""
        return {"love": [], "enemy": []}

    # ============================================================
    # 配置生成方法
    # ============================================================

    def generate_config(
        self, extracted: Dict[str, Any], world_name: str = None
    ) -> Dict[str, Any]:
        """生成世界观配置

        Args:
            extracted: 提取的世界观元素
            world_name: 世界观名称（可选）

        Returns:
            完整的世界观配置
        """
        if world_name is None:
            world_name = extracted.get("world_name", "未命名世界")

        config = {
            "world_name": world_name,
            "world_type": "auto-generated",
            "description": f"自动从大纲生成的世界观配置 - {datetime.now().strftime('%Y-%m-%d')}",
            "power_systems": extracted.get("power_systems", {}),
            "factions": extracted.get("factions", {}),
            "key_characters": extracted.get("key_characters", {}),
            "eras": extracted.get("eras", {}),
            "core_principles": extracted.get("core_principles", {}),
            "relationships": extracted.get("relationships", {}),
            "technique_mappings": {
                "战斗": {"power_specific": {}},
                "意境": {"era_specific": {}},
                "人物": {"faction_specific": {}},
            },
        }

        return config

    def save_config(self, config: Dict[str, Any], world_name: str) -> Path:
        """保存世界观配置

        Args:
            config: 世界观配置
            world_name: 世界观名称

        Returns:
            保存的文件路径
        """
        config_file = self.configs_dir / f"{world_name}.json"

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return config_file

    def generate_from_outline(
        self, outline_path: str, world_name: str = None, save: bool = True
    ) -> Dict[str, Any]:
        """从大纲生成世界观配置

        Args:
            outline_path: 大纲文件路径
            world_name: 世界观名称（可选，默认从大纲提取）
            save: 是否保存到文件

        Returns:
            生成的配置和保存路径
        """
        # 解析大纲
        extracted = self.parse_outline(outline_path)

        # 生成配置
        config = self.generate_config(extracted, world_name)

        result = {"config": config, "saved": False, "file_path": None}

        # 保存配置
        if save:
            file_path = self.save_config(config, config["world_name"])
            result["saved"] = True
            result["file_path"] = str(file_path)

        return result

    # ============================================================
    # AI辅助生成方法
    # ============================================================

    def generate_with_ai_prompt(self, outline_content: str) -> str:
        """生成AI提示词，让AI帮助完善世界观

        Args:
            outline_content: 大纲内容

        Returns:
            AI提示词
        """
        prompt = f"""请根据以下小说大纲，生成完整的世界观配置。

大纲内容：
```
{outline_content[:5000]}  # 限制长度
```

请按照以下JSON格式输出世界观配置：

```json
{{
  "world_name": "世界观名称",
  "world_type": "世界观类型（如：xianxia/fantasy/scifi/multi-power-fantasy）",
  "description": "世界观描述",
  "power_systems": {{
    "力量体系名称": {{
      "source": "力量来源",
      "cultivation": "修炼方式",
      "combat_style": "战斗风格",
      "costs": ["代价1", "代价2"],
      "subtypes": {{
        "子类型": {{
          "abilities": ["能力1", "能力2"],
          "cost": "代价描述"
        }}
      }}
    }}
  }},
  "factions": {{
    "势力名称": {{
      "structure": "组织结构",
      "political": ["政治层级"],
      "economy": ["经济来源"],
      "culture": ["文化特征"],
      "architecture": "建筑风格"
    }}
  }},
  "key_characters": {{
    "角色名": {{
      "faction": "所属势力",
      "power": "力量体系",
      "subtype": "子类型",
      "abilities": ["能力1", "能力2"]
    }}
  }},
  "eras": {{
    "时代名": {{
      "mood": "氛围",
      "color": "色调",
      "symbols": "象征"
    }}
  }},
  "core_principles": {{
    "moral_view": "道德观",
    "core_theme": "核心主题",
    "romance_rule": "感情线原则"
  }},
  "relationships": {{
    "love": [{{"from": "角色A", "to": "角色B", "conflict": "冲突", "ending": "结局"}}],
    "enemy": [{{"from": "势力A", "to": "势力B", "nature": "敌对原因"}}]
  }}
}}
```

请确保：
1. 所有力量体系都有明确的代价
2. 势力有独特的文化和建筑风格
3. 角色能力与力量体系匹配
4. 核心原则贯穿整个世界观
"""
        return prompt


# ============================================================
# 命令行接口
# ============================================================


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="世界观生成器")
    parser.add_argument("--outline", "-o", help="大纲文件路径")
    parser.add_argument("--name", "-n", help="世界观名称")
    parser.add_argument("--list", "-l", action="store_true", help="列出已有世界观")
    parser.add_argument("--ai-prompt", "-a", action="store_true", help="生成AI提示词")

    args = parser.parse_args()

    generator = WorldviewGenerator()

    if args.list:
        # 列出已有世界观
        print("=" * 60)
        print("已有世界观配置")
        print("=" * 60)
        for config_file in generator.configs_dir.glob("*.json"):
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            print(f"\n- {config_file.stem}")
            print(f"  类型: {config.get('world_type', 'unknown')}")
            print(f"  力量体系: {len(config.get('power_systems', {}))}个")
            print(f"  势力: {len(config.get('factions', {}))}个")
            print(f"  角色: {len(config.get('key_characters', {}))}个")
        return

    if not args.outline:
        print("请使用 --outline 指定大纲文件路径")
        print("示例: python worldview_generator.py --outline 总大纲.md --name 我的世界")
        return

    if args.ai_prompt:
        # 生成AI提示词
        outline_file = generator.project_root / args.outline
        if outline_file.exists():
            with open(outline_file, "r", encoding="utf-8") as f:
                content = f.read()
            prompt = generator.generate_with_ai_prompt(content)
            print(prompt)
        else:
            print(f"大纲文件不存在: {outline_file}")
        return

    # 生成世界观配置
    result = generator.generate_from_outline(args.outline, args.name)

    print("=" * 60)
    print("世界观配置生成完成")
    print("=" * 60)
    print(f"世界名称: {result['config']['world_name']}")
    print(f"力量体系: {len(result['config']['power_systems'])}个")
    print(f"势力: {len(result['config']['factions'])}个")
    print(f"角色: {len(result['config']['key_characters'])}个")
    print(f"时代: {len(result['config']['eras'])}个")

    if result["saved"]:
        print(f"\n已保存到: {result['file_path']}")
    else:
        print("\n未保存到文件")


if __name__ == "__main__":
    main()
