# 已归档迁移脚本

本目录包含已完成迁移任务的脚本，**不再需要运行**。

## 脚本列表（13个）

| 文件名 | 用途 | 状态 |
|--------|------|------|
| `migrate_all_to_bge_m3.py` | 全量迁移到 BGE-M3 模型 | ✅ 已完成 |
| `migrate_batch_low_memory.py` | 低内存批量迁移 | ✅ 已完成 |
| `migrate_bge_m3_live.py` | 在线迁移（不停服） | ✅ 已完成 |
| `migrate_cases_fixed.py` | 案例库修复迁移 | ✅ 已完成 |
| `migrate_cases_incremental.py` | 案例库增量迁移 | ✅ 已完成 |
| `migrate_cases_uuid.py` | 案例库 UUID 重构 | ✅ 已完成 |
| `migrate_docker.py` | Docker 部署迁移 | ✅ 已完成 |
| `migrate_full.py` | 全量数据迁移 | ✅ 已完成 |
| `migrate_lite_resumable.py` | 轻量可恢复迁移 | ✅ 已完成 |
| `migrate_lite.py` | 轻量迁移 | ✅ 已完成 |
| `migrate_resumable.py` | 可恢复迁移 | ✅ 已完成 |
| `migrate_techniques_to_v2.py` | 技法库 v2 迁移 | ✅ 已完成 |
| `migrate_to_bge_m3.py` | BGE-M3 模型迁移 | ✅ 已完成 |

## 保留原因

这些脚本保留用于：
1. **历史参考**：记录迁移过程和方法
2. **回滚参考**：万一需要逆向迁移，可参考实现
3. **审计溯源**：记录数据结构演变历史

## 可安全删除

如确认不再需要历史参考，可执行：

```bash
# 删除整个目录
rm -rf tools/archived_migrations/

# 或仅保留 README
rm tools/archived_migrations/*.py
```

## 当前数据状态

- **技法库**: `writing_techniques_v2` (BGE-M3 混合检索)
- **案例库**: `case_library_v2` (UUID 主键)
- **设定库**: `novel_settings_v2` (完整 payload)
- **向量维度**: 1024 (BGE-M3 dense)
- **检索模式**: Dense + Sparse + ColBERT 三路混合

---

**归档时间**: 2026-04-23
**归档原因**: 所有迁移任务已完成，数据库结构稳定