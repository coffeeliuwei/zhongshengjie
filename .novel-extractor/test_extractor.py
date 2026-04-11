"""测试提取器"""

from pathlib import Path
import re
import sys

sys.path.insert(0, "extractors")
from worldview_element_extractor import WorldviewElementExtractor

ext = WorldviewElementExtractor()

novels_dir = Path("E:/小说资源")
all_txt = list(novels_dir.glob("**/*.txt"))

# 找含中文且有元素的文件
test_file = None
for novel_path in all_txt[:20]:
    content = novel_path.read_text(encoding="utf-8", errors="ignore")
    chinese_chars = len(re.findall(r"[\u4e00-\u9fa5]", content))
    if chinese_chars > 100:
        has_element = any(
            suffix in content for suffix in ["城", "山", "宗", "门", "国"]
        )
        if has_element:
            test_file = novel_path
            break

if test_file:
    print(f"测试文件: {test_file.name}")
    content = test_file.read_text(encoding="utf-8", errors="ignore")
    print(f"大小: {len(content)}字符")

    # 测试正则匹配
    print("\n正则匹配结果:")
    for etype, patterns in ext.ELEMENT_PATTERNS.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, content))
            print(f"{etype}: {len(matches)}匹配")
            for m in matches[:10]:
                print(f'  "{m.group(0)}"')

    # 测试完整提取
    results = ext.extract_from_novel(content, "test", test_file)
    print(f"\nextract_from_novel: {len(results)}条")
    if results:
        for r in results[:15]:
            print(f"  {r['element_name']} [{r['element_type']}] freq={r['frequency']}")
else:
    print("未找到含元素的测试文件")
