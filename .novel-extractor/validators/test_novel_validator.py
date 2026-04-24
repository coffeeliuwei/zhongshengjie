#!/usr/bin/env python3
"""
测试 novel_validator.py 的脚本
"""

import sys

sys.path.insert(0, r"D:\动画\众生界\.novel-extractor")

from validators.novel_validator import NovelValidator, ValidationResult

# 创建验证器
validator = NovelValidator()

# 测试中文小说文本
test_text = """第一章 修仙问道

李云站在山巅，看着远方的云雾缭绕，心中思绪万千。
"道友，请留步！"身后传来一声呼唤。
他转身看去，只见一位身穿青袍的老者正御剑而来。
"前辈有何指教？"李云恭敬地问道。
老者微微一笑："看你骨骼惊奇，可愿拜入我门下？"

李云心中一动，这老者修为深不可测，若能拜入其门下...
"弟子愿意！"他当即跪下拜师。
"好！从今日起，你便是我青云宗弟子！"老者大笑道。

从此，李云踏上修仙之路...
"""

print("=" * 50)
print("小说验证器测试")
print("=" * 50)

# 测试综合验证
print("\n1. 测试综合验证 (validate):")
result = validator.validate(test_text)
print(f"   是否有效: {result.is_valid}")
print(f"   失败原因: {result.reason}")
print(f"   中文比例: {result.chinese_ratio:.2%}")
print(f"   特征词数: {result.feature_count}")

# 测试中文比例检测
print("\n2. 测试中文比例检测 (check_chinese_ratio):")
chinese_result = validator.check_chinese_ratio(test_text)
print(f"   通过: {chinese_result['passed']}")
print(f"   比例: {chinese_result['ratio']:.2%}")
print(f"   中文字符: {chinese_result['chinese_chars']}")
print(f"   总字符: {chinese_result['total_chars']}")

# 测试小说特征词检测
print("\n3. 测试小说特征词检测 (check_novel_features):")
features_result = validator.check_novel_features(test_text)
print(f"   通过: {features_result['passed']}")
print(f"   特征词总数: {features_result['count']}")
print(f"   不重复词数: {features_result['unique_count']}")

# 测试非小说内容
print("\n4. 测试非小说内容:")
non_novel_text = "This is a technical document about Python programming."
result2 = validator.validate(non_novel_text)
print(f"   是否有效: {result2.is_valid}")
print(f"   失败原因: {result2.reason}")

# 测试空文本
print("\n5. 测试空文本:")
result3 = validator.validate("")
print(f"   是否有效: {result3.is_valid}")
print(f"   失败原因: {result3.reason}")

print("\n" + "=" * 50)
print("测试完成!")
print("=" * 50)
