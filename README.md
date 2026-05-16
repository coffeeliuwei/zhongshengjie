# 众生界

<p align="center">
  <img src="assets/unnamed.png" alt="众生界" width="600">
</p>

<p align="center">
  <i>千山无名谁曾记，万骨归尘风不知</i>
</p>

<p align="center">
  <i>山风吹尽千年事，更有何人问此时</i>
</p>

---

## 简介

天无主，地无归处。

千年时光流转，众生在洪流中浮沉。

那些鲜活的人——有过名字，有过希望。
如今，名字尘封在岁月深处。

众生皆苦，众生在追问：我是谁？

无人应答。

风穿过无名的墓，穿过荒野的风，穿过那些从未被铭记的人。
他们曾以为自己知道答案。

千年的追问，既无答案，也无尽头。
却如同一粒尘埃，静默地宣布自己存在过。

去问风，去问那些死在黎明前的人——
时光之下，皆是众生。

---

## 项目简介

基于AI的小说创作辅助系统，采用Anthropic Harness架构实现Generator/Evaluator分离的多Agent协作创作。

**核心特性**：
- 5位专业作家 + 1位鉴赏师 + 1位审核评估师
- **灵感引擎（v2）**：鉴赏师三方协商 → 创意契约 → 派单写手重写 → 带豁免评估
- **四层专家架构**：方法论层 → 统一API层 → 技法/案例库层 → 世界观适配层
- **统一提炼引擎**：单一入口、11维度并行提取、数据回流闭环
- 技法库/知识库/案例库向量检索（BGE-M3混合检索）
- **对话式工作流**：意图识别、状态管理、错误恢复
- 章节经验自动沉淀与检索
- 用户反馈闭环机制
- **自动类型发现**：场景/力量/势力/技法四大类型
- **28种场景类型**：开篇/战斗/情感/悬念/转折等
- **场景契约系统**：解决多作家并行创作拼接冲突（12大一致性规则）
- **多世界观支持**：可切换不同世界观配置
- **变更自动检测**：大纲/设定/技法变更自动同步
- **去AI感管线（v0.3）**：100位作家风格档案 + Stage 3.7风格包注入 + Phase 3.5质量门控（Burstiness/套句双检测）+ 自我风格自动融合
- **叙事台账（v0.3）**：跨章节节拍/情绪/主题三维度追踪，30-40章后自动触发多样性约束，防重复感

---



## 📖 学生用户请看这里

> 如果你是老师课堂上的学生，请直接阅读专门为你准备的指导书，里面有从零开始的完整步骤。

**👉 [实训指导书（学生版）](docs/实训指导书_学生版.md)**

涵盖内容：全程对话驱动，复制一段提示词给 opencode 即可完成安装；世界观建立、章节写作、大纲/设定/技法/评估；外部小说库批量提炼（两路并行，GPU 加速）；常见问题速查。

**👉 [实训指导书（二阶段：云原生 API 架构）](docs/实训指导书_二阶段_云原生API架构.md)**

涵盖内容：将本地单机系统改造为阿里云多写手共享平台；VPC + ECS + SAE + API 网关 + OSS + RAM 完整配置；数据迁移、写手接入、高并发优化、商用全场景（安全/备份/熔断/多租户/计费）。代码由 opencode 按实施计划自动生成，无需手动复制：[P1 检索服务](docs/实施计划_二阶段_P1_云端检索API服务.md) · [P2 迁移接入](docs/实施计划_二阶段_P2_数据迁移与写手接入.md) · [P3 高并发商用](docs/实施计划_二阶段_P3_高并发商用改造.md)

---


> 此项目为教学用，不允许批量生成小说用于商业

---

## 更新日志

### v0.3.0 (2026-05-16，master) - 去AI感管线 + 叙事台账

**Problem 1：去AI感（人味注入）**

- ✨ `docs/style_collection/author_styles.yaml`：100位作家风格总档案（178KB），含 aws_profile 8维、行为约束、AI套句黑名单、风格锚点
- ✨ `docs/style_collection/authors_*.yaml`：7个领域碎片文件（剑尘/墨言/云溪/玄一/苍澜/跨域），`merge_author_styles.py` 一键合并
- ✨ `config/writers_style_config.yaml`：5写手默认作家配比（剑尘=天蚕土豆40%+麦卡锡15%等）+ quality_gate 参数
- ✨ `tools/style_injector.py`：Stage 3.7 风格包生成器，按写手+场景类型按权重采样约束/quirk/锚点/黑名单；自动融合 `memory_points_v1` 自我风格（记忆点≥10条时追加）
- ✨ `tools/quality_gate.py`：Phase 3.5 双重检测——Burstiness（句长方差≥50）+ AI套句命中率（≤15%）；FAIL→定向重写建议→最多1次重试
- ✨ `tools/merge_author_styles.py`：碎片YAML合并工具，自动去重
- 🔧 `novel-workflow/SKILL.md`：新增 Stage 3.7（风格包预加载）和 Phase 3.5（质量门控）节点，补充完整 Python 调用代码
- 🔧 5个 `novelist-*/SKILL.md`：全部加入"作家风格包接收"说明（接收格式 + 4条应用规则 + 配比调整命令）

**Problem 2：叙事台账（防30-40章重复感）**

- ✨ `tools/narrative_ledger.py`：跨章节三维度多样性追踪核心模块
  - 节拍台账：同类型组连续3章 → 禁用强制约束；窗口内4+次 → 降频建议
  - 情绪曲线：连续4章张力≥4 → 强制降温；连续3章≤2 → 升温建议
  - 主题权重：8大核心主题，≥30章未出现→沉睡提醒，≥50章→遗失警告
- ✨ `config/narrative_ledger_config.yaml`：场景类型7大分组、阈值、众生界8大核心主题
- 🔧 `novel-workflow/SKILL.md`：阶段1末尾读台账注入多样性约束，阶段8末尾更新台账（含张力换算规则）
- 🔧 `novelist-xuanyi/SKILL.md`：新增主题标注规则（Phase 1 草稿末追加 `[主题标注]` 块）

**文档**：
- 📖 `docs/系统架构.md`：新增 §十五（去AI感管线，含实测验证表）和 §十六（叙事台账）

---

### v0.2.5 (2026-05-11，master) - 司法案例写作素材管道

**司法案例爬取 → 过滤 → 向量入库全链路**：
- 🕷️ `tools/scrape_spp.py`：抓取最高人民检察院 spp.gov.cn 典型案例/检察要闻/检察动态；静态 .shtml 无需 JS；断点续传；本次抓取 749 篇（310+450+0）
- 🕷️ `tools/scrape_thepaper.py`：澎湃新闻辅助爬取，17 个司法频道，与 spp 输出格式兼容
- 🔍 `tools/filter_judicial_cases.py`：关键词评分过滤（STRONG×3 / WEAK×1 / NEGATIVE×−4）；自动分流到 `reviewed/`（保留）/ `uncertain/`（待查）/ `rejected/`（丢弃）；本次 749 篇 → 保留256 / 待查62 / 丢弃431
- 📥 `tools/ingest_judicial_cases.py`：BGE-M3 dense+sparse 嵌入，800字分块，写入 `judicial_cases_v1` collection；当前入库 **1007 块（256篇）**
- 🔎 `UnifiedRetrievalAPI.search_judicial_cases(query, section, top_k)`：写手可直接调用，按语义检索真实案例片段

**配置**：
- `config.json`：新增 `paths.judicial_cases_dir`（默认 `E:/司法案例`）、`database.collections.judicial_cases`（`judicial_cases_v1`）
- `core/config_loader.py`：新增 `get_judicial_cases_dir()` 函数

---

### v0.2.4 (2026-05-02，master) - 二阶段实训文档发布

**二阶段云原生 API 架构改造文档**：
- 📖 [实训指导书\_二阶段\_云原生API架构](docs/实训指导书_二阶段_云原生API架构.md) v3.2.0：10 步基础改造 + 附录 A 高并发 + 附录 B 商用全场景；代码全部抽离到实施计划，指导书专注知识讲授
- 📖 [实施计划\_P1](docs/实施计划_二阶段_P1_云端检索API服务.md)：`zsj-api/` FastAPI 服务（4 接口 + RRF 混合检索），opencode 一键生成
- 📖 [实施计划\_P2](docs/实施计划_二阶段_P2_数据迁移与写手接入.md)：`tools/migrate_to_cloud.py`（批量迁移 + 断点续传）+ `core/retrieval/cloud_client.py`（AppCode 认证）
- 📖 [实施计划\_P3](docs/实施计划_二阶段_P3_高并发商用改造.md)：Redis 缓存版 main.py、三状态熔断器、重试客户端、Locust 压测、JWT 签发、ECS 备份、计费导出，共 8 个文件

---

### v0.2.3 (2026-05-01，master) - 全面代码审计修复

**配置安全**：
- 🔧 `core/health_check.py`：`check_database()` 硬编码 `host="localhost", port=6333` → 改用 `get_qdrant_url()` / `QDRANT_URL` 环境变量，支持非本机部署
- 🔧 `tools/aggregate_dialogue_style.py`：硬编码 URL → `os.environ.get("QDRANT_URL", ...)`
- 🔧 `modules/migration/init_environment.py`：硬编码 `host="localhost"` → `os.environ.get("QDRANT_URL", ...)`

**代码质量**：
- 🔧 `core/health_check.py`：裸 `except:` → `except Exception:`
- 🔧 `core/retrieval/unified_retrieval_api.py`：删除导入但从未使用的 `lru_cache`

**导入链防护**（级联崩溃修复）：
- 🔧 `core/feedback/experience_writer.py`：`import jsonschema` 改为条件导入，缺失时 schema 校验静默跳过而非抛 `ImportError` 阻断整条 `conversation→intent_router→feedback` 导入链
- 🔧 `core/feedback/__init__.py`：`ExperienceWriter` 导入包 `try/except`，避免底层缺失影响上层所有调用者

**依赖管理**：
- 🔧 `requirements.txt`：核心 ML/推理包从 `>=` 锁定为精确版本（`sentence-transformers==5.4.1`、`FlagEmbedding==1.4.0`、`qdrant-client==1.17.1`、`numpy==2.4.4` 等），防止大版本升级静默破坏向量维度或 API；`torch` 保留 `>=` 因 CUDA 后缀因机器而异

**测试**：导入链防护修复后，此前因 `jsonschema` 缺失导致无法收集的 2 个测试文件恢复正常

---

### v0.2.2 (2026-04-28，master) - 案例库性能 & 稳定性 & 架构修复

**案例库检索扩展**：
- ✨ `search_case_quality_anchor()`：按 quality_score 倒序检索，写前提供高质量目标锚点
- ✨ `search_case_technique_instance()`：语义匹配 ANTI_XXX 约束 → 返回反例散文示范
- ✨ `write_own_chapter_scene()` / `search_own_chapters()`：写手自有章节写入向量库，支持跨章检索
- ✨ `ensure_own_chapters_collection()`：首次调用自动建 collection，无需手动初始化
- ✨ `FileUpdater.write_scenes_to_case_library()`：阶段 8 触发，自动归档本章场景

**case_builder 性能优化**：
- ⚡ `convert_files` 多线程：非 mobi → `ThreadPoolExecutor(workers=8)`，mobi → `ProcessPoolExecutor(workers=4)`，转换速度提升约 4x
- ⚡ `extract_cases` 批量 BGE-M3：Phase2 批量 encode（Q3 2n 条 + Q4 n 条各一次），不再逐候选调用
- ✨ `--all` 一键全流程（convert → extract → sync），`--embed-batch` 控制 GPU 推理批次
- ✨ `convert_failures.txt`：转换失败文件自动记录到 `E:/case-library/convert_failures.txt`

**稳定性修复**：
- 🔧 `extraction_runner.py`：Windows 下改用 `OpenProcess` 替代 `os.kill(pid, 0)`，修复进程存活检测崩溃
- 🔧 `anti_template_constraints.json`：ANTI_046/051/052/053 的 constraint_text 中 ASCII 双引号改为「」，修复 JSON 解析失败
- 🔧 `case_builder.py`：print 中 `⚠`（U+26A0）→ `[!]`，修复 PowerShell GBK 环境下 epub 读取失败时进程崩溃
- 🔧 `checkpoint_manager.py`：`load_latest_checkpoint` 异常静默 → 打印文件名和错误信息
- 🔧 `health_check.py`：`scene_writer_mapping` 检查路径从 `.vectorstore/` 修正为 `config/`
- 🔧 `tests/test_vector_dimension.py`：`sync_to_qdrant.py` 路径修正为 `.novel-extractor/`

**灵感引擎修复**：
- 🔧 `stage5_5.py`：新增 `build_stage5_5_prompt_with_real_data()` — 修复鉴赏师 `as_menu()` 未接入导致的伪造0建议
- 🔧 `novel-inspiration-ingest` SKILL：阶段2必读清单与势力列表改为从 `config.json → worldview/paths` 动态读取，删除众生界专属硬编码
- 🔧 `checkpoint_manager`：`session_id` 直接传递，不再从 `workflow_id` 倒推

**实训指导书 v0.3.0 重构**：
- 📖 全程对话驱动，除插件安装外无需手动敲命令
- 📖 新增第五步：外部小说库批量提炼（独立章节，随时可做）
- 📖 修复安装提示词中 BGE-M3 下载命令（`sentence_transformers` → `FlagEmbedding`）
- 📖 三档 embed-batch（笔记本独显/台式独显/CPU），含散热提示
- 📖 Q&A 改为"告诉 AI 描述问题"导向，删除附录B手动安装步骤

**测试**：pytest 684 passed, 2 skipped（修复1个路径错误测试）

---

### v0.2.1 (2026-04-21) - 多小说解耦完整实施（M8）

**多小说解耦（M8）**：
- ✨ 新增 `core/world_loader.py`：`get_world_config` / `switch_world` / `list_available_worlds`
- ✨ CLI 新增 `switch-world` 子命令（`python -m core switch-world 星海纪元`）
- 🔧 skill 文件 B/C 类路径修复（4 处绝对路径 → config 动态读取）
- 🔧 skill 文件 A 类世界观名词批量替换（~200 处，血牙/林夕/村庄广场/血脉-天裂等 → 占位符）
- ✨ 新增 5 个示例世界观配置（`config/worlds/`：修仙世界示例/星海纪元/科幻世界示例/西方奇幻示例）

**测试**：pytest 666 passed, 2 skipped, 0 failed（+21 vs v0.2.0 基线）

---

### v0.2.0 (2026-04-21) - v2 灵感引擎完整集成

**灵感引擎核心组件（P1）**：
- ✨ 创意契约系统（creative_contract.py）— 三方协商产出意向书，含 preserve_list / rejected_list / negotiation_log
- ✨ 派单器（dispatcher.py）— 按契约 item 分发给各写手
- ✨ 鉴赏师 v2 SKILL（novelist-connoisseur，404 行）— 查约束库菜单 + 查记忆点 → 建议 + 派单监工
- ✨ 评估师豁免逻辑（evaluator_exemption.py）— 读契约 preserve_list 豁免对应维度（子项级别）
- ✨ 三方协商升级（escalation_dialogue.py）— 鉴赏师 + 评估师 + 作者，支持撤销/强制通过/重协商
- 🗑️ 多变体生成器（variant_generator.py）删除 — v2 改为 original-only 模式

**工作流集成（P2）**：
- ✨ 阶段 5.5：三方协商接入 — 整章润色后进入协商，产出创意契约
- ✨ 阶段 5.6：派单执行 — 契约下发给剑尘/云溪改写，MUST_PRESERVE 标记生效
- ✨ 阶段 6：带豁免评估 — 读 preserve_list 豁免维度，3 次 <0.8 触发对话升级
- ✨ 阶段 7：推翻事件回流 — author_force_pass → memory_points_v1 (retrieval_weight=2.0)
- ✨ 阶段 8：经验写入 — 每章 log.json 含 techniques_used / what_worked / what_didnt_work

**多小说解耦（P5）**：
- 🔧 novel-workflow SKILL 路径硬编码修复（PROJECT_ROOT → 环境变量自动检测）
- 🔧 novelist-canglan SKILL switch_world 硬编码修复（→ 从 config 自动加载）
- ✨ init_novel.py 新增 --template 模式（世界观配置模板生成）
- 🔧 data_builder.py DEFAULT_CONFIG 补齐 5 个缺失 v1 collection

**测试**：pytest 645 passed, 0 failed（修复了 3 个预存在缺陷，2 skipped）

---

### v0.1.0-preview (2026-04-20) - 首个预览版发布

**发布**：
- 🚀 面向学生开放首个预览版（master 分支可下载）
- 📖 傻瓜版快速开始文档（5步跑起来）

**v2 灵感引擎核心组件（P1-1 ~ P1-7，未集成 workflow，待 P2）**：
- ✨ 创意契约系统（creative_contract.py）
- ✨ 派单器（dispatcher.py）
- ✨ 鉴赏师 v2（三方协商 + 派单监工）
- ✨ Evaluator 豁免逻辑（evaluator_exemption.py）
- ✨ escalation 三方协商机制

**测试**：pytest 629 passed 基线（3 failed 为预存在缺陷，v0.2.0 已修复，645 passed, 0 failed）

---

### v14.0 (2026-04-14) - 审核维度对话添加与项目清理

**新增功能**：
- ✨ 审核维度对话添加机制 - 用户反馈自动提取禁止项候选
- ✨ 审核维度动态加载 - 新增禁止项实时生效无需重启
- ✨ 案例库核心数据结构 - 编号场景目录组织
- ✨ 小说提炼系统核心代码 - 支持批量提炼

**改进**：
- 技法管理改为素材提炼模式
- Collection三维度功能增强设计方案
- README反映实际项目状态（Skills数量、目录结构）

**清理**：
- 移除superpowers/archived等文档目录（git优化）
- 移除冗余的config_loader代理模块
- 修正.gitignore中的qdrant路径bug
- 撤销意外提交的数据库文件

### v13.0 (2026-04-10) - 统一提炼引擎重构

**新增模块**：
- ✨ 统一提炼引擎 (UnifiedExtractor) - 11维度并行提取
- ✨ 对话入口层 (ConversationEntryLayer) - 意图识别+状态管理+错误恢复
- ✨ 变更检测器 (ChangeDetector) - 自动检测大纲/设定变更
- ✨ 类型发现器 (TypeDiscoverer) - 4大类型自动发现
- ✨ 统一检索API (UnifiedRetrievalAPI) - 多源检索+混合检索
- ✨ 反馈系统 (FeedbackCollector/ExperienceWriter) - 评估回流+经验沉淀
- ✨ 生命周期管理 (TechniqueTracker/ContractLifecycle) - 技法追踪+版本控制

**改进**：
- 融合度：45% → 100%
- 数据覆盖：48% → 100%
- 可检索维度：3个 → 14个
- 提炼入口：2套独立 → 1套单一
- 测试用例：~100 → 226个

**修复**：
- 添加 .mobi 格式支持
- 修复进度追踪 bug
- 修复裸 except 子句
- 统一配置管理