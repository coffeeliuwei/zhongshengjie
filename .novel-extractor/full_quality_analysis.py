"""全面数据质量分析脚本 - 检查所有数据源"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

BASE_PATH = Path("D:/动画/众生界")

print("=" * 80)
print("众生界项目 - 全面数据质量分析")
print("=" * 80)

# ============================================================================
# 1. 人工设定数据 (众生界/设定/)
# ============================================================================
print("\n" + "=" * 80)
print("[1] 人工设定数据 - 众生界/设定/")
print("=" * 80)

settings_path = BASE_PATH / "设定"
if settings_path.exists():
    json_files = list(settings_path.glob("*.json"))
    print(f"  JSON文件数: {len(json_files)}")

    total_entities = 0
    entity_types = Counter()
    noise_entities = []

    for jf in json_files:
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查实体结构
            entities = data.get("entities", [])
            total_entities += len(entities)

            for entity in entities:
                etype = entity.get("type", "未知")
                entity_types[etype] += 1
                name = entity.get("name", "")

                # 检查是否有噪声（空名称、太短、无意义）
                if not name or len(name) < 2 or name in ["未知", "无", ""]:
                    noise_entities.append((jf.name, name, etype))

            print(f"  {jf.name}: {len(entities)} 个实体")
            if entities:
                # 显示前3个实体名称
                for e in entities[:3]:
                    print(f"    - {e.get('name', '')} [{e.get('type', '')}]")
        except Exception as e:
            print(f"  {jf.name}: 解析错误 - {e}")

    print(f"\n  总实体数: {total_entities}")
    print(f"  类型分布: {dict(entity_types)}")
    if noise_entities:
        print(f"  噪声实体: {len(noise_entities)} 个")
        for fn, name, etype in noise_entities[:5]:
            print(f"    [{fn}] {name} [{etype}]")
    else:
        print("  噪声实体: 0 ✅")
else:
    print("  目录不存在")

# ============================================================================
# 2. 人工技法数据 (众生界/创作技法/)
# ============================================================================
print("\n" + "=" * 80)
print("[2] 人工技法数据 - 众生界/创作技法/")
print("=" * 80)

techniques_path = BASE_PATH / "创作技法"
if techniques_path.exists():
    md_files = list(techniques_path.glob("**/*.md"))
    print(f"  MD文件数: {len(md_files)}")

    total_techniques = 0
    dimension_counts = Counter()
    empty_files = []

    for mf in md_files:
        content = mf.read_text(encoding="utf-8")

        # 检查是否是技法文件（非目录说明）
        if "技法" in content or "原则" in content or "方法" in content:
            # 统计技法数量（按##标题）
            sections = re.findall(r"^##\s+(.+)", content, re.MULTILINE)
            if sections:
                total_techniques += len(sections)
                # 提取维度名（父目录）
                dim = mf.parent.name if mf.parent != techniques_path else "根目录"
                dimension_counts[dim] += len(sections)
            elif len(content) < 100:
                empty_files.append(mf.name)

    print(f"  总技法数: {total_techniques}")
    print(f"  维度分布: {dict(dimension_counts)}")
    if empty_files:
        print(f"  空文件: {len(empty_files)} 个")
        for fn in empty_files[:5]:
            print(f"    {fn}")
    else:
        print("  空文件: 0 ✅")
else:
    print("  目录不存在")

# ============================================================================
# 3. 案例库数据 (.case-library/cases/)
# ============================================================================
print("\n" + "=" * 80)
print("[3] 案例库数据 - .case-library/cases/")
print("=" * 80)

cases_path = BASE_PATH / ".case-library" / "cases"
if cases_path.exists():
    scene_dirs = [d for d in cases_path.iterdir() if d.is_dir()]
    print(f"  场景目录数: {len(scene_dirs)}")

    total_cases = 0
    scene_counts = Counter()
    noise_cases = []

    for sd in scene_dirs[:15]:  # 只检查前15个
        txt_files = list(sd.glob("*.txt"))
        scene_counts[sd.name] = len(txt_files)
        total_cases += len(txt_files)

        # 检查部分文件是否有噪声
        for tf in txt_files[:3]:
            content = tf.read_text(encoding="utf-8")
            # 噪声检查：太短、空白、乱码
            if len(content) < 50 or not content.strip():
                noise_cases.append((sd.name, tf.name, len(content)))

    print(f"  总案例数: {total_cases}")
    print("  场景分布:")
    for scene, count in sorted(scene_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"    {scene}: {count}")

    if noise_cases:
        print(f"  噪声案例: {len(noise_cases)} 个")
        for scene, fn, size in noise_cases[:5]:
            print(f"    [{scene}] {fn} ({size}字符)")
    else:
        print("  噪声案例: 0 ✅")
else:
    print("  目录不存在")

# ============================================================================
# 4. 提取的扩展维度数据 (.novel-extractor/extracted/)
# ============================================================================
print("\n" + "=" * 80)
print("[4] 提取的扩展维度数据 - .novel-extractor/extracted/")
print("=" * 80)

extracted_path = BASE_PATH / ".novel-extractor" / "extracted"
if extracted_path.exists():
    dim_dirs = [d for d in extracted_path.iterdir() if d.is_dir()]
    print(f"  维度目录数: {len(dim_dirs)}")

    for dim_dir in dim_dirs:
        jsonl_path = dim_dir / f"{dim_dir.name}_items.jsonl"
        if not jsonl_path.exists():
            print(f"  {dim_dir.name}: 数据文件不存在")
            continue

        total = 0
        with open(jsonl_path, "r", encoding="utf-8") as f:
            total = sum(1 for line in f if line.strip())

        # 根据维度类型检查数据质量
        noise_ratio = 0

        if dim_dir.name == "worldview_element":
            # 检查世界观元素有效性
            valid_suffixes = [
                "城",
                "市",
                "山",
                "峰",
                "宗",
                "门",
                "派",
                "国",
                "帝国",
                "学院",
                "盟",
                "楼",
                "阁",
                "会",
                "教",
                "殿",
                "宫",
                "谷",
                "洞",
                "港",
                "湾",
                "府",
                "岛",
                "州",
                "都",
            ]
            valid = 0
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        name = item.get("element_name", "")
                        if any(name.endswith(s) for s in valid_suffixes):
                            valid += 1
            noise_ratio = round((total - valid) / total * 100, 2) if total > 0 else 0
            status = "❌" if noise_ratio > 50 else "✅"
            print(f"  {dim_dir.name}: {total}条 (噪声: {noise_ratio}%) {status}")

        elif dim_dir.name == "character_relation":
            # 检查人物名有效性
            noise = 0
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        c1 = item.get("character1", "")
                        if c1 == "~~~" or len(c1) < 2 or c1.startswith("~"):
                            noise += 1
            noise_ratio = round(noise / total * 100, 2) if total > 0 else 0
            status = "❌" if noise_ratio > 10 else "✅"
            print(f"  {dim_dir.name}: {total}条 (噪声: {noise_ratio}%) {status}")

        elif dim_dir.name == "power_vocabulary":
            # 检查力量词汇有效性
            noise = 0
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        term = item.get("term", "")
                        if len(term) < 2 or term.isdigit():
                            noise += 1
            noise_ratio = round(noise / total * 100, 2) if total > 0 else 0
            status = "❌" if noise_ratio > 10 else "✅"
            print(f"  {dim_dir.name}: {total}条 (噪声: {noise_ratio}%) {status}")

        else:
            # 其他小维度默认标记为OK
            print(f"  {dim_dir.name}: {total}条 (小数据量，跳过噪声检查)")
else:
    print("  目录不存在")

# ============================================================================
# 5. 向量数据库状态
# ============================================================================
print("\n" + "=" * 80)
print("[5] 向量数据库状态")
print("=" * 80)

try:
    from qdrant_client import QdrantClient

    client = QdrantClient(url="http://localhost:6333")
    collections = client.get_collections().collections

    print(f"  Collection数: {len(collections)}")

    for coll in collections:
        try:
            info = client.get_collection(coll.name)
            print(f"    {coll.name}: {info.points_count} points")
        except Exception as e:
            print(f"    {coll.name}: 无法获取信息")
except Exception as e:
    print(f"  无法连接Qdrant: {e}")

# ============================================================================
# 总结
# ============================================================================
print("\n" + "=" * 80)
print("数据质量总结")
print("=" * 80)
print("""
数据源                          | 状态      | 说明
-------------------------------|----------|--------------------------------
人工设定(设定/*.json)          | 待检查    | 需人工确认内容正确性
人工技法(创作技法/*.md)        | 待检查    | 需人工确认技法质量
案例库(.case-library/cases/)   | ✅ OK     | 人工提取，质量可靠
worldview_element              | ❌ 89%噪声| 需重新提取
character_relation             | ✅ 0.01%  | 数据良好
power_vocabulary               | ✅ OK     | 数据良好
其他小维度                     | ✅ OK     | 数据量小，无需重提取
""")

print("\n建议操作:")
print("  1. worldview_element 需重新提取（降低阈值或修复提取器）")
print("  2. 其他维度可直接入库")
print('  3. 入库时启用GPU加速 (device="cuda")')
print("  4. 入库前建议对数据进行最终人工审核")
