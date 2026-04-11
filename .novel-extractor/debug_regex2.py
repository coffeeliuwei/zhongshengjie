"""调试正则表达式"""

import re
from pathlib import Path

novel_path = Path(
    "D:/动画/众生界/.case-library/converted/08福尔摩斯探案全集.txt"
)  # 使用已转换文件

if novel_path.exists():
    content = novel_path.read_text(encoding="utf-8", errors="ignore")
    print(f"文件: {novel_path.name}")
    print(f"大小: {len(content)}字符")

    print("\n[1] 简单模式搜索（无边界约束）:")
    for suffix in ["宗", "门", "城", "山", "国", "殿", "宫", "谷"]:
        pattern = f"[\\u4e00-\\u9fa5]{{2,4}}{suffix}"
        matches = re.findall(pattern, content)
        if matches:
            print(f"  {suffix}: {len(matches)}个")
            print(f"    示例: {matches[:8]}")

    print("\n[2] 测试提取器模式:")
    # 简化版正则（去掉复杂的边界约束）
    for suffix in ["宗", "门", "城"]:
        # 只检查后缀后面不是中文
        pattern = f"[\\u4e00-\\u9fa5]{{2,4}}{suffix}(?![\\u4e00-\\u9fa5])"
        matches = re.findall(pattern, content)
        print(f"  {suffix}: {len(matches)}个")
        if matches:
            print(f"    示例: {matches[:8]}")
else:
    print("文件不存在")
