"""调试正则表达式"""
import re
from pathlib import Path

novel_path = Path('E:/小说资源/0002002.青山剑志.txt')
content = novel_path.read_text(encoding='utf-8', errors='ignore')

print('=' * 70)
print('正则表达式调试')
print('=' * 70)

# 简单模式（无边界约束）
print('\n[1] 简单模式搜索:')
for suffix in ['宗', '门', '城', '山', '国']:
    pattern = f'[\u4e00-\u9fa5]{{2,4}}{suffix}'
    matches = re.findall(pattern, content)
    print(f'  {suffix}: {len(matches)}个')
    if matches:
        print(f'    示例: {matches[:10]}')

# 提取器的原始模式（有边界约束）
print('\n[2] 提取器模式（有边界约束）:')
patterns = {
    '地点': r"(?
![，。！？\s])([\u4e00-\u9fa5]{2,4})(城|市|都|港|湾|府|岛|州|山|峰|谷|洞|宫|殿)(?![\u4e00-\u9fa5])" , '组织': r"(?
![，。！？\s])([\u4e00-\u9fa5]{2,4})(宗|门|派|会|教|社|盟|学院|团|阁|楼)(?![\u4e00-\u9fa5])" , '势力': r"(?
![，。！？\s])([\u4e00-\u9fa5]{2,4})(国|帝国|王国|邦|联盟|王朝)(?![\u4e00-\u9fa5])" , } for etype, pattern in patterns.items(): matches = list(re.finditer(pattern, content)) print(f'  {etype}: {len(matches)}匹配') if matches: for m in matches[:5]: print(f'    "{m.group(0)}"') # 尝试放宽边界约束 print('\n[3] 放宽边界约束:') for suffix in ['宗', '门', '城']: # 只要求后面不是中文 pattern_relaxed = f'[\u4e00-\u9fa5]{{2,4}}{suffix}(?![\u4e00-\u9fa5])' matches = re.findall(pattern_relaxed, content) print(f'  {suffix}: {len(matches)}个') if matches: print(f'    示例: {matches[:10]}') # 找一个实际例子分析 print('\n[4] 分析实际匹配:') # 找到"宗"字的位置 for i, char in enumerate(content): if char == '宗': context = content[max(0,i-10):i+10] print(f'  位置{i}: "...{context}..."') if i > 10: break