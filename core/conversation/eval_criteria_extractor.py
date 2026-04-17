#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
审核维度提取器
==============

处理用户对话添加审核维度（禁止项）的功能。

核心功能：
- 模式提取（从用户提供的内容提取禁止项模式）
- 与现有禁止项对比（避免重复）
- 生成禁止项候选供用户确认
- 入库到 evaluation_criteria_v1 Collection

参考：evaluation-criteria-extension-design.md 第6节
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

# M1修复：导入FileUpdater用于向量库同步
from core.conversation.file_updater import FileUpdater


@dataclass
class ProhibitionCandidate:
    """禁止项候选"""

    name: str
    pattern: str
    examples: List[str]
    threshold: str = "出现1个即失败"
    user_input: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class EvaluationCriteriaExtractor:
    """审核维度提取器"""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = (
            Path(project_root) if project_root else self._detect_project_root()
        )
        self.pending_criteria: Optional[ProhibitionCandidate] = None
        self.existing_prohibitions: List[str] = []

    def _detect_project_root(self) -> Path:
        """自动检测项目根目录"""
        current = Path(__file__).resolve()
        markers = ["README.md", "config.example.json", "创作技法"]

        for parent in current.parents:
            if any((parent / marker).exists() for marker in markers):
                return parent
        return Path.cwd()

    def extract_prohibition(self, user_input: str) -> ProhibitionCandidate:
        """
        从用户输入提取禁止项

        Args:
            user_input: 用户原始输入，如 "我发现很多小说用'嘴角勾起一抹'这个表达，感觉很假"

        Returns:
            ProhibitionCandidate: 禁止项候选
        """
        # 1. 提取禁止项名称和示例
        name, examples = self._extract_name_and_examples(user_input)

        # 2. 生成模式
        pattern = self._generate_pattern(examples)

        # 3. 检查是否已存在
        is_duplicate = self._check_duplicate(name)

        # 4. 计算置信度
        confidence = 0.9 if len(examples) >= 3 else 0.7 if len(examples) >= 1 else 0.5

        candidate = ProhibitionCandidate(
            name=name,
            pattern=pattern,
            examples=examples,
            user_input=user_input,
            confidence=confidence,
        )

        # 保存待确认
        self.pending_criteria = candidate

        return candidate

    def discover_from_file(self, file_path: str) -> List[ProhibitionCandidate]:
        """
        从文档文件中批量发现禁止项候选

        Args:
            file_path: 文档路径

        Returns:
            禁止项候选列表
        """
        # 1. 解析路径
        full_path = self._resolve_file_path(file_path)

        if not full_path or not full_path.exists():
            print(f"[ERROR] 文件不存在: {file_path}")
            return []

        # 2. 读取文档
        content = self._read_document(full_path)

        if not content:
            return []

        print(f"[INFO] 扫描文档: {full_path.name}")

        # 3. 扫描已知"假表达"模式
        candidates = self._scan_for_fake_expressions(content)

        # 4. 统计高频可疑表达
        frequency_candidates = self._analyze_high_frequency_patterns(content)

        # 5. 合并结果
        all_candidates = candidates + frequency_candidates

        # 6. 去重
        unique = self._deduplicate_candidates(all_candidates)

        print(f"[OK] 发现 {len(unique)} 个潜在禁止项")
        return unique

    def _resolve_file_path(self, file_path: str) -> Optional[Path]:
        """解析文件路径"""
        path = Path(file_path)

        if path.exists():
            return path

        relative = self.project_root / file_path
        if relative.exists():
            return relative

        return None

    def _read_document(self, path: Path) -> str:
        """读取文档"""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="gbk")
            except:
                return ""
        except:
            return ""

    def _scan_for_fake_expressions(self, content: str) -> List[ProhibitionCandidate]:
        """
        扫描已知"假表达"模式

        Args:
            content: 文档内容

        Returns:
            发现的禁止项候选
        """
        candidates = []

        # 已知的"假表达"模式（用户常见反馈）
        fake_patterns = [
            # AI味表达
            {
                "name": "眼中闪过",
                "pattern": r"眼中闪过(一丝|一抹|一道)",
                "examples_template": ["眼中闪过一丝冷意", "眼中闪过一抹笑意"],
            },
            {
                "name": "心中涌起",
                "pattern": r"心中涌起(一股|一丝)",
                "examples_template": ["心中涌起一股暖流", "心中涌起一丝不安"],
            },
            {
                "name": "嘴角勾起",
                "pattern": r"嘴角勾起(一抹|一丝)",
                "examples_template": ["嘴角勾起一抹微笑", "嘴角勾起一丝冷笑"],
            },
            {
                "name": "不禁表达",
                "pattern": r"不禁(V+)",
                "examples_template": ["不禁感叹", "不禁流下泪水"],
            },
            # 精确数字滥用
            {
                "name": "精确年龄",
                "pattern": r"\d{1,2}岁的",
                "examples_template": ["十八岁的少年", "二十五岁的女子"],
            },
            # 抽象统计词
            {
                "name": "无数滥用",
                "pattern": r"无数",
                "examples_template": ["无数人", "无数个"],
            },
        ]

        for pattern_def in fake_patterns:
            matches = re.findall(pattern_def["pattern"], content)
            if matches:
                # 统计出现次数
                count = len(matches)
                if count >= 3:  # 出现3次以上才建议
                    candidate = ProhibitionCandidate(
                        name=pattern_def["name"],
                        pattern=pattern_def["pattern"],
                        examples=pattern_def["examples_template"],
                        threshold=f"出现≥{count}个，建议添加",
                        confidence=0.8,
                    )
                    candidates.append(candidate)

        return candidates

    def _analyze_high_frequency_patterns(
        self, content: str
    ) -> List[ProhibitionCandidate]:
        """
        分析高频可疑表达

        Args:
            content: 文档内容

        Returns:
            高频表达候选
        """
        candidates = []

        # 提取四字短语
        phrases = re.findall(r"[^，。！？\n]{4,8}[，。！？]", content)

        # 统计频率
        from collections import Counter

        phrase_counts = Counter(phrases)

        # 找出高频表达（出现5次以上）
        for phrase, count in phrase_counts.items():
            if count >= 5 and len(phrase) >= 4:
                # 检查是否是重复性表达（可能是问题表达）
                # 例如："微微一笑"出现10次
                if self._is_repetitive_expression(phrase):
                    candidate = ProhibitionCandidate(
                        name=phrase.strip("，。！？"),
                        pattern=phrase.strip("，。！？"),
                        examples=[phrase] * 3,
                        threshold=f"出现{count}次，建议检查",
                        confidence=0.5,  # 低置信度，需人工判断
                    )
                    candidates.append(candidate)

        return candidates[:10]  # 最多返回10个高频候选

    def _is_repetitive_expression(self, phrase: str) -> bool:
        """判断是否是重复性表达（可能是模板化写作）"""
        # 常见的模板化表达特征
        template_indicators = ["微微", "不禁", "淡淡", "轻轻", "猛然", "突然"]
        return any(indicator in phrase for indicator in template_indicators)

    def _deduplicate_candidates(
        self, candidates: List[ProhibitionCandidate]
    ) -> List[ProhibitionCandidate]:
        """去重"""
        seen_names = set()
        unique = []
        for c in candidates:
            if c.name not in seen_names and c.name not in self.existing_prohibitions:
                seen_names.add(c.name)
                unique.append(c)
        return unique

    def _extract_name_and_examples(self, user_input: str) -> tuple[str, List[str]]:
        """
        提取禁止项名称和示例

        Args:
            user_input: 用户输入

        Returns:
            (name, examples)
        """
        # 提取引号内容作为候选
        quoted_content = re.findall(r"'([^']+)'|\"([^']+)\"", user_input)

        examples = []
        name = ""

        if quoted_content:
            # 取第一个作为基础
            base_content = quoted_content[0][0] or quoted_content[0][1]
            name = base_content

            # 生成变体示例
            examples = self._generate_variants(base_content)

        else:
            # 提取关键词
            keywords = re.findall(r"[用使]了(.+?)这个表达", user_input)
            if keywords:
                name = keywords[0]
                examples = [name]

        if not name:
            name = "新禁止项"
            examples = ["示例待填写"]

        return name, examples

    def _generate_variants(self, base: str) -> List[str]:
        """
        生成变体示例

        Args:
            base: 基础内容

        Returns:
            变体列表
        """
        variants = [base]

        # 情感词汇替换
        emotions = ["微笑", "冷笑", "弧度", "笑意", "嘲讽", "温柔"]
        if "{emotion}" in base or any(e in base for e in emotions):
            pattern = base
            for emotion in emotions[:3]:
                variant = pattern.replace("{emotion}", emotion)
                # 或替换现有情感词
                for e in emotions:
                    if e in variant:
                        variants.append(variant.replace(e, emotion))
                        break

        return variants[:5]  # 最多5个示例

    def _generate_pattern(self, examples: List[str]) -> str:
        """
        生成匹配模式

        Args:
            examples: 示例列表

        Returns:
            正则模式
        """
        if not examples:
            return ""

        # 分析示例的共同结构
        base = examples[0]

        # 情感词汇替换为占位符
        emotions = ["微笑", "冷笑", "弧度", "笑意", "嘲讽", "温柔", "暖意", "冷意"]
        pattern = base
        for emotion in emotions:
            if emotion in pattern:
                pattern = pattern.replace(emotion, "{emotion}")
                break

        return pattern

    def _check_duplicate(self, name: str) -> bool:
        """
        检查是否已存在

        Args:
            name: 禁止项名称

        Returns:
            是否重复
        """
        # 加载现有禁止项
        self._load_existing_prohibitions()

        return name in self.existing_prohibitions

    def _load_existing_prohibitions(self) -> List[str]:
        """加载现有禁止项"""
        migrated_path = (
            self.project_root / "tools" / "evaluation_criteria_migrated.json"
        )

        if migrated_path.exists():
            with open(migrated_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.existing_prohibitions = [
                c["name"]
                for c in data.get("criteria", [])
                if c.get("dimension_type") == "prohibition"
            ]

        return self.existing_prohibitions

    def format_for_confirmation(self, candidate: ProhibitionCandidate) -> str:
        """
        格式化供用户确认

        Args:
            candidate: 禁止项候选

        Returns:
            格式化文本
        """
        duplicate_warning = ""
        if candidate.name in self.existing_prohibitions:
            duplicate_warning = "\n⚠️ 注意：此禁止项已存在，建议修改名称或取消"

        return f"""
【建议新增禁止项】
名称：{candidate.name}
模式：{candidate.pattern}
示例：
{chr(10).join(f"  - {ex}" for ex in candidate.examples)}
失败标准：{candidate.threshold}
置信度：{candidate.confidence:.0%}
{duplicate_warning}

确认入库？[是/否/修改]
"""

    def confirm_and_save(self, new_name: Optional[str] = None) -> bool:
        """
        确认并保存

        Args:
            new_name: 新名称（可选）

        Returns:
            是否成功
        """
        if not self.pending_criteria:
            return False

        candidate = self.pending_criteria

        # 更新名称
        if new_name:
            candidate.name = new_name

        # 1. 写入迁移文件
        self._append_to_migrated_file(candidate)

        # 2. 同步到向量库
        self._sync_to_vectorstore(candidate)

        # 3. 清除待确认
        self.pending_criteria = None

        return True

    def _append_to_migrated_file(self, candidate: ProhibitionCandidate) -> bool:
        """
        追加到迁移文件

        Args:
            candidate: 禁止项候选

        Returns:
            是否成功
        """
        migrated_path = (
            self.project_root / "tools" / "evaluation_criteria_migrated.json"
        )

        # 加载现有数据
        if migrated_path.exists():
            with open(migrated_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {
                "migrated_at": datetime.now().isoformat(),
                "source": "user_dialogue",
                "count": 0,
                "criteria": [],
            }

        # 确保 criteria 是列表
        if not isinstance(data.get("criteria"), list):
            data["criteria"] = []

        # 构建新条目
        new_entry = {
            "id": f"eval_prohibition_user_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "dimension_type": "prohibition",
            "dimension_name": "禁止项检测",
            "name": candidate.name,
            "pattern": candidate.pattern,
            "examples": candidate.examples,
            "threshold": candidate.threshold,
            "source": "user_dialogue",
            "created_at": candidate.created_at,
            "updated_at": datetime.now().isoformat(),
            "is_active": True,
        }

        # 添加
        data["criteria"].append(new_entry)
        data["count"] = len(data["criteria"])
        data["updated_at"] = datetime.now().isoformat()

        # 保存
        with open(migrated_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] 已添加禁止项: {candidate.name}")
        return True

    def _sync_to_vectorstore(self, candidate: ProhibitionCandidate) -> bool:
        """
        同步到向量库 (M1修复：调用FileUpdater真实同步)

        Args:
            candidate: 禁止项候选

        Returns:
            是否成功
        """
        # 构建数据结构
        data = {
            "name": candidate.name,
            "pattern": candidate.pattern,
            "examples": candidate.examples,
            "threshold": candidate.threshold,
            "type": "prohibition",
            "created_at": candidate.created_at,
        }

        # 调用FileUpdater同步到evaluation_criteria_v1 Collection
        file_updater = FileUpdater(project_root=str(self.project_root))
        result = file_updater.sync_to_vectorstore("evaluation_criteria_v1", data)

        if result:
            print(f"[OK] 已同步禁止项到向量库: {candidate.name}")
        else:
            print(f"[WARN] 禁止项同步失败，已记录日志")
            # 备用：记录到日志文件
            log_path = self.project_root / "logs" / "evaluation_criteria_sync.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "add_prohibition_failed",
                "name": candidate.name,
                "pattern": candidate.pattern,
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return result


# 测试代码
if __name__ == "__main__":
    extractor = EvaluationCriteriaExtractor()

    test_input = "我发现很多小说用'嘴角勾起一抹'这个表达，感觉很假，能不能加入禁止项？"

    print("=" * 60)
    print("审核维度提取器测试")
    print("=" * 60)

    candidate = extractor.extract_prohibition(test_input)
    print(extractor.format_for_confirmation(candidate))
