"""调试提取器"""

import sys
import json
import re
from pathlib import Path

sys.path.insert(0, "extractors")
from worldview_element_extractor import WorldviewElementExtractor

ext = WorldviewElementExtractor()

# 测试一个小说文件
novels_dir = Path("E:/小说资源")
novel_files = list(novels_dir.glob("*.txt"))[:1]

if novel_files:
    novel_path = novel_files[0]
    print(f"测试文件: {novel_path.name}")

    content = novel_path.read_text(encoding="utf-8", errors="ignore")
    print(f"文件大小: {len(content)}字符")

    # 直接调用extract_from_novel
    results = ext.extract_from_novel(content, "test", novel_path)
    print(f"extract_from_novel结果: {len(results)}条")

    if results:
        for r in results[:20]:
            name = r.get("element_name", "")
            etype = r.get("element_type", "")
            freq = r.get("frequency", 0)
            print(f"  {name} [{etype}] freq={freq}")
    else:
        # 手动测试正则匹配
        print()
        print("手动测试正则:")
        for etype, patterns in ext.ELEMENT_PATTERNS.items():
            for pattern in patterns:
                matches = list(re.finditer(pattern, content))
                print(f"  {etype}: {len(matches)}匹配")
                if matches:
                    for m in matches[:10]:
                        full = m.group(0)
                        base = m.group(1)
                        suffix = m.group(2) if len(m.groups()) > 1 else ""
                        print(f'    "{full}" -> base="{base}" suffix="{suffix}"')
                        # 检查是否被排除
                        if full in ext.EXCLUDED_WORDS:
                            print(f"      [EXCLUDED] 在排除词列表")
                        if any(full.startswith(p) for p in ext.EXCLUDED_PREFIXES):
                            print(f"      [EXCLUDED] 以排除前缀开头")
else:
    print("小说目录不存在或无文件")
