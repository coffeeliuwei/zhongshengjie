# 链路 D · 失败记录

**失败时间**：2026-04-18 14:39 (UTC+8)

**失败类型**：ImportError - get_project_root() 抛异常

**完整 Trace**：
```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\动画\众生界\core\__main__.py", line 9, in <module>
    main()
  File "D:\动画\众生界\core\cli.py", line 508, in <module>
    sys.exit(cli.run())
  File "D:\动画\众生界\core\cli.py", line 126, in <module>
    return handler(parsed)
  File "D:\动画\众生界\core\cli.py", line 163, in <module>
    kb = KnowledgeBase()
  File "D:\动画\众生界\modules\knowledge_base\__init__.py", line 97, in __init__
    self.sync_manager = SyncManager(use_docker=use_docker)
  File "D:\动画\众生界\modules\knowledge_base\sync_manager.py", line 141, in __init__
    self.project_dir = project_dir or get_project_root()
  File "D:\动画\众生界\modules\knowledge_base\sync_manager.py", line 43, in <module>
    raise ImportError
ImportError
```

**分析**：
1. `core/cli.py` 运行 `python -m core kb --stats`
2. `KnowledgeBase.__init__` 调用 `SyncManager`
3. `SyncManager.__init__` 调用 `get_project_root()`
4. `get_project_root()` 抛 ImportError

**按 §6 失败回退矩阵**：
- 此失败不在表格预设场景中（非 Qdrant 连接问题、非 collection 名不匹配）
- 属于 `sync_manager.py` 内部函数 `get_project_root()` 的问题
- 建议：开 N1 调查任务，不简单回退到某个 M

**替代验证方案**：
直接用 Qdrant API 检查 collection 状态（已在前/后快照中完成）：
- novel_settings_v2: 160 (不变)
- writing_techniques_v2: 986 (不变)
- case_library_v2: 387377 (不变)

**结论**：
- 链路 D CLI 入口失败 ❌
- 但 Qdrant 三集合数据验证通过 ✅（通过快照采集）
- 数据一致性确认：三集合 count 前后不变