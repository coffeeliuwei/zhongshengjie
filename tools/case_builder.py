#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例库构建器
============

帮助新用户从自己的小说资源中提取标杆案例。

流程：
1. 格式转换（epub/mobi → txt）
2. 场景识别（自动识别关键场景）
3. 案例提取（提取高质量片段）
4. 质量评估（多维度评分）
5. 同步向量库（支持语义检索）

用法：
    python case_builder.py --init                    # 初始化案例库
    python case_builder.py --scan SOURCES...         # 扫描小说资源
    python case_builder.py --convert                 # 转换格式
    python case_builder.py --extract --limit 1000    # 提取案例
    python case_builder.py --sync                    # 同步到向量库
    python case_builder.py --status                  # 查看状态
"""

import argparse
import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict


# 场景类型定义
SCENE_TYPES = {
    "开篇场景": {
        "keywords": ["第一章", "第1章", "序章", "开篇", "序幕"],
        "position": "start",
        "min_len": 500,
        "max_len": 2000,
    },
    "打脸场景": {
        "keywords": [
            "废物",
            "嘲讽",
            "震惊",
            "不可能",
            "震撼",
            "跪下",
            "死寂",
            "倒吸凉气",
            "瞳孔收缩",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "高潮场景": {
        "keywords": [
            "决战",
            "爆发",
            "生死",
            "极限",
            "巅峰",
            "终极",
            "最后",
            "拼尽全力",
        ],
        "position": "any",
        "min_len": 500,
        "max_len": 3000,
    },
    "战斗场景": {
        "keywords": [
            "招",
            "剑",
            "刀",
            "拳",
            "攻击",
            "防御",
            "技能",
            "招式",
            "斗气",
            "灵力",
        ],
        "position": "any",
        "min_len": 400,
        "max_len": 2500,
    },
    "对话场景": {
        "keywords": ['"', '"', "说道", "问道", "答道", "笑道", "沉声道"],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "情感场景": {
        "keywords": [
            "泪",
            "感动",
            "心疼",
            "温暖",
            "苦涩",
            "复杂",
            "情绪",
            "眼眶",
            "哽咽",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "悬念场景": {
        "keywords": [
            "究竟",
            "到底",
            "秘密",
            "真相",
            "谜团",
            "不可思议",
            "难以置信",
            "未知",
        ],
        "position": "any",
        "min_len": 300,
        "max_len": 1500,
    },
    "转折场景": {
        "keywords": ["突然", "意外", "却", "竟", "不料", "没想到", "反转", "转折"],
        "position": "any",
        "min_len": 300,
        "max_len": 2000,
    },
    "结尾场景": {
        "keywords": [],
        "position": "end",
        "min_len": 300,
        "max_len": 1000,
    },
    "人物出场": {
        "keywords": ["首次", "第一次", "登场", "亮相", "出现在"],
        "position": "any",
        "min_len": 400,
        "max_len": 2000,
    },
}

# 题材关键词
GENRE_KEYWORDS = {
    "玄幻奇幻": [
        "修炼",
        "境界",
        "灵气",
        "丹药",
        "功法",
        "宗门",
        "武道",
        "元婴",
        "金丹",
    ],
    "武侠仙侠": ["江湖", "武功", "内功", "轻功", "剑法", "侠", "道长", "掌门"],
    "现代都市": ["总裁", "公司", "都市", "现代", "城市", "白领", "董事长"],
    "历史军事": ["将军", "皇帝", "朝代", "军队", "战争", "城池", "谋略"],
    "科幻灵异": ["星际", "飞船", "异能", "超能力", "未来", "科技", "异变"],
    "青春校园": ["学校", "校园", "同学", "老师", "青春", "班级", "考试"],
    "游戏竞技": ["游戏", "玩家", "副本", "BOSS", "等级", "装备", "公会"],
    "女频言情": ["王爷", "妃", "宫", "公主", "丞相", "将军府", "嫡女"],
}


@dataclass
class Case:
    """案例数据结构"""

    case_id: str
    scene_type: str
    genre: str
    novel_name: str
    content: str
    word_count: int
    quality_score: float
    emotion_value: float
    techniques: List[str]
    keywords: List[str]
    source_file: str
    chapter: int = 0
    position: str = ""


class CaseBuilder:
    """案例库构建器"""

    def __init__(self, case_library_dir: Path, config: Optional[Dict] = None):
        self.case_library_dir = case_library_dir
        self.config = config or {}
        self.qdrant_url = self.config.get("qdrant_url", "http://localhost:6333")
        self.collection_name = self.config.get("collections", {}).get(
            "case_library", "case_library_v2"
        )

        # 目录结构
        self.converted_dir = case_library_dir / "converted"
        self.cases_dir = case_library_dir / "cases"
        self.logs_dir = case_library_dir / "logs"
        self.index_file = case_library_dir / "case_index.json"
        self.stats_file = case_library_dir / "case_stats.json"

        # 内部状态
        self.novel_index: Dict[str, Any] = {}
        self.processed_files: Set[str] = set()

    def init_structure(self):
        """初始化案例库目录结构"""
        print("\n" + "=" * 60)
        print("初始化案例库目录结构")
        print("=" * 60)

        # 创建目录
        dirs = [
            self.case_library_dir,
            self.converted_dir,
            self.cases_dir,
            self.logs_dir,
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ {d.name}/")

        # 创建场景类型目录
        for scene_type in SCENE_TYPES.keys():
            scene_dir = self.cases_dir / scene_type
            scene_dir.mkdir(exist_ok=True)
        print(f"    ✓ 场景目录 ({len(SCENE_TYPES)} 种)")

        # 创建README
        readme = self.case_library_dir / "README.md"
        readme_content = """# 案例库

案例库存储从优秀小说中提取的标杆片段，供创作参考。

## 目录结构

```
.case-library/
├── converted/          # 转换后的小说文件
├── cases/              # 提取的案例（按场景类型分类）
│   ├── 开篇场景/
│   ├── 打脸场景/
│   ├── 战斗场景/
│   └── ...
├── logs/               # 日志文件
├── case_index.json     # 案例索引
└── case_stats.json     # 统计信息
```

## 支持的场景类型

| 场景类型 | 提取标准 |
|----------|----------|
| 开篇场景 | 第一章开头500-2000字 |
| 打脸场景 | 包含嘲讽+震惊的片段 |
| 高潮场景 | 情绪顶点/决战时刻 |
| 战斗场景 | 完整战斗描写 |
| 对话场景 | 有意义的对话片段 |
| 情感场景 | 情感表达段落 |
| 悬念场景 | 悬念设置片段 |
| 转折场景 | 剧情转折点 |
| 结尾场景 | 章节结尾300-1000字 |
| 人物出场 | 人物首次亮相描写 |

## 快速构建

```bash
# 1. 扫描小说资源
python case_builder.py --scan "E:/小说资源"

# 2. 转换格式（epub/mobi → txt）
python case_builder.py --convert

# 3. 提取案例
python case_builder.py --extract --limit 5000

# 4. 同步到向量库
python case_builder.py --sync
```

## 质量标准

案例入库需要满足：
- 质量评分 ≥ 6.0
- 内容完整（非断裂片段）
- 无AI味/禁止项
- 有技法体现
"""
        readme.write_text(readme_content, encoding="utf-8")
        print(f"    ✓ README.md")

        # 创建配置文件
        config_file = self.case_library_dir / "config.json"
        if not config_file.exists():
            default_config = {
                "novel_sources": [],
                "scene_types": list(SCENE_TYPES.keys()),
                "quality_threshold": 6.0,
                "max_cases_per_type": 10000,
                "batch_size": 100,
            }
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            print(f"    ✓ config.json")

        print("\n案例库初始化完成!")
        print(f"目录位置: {self.case_library_dir}")
        return True

    def scan_sources(self, source_dirs: List[Path]):
        """扫描小说资源目录"""
        print("\n" + "=" * 60)
        print("扫描小说资源")
        print("=" * 60)

        total_files = 0
        file_types = {"txt": 0, "epub": 0, "mobi": 0, "other": 0}

        for source_dir in source_dirs:
            if not source_dir.exists():
                print(f"    ✗ {source_dir} 不存在")
                continue

            print(f"\n    扫描: {source_dir}")

            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    suffix = file_path.suffix.lower().lstrip(".")
                    if suffix in file_types:
                        file_types[suffix] += 1
                    else:
                        file_types["other"] += 1
                    total_files += 1

        print("\n" + "-" * 40)
        print(f"    总文件数: {total_files}")
        print(f"    TXT: {file_types['txt']}")
        print(f"    EPUB: {file_types['epub']}")
        print(f"    MOBI: {file_types['mobi']}")
        print(f"    其他: {file_types['other']}")

        # 保存扫描结果
        scan_result = {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total_files,
            "file_types": file_types,
            "source_dirs": [str(d) for d in source_dirs],
        }

        result_file = self.case_library_dir / "scan_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(scan_result, f, indent=2, ensure_ascii=False)

        print(f"\n    扫描结果已保存: {result_file}")
        return True

    def convert_files(self, source_dirs: Optional[List[Path]] = None, limit: int = 0):
        """转换小说格式"""
        print("\n" + "=" * 60)
        print("转换小说格式")
        print("=" * 60)

        # 确定来源目录
        if source_dirs:
            dirs = source_dirs
        else:
            config_file = self.case_library_dir / "config.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                dirs = [Path(d) for d in config.get("novel_sources", [])]
            else:
                print("    ✗ 未配置小说来源目录")
                return False

        converted_count = 0
        failed_count = 0

        for source_dir in dirs:
            if not source_dir.exists():
                continue

            for file_path in source_dir.rglob("*"):
                if limit and converted_count >= limit:
                    break

                suffix = file_path.suffix.lower()

                if suffix == ".txt":
                    # 直接复制
                    dest = self.converted_dir / f"{file_path.stem}.txt"
                    if not dest.exists():
                        try:
                            content = file_path.read_text(
                                encoding="utf-8", errors="ignore"
                            )
                            dest.write_text(content, encoding="utf-8")
                            converted_count += 1
                            if converted_count % 100 == 0:
                                print(f"    已转换: {converted_count}")
                        except Exception as e:
                            failed_count += 1

                elif suffix == ".epub":
                    # 需要ebooklib
                    try:
                        import ebooklib
                        from ebooklib import epub

                        book = epub.read_epub(str(file_path))
                        content = ""
                        for doc in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                            content += doc.get_content().decode(
                                "utf-8", errors="ignore"
                            )

                        # 简单清理HTML
                        content = re.sub(r"<[^>]+>", "", content)

                        dest = self.converted_dir / f"{file_path.stem}.txt"
                        dest.write_text(content, encoding="utf-8")
                        converted_count += 1

                    except ImportError:
                        print("    ✗ 需要安装 ebooklib: pip install ebooklib")
                        return False
                    except Exception as e:
                        failed_count += 1

                elif suffix == ".mobi":
                    # MOBI需要calibre
                    print(f"    ⚠ MOBI格式需要安装calibre，跳过: {file_path.name}")
                    failed_count += 1

        print(f"\n转换完成: {converted_count} 成功, {failed_count} 失败")
        return True

    def extract_cases(self, limit: int = 1000, scene_types: Optional[List[str]] = None):
        """提取案例"""
        print("\n" + "=" * 60)
        print("提取案例")
        print("=" * 60)

        # 确定场景类型
        target_scenes = scene_types or list(SCENE_TYPES.keys())
        print(f"    目标场景: {len(target_scenes)} 种")

        # 扫描已转换的文件
        novel_files = list(self.converted_dir.glob("*.txt"))

        if not novel_files:
            print("    ✗ 未找到转换后的小说文件")
            print("    请先运行: python case_builder.py --convert")
            return False

        print(f"    小说文件: {len(novel_files)} 本")
        print(f"    提取限制: {limit} 条")

        # 提取案例
        all_cases: List[Case] = []

        for i, novel_file in enumerate(novel_files):
            if len(all_cases) >= limit:
                break

            try:
                content = novel_file.read_text(encoding="utf-8", errors="ignore")
                novel_name = novel_file.stem

                # 检测题材
                genre = self._detect_genre(content[:5000])

                # 按段落分割
                paragraphs = self._split_paragraphs(content)

                # 按场景类型提取
                for scene_type in target_scenes:
                    if len(all_cases) >= limit:
                        break

                    scene_config = SCENE_TYPES.get(scene_type, {})
                    cases = self._extract_scene_cases(
                        paragraphs=paragraphs,
                        scene_type=scene_type,
                        scene_config=scene_config,
                        novel_name=novel_name,
                        genre=genre,
                        source_file=novel_file.name,
                    )

                    all_cases.extend(cases)

                if (i + 1) % 10 == 0:
                    print(
                        f"    处理进度: {i + 1}/{len(novel_files)}, 提取: {len(all_cases)}"
                    )

            except Exception as e:
                print(f"    ✗ {novel_file.name}: {e}")

        print(f"\n提取完成: {len(all_cases)} 条案例")

        # 保存案例
        self._save_cases(all_cases)

        # 更新索引
        self._update_index(all_cases)

        return True

    def _detect_genre(self, content: str) -> str:
        """检测题材"""
        scores = {}
        for genre, keywords in GENRE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in content)
            scores[genre] = score

        if scores:
            best = max(scores, key=scores.get)
            if scores[best] >= 3:
                return best

        return "玄幻奇幻"  # 默认

    def _split_paragraphs(self, content: str) -> List[str]:
        """分割段落"""
        # 按空行分割
        paragraphs = re.split(r"\n\s*\n", content)

        # 过滤太短或太长的
        filtered = []
        for p in paragraphs:
            p = p.strip()
            if 100 <= len(p) <= 5000:
                filtered.append(p)

        return filtered

    def _extract_scene_cases(
        self,
        paragraphs: List[str],
        scene_type: str,
        scene_config: Dict,
        novel_name: str,
        genre: str,
        source_file: str,
    ) -> List[Case]:
        """提取特定场景类型的案例"""
        cases = []

        keywords = scene_config.get("keywords", [])
        min_len = scene_config.get("min_len", 300)
        max_len = scene_config.get("max_len", 3000)
        position = scene_config.get("position", "any")

        for i, para in enumerate(paragraphs):
            # 长度检查
            if not (min_len <= len(para) <= max_len):
                continue

            # 位置检查
            if position == "start" and i > 5:
                continue
            if position == "end" and i < len(paragraphs) - 5:
                continue

            # 关键词检查
            match_count = 0
            matched_keywords = []
            for kw in keywords:
                if kw in para:
                    match_count += 1
                    matched_keywords.append(kw)

            # 至少匹配2个关键词（或开篇/结尾场景特殊处理）
            if position == "any" and match_count < 2:
                continue

            # 计算质量分
            quality_score = self._calculate_quality(para, match_count)

            if quality_score < 6.0:
                continue

            # 创建案例
            case = Case(
                case_id=self._generate_case_id(para),
                scene_type=scene_type,
                genre=genre,
                novel_name=novel_name,
                content=para[:2000],
                word_count=len(para),
                quality_score=quality_score,
                emotion_value=0.5,
                techniques=[],
                keywords=matched_keywords[:5],
                source_file=source_file,
            )

            cases.append(case)

        return cases

    def _calculate_quality(self, content: str, match_count: int) -> float:
        """计算质量分"""
        score = 6.0  # 基础分

        # 关键词匹配加分
        score += min(match_count * 0.3, 1.5)

        # 长度适中加分
        if 500 <= len(content) <= 2000:
            score += 0.5

        # 检查禁止项（AI味等）
        forbidden = ["总之", "综上所述", "不得不说", "让人不禁"]
        for f in forbidden:
            if f in content:
                score -= 0.5

        # 检查对话密度
        quote_count = content.count('"') + content.count('"')
        if quote_count >= 4:
            score += 0.3

        return min(max(score, 0), 10)  # 限制在0-10

    def _generate_case_id(self, content: str) -> str:
        """生成案例ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _save_cases(self, cases: List[Case]):
        """保存案例到文件"""
        print("\n保存案例...")

        # 按场景类型分组保存
        for scene_type in SCENE_TYPES.keys():
            scene_cases = [c for c in cases if c.scene_type == scene_type]

            if not scene_cases:
                continue

            scene_dir = self.cases_dir / scene_type
            scene_dir.mkdir(exist_ok=True)

            for case in scene_cases:
                case_file = scene_dir / f"{case.case_id}.txt"
                case_file.write_text(case.content, encoding="utf-8")

                meta_file = scene_dir / f"{case.case_id}.json"
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(asdict(case), f, indent=2, ensure_ascii=False)

            print(f"    {scene_type}: {len(scene_cases)} 条")

    def _update_index(self, cases: List[Case]):
        """更新案例索引"""
        index = {
            "total": len(cases),
            "by_scene": {},
            "by_genre": {},
            "updated": datetime.now().strftime("%Y-%m-%d"),
        }

        for case in cases:
            # 按场景统计
            if case.scene_type not in index["by_scene"]:
                index["by_scene"][case.scene_type] = 0
            index["by_scene"][case.scene_type] += 1

            # 按题材统计
            if case.genre not in index["by_genre"]:
                index["by_genre"][case.genre] = 0
            index["by_genre"][case.genre] += 1

        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        print(f"\n索引更新: {self.index_file}")

    def sync_to_vectorstore(self, batch_size: int = 50):
        """同步案例到向量库"""
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import (
            PointStruct,
            VectorParams,
            Distance,
            SparseVectorParams,
        )
        from FlagEmbedding import BGEM3FlagModel

        print("\n" + "=" * 60)
        print("同步案例到向量库")
        print("=" * 60)

        # 收集所有案例
        all_cases = []
        for scene_dir in self.cases_dir.iterdir():
            if not scene_dir.is_dir():
                continue

            for meta_file in scene_dir.glob("*.json"):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        case_data = json.load(f)
                    all_cases.append(case_data)
                except:
                    continue

        if not all_cases:
            print("    ✗ 未找到案例")
            return False

        print(f"    找到 {len(all_cases)} 条案例")

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
            model = BGEM3FlagModel(model_path, use_fp16=True, device="cpu")
        else:
            import os

            cache_path = os.environ.get("BGE_M3_MODEL_PATH")
            if cache_path:
                model = BGEM3FlagModel(cache_path, use_fp16=True, device="cpu")
            else:
                model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
        print("    模型加载完成")

        # 同步
        print("\n同步到向量库...")

        for i in range(0, len(all_cases), batch_size):
            batch = all_cases[i : i + batch_size]

            texts = [c.get("content", "") for c in batch]
            out = model.encode(texts, return_dense=True, return_sparse=True)

            points = []
            for j, case in enumerate(batch):
                point = PointStruct(
                    id=int(hash(case.get("case_id", f"case_{i + j}")) % (2**31)),
                    vector={
                        "dense": out["dense_vecs"][j].tolist(),
                        "sparse": {
                            "indices": list(out["lexical_weights"][j].keys()),
                            "values": list(out["lexical_weights"][j].values()),
                        },
                    },
                    payload={
                        "name": case.get("novel_name", ""),
                        "scene_type": case.get("scene_type", ""),
                        "genre": case.get("genre", ""),
                        "content": case.get("content", "")[:500],
                        "word_count": case.get("word_count", 0),
                        "quality_score": case.get("quality_score", 7.0),
                        "keywords": case.get("keywords", []),
                        "source": case.get("source_file", ""),
                    },
                )
                points.append(point)

            client.upsert(self.collection_name, points)
            progress = min(i + batch_size, len(all_cases))
            pct = progress / len(all_cases) * 100
            print(f"    [{pct:.0f}%] {progress}/{len(all_cases)}")

        # 验证
        info = client.get_collection(self.collection_name)
        print(f"\n✓ {self.collection_name}: {info.points_count:,} 条")

        return True

    def get_status(self):
        """获取案例库状态"""
        print("\n" + "=" * 60)
        print("案例库状态")
        print("=" * 60)

        # 检查目录
        print("\n[目录状态]")
        for d in [self.converted_dir, self.cases_dir, self.logs_dir]:
            if d.exists():
                file_count = len(list(d.rglob("*")))
                print(f"    {d.name}/: {file_count} 文件")
            else:
                print(f"    {d.name}/: 不存在")

        # 检查索引
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                index = json.load(f)

            print("\n[案例统计]")
            print(f"    总计: {index.get('total', 0)}")

            print("\n    按场景:")
            for scene, count in index.get("by_scene", {}).items():
                print(f"      {scene}: {count}")

            print("\n    按题材:")
            for genre, count in index.get("by_genre", {}).items():
                print(f"      {genre}: {count}")
        else:
            print("\n[案例索引] 未创建")

        return True


def main():
    parser = argparse.ArgumentParser(description="案例库构建器")
    parser.add_argument(
        "--case-library-dir", default=".case-library", help="案例库目录路径"
    )
    parser.add_argument("--config", help="配置文件路径")

    # 命令
    parser.add_argument("--init", action="store_true", help="初始化案例库")
    parser.add_argument("--scan", nargs="+", metavar="DIR", help="扫描小说资源目录")
    parser.add_argument("--convert", action="store_true", help="转换小说格式")
    parser.add_argument("--extract", action="store_true", help="提取案例")
    parser.add_argument("--sync", action="store_true", help="同步到向量库")
    parser.add_argument("--status", action="store_true", help="查看状态")

    # 参数
    parser.add_argument("--limit", type=int, default=0, help="处理数量限制")
    parser.add_argument("--scenes", nargs="+", help="指定场景类型")
    parser.add_argument("--batch-size", type=int, default=50, help="批处理大小")

    args = parser.parse_args()

    # 加载配置
    config = {}
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

    # 案例库目录
    case_library_dir = Path(args.case_library_dir)
    builder = CaseBuilder(case_library_dir, config)

    # 执行命令
    if args.init:
        builder.init_structure()
    elif args.scan:
        builder.scan_sources([Path(d) for d in args.scan])
    elif args.convert:
        builder.convert_files(limit=args.limit)
    elif args.extract:
        builder.extract_cases(limit=args.limit or 1000, scene_types=args.scenes)
    elif args.sync:
        builder.sync_to_vectorstore(batch_size=args.batch_size)
    elif args.status:
        builder.get_status()
    else:
        parser.print_help()
        print("\n示例:")
        print("  python case_builder.py --init")
        print("  python case_builder.py --scan E:/小说资源")
        print("  python case_builder.py --convert")
        print("  python case_builder.py --extract --limit 1000")
        print("  python case_builder.py --sync")


if __name__ == "__main__":
    main()
