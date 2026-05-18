# 众生界项目骨架

> **自动生成** | 2026-05-18 13:21 (Asia/Shanghai)
> **用途**: 供 AI 快速认知项目结构，不含实现细节
> **覆盖**: 189 个文件 / 164 个类 / 541 个函数
> **更新**: git pre-commit hook 自动触发（.py 变更时重新生成）

---

## 目录索引

| 目录 | 职责 |
|------|------|
| `core/` | 核心业务：对话路由、检索、配置、生命周期 |
| `modules/` | 功能模块：知识库、验证、可视化、迁移 |
| `tools/` | CLI 工具：构建/同步/分析/提炼 |
| `scripts/` | 定时/批量脚本 |
| `config/` | 维度配置 |
| `.vectorstore/` | 向量库运维工具 |
| `.novel-extractor/` | 外部小说提炼引擎 |

---

## `core/`


### `core/change_detector/__init__.py`

- `def quick_scan(project_root: str | None = None) -> dict[str, Any]`  # 快速扫描变更的便捷函数

- `def quick_sync(
    project_root: str | None = None, rebuild: bool = False
) -> dict[str, Any]`  # 快速同步变更的便捷函数

### `core/change_detector/change_detector.py`

**class ChangeDetector**
  _统一变更检测器_
  - `__init__(
        self,
        project_root: Optional[Path] = None,
        watch_list: Optional[Dict[str, str]] = None,
        auto_sync: bool = True,
        use_hash: bool = True,
    )`  # 初始化变更检测器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `_detect_file_changes(self, pattern: str) -> List[FileChange]`  # 检测单个数据源的文件变更
  - `scan_changes(self) -> Dict[str, List[FileChange]]`  # 扫描所有数据源变更
  - `sync_changes(
        self,
        changes: Dict[str, List[FileChange]],
        rebuild: bool = False,
    ) -> Dict[str, SyncResult]`  # 同步变更到对应的存储
  - `_sync_outline_to_worldview(self) -> SyncResult`  # 大纲 → 世界观配置
  - `_sync_settings_to_graph(self, rebuild: bool = False) -> SyncResult`  # 设定 → 知识图谱
  - `_sync_techniques_to_qdrant(self, rebuild: bool = False) -> SyncResult`  # 技法 → 向量库
  - `run(
        self,
        sync: bool = True,
        rebuild: bool = False,
    ) -> ChangeReport`  # 执行变更检测和同步
  - `_generate_summary(
        self,
        changes: Dict[str, List[FileChange]],
        sync_results: Dict[str, SyncResult],
    ) -> str`  # 生成变更摘要
  - `get_change_history(
        self,
        limit: int = 10,
    ) -> List[ChangeReport]`  # 获取变更历史
  - `clear_history(self) -> None`  # 清除变更历史
  - `reset_state(self) -> None`  # 重置文件状态
  - `add_watch_target(
        self,
        source: str,
        pattern: str,
    ) -> None`  # 添加监控目标
  - `remove_watch_target(self, source: str) -> None`  # 移除监控目标
  - `get_watch_list(self) -> Dict[str, str]`  # 获取监控配置
  - `get_sync_status(self) -> Dict[str, Any]`  # 获取同步状态
  - `force_sync_all(self, rebuild: bool = False) -> Dict[str, SyncResult]`  # 强制同步所有数据源

### `core/change_detector/file_watcher.py`

**class FileWatcher**
  _文件变更检测器_
  - `__init__(
        self,
        project_root: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        use_hash: bool = True,
    )`  # 初始化文件检测器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `_load_state(self) -> None`  # 加载已保存的文件状态
  - `_save_state(self) -> None`  # 保存文件状态到缓存
  - `_get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]`  # 获取文件信息（mtime, size, hash）
  - `_compute_hash(self, file_path: Path, algorithm: str = "md5") -> str`  # 计算文件hash
  - `detect_change(self, file_path: Path) -> Optional[FileChange]`  # 检测单个文件变更
  - `detect_changes(
        self,
        pattern: str,
        base_dir: Optional[Path] = None,
    ) -> List[FileChange]`  # 批量检测文件变更
  - `detect_directory_changes(
        self,
        directory: Path,
        extensions: list[str] | None = None,
    ) -> list[FileChange]`  # 检测目录下所有文件的变更
  - `get_file_state(self, file_path: Path) -> Optional[FileState]`  # 获取文件的当前状态
  - `clear_state(self) -> None`  # 清除所有状态记录
  - `reset_file_state(self, file_path: Path) -> None`  # 重置单个文件的状态
  - `sync_state(self) -> None`  # 同步状态到缓存文件
  - `get_all_states(self) -> Dict[str, FileState]`  # 获取所有文件状态

### `core/change_detector/sync_manager_adapter.py`

**class SyncManagerAdapter**
  _同步管理器适配器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化适配器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `_get_sync_manager(self)`  # 获取 SyncManager 实例
  - `_get_worldview_generator(self)`  # 获取世界观生成器实例（M2-β 后永久使用 Mock，旧实现已归档至 .archived/vectorstore_core_20260418/）
  - `sync_outline_to_worldview(
        self,
        outline_file: Optional[Path] = None,
    ) -> SyncResult`  # 同步大纲到世界观配置
  - `sync_settings_to_graph(
        self,
        settings_dir: Optional[Path] = None,
        rebuild: bool = False,
    ) -> SyncResult`  # 同步设定到知识图谱
  - `sync_techniques_to_qdrant(
        self,
        techniques_dir: Optional[Path] = None,
        rebuild: bool = False,
    ) -> SyncResult`  # 同步技法到向量库
  - `sync_cases_to_qdrant(
        self,
        rebuild: bool = False,
    ) -> SyncResult`  # 同步案例库到向量库
  - `sync_chapter_outline_file(self, file_path: Path) -> SyncResult`  # 将单个章节大纲文件同步到 Qdrant chapter_outlines collection。
  - `sync_total_outline_to_qdrant(
        self, outline_file: Optional[Path] = None
    ) -> SyncResult`  # 将总大纲文件同步到 Qdrant novel_plot_v1 collection。
  - `sync_all(
        self,
        rebuild: bool = False,
    ) -> Dict[str, SyncResult]`  # 同步所有数据源
  - `get_sync_status(self) -> Dict[str, Any]`  # 获取同步状态

**class _MockSyncManager**
  _模拟 SyncManager（用于导入失败时）_
  - `sync_novel_settings(self, rebuild: bool = False) -> int`
  - `sync_techniques(self, rebuild: bool = False) -> int`
  - `sync_cases(self, rebuild: bool = False) -> int`
  - `get_sync_status(self) -> Dict[str, Any]`

**class _MockWorldviewGenerator**
  _模拟世界观生成器（用于导入失败时）_
  - `sync_from_outline(self, outline_path: str = "总大纲.md") -> Dict[str, Any]`

### `core/cli.py`
> 众生界 - 命令行入口

**class CLI**
  _命令行接口_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化CLI
  - `_create_parser(self) -> argparse.ArgumentParser`  # 创建命令行解析器
  - `run(self, args: Optional[list] = None) -> int`  # 运行CLI
  - `_handle_config(self, args: argparse.Namespace) -> int`  # 处理配置模块
  - `_handle_knowledge_base(self, args: argparse.Namespace) -> int`  # 处理知识入库模块
  - `_handle_validation(self, args: argparse.Namespace) -> int`  # 处理验证模块
  - `_handle_creation(self, args: argparse.Namespace) -> int`  # 处理创作模块（M2-β 后该模块已归档，转为引导用户走 skill 入口）
  - `_handle_migration(self, args: argparse.Namespace) -> int`  # 处理移植模块（功能未实现，返回 exit code 2）
  - `_handle_visualization(self, args: argparse.Namespace) -> int`  # 处理可视化模块
  - `_handle_switch_world(self, args: argparse.Namespace) -> int`  # 处理世界观切换模块 (M8 新增)

- `def main()`  # CLI入口函数

### `core/config_bridge.py`

- `def _get_config()`

- `def get_project_dir() -> Path`  # 获取项目根目录

- `def get_model_path() -> Optional[str]`  # 获取模型路径

- `def get_qdrant_url() -> str`  # 获取Qdrant URL

- `def get_vectorstore_dir() -> Path`  # 获取向量库目录

- `def init_paths_from_config()`  # 从配置文件重新初始化路径

### `core/config_loader.py`

- `def find_project_root() -> Path`  # 自动检测项目根目录

- `def get_project_root() -> Path`  # 获取项目根目录

- `def get_config_path() -> Path`  # 获取配置文件路径

- `def load_config() -> Dict[str, Any]`  # 加载配置

- `def get_config() -> Dict[str, Any]`  # 获取全局配置

- `def get_path(path_name: str) -> Path`  # 获取路径配置

- `def get_model_path() -> Optional[str]`  # 获取模型路径

- `def get_hf_cache_dir() -> Optional[str]`  # 获取HuggingFace缓存目录

- `def get_qdrant_url() -> str`  # 获取Qdrant URL

- `def get_collection_name(collection_type: str) -> str`  # 获取collection名称

- `def get_database_timeout() -> int`  # 获取数据库超时时间（秒）

- `def get_batch_size() -> int`  # 获取批处理大小

- `def get_retrieval_config() -> dict`  # 获取检索配置

- `def get_max_content_length() -> int`  # 获取最大内容长度

- `def get_max_payload_size() -> int`  # 获取最大payload大小

- `def get_skip_rules() -> list`  # 获取跳过的校验规则列表

- `def get_worldview_config() -> dict`  # 获取世界观配置

- `def get_current_world() -> str`  # 获取当前世界观名称

- `def get_outline_path() -> Optional[str]`  # 获取大纲文件路径

- `def is_auto_sync_enabled() -> bool`  # 检查是否启用自动同步

- `def get_settings_dir() -> Path`

- `def get_techniques_dir() -> Path`

- `def get_vectorstore_dir() -> Path`

- `def get_case_library_dir() -> Path`

- `def get_judicial_cases_dir() -> Path`

- `def get_logs_dir() -> Path`

- `def get_cache_dir() -> Path`  # 获取缓存目录

- `def get_temp_dir() -> Path`  # 获取临时目录（用于避免C盘空间问题）

- `def get_contracts_dir() -> Path`  # 获取场景契约存储目录

- `def get_novel_extractor_dir() -> Path`  # 获取小说提取器目录 (.novel-extractor)

- `def get_world_configs_dir() -> Path`  # 获取世界观配置目录 (.vectorstore/core/world_configs)

- `def get_scene_writer_mapping_path() -> Path`  # 获取场景作家映射文件路径

- `def get_knowledge_graph_path() -> Path`  # 获取知识图谱文件路径

- `def get_qdrant_storage_dir() -> Path`  # 获取Qdrant存储目录

- `def get_config_dir() -> Path`  # 获取配置目录 (config/)

- `def get_world_config_path(world_name: str = None) -> Path`  # 获取指定世界观配置文件路径

- `def get_novel_sources() -> list`  # 获取小说资源目录列表

- `def get_skills_base_path() -> Path`  # 获取Skills基础路径

- `def get_realm_order(power_system: str = None) -> list`  # 获取境界等级顺序

- `def get_all_realm_orders() -> dict`  # 获取所有力量体系的境界配置

- `def _load_current_world_config() -> dict`  # 加载当前世界观配置，文件不存在时静默返回空字典，其他异常打印警告

- `def reset_config()`  # 重置配置（用于测试）

- `def get_quality_thresholds() -> dict`  # 获取数据清洗质量阈值配置

- `def get_clean_pipeline_config() -> dict`  # 获取清洗流程配置

- `def get_clean_dir() -> Path`  # 获取清洗后小说存储目录

- `def ensure_all_dirs() -> list`  # 创建项目所需的全部本地目录（幂等，已存在则跳过）。

- `def get_device(verbose: bool = True) -> str`  # 检测可用的推理设备，返回 'cuda' 或 'cpu'。

- `def get_inspiration_engine_config() -> dict`  # 获取灵感引擎配置

### `core/config_manager.py`
> config_manager.py — 已废弃（Deprecated）

**class ConfigManager**
  _配置管理器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化配置管理器
  - `_load_config(self) -> None`  # 加载所有配置
  - `_parse_config_md(self) -> None`  # 解析CONFIG.md文件
  - `_load_system_config(self) -> None`  # 加载system_config.json
  - `save_system_config(self) -> None`  # 保存system_config.json
  - `get_db_connection_url(self) -> str`  # 获取数据库连接URL
  - `get_collection_name(self, collection_type: str) -> str`  # 获取集合名称
  - `ensure_directories(self) -> None`  # 确保所有目录存在
  - `update_custom_resource(self, resource_id: str, path: Path) -> None`  # 更新自定义资源目录
  - `get_config_summary(self) -> Dict[str, Any]`  # 获取配置摘要

- `def get_config(project_root: Optional[Path] = None) -> ConfigManager`  # 获取全局配置实例

### `core/conversation/__init__.py`

- `def process_user_input(
    user_input: str, project_root: Optional[str] = None
) -> Dict[str, Any]`  # 处理用户输入的便捷函数

### `core/conversation/checkpoint_manager.py`

**class CheckpointManager**
  _Checkpoint 文件 I/O。_
  - `__init__(self, session_id: str, project_root: Optional[Path] = None)`
  - `save_scene_summary(
        self,
        chapter: int,
        scene_index: int,
        scene_type: str,
        summary: str,
        key_points: List[str],
        writer_agent: str = "",
    ) -> str`  # 保存场景摘要（每场完成后调用）。
  - `load_chapter_summaries(self, chapter: int) -> List[SceneSummary]`  # 加载章节内所有已完成场景摘要（按 scene_index 排序）。
  - `format_summaries_for_prompt(self, chapter: int) -> str`  # 将已完成场景摘要格式化为注入字符串。
  - `save_checkpoint(
        self,
        chapter: int,
        phase: int,
        scene_index: int = 0,
        scene_total: int = 0,
        phase_sub: Optional[str] = None,
        active_writer: Optional[str] = None,
        pending_actions: Optional[List[str]] = None,
        note: str = "",
    ) -> str`  # 保存工作流断点。
  - `load_latest_checkpoint(self, chapter: int) -> Optional[WorkflowCheckpoint]`  # 加载章节最新断点。
  - `get_resume_description(self, chapter: int) -> str`  # 返回可读的断点恢复说明（供 generate_resume_prompt 使用）。
  - `clear_chapter_checkpoints(self, chapter: int) -> int`  # 章节确认后清理当章所有 checkpoint 文件（阶段7调用）。

### `core/conversation/conversation_entry_layer.py`

**class ProcessingStatus((Enum))**
  _处理状态_

**class ConversationEntryLayer**
  _对话入口层_
  - `__init__(
        self, project_root: Optional[str] = None, session_id: Optional[str] = None
    )`  # 初始化对话入口层
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `process_input(self, user_input: str) -> ProcessingResult`  # 处理用户输入（主入口）
  - `_handle_special_intents(
        self, intent_result: IntentResult, user_input: str
    ) -> Optional[ProcessingResult]`  # 处理特殊意图
  - `_execute_intent(
        self,
        intent_result: IntentResult,
        user_input: str,
        missing_info: List[MissingInfo],
    ) -> ProcessingResult`  # 执行意图
  - `_execute_setting_update(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult`  # 执行设定更新
  - `_execute_workflow_control(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult`  # 执行工作流控制
  - `_get_retrieval_api(self)`  # [M3-α] 懒加载 UnifiedRetrievalAPI（首次调用时初始化 BGE-M3）
  - `_execute_query(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult`  # [M3-α] 按意图分支接入真实检索 / 状态查询
  - `_execute_tracking(
        self, intent_result: IntentResult, user_input: str
    ) -> ProcessingResult`  # 执行追踪系统操作
  - `_parse_chapter_number(self, chapter_str: str) -> int`  # 解析章节号
  - `update_workflow_progress(
        self, phase: int, metadata: Optional[Dict[str, Any]] = None
    ) -> None`  # 更新工作流进度
  - `complete_workflow(self) -> None`  # 完成当前工作流
  - `get_context(self, limit: int = 10) -> List[Dict[str, Any]]`  # 获取对话上下文
  - `clear_context(self) -> None`  # 清空对话上下文
  - `_inject_feedback_context(self, result: ProcessingResult) -> ProcessingResult`  # 将旁路收集的反馈上下文注入 ProcessingResult.data

### `core/conversation/data_extractor.py`

**class ConversationDataExtractor**
  _会话数据提取器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化数据提取器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `extract_and_update(
        self, user_input: str, intent_result: IntentResult
    ) -> ExtractionResult`  # 提取数据并更新文件
  - `_extract_structured_data(
        self, intent: str, entities: Dict[str, str]
    ) -> Optional[Dict[str, Any]]`  # 提取结构化数据
  - `_build_character_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建角色数据
  - `_build_character_ability_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建角色能力数据
  - `_build_relation_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建关系数据
  - `_build_faction_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建势力数据
  - `_build_faction_member_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建势力成员数据
  - `_build_plot_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建剧情数据
  - `_build_hook_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建伏笔数据
  - `_build_resource_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建资源数据
  - `_build_payoff_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建承诺数据
  - `_build_power_type_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建力量体系数据
  - `_build_power_level_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建力量境界数据
  - `_build_era_data(self, entities: Dict[str, str]) -> Dict[str, Any]`  # 构建时代数据
  - `_update_source_file(
        self, file_path: str, intent: str, data: Dict[str, Any]
    ) -> bool`  # 更新源文件
  - `_sync_to_vectorstore(self, collection: str, data: Dict[str, Any]) -> bool`  # 同步到向量数据库
  - `_generate_feedback(
        self, intent: str, data: Dict[str, Any], success: bool
    ) -> str`  # 生成用户反馈
  - `get_target_file(self, intent: str) -> Optional[str]`  # 获取意图对应的目标文件
  - `get_collection(self, intent: str) -> Optional[str]`  # 获取意图对应的向量数据库Collection

### `core/conversation/eval_criteria_extractor.py`

**class EvaluationCriteriaExtractor**
  _审核维度提取器_
  - `__init__(self, project_root: Optional[str] = None)`
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `extract_prohibition(self, user_input: str) -> ProhibitionCandidate`  # 从用户输入提取禁止项
  - `discover_from_file(self, file_path: str) -> List[ProhibitionCandidate]`  # 从文档文件中批量发现禁止项候选
  - `_resolve_file_path(self, file_path: str) -> Optional[Path]`  # 解析文件路径
  - `_read_document(self, path: Path) -> str`  # 读取文档
  - `_scan_for_fake_expressions(self, content: str) -> List[ProhibitionCandidate]`  # 扫描已知"假表达"模式
  - `_analyze_high_frequency_patterns(
        self, content: str
    ) -> List[ProhibitionCandidate]`  # 分析高频可疑表达
  - `_is_repetitive_expression(self, phrase: str) -> bool`  # 判断是否是重复性表达（可能是模板化写作）
  - `_deduplicate_candidates(
        self, candidates: List[ProhibitionCandidate]
    ) -> List[ProhibitionCandidate]`  # 去重
  - `_extract_name_and_examples(self, user_input: str) -> tuple[str, List[str]]`  # 提取禁止项名称和示例
  - `_generate_variants(self, base: str) -> List[str]`  # 生成变体示例
  - `_generate_pattern(self, examples: List[str]) -> str`  # 生成匹配模式
  - `_check_duplicate(self, name: str) -> bool`  # 检查是否已存在
  - `_load_existing_prohibitions(self) -> List[str]`  # 加载现有禁止项
  - `format_for_confirmation(self, candidate: ProhibitionCandidate) -> str`  # 格式化供用户确认
  - `confirm_and_save(self, new_name: Optional[str] = None) -> bool`  # 确认并保存
  - `_append_to_migrated_file(self, candidate: ProhibitionCandidate) -> bool`  # 追加到迁移文件
  - `_sync_to_vectorstore(self, candidate: ProhibitionCandidate) -> bool`  # 同步到向量库 (M1修复：调用FileUpdater真实同步)

### `core/conversation/file_updater.py`

**class FileUpdater**
  _文件更新器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化文件更新器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `update_markdown(
        self, file_path: str, intent: str, data: Dict[str, Any]
    ) -> bool`  # 更新Markdown文件
  - `update_json(self, file_path: str, intent: str, data: Dict[str, Any]) -> bool`  # 更新JSON文件
  - `sync_to_vectorstore(self, collection: str, data: Dict[str, Any]) -> bool`  # 同步到向量数据库
  - `_generate_embedding_text(self, collection: str, data: Dict[str, Any]) -> str`  # 根据Collection类型生成嵌入文本
  - `_create_new_file(self, path: Path, intent: str, data: Dict[str, Any]) -> bool`  # 创建新文件
  - `_create_backup(self, path: Path) -> Optional[Path]`  # 创建文件备份
  - `_generate_initial_content(
        self, filename: str, intent: str, data: Dict[str, Any]
    ) -> str`  # 生成初始文件内容
  - `_generate_markdown_header(self, filename: str) -> str`  # 生成Markdown文件头部
  - `_format_data_as_markdown(self, data: Dict[str, Any], intent: str) -> str`  # 将数据格式化为Markdown
  - `_handle_tracking_file(
        self, path: Path, content: str, intent: str, data: Dict[str, Any]
    ) -> Optional[str]`  # 处理追踪系统文件
  - `_format_hook_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化伏笔条目
  - `_update_hook_status(self, file_path: Path, data: Dict[str, Any]) -> None`  # 更新伏笔状态（触发/解决）
  - `_format_resource_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化资源条目
  - `_format_injury_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化伤害条目
  - `_format_info_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化信息条目
  - `_format_share_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化信息分享条目
  - `_format_payoff_entry(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 格式化承诺条目
  - `_update_payoff_status(self, file_path: Path, data: Dict[str, Any]) -> None`  # 更新承诺状态（已兑现）
  - `_update_character_profile(
        self, path: Path, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 更新人物谱
  - `_append_new_character(self, content: str, data: Dict[str, Any]) -> str`  # 追加新角色
  - `_add_character_ability(self, file_path: Path, data: Dict[str, Any]) -> None`  # 在角色条目的"能力"小节追加新能力
  - `_add_character_relation(self, file_path: Path, data: Dict[str, Any]) -> None`  # 在角色条目的"关系"小节追加新关系
  - `_update_faction_profile(
        self, content: str, data: Dict[str, Any], intent: str
    ) -> str`  # 更新势力档案
  - `_update_power_system(self, file_path: Path, data: Dict[str, Any]) -> None`  # 更新力量体系条目
  - `_update_timeline(self, content: str, data: Dict[str, Any], intent: str) -> str`  # 更新时间线
  - `_append_to_file(self, content: str, data: Dict[str, Any], intent: str) -> str`  # 默认追加到文件
  - `_merge_json_data(
        self, existing: Dict[str, Any], new_data: Dict[str, Any], intent: str
    ) -> Dict[str, Any]`  # 合并JSON数据
  - `_log_vectorstore_update(self, collection: str, data: Dict[str, Any])`  # 记录向量数据库更新日志
  - `write_scenes_to_case_library(
        self,
        chapter_name: str,
        scenes: List[Dict[str, Any]],
        novel_name: str = "众生界",
    ) -> Dict[str, Any]`  # 将本章场景写入本书案例库，供后续章节一致性检索。

### `core/conversation/intent_clarifier.py`

**class ClarificationType((Enum))**
  _澄清类型_

**class IntentClarifier**
  _意图澄清器_
  - `__init__(self)`  # 初始化意图澄清器
  - `needs_clarification(self, intent_result: IntentResult) -> bool`  # 判断是否需要澄清
  - `generate_clarification(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion`  # 生成澄清问题
  - `_determine_clarification_type(
        self, intent_result: IntentResult
    ) -> ClarificationType`  # 确定澄清类型
  - `_generate_low_confidence_question(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion`  # 生成低置信度问题
  - `_generate_ambiguous_question(
        self, intent_result: IntentResult
    ) -> ClarificationQuestion`  # 生成模糊意图问题
  - `_generate_trigger_question(
        self, intent_result: IntentResult, user_input: str
    ) -> ClarificationQuestion`  # 生成触发模式问题
  - `_generate_missing_entity_question(
        self, intent_result: IntentResult
    ) -> ClarificationQuestion`  # 生成缺少实体问题
  - `_find_matching_template(self, user_input: str) -> Optional[Dict[str, Any]]`  # 查找匹配的澄清模板
  - `_generate_intent_description(
        self, intent: str, entities: Dict[str, str]
    ) -> str`  # 生成意图描述
  - `process_clarification_response(
        self, user_response: str, clarification: ClarificationQuestion
    ) -> Dict[str, Any]`  # 处理用户澄清回复
  - `get_clarification_history(self, limit: int = 10) -> List[ClarificationQuestion]`  # 获取澄清历史
  - `clear_history(self) -> None`  # 清空澄清历史

### `core/conversation/intent_classifier.py`

**class IntentCategory((Enum))**
  _意图分类_

**class IntentClassifier**
  _意图分类器（M4 后 patterns 从 config/intent_patterns.json 加载）_
  - `__init__(self)`  # 初始化意图分类器（[M4] 从 config/intent_patterns.json 加载 patterns）
  - `_compile_patterns(self)`  # 预编译所有正则表达式
  - `classify(self, user_input: str) -> IntentResult`  # 分类用户输入的意图
  - `_match_patterns(
        self, text: str, intent_configs: Dict, is_core: bool
    ) -> Optional[IntentResult]`  # 匹配意图模式
  - `_extract_entities(
        self, match: re.Match, entity_names: List[str]
    ) -> Dict[str, str]`  # 从正则匹配中提取实体
  - `_calculate_confidence(self, match: re.Match, text: str, is_core: bool) -> float`  # 计算意图置信度
  - `get_intent_info(self, intent_name: str) -> Optional[Dict]`  # 获取意图详细信息
  - `get_all_intents(self) -> Dict[str, List[str]]`  # 获取所有支持的意图类型
  - `get_intents_by_category(self, category: IntentCategory) -> List[str]`  # 按分类获取意图类型

### `core/conversation/intent_router.py`

**class IntentRouter**
  _意图路由器_
  - `__init__(self)`  # 初始化路由器，创建持久化提取器实例以跨调用共享 pending 状态
  - `route(
        self,
        intent: str,
        entities: Dict[str, Any],
        user_input: str,
    ) -> RoutingResult`  # 路由意图到对应后端处理函数
  - `_get_handler(self, intent: str)`  # 查找意图对应处理函数，未注册返回 None
  - `_handle_reader_moment_feedback(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 处理读者反馈类意图（正向/对比/外部注入），通过 FeedbackDispatcher 路由
  - `_handle_overturn_feedback(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 处理推翻事件反馈，通过 FeedbackDispatcher 路由
  - `_handle_connoisseur_audit_response(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 处理鉴赏师审计响应：作者标定真实点火次数
  - `_handle_inspiration_status_query(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 返回灵感引擎状态报告
  - `_handle_constraint_query(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 查询约束库状态
  - `_handle_constraint_add(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 提示用户通过对话添加约束
  - `_handle_constraint_tuning(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 提示用户约束调整流程
  - `_handle_inspiration_bailout(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 临时关闭灵感引擎
  - `_handle_extract_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 从用户输入中提炼技法候选
  - `_handle_extract_technique_from_file(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 从文件路径提炼技法
  - `_handle_confirm_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 确认技法候选，写入文件并同步到向量库
  - `_handle_modify_technique(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 修改技法名称
  - `_handle_add_evaluation_criteria(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 从用户描述中提炼禁止项候选
  - `_handle_discover_prohibitions_from_file(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 从文件扫描发现禁止项候选
  - `_handle_modify_evaluation_threshold(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 修改评估阈值
  - `_handle_confirm_evaluation_criteria(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 确认将评估标准/禁止项写入文件并同步到 Qdrant
  - `_handle_inspiration_conflict_resolution(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 处理用户与鉴赏师冲突——用户表态接受或推翻
  - `_handle_incremental_extraction(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 启动增量提炼（已完成维度自动跳过）
  - `_handle_full_extraction(
        self, intent: str, entities: Dict[str, Any], user_input: str
    ) -> RoutingResult`  # 启动全量提炼（强制重跑，忽略历史进度）

- `def record_audit_label(label: str) -> str`  # 记录作者对审计的标定结果（写入日志，可后续升级为记忆点入库）

- `def _query_constraints(user_input: str) -> str`  # 查询约束库并生成简报

### `core/conversation/missing_info_detector.py`

**class SeverityLevel((Enum))**
  _严重程度_

**class RequiredInfoConfig((TypedDict, total=False))**
  _必需信息配置_

**class MissingInfoDetector**
  _缺失信息检测器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化缺失信息检测器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `detect_missing(
        self, intent: str, entities: Dict[str, str], session_id: Optional[str] = None
    ) -> List[MissingInfo]`  # 检测缺失信息
  - `generate_missing_prompt(self, missing: List[MissingInfo]) -> str`  # 生成缺失信息提示
  - `check_file_exists(self, file_path: str) -> bool`  # 检查文件是否存在
  - `check_setting_complete(self, setting_type: str) -> Dict[str, Any]`  # 检查设定是否完整
  - `auto_fix(self, missing: List[MissingInfo]) -> Dict[str, Any]`  # 自动修复可修复的问题
  - `_try_auto_fix(self, missing_info: MissingInfo) -> bool`  # 尝试自动修复
  - `_generate_chapter_outline(self) -> bool`  # 生成章节大纲
  - `_create_faction_file(self) -> bool`  # 创建势力设定文件
  - `_create_default_worldview(self) -> bool`  # 创建默认世界观配置

- `def _check_character_exists(project_root: str, character_name: str) -> bool`  # 检查角色是否存在

- `def _check_novel_library(project_root: str) -> bool`  # 检查小说库配置

- `def _check_vector_database() -> bool`  # 检查向量数据库连接

### `core/conversation/progress_reporter.py`

**class ProgressReporter**
  _进度报告器_
  - `__init__(self)`  # 初始化进度报告器
  - `start_tracking(self) -> None`  # 开始跟踪
  - `record_phase_start(self, phase: int) -> None`  # 记录阶段开始时间
  - `get_phase_name(
        self, phase: int, workflow_type: str = "chapter_creation"
    ) -> str`  # 获取阶段名称
  - `get_phase_icon(self, phase_name: str) -> str`  # 获取阶段图标
  - `generate_progress(self, state: Dict[str, Any]) -> str`  # 生成进度报告
  - `_generate_progress_bar(self, current: int, total: int, width: int = 20) -> str`  # 生成进度条
  - `_calculate_elapsed_time(self, started_at: str) -> Optional[str]`  # 计算已用时间
  - `estimate_remaining_time(
        self, current: int, total: int, avg_phase_time: float = 60.0
    ) -> str`  # 估算剩余时间
  - `generate_phase_detail(
        self, phase: int, workflow_type: str = "chapter_creation"
    ) -> str`  # 生成阶段详细描述
  - `generate_full_report(
        self, state: Dict[str, Any], include_details: bool = True
    ) -> str`  # 生成完整进度报告
  - `generate_quick_status(self, state: Dict[str, Any]) -> str`  # 生成快速状态报告

### `core/conversation/technique_extractor.py`

**class TechniqueExtractor**
  _技法提炼器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化技法提炼器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `extract_from_content(self, content: str) -> TechniqueCandidate`  # 从用户提供的素材中提取技法
  - `extract_from_file(self, file_path: str) -> List[TechniqueCandidate]`  # 从文档文件中批量提取技法
  - `_resolve_file_path(self, file_path: str) -> Optional[Path]`  # 解析文件路径
  - `_read_document(self, path: Path) -> str`  # 读取文档内容
  - `_segment_document(self, content: str) -> List[str]`  # 分段处理长文档
  - `_deduplicate_candidates(
        self, candidates: List[TechniqueCandidate]
    ) -> List[TechniqueCandidate]`  # 去重相似技法
  - `_search_similar_techniques(self, content: str) -> List[Dict]`  # 检索相似技法（使用统一检索 API）
  - `_analyze_elements(self, content: str) -> List[str]`  # 分析技法要素
  - `_match_dimension(self, elements: List[str], content: str) -> str`  # 根据要素和内容归入维度
  - `_generate_name(self, elements: List[str], dimension: str) -> str`  # 生成技法名称
  - `_infer_scenes(self, content: str, dimension: str) -> List[str]`  # 推断适用场景
  - `_calculate_confidence(
        self, elements: List[str], similar_techniques: List[Dict]
    ) -> float`  # 计算置信度
  - `format_candidate_for_display(self, candidate: TechniqueCandidate) -> str`  # 格式化技法候选供用户确认
  - `confirm_and_save(self) -> bool`  # 确认并保存技法
  - `_write_technique_file(self, candidate: TechniqueCandidate) -> Optional[Path]`  # 写入技法文件
  - `_get_dimension_dir(self, dimension: str) -> str`  # 获取维度目录名
  - `_sync_to_vectorstore(self, candidate: TechniqueCandidate) -> bool`  # 同步到向量库

### `core/conversation/undo_manager.py`

**class OperationType((Enum))**
  _操作类型_

**class UndoManager**
  _撤销管理器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化撤销管理器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `_load_history(self) -> None`  # 加载历史记录
  - `_save_history(self) -> None`  # 保存历史记录
  - `record_operation(
        self,
        operation_type: OperationType,
        description: str,
        file_path: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        create_backup: bool = True,
    ) -> OperationRecord`  # 记录操作
  - `_create_backup(self, file_path: str, operation_id: str) -> Optional[str]`  # 创建文件备份
  - `undo_last(self) -> Optional[OperationRecord]`  # 撤销最近一次操作
  - `undo_operation(self, operation_id: str) -> Optional[OperationRecord]`  # 撤销指定操作
  - `_restore_backup(self, file_path: str, backup_path: str) -> bool`  # 从备份恢复文件
  - `get_history(self, limit: int = 10) -> List[OperationRecord]`  # 获取操作历史
  - `get_undoable_operations(self) -> List[OperationRecord]`  # 获取可撤销的操作
  - `generate_undo_prompt(self) -> str`  # 生成撤销提示
  - `clear_history(self) -> None`  # 清空历史记录
  - `clear_old_backups(self, days: int = 7) -> int`  # 清理旧备份文件

### `core/conversation/workflow_state_checker.py`

**class WorkflowStateChecker**
  _工作流状态检查器_
  - `__init__(self, project_root: Optional[str] = None)`  # 初始化状态检查器
  - `_detect_project_root(self) -> Path`  # 自动检测项目根目录
  - `check_pending_workflow(self, session_id: str) -> Optional[WorkflowState]`  # 检查是否有未完成的工作流
  - `save_state(self, session_id: str, state: Dict[str, Any]) -> bool`  # 保存工作流状态
  - `mark_completed(self, session_id: str) -> bool`  # 标记工作流已完成
  - `clear_state(self, session_id: str) -> bool`  # 清除工作流状态
  - `generate_resume_prompt(self, pending: WorkflowState) -> str`  # 生成恢复提示，附加场景摘要上下文（如有）。
  - `update_phase(
        self, session_id: str, phase: int, metadata: Optional[Dict[str, Any]] = None
    ) -> bool`  # 更新当前阶段
  - `get_all_pending_workflows(self) -> List[WorkflowState]`  # 获取所有未完成的工作流
  - `create_workflow(
        self,
        session_id: str,
        workflow_type: str,
        chapter: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowState`  # 创建新工作流

### `core/db_connection.py`
> 数据库连接管理器

**class DatabaseStatus((Enum))**
  _数据库状态_

**class DatabaseConnectionManager**
  _数据库连接管理器_
  - `__init__(
        self,
        qdrant_url: Optional[str] = None,
        cache_dir: Path = None,
        auto_check: bool = True,
    )`  # 初始化数据库连接管理器
  - `check_connection(self) -> ConnectionInfo`  # 检测数据库连接
  - `get_client(self)`  # 获取 Qdrant 客户端
  - `get_embedder(self)`  # 获取嵌入模型
  - `_load_local_cache(self) -> None`  # 加载本地缓存
  - `_save_local_cache(self, collection: str) -> None`  # 保存本地缓存
  - `save_to_cache(
        self, collection: str, item_id: str, data: Dict[str, Any]
    ) -> bool`  # 保存数据到缓存（降级模式使用）
  - `search_in_cache(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]`  # 从缓存搜索（降级模式使用）
  - `get_from_cache(self, collection: str, item_id: str) -> Optional[Dict[str, Any]]`  # 从缓存获取单个数据
  - `list_cache(self, collection: str) -> List[Dict[str, Any]]`  # 列出缓存中的所有数据
  - `get_cache_stats(self) -> Dict[str, int]`  # 获取缓存统计
  - `upsert(
        self,
        collection: str,
        item_id: str,
        vector: List[float],
        payload: Dict[str, Any],
    ) -> bool`  # 插入或更新数据（自动选择模式）
  - `search(
        self,
        collection: str,
        query: str,
        top_k: int = 5,
        filters: Dict[str, str] = None,
    ) -> List[Dict[str, Any]]`  # 搜索数据（自动选择模式）
  - `get_stats(self) -> Dict[str, Any]`  # 获取数据库统计信息

- `def get_db_manager(
    qdrant_url: Optional[str] = None,
    cache_dir: Path = None,
    auto_check: bool = True,
) -> DatabaseConnectionManager`  # 获取全局数据库连接管理器

### `core/error_handler.py`
> 统一错误处理框架

**class ErrorLevel((Enum))**
  _错误级别_

**class ErrorCode((Enum))**
  _错误码定义_
  - `__init__(self, code: str, message: str)`

**class CreationError((NovelError))**
  _创作模块错误_
  - `__init__(
        self, error_code: ErrorCode = ErrorCode.CREATION_WORKFLOW_FAILED, **kwargs
    )`

**class DatabaseError((NovelError))**
  _数据库错误_
  - `__init__(
        self, error_code: ErrorCode = ErrorCode.DATABASE_CONNECTION_FAILED, **kwargs
    )`

**class FileError((NovelError))**
  _文件错误_
  - `__init__(self, error_code: ErrorCode = ErrorCode.FILE_NOT_FOUND, **kwargs)`

**class ConfigError((NovelError))**
  _配置错误_
  - `__init__(self, error_code: ErrorCode = ErrorCode.CONFIG_NOT_FOUND, **kwargs)`

**class SkillError((NovelError))**
  _技能错误_
  - `__init__(self, error_code: ErrorCode = ErrorCode.SKILL_NOT_FOUND, **kwargs)`

**class SearchError((NovelError))**
  _检索错误_
  - `__init__(self, error_code: ErrorCode = ErrorCode.SEARCH_NO_RESULTS, **kwargs)`

**class SystemError((NovelError))**
  _系统错误_
  - `__init__(
        self, error_code: ErrorCode = ErrorCode.SYSTEM_INITIALIZATION_FAILED, **kwargs
    )`

**class ErrorContext**
  _错误处理上下文管理器_
  - `__init__(
        self,
        operation: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN,
        error_level: ErrorLevel = ErrorLevel.ERROR,
        suggestions: Optional[List[str]] = None,
        reraise: bool = False,
    )`
  - `__enter__(self)`
  - `__exit__(self, exc_type, exc_val, exc_tb)`

**class ErrorCollector**
  _错误收集器_
  - `__init__(self)`
  - `catch(self, operation: str, **kwargs) -> ErrorContext`  # 创建错误捕获上下文
  - `add_error(self, error: NovelError)`  # 添加错误
  - `summary(self) -> str`  # 错误摘要
  - `to_dict(self) -> Dict[str, Any]`  # 转换为字典

- `def handle_errors(
    default_return: Any = None,
    reraise: bool = False,
    log_trace: bool = True,
    suggestions: Optional[List[str]] = None,
)`  # 错误处理装饰器

- `def _log_error(error: NovelError)`  # 记录错误日志

- `def raise_error(
    error_code: ErrorCode,
    details: Optional[Dict] = None,
    suggestions: Optional[List[str]] = None,
)`  # 便捷函数：抛出错误

### `core/evaluation_criteria_loader.py`

**class EvaluationCriteriaLoader**
  _审核维度加载器_
  - `__init__(self)`  # 初始化
  - `load(self) -> Dict[str, int]`  # 从向量库加载审核标准
  - `_convert_to_executable(self, name: str, template_pattern: str) -> List[str]`  # 将模板pattern转换为可执行正则
  - `detect_prohibitions(self, text: str) -> List[ProhibitionMatch]`  # 检测文本中的禁止项
  - `get_technique_criteria(self, dimension: str = None) -> List[Dict]`  # 获取技法评估标准
  - `get_thresholds(self) -> Dict[str, Any]`  # 获取阈值配置
  - `format_prohibition_report(self, results: List[ProhibitionMatch]) -> str`  # 格式化禁止项检测报告

### `core/extraction/extraction_formatter.py`
> 将 ExtractionRunner 结果转换为中文对话回复

- `def format_start_response(result: dict, mode: str) -> str`

- `def format_status_response(status: dict) -> str`

### `core/extraction/extraction_runner.py`
> 提炼子进程生命周期管理

**class ExtractionRunner**
  _管理 .novel-extractor/run.py 子进程_
  - `__init__(self, extractor_dir: Optional[Path] = None)`
  - `is_running(self) -> bool`  # 检测提炼子进程是否存活；清理孤儿 PID 文件
  - `get_status(self) -> dict`  # 调用 run.py --status，返回原始输出和运行状态
  - `start(self, mode: str) -> dict`  # 启动提炼子进程。

- `def _default_extractor_dir() -> Path`

### `core/feedback/experience_writer.py`
> 章节经验写入器

**class ExperienceWriter**
  _章节经验写入器 - 让系统记住创作经验_
  - `__init__(self, log_dir: str = None)`  # 初始化经验写入器
  - `write_chapter_experience(
        self, chapter: int, experience: Dict[str, Any]
    ) -> Dict[str, Any]`  # 写入章节经验
  - `_extract_what_worked(self, experience: Dict) -> List[Dict[str, Any]]`  # 提取成功的做法
  - `_extract_what_didnt_work(self, experience: Dict) -> List[Dict[str, Any]]`  # 提取失败的做法
  - `_generate_insights(self, experience: Dict) -> List[Dict[str, Any]]`  # 生成洞察
  - `_extract_scene_techniques(self, techniques_used: List, scene: str) -> List[str]`  # 提取场景相关的技法
  - `_analyze_modification_patterns(self, user_modifications: List) -> List[str]`  # 分析用户修改模式
  - `retrieve_chapter_experience(
        self, chapter: int, scene_type: str = None, writer: str = None
    ) -> Optional[Dict[str, Any]]`  # 检索章节经验
  - `retrieve_recent_experiences(
        self,
        before_chapter: int,
        scene_type: str = None,
        writer: str = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索最近的章节经验
  - `_get_experience_dir(self) -> Path`  # 获取经验日志目录
  - `retrieve_scene_experience(self, scene_type: str) -> Dict[str, Any]`  # 按场景类型检索经验
  - `retrieve_technique_effectiveness(self, technique_name: str) -> Dict[str, Any]`  # 检索技法效果统计
  - `get_recent_forbidden_candidates(self, days: int = 30) -> List[Dict[str, Any]]`  # 获取最近的禁止项候选
  - `aggregate_lessons(
        self, scene_type: str = None, limit_chapters: int = 50
    ) -> Dict[str, Any]`  # 汇总经验教训

- `def _get_experience_schema()`

### `core/feedback/feedback_collector.py`
> 用户反馈收集器

**class FeedbackCollector**
  _用户反馈收集器 - 从用户修改中学习_
  - `__init__(self)`  # 初始化反馈收集器
  - `collect_from_rewrite(self, user_input: str) -> Dict[str, Any]`  # 从重写请求收集反馈
  - `collect_from_modification(
        self, user_input: str, original: str, modified: str
    ) -> Dict[str, Any]`  # 从用户修改操作收集反馈
  - `collect_from_explicit(self, user_input: str) -> Dict[str, Any]`  # 从显式反馈收集
  - `_identify_feedback_type(self, user_input: str) -> str`  # 识别反馈类型
  - `_extract_issue(self, user_input: str, feedback_type: str) -> str`  # 提取具体问题
  - `_extract_scene_type(self, user_input: str) -> Optional[str]`  # 提取场景类型
  - `_extract_writer(self, user_input: str) -> Optional[str]`  # 提取作家信息
  - `_is_significant_positive(self, user_input: str) -> bool`  # 判断是否是重要的正面反馈
  - `_analyze_diff(self, original: str, modified: str) -> Dict[str, Any]`  # 分析文本差异
  - `_identify_modification_type(
        self, original: str, modified: str, diff_analysis: Dict
    ) -> str`  # 识别修改类型
  - `_extract_lesson_from_modification(
        self, user_input: str, modification_type: str, diff_analysis: Dict
    ) -> str`  # 从修改中提取经验教训
  - `get_feedback_history(self, limit: int = 50) -> List[Dict]`  # 获取反馈历史
  - `clear_history(self)`  # 清空反馈历史
  - `save_history(self, path: Path) -> None`  # 持久化 feedback_history 到 JSON 文件
  - `load_history(self, path: Path) -> None`  # 从 JSON 文件恢复 feedback_history；文件不存在时静默跳过

### `core/feedback/feedback_dispatcher.py`

**class FeedbackDispatcher**
  _统一反馈调度器_
  - `__init__(self, history_path: Optional[Path] = None)`
  - `dispatch(
        self,
        feedback_category: str,
        user_input: str,
        scene_type_lookup: Optional[Callable[[str], str]] = None,
        is_overturn: bool = False,
    ) -> Dict[str, Any]`  # 路由反馈到对应子系统
  - `_dispatch_to_resonance(
        self,
        user_input: str,
        scene_type_lookup: Optional[Callable],
        is_overturn: bool,
    ) -> Dict[str, Any]`  # 灵感引擎反馈 → resonance_feedback
  - `_dispatch_to_collector(self, user_input: str) -> Dict[str, Any]`  # 写作质量反馈 → FeedbackCollector

### `core/feedback/feedback_processor.py`
> 反馈处理器

**class FeedbackProcessor**
  _反馈处理器 - 处理反馈并提取有价值信息_
  - `__init__(self, thresholds: Dict[str, float] = None)`  # 初始化反馈处理器
  - `process_feedback(self, feedback: Dict[str, Any]) -> Dict[str, Any]`  # 处理反馈
  - `_extract_improvement_points(self, feedback: Dict) -> List[str]`  # 提取改进点
  - `_calculate_severity(self, feedback: Dict, improvement_points: List) -> str`  # 计算严重程度
  - `_map_to_technique(
        self, feedback: Dict, improvement_points: List
    ) -> Dict[str, Any]`  # 映射到技法
  - `_extract_forbidden_items(self, feedback: Dict) -> List[str]`  # 提取禁止项
  - `_is_actionable(
        self, feedback: Dict, improvement_points: List, severity: str
    ) -> bool`  # 判断是否可操作
  - `_parse_lesson(self, lesson: str) -> List[str]`  # 解析经验教训
  - `_extract_keywords_from_input(self, raw_input: str) -> List[str]`  # 从用户输入提取关键词
  - `_get_scene_technique_mapping(self, scene_type: str) -> Optional[Dict]`  # 获取场景技法映射
  - `_get_writer_technique_mapping(self, writer: str) -> Optional[Dict]`  # 获取作家技法映射
  - `_count_pattern_in_history(self, pattern: str) -> int`  # 计算模式在历史中出现的次数
  - `get_improvement_summary(self) -> Dict[str, Any]`  # 获取改进点汇总
  - `get_processed_history(self, limit: int = 50) -> List[Dict]`  # 获取处理历史
  - `clear_history(self)`  # 清空处理历史
  - `analyze_history_file(self, path) -> dict`  # 从 feedback_history.json 读取并分析反馈模式

### `core/health_check.py`
> 系统健康检查模块

**class HealthStatus((Enum))**
  _健康状态_

**class HealthChecker**
  _系统健康检查器_
  - `__init__(self, project_root: str = None)`
  - `check_all(self, quick: bool = False) -> HealthReport`  # 执行所有健康检查
  - `check_database(self) -> HealthCheckResult`  # 检查数据库状态
  - `check_skills(self) -> HealthCheckResult`  # 检查技能文件
  - `check_config(self) -> HealthCheckResult`  # 检查配置文件
  - `check_settings(self) -> HealthCheckResult`  # 检查设定文件
  - `check_directories(self) -> HealthCheckResult`  # 检查目录结构
  - `_determine_overall_status(
        self, results: List[HealthCheckResult]
    ) -> HealthStatus`  # 确定总体状态
  - `add_check(self, name: str, check_func: Callable)`  # 添加自定义检查
  - `quick_check(self) -> bool`  # 快速检查（返回布尔值）

- `def run_health_check(quick: bool = False)`  # 运行健康检查（CLI 入口）

### `core/inspiration/appraisal_agent.py`

**class AppraisalParseError((Exception))**

- `def build_appraisal_spec(
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    memory_point_count: int,
    retrieved_references: Optional[List[Dict[str, Any]]] = None,
    structural_summary: Optional[str] = None,
    cold_threshold: int = 50,
    growing_threshold: int = 300,
) -> Dict[str, Any]`  # 构造鉴赏师调用规格

- `def _candidates_block(candidates: List[Dict[str, Any]]) -> str`

- `def _scene_block(scene_context: Dict[str, Any]) -> str`

- `def _build_cold_prompt(candidates, scene_context) -> str`

- `def _build_growing_prompt(candidates, scene_context, refs) -> str`

- `def _build_mature_prompt(candidates, scene_context, refs, structural_summary) -> str`

- `def _format_ref(r: Dict[str, Any]) -> str`

- `def parse_appraisal_response(raw: str) -> AppraisalResult`  # 解析鉴赏师 Skill 输出

### `core/inspiration/audit_trigger.py`

**class AuditTrigger**
  _审计触发器_
  - `__init__(
        self,
        appraisal_interval: int = 10,
        overturn_threshold: int = 10,
    )`  # Args:
  - `record_appraisal(self, result: Dict[str, Any]) -> Optional[str]`  # 记录一次鉴赏结果
  - `record_overturn(self) -> Optional[str]`  # 记录一次推翻事件
  - `_run_appraisal_audit(self) -> str`  # 分析当前批次鉴赏日志，生成退化审计报告

### `core/inspiration/constraint_library.py`

**class ConstraintLibrary**
  _反模板约束库。_
  - `__init__(self, path: Optional[Path] = None)`
  - `_load(self) -> Dict[str, Any]`  # 加载约束 JSON 文件
  - `list_active(self) -> List[Dict[str, Any]]`  # 所有 status='active' 的约束
  - `filter_by_scene_type(self, scene_type: str) -> List[Dict[str, Any]]`  # 筛选可兼容指定场景类型的活跃约束
  - `pick_for_variants(
        self,
        scene_type: str,
        n: int,
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]`  # 为 N 个变体抽取约束，加权随机（保证类别多样性）
  - `get_by_id(self, constraint_id: str) -> Optional[Dict[str, Any]]`  # 按 ID 查找约束
  - `get_version(self) -> str`  # 获取约束库版本
  - `count_total(self) -> int`  # 统计约束总数（含 disabled）
  - `count_active(self) -> int`  # 统计活跃约束数
  - `list_categories(self) -> List[str]`  # 列出所有约束类别
  - `as_menu(self, scene_type: Optional[str] = None) -> List[Dict[str, Any]]`  # 返回活跃约束的菜单视图(不随机、不采样)。
  - `count_by_category(self) -> Dict[str, int]`  # 按类别统计活跃约束数(disabled 不计入)。
  - `search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]`  # 对活跃约束的 constraint_text 做 case-insensitive 子串搜索。
  - `format_menu_text(self, scene_type: Optional[str] = None) -> str`  # 生成中文 Markdown 菜单,供鉴赏师 prompt 注入。

- `def _default_constraints_path() -> Path`  # 从配置获取约束文件路径（而非硬编码相对路径）

### `core/inspiration/creative_contract.py`
> 创意契约(Creative Contract)数据模型。

**class ContractValidationError((ValueError))**
  _契约数据校验失败。_

- `def generate_contract_id() -> str`  # 生成 contract_id,格式 cc_YYYYMMDD_<6hex>,日期用 Shanghai 时区。

### `core/inspiration/dispatcher.py`
> 派单器(Dispatcher)— v2 阶段 5.6 核心纯函数层。

**class DispatcherError((ContractValidationError))**
  _派单器特有的错误(复用 ContractValidationError 的 ValueError 血统)。_

- `def dispatch(contract: CreativeContract) -> List[DispatchPackage]`  # 把一份已校验契约转成每位写手的派单包列表。

- `def _format_preserve_block(*, preserve_item: PreserveItem, task: str) -> str`  # 为单条 PreserveItem 渲染 v2 §5 模板中"项目"块(Chinese,Q2 嵌套)。

- `def _build_prompt_increment(
    *,
    contract_id: str,
    writer: str,
    pairs: List,  # List[Tuple[PreserveItem, str]]
) -> str`  # 拼接整块派单 prompt:header + 多个项目块 + footer。

- `def _group_assignments_by_writer(
    assignments: List[WriterAssignment],
) -> Dict[str, List[WriterAssignment]]`  # 按 writer 分组并保持原列表中的相对顺序。

### `core/inspiration/embedder.py`

- `def _load_model()`  # 加载 BGE-M3 模型（首次调用）

- `def _get_model()`  # 获取模型实例（懒加载）

- `def embed_text(text: str) -> List[float]`  # 将文本编码为 1024 维 dense vector

- `def embed_scene_context(scene_context: dict) -> List[float]`  # 将场景上下文 dict 拼接为文本后编码

### `core/inspiration/escalation_dialogue.py`

- `def format_rater_vs_evaluator_conflict(
    rater_selected_id: str,
    ignition_point: str,
    evaluator_violation: str,
    other_candidates: List[Dict[str, Any]],
) -> str`  # 格式化鉴赏师与评估师冲突的升级对话

- `def format_all_variants_failed(
    candidate_ids: List[str],
    common_flaw: str,
) -> str`  # 格式化所有变体被评估师打回的升级对话

- `def format_appraisal_audit(
    appraisal_count: int,
    vague_count: int,
    baseline_win_count: int,
) -> str`  # 格式化鉴赏师退化审计报告

- `def format_overturn_audit(
    overturn_count: int,
) -> str`  # 格式化推翻事件审计报告

- `def format_stage6_three_choice(
    item_summaries: List[Dict[str, str]],
    failed_dimensions: List[str],
    consecutive_fail_count: int,
) -> str`  # 格式化阶段 6 整章评估连续失败触发的三选升级对话。

- `def parse_stage6_choice(user_input: str) -> Tuple[str, Optional[str]]`  # 解析作者对 format_stage6_three_choice 的回复。

### `core/inspiration/evaluator_exemption.py`

**class ExemptionBuildError((ValueError))**
  _构建豁免索引时发现不合法数据(通常是 Q4 违反)。_

- `def build_exemption_map(contract: CreativeContract) -> ExemptionMap`  # 从契约抽取段落级豁免索引。

- `def is_exempt(
    exemption_map: ExemptionMap,
    paragraph_index: int,
    dimension: str,
    sub_item: str,
) -> bool`  # 查询 (段落, 维度, 子项) 是否被豁免。

- `def format_exemption_report(exemption_map: ExemptionMap) -> str`  # 生成可读的中文豁免报告。段落升序,维度按名称升序,子项按名称升序。

### `core/inspiration/memory_point_sync.py`

**class MemoryPointSync**
  _记忆点库 CRUD_
  - `__init__(
        self, client: Optional[QdrantClient] = None, qdrant_path: Optional[str] = None
    )`
  - `ensure_collection(self) -> None`  # 确保 memory_points_v1 collection 存在，不存在则自动创建。
  - `create(
        self, payload: Dict[str, Any], embedding: Optional[List[float]] = None
    ) -> str`  # 创建记忆点
  - `count(self) -> int`  # 记忆点总数
  - `count_overturn_events(self) -> int`  # 推翻事件数
  - `search_similar(
        self,
        embedding: List[float],
        scene_type: Optional[str] = None,
        polarity: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]`  # 检索相似记忆点
  - `list_recent(
        self,
        polarity: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]`  # 按极性列出最近的记忆点（按 created_at 降序，不需要 embedding）。
  - `search_by_writer(
        self,
        embedding: List[float],
        writer_agent: str,
        scene_type: Optional[str] = None,
        polarity: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]`  # 按作家角色检索记忆点。
  - `list_recent_by_writer(
        self,
        polarity: str,
        writer_agent: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]`  # 按作家角色列出最近记忆点（created_at 降序）。
  - `get_stats(self) -> Dict[str, Any]`  # 获取记忆点库统计
  - `_determine_phase(self, count: int) -> str`  # 根据记忆点数判断鉴赏师阶段

### `core/inspiration/resonance_feedback.py`

- `def _extract_signal(user_input: str) -> Dict[str, Any]`  # 从自然语言提取情绪信号

- `def _extract_note(user_input: str) -> str`  # 保留原话作为备注

- `def _resolve_chapter_path(chapter_ref: str) -> Optional[Path]`  # 章节引用解析为文件路径

- `def handle_reader_feedback(
    user_input: str,
    scene_type_lookup: Callable[[str], str],
    sync: Optional[MemoryPointSync] = None,
    is_overturn: bool = False,
) -> Dict[str, Any]`  # 处理 reader_moment_feedback 意图

### `core/inspiration/segment_locator.py`

- `def _split_paragraphs(text: str) -> List[str]`  # 按双空行或单空行分段，过滤空段

- `def locate_segment(
    chapter_file: Path,
    location_hint: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Optional[Dict[str, Any]]`  # 定位章节中的段落

- `def _hint_to_index(hint: str, total: int) -> Optional[int]`  # 位置词转换为段落索引

- `def _in_position_range(index: int, total: int, hint: str) -> bool`  # 判断索引是否落在 hint 描述的区间

### `core/inspiration/stage5_5.py`

**class ConnoisseurParseError((ValueError))**
  _鉴赏师 JSON 解析失败。_

- `def _render_menu(menu_items: List[Dict[str, Any]]) -> str`  # 将约束菜单列表渲染为 SKILL.md §5.5.2 要求的分类文本块。

- `def _render_samples(samples: List[Dict[str, Any]], label: str) -> str`  # 将记忆点列表渲染为审美指纹文本块。

- `def build_connoisseur_prompt(
    chapter_text: str,
    chapter_ref: str,
    menu_items: List[Dict[str, Any]],
    positive_samples: List[Dict[str, Any]],
    negative_samples: List[Dict[str, Any]],
) -> Dict[str, Any]`  # 构造发给 novelist-connoisseur SKILL 的 prompt 规格。

- `def parse_connoisseur_response(raw_json: str) -> ConnoisseurResponse`  # 解析鉴赏师返回的 JSON 字符串为 ConnoisseurResponse。

- `def suggestions_to_preserve_candidates(
    suggestions: List[ConnoisseurSuggestion],
) -> List[PreserveItem]`  # 将鉴赏师建议列表转为 PreserveItem 候选（供作者采纳/驳回）。

- `def build_creative_contract(
    accepted_items: List[PreserveItem],
    rejected_items: List[RejectedItem],
    chapter_ref: str,
    negotiation_log: Optional[List[NegotiationTurn]] = None,
    skipped_by_author: bool = False,
) -> CreativeContract`  # 根据作者采纳决策生成并校验 CreativeContract。

- `def build_stage5_5_prompt_with_real_data(
    chapter_text: str,
    chapter_ref: str,
    scene_type: Optional[str] = None,
    positive_top_k: int = 5,
    negative_top_k: int = 5,
) -> Dict[str, Any]`  # build_connoisseur_prompt 的集成入口：自动从 ConstraintLibrary 和 MemoryPointSync 加载真实数据。

### `core/inspiration/status_reporter.py`

- `def _get_thresholds()`  # 从配置获取阈值

- `def report_status(sync: Optional[MemoryPointSync] = None) -> str`  # 生成状态报告文本

### `core/inspiration/structural_analyzer.py`

- `def analyze(text: str) -> Dict[str, Any]`  # 提取段落结构特征

- `def _safe_defaults() -> Dict[str, Any]`

- `def _split_sentences(text: str) -> List[str]`

- `def _imagery_density(text: str) -> str`  # 统计意象关键词密度，分桶为 low/medium/high

- `def _perspective(text: str) -> str`  # 粗略判断视角

- `def _rhythm_pattern(lens: List[int]) -> str`  # 根据句长序列匹配节奏模板

- `def _verb_density(text: str) -> float`  # 粗略动词密度（仅基于常见动词词典）

- `def _adjective_ratio(text: str) -> float`  # 粗略形容词比例（仅基于常见形容词词典）

### `core/inspiration/workflow_bridge.py`

- `def _resolve_writer_skill(chinese_name: str) -> str`  # 中文作家名映射为 Skill 名

- `def phase1_dispatch(
    scene_type: str,
    scene_context: Dict[str, Any],
    original_writers: List[str],
    config: Dict[str, Any],
    seed: Optional[int] = None,
) -> Dict[str, Any]`  # Stage 4 Phase 1 分发器（v2：变体模式已移除，始终返回原始写手列表）

- `def _embed_scene_context(scene_context: Dict[str, Any]) -> List[float]`  # 将场景上下文编码为向量（调用 BGE-M3）

- `def _retrieve_references_for_appraisal(
    sync: MemoryPointSync,
    embedding: List[float],
    scene_type: str,
    top_k: int = 3,
) -> List[Dict[str, Any]]`  # 检索正负向记忆点，供鉴赏师 prompt 注入

- `def select_winner_spec(
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    memory_point_count: Optional[int] = None,
    retrieved_references: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]`  # 构造鉴赏师选择规格（含 E 机制记忆点注入）

- `def execute_variants(
    specs: List[Dict[str, Any]],
    writer_caller: Any,
) -> List[Dict[str, Any]]`  # 将变体规格列表执行为带文本的候选列表

- `def record_winner(
    appraisal: Any,
    candidates: List[Dict[str, Any]],
    scene_context: Dict[str, Any],
    sync: Optional[Any] = None,
) -> Optional[str]`  # 将鉴赏师选择结果写入记忆点库

### `core/inspiration/writer_memory_retriever.py`

- `def retrieve_writer_memory(
    writer_agent: str,
    current_scene_type: str,
    embedding: List[float],
    sync: Optional[MemoryPointSync] = None,
) -> Dict[str, Any]`  # 检索作家专属记忆。

### `core/lifecycle/config_version_control.py`
> 配置版本控制 - ConfigVersionControl

**class ConfigVersionControl**
  _配置版本控制_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化配置版本控制
  - `_ensure_storage(self) -> None`  # 确保存储目录和索引文件存在
  - `_load_index(self) -> Dict[str, Any]`  # 加载快照索引
  - `_save_index(self, index: Dict[str, Any]) -> None`  # 保存快照索引
  - `_calculate_checksum(self, file_path: Path) -> str`  # 计算文件校验和
  - `_collect_config_files(self) -> Dict[str, Tuple[Path, str]]`  # 收集所有配置文件
  - `create_snapshot(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_auto: bool = False,
    ) -> str`  # 创建配置快照
  - `restore_snapshot(
        self,
        snapshot_id: str,
        backup_current: bool = True,
    ) -> Dict[str, Any]`  # 恢复配置快照
  - `list_snapshots(
        self,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[ConfigSnapshot]`  # 列出配置快照
  - `diff_snapshots(
        self,
        snapshot_id1: str,
        snapshot_id2: str,
    ) -> List[SnapshotDiff]`  # 对比两个快照
  - `_compare_json(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any],
        prefix: str,
    ) -> List[SnapshotDiff]`  # 递归对比两个JSON对象
  - `_estimate_lines(self, file_path: Path) -> int`  # 估算文件行数
  - `auto_snapshot(self) -> Optional[str]`  # 自动快照（检测配置变更时）
  - `delete_snapshot(self, snapshot_id: str) -> bool`  # 删除快照
  - `get_snapshot(self, snapshot_id: str) -> Optional[ConfigSnapshot]`  # 获取快照详情
  - `cleanup_old_snapshots(
        self, keep_days: int = 30, keep_manual: bool = True
    ) -> int`  # 清理旧快照

- `def get_config_version_control(
    project_root: Optional[Path] = None,
) -> ConfigVersionControl`  # 获取配置版本控制实例

### `core/lifecycle/contract_lifecycle.py`
> 契约生命周期管理 - ContractLifecycle

**class ConsistencyRule((Enum))**
  _12大一致性规则_

**class ViolationSeverity((Enum))**
  _违规严重程度_

**class ContractLifecycle**
  _契约生命周期管理_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化契约生命周期
  - `_load_realm_orders(self) -> Dict[str, list]`  # 加载所有力量体系的境界配置
  - `get_realm_order_for_character(self, character_name: str) -> list`  # 根据角色的力量体系获取对应的境界顺序
  - `_ensure_storage(self) -> None`  # 确保存储目录和索引文件存在
  - `_load_index(self) -> Dict[str, Any]`  # 加载契约索引
  - `_save_index(self, index: Dict[str, Any]) -> None`  # 保存契约索引
  - `_load_worldview_settings(self) -> Dict[str, Any]`  # 加载世界观设定
  - `_parse_character_file(self, file_path: Path) -> Dict[str, Any]`  # 解析人物文件
  - `_parse_power_file(self, file_path: Path) -> Dict[str, Any]`  # 解析力量体系文件
  - `_parse_timeline_file(self, file_path: Path) -> Dict[str, Any]`  # 解析时间线文件
  - `_parse_faction_file(self, file_path: Path) -> Dict[str, Any]`  # 解析势力文件
  - `create_contract(
        self,
        scene_id: str,
        contract_data: Dict[str, Any],
        auto_validate: bool = True,
    ) -> SceneContract`  # 创建场景契约
  - `_build_rules(self, contract_data: Dict[str, Any]) -> List[ContractRule]`  # 根据契约数据构建规则
  - `validate_contract(self, contract: SceneContract) -> List[Violation]`  # 验证契约
  - `_validate_rule(
        self,
        contract: SceneContract,
        rule: ContractRule,
    ) -> List[Violation]`  # 验证单个规则
  - `_validate_character(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证角色一致性
  - `_validate_timeline(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证时间线一致性
  - `_validate_power_system(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证力量体系一致性
  - `_validate_geography(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证地理位置一致性
  - `_validate_information(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证情报边界一致性
  - `_validate_resource(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证资源追踪一致性
  - `_validate_foreshadow(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证伏笔追踪一致性
  - `_validate_promise(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证承诺追踪一致性
  - `_validate_language_style(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证语言风格一致性
  - `_validate_terminology(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证术语一致性
  - `_validate_theme(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证主题一致性
  - `_validate_tone(
        self,
        contract: SceneContract,
        constraint: Dict[str, Any],
    ) -> List[Violation]`  # 验证基调一致性
  - `check_contract_compliance(
        self,
        scene_id: str,
        content: str,
    ) -> List[Violation]`  # 检查内容是否符合契约
  - `_check_content_rule(
        self,
        content: str,
        contract: SceneContract,
        rule: ContractRule,
    ) -> List[Violation]`  # 检查内容是否符合规则
  - `resolve_conflicts(
        self,
        contracts: List[SceneContract],
    ) -> Dict[str, Any]`  # 解决契约冲突
  - `_check_character_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]`  # 检查角色状态冲突
  - `_check_time_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]`  # 检查时间冲突
  - `_check_geography_conflict(
        self,
        contract1: SceneContract,
        contract2: SceneContract,
    ) -> Optional[Dict[str, Any]]`  # 检查地理冲突
  - `_generate_resolution_plan(
        self,
        conflicts: List[Dict[str, Any]],
        contracts: List[SceneContract],
    ) -> Dict[str, Any]`  # 生成冲突解决方案
  - `_save_contract(self, contract: SceneContract) -> None`  # 保存契约
  - `_load_contract(self, scene_id: str) -> Optional[SceneContract]`  # 加载契约
  - `_update_index(self, contract: SceneContract) -> None`  # 更新契约索引
  - `complete_contract(self, scene_id: str) -> bool`  # 完成契约（场景创作完成）
  - `get_contract(self, scene_id: str) -> Optional[SceneContract]`  # 获取场景契约
  - `list_active_contracts(self) -> List[SceneContract]`  # 列出所有活动契约

- `def get_contract_lifecycle(project_root: Optional[Path] = None) -> ContractLifecycle`  # 获取契约生命周期管理实例

### `core/lifecycle/technique_tracker.py`
> 技法追踪器 - TechniqueTracker

**class TechniqueTracker**
  _技法追踪器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化技法追踪器
  - `_ensure_storage(self) -> None`  # 确保存储文件存在
  - `_load_data(self) -> Dict[str, Any]`  # 加载存储数据
  - `_save_data(self, data: Dict[str, Any]) -> None`  # 保存存储数据
  - `track_usage(
        self,
        technique_id: str,
        context: Dict[str, Any],
        scene_type: Optional[str] = None,
        writer: Optional[str] = None,
        chapter: Optional[int] = None,
        effectiveness: Optional[float] = None,
        feedback: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> str`  # 追踪技法使用
  - `_update_stats(
        self, data: Dict[str, Any], technique_id: str, usage: TechniqueUsage
    ) -> None`  # 更新技法统计
  - `get_usage_stats(self, technique_id: str) -> TechniqueStats`  # 获取技法使用统计
  - `get_effectiveness_score(self, technique_id: str) -> float`  # 获取技法效果评分
  - `recommend_techniques(
        self,
        context: Dict[str, Any],
        dimension: Optional[str] = None,
        scene_type: Optional[str] = None,
        top_k: int = 5,
        min_effectiveness: float = 0.3,
    ) -> List[Tuple[str, float, TechniqueStats]]`  # 推荐技法
  - `_calculate_recommendation_score(
        self,
        technique_id: str,
        stat: Dict[str, Any],
        context: Dict[str, Any],
        scene_type: Optional[str] = None,
    ) -> float`  # 计算技法推荐评分
  - `_context_overlap(
        self, context1: Dict[str, Any], context2: Dict[str, Any]
    ) -> float`  # 计算两个上下文的相似度
  - `get_dimension_stats(self, dimension: str) -> Dict[str, TechniqueStats]`  # 获取某个维度的所有技法统计
  - `clear_old_records(self, days: int = 30) -> int`  # 清理旧记录

- `def get_technique_tracker(project_root: Optional[Path] = None) -> TechniqueTracker`  # 获取技法追踪器实例

### `core/logging_utils.py`

**class JSONLogger**
  _写入 .jsonl 文件的结构化日志器。_
  - `__init__(self, log_path: Path, module_name: str) -> None`
  - `log(self, level: str, message: str, **kwargs: object) -> None`  # 写入一条 JSON 日志行。自动注入 trace_id（如有）。
  - `info(self, message: str, **kwargs: object) -> None`
  - `warning(self, message: str, **kwargs: object) -> None`
  - `error(self, message: str, **kwargs: object) -> None`

- `def get_logger(module_name: str, log_dir: str = "logs") -> JSONLogger`  # 获取模块日志器（自动命名 .jsonl 文件）

### `core/metrics.py`

- `def start_metrics_server(port: int = 9090) -> bool`  # 启动 Prometheus HTTP 服务

- `def get_metrics_port() -> int`  # 从环境变量获取 Prometheus 端口

- `def record_retrieval(
    source: str,
    dimension: Optional[str] = None,
    latency_seconds: float = 0.0,
    results_count: int = 0
) -> None`  # 记录一次检索的指标

- `def record_evaluation(
    dimension: str,
    score: float,
    chapter: str = "",
    result: str = "pass"
) -> None`  # 记录一次评估的指标

- `def update_qdrant_health(healthy: bool) -> None`  # 更新 Qdrant 健康状态

- `def update_qdrant_collections(count: int) -> None`  # 更新 Qdrant 集合数量

- `def record_workflow_stage(
    stage: str,
    latency_seconds: float,
    success: bool = True
) -> None`  # 记录工作流阶段执行

### `core/model_manager.py`

**class ModelManager**
  _模型版本管理器_
  - `__init__(self, config_path: Optional[Path] = None)`  # 初始化模型管理器
  - `get_current_embedding_model(self) -> Dict[str, Any]`  # 获取当前嵌入模型配置
  - `list_available_embedding_models(self) -> List[Dict[str, Any]]`  # 列出所有可用的嵌入模型
  - `get_embedding_model_path(self, model_id: Optional[str] = None) -> Optional[Path]`  # 获取嵌入模型路径
  - `get_current_llm_model(self) -> Dict[str, Any]`  # 获取当前 LLM 模型配置
  - `list_available_llm_models(self) -> List[Dict[str, Any]]`  # 列出所有可用的 LLM 模型
  - `benchmark_embedding_model(
        self, 
        model_id: str,
        benchmark_path: Optional[Path] = None
    ) -> Dict[str, Any]`  # 运行嵌入模型基准测试
  - `switch_embedding_model(self, new_model_id: str) -> bool`  # 切换嵌入模型
  - `get_model_info_summary(self) -> str`  # 获取模型信息摘要

- `def get_model_manager() -> ModelManager`  # 获取全局模型管理器

### `core/parsing/chapter_outline_parser.py`
> 章节大纲解析器

**class ChapterOutlineParser**
  _章节大纲 Markdown 解析器_
  - `parse(self, content: str) -> Dict[str, Any]`  # 解析大纲文本
  - `parse_file(self, file_path) -> Optional[Dict[str, Any]]`  # 从文件解析大纲
  - `find_outline_file(self, chapter_num: int, outline_dir) -> Optional[Path]`  # 在大纲目录中查找指定章节的大纲文件
  - `_parse_table(self, content: str, section_name: str) -> Dict[str, str]`  # 解析 Markdown 表格为字典
  - `_parse_structure_table(self, content: str) -> List[Dict[str, str]]`  # 解析章节结构表格为列表
  - `_parse_scenes(self, content: str) -> List[Dict[str, Any]]`  # 解析详细场景设计
  - `_parse_scene(self, title: str, body: str) -> Dict[str, Any]`  # 解析单个场景
  - `_build_summary(self, result: Dict[str, Any]) -> str`  # 生成适合注入 AI 上下文的大纲摘要

### `core/path_manager.py`
> 路径管理器

**class PathManager**
  _路径管理器_
  - `__init__(self, config: Optional[ConfigManager] = None)`  # 初始化路径管理器
  - `get_technique_dimension_dir(self, dimension: str) -> Path`  # 获取技法维度目录
  - `get_chapter_file(self, chapter_name: str) -> Path`  # 获取章节文件路径
  - `get_chapter_outline(self, chapter_name: str) -> Path`  # 获取章节大纲文件路径
  - `get_module_dir(self, module_name: str) -> Path`  # 获取模块目录路径
  - `get_log_file(self, log_name: str) -> Path`  # 获取日志文件路径
  - `get_custom_resource(self, resource_id: str) -> Optional[Path]`  # 获取自定义资源路径
  - `add_custom_resource(self, resource_id: str, path: Path) -> None`  # 添加自定义资源路径
  - `detect_project_root(self) -> Path`  # 检测项目根目录
  - `list_setting_files(self) -> List[Path]`  # 列出所有设定文件
  - `list_technique_files(self) -> List[Path]`  # 列出所有技法文件
  - `list_chapter_files(self) -> List[Path]`  # 列出所有章节文件
  - `ensure_path(self, path: Path) -> Path`  # 确保路径存在
  - `resolve_relative_path(self, relative_path: str) -> Path`  # 将相对路径转换为绝对路径

- `def get_path_manager(config: Optional[ConfigManager] = None) -> PathManager`  # 获取全局路径管理实例

### `core/retrieval/unified_retrieval_api.py`

**class UnifiedRetrievalAPI**
  _统一检索API_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        weight_preset: str = "general",
        use_cache: bool = True,
        cache_ttl: int = 300,
    )`  # 初始化统一检索API
  - `_get_cache_key(
        self,
        query: str,
        source: str,
        filters: Optional[Dict] = None,
        top_k: int = 10,
    ) -> str`  # 生成缓存键
  - `_get_cached(self, cache_key: str) -> Optional[Any]`  # 获取缓存结果
  - `_set_cache(self, cache_key: str, result: Any)`  # 设置缓存
  - `clear_cache(self)`  # 清除缓存
  - `retrieve(
        self,
        query: str,
        sources: List[str] = ["novel", "technique", "case"],
        filters: Optional[Dict] = None,
        top_k: int = 5,
        use_rerank: bool = True,
    ) -> Dict[str, List[Dict]]`  # 统一入口 - 同时检索多个数据源
  - `search_techniques(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 创作技法检索（兼容现有接口）
  - `search_by_keywords(
        self,
        keywords: list,
        dimension: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 关键词列表合并为查询串后检索技法
  - `search_worldview_techniques(
        self,
        query: str = "世界观构建",
        dimension: str = "世界观维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索世界观维度技法
  - `get_worldview_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 获取世界观专家级技法（史诗级世界观 + 力量体系）
  - `search_plot_techniques(
        self,
        query: str = "剧情推进",
        dimension: str = "剧情维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索剧情维度技法
  - `search_foreshadowing_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 检索伏笔设置技法
  - `search_suspense_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 检索悬念制造技法
  - `search_reversal_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 检索反转技法
  - `get_plot_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 获取剧情专家级技法
  - `search_poetry_techniques(
        self,
        query: str = "氛围意境",
        dimension: str = "氛围意境维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索氛围意境维度技法
  - `search_poetry_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]`  # 关键词检索氛围意境技法
  - `get_poetry_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 获取氛围意境专家级技法
  - `search_character_techniques(
        self,
        query: str = "人物刻画",
        dimension: str = "人物维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索人物维度技法
  - `search_emotion_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 检索情感描写技法
  - `get_character_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]`  # 获取人物塑造专家级技法
  - `search_battle_techniques(
        self,
        query: str = "战斗描写",
        dimension: str = "战斗冲突维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索战斗冲突维度技法
  - `search_battle_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]`  # 关键词检索战斗技法
  - `get_battle_expert_techniques(
        self, power_system: str = "", top_k: int = 5
    ) -> List[Dict[str, Any]]`  # 获取战斗冲突专家级技法，可按力量体系过滤
  - `search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 标杆案例检索（兼容现有接口）
  - `search_worldview_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 世界观/势力案例检索（苍澜专用）
  - `search_plot_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 剧情/伏笔案例检索（玄一专用）
  - `search_poetry_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 意境/诗意案例检索（云溪专用）
  - `search_character_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 人物/情感案例检索（墨言专用）
  - `search_battle_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]`  # 战斗/力量案例检索（剑尘专用）
  - `search_judicial_cases(
        self,
        query: str,
        section: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.4,
    ) -> List[Dict[str, Any]]`  # 司法案例检索（真实犯罪案例写作素材）
  - `search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 小说设定检索（兼容现有接口）
  - `search_power_vocabulary(
        self,
        query: str,
        power_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 力量词汇检索
  - `search_dialogue_style(
        self,
        query: str,
        faction: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 对话风格检索
  - `search_emotion_arc(
        self,
        query: str,
        arc_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 情感弧线检索
  - `search_worldview_element(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 世界观元素检索
  - `search_character_relation(
        self,
        query: str,
        relation_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 人物关系检索
  - `search_author_style(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 作者风格检索
  - `search_foreshadow_pair(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 伏笔配对检索
  - `search_power_cost(
        self,
        query: str,
        power_type: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 力量代价检索
  - `set_weight_preset(self, preset: str)`  # 设置权重预设
  - `get_stats(self) -> Dict[str, Any]`  # 获取数据库统计信息
  - `list_dimensions(self) -> List[str]`  # 列出所有技法维度
  - `list_entity_types(self) -> List[str]`  # 列出所有实体类型
  - `list_power_types(self) -> List[str]`  # 列出所有力量类型
  - `list_faction_types(self) -> List[str]`  # 列出所有派系类型
  - `list_arc_types(self) -> List[str]`  # 列出所有情感弧线类型
  - `list_characters(self) -> List[str]`  # 列出所有角色名称
  - `list_factions(self) -> List[str]`  # 列出所有势力名称
  - `get_character(self, name: str) -> Optional[Dict[str, Any]]`  # 获取角色设定
  - `get_faction(self, name: str) -> Optional[Dict[str, Any]]`  # 获取势力设定

### `core/tracing.py`

**class TraceContext**
  _追踪上下文管理器_
  - `__init__(self, trace_id: Optional[str] = None)`  # 初始化追踪上下文
  - `__enter__(self) -> str`  # 进入追踪上下文
  - `__exit__(self, exc_type, exc_val, exc_tb) -> None`  # 退出追踪上下文

- `def get_trace_id() -> str`  # 获取当前追踪 ID

- `def set_trace_id(tid: str) -> None`  # 设置追踪 ID

- `def new_trace() -> str`  # 创建新的追踪 ID

- `def clear_trace() -> None`  # 清除当前追踪 ID

- `def is_tracing() -> bool`  # 检查是否处于追踪状态

- `def trace(name: Optional[str] = None)`  # 追踪装饰器

- `def new_sub_trace(parent_id: Optional[str] = None, suffix: str = "") -> str`  # 创建子追踪 ID

- `def get_parent_trace_id(trace_id: str) -> Optional[str]`  # 从子追踪 ID 中获取父追踪 ID

### `core/type_discovery/faction_discoverer.py`

**class FactionDiscoverer((TypeDiscoverer))**
  _势力类型发现器_
  - `_load_existing_types(self) -> Set[str]`  # 加载现有势力类型
  - `_get_config_path(self) -> Path`  # 获取配置文件路径
  - `_get_type_category(self) -> str`  # 获取类型类别
  - `_match_existing(self, text: str) -> bool`  # 匹配现有势力类型
  - `_generate_type_name(self, kw1: str, kw2: str) -> str`  # 根据关键词生成势力类型名称
  - `discover_factions(self, dialogues: List[str]) -> List[DiscoveredType]`  # 从对话中发现新的势力类型
  - `_extract_faction_features(self, text: str) -> Dict`  # 从文本中提取势力特征
  - `sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int`  # 同步到 faction_types.json

### `core/type_discovery/power_type_discoverer.py`

**class PowerTypeDiscoverer((TypeDiscoverer))**
  _力量类型发现器_
  - `_load_existing_types(self) -> Set[str]`  # 加载现有力量类型
  - `_get_config_path(self) -> Path`  # 获取配置文件路径
  - `_get_type_category(self) -> str`  # 获取类型类别
  - `_match_existing(self, text: str) -> bool`  # 匹配现有力量类型
  - `_generate_type_name(self, kw1: str, kw2: str) -> str`  # 根据关键词生成力量类型名称
  - `discover_power_types(self, novels: List[str]) -> List[DiscoveredType]`  # 从小说中发现新的力量体系类型
  - `_extract_power_features(self, text: str) -> Dict`  # 从文本中提取力量特征
  - `sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int`  # 同步到 power_types.json

### `core/type_discovery/technique_discoverer.py`

**class TechniqueDiscoverer((TypeDiscoverer))**
  _技法类型发现器_
  - `_load_existing_types(self) -> Set[str]`  # 加载现有技法类型
  - `_get_config_path(self) -> Path`  # 获取配置文件路径
  - `_get_type_category(self) -> str`  # 获取类型类别
  - `_match_existing(self, text: str) -> bool`  # 匹配现有技法类型
  - `_generate_type_name(self, kw1: str, kw2: str) -> str`  # 根据关键词生成技法类型名称
  - `discover_techniques(self, cases: List[str]) -> List[DiscoveredType]`  # 从案例中发现新的技法类型
  - `_extract_technique_features(self, text: str) -> Dict`  # 从文本中提取技法特征
  - `sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int`  # 同步到 technique_types.json

### `core/type_discovery/type_discoverer.py`

**class TypeDiscoverer((ABC))**
  _统一类型发现器基类_
  - `__init__(self, config: Optional[Dict] = None)`
  - `_extract_keywords(self, text: str) -> List[str]`  # 从文本中提取关键词
  - `collect_unmatched(self, texts: List[str], source_name: str) -> List[Dict]`  # 收集未匹配的片段
  - `_cluster_by_keywords(self) -> Dict[str, Dict]`  # 关键词聚类分析
  - `discover_types(self) -> List[DiscoveredType]`  # 从未匹配片段中发现新类型
  - `approve_type(self, type_name: str) -> bool`  # 审批确认类型
  - `reject_type(self, type_name: str) -> bool`  # 拒绝类型
  - `save_discovered(self) -> Path`  # 保存发现的类型
  - `load_discovered(self) -> List[DiscoveredType]`  # 加载已发现的类型
  - `sync_to_config(self, types: Optional[List[DiscoveredType]] = None) -> int`  # 同步到配置文件
  - `get_status(self) -> Dict[str, Any]`  # 获取发现器状态

- `def get_scene_discoverer()`  # 获取场景发现器实例（复用现有的 scene_discoverer.py）

### `core/world_loader.py`

- `def _load_config(project_root: Optional[Path] = None) -> Dict[str, Any]`  # 加载 config.json

- `def get_current_world_name(project_root: Optional[Path] = None) -> str`  # 返回当前世界观名称。

- `def get_world_config(
    world_name: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]`  # 加载指定世界观的配置。

- `def switch_world(new_world_name: str, project_root: Optional[Path] = None) -> None`  # 切换当前世界观（修改 config.json）。

- `def list_available_worlds(project_root: Optional[Path] = None) -> list`  # 列出 config/worlds/ 下所有可用世界观

## `modules/`


### `modules/feedback/__init__.py`

- `def quick_analyze(user_input: str, content: str = "") -> dict`  # 快速分析用户输入

### `modules/feedback/conflict_detector.py`

**class ConflictDetector**
  _冲突检测器_
  - `detect_all(
        self, worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]`  # 检测所有冲突
  - `detect_memory_conflicts(
        self, worldview: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]`  # 检测记忆逻辑冲突
  - `detect_foreshadow_conflicts(
        self, plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]`  # 检测伏笔与人物状态的匹配
  - `detect_timeline_conflicts(
        self, worldview: Dict[str, Any], plot: Dict[str, Any]
    ) -> List[Conflict]`  # 检测时间线冲突
  - `detect_setting_conflicts(
        self, worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
    ) -> List[Conflict]`  # 检测设定一致性
  - `_extract_memory_content(self, text: str, memory_type: str) -> List[str]`  # 提取记忆相关内容
  - `_is_memory_conflict(self, forget_item: str, remember_item: str) -> bool`  # 判断是否存在记忆冲突
  - `_check_usage_before_trigger(
        self, text: str, trigger: str, ability: str
    ) -> bool`  # 检查是否在触发前使用了能力

- `def detect_conflicts(
    worldview: Dict[str, Any], plot: Dict[str, Any], character: Dict[str, Any]
) -> List[Conflict]`  # 检测冲突（便捷函数）

### `modules/feedback/influence_analyzer.py`

**class InfluenceAnalyzer**
  _影响范围分析器_
  - `analyze(
        self,
        modification_level: ModificationLevel,
        content_changes: Dict[str, Any] = None,
    ) -> InfluenceReport`  # 分析修改影响范围
  - `_refine_impact(
        self, base_impact: Dict[str, Any], content_changes: Dict[str, Any]
    ) -> Dict[str, Any]`  # 细化影响范围
  - `_detect_entities(self, content_changes: Dict[str, Any]) -> Dict[str, List[str]]`  # 检测涉及的实体
  - `_adjust_by_entities(
        self, impact: Dict[str, Any], entities: Dict[str, List[str]]
    ) -> Dict[str, Any]`  # 根据涉及实体调整影响范围
  - `generate_report_text(self, report: InfluenceReport) -> str`  # 生成人类可读的影响报告

- `def analyze_influence(
    modification_level: ModificationLevel, content_changes: Dict[str, Any] = None
) -> InfluenceReport`  # 分析修改影响范围（便捷函数）

### `modules/feedback/intent_recognizer.py`

**class IntentRecognizer**
  _意图识别器_
  - `recognize(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> IntentResult`  # 识别用户意图
  - `_detect_rewrite(self, user_input: str) -> bool`  # 检测是否是重写请求
  - `_detect_modification_level(self, user_input: str) -> ModificationLevel`  # 检测修改层级
  - `_detect_rewrite_mode(self, user_input: str) -> RewriteMode`  # 检测重写模式
  - `_extract_chapter(self, user_input: str) -> str`  # 提取目标章节
  - `_extract_keywords(self, user_input: str) -> List[str]`  # 提取关键词
  - `_calculate_confidence(
        self,
        user_input: str,
        is_rewrite: bool,
        modification_level: ModificationLevel,
        rewrite_mode: RewriteMode,
    ) -> float`  # 计算置信度
  - `_determine_routing(
        self, is_rewrite: bool, modification_level: ModificationLevel
    ) -> str`  # 确定路由目标

- `def recognize_intent(user_input: str, context: Dict[str, Any] = None) -> IntentResult`  # 识别用户意图（便捷函数）

### `modules/feedback/tracking_syncer.py`

**class TrackingSyncer**
  _追踪同步器_
  - `__init__(self, project_root: str = None)`  # 初始化追踪同步器
  - `sync(
        self,
        original_content: str,
        modified_content: str,
        modification_level: ModificationLevel,
        tracking_files: Dict[str, Any] = None,
    ) -> TrackingUpdate`  # 同步追踪文件
  - `_need_update(self, modification_level: ModificationLevel) -> bool`  # 检查是否需要更新
  - `_detect_changes(self, original: str, modified: str) -> List[Dict[str, Any]]`  # 检测内容变化
  - `_analyze_impact(
        self, changes: List[Dict[str, Any]], modification_level: ModificationLevel
    ) -> Dict[str, Any]`  # 分析变化对追踪的影响
  - `_generate_updates(
        self, impact: Dict[str, Any], tracking_files: Dict[str, Any]
    ) -> Dict[str, Dict]`  # 生成更新内容
  - `_get_manual_confirm_items(self, impact: Dict[str, Any]) -> List[str]`  # 获取需要人工确认的项目
  - `load_tracking_file(self, name: str) -> Dict[str, Any]`  # 加载追踪文件
  - `save_tracking_file(self, name: str, data: Dict[str, Any]) -> bool`  # 保存追踪文件

- `def sync_tracking(
    original_content: str,
    modified_content: str,
    modification_level: ModificationLevel,
    tracking_files: Dict[str, Any] = None,
    project_root: str = None,
) -> TrackingUpdate`  # 同步追踪文件（便捷函数）

### `modules/feedback/types.py`

**class ModificationLevel((Enum))**
  _修改层级_

**class RewriteMode((Enum))**
  _重写模式_

**class ModificationStrategy((Enum))**
  _修改策略_

**class ConflictSeverity((Enum))**
  _冲突严重程度_

### `modules/knowledge_base/__init__.py`
> 知识库模块 - 入口文件

**class KnowledgeBase**
  _知识库统一接口_
  - `__init__(self, use_docker: bool = True, auto_check_db: bool = True)`  # 初始化知识库
  - `check_database(self) -> dict`  # 检查数据库连接状态
  - `sync(self, target: str = "all", rebuild: bool = False) -> dict`  # 同步数据到向量库
  - `sync_novel_settings(self, rebuild: bool = False) -> int`  # 同步小说设定
  - `sync_techniques(self, rebuild: bool = False) -> int`  # 同步创作技法
  - `sync_cases(self, rebuild: bool = False) -> int`  # 同步案例库
  - `search_novel(
        self,
        query: str,
        entity_type: str = None,
        top_k: int = 5,
    ) -> list`  # 检索小说设定
  - `search_technique(
        self,
        query: str,
        dimension: str = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list`  # 检索创作技法
  - `search_case(
        self,
        query: str,
        scene_type: str = None,
        genre: str = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> list`  # 检索标杆案例
  - `get_character(self, name: str) -> dict`  # 获取角色设定
  - `get_faction(self, name: str) -> dict`  # 获取势力设定
  - `get_power_branch(self, name: str) -> dict`  # 获取力量派别
  - `get_stats(self) -> dict`  # 获取数据库统计信息
  - `list_characters(self) -> list`  # 列出所有角色
  - `list_factions(self) -> list`  # 列出所有势力
  - `list_dimensions(self) -> list`  # 列出所有技法维度
  - `vectorize_knowledge(self, rebuild: bool = False) -> dict`  # 向量化大纲/设定
  - `vectorize_techniques(self, rebuild: bool = False) -> dict`  # 向量化创作技法

### `modules/knowledge_base/hybrid_search_manager.py`
> BGE-M3 混合检索管理器

**class HybridSearchManager**
  _BGE-M3 混合检索管理器_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
        weight_preset: str = DEFAULT_WEIGHT_PRESET,
    )`  # 初始化混合检索管理器
  - `_get_client(self) -> QdrantClient`  # 获取 Qdrant 客户端
  - `_load_model(self)`  # 加载 BGE-M3 模型，失败时重试三次
  - `_encode_query(self, query: str) -> Dict[str, Any]`  # 编码查询文本，生成三种向量
  - `set_weight_preset(self, preset: str)`  # 设置权重预设
  - `search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 混合检索小说设定
  - `get_character(self, name: str) -> Optional[Dict[str, Any]]`  # 获取角色设定
  - `get_faction(self, name: str) -> Optional[Dict[str, Any]]`  # 获取势力设定
  - `search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 混合检索创作技法，同时查 writing_techniques_v2（auto-ingest活数据）
  - `list_dimensions(self) -> List[str]`  # 列出所有技法维度
  - `search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
        use_rerank: bool = True,
    ) -> List[Dict[str, Any]]`  # 混合检索标杆案例
  - `_colbert_rerank(
        self,
        client: QdrantClient,
        collection_name: str,
        query_colbert: Any,
        candidates: List[Any],
        top_k: int,
        content_field: str = "content",
    ) -> List[Any]`  # 使用 ColBERT 对候选集重排序（动态编码，不依赖存储的向量）
  - `get_stats(self) -> Dict[str, Any]`  # 获取数据库统计信息
  - `list_characters(self) -> List[str]`  # 列出所有角色名称
  - `list_factions(self) -> List[str]`  # 列出所有势力名称
  - `search_worldview(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索世界观元素
  - `search_power_vocabulary(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索力量词汇
  - `search_character_relation(
        self,
        query: str,
        character: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索人物关系
  - `search_power_cost(
        self,
        query: str,
        power_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索力量代价描写
  - `search_author_style(
        self,
        query: str,
        genre: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索作者风格段落
  - `retrieve_for_scene(
        self,
        scene_type: str,
        context: Optional[str] = None,
        top_k: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]`  # 场景创作素材检索
  - `search_extended(
        self,
        collection_key: str,
        query: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 通用扩展维度检索

### `modules/knowledge_base/hybrid_search_manager_lite.py`
> 轻量混合检索管理器 - Dense + Sparse

**class HybridSearchManager**
  _轻量混合检索管理器 (Dense + Sparse)_
  - `__init__(self, qdrant_path: Path = None)`
  - `_get_client(self) -> QdrantClient`
  - `_load_model(self)`
  - `_encode_query(self, query: str) -> dict`  # 编码查询，返回 Dense 和 Sparse 向量
  - `search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]`  # 检索小说设定
  - `get_character(self, name: str) -> Optional[Dict]`  # 获取角色设定
  - `get_faction(self, name: str) -> Optional[Dict]`  # 获取势力设定
  - `search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]`  # 检索创作技法
  - `list_dimensions(self) -> List[str]`  # 列出技法维度
  - `search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]`  # 检索标杆案例
  - `_collection_exists(self, name: str) -> bool`  # 检查 Collection 是否存在
  - `_rrf_merge(self, dense_results: list, sparse_results: list, top_k: int) -> list`  # RRF (Reciprocal Rank Fusion) 融合
  - `get_stats(self) -> Dict[str, Any]`  # 获取数据库统计

### `modules/knowledge_base/hybrid_sync_manager.py`

**class HybridSyncManager**
  _BGE-M3 混合同步管理器_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    )`  # 初始化混合同步管理器
  - `_get_client(self) -> QdrantClient`  # 获取 Qdrant 客户端
  - `_resolve_model_path(self) -> str`  # 从本地缓存目录找 BGE-M3 snapshot 路径（必须含 tokenizer.json），找不到返回模型名
  - `_load_model(self)`  # 加载 BGE-M3 模型
  - `_encode_batch(
        self, texts: List[str], show_progress: bool = True
    ) -> Dict[str, Any]`  # 批量编码文本，生成三种向量
  - `_encode_batch_lite(self, texts: list) -> dict`  # 只编码 dense + sparse，不编 colbert，节省内存
  - `_create_lite_collection(self, collection_name: str) -> bool`  # 创建只含 dense + sparse 的 collection（无 colbert）
  - `_create_hybrid_collection(self, collection_name: str) -> bool`  # 创建支持混合检索的 Collection
  - `sync_all(self, rebuild: bool = True) -> Dict[str, int]`  # 同步所有数据
  - `sync_novel_settings(self, rebuild: bool = True) -> int`  # 同步小说设定
  - `sync_techniques(self, rebuild: bool = True) -> int`  # 同步创作技法
  - `sync_cases(self, rebuild: bool = True) -> int`  # 同步案例库
  - `sync_technique_json(
        self,
        json_path: Optional[str] = None,
        rebuild: bool = True,
    ) -> int`  # 直接从 technique_all.json 同步 138,968 条批量提炼技法到 writing_techniques_v2。
  - `_upload_points(self, collection_name: str, points: List[PointStruct])`  # 批量上传 Points
  - `_build_entity_text(self, name: str, props: Dict) -> str`  # 构建实体文本用于编码
  - `_extract_technique_sections(self, content: str) -> List[Dict[str, str]]`  # 从技法文件中提取章节

### `modules/knowledge_base/search_manager.py`
> 检索管理器 - 从向量库检索数据

**class SearchManager**
  _检索管理器_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    )`  # 初始化检索管理器
  - `_get_client(self) -> QdrantClient`  # 获取Qdrant客户端
  - `_load_model(self)`  # 懒加载嵌入模型
  - `_get_embedding(self, text: str) -> List[float]`  # 获取文本嵌入向量
  - `search_novel(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]`  # 检索小说设定
  - `get_character(self, name: str) -> Optional[Dict[str, Any]]`  # 获取角色设定
  - `get_faction(self, name: str) -> Optional[Dict[str, Any]]`  # 获取势力设定
  - `get_power_branch(self, name: str) -> Optional[Dict[str, Any]]`  # 获取力量派别
  - `list_characters(self) -> List[str]`  # 列出所有角色名称
  - `list_factions(self) -> List[str]`  # 列出所有势力名称
  - `search_technique(
        self,
        query: str,
        dimension: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> List[Dict[str, Any]]`  # 检索创作技法
  - `list_dimensions(self) -> List[str]`  # 列出所有技法维度
  - `get_techniques_by_dimension(
        self, dimension: str, top_k: int = 50
    ) -> List[Dict[str, Any]]`  # 按维度获取所有技法
  - `search_case(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]`  # 检索标杆案例
  - `get_stats(self) -> Dict[str, Any]`  # 获取数据库统计信息
  - `count_novel(self) -> int`  # 获取小说设定总数
  - `count_technique(self) -> int`  # 获取创作技法总数
  - `count_case(self) -> int`  # 获取案例总数
  - `search_case_quality_anchor(
        self,
        scene_type: str,
        emotional_tone: Optional[str] = None,
        top_k: int = 3,
        min_quality: float = 7.0,
    ) -> List[Dict[str, Any]]`  # 检索质量锚点：同场景类型中 quality_score 最高的案例。
  - `search_case_technique_instance(
        self,
        constraint_text: str,
        scene_type: Optional[str] = None,
        top_k: int = 2,
        min_score: float = 0.55,
    ) -> List[Dict[str, Any]]`  # 技法实例检索：以约束条文为查询，语义匹配案例库中的技法应用示例。
  - `ensure_own_chapters_collection(self) -> None`  # 确保本书章节集合存在，不存在则自动创建
  - `write_own_chapter_scene(
        self,
        chapter_name: str,
        scene_index: int,
        scene_type: str,
        content: str,
        techniques_used: List[str],
        quality_score: float,
        novel_name: str = "众生界",
    ) -> bool`  # 将已完成场景写入本书章节集合，供后续章节做一致性检索和技法去重。
  - `search_own_chapters(
        self,
        scene_type: str,
        novel_name: str = "众生界",
        exclude_chapter: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]`  # 检索本书已写章节：用于风格一致性检查和技法去重。

### `modules/knowledge_base/sync_manager.py`
> 同步管理器 - 数据同步到向量库

**class SyncManager**
  _数据同步管理器_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    )`  # 初始化同步管理器
  - `_get_client(self) -> QdrantClient`  # 获取Qdrant客户端
  - `_load_model(self)`  # 加载嵌入模型（BGE-M3，1024 维 dense vector）
  - `sync(self, target: str = "all", rebuild: bool = False) -> Dict[str, Any]`  # 同步数据到向量库
  - `sync_novel_settings(self, rebuild: bool = False) -> int`  # 同步小说设定
  - `sync_techniques(self, rebuild: bool = False) -> int`  # 同步创作技法
  - `sync_cases(self, rebuild: bool = False) -> int`  # [M3-β] 委托给 tools/case_builder.py --sync 完成案例向量化同步
  - `_extract_technique_sections(self, content: str) -> List[Dict[str, str]]`  # 从技法文件中提取章节/技法单元
  - `get_sync_status(self) -> Dict[str, Any]`  # 获取同步状态

### `modules/knowledge_base/vectorizer_manager.py`
> 向量化管理器 - 数据向量化处理

**class VectorizerManager**
  _向量化管理器_
  - `__init__(self, project_dir: Optional[Path] = None)`  # 初始化向量化管理器
  - `vectorize_knowledge(self, rebuild: bool = False) -> Dict[str, Any]`  # 向量化大纲/设定
  - `vectorize_techniques(self, rebuild: bool = False) -> Dict[str, Any]`  # 向量化创作技法
  - `_process_outline_files(self, collection)`  # 处理章节大纲文件
  - `_process_setting_files(self, collection)`  # 处理设定文件
  - `_process_total_outline(self, collection)`  # 处理总大纲
  - `_process_technique_files(self) -> List[TechniqueChunk]`  # 处理技法文件
  - `_parse_outline(self, file_path: Path) -> List[KnowledgeUnit]`  # 解析章节大纲
  - `_parse_setting(self, file_path: Path) -> List[KnowledgeUnit]`  # 解析设定文件
  - `_parse_power_system(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]`  # 解析力量体系
  - `_parse_characters(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]`  # 解析人物谱
  - `_parse_factions(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]`  # 解析势力
  - `_parse_generic(
        self, content: str, file_path: Path, now: str
    ) -> List[KnowledgeUnit]`  # 通用解析
  - `_split_technique_file(self, file_path: Path) -> List[TechniqueChunk]`  # 将技法文件分割成多个技法单元
  - `_extract_chapter_info(self, content: str) -> Dict[str, Any]`  # 提取章节信息
  - `_extract_scenes(self, content: str) -> List[Dict[str, str]]`  # 提取场景
  - `_clean_scene_content(self, content: str) -> str`  # 清理场景内容
  - `_format_chapter_info(self, info: Dict[str, Any]) -> str`  # 格式化章节信息
  - `_extract_technique_name(self, content: str) -> str`  # 从内容中提取技法名称
  - `_extract_keywords(self, content: str) -> List[str]`  # 从内容中提取关键词
  - `_determine_applicable_scenarios(
        self, content: str, dimension: str
    ) -> List[str]`  # 确定适用场景
  - `_get_id(self, name: str, type_prefix: str) -> str`  # 生成ID
  - `_add_units(self, collection, units: List[KnowledgeUnit])`  # 添加知识单元到集合
  - `_print_stats(self, title: str)`  # 打印统计

### `modules/migration/export_template.py`
> 项目模板导出器

**class TemplateExporter**
  _项目模板导出器_
  - `__init__(self, project_root: Path)`  # 初始化模板导出器
  - `export_template(
        self,
        target_dir: Path,
        preserve_structure: bool = True,
        create_examples: bool = True,
    ) -> Dict[str, Any]`  # 导出项目模板
  - `_create_migration_document(
        self, target_dir: Path, stats: Dict[str, Any]
    ) -> None`  # 创建移植文档
  - `_create_system_config_template(self, target_dir: Path) -> None`  # 创建系统配置模板

### `modules/migration/init_environment.py`
> 环境初始化器

**class EnvironmentInitializer**
  _环境初始化器_
  - `__init__(self, project_root: Path)`  # 初始化环境初始化器
  - `initialize(
        self, create_examples: bool = True, init_vectorstore: bool = False
    ) -> Dict[str, Any]`  # 初始化环境
  - `_create_system_config(self, timestamp: str) -> None`  # 创建system_config.json
  - `_init_vectorstore(self) -> None`  # 初始化向量数据库
  - `_create_init_document(self, timestamp: str, stats: Dict[str, Any]) -> None`  # 创建初始化文档

### `modules/validation/__init__.py`
> 验证模块 - 入口文件

- `def validate_all(quick: bool = False) -> dict`  # 运行所有验证（便捷函数）

- `def validate_chapter(chapter_path: str) -> dict`  # 验证章节（便捷函数）

- `def check_all() -> dict`  # 运行所有检查（便捷函数）

- `def score_chapter(chapter_path: str, scores: dict) -> str`  # 评分章节（便捷函数）

### `modules/validation/checker_manager.py`

**class CheckerManager**
  _检查管理器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化检查管理器
  - `_load_knowledge_graph(self) -> Optional[Dict]`  # 加载知识图谱
  - `check_sources(self) -> Dict[str, Any]`  # 检查案例库来源
  - `check_missing(self) -> Dict[str, Any]`  # 检查知识图谱中缺失的实体
  - `check_relations(self) -> Dict[str, Any]`  # 检查关系格式
  - `check_entity(self) -> Dict[str, Any]`  # 检查实体结构
  - `check_bloodline(self) -> Dict[str, Any]`  # 检查血脉格式
  - `check_all(self) -> Dict[str, Any]`  # 运行所有检查
  - `get_report(self) -> str`  # 生成检查报告文本

### `modules/validation/scorer_manager.py`

**class ScorerManager**
  _评分管理器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化评分管理器
  - `load_chapter(self, chapter_path: str) -> bool`  # 加载章节内容
  - `get_dimension_max_score(self, dim_name: str) -> int`  # 获取维度满分
  - `set_scores(self, scores: Dict[str, int]) -> int`  # 设置评分
  - `get_dimension_scores(self) -> Dict[str, Any]`  # 获取维度评分
  - `calculate_weighted_score(self) -> float`  # 计算加权总分
  - `check_thresholds(self) -> Dict[str, Any]`  # 检查是否达标
  - `generate_report(self, output_format: str = "text") -> str`  # 生成评分报告
  - `interactive_score(self) -> int`  # 交互式评分

- `def get_rating(score: int) -> str`  # 根据总分获取评级

- `def run_scorer_cli(args) -> int`  # CLI评分入口

### `modules/validation/validation_manager.py`

**class ValidationHistory**
  _验证历史管理（整合 verification_history.py）_
  - `__init__(self, history_dir: Optional[Path] = None)`  # 初始化验证历史
  - `_ensure_dir(self) -> None`  # 确保目录存在
  - `_load_history(self) -> Dict`  # 加载历史记录
  - `_save_history(self, data: Dict) -> None`  # 保存历史记录
  - `save_result(
        self,
        verification_type: str,
        result: Dict[str, Any],
        metadata: Optional[Dict] = None,
    ) -> str`  # 保存验证结果
  - `get_recent(self, verification_type: str, limit: int = 10) -> List[Dict]`  # 获取最近的验证记录
  - `get_latest(self, verification_type: str) -> Optional[Dict]`  # 获取最新验证记录
  - `get_summary(self) -> Dict`  # 获取所有验证类型的摘要
  - `cleanup_old_records(self, keep_count: int = 50) -> None`  # 清理旧记录

**class ValidationManager**
  _验证管理器 - 统一验证入口_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化验证管理器
  - `_run_script(self, script_path: Path) -> Tuple[bool, str]`  # 运行单个验证脚本
  - `_validate_merge(self) -> Tuple[bool, Dict]`  # 验证哲学设定和社会结构合并
  - `_validate_worldview(self) -> Tuple[bool, Dict]`  # 验证力量体系和时间线
  - `_check_sources(self) -> Tuple[bool, Dict]`  # 检查案例库来源
  - `run_all(
        self,
        quick: bool = False,
        selected: Optional[List[str]] = None,
        save_history: bool = True,
    ) -> Dict`  # 运行所有验证
  - `run_quick(self) -> Dict`  # 快速验证（只运行快速验证项）
  - `validate_chapter(self, chapter_path: str) -> Dict`  # 验证指定章节
  - `show_history(self) -> None`  # 显示验证历史
  - `print_summary(self, report: Dict) -> bool`  # 打印汇总报告

- `def run_validation_cli(args) -> int`  # CLI验证入口

### `modules/visualization/db_visualizer.py`

**class DBVisualizer**
  _数据库可视化器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化
  - `_connect_chroma(self) -> Optional[Any]`  # 连接 ChromaDB
  - `_connect_qdrant(self) -> Optional[Any]`  # 连接 Qdrant
  - `get_collection_stats(
        self, collection_name: str, db_type: str = "qdrant"
    ) -> Dict`  # 获取集合统计信息
  - `list_collections(self, db_type: str = "qdrant") -> List[str]`  # 列出所有集合
  - `generate_report(
        self, db_type: str = "qdrant", output: Optional[Path] = None
    ) -> Dict`  # 生成数据库报告
  - `print_summary(self, report: Dict)`  # 打印报告摘要
  - `check_data_integrity(
        self, collection_name: str, db_type: str = "qdrant"
    ) -> Dict`  # 检查数据完整性

- `def main()`  # 命令行入口

### `modules/visualization/graph_visualizer.py`

**class GraphVisualizer**
  _知识图谱可视化器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化
  - `_connect_qdrant(self) -> Optional[Any]`  # 连接 Qdrant 数据库
  - `load_knowledge_graph_data(self) -> Dict[str, Any]`  # 加载知识图谱数据
  - `load_technique_data(self) -> List[Dict[str, Any]]`  # 加载技法数据
  - `generate_knowledge_graph_html(
        self, data: Optional[Dict] = None, output: Optional[Path] = None
    ) -> str`  # 生成知识图谱 HTML
  - `generate_technique_graph_html(
        self, techniques: Optional[List] = None, output: Optional[Path] = None
    ) -> str`  # 生成技法图谱 HTML
  - `_render_knowledge_graph_html(
        self, entity_list: List, relation_list: List, timestamp: str
    ) -> str`  # 渲染知识图谱 HTML
  - `_render_technique_graph_html(
        self,
        techniques: List,
        techniques_by_dimension: Dict,
        techniques_by_writer: Dict,
        dimension_counts: Dict,
        writer_counts: Dict,
        core_count: int,
        timestamp: str,
    ) -> str`  # 渲染技法图谱 HTML

- `def main()`  # 命令行入口

### `modules/visualization/stats_visualizer.py`

**class StatsVisualizer**
  _统计可视化器_
  - `__init__(self, project_root: Optional[Path] = None)`  # 初始化
  - `get_knowledge_graph_stats(self) -> Dict`  # 获取知识图谱统计
  - `get_technique_stats(self) -> Dict`  # 获取技法库统计
  - `get_database_stats(self) -> Dict`  # 获取数据库统计
  - `get_project_stats(self) -> Dict`  # 获取项目整体统计
  - `generate_report(
        self, output: Optional[Path] = None, format: str = "json"
    ) -> str`  # 生成统计报告
  - `_render_text_report(self, stats: Dict) -> str`  # 渲染文本格式报告
  - `_render_html_report(self, stats: Dict) -> str`  # 渲染 HTML 格式报告
  - `print_summary(self)`  # 打印统计摘要

- `def main()`  # 命令行入口

## `tools/`


### `tools/aggregate_dialogue_style.py`

- `def _resolve_model_path() -> str`

- `def aggregate(data: list) -> list`  # 按 faction 聚合，返回 8 条汇总记录

- `def build_text(item: dict) -> str`

- `def main()`

### `tools/analyze_migration_difference.py`

- `def log(msg)`

- `def main()`

### `tools/annotate_benchmark.py`

- `def load_seeds(source_filter: str = None) -> list`  # 从 benchmark.json 加载种子查询

- `def load_annotated() -> dict`  # 加载已有标注结果（支持续标）

- `def save_annotated(data: dict) -> None`  # 保存标注结果

- `def run_search(api, query: str, source: str, top_k: int) -> list`  # 根据 source 调用对应检索接口，返回结果列表

- `def extract_id(result: dict) -> str`  # 从检索结果中提取 ID

- `def extract_preview(result: dict, max_len: int = 120) -> str`  # 从检索结果中提取预览文本

- `def annotate_one(query_text: str, source: str, results: list) -> Optional[List[dict]]`  # 对一条查询的检索结果进行交互式打分。

- `def already_annotated(annotated_data: dict, query_text: str) -> bool`  # 检查该查询是否已标注过

- `def main()`

### `tools/audit_outline_vs_settings.py`

- `def load_outline_key_settings(project_root: Path) -> List[Dict[str, Any]]`

- `def load_knowledge_graph(project_root: Path) -> Dict[str, Any]`

- `def flatten_settings(kg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]`  # 将知识图谱实体的“属性”浅层展开为 entity -> { field -> value }

- `def _load_field_aliases() -> Dict[str, str]`  # 从 config/audit_field_map.json 读取字段映射（不存在则返回默认通用映射）。

- `def _build_known_entities(settings_map: Dict[str, Dict[str, Any]]) -> List[str]`

- `def _match_entity_prefix(text: str, candidates: List[str]) -> Tuple[str, str]`  # 在 text 中寻找最长前缀实体名，返回 (entity, suffix)；找不到返回 (text, '').

- `def _derive_entity_and_field(item: Dict[str, Any], settings_map: Dict[str, Dict[str, Any]]) -> Tuple[str, str]`  # 从大纲条目推导 entity 与精确字段名。

- `def build_report(outline_items: List[Dict[str, Any]], settings_map: Dict[str, Dict[str, Any]])`

- `def main()`

### `tools/batch_extract.py`

- `def log(msg: str)`

- `def run_step(label: str, cmd: list, cwd=None) -> bool`  # 运行一个子步骤，失败时打印警告但不中断整体流程

- `def step1_case_builder(py: str, limit: int = 0)`  # 案例提炼：先 --convert 转格式，再 --extract 关键词匹配管道（含 C4+Bigram熵+MinHash）

- `def step2_semantic_case(py: str, limit: int = 0)`  # [U1] NOOP - 语义案例提炼已统一到 case_builder --extract

- `def step3_dimensions(py: str, limit: int = 0)`  # 10维度提炼：technique/角色关系/情感弧/对话风格等

- `def step3b_cleanup_jsonl()`  # 删除各维度的 JSONL 原始积累文件（_all.json 已保存，JSONL 不再需要）

- `def step4_scene_discovery(py: str)`  # 场景自动发现：从未分类片段中发现新场景类型

- `def step5_sync_cases(py: str)`  # [U1] 同步案例到 Qdrant case_library_v2 - 通过 case_builder --sync

- `def step6_sync_dimensions(py: str)`  # 将 E:\\novel_extracted 各维度 _all.json 向量化并全量重建 Qdrant collections

- `def main()`

### `tools/build_all.py`

- `def _build_cmd(stage: dict, rebuild: bool, technique_json: str) -> List[str]`  # 构建阶段的实际命令，替换占位符，按需追加 rebuild_extra

- `def run_stage(stage: dict, rebuild: bool, technique_json: str) -> bool`  # 运行一个阶段，输出同时打印到终端和写入日志文件

- `def show_status(qdrant_url: str = None) -> None`  # 显示各 collection 当前条数

- `def clear_case_data(case_lib_path: Path = None) -> None`  # --rebuild 时清除 case 阶段索引文件，不删小说源文件

- `def print_header(title)`  # 打印标题

- `def print_step(step, total, message)`  # 打印步骤

- `def check_dependencies()`  # 检查依赖

- `def check_docker()`  # 检查Docker

- `def init_project(project_dir: Path, novel_name: str)`  # 初始化项目

- `def build_techniques(techniques_dir: Path, quick: bool = False)`  # 构建技法库

- `def build_knowledge(settings_dir: Path, quick: bool = False)`  # 构建知识库

- `def build_cases(case_library_dir: Path, skip: bool = False, quick: bool = False)`  # 构建案例库

- `def build_scene_mapping(vectorstore_dir: Path, quick: bool = False)`  # 构建场景映射

- `def verify_system(project_dir: Path)`  # 验证系统

- `def main()`

### `tools/case_builder.py`

**class CaseBuilder**
  _案例库构建器_
  - `__init__(self, case_library_dir: Path = None, config: Optional[Dict] = None)`  # 初始化案例库构建器
  - `init_structure(self)`  # 初始化案例库目录结构
  - `scan_sources(self, source_dirs: List[Path] = None)`  # 扫描小说资源目录
  - `_read_novel(self, novel_path: Path) -> Optional[str]`  # 统一入口：读取任意格式小说，返回纯文本。失败返回 None。
  - `_read_txt_meta(self, path: Path) -> "tuple[str, str, float]"`  # 读取 txt，返回 (text, detected_enc, cjk_ratio)。
  - `_read_txt(self, path: Path) -> Optional[str]`  # txt 编码自动检测，返回解码后文本（供 _read_novel 调用）
  - `_read_epub(self, path: Path) -> Optional[str]`  # epub 双路径 HTML 检测（对齐 base_extractor）
  - `_read_mobi(self, path: Path) -> Optional[str]`  # mobi → epub 路径，安全 tempfile.tempdir 设置（串行锁保证多线程安全）
  - `_read_mobi_locked(self, path: Path) -> Optional[str]`
  - `_read_pdf(self, path: Path) -> Optional[str]`  # pdf → pdfminer.six（可选依赖）
  - `_read_docx(self, path: Path) -> Optional[str]`  # docx → python-docx（可选依赖）
  - `convert_files(
        self,
        source_dirs: Optional[List[Path]] = None,
        limit: int = 0,
        workers: int = 8,
    )`  # 转换小说格式（多线程 I/O 加速）
  - `extract_cases(
        self,
        limit: int = 0,
        scene_types: Optional[List[str]] = None,
        embed_batch: int = 128,
    )`  # 提取案例（Q3/Q4 批量推理，每本书只调两次 BGE-M3 而非逐候选调用）
  - `_detect_genre(self, content: str) -> str`  # 多位置采样题材检测（Q2：3段采样 + 扩充词库 + 默认未分类）
  - `_compute_boundary_delta(
        self,
        paragraphs: List[str],
        para_index: int,
        model,
        window: int = 3,
    ) -> float`  # Q3：Embedding Delta Signal (Schneider et al. 2021).
  - `_build_scene_type_anchors(self, model) -> Optional[Dict[str, Any]]`  # Q4：为 28 种场景类型预计算锚向量（one-time，结果不缓存到磁盘）。
  - `_semantic_verify_case(
        self,
        case_embedding,  # np.ndarray，案例段落的 BGE-M3 dense vector
        keyword_scene_type: str,
        anchors: Dict[str, Any],
        min_similarity: float = None,
    ) -> Optional[str]`  # Q4：Zero-shot 语义校验场景类型。
  - `_split_paragraphs(self, content: str) -> List[str]`  # 分割段落，并过滤广告/目录/低质量内容。
  - `_extract_scene_cases(
        self,
        paragraphs: List[str],
        scene_type: str,
        scene_config: Dict,
        novel_name: str,
        genre: str,
        source_file: str,
        bge_model=None,
        scene_anchors=None,
        _return_indices: bool = False,
    )`  # 提取特定场景类型的案例（含 Q3/Q4 语义验证）。
  - `_calculate_quality(
        self,
        content: str,
        match_count: int,
        kw_score: float = 0.0,
        scene_type: str = "",
    ) -> float`  # 计算质量分（扩展版：禁用词 + 信息密度 + 句末完整性 + Q1加权分）
  - `_generate_case_id(self, content: str) -> str`  # 生成案例ID
  - `_filter_near_duplicates(
        self,
        cases: "List[Case]",
        index_path: Optional[Path] = None,
    ) -> "tuple[List[Case], Dict[str, int]]"`  # 用 MinHash LSH 过滤近重复案例，并把新增案例写入持久化索引。
  - `_save_cases(self, cases: List[Case])`  # 保存案例到文件
  - `_update_index(self, cases: List[Case])`  # 更新案例索引
  - `sync_to_vectorstore(
        self,
        batch_size: int = 128,
        embed_batch: Optional[int] = None,
        skip_existing: bool = False,
    )`  # 同步案例到向量库（对齐路径二：HNSW禁用 + upsert重试 + embed/upsert流水线）
  - `get_status(self)`  # 获取案例库状态
  - `discover_new_scenes(
        self,
        limit: int = 5000,
        min_cluster_size: int = 10,
        max_clusters: int = 20,
        auto_apply: bool = False,
    )`  # 自动发现新场景类型
  - `apply_discovered_scenes(self, confidence_threshold: float = 0.6)`  # 应用发现的新场景类型

- `def _is_ad_paragraph(para: str) -> bool`  # 检测广告/下载站段落。返回 True 表示应过滤。

- `def _is_catalog_page(para: str) -> bool`  # 检测目录页：>= 3 行且 >= 40% 行符合章节标题格式。

- `def _get_chinese_ratio(text: str) -> float`  # 汉字占总字符数的比例。

- `def _is_sentence_complete(para: str) -> bool`  # 段落末尾是否为合法句末符号。

- `def _info_density(text: str) -> float`  # 词汇多样性（TTR）= 唯一 bigram 数 / 总 bigram 数。

- `def _clean_lines(paragraph: str) -> str`  # C4 风格行级清洗：逐行判定，丢弃广告/声明行后重新拼接。

- `def _bigram_entropy(text: str) -> float`  # 计算 bigram Shannon 熵。正常汉语小说 bigram 熵 > 7.0；模板化/重复文本 < 5.0。

- `def _mobi_to_txt(task: tuple) -> str`  # ProcessPoolExecutor worker：mobi → epub → txt。

- `def main()`

### `tools/check_collection_health.py`

- `def main()`

### `tools/check_env.py`
> tools/check_env.py

- `def ok(msg: str)`

- `def fail(msg: str)`

- `def warn(msg: str)`

- `def section(title: str)`

- `def check_python_version() -> bool`  # Python 版本 >= 3.10

- `def check_config_json() -> bool`  # config.json 存在且是合法 JSON

- `def check_dirs() -> bool`  # 检查各关键目录是否存在

- `def check_packages() -> bool`  # 检查关键 Python 包

- `def check_gpu() -> bool`  # 检查 GPU / CUDA 状态，始终返回 True（无 GPU 是正常情况，不阻断使用）

- `def check_qdrant(quick: bool = False) -> bool`  # 检查 Qdrant 连接

- `def check_config_values() -> bool`  # 检查 config.json 中的关键字段值是否合理（不只是文件存在）

- `def check_config_loader_importable() -> bool`  # 核心模块是否可导入

- `def main()`

### `tools/cleanup_old_collections.py`

- `def log(msg)`

- `def check_and_clean()`

### `tools/config_helper.py`

- `def detect_project_root() -> Path`  # 自动检测项目根目录

- `def detect_huggingface_cache() -> Optional[Path]`  # 检测 HuggingFace 缓存目录

- `def find_bge_m3_model(cache_dir: Optional[Path] = None) -> Optional[str]`  # 查找 BGE-M3 模型路径

- `def detect_novel_sources() -> List[str]`  # 检测可能的小说资源目录

- `def create_config(
    project_root: Path,
    model_path: Optional[str] = None,
    novel_sources: List[str] = None,
    output_path: Optional[Path] = None,
) -> Dict[str, Any]`  # 创建配置字典

- `def interactive_setup()`  # 交互式配置

- `def show_config()`  # 显示当前配置

- `def main()`

### `tools/data_builder.py`

**class DataBuilder**
  _数据构建管理器_
  - `__init__(self, config_path: Optional[Path] = None)`
  - `_load_config(self, config_path: Optional[Path]) -> Dict`  # 加载配置
  - `_connect_qdrant(self)`  # 连接Qdrant
  - `_load_model(self)`  # 加载嵌入模型
  - `init_collections(self)`  # 初始化所有向量库collections
  - `sync_techniques(self, techniques_dir: Optional[Path] = None)`  # 同步技法数据
  - `sync_settings(self, settings_dir: Optional[Path] = None)`  # 同步设定数据
  - `build_case_library(
        self,
        source_dirs: Optional[List[Path]] = None,
        scene_types: Optional[List[str]] = None,
        limit: Optional[int] = None,
    )`  # 构建案例库
  - `get_status(self)`  # 获取系统状态
  - `build_all(self)`  # 一键构建全部
  - `_parse_techniques(self, tech_dir: Path) -> List[Dict]`  # 解析技法文件
  - `_parse_settings(self, settings_dir: Path) -> List[Dict]`  # 解析设定文件
  - `_classify_setting(self, filename: str, title: str, content: str) -> str`  # 自动分类设定
  - `_get_default_scene_types(self) -> List[str]`  # 获取默认场景类型
  - `_extract_cases(
        self,
        novel_dirs: List[Path],
        scene_types: List[str],
        limit: Optional[int],
    ) -> List[Dict]`  # 提取案例（简化版本）
  - `_sync_to_collection(
        self,
        collection_name: str,
        items: List[Dict],
        batch_size: int,
    )`  # 同步数据到collection

- `def main()`

### `tools/data_migrator.py`

**class DataMigrator**
  _数据迁移管理器_
  - `__init__(
        self,
        project_dir: Optional[Path] = None,
        use_docker: bool = True,
        docker_url: str = None,
    )`  # 初始化数据迁移器
  - `_get_client(self) -> QdrantClient`  # 获取Qdrant客户端（复用现有逻辑）
  - `_load_model(self)`  # 加载嵌入模型（复用现有逻辑）
  - `_load_progress(self) -> Dict[str, Any]`  # 加载迁移进度
  - `_save_progress(self)`  # 保存迁移进度
  - `migrate_json_to_qdrant(
        self,
        collection_name: str,
        json_file: Path,
        batch_size: int = 100,
        force: bool = False,
    ) -> Dict[str, Any]`  # 迁移JSON数据到Qdrant
  - `_create_hybrid_collection(
        self, client: QdrantClient, collection_name: str, vector_size: int
    )`  # 创建混合检索Collection（V2）
  - `_create_simple_collection(
        self, client: QdrantClient, collection_name: str, vector_size: int
    )`  # 创建单向量检索Collection（V1）
  - `_extract_records(
        self, data: Any, json_file: Path, collection_name: str
    ) -> List[Dict[str, Any]]`  # 从JSON数据提取记录
  - `_migrate_batch(
        self,
        client: QdrantClient,
        collection_name: str,
        model: Any,
        batch: List[Dict[str, Any]],
        batch_start: int,
        total: int,
    ) -> int`  # 迁移一批数据
  - `_calculate_file_hash(self, file_path: Path) -> str`  # 计算文件哈希（用于增量迁移检测）
  - `create_extended_collections(self) -> Dict[str, Any]`  # 创建扩展维度Collection
  - `migrate_all(self, force: bool = False) -> Dict[str, Any]`  # 迁移所有数据
  - `get_migration_status(self) -> Dict[str, Any]`  # 获取迁移状态
  - `print_status(self)`  # 打印迁移状态（CLI显示）

- `def main()`  # CLI入口

### `tools/dedup_case_library.py`

- `def _read_content(json_file: Path) -> str`  # 从 JSON 文件读取 content；若 content 为空，回退读 .txt 兄弟。

- `def _archive_file(json_file: Path, cases_root: Path, archive_root: Path) -> None`  # 把 json + 同名 txt 移动到归档目录，保留相对路径结构。

- `def run_dedup(
    cases_root: Path,
    archive_root: Path,
    index_path: Path,
    dry_run: bool = False,
    progress_every: int = 10000,
) -> Dict[str, int]`  # 执行存量去重。返回统计 dict。

- `def main()`

### `tools/dedup_utils.py`
> MinHash LSH 近重复检测工具

- `def compute_minhash(text: str) -> MinHash`  # 为一段文本计算 MinHash 指纹。

- `def create_lsh() -> Tuple[MinHashLSH, Dict[str, MinHash]]`  # 新建空的 LSH 紟引 + minhash 缓存（用于后续持久化）。

- `def save_lsh(lsh: MinHashLSH, cache: Dict[str, MinHash], path: Path) -> None`  # 保存 LSH 紟引 + minhash 缓存到 pickle 文件。

- `def load_lsh(path: Path) -> Tuple[MinHashLSH, Dict[str, MinHash]]`  # 从 pickle 文件加载 LSH 紟引；不存在则返回空索引。

- `def is_near_duplicate(lsh: MinHashLSH, minhash: MinHash) -> bool`  # 判断 minhash 是否与 lsh 中已有条目近重复。

### `tools/deep_analyze_missing_data.py`

- `def log(msg)`

- `def main()`

### `tools/dump_syntax_trees.py`
> 导出项目所有 Python 文件的语法树 (tree-sitter 0.25+)

- `def node_to_text(node, src: bytes, indent: int = 0) -> str`  # 递归生成语法树文本

- `def dump_file(py_file: Path, out_file: Path)`

- `def main()`

### `tools/eval_criteria_migrator.py`

**class EvaluationCriteriaMigrator**
  _审核维度迁移器_
  - `__init__(self, project_root: Optional[str] = None)`
  - `migrate_all(self) -> Dict[str, int]`  # 迁移所有审核标准
  - `_read_skill_file(self) -> Optional[str]`  # 读取 SKILL.md 文件
  - `_migrate_prohibitions(self, content: str) -> List[EvaluationCriteria]`  # 从 SKILL.md 揁移禁止项
  - `_migrate_technique_criteria(self, content: str) -> List[EvaluationCriteria]`  # 从 SKILL.md 迁移技法评估标准
  - `_migrate_thresholds(self, content: str) -> List[EvaluationCriteria]`  # 从 SKILL.md 迁移阈值配置
  - `save_to_file(self) -> Path`  # 保存迁移结果到文件
  - `sync_to_qdrant(self) -> Dict[str, Any]`  # 同步到 Qdrant 向量库

- `def main()`

### `tools/eval_retrieval_quality.py`

- `def calculate_recall_at_k(
    results: List[Dict], 
    expected: List[Dict], 
    k: int = 10,
    min_relevance: int = 2
) -> float`  # 计算 Recall@K

- `def calculate_dcg(results: List[Dict], expected: List[Dict], k: int = 10) -> float`  # 计算 DCG (Discounted Cumulative Gain)

- `def calculate_idcg(expected: List[Dict], k: int = 10) -> float`  # 计算 Ideal DCG

- `def calculate_ndcg(
    results: List[Dict], 
    expected: List[Dict], 
    k: int = 10
) -> float`  # 计算 NDCG (Normalized DCG)

- `def load_benchmark(benchmark_path: Path) -> Dict[str, Any]`  # 加载评估基准数据集

- `def evaluate_retrieval(
    api: UnifiedRetrievalAPI,
    benchmark: Dict[str, Any],
    top_k: int = 10
) -> Dict[str, Any]`  # 执行检索评估

- `def print_report(report: Dict[str, Any]) -> None`  # 打印评估报告

- `def main()`

### `tools/extract_intent_patterns_to_json.py`

- `def _serialize_intents(intents: dict) -> dict`  # 把 IntentCategory enum 转成字符串名，patterns 与 entities 原样保留

- `def main()`

### `tools/filter_judicial_cases.py`

- `def score_article(text: str) -> tuple[int, list[str], list[str]]`  # 返回 (分数, 命中的正向词, 命中的负向词)

- `def parse_article(filepath: Path) -> dict`

- `def run(base_dir: Path, threshold_keep: int, threshold_uncertain: int, dry_run: bool)`

- `def main()`

### `tools/gen_skeleton.py`
> 项目骨架生成器 - 众生界 (tree-sitter 0.25+)

- `def get_docstring(node, src: bytes) -> str`  # 提取函数/类的第一个字符串作为 docstring

- `def get_params(func_node, src: bytes) -> str`

- `def get_return_annotation(func_node, src: bytes) -> str`

- `def analyze_file(py_file: Path) -> dict`  # 提取文件的模块信息：docstring、imports、类、顶层函数

- `def format_file_section(rel_path: str, info: dict) -> str`

- `def main()`

### `tools/imagery_builder.py`

**class ImageryBuilder**
  _诗词意象库构建器_
  - `__init__(self, config: Optional[Dict] = None)`
  - `_get_client(self)`  # 获取Qdrant客户端
  - `_get_model(self)`  # 获取BGE-M3模型
  - `_get_embedding(self, text: str) -> List[float]`  # 获取文本向量
  - `init_imagery_data(self) -> List[Dict]`  # 初始化意象数据
  - `sync_to_qdrant(self, imagery_list: List[Dict])`  # 同步到Qdrant向量库
  - `test_search(self, query: str, world_context: str = None, top_k: int = 5)`  # 测试检索功能

- `def main()`

### `tools/ingest_judicial_cases.py`

- `def parse_article(filepath: Path) -> dict`

- `def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list`

- `def _upsert_with_retry(client, collection: str, points, retries: int = 5)`

- `def run(reviewed_dir: Path, collection: str, qdrant_url: str, rebuild: bool, embed_batch: int)`

- `def main()`

### `tools/init_novel.py`

- `def list_templates() -> list[str]`  # 列出可用世界配置模板

- `def create_world_config(novel_name: str, template: str) -> Path`  # 从模板创建世界配置文件

- `def update_config_json(novel_name: str) -> None`  # 更新 config.json 的 worldview.current_world

- `def create_directory_structure(base_path: Path)`  # 创建目录结构

- `def create_config_template(base_path: Path, novel_name: str)`  # 创建配置模板

- `def create_gitignore(base_path: Path)`  # 创建 .gitignore

- `def create_sample_technique(base_path: Path)`  # 创建示例技法文件

- `def create_sample_settings(base_path: Path)`  # 创建示例设定文件

- `def main()`

### `tools/kg_apply_patch.py`

- `def main()`

### `tools/knowledge_builder.py`

**class KnowledgeBuilder**
  _知识库构建器_
  - `__init__(self, settings_dir: Path, config: Optional[Dict] = None)`
  - `init_structure(self)`  # 初始化知识库目录结构
  - `create_setting(self, setting_type: str, name: str)`  # 创建单个设定文件
  - `parse_settings(self) -> List[Dict]`  # 解析所有设定文件
  - `_classify_setting(self, filename: str, title: str, content: str) -> str`  # 自动分类设定
  - `_extract_entities(self, content: str) -> Dict`  # 提取实体
  - `build_knowledge_graph(self)`  # 从设定构建知识图谱
  - `sync_to_vectorstore(self)`  # 同步设定到向量库
  - `get_status(self)`  # 获取知识库状态

- `def main()`

### `tools/merge_author_styles.py`

- `def load_fragment(path: Path) -> list`

- `def merge_authors(fragment_files: list[Path]) -> list`

- `def build_header(total: int) -> str`

- `def main()`

### `tools/narrative_ledger.py`
> tools/narrative_ledger.py

- `def _load_cfg() -> dict`

- `def _ledger_path() -> Path`

- `def _load_ledger() -> dict`

- `def _save_ledger(data: dict) -> None`

- `def _now() -> str`

- `def update_chapter(
    chapter: int,
    scene_types: list[str],
    tension_level: int,
    themes_touched: dict[str, int] | None = None,
) -> None`  # 在阶段8经验写入后调用，更新台账。

- `def get_diversity_constraints(next_chapter: int) -> str`  # 在阶段1大纲解析后调用，返回可直接注入 prompt 的多样性约束块。

- `def show_summary() -> str`  # 生成台账当前状态的可读摘要。

- `def main() -> None`

### `tools/quality_gate.py`
> tools/quality_gate.py

- `def _load_yaml(path: Path) -> Any`

- `def _load_writer_blacklist(writer: str) -> list[str]`  # 加载写手配置中所有作家的黑名单（并集）。

- `def _load_gate_config() -> dict`

- `def compute_burstiness(text: str) -> tuple[bool, float, str]`  # 计算句子长度方差（Burstiness 指标）。

- `def check_ai_blacklist(
    text: str,
    writer_blacklist: list[str] | None = None,
) -> tuple[bool, list[str], float]`  # 检测 AI 套句命中情况。

- `def run_quality_gate(
    text: str,
    writer: str | None = None,
    chapter: int | None = None,
    scene_index: int | None = None,
) -> dict[str, Any]`  # 执行完整质量检测。

- `def format_report(result: dict) -> str`  # 格式化为可读报告文本。

- `def main() -> None`

### `tools/scene_discoverer.py`

**class SceneDiscoverer**
  _场景自动发现器_
  - `__init__(self, config: Optional[Dict] = None)`
  - `_load_existing_scenes(self) -> Set[str]`  # 加载现有场景类型
  - `collect_unclassified(
        self, paragraphs: List[str], novel_name: str
    ) -> List[Dict]`  # 收集无法归类到现有场景类型的片段
  - `_extract_keywords(self, text: str) -> List[str]`  # 从文本中提取关键词
  - `discover_scenes(self) -> List[DiscoveredScene]`  # 从无法归类的片段中发现新场景类型
  - `_cluster_by_keywords(self) -> Dict[str, Dict]`  # 通过关键词聚类发现场景模式
  - `_generate_scene_name(self, kw1: str, kw2: str) -> str`  # 根据关键词生成场景名称
  - `save_discovered(self) -> Path`  # 保存发现的场景到文件
  - `load_discovered(self) -> List[DiscoveredScene]`  # 加载已发现的场景
  - `sync_to_case_builder(
        self, scenes: Optional[List[DiscoveredScene]] = None
    ) -> int`  # 同步新场景到case_builder.py的SCENE_TYPES
  - `sync_to_scene_mapping(
        self, scenes: Optional[List[DiscoveredScene]] = None
    ) -> int`  # 同步新场景到scene_writer_mapping.json
  - `sync_to_skill(self, scenes: Optional[List[DiscoveredScene]] = None) -> int`  # 同步新场景到novelist-workflow SKILL.md
  - `sync_all(
        self, scenes: Optional[List[DiscoveredScene]] = None, sync_qdrant: bool = False
    ) -> Dict[str, int]`  # 同步到所有配置文件
  - `_sync_to_qdrant(self) -> int`  # 同步场景案例到向量库
  - `approve_scene(self, scene_name: str) -> bool`  # 批准一个发现的场景
  - `reject_scene(self, scene_name: str) -> bool`  # 拒绝一个发现的场景
  - `get_status(self) -> Dict[str, Any]`  # 获取发现器状态

- `def main()`

### `tools/scene_discovery.py`

**class KeywordExtractor**
  _关键词提取器 - 从文本片段中提取高频关键词_
  - `__init__(self, existing_scene_types: Dict = None)`
  - `extract_keywords(
        self, fragments: List[str], top_k: int = 8, min_freq: int = 3
    ) -> List[Tuple[str, int]]`  # 从片段中提取高频关键词
  - `generate_scene_name(self, keywords: List[str]) -> str`  # 根据关键词生成场景名称

**class ClusteringEngine**
  _语义聚类引擎 - 使用BGE-M3向量聚类相似片段_
  - `__init__(self, model_path: str = None)`
  - `_load_model(self)`  # 懒加载BGE-M3模型
  - `get_embeddings(self, texts: List[str]) -> np.ndarray`  # 获取文本嵌入向量
  - `cluster_fragments(
        self,
        fragments: List[UnclassifiedFragment],
        min_cluster_size: int = 10,
        similarity_threshold: float = 0.75,
        max_clusters: int = 20,
    ) -> List[List[UnclassifiedFragment]]`  # 聚类未归类片段

**class SceneDiscovery**
  _自动场景发现器_
  - `__init__(
        self,
        case_library_dir: Path,
        config: Optional[Dict] = None,
        scene_types: Dict = None,
    )`
  - `collect_unclassified_fragments(
        self, converted_dir: Path, limit: int = 5000
    ) -> List[UnclassifiedFragment]`  # 收集无法归类的片段
  - `_detect_genre(self, content: str) -> str`  # 检测题材
  - `_split_paragraphs(self, content: str) -> List[str]`  # 分割段落
  - `_find_best_scene_match(self, content: str) -> Dict`  # 找到最佳场景匹配
  - `_calculate_quality(self, content: str, match_count: int) -> float`  # 计算质量分
  - `discover_new_scenes(
        self, unclassified: List[UnclassifiedFragment]
    ) -> List[DiscoveredScene]`  # 发现新场景类型
  - `_calc_cluster_similarity(self, fragments: List[UnclassifiedFragment]) -> float`  # 计算聚类内平均相似度
  - `_calculate_confidence(
        self,
        fragment_count: int,
        avg_similarity: float,
        keyword_count: int,
        avg_quality: float,
    ) -> float`  # 计算发现置信度
  - `apply_discovered_scenes(
        self,
        discovered: List[DiscoveredScene],
        scene_types_file: Path = None,
        mapping_file: Path = None,
    ) -> bool`  # 应用发现的新场景到配置文件
  - `_save_unclassified(self, fragments: List[UnclassifiedFragment])`  # 保存未归类片段
  - `_save_discovered(self, scenes: List[DiscoveredScene])`  # 保存发现的新场景
  - `_save_stats(self, discovered: List[DiscoveredScene], updated_scene_types: Dict)`  # 保存统计信息
  - `_update_scene_types_file(self, file_path: Path, scene_types: Dict)`  # 更新场景类型配置文件
  - `_update_mapping_file(
        self, mapping_file: Path, discovered: List[DiscoveredScene]
    )`  # 更新场景映射配置文件
  - `get_status(self) -> Dict`  # 获取发现状态

- `def main()`

### `tools/scene_mapping_builder.py`

**class SceneMappingBuilder**
  _场景映射构建器_
  - `__init__(self, vectorstore_dir: Path = None)`
  - `init_mapping(self)`  # 初始化默认映射
  - `load_mapping(self) -> Dict`  # 加载映射
  - `show_mapping(self)`  # 显示当前映射
  - `set_mapping(self, scene_type: str, writer_id: str)`  # 设置场景映射
  - `add_scene_type(self, scene_type: str, writer_id: str = None)`  # 添加新场景类型
  - `add_writer(
        self, writer_id: str, name: str, specialty: str, skills: List[str], style: str
    )`  # 添加新作家

- `def main()`

### `tools/scrape_spp.py`

- `def _sleep()`

- `def _slug(text: str, maxlen: int = 40) -> str`

- `def _get(url: str, retries: int = 3) -> requests.Response | None`

- `def list_articles(section: str, max_pages: int) -> list[dict]`

- `def fetch_article(url: str) -> dict | None`

- `def save_article(output_dir: Path, meta: dict, detail: dict) -> Path`

- `def load_progress(output_dir: Path) -> set[str]`

- `def save_progress(output_dir: Path, done: set[str])`

- `def run(output_dir: Path, max_pages: int)`

- `def main()`

### `tools/scrape_thepaper.py`

- `def _default_output() -> Path`

- `def _sleep()`

- `def _slug(text: str, maxlen: int = 40) -> str`

- `def _article_id_from_url(url: str | None) -> str | None`

- `def _href(tag) -> str`  # BeautifulSoup tag.get("href") → plain str，消除 AttributeValueList 类型歧义。

- `def _get(url: str, params: dict | None = None, retries: int = 3) -> requests.Response | None`

- `def search_articles(keyword: str, max_pages: int = 5) -> list[dict]`  # 通过 Baidu 站内搜索「site:thepaper.cn keyword」获取澎湃文章 URL。

- `def channel_articles(channel_name: str, channel_id: str, max_pages: int = 20) -> list[dict]`  # 抓取指定频道的文章列表。

- `def fetch_article_content(url: str) -> dict | None`  # 抓取单篇文章正文，返回 {title, date, content, author}。

- `def save_article(output_dir: Path, category: str, meta: dict, detail: dict) -> Path`  # 保存为 META + 正文 的 .txt 文件。

- `def load_progress(output_dir: Path) -> set[str]`

- `def save_progress(output_dir: Path, done_ids: set[str])`

- `def run(
    keywords: list[str],
    channels: dict[str, str],
    output_dir: Path,
    limit_per_keyword: int,
    channel_only: bool,
)`

- `def main()`

### `tools/spec_generator.py`
> 项目目录树后序遍历 + Spec生成器

- `def get_file_type(ext)`

- `def analyze_file(filepath, max_lines=50)`  # 分析单个文件，提取关键信息

- `def postorder_traverse(root_path)`  # 后序遍历目录树

- `def generate_spec(root_path, output_file="spec.md")`  # 生成spec.md

### `tools/static_analysis.py`
> Tree-sitter 静态分析 - 众生界项目 (tree-sitter 0.25+)

- `def walk_nodes(node)`

- `def in_main_block(node) -> bool`  # 判断节点是否在 if __name__ == '__main__' 块内

- `def rel(path: Path) -> str`

- `def analyze_file(py_file: Path) -> dict`

- `def main()`

### `tools/style_injector.py`
> tools/style_injector.py

- `def _fetch_self_style_block() -> str`  # 从 memory_points_v1 读取本书自我风格偏好，拼成 prompt 追加块。

- `def _load_yaml(path: Path) -> Any`

- `def _get_author(styles_data: dict, name: str) -> dict | None`

- `def build_writer_style_context(
    writer: str,
    scene_type: str,
    seed: int | None = None,
) -> str`  # 构建写手风格上下文提示块。

- `def list_available_authors(writer: str) -> list[str]`  # 列出写手可用的作家列表（供用户调整配比时参考）。

- `def get_current_mix(writer: str) -> dict[str, float]`  # 返回写手当前的作家配比。

- `def main() -> None`

### `tools/sync_eval_criteria_to_qdrant.py`

- `def log(msg: str)`  # 日志输出

- `def load_criteria() -> List[Dict[str, Any]]`  # 加载审核维度数据

- `def generate_embedding_text(criteria: Dict[str, Any]) -> str`  # 为审核维度生成嵌入文本

- `def create_collection(client, collection_name: str)`  # 创建Collection

- `def upload_criteria(
    client, criteria: List[Dict[str, Any]], collection_name: str, model
)`  # 上传审核维度到向量库

- `def verify_upload(client, collection_name: str)`  # 验证上传结果

- `def main()`  # 主函数

### `tools/sync_extracted_to_qdrant.py`
> tools/sync_extracted_to_qdrant.py

- `def _text_author_style(item: Dict) -> str`

- `def _text_character_relation(item: Dict) -> str`

- `def _text_dialogue_style(item: Dict) -> str`

- `def _text_emotion_arc(item: Dict) -> str`

- `def _text_foreshadow_pair(item: Dict) -> str`

- `def _text_power_cost(item: Dict) -> str`

- `def _text_power_vocabulary(item: Dict) -> str`

- `def _text_worldview_element(item: Dict) -> str`

- `def load_model()`  # 加载 BGE-M3 模型（FlagEmbedding）

- `def embed_batch(model, texts: List[str]) -> List[List[float]]`  # 批量向量化，返回 dense 向量列表

- `def rebuild_collection(client, collection_name: str) -> None`  # 删除旧 collection 并重建（仅 dense 1024维 Cosine）

- `def _make_payload(item: Dict, embed_text: str) -> Dict`  # 构造 payload，去掉超过500字符的列表字段

- `def sync_dimension(
    client, model, dim_id: str, config: Dict,
    dry_run: bool = False, skip_existing: bool = False,
    upsert_batch: int = UPSERT_BATCH, embed_batch: int = EMBED_BATCH_SIZE,
    max_length: int = 512,
) -> int`  # 同步单个维度，返回已同步条数

- `def main()`

### `tools/sync_settings.py`

- `def parse_markdown_setting(file_path: Path) -> Dict[str, Any]`  # 解析设定MD文件

- `def classify_setting(filename: str, title: str, content: str) -> str`  # 自动分类设定

- `def load_config(config_path: Path) -> Dict[str, Any]`  # 加载配置文件

- `def sync_settings_to_qdrant(
    settings: List[Dict[str, Any]],
    qdrant_url: str,
    collection_name: str,
    model_path: str = None,
    batch_size: int = 20,
)`  # 同步设定到Qdrant

- `def main()`

### `tools/sync_techniques.py`

- `def parse_techniques(content)`  # 解析技法文件

- `def main()`

### `tools/technique_builder.py`

**class TechniqueBuilder**
  _技法库构建器_
  - `__init__(self, techniques_dir: Path, config: Optional[Dict] = None)`
  - `init_structure(self)`  # 初始化技法目录结构
  - `_create_sample_techniques(self)`  # 创建示例技法文件
  - `import_technique_file(
        self, file_path: Path, target_dimension: Optional[str] = None
    )`  # 导入单个技法文件
  - `parse_directory(self, source_dir: Path)`  # 解析目录下的所有技法文件
  - `_parse_technique_content(self, content: str, default_name: str) -> List[Dict]`  # 解析技法内容
  - `_format_technique(self, name: str, subtitle: str, content: str) -> str`  # 格式化技法内容
  - `sync_to_vectorstore(self)`  # 同步技法到向量库
  - `generate_template(self)`  # 生成技法模板文件

- `def main()`

### `tools/test_qdrant_connection.py`

- `def test_connection() -> bool`  # 测试Qdrant连接

- `def test_collections(client) -> Dict[str, Dict]`  # 测试各Collection数据量

- `def test_data_integrity(client, collections: Dict) -> Dict`  # 测试数据完整性

- `def test_retrieval(client) -> Dict`  # 测试scroll检索功能

- `def run_all_tests()`  # 运行全部测试

- `def print_test_summary()`  # 打印测试总结

### `tools/unified_extractor.py`

**class UnifiedExtractor**
  _统一提炼引擎_
  - `__init__(self, config: Optional[Dict] = None)`  # 初始化统一提炼引擎
  - `_init_submodules(self)`  # 初始化子模块
  - `_load_progress(self) -> UnifiedProgress`  # 加载统一进度
  - `_save_progress(self)`  # 保存统一进度
  - `_create_extractor(self, dimension_id: str)`  # 创建提取器实例
  - `extract(
        self,
        dimensions: Optional[List[str]] = None,
        force: bool = False,
        workers: int = 4,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]`  # 单一入口启动所有提取
  - `_run_parallel_extraction(
        self,
        dimensions: List[str],
        workers: int,
        force: bool,
        limit: Optional[int],
    ) -> Dict[str, Dict]`  # 并行执行多个维度的提取
  - `extract_dimension(
        self,
        dimension_id: str,
        force: bool = False,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]`  # 单个维度提取
  - `_run_scene_discovery(self) -> List`  # 运行场景发现
  - `_sync_to_qdrant(self, dimensions: List[str]) -> Dict[str, Any]`  # 同步到Qdrant向量数据库
  - `_determine_final_status(self, results: Dict[str, Dict]) -> str`  # 确定最终状态
  - `_calculate_duration(self) -> str`  # 计算执行时长
  - `_print_summary(self, extraction_results: Dict, sync_results: Dict)`  # 打印汇总
  - `get_status(self) -> Dict[str, Any]`  # 获取当前状态
  - `print_status(self)`  # 打印当前状态

- `def _dimension_worker(
    dimension_id: str,
    force: bool,
    limit,
) -> dict`  # ProcessPoolExecutor 工作函数，在独立子进程中运行单个维度提炼

- `def main()`

### `tools/validation/judge.py`

**class BaseJudge((ABC))**
  _抽象基类：给定查询和检索结果，返回相关性得分_

**class SkipJudge((BaseJudge))**
  _不调用 LLM，所有得分返回 None，只看 Qdrant 分数分布_
  - `score(self, query: str, result_text: str, collection_type: str) -> None`

**class ManualJudge((BaseJudge))**
  _终端交互，人工逐条打分_
  - `score(self, query: str, result_text: str, collection_type: str) -> int | None`

**class OpenAICompatibleJudge((BaseJudge))**
  _兼容 OpenAI 协议的 LLM judge（Ollama / DeepSeek / Qwen 等）_
  - `__init__(self, base_url: str, api_key: str, model: str)`
  - `score(self, query: str, result_text: str, collection_type: str) -> int | None`

**class OpenAIJudge((OpenAICompatibleJudge))**
  _OpenAI 官方 API judge_
  - `__init__(self, api_key: str, model: str = "gpt-4o")`

**class ClaudeJudge((BaseJudge))**
  _Anthropic Claude judge_
  - `__init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001")`
  - `score(self, query: str, result_text: str, collection_type: str) -> int | None`

- `def _parse_score(text: str) -> int | None`  # 从 LLM 返回文本中提取 0/1/2

- `def make_judge(provider: str, **kwargs) -> BaseJudge`  # 工厂函数，根据 provider 字符串创建对应 Judge 实例

### `tools/validation/validate_retrieval.py`

**class CollectionValidator**
  _单个 collection 的检索质量验证器_
  - `__init__(self, qdrant_client, judge, queries: dict)`
  - `validate_collection(self, collection_name: str) -> dict`  # 验证单个 collection，返回结果字典

- `def ndcg_at_5(scores: list[int]) -> float`  # 计算 nDCG@5，scores 为 [0,1,2] 列表，长度 5

- `def precision_at_5(scores: list[int]) -> float`  # Precision@5，得分 >= 1 视为相关

- `def embed_query(text: str) -> list[float]`  # 封装 BGE-M3 嵌入，便于测试时 mock

- `def load_queries(override_path: str | None = None) -> dict`  # 加载查询文件，支持外部覆盖

- `def _collection_status_emoji(result: dict) -> str`

- `def write_json_report(all_results: list[dict], judge_name: str, qdrant_url: str) -> Path`

- `def write_markdown_report(all_results: list[dict], judge_name: str) -> Path`

- `def main()`

## `scripts/`


### `scripts/chapter_state_tracker.py`
> 跨章节人物状态追踪工具

- `def load_states() -> Dict[str, Any]`  # 加载当前状态文件，文件不存在时返回空字典

- `def _save_states(states: Dict[str, Any]) -> None`  # 写入状态文件

- `def update_character_state(
    character: str, chapter: str, updates: Dict[str, Any]
) -> None`  # 更新单个角色状态（合并更新，不覆盖未提及字段）

- `def get_character_state(character: str) -> Optional[Dict[str, Any]]`  # 获取角色当前状态，角色不存在时返回 None

- `def get_all_active_states() -> Dict[str, Any]`  # 获取所有角色的当前状态，用于注入创作上下文

- `def format_states_for_context(states: Dict[str, Any]) -> str`  # 将状态字典格式化为可注入创作上下文的文字

### `scripts/sync_outlines.py`

- `def sync_all_outlines(force: bool = False) -> None`  # 全量同步所有大纲文件到 Qdrant

- `def sync_total_outline() -> None`  # 仅同步总大纲

- `def sync_chapter_outlines() -> None`  # 仅同步所有章节大纲

- `def _force_sync_all(detector) -> None`  # 强制同步所有大纲（不经过变更检测）

- `def main() -> None`

## `config/`


### `config/dimension_sync.py`

**class DimensionSync**
  _维度配置同步器_
  - `__init__(self)`  # 初始化同步器
  - `add_scene_type(self, scene_type: str, config: Dict) -> bool`  # 添加新场景类型
  - `add_power_type(self, power_type: str, config: Dict) -> bool`  # 添加新力量类型
  - `add_faction_type(self, faction_type: str, config: Dict) -> bool`  # 添加新势力类型
  - `_log_update(
        self, config_type: str, action: str, key: str, old_value: Any, new_value: Any
    )`  # 记录配置更新
  - `sync_all(self) -> Dict[str, int]`  # 同步所有配置
  - `get_update_log(self, limit: int = 10) -> List[Dict]`  # 获取配置更新日志
  - `validate_all(self) -> Dict[str, bool]`  # 验证所有配置文件

- `def get_scene_types() -> Dict`  # 获取场景类型配置

- `def get_power_types() -> Dict`  # 获取力量类型配置

- `def get_faction_types() -> Dict`  # 获取势力类型配置

- `def get_technique_types() -> Dict`  # 获取技法类型配置

## `.vectorstore/`


### `.vectorstore/add_civilization_tech.py`

- `def add_tech_to_graph() -> None`  # 添加技术基础实体到知识图谱

- `def main()`

### `.vectorstore/add_scene_templates.py`

- `def add_templates_to_graph() -> None`  # 添加场景模板到知识图谱

- `def main()`

### `.vectorstore/bge_m3_config.py`
> BGE-M3 混合检索配置

- `def get_collection_config()`  # 获取支持混合检索的Collection配置

- `def get_hybrid_query(
    dense_vector: list,
    sparse_indices: list,
    sparse_values: list,
    colbert_vectors: list,
    weights: dict = None,
    recall_config: dict = None,
)`  # 构建混合检索查询

### `.vectorstore/extend_character_backstories.py`

- `def parse_backstory_file() -> Dict[str, Dict]`  # 解析角色过往经历文件

- `def parse_backstory_section(content: str) -> Dict[str, str]`  # 解析过往经历部分

- `def parse_emotion_section(content: str) -> Dict[str, Dict[str, str]]`  # 解析情绪触发部分

- `def parse_behavior_section(content: str) -> List[Dict[str, str]]`  # 解析行为烙印部分

- `def update_knowledge_graph(characters: Dict[str, Dict]) -> None`  # 更新知识图谱中的角色实体

- `def main()`

### `.vectorstore/extract_relations.py`

- `def extract_relations()`  # 从实体属性中提取隐含关系

### `.vectorstore/graph_visualizer.py`

- `def load_from_qdrant() -> Dict`  # 从JSON文件加载知识图谱数据（优先）

- `def generate_html(data: Dict) -> str`  # 生成HTML可视化

- `def generate_html_content(entity_list: List, relation_list: List) -> str`  # 生成HTML内容

- `def main()`

### `.vectorstore/hybrid_retriever.py`

**class HybridRetriever**
  _混合检索器 - Dense + ColBERT + RRF融合_
  - `__init__(self, use_gpu: bool = True)`  # 初始化检索器
  - `_init_model(self)`  # 初始化BGE-M3模型
  - `_init_client(self)`  # 初始化Qdrant客户端
  - `_scan_vector_configs(self)`  # 扫描所有collection的向量配置
  - `get_collection_config(self, collection: str) -> Dict[str, bool]`  # 获取collection向量配置
  - `encode_query(self, query: str) -> Dict[str, Any]`  # 编码查询为多向量
  - `dense_search(
        self, collection: str, dense_vec: List[float], top_k: int = 50
    ) -> List[ScoredPoint]`  # Dense向量检索
  - `colbert_search(
        self, collection: str, colbert_vecs: List[List[float]], top_k: int = 50
    ) -> List[ScoredPoint]`  # ColBERT向量检索（多向量，late interaction）
  - `rrf_fusion(
        self,
        dense_results: List[ScoredPoint],
        colbert_results: List[ScoredPoint],
        k: int = 60,
        top_k: int = 10,
    ) -> List[SearchResult]`  # RRF (Reciprocal Rank Fusion) 融合
  - `retrieve(
        self,
        query: str,
        collection: str,
        top_k: int = 10,
        dense_top_k: int = 50,
        colbert_top_k: int = 50,
        fusion_k: int = 60,
        verbose: bool = False,
    ) -> List[SearchResult]`  # 混合检索
  - `multi_collection_retrieve(
        self,
        query: str,
        collections: List[str],
        top_k_per_collection: int = 5,
        final_top_k: int = 10,
        verbose: bool = False,
    ) -> Dict[str, List[SearchResult]]`  # 多collection检索

**class RetrievalCache**
  _检索缓存_
  - `__init__(self, max_size: int = 1000, ttl: int = 3600)`
  - `get(self, key: str) -> Optional[List[SearchResult]]`  # 获取缓存
  - `set(self, key: str, results: List[SearchResult])`  # 设置缓存
  - `warm_up(
        self, retriever: HybridRetriever, queries: List[str], collections: List[str]
    )`  # 预热热门查询

- `def create_cached_retriever(
    warm_up: bool = False,
) -> Tuple[HybridRetriever, RetrievalCache]`  # 创建带缓存的检索器

### `.vectorstore/memory_points_v1_config.py`

- `def init_collection(client: QdrantClient) -> bool`  # 初始化 memory_points_v1 Collection。

### `.vectorstore/parse_missing_data.py`

- `def parse_behavior_template()`  # 解析行为预判模板.md

- `def parse_character_deep_settings()`  # 解析角色过往经历与情绪触发.md

- `def _save_table_data(result, role, section, rows)`  # 保存表格数据

- `def update_knowledge_graph(scene_templates, emotion_states, character_deep)`  # 更新知识图谱

- `def main()`

### `.vectorstore/retrieval_evaluation.py`

**class RetrievalEvaluator**
  _检索质量评估器_
  - `__init__(self)`
  - `evaluate_hit_rate(
        self,
        results: List[SearchResult],
        expected_keywords: List[str],
        top_k: int = 10,
    ) -> Tuple[float, float, float]`  # 计算命中率
  - `evaluate_keyword_match(
        self,
        results: List[SearchResult],
        must_contain: List[str],
    ) -> float`  # 计算关键词匹配率
  - `run_single_test(
        self,
        test_case: Dict[str, Any],
        collection: str,
        top_k: int = 10,
    ) -> EvaluationResult`  # 运行单个测试
  - `run_all_tests(self) -> Dict[str, Any]`  # 运行全部测试
  - `generate_report(self) -> Dict[str, Any]`  # 生成评估报告
  - `print_report(self)`  # 打印评估报告
  - `save_report(self, output_path: str = "evaluation_report.json")`  # 保存评估报告

### `.vectorstore/sync/md_parser.py`

**class MDParser**
  _Markdown解析器基类_

**class FactionParser((MDParser))**
  _势力解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有势力信息
  - `_parse_from_outline(self, content: str) -> List[Dict]`  # 从总大纲解析势力基础信息
  - `_parse_faction_branches(self, content: str, faction_name: str) -> List[Dict]`  # 解析势力内部派系
  - `_merge_faction_details(self, factions: List[Dict], content: str) -> List[Dict]`  # 从十大势力.md合并详细信息
  - `_parse_political_structure(self, section: str) -> Dict`  # 解析政治结构
  - `_parse_economic_structure(self, section: str) -> Dict`  # 解析经济结构
  - `_parse_cultural_structure(self, section: str) -> List[str]`  # 解析文化结构

**class CharacterParser((MDParser))**
  _角色解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有角色信息
  - `_parse_from_character_file(self, content: str) -> List[Dict]`  # 从人物谱.md解析角色基础信息
  - `_parse_power_details(self, content: str, characters: List[Dict]) -> List[Dict]`  # 解析角色力量体系详细表格
  - `_name_to_id(self, name: str) -> str`  # 角色名转ID
  - `_get_power_system(self, faction: str) -> str`  # 根据势力推断力量体系
  - `_merge_character_details(
        self, characters: List[Dict], content: str
    ) -> List[Dict]`  # 从总大纲合并角色详细信息
  - `_parse_romance(self, content: str, char_name: str) -> List[Dict]`  # 解析角色感情关系

**class PowerSystemParser((MDParser))**
  _力量体系解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有力量体系
  - `_parse_realms_direct(self, content: str, marker: str) -> List[str]`  # 直接从全文解析境界划分
  - `_parse_branches(self, section: str, power_name: str) -> List[Dict]`  # 解析力量体系派别
  - `_extract_branch_info(self, row: Dict, power_name: str) -> Dict`  # 根据力量体系类型提取派别信息
  - `_parse_realms(self, section: str, power_name: str) -> List[str]`  # 解析境界划分
  - `_parse_costs(self, section: str, power_name: str) -> List[Dict]`  # 解析力量体系代价
  - `_name_to_id(self, name: str) -> str`

**class EraParser((MDParser))**
  _时代解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有时代
  - `_name_to_id(self, name: str) -> str`

**class EventParser((MDParser))**
  _事件解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有事件
  - `_name_to_id(self, name: str) -> str`
  - `_extract_overview(self, section: str) -> str`  # 提取事件概述

**class TechniqueParser((MDParser))**
  _创作技法解析器_
  - `parse_all(self) -> List[Dict]`  # 解析所有创作技法
  - `_parse_technique_file(
        self, file_path: Path, dimension: str, writer: str
    ) -> List[Dict]`  # 解析单个技法文件
  - `_extract_technique_name(self, content: str) -> str`  # 从内容中提取技法名称
  - `_extract_keywords(self, content: str) -> List[str]`  # 从内容中提取关键词
  - `_determine_scenarios(self, content: str, dimension: str) -> List[str]`  # 确定适用场景

**class TechBaseParser((MDParser))**
  _技术基础解析器 - 解析各文明技术基础文件_
  - `parse_all(self) -> List[Dict]`  # 解析所有技术基础
  - `_parse_civilization_tech(self, content: str, civilization: str) -> List[Dict]`  # 解析单个文明的技术基础
  - `_extract_plot_applications(self, section: str) -> List[str]`  # 提取情节应用
  - `_extract_domain(self, name: str, section: str) -> str`  # 提取技术领域
  - `_extract_source(self, section: str, civilization: str) -> str`  # 提取技术来源
  - `_name_to_id(self, name: str) -> str`  # 名称转ID

**class FullParser**
  _完整解析器_
  - `__init__(self)`
  - `parse_all(self) -> Dict`  # 解析所有数据
  - `save_to_json(self, output_path: Path = None)`  # 保存解析结果到JSON

- `def main()`

### `.vectorstore/sync/rebuild_knowledge_graph_v2.py`

**class KnowledgeGraphBuilder**
  _知识图谱构建器_
  - `__init__(self)`
  - `build_all(self)`  # 构建完整知识图谱
  - `_build_factions(self, factions: List[Dict])`  # 构建势力实体
  - `_build_characters(self, characters: List[Dict])`  # 构建角色实体
  - `_build_power_systems(self, systems: List[Dict])`  # 构建力量体系实体
  - `_build_eras(self, eras: List[Dict])`  # 构建时代实体
  - `_build_events(self, events: List[Dict])`  # 构建事件实体
  - `_build_tech_bases(self, tech_bases: List[Dict])`  # 构建技术基础实体
  - `_build_techniques(self, techniques: List[Dict])`  # 构建创作技法实体
  - `_build_relations(self, data: Dict)`  # 构建关系
  - `_add_relation(
        self, source: str, relation_type: str, target: str, attributes: dict = None
    )`  # 添加关系
  - `_print_stats(self)`  # 打印统计
  - `_save(self)`  # 保存知识图谱

- `def main()`

### `.vectorstore/sync_sparse_vectors.py`

**class SparseVectorSyncer**
  _Sparse向量入库器_
  - `__init__(self, use_gpu: bool = True)`
  - `_load_model(self)`  # 加载BGE-M3模型
  - `_create_sparse_collection(self, collection_name: str) -> bool`  # 创建支持Dense+Sparse的Collection
  - `_load_data(self, collection_name: str) -> List[Dict]`  # 加载数据
  - `sync_collection(
        self,
        collection_name: str,
        batch_size: int = 100,
        rebuild: bool = True,
    ) -> int`  # 同步单个Collection
  - `get_status(self)`  # 获取所有Collection状态

- `def main()`

### `.vectorstore/technique_graph_visualizer.py`

- `def load_techniques_from_qdrant()`  # 从Qdrant数据库加载技法详细数据

- `def generate_html(techniques, dimension_counts, writer_counts)`  # 生成完整的技法图谱HTML

- `def main()`

### `.vectorstore/tools/check/check_sources.py`

- `def check_case_library()`

### `.vectorstore/tools/check/checklist_scorer.py`

**class ChecklistScorer**
  _检查清单评分器_
  - `__init__(self)`
  - `load_chapter(self, chapter_path: str)`  # 加载章节内容
  - `input_scores_interactive(self)`  # 交互式输入评分
  - `set_scores(self, scores: Dict[str, int])`  # 直接设置评分
  - `calculate_weighted_score(self) -> float`  # 计算加权总分
  - `generate_report(self, output_format: str = "text") -> str`  # 生成评分报告

- `def get_rating(score: int) -> str`  # 根据总分获取评级

- `def main()`

### `.vectorstore/tools/check/verification_history.py`

**class VerificationHistory**
  _验证结果历史管理_
  - `__init__(self, history_dir: Path = None)`
  - `_ensure_dir(self)`  # 确保目录存在
  - `_load_history(self) -> Dict`  # 加载历史记录
  - `_save_history(self, data: Dict)`  # 保存历史记录
  - `save_result(
        self, verification_type: str, result: Dict[str, Any], metadata: Dict = None
    ) -> str`  # 保存验证结果
  - `get_recent(self, verification_type: str, limit: int = 10) -> List[Dict]`  # 获取最近的验证记录
  - `get_latest(self, verification_type: str) -> Optional[Dict]`  # 获取最新验证记录
  - `compare_with_previous(self, verification_type: str, current: Dict) -> Dict`  # 与上次验证结果对比
  - `get_summary(self) -> Dict`  # 获取所有验证类型的摘要
  - `cleanup_old_records(self, keep_count: int = 50)`  # 清理旧记录，只保留最近的N条

- `def main()`

### `.vectorstore/tools/debug/fix_xueya.py`

- `def main()`

### `.vectorstore/tools/debug/relation_editor.py`

**class KnowledgeGraphEditor**
  _知识图谱编辑器_
  - `__init__(self)`
  - `load(self)`  # 加载图谱
  - `save(self)`  # 保存图谱
  - `list_relations(self, filter_type: str = None, filter_entity: str = None)`  # 列出关系
  - `list_entities(self, filter_type: str = None)`  # 列出实体
  - `add_relation(self, source: str, rel_type: str, target: str, attrs: Dict = None)`  # 添加关系
  - `remove_relation(self, index: int)`  # 删除关系（按索引）
  - `modify_relation(
        self,
        index: int,
        source: str = None,
        rel_type: str = None,
        target: str = None,
        attrs: Dict = None,
    )`  # 修改关系
  - `find_errors(self)`  # 查找可能错误的关系
  - `sync_all(self)`  # 同步到所有存储

- `def interactive_mode()`  # 交互模式

### `.vectorstore/tools/verify/verify_all.py`

- `def run_script(script_path: Path) -> Tuple[bool, str]`  # 运行单个验证脚本

- `def run_all_verifications(quick: bool = False, selected: List[str] = None) -> dict`  # 运行所有验证

- `def print_summary(report: dict)`  # 打印汇总报告

- `def save_to_history(report: dict)`  # 保存验证结果到历史记录

- `def show_history()`  # 显示验证历史

- `def main()`

### `.vectorstore/unified_retrieval_api.py`

**class RetrievalSource((Enum))**
  _检索源_

**class UnifiedRetrievalAPI**
  _统一检索API_
  - `__init__(self, use_cache: bool = True, warm_up: bool = False)`  # 初始化API
  - `_warm_up_cache(self)`  # 预热缓存
  - `_format_result(self, sr: SearchResult, source: str, rank: int) -> UnifiedResult`  # 格式化检索结果
  - `retrieve(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        top_k: int = 10,
        top_k_per_source: int = 5,
        fusion_strategy: str = "concat",  # concat/rrf/score_weighted
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 多源检索
  - `search_techniques(
        self,
        query: str,
        dimension: Optional[str] = None,
        writer: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 技法检索
  - `search_cases(
        self,
        query: str,
        scene_type: Optional[str] = None,
        genre: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 案例检索
  - `search_worldview(
        self,
        query: str,
        element_type: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 世界观元素检索
  - `search_power_vocabulary(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 力量词汇检索
  - `search_character_relations(
        self,
        query: str,
        character: Optional[str] = None,
        top_k: int = 5,
        verbose: bool = False,
    ) -> List[UnifiedResult]`  # 人物关系检索
  - `retrieve_for_scene(
        self,
        scene_type: str,
        context: Optional[str] = None,
        top_k: int = 3,
        verbose: bool = False,
    ) -> Dict[str, List[UnifiedResult]]`  # 场景创作素材检索
  - `get_stats(self) -> Dict[str, Any]`  # 获取检索统计

- `def get_unified_api(warm_up: bool = False) -> UnifiedRetrievalAPI`  # 获取统一检索API（单例模式）

### `.vectorstore/verify_all_workflow_interfaces.py`

- `def test(name, condition, detail="")`  # 记录测试结果

- `def warn(name, detail="")`  # 记录警告

## `.novel-extractor/`


### `.novel-extractor/author_style_extractor.py`

**class AuthorStyleExtractor((BaseExtractor))**
  _作者风格指纹提取器 v2.0_
  - `__init__(self)`
  - `_segment_sentences(self, content: str) -> List[str]`  # 分割句子
  - `_count_chinese_chars(self, text: str) -> int`  # 统计汉字数
  - `_analyze_sentence_length(self, sentences: List[str]) -> Dict[str, float]`  # 分析句长分布
  - `_analyze_word_preference(self, content: str) -> Dict[str, Any]`  # 分析用词偏好
  - `_analyze_rhetoric(self, content: str) -> Dict[str, int]`  # 分析修辞手法使用
  - `_identify_style_pattern(self, features: Dict) -> str`  # 识别风格模式
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取风格特征
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 按风格模式聚合
  - `_get_style_description(self, style_pattern: str) -> str`  # 获取风格描述

- `def extract_author_styles(limit: int = None)`

### `.novel-extractor/base_extractor.py`
> 小说提炼系统 - 基础提取器

**class BaseExtractor((ABC))**
  _提取器基类_
  - `__init__(self, dimension_id: str)`
  - `_load_progress(self) -> ExtractionProgress`  # 加载进度
  - `_save_progress(self)`  # 保存进度
  - `_get_novel_id(self, novel_path: Path) -> str`  # 生成小说唯一ID（基于路径hash）
  - `_scan_novels(self) -> Generator[Path, None, None]`  # 扫描所有小说文件
  - `_read_novel(self, novel_path: Path) -> Optional[str]`  # 读取小说内容
  - `_read_epub(self, novel_path: Path) -> Optional[str]`  # 读取 epub 文件内容
  - `_read_mobi(self, novel_path: Path) -> Optional[str]`  # 读取 mobi 文件内容
  - `_read_pdf(self, novel_path: Path) -> Optional[str]`  # 读取 PDF 文件内容（可选依赖 pdfminer.six）
  - `_read_docx(self, novel_path: Path) -> Optional[str]`  # 读取 DOCX 文件内容（可选依赖 python-docx）
  - `run(self, limit: int = None, resume: bool = True) -> Dict[str, Any]`  # 运行提取
  - `_is_novel_processed(self, novel_id: str) -> bool`  # 检查小说是否已处理
  - `_save_extracted_items(self, items: List[dict], novel_id: str)`  # 保存提取结果
  - `_save_final_results(self)`  # 保存最终结果

**class BatchExtractor**
  _批量提取管理器_
  - `__init__(self)`
  - `register(self, extractor: BaseExtractor)`  # 注册提取器
  - `run_all(self, priorities: List[Priority] = None, limit: int = None)`  # 运行所有提取器
  - `get_status(self) -> Dict[str, Dict]`  # 获取所有提取器状态

### `.novel-extractor/cleaners/deep_cleaner.py`

**class DeepCleaner**
  _深度清洗器类_
  - `__init__(
        self,
        min_paragraph_length: int = 10,
        max_pinyin_ratio: float = 0.3,
        retention_threshold: float = 50.0,
    )`  # 初始化深度清洗器
  - `clean(self, text: str) -> Dict[str, Any]`  # 主清洗方法
  - `_remove_html(self, text: str) -> str`  # 清理HTML标签和HTML实体
  - `_filter_ads(self, text: str) -> str`  # 过滤广告推广内容
  - `_clean_antipiracy(self, text: str) -> str`  # 清理防盗版内容
  - `_format_chapters(self, text: str) -> str`  # 格式化章节标题
  - `_align_paragraphs(self, text: str) -> str`  # 段落整理

- `def deep_clean(text: str, **kwargs) -> Dict[str, Any]`  # 便捷函数：快速清洗文本

### `.novel-extractor/config.py`
> 小说提炼系统配置

**class Priority((Enum))**

- `def _load_config()`  # 从 config.json 加载配置，失败时返回空字典

- `def get_output_path(dimension_id: str, filename: str = None) -> Path`  # 获取输出文件路径

- `def get_progress_path(dimension_id: str) -> Path`  # 获取进度文件路径

- `def init_extractor()`  # 初始化提炼系统

- `def init_system()`  # unified_config 兼容别名，等价于 init_extractor()

### `.novel-extractor/dialogue_style_extractor.py`
> 势力对话风格提取器

**class DialogueStyleExtractor((BaseExtractor))**
  _势力对话风格提取器_
  - `__init__(self)`
  - `_load_genre_mapping(self) -> Dict[str, List[str]]`  # 加载题材-小说映射（从案例库）
  - `_detect_genre(self, novel_path: Path) -> Optional[str]`  # 检测小说题材（路径匹配）
  - `_detect_genre_from_content(self, content: str) -> str`  # 从内容关键词检测题材（路径无法识别时的兜底）
  - `_extract_dialogues(self, content: str) -> List[Dict[str, Any]]`  # 提取对话片段
  - `_extract_speaker(self, context: str) -> Optional[str]`  # 从上下文提取说话人
  - `_analyze_dialogue_style(
        self, dialogues: List[Dict], faction: str
    ) -> Dict[str, Any]`  # 分析对话风格
  - `_extract_word_features(self, text: str, faction: str) -> Dict[str, Any]`  # 提取用词特征
  - `_extract_sentence_features(self, text: str) -> Dict[str, Any]`  # 提取句式特征
  - `_extract_tone_features(
        self, text: str, dialogues: List[Dict]
    ) -> Dict[str, Any]`  # 提取语气特征
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取对话风格
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 合并同一势力的风格
  - `_merge_faction_styles(self, faction: str, styles: List[dict]) -> dict`  # 合并同一势力的多个风格样本
  - `_generate_style_summary(
        self, faction: str, word_freq: Dict[str, int], tone_dist: Dict[str, int]
    ) -> str`  # 生成风格摘要

- `def extract_dialogue_styles(limit: int = None)`  # 提取对话风格

### `.novel-extractor/emotion_arc_extractor.py`
> 情感曲线提取器

**class EmotionArcExtractor((BaseExtractor))**
  _情感曲线提取器_
  - `__init__(self)`
  - `_calculate_emotion_score(self, text: str) -> float`  # 计算文本情感得分
  - `_segment_text(self, content: str, num_segments: int = 20) -> List[str]`  # 将文本分成多个片段
  - `_extract_arc(self, content: str) -> List[EmotionPoint]`  # 提取情感曲线
  - `_classify_arc_type(self, arc: List[EmotionPoint]) -> str`  # 分类情感曲线类型
  - `_calculate_arc_statistics(self, arc: List[EmotionPoint]) -> Dict[str, Any]`  # 计算曲线统计特征
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取情感曲线
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 按曲线类型聚合
  - `_get_arc_description(self, arc_type: str) -> str`  # 获取曲线类型描述

- `def extract_emotion_arcs(limit: int = None)`  # 提取情感曲线

### `.novel-extractor/extractors/author_style_extractor.py`
> 作者风格指纹提取器

**class AuthorStyleExtractor((_AuthorStyleExtractor))**
  _作者风格指纹提取器（代理）_

### `.novel-extractor/extractors/case_extractor.py`
> 场景案例提取器

**class CaseExtractor**
  _场景案例提取器_
  - `__init__(self)`
  - `_load_progress(self) -> CaseExtractionProgress`  # 加载进度
  - `_save_progress(self)`  # 保存进度
  - `_get_stats(self) -> Dict[str, Any]`  # 获取当前统计
  - `run(
        self,
        limit: int = None,
        scene_types: List[str] = None,
        genres: List[str] = None,
        resume: bool = True,
    ) -> Dict[str, Any]`  # 运行场景案例提取
  - `get_status(self) -> Dict[str, Any]`  # 获取提取状态
  - `extract_for_scene(self, scene_type: str, top_k: int = 10) -> List[Dict]`  # 获取指定场景类型的案例

- `def extract_cases(**kwargs) -> Dict[str, Any]`  # 提取场景案例

- `def get_case_stats() -> Dict[str, Any]`  # 获取案例统计

### `.novel-extractor/extractors/chapter_structure_extractor.py`
> 章节结构模式提取器

**class ChapterStructureExtractor((BaseExtractor))**
  _章节结构模式提取器_
  - `__init__(self)`
  - `_split_into_chapters(self, content: str) -> List[Dict[str, Any]]`  # 分割章节
  - `extract_from_novel(self, content: str, novel_id: str, novel_path) -> List[dict]`  # 从小说提取章节结构
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果
  - `_identify_rhythm(self, lengths: List[int]) -> str`  # 识别节奏模式

### `.novel-extractor/extractors/character_relation_extractor.py`
> Character relation extractor

**class CharacterRelationExtractor((BaseExtractor))**
  _Builds a character co-occurrence graph from novel text._
  - `__init__(self)`
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`
  - `process_extracted(self, items: List[dict]) -> List[dict]`

- `def _is_valid_name(nm: str) -> bool`

- `def _detect_names(text: str) -> List[str]`  # Extract character names from high-precision context patterns.

- `def _split_chapters(novel_text: str) -> Dict[int, str]`

- `def _sentences(text: str) -> List[str]`

- `def _contexts_for_pair(chunk: str, a: str, b: str, chapter_id: int) -> List[str]`

### `.novel-extractor/extractors/dialogue_style_extractor.py`
> 势力对话风格提取器

**class DialogueStyleExtractor((_DialogueStyleExtractor))**
  _势力对话风格提取器（代理）_

### `.novel-extractor/extractors/emotion_arc_extractor.py`
> 情感曲线提取器

**class EmotionArcExtractor((_EmotionArcExtractor))**
  _情感曲线提取器（代理）_

### `.novel-extractor/extractors/foreshadow_pair_extractor.py`
> 伏笔回收配对提取器

**class ForeshadowPairExtractor((_ForeshadowPairExtractor))**
  _伏笔回收配对提取器（代理）_

### `.novel-extractor/extractors/power_cost_extractor.py`
> 力量体系代价提取器

**class PowerCostExtractor((_PowerCostExtractor))**
  _力量体系代价提取器（代理）_

### `.novel-extractor/extractors/technique_extractor.py`
> 创作技法精炼提取器

**class TechniqueExtractor((BaseExtractor))**
  _创作技法精炼提取器_
  - `__init__(self, incremental: bool = False)`
  - `get_extraction_stats(self) -> dict`  # 获取提取统计信息（增量模式相关统计）
  - `extract_from_novel(self, content: str, novel_id: str, novel_path) -> List[dict]`  # 从单本小说提取技法线索
  - `_detect_scene(self, content: str, scene_type: str) -> bool`  # 检测内容是否包含特定场景
  - `_extract_examples(
        self, content: str, keywords: List[str], max_examples: int = 3
    ) -> List[str]`  # 提取包含关键词的上下文示例
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 合并同类技法
  - `_infer_dimension(self, tech_name: str, scene_types: List[str]) -> str`  # 推断技法所属维度
  - `_generate_description(
        self, tech_name: str, dimension: str, examples: List[str]
    ) -> str`  # 生成技法描述
  - `extract_from_case_library(self, limit: int = None) -> List[dict]`  # 从案例库反推技法
  - `save_to_technique_library(self, techniques: List[dict]) -> int`  # 保存技法到技法库
  - `_load_existing_techniques(self) -> List[Dict[str, Any]]`  # 加载现有技法列表

**class TechniqueProgressTracker**
  _技法提取进度追踪器_
  - `__init__(self, progress_file: str = "technique_progress.json")`
  - `_load_progress(self) -> dict`
  - `mark_novel_processed(self, novel_name: str)`
  - `is_novel_processed(self, novel_name: str) -> bool`
  - `get_unprocessed_novels(self, all_novels: list) -> list`
  - `_save_progress(self)`
  - `update_technique_count(self, count: int)`

**class TechniqueQualityFilter**
  _技法质量过滤器_
  - `__init__(self, existing_techniques: list)`
  - `is_duplicate(self, technique: dict) -> bool`  # 检查是否与现有技法重复
  - `_calculate_similarity(self, text1: str, text2: str) -> float`  # 简单文本相似度计算（Jaccard）
  - `filter_techniques(self, techniques: list) -> list`  # 过滤重复技法

- `def extract_techniques_from_novels(limit: int = None)`  # 从小说提取技法

- `def extract_techniques_from_cases(limit: int = None)`  # 从案例库反推技法

### `.novel-extractor/extractors/vocabulary_extractor.py`
> 力量体系词汇提取器

**class VocabularyExtractor((_VocabularyExtractor))**
  _力量体系词汇提取器（代理）_

### `.novel-extractor/extractors/worldview_element_extractor.py`
> 世界观元素提取器 v3.0

**class WorldviewElementExtractor((BaseExtractor))**
  _世界观元素提取器 v2.0_
  - `__init__(self)`
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[Dict]`  # 从小说提取世界观元素（频次统计模式）
  - `process_extracted(self, items: List[Dict]) -> List[Dict]`  # 处理提取结果 - 跨小说去重合并
  - `_infer_type(self, name: str) -> str`  # 推断元素类型（兼容旧代码）

### `.novel-extractor/foreshadow_pair_extractor.py`
> 伏笔回收配对提取器

**class ForeshadowPairExtractor((BaseExtractor))**
  _伏笔回收配对提取器_
  - `__init__(self)`
  - `_find_foreshadow_candidates(self, content: str) -> List[Dict]`  # 寻找伏笔候选
  - `_find_payoff_candidates(self, content: str) -> List[Dict]`  # 寻找回收候选
  - `_calculate_similarity(self, text1: str, text2: str) -> float`  # 计算文本相似度（简化版）
  - `_match_pairs(
        self, foreshadows: List[Dict], payoffs: List[Dict], content: str
    ) -> List[ForeshadowPair]`  # 匹配伏笔-回收配对
  - `_classify_relation(self, foreshadow: Dict, payoff: Dict) -> str`  # 分类伏笔类型
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取伏笔配对
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 按类型聚合
  - `_get_relation_description(self, relation_type: str) -> str`  # 获取关系类型描述

- `def extract_foreshadow_pairs(limit: int = None)`  # 提取伏笔配对

### `.novel-extractor/incremental_sync.py`
> 增量同步系统

**class IncrementalSyncManager**
  _增量同步管理器_
  - `__init__(self)`
  - `_load_index(self) -> Dict[str, NovelIndex]`  # 加载索引
  - `_save_index(self)`  # 保存索引
  - `_generate_novel_id(self, path: Path) -> str`  # 生成小说ID
  - `scan_new_novels(self) -> Dict[str, List[Path]]`  # 扫描新小说
  - `get_pending_novels(self, dimension_id: str = None) -> List[Path]`  # 获取待处理的小说
  - `mark_processed(self, novel_id: str, dimension_id: str)`  # 标记已处理
  - `get_status(self) -> Dict[str, Any]`  # 获取状态
  - `process_new_novels(
        self, dimension_id: str = None, priority: str = None, limit: int = None
    )`  # 处理新小说

- `def main()`

- `def _run_scene_discovery(novel_paths: List[Path])`  # 运行场景发现器

### `.novel-extractor/noise_filter.py`
> 噪音过滤脚本

- `def filter_worldview_element(item: Dict) -> Dict`  # 过滤世界观元素噪音

- `def filter_character_relation(item: Dict) -> Dict`  # 过滤人物关系噪音

- `def filter_generic(item: Dict, dimension: str) -> Dict`  # 通用噪音过滤

- `def filter_dimension(dimension: str) -> Dict`  # 过滤单个维度的噪音

- `def filter_all() -> Dict`  # 过滤所有维度

- `def get_status() -> Dict`  # 获取噪音过滤状态

- `def print_status()`  # 打印状态

### `.novel-extractor/parallel_sync.py`
> 并行入库脚本 - 同时入库多个维度

- `def run_parallel(dimensions: list, max_workers: int = 3)`  # 并行入库多个维度

- `def main()`

### `.novel-extractor/power_cost_extractor.py`
> 力量体系代价提取器

**class PowerCostExtractor((BaseExtractor))**
  _力量体系代价提取器_
  - `__init__(self)`
  - `_detect_power_type(self, text: str) -> str`  # 检测文本中的力量类型，找不到时返回'通用
  - `_detect_cost_expression(self, text: str, power_type: str) -> List[str]`  # 检测代价表现
  - `_find_cost_context(self, content: str, cost: str) -> Tuple[str, str]`  # 查找代价的上下文和触发条件
  - `_extract_battle_scenes(self, content: str) -> List[str]`  # 提取战斗场景
  - `_extract_cost_pairs(self, content: str, power_type: str = None) -> List[PowerCost]`  # 提取力量使用-代价配对
  - `_classify_cost(self, cost_expr: str, power_type: str) -> str`  # 分类代价类型
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取力量代价
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 按力量体系聚合
  - `_get_common_triggers(self, expressions: List[dict]) -> List[str]`  # 获取常见触发条件

- `def generate_cost_template(power_type: str, intensity: str = "medium") -> str`  # 生成力量代价描写模板

- `def extract_power_costs(limit: int = None)`  # 提取力量代价

### `.novel-extractor/run.py`
> 众生界 - 完整小说提炼系统 v2.0

- `def create_extractor(dim_id: str)`  # 创建提取器实例（延迟导入避免循环依赖）

- `def print_banner()`  # 打印横幅

- `def print_status()`  # 打印系统状态

- `def run_extraction(
    dimension: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    resume: bool = True,
)`  # 运行提炼

- `def run_sync()`  # 运行增量同步

- `def generate_report()`  # 生成提炼报告

- `def main()`

### `.novel-extractor/run_clean.py`
> 小说清洗流程入口脚本

**class NovelCleanPipeline**
  _小说清洗流程管道_
  - `__init__(self)`  # 初始化清洗管道
  - `clean_single(self, file_path: Path) -> Dict[str, Any]`  # 清洗单个小说文件
  - `run(self, limit: int = None, verbose: bool = True) -> Dict[str, Any]`  # 执行清洗流程
  - `_save_log(self)`  # 保存清洗日志
  - `_print_stats(self)`  # 打印统计结果
  - `get_status(self) -> Dict[str, Any]`  # 获取当前状态

- `def print_status()`  # 打印当前状态

- `def main()`  # 主入口

### `.novel-extractor/run_extractor.py`
> 小说提炼系统 - 主入口

- `def print_banner()`  # 打印横幅

- `def print_status()`  # 打印系统状态

- `def create_batch_extractor() -> BatchExtractor`  # 创建批量提取器并注册所有提取器

- `def run_extraction(
    priority: Optional[str] = None,
    dimension: Optional[str] = None,
    limit: Optional[int] = None,
    resume: bool = True,
)`  # 运行提炼

- `def generate_report()`  # 生成提炼报告

- `def main()`

### `.novel-extractor/scorers/quality_scorer.py`
> 质量评分器 - 压缩率检测、信息密度评分、结构完整性评分、语言质量评分

**class QualityScorer**
  _质量评分器_
  - `__init__(self, keywords: Optional[List[str]] = None)`  # 初始化评分器
  - `score(self, text: str) -> Dict`  # 计算综合质量评分
  - `_score_compression(self, text: str) -> Dict`  # 压缩率评分
  - `_score_density(self, text: str) -> float`  # 信息密度评分
  - `_score_structure(self, text: str) -> float`  # 结构完整性评分
  - `_score_language(self, text: str) -> float`  # 语言质量评分
  - `_get_failure_reason(self, scores: Dict) -> str`  # 生成失败原因
  - `batch_score(self, texts: List[str]) -> List[Dict]`  # 批量评分
  - `get_stats(self, results: List[Dict]) -> Dict`  # 统计批量评分结果

- `def score_text(text: str) -> Dict`  # 快速评分单个文本

- `def score_batch(texts: List[str]) -> List[Dict]`  # 快速批量评分

### `.novel-extractor/sync_to_qdrant.py`
> 提取数据入库 Qdrant 向量数据库

**class ExtractorSyncManager**
  _提取数据入库管理器_
  - `__init__(self, use_docker: bool = True)`
  - `_get_client(self) -> QdrantClient`  # 获取 Qdrant 客户端
  - `_load_model(self, use_gpu: bool = True)`  # 加载 BGE-M3 模型（支持GPU加速）
  - `_create_collection(self, collection_name: str) -> bool`  # 创建 Collection
  - `sync_dimension(
        self,
        dimension_id: str,
        rebuild: bool = False,
        chunk_size: int = 5000,
        resume: bool = True,
        use_filtered: bool = None,  # 是否使用过滤后的数据
    ) -> int`  # 同步单个维度（分块处理，支持断点续传）
  - `_build_text(self, item: Dict, config: Dict) -> str`  # 构建用于编码的文本
  - `_build_payload(self, item: Dict, config: Dict, text: str) -> Dict`  # 构建 payload
  - `sync_all(self, rebuild: bool = True) -> Dict[str, int]`  # 同步所有维度
  - `get_status(self) -> Dict[str, Any]`  # 获取入库状态
  - `print_status(self)`  # 打印状态

- `def main()`

### `.novel-extractor/test_retrieval.py`

- `def load_config()`

- `def test_retrieval()`

### `.novel-extractor/tests/test_mobi_support.py`

**class DummyExtractor((be.BaseExtractor))**
  - `__init__(self)`
  - `extract_from_novel(self, content, novel_id, novel_path)`
  - `process_extracted(self, items)`

- `def test_scan_novels_includes_mobi(tmp_path, monkeypatch)`

- `def test_read_novel_mobi_returns_path()`

### `.novel-extractor/validators/ingestion_validator.py`

**class IngestionValidator**
  _入库校验器_
  - `__init__(self, config_path: Optional[str] = None)`  # 初始化校验器
  - `_load_config(self, config_path: Optional[str]) -> Dict[str, Any]`  # 加载配置
  - `_load_noise_features(self) -> List[str]`  # 加载噪音特征词列表
  - `_load_noise_threshold(self) -> float`  # 加载噪音阈值
  - `_patterns_from_features(self) -> List[str]`  # 将噪音特征词转换为正则表达式模式
  - `_check_noise(self, text: str) -> ValidationResult`  # 单条数据噪音检测
  - `validate_batch(
        self, data_items: List[Dict[str, Any]], content_key: str = "content"
    ) -> BatchValidationResult`  # 批量验证数据
  - `validate_single(self, content: str) -> ValidationResult`  # 验证单条数据
  - `get_config_info(self) -> Dict[str, Any]`  # 获取当前配置信息

- `def validate_batch(
    data_items: List[Dict[str, Any]],
    content_key: str = "content",
    config_path: Optional[str] = None,
) -> BatchValidationResult`  # 便捷函数：批量验证数据

- `def validate_single(
    content: str, config_path: Optional[str] = None
) -> ValidationResult`  # 便捷函数：验证单条数据

### `.novel-extractor/validators/novel_validator.py`
> 小说内容验证器模块

**class NovelValidator**
  _小说内容验证器_
  - `__init__(self, config_path: Optional[str] = None)`  # 初始化验证器
  - `_load_config(self, config_path: Optional[str] = None) -> dict[str, Any]`  # 加载配置文件
  - `check_chinese_ratio(self, text: str) -> dict[str, Any]`  # 检测文本中的中文比例
  - `check_novel_features(self, text: str) -> dict[str, Any]`  # 检测文本中的小说特征词数量
  - `validate(self, text: str) -> ValidationResult`  # 执行综合验证
  - `validate_file(self, file_path: str) -> ValidationResult`  # 验证文件内容
  - `get_config_info(self) -> dict[str, Any]`  # 获取当前配置信息

- `def validate_novel(text: str, config_path: Optional[str] = None) -> ValidationResult`  # 快速验证函数

- `def validate_novel_file(
    file_path: str, config_path: Optional[str] = None
) -> ValidationResult`  # 快速验证文件函数

### `.novel-extractor/vocabulary_extractor.py`
> 力量体系词汇提取器

**class VocabularyExtractor((BaseExtractor))**
  _力量体系词汇提取器 v2.0_
  - `__init__(self)`
  - `_load_known_vocabulary(self) -> Dict[str, Dict[str, List[str]]]`  # 加载已知词汇
  - `_detect_power_type(self, text: str) -> Optional[str]`  # 检测文本中的力量类型
  - `_detect_genre(self, content: str) -> str`  # 检测小说题材
  - `_extract_terms(
        self, content: str, category: str, patterns: List[str]
    ) -> Dict[str, int]`  # 提取特定类别的词汇
  - `_get_term_context(self, content: str, term: str) -> List[str]`  # 获取词汇上下文
  - `extract_from_novel(
        self, content: str, novel_id: str, novel_path: Path
    ) -> List[dict]`  # 从小说提取词汇
  - `process_extracted(self, items: List[dict]) -> List[dict]`  # 处理提取结果 - 去重合并

- `def extract_vocabulary(limit: int = None)`  # 提取力量词汇