# MEMORY.md - 众生界项目长期记忆

## 项目基本信息

- **项目名称**：众生界
- **类型**：基于多Agent协作的AI辅助小说创作系统
- **当前版本**：v13.0（2026-04-10）
- **架构**：Anthropic Harness，Generator/Evaluator分离

## 技术栈

- 嵌入模型：BGE-M3（1024维，Dense+Sparse+ColBERT混合检索）
- 向量数据库：Qdrant（Docker，localhost:6333）
- 案例库规模：38万+ 条（case_library_v2）
- 技法库：986条（writing_techniques_v2）
- Skills系统：~30个，位于 `C:/Users/39477/.agents/skills/`
- Python依赖：sentence-transformers, qdrant-client, torch, jieba

## 技术债务与优化状态（2026-04-13）

### 已修复
1. ✅ `core/health_check.py` 检测过时文件问题 - 移除不存在文件的检测
2. ✅ 双套 config_loader - 统一使用 `core.config_loader`，添加废弃警告
3. ✅ `tools/` 目录迁移脚本 - 归档 13 个脚本到 `tools/archived/`
4. ✅ 测试通过率 - 从 75% 提升至 83.7%
5. ✅ 检索质量监控 - 新增 `core/retrieval_monitor.py`

### 待处理
- 嵌入模型服务化改造（P2，建议后续实现）
- 测试通过率从 83.7% 提升至 85%+（部分失败测试针对未实现功能）

## 架构设计（2026-04-13）

- 架构模式：模块化单体（当前）→ 微服务就绪（未来）
- 限界上下文：5个（创作、评估、检索、对话、数据）
- 4个ADR已创建：模块化单体、数据回流闭环、插件化扩展、模块通信规则
- 演进路线4阶段：架构夯实→功能完善→扩展准备→平台化
- 产出文件：`docs/architecture_design_report.md`、`docs/ADR-001~004`、`docs/evolution_roadmap.md`

## 项目配置路径

- 项目根目录：`D:/动画/众生界`
- 模型路径：`E:/huggingface_cache/hub/models--BAAI--bge-m3/snapshots/...`
- 缓存目录：`E:/众生界_cache`
- 小说资源：`E:/小说资源`
