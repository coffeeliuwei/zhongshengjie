"""章节大纲解析器

将 Markdown 格式的大纲文件解析为结构化数据，供创作工作流注入上下文使用。

支持格式（基于实际大纲文件如 第一章-天裂大纲.md）：
  # 《众生界》第N章：标题
  ## 章节信息（表格：| 项目 | 内容 |）
  ## 核心逻辑
    ### 关键设定（表格）
  ## 详细场景设计
    ### 场景X：场景名（引用块内容）
  ## 写作要点（表格）
  ## 章节结构（表格）
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional


class ChapterOutlineParser:
    """章节大纲 Markdown 解析器"""

    # 数字 → 汉字 映射（支持 1-20 章）
    _NUM_TO_CHINESE = {
        1: "一",
        2: "二",
        3: "三",
        4: "四",
        5: "五",
        6: "六",
        7: "七",
        8: "八",
        9: "九",
        10: "十",
        11: "十一",
        12: "十二",
        13: "十三",
        14: "十四",
        15: "十五",
        16: "十六",
        17: "十七",
        18: "十八",
        19: "十九",
        20: "二十",
    }

    def parse(self, content: str) -> Dict[str, Any]:
        """解析大纲文本

        Args:
            content: 大纲 Markdown 文本

        Returns:
            结构化大纲 dict，包含：
              - chapter_title: str
              - chapter_info: dict（章节名、视角、身份、核心情感等）
              - key_settings: dict（关键设定）
              - scenes: List[dict]（详细场景设计）
              - writing_notes: dict（写作要点）
              - chapter_structure: List[dict]（章节结构）
              - summary: str（所有场景的简要摘要，用于注入上下文）
        """
        result = {
            "chapter_title": "",
            "chapter_info": {},
            "key_settings": {},
            "scenes": [],
            "writing_notes": {},
            "chapter_structure": [],
            "summary": "",
        }

        lines = content.splitlines()

        # 提取章节标题
        for line in lines:
            if line.startswith("# "):
                result["chapter_title"] = line[2:].strip()
                break

        # 解析章节信息表格
        result["chapter_info"] = self._parse_table(content, "章节信息")

        # 解析关键设定表格
        result["key_settings"] = self._parse_table(content, "关键设定")

        # 解析写作要点表格
        result["writing_notes"] = self._parse_table(content, "写作要点")

        # 解析章节结构表格
        result["chapter_structure"] = self._parse_structure_table(content)

        # 解析详细场景设计
        result["scenes"] = self._parse_scenes(content)

        # 生成摘要
        result["summary"] = self._build_summary(result)

        return result

    def parse_file(self, file_path) -> Optional[Dict[str, Any]]:
        """从文件解析大纲

        Args:
            file_path: Path 或 str，大纲文件路径

        Returns:
            结构化大纲 dict，文件不存在返回 None
        """
        path = Path(file_path)
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        return self.parse(content)

    def find_outline_file(self, chapter_num: int, outline_dir) -> Optional[Path]:
        """在大纲目录中查找指定章节的大纲文件

        支持的文件名格式：
          - 第一章大纲.md
          - 第一章-天裂大纲.md
          - 第1章大纲.md
          - 第1章-天裂大纲.md

        Args:
            chapter_num: 章节序号（整数，从 1 开始）
            outline_dir: 大纲目录路径

        Returns:
            找到的文件 Path，未找到返回 None
        """
        outline_dir = Path(outline_dir)
        if not outline_dir.exists():
            return None

        chinese = self._NUM_TO_CHINESE.get(chapter_num, str(chapter_num))

        # 按优先级匹配：汉字章序优先，阿拉伯数字次之
        patterns = [
            f"第{chinese}章*大纲.md",  # 第一章大纲.md / 第一章-天裂大纲.md
            f"第{chinese}章-*.md",  # 第一章-天裂.md / 第一章-天裂-优化版.md
            f"第{chinese}章*.md",  # 第一章.md（宽松匹配）
            f"第{chapter_num}章*大纲.md",  # 第1章大纲.md
            f"第{chapter_num}章-*.md",  # 第1章-天裂.md
            f"第{chapter_num}章*.md",  # 第1章-任意内容.md
        ]

        for pattern in patterns:
            matches = list(outline_dir.glob(pattern))
            if matches:
                # N3修复：返回最新修改的文件，而非第一个匹配
                return max(matches, key=lambda p: p.stat().st_mtime)

        return None

    def _parse_table(self, content: str, section_name: str) -> Dict[str, str]:
        """解析 Markdown 表格为字典

        Args:
            content: Markdown 内容
            section_name: 表格所在章节名（如 "章节信息" 或 "关键设定"）

        Returns:
            {列1值: 列2值} 格式的字典
        """
        result = {}

        # 尝试匹配二级标题（## 章节名）或三级标题（### 章节名）
        section_pattern = re.compile(rf"^(##|###)\s+{section_name}\s*$", re.MULTILINE)
        section_match = section_pattern.search(content)
        if not section_match:
            return result

        start = section_match.end()
        header_level = section_match.group(1)  # ## 或 ###

        # 提取表格内容（直到下一个同级或更高级标题）
        # 三级标题后遇到二级标题要停止，二级标题后遇到三级标题继续
        if header_level == "###":
            # 三级标题：遇到 ## 或 ### 都停止
            end_pattern = re.compile(r"^(##|###)\s+", re.MULTILINE)
        else:
            # 二级标题：只遇到 ## 停止（### 是子章节）
            end_pattern = re.compile(r"^##\s+", re.MULTILINE)

        end_match = end_pattern.search(content[start:])
        if end_match:
            table_content = content[start : start + end_match.start()]
        else:
            table_content = content[start:]

        # 解析表格行
        # 格式：| 项目 | 内容 |
        for line in table_content.splitlines():
            line = line.strip()
            if not line or line.startswith("|--") or line.startswith("|-"):
                continue
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                # 去除空元素
                parts = [p for p in parts if p]
                if len(parts) >= 2:
                    key = parts[0]
                    value = parts[1]
                    # 去除 ** 包裹
                    key = re.sub(r"\*\*(.+?)\*\*", r"\1", key)
                    result[key] = value

        return result

    def _parse_structure_table(self, content: str) -> List[Dict[str, str]]:
        """解析章节结构表格为列表

        Returns:
            [{阶段: ..., 内容: ..., 时间线: ...}] 格式的列表
        """
        result = []

        # 定位章节结构表格
        section_match = re.search(r"^##\s+章节结构\s*$", content, re.MULTILINE)
        if not section_match:
            return result

        start = section_match.end()
        end_match = re.search(r"^##\s+", content[start:])
        if end_match:
            table_content = content[start : start + end_match.start()]
        else:
            table_content = content[start:]

        # 解析表格行
        headers = []
        for line in table_content.splitlines():
            line = line.strip()
            if not line or line.startswith("|--") or line.startswith("|-"):
                continue
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                parts = [p for p in parts if p]

                if not headers:
                    # 第一行是表头
                    headers = [re.sub(r"\*\*(.+?)\*\*", r"\1", p) for p in parts]
                elif len(parts) >= 1:
                    # 数据行
                    row = {}
                    for i, h in enumerate(headers):
                        if i < len(parts):
                            val = parts[i]
                            val = re.sub(r"\*\*(.+?)\*\*", r"\1", val)
                            row[h] = val
                    if row:
                        result.append(row)

        return result

    def _parse_scenes(self, content: str) -> List[Dict[str, Any]]:
        """解析详细场景设计

        Returns:
            [{title: ..., content: ...}] 格式的列表
        """
        scenes = []

        # 定位详细场景设计章节
        section_match = re.search(r"^##\s+详细场景设计\s*$", content, re.MULTILINE)
        if not section_match:
            return scenes

        start = section_match.end()
        end_match = re.search(r"^##\s+", content[start:])
        if end_match:
            scene_content = content[start : start + end_match.start()]
        else:
            scene_content = content[start:]

        # 按 ### 场景分割
        scene_pattern = re.compile(r"^###\s+(.+)$", re.MULTILINE)
        parts = scene_pattern.split(scene_content)

        # split 结果：[序幕文本, 标题1, 内容1, 标题2, 内容2, ...]
        i = 1  # 跳过序幕
        while i + 1 < len(parts):
            title = parts[i].strip()
            body = parts[i + 1]
            scenes.append(self._parse_scene(title, body))
            i += 2

        return scenes

    def _parse_scene(self, title: str, body: str) -> Dict[str, Any]:
        """解析单个场景"""
        scene = {
            "title": title,
            "content": "",
        }

        # 提取引用块内容（> 开头的行）
        quote_lines = []
        in_quote = False
        for line in body.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith(">"):
                in_quote = True
                # 提取引用内容（去除 > 前缀）
                quote_text = line_stripped[1:].strip()
                if quote_text:
                    quote_lines.append(quote_text)
            elif in_quote and not line_stripped:
                # 引用块内的空行保留
                quote_lines.append("")
            elif in_quote and line_stripped:
                # 引用块结束或继续
                if not line_stripped.startswith(">"):
                    # 非引用内容，结束当前引用块
                    break

        # 合并引用内容
        scene["content"] = "\n".join(quote_lines).strip()

        return scene

    def _build_summary(self, result: Dict[str, Any]) -> str:
        """生成适合注入 AI 上下文的大纲摘要"""
        parts = []

        # 章节标题
        if result["chapter_title"]:
            parts.append(f"【{result['chapter_title']}】")

        # 章节信息
        info = result.get("chapter_info", {})
        if info:
            parts.append("\n章节信息：")
            if info.get("章节名"):
                parts.append(f"  章节名：{info['章节名']}")
            if info.get("视角"):
                parts.append(f"  视角：{info['视角']}")
            if info.get("核心情感"):
                parts.append(f"  核心情感：{info['核心情感']}")

        # 关键设定
        settings = result.get("key_settings", {})
        if settings:
            parts.append("\n关键设定：")
            for k, v in list(settings.items())[:5]:  # 最多5条
                parts.append(f"  {k}：{v}")

        # 场景设计
        scenes = result.get("scenes", [])
        if scenes:
            parts.append(f"\n场景设计（共{len(scenes)}个）：")
            for i, scene in enumerate(scenes, 1):
                scene_text = f"  场景{i}「{scene['title']}」"
                if scene.get("content"):
                    # 截取前100字符作为摘要
                    content_preview = scene["content"][:100]
                    if len(scene["content"]) > 100:
                        content_preview += "..."
                    scene_text += f"：{content_preview}"
                parts.append(scene_text)

        # 写作要点
        notes = result.get("writing_notes", {})
        if notes:
            parts.append("\n写作要点：")
            for k, v in list(notes.items())[:3]:  # 最多3条
                parts.append(f"  {k}：{v}")

        # 章节结构
        structure = result.get("chapter_structure", [])
        if structure:
            parts.append("\n章节结构：")
            for item in structure[:5]:  # 最多5条
                stage = item.get("阶段", "")
                content = item.get("内容", "")
                timeline = item.get("时间线", "")
                if stage:
                    parts.append(f"  {stage}：{content}（{timeline}）")

        return "\n".join(parts)
