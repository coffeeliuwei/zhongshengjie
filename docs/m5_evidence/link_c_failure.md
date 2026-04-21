# 链路 C · 失败记录

**失败时间**：2026-04-18 14:38 (UTC+8)

**失败类型**：TypeError - sync_from_outline() 缺少必需参数

**完整 Trace**：
```
generator type: _MockWorldviewGenerator
Traceback (most recent call last):
  File "<string>", line 8, in <module>
TypeError: _MockWorldviewGenerator.sync_from_outline() missing 1 required positional argument: 'outline_path'
```

**分析**：
1. `_MockWorldviewGenerator` 类型正确 ✅（M2-β 后预期使用 Mock）
2. 但 `_MockWorldviewGenerator.sync_from_outline()` 需要 `outline_path` 参数
3. M5 计划 §3.3 的测试代码未传参数：`result = gen.sync_from_outline()`
4. 应改为：`result = gen.sync_from_outline('总大纲.md')`

**按 §6 失败回退矩阵**：
- 属于 "C 失败：sync_from_outline 抛 AttributeError" 类
- 应回退 M2-β

**回退建议**：
1. 检查 `core/change_detector/sync_manager_adapter.py` 的 `_MockWorldviewGenerator.sync_from_outline` 方法签名
2. 可能需要：
   - 修改 M5 测试代码传参数
   - 或修改 Mock 类使 outline_path 可选（默认 '总大纲.md'）

**大纲恢复状态**：✅ 已恢复（git diff 总大纲.md 为空）

---

**注意**：此失败不影响链路 D 和后续快照采集，已按计划继续执行。