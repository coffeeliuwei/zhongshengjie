# Release Notes — v0.2.0

- **发布日期**：2026-04-21 (Asia/Shanghai)
- **分支**：master（由 v2-dev 合并，31 commits，107 files）
- **测试基线**：pytest 645 passed, 0 failed, 2 skipped

---

## 亮点

v0.2.0 完成了 **v2 灵感引擎的全面集成**——从创意契约、三方协商，到 workflow 各阶段的完整串联，以及多小说解耦的第一步。这是 v0.1.0-preview 发布后最大的一次功能迭代（+9127 行核心代码）。

---

## 新增功能

### 灵感引擎核心组件（P1-1 ~ P1-7）

| 组件 | 文件 | 说明 |
|------|------|------|
| 创意契约系统 | `core/inspiration/creative_contract.py` | 三方协商产出的意向书；含 preserve_list（嵌套 aspects）、rejected_list、negotiation_log、skipped_by_author 字段 |
| 派单器 | `core/inspiration/dispatcher.py` | 按契约 item 分发给各写手 |
| 鉴赏师 v2 SKILL | `~/.agents/skills/novelist-connoisseur/SKILL.md` | 404 行 v2 版本；查约束库菜单 + 查记忆点 → 建议 + 派单监工 |
| 评估师豁免逻辑 | `core/inspiration/evaluator_exemption.py` | 读契约 preserve_list，按子项豁免（禁止整维度豁免） |
| 三方协商升级 | `core/inspiration/escalation_dialogue.py` | 3-choice 作者决策（撤销/强制通过/重协商）+ 死锁兜底 |
| 约束库菜单 API | `core/inspiration/constraint_library.py` | 新增 4 个菜单查询方法 |

**已删除**：`core/inspiration/variant_generator.py`（v2 改为 original-only，不再生成变体）

### 工作流集成（P2-1 ~ P2-5）

| 阶段 | 文件 | 说明 |
|------|------|------|
| 5.5 三方协商 | `core/inspiration/stage5_5.py` | 整章润色后调用鉴赏师→评估师→作者协商，产出创意契约 |
| 5.6 派单执行 | workflow 集成 | 契约下发写手，MUST_PRESERVE 标记写入段落 |
| 6 带豁免评估 | workflow 集成 | 评估读 preserve_list 豁免维度；3 次 <0.8 触发升级 |
| 7 推翻回流 | workflow 集成 | author_force_pass → memory_points_v1 (retrieval_weight=2.0) |
| 8 经验写入 | workflow 集成 | 每章 log.json 含 techniques_used / what_worked / what_didnt_work |

### 多小说解耦（P5）

- `novel-workflow` SKILL：PROJECT_ROOT 硬编码路径 → 环境变量自动检测
- `novelist-canglan` SKILL：switch_world 硬编码 → 从 config.json 自动加载
- `tools/init_novel.py`：新增 `--template` 模式，生成世界观配置模板
- `tools/data_builder.py`：DEFAULT_CONFIG 补齐 5 个缺失 v1 collection

---

## 修复

- 修复 3 个预存在的 scene_writer_mapping.json 相关测试失败（创建缺失文件）
- 修复 escalation_dialogue.py 的 stale 测试（适配 original-only 模式）

---

## 测试

```
pytest 645 passed, 0 failed, 2 skipped
```

较 v0.1.0-preview（629 passed, 3 failed）：**+16 passed，3 failed → 0 failed**。

---

## 已知限制

- M8 多小说解耦仅完成第一步（skill 路径修复 + init_novel template）；全量解耦（12 个 skill 去世界观硬编码）列为后续工作
- 72 个"悬空"文件（v1 集成修改、工具、数据文件等）未并入本次发布

---

## 升级指南

从 v0.1.0-preview 升级：

```bash
git pull origin master
```

新功能默认开启，无需修改配置。如使用 novelist-connoisseur skill，需同步 `~/.agents/skills/novelist-connoisseur/SKILL.md`（鉴赏师 v2 版本）。

---

## 致谢

本次发布由 Claude Sonnet 4.6 设计规划，opencode (GLM5) 实施代码，共完成 31 个 commit，覆盖 P1~P5 全阶段。
