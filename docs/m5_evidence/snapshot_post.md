# M5 端到端验证 · 后快照

**时间**：2026-04-18 14:39:00 (UTC+8)
**git HEAD**：8365fe21ae9bf8200446c5f87cba08cbb188ec59

## Qdrant 三集合 point count

| Collection | Post-count | Pre-count | Diff |
|---|---|---|---|
| novel_settings_v2 | 160 | 160 | 0 (不变 ✅) |
| writing_techniques_v2 | 986 | 986 | 0 (不变 ✅) |
| case_library_v2 | 387377 | 387377 | 0 (不变 ✅) |

## 关键文件 mtime + sha256（前 8 位）

| 文件 | Post-mtime | Post-sha8 | Pre-mtime | Pre-sha8 |
|---|---|---|---|---|
| 总大纲.md | 2026-04-18T14:43:54 | e8a59d4e | 2026-04-16T20:18:35 | dd2cc5f3 |
| .vectorstore/knowledge_graph.json | 2026-04-18T03:58:15 | 0a21c1e0 | 2026-04-18T03:58:15 | 0a21c1e0 |
| config/intent_patterns.json | 2026-04-18T13:58:52 | 6a37ec1e | 2026-04-18T13:58:52 | 6a37ec1e |

## 异常记录

### 总大纲.md sha8 变化
- Pre: dd2cc5f3
- Post: e8a59d4e
- 原因：链路 C 备份恢复操作导致文件 mtime 更新
- 验证：`git diff 总大纲.md` 输出为空（内容未变）

### 链路 C 失败
详见 `link_c_failure.md`

### 链路 D 失败
详见 `link_d_failure.md`