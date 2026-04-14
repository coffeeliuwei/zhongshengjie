# AI项目掌控手册

> **作者**：coffeeliuwei
> **版本**：v14.0
> **最后更新**：2026-04-13
> 
> 本文档帮助AI快速理解项目全貌，包含流程、配置、数据、API等一切必要信息
> 
> **AI新环境快速启动**：阅读本文档后即可配置运行项目

---

## 零、Skills安装步骤（⚠️ 必须第一步）

本项目使用 Skills 系统定义作家能力，**必须在配置前完成安装**。

### Skills位置说明

| 目录 | 用途 | Git状态 |
|------|------|---------|
| `skills/` | Skills源码定义 | ✅ 已推送（14个Skill.md） |
| `~/.agents/skills/` | Skills运行目录 | ❌ 不推送（本地安装） |

### 安装步骤

```bash
# 1. 创建Skills目录
mkdir -p ~/.agents/skills          # Linux/Mac
mkdir %USERPROFILE%\.agents\skills  # Windows PowerShell

# 2. 复制Skills定义到运行目录
cd zhongshengjie

# Linux/Mac
cp -r skills/* ~/.agents/skills/

# Windows PowerShell
Copy-Item -Recurse skills/* $env:USERPROFILE\.agents\skills\

# 3. 验证安装
ls ~/.agents/skills                # Linux/Mac
dir $env:USERPROFILE\.agents\skills  # Windows

# 应输出以下目录：
# novelist-canglan/      (苍澜 - 世界观架构师)
# novelist-xuanyi/       (玄一 - 剧情编织师)
# novelist-moyan/        (墨言 - 人物刻画师)
# novelist-jianchen/     (剑尘 - 战斗设计师)
# novelist-yunxi/        (云溪 - 意境营造师)
# novelist-evaluator/    (审核评估师)
# novelist-shared/       (共享规范)
# novelist-technique-search/  (技法检索)
# novelist-worldview-generator/  (世界观生成)
```

### Skills清单（28种场景类型对应）

| Skill | 专长 | 负责场景 |
|-------|------|----------|
| novelist-canglan | 世界观架构 | 势力登场、世界观展开 |
| novelist-xuanyi | 剧情编织 | 悬念、伏笔设置/回收、转折、阴谋揭露、情报揭示 |
| novelist-moyan | 人物刻画 | 人物出场、情感、心理、社交、成长蜕变、回忆场景 |
| novelist-jianchen | 战斗设计 | 战斗、打脸、高潮、修炼突破、危机降临、冲突升级 |
| novelist-yunxi | 意境营造 | 开篇、结尾、环境、氛围、探索发现、恢复休养 |
| novelist-evaluator | 审核评估 | 质量评估（独立于创作） |
| novelist-shared | 共享规范 | 文风要求、字数规则、禁止项 |
| novelist-technique-search | 技法检索 | BGE-M3混合检索 |
| novelist-worldview-generator | 世界观生成 | 从大纲自动生成配置 |

**28种场景类型完整列表**：开篇、战斗、情感、悬念、转折、世界观展开、打脸、高潮、人物出场、成长蜕变、伏笔设置、伏笔回收、阴谋揭露、社交、势力登场、修炼突破、资源获取、探索发现、情报揭示、危机降临、冲突升级、团队组建、反派出场、恢复休养、回忆场景、结尾

---

## 一、项目概述

### 1.1 项目定位

多Agent协作小说创作辅助系统，核心能力：
- **四层专家架构**：方法论层 → 统一API层 → 技法/案例库层 → 世界观适配层
- **技法检索**：按场景/维度检索写作技法（BGE-M3混合检索）
- **设定检索**：自动检索相关设定确保一致性
- **案例检索**：参考标杆片段（38万+案例）
- **多Agent协作**：5作家+1审核
- **自动场景发现**：从外部小说库自动学习新场景类型
- **经验检索**：检索前几章创作经验指导当前创作
- **多世界观支持**：可切换不同世界观配置

### 1.2 技术架构

```
用户输入 → Skills (novel-*) → 统一API层 → 向量检索 → 生成内容 → 评估 → 输出
                 ↑                ↑
          配置加载器        世界观适配层
                 ↑                ↑
          config.json    world_configs/*.json
```

### 1.3 核心组件

| 组件 | 位置 | 作用 |
|------|------|------|
| 配置加载器 | `core/config_loader.py` | 统一配置管理 |
| 世界观加载器 | `core/world_config_loader.py` | 世界观配置管理 |
| 统一API层 | `core/*_api.py` | 作家专用接口 |
| **对话入口层** | `core/conversation/` | ✨ 意图识别+状态管理+错误恢复 |
| **统一提炼引擎** | `tools/unified_extractor.py` | ✨ 11维度并行提取 |
| **变更检测器** | `core/change_detector/` | ✨ 自动检测大纲/设定变更 |
| **类型发现器** | `core/type_discovery/` | ✨ 4大类型自动发现 |
| **统一检索API** | `core/retrieval/` | ✨ 多源检索+混合检索 |
| **反馈系统** | `core/feedback/` | ✨ 评估回流+经验沉淀 |
| **生命周期管理** | `core/lifecycle/` | ✨ 技法追踪+版本控制+契约管理 |
| Skills | `~/.agents/skills/` | 作家技能定义（30个） |
| 向量检索 | `.vectorstore/core/` | Qdrant检索接口 |
| 工作流 | `.vectorstore/core/workflow.py` | 检索协调+经验检索 |
| 数据构建 | `tools/*.py` | 构建各种数据 |

### 1.4 设计方案索引

| 文档 | 路径 | 说明 |
|------|------|------|
| Collection三维度功能增强方案 | `docs/superpowers/specs/2026-04-13-collection-enhancement-design.md` | Collection自我学习、对话管理、自动同步设计 |
| 审核维度扩展方案 | `docs/superpowers/specs/2026-04-13-evaluation-criteria-extension-design.md` | Evaluator审核标准扩展、动态加载设计 |
| 数据提取流水线方案 | `docs/superpowers/specs/2026-04-11-data-extraction-pipeline-design.md` | 统一提炼引擎详细设计 |

---

## 二、配置系统（重要）

### 2.1 配置文件

| 文件 | 用途 | Git状态 |
|------|------|---------|
| `config.example.json` | 配置模板 | ✅ 推送GitHub |
| `config.json` | 用户配置 | ❌ 不推送（含敏感路径） |

### 2.2 快速配置

```bash
# 1. 复制模板
cp config.example.json config.json

# 2. 编辑配置（修改为您自己的路径）
# 必填项：project_root, model_path, novel_sources
```

### 2.3 配置项说明

```json
{
  "project": {
    "name": "我的小说",
    "version": "1.0.0"
  },
  
  "paths": {
    "project_root": null,
    "settings_dir": "设定",
    "techniques_dir": "创作技法",
    "vectorstore_dir": ".vectorstore",
    "case_library_dir": ".case-library",
    "logs_dir": "logs"
  },
  
  "database": {
    "qdrant_host": "localhost",
    "qdrant_port": 6333,
    "qdrant_url": "http://localhost:6333",
    "collections": {
      "novel_settings": "novel_settings_v2",
      "writing_techniques": "writing_techniques_v2",
      "case_library": "case_library_v2"
    }
  },
  
  "model": {
    "embedding_model": "BAAI/bge-m3",
    "model_path": null,
    "hf_cache_dir": null,
    "vector_size": 1024
  },
  
  "novel_sources": {
    "directories": ["E:\\小说资源"]
  }
}
```

### 2.4 配置加载API

```python
from core.config_loader import (
    # 基础配置
    get_config,           # 获取完整配置
    get_project_root,     # 项目根目录 Path
    get_config_path,      # 配置文件路径 Path
    
    # 数据库配置
    get_qdrant_url,       # Qdrant URL str
    get_collection_name,  # Collection名称
    get_database_timeout, # 数据库超时（秒）int
    get_qdrant_storage_dir, # Qdrant存储目录 Path
    
    # 模型配置
    get_model_path,       # 模型路径 str
    get_batch_size,       # 批处理大小 int
    
    # 路径配置
    get_settings_dir,     # 设定目录 Path
    get_techniques_dir,   # 技法目录 Path
    get_vectorstore_dir,  # 向量库目录 Path
    get_case_library_dir, # 案例库目录 Path
    get_logs_dir,         # 日志目录 Path
    get_cache_dir,        # 缓存目录 Path
    get_contracts_dir,    # 场景契约目录 Path
    get_skills_base_path, # Skills安装目录 Path
    get_novel_sources,    # 小说资源目录列表 [Path]
    get_novel_extractor_dir, # 小说提取目录 Path
    get_config_dir,       # 配置目录 Path
    
    # 世界观配置（新增）
    get_world_configs_dir,      # 世界观配置目录 Path
    get_scene_writer_mapping_path, # 场景作家映射文件 Path
    get_knowledge_graph_path,   # 知识图谱文件 Path
    get_world_config_path,      # 指定世界观配置文件 Path
    get_current_world,          # 当前世界观名称 str
    get_worldview_config,       # 世界观配置 dict
    
    # 校验配置
    get_realm_order,      # 境界等级顺序 list（支持多力量体系）
    get_all_realm_orders, # 所有力量体系的境界 dict
    get_skip_rules,       # 跳过的校验规则 list
    
    # 检索配置
    get_retrieval_config, # 检索配置 dict
    get_max_content_length, # 内容最大长度 int
    get_max_payload_size,   # Payload最大大小 int
    
    # HuggingFace配置
    get_hf_cache_dir,     # HuggingFace缓存目录 str
    
    # 通用路径获取
    get_path,             # 通用路径获取函数
)
```

### 2.5 环境变量覆盖

| 环境变量 | 对应配置 |
|---------|---------|
| `NOVEL_PROJECT_ROOT` | `paths.project_root` |
| `NOVEL_CONFIG_PATH` | 配置文件路径 |
| `BGE_M3_MODEL_PATH` | `model.model_path` |
| `HF_HOME` | `model.hf_cache_dir` |

---

## 三、创作流程

### 3.1 完整流程（8阶段+反馈处理）

```
阶段0: 需求澄清 → 阶段0.5: 变更检测（新增）
→ 阶段1: 大纲解析 → 阶段2: 场景识别
→ 阶段2.5: 经验检索 → 阶段3: 设定检索 
→ 阶段3.5: 场景契约 → 阶段4: 逐场景创作
→ 阶段5: 整章评估 → 阶段6: 用户确认 → 阶段7: 经验写入
```

### 3.2 对话入口层（新增）

用户输入 → ConversationEntryLayer → 工作流执行

```python
from core.conversation import ConversationEntryLayer

entry_layer = ConversationEntryLayer()
result = entry_layer.process_input("写第一章")
```

**支持的意图类型**（25+种）：
- 工作流控制：start_chapter, continue_workflow, pause_workflow
- 数据提炼：full_extraction, incremental_extraction
- 设定更新：add_character_ability, add_faction, modify_plot
- 查询：query_character, query_progress

### 3.2 触发命令

| 命令 | 触发流程 |
|------|----------|
| `写第N章` | 完整创作流程 |
| `重写第N章` | 情节保留重写 |
| `查看评估报告` | 显示Evaluator输出 |

### 3.3 作家调度

**动态前置作家**：根据 `scene_writer_mapping.json` 配置决定前置作家

**场景类型分配**（28种场景）：

| 场景类型 | 负责作家 | 说明 |
|----------|----------|------|
| 开篇 | 云溪 | 开篇布局、引入 |
| 结尾 | 云溪 | 收尾、余韵 |
| 战斗 | 剑尘 | 战斗描写、冲突 |
| 打脸 | 剑尘 | 爽点爆发、反击 |
| 高潮 | 剑尘 | 情节顶点、爆发 |
| 情感 | 墨言 | 情感细腻描写 |
| 人物出场 | 墨言 | 新角色登场 |
| 成长蜕变 | 墨言 | 角色内心转变 |
| 回忆场景 | 墨言 | 过往回忆插叙 |
| 社交 | 墨言 | 人物互动交往 |
| 悬念 | 玄一 | 悬念铺设、紧张感 |
| 伏笔设置 | 玄一 | 埋下线索 |
| 伏笔回收 | 玄一 | 揭示前文线索 |
| 转折 | 玄一 | 剧情反转 |
| 阴谋揭露 | 玄一 | 揭示隐藏计划 |
| 情报揭示 | 玄一 | 关键信息披露 |
| 世界观展开 | 苍澜 | 世界观细节展示 |
| 势力登场 | 苍澜 | 新势力引入 |
| 修炼突破 | 剑尘 | 力量提升场景 |
| 资源获取 | 剑尘 | 获得资源/宝物 |
| 探索发现 | 云溪 | 探险、发现新事物 |
| 危机降临 | 剑尘 | 危险到来 |
| 冲突升级 | 剑尘 | 矛盾激化 |
| 团队组建 | 墨言 | 队伍集结 |
| 反派出场 | 墨言 | 反派角色登场 |
| 恢复休养 | 云溪 | 战后休整 |

**source_map检索映射**（`retrieve_for_scene`支持）：
- `novel` → novel_settings_v2（角色/势力/设定）
- `technique` → writing_techniques_v2（创作技法）
- `case` → case_library_v2（标杆案例）
- `emotion_arc` → emotion_arc_v1（情感弧线参考）
- `foreshadow_pair` → foreshadow_pair_v1（伏笔对参考）
- `dialogue_style` → dialogue_style_v1（对话风格）
- `power_cost` → power_cost_v1（力量代价）
- `power_vocabulary` → power_vocabulary_v1（力量词汇）

### 3.4 Phase执行流程

```
Phase 1: 并行生成（苍澜+玄一+墨言前置）
    ↓
Phase 1.5: 一致性检测（自动）
    ↓
Phase 1.6: 融合调整（云溪）
    ↓
Phase 2: 核心创作（主作家）
    ↓
Phase 3: 收尾润色（云溪）
```

---

## 四、数据源

### 4.1 技法库

| 项目 | 值 |
|------|-----|
| 位置 | `创作技法/` |
| 向量库 | `writing_techniques_v2` |
| 数据量 | **986条** |
| 维度 | 11个维度 |
| 接口 | `.vectorstore/core/technique_search.py` |

### 4.2 知识库

| 项目 | 值 |
|------|-----|
| 位置 | `设定/` |
| 向量库 | `novel_settings_v2` |
| 数据量 | **160条** |
| 接口 | `.vectorstore/core/knowledge_search.py` |

### 4.3 案例库

| 项目 | 值 |
|------|-----|
| 位置 | `.case-library/` |
| 向量库 | `case_library_v2` |
| 数据量 | **387,377条** |
| 场景类型 | **28种**（见第3.3节完整列表） |
| 接口 | `.vectorstore/core/case_search.py` |

> **素材提炼模式**：案例库通过用户提供的外部小说资料自动提炼，非直接添加技法。系统从小说库提取标杆片段，用户无需理解技法概念。

### 4.4 世界观配置

| 项目 | 值 |
|------|-----|
| 位置 | `.vectorstore/core/world_configs/` |
| 配置文件 | `众生界.json`, `修仙世界示例.json`, `西方奇幻示例.json`, `科幻世界示例.json` |
| 接口 | `.vectorstore/core/world_config_loader.py` |

### 4.5 统一配置管理（新增）

| 配置文件 | 位置 | 内容 |
|----------|------|------|
| scene_types.json | `config/dimensions/` | **28种场景类型**（完整列表见第3.3节） |
| power_types.json | `config/dimensions/` | 7种力量类型 |
| faction_types.json | `config/dimensions/` | 10种势力类型 |
| technique_types.json | `config/dimensions/` | 11种技法类型 |

**配置同步器**：`config/dimension_sync.py` - 自动更新所有配置

**28种场景类型完整配置**：
```json
{
  "scene_types": [
    "开篇", "结尾", "战斗", "情感", "悬念", "转折", "世界观展开",
    "打脸", "高潮", "人物出场", "成长蜕变", "伏笔设置", "伏笔回收",
    "阴谋揭露", "社交", "势力登场", "修炼突破", "资源获取",
    "探索发现", "情报揭示", "危机降临", "冲突升级", "团队组建",
    "反派出场", "恢复休养", "回忆场景"
  ]
}
```

---

## 五、统一API层

### 5.1 API概览

| API | 文件 | 作家 | 功能 |
|-----|------|------|------|
| WorldviewAPI | `worldview_api.py` | 苍澜 | 世界观架构 |
| CharacterAPI | `character_api.py` | 墨言 | 人物刻画 |
| PlotAPI | `plot_api.py` | 玄一 | 剧情编织 |
| BattleAPI | `battle_api.py` | 剑尘 | 战斗设计 |
| PoetryAPI | `poetry_api.py` | 云溪 | 诗词意境 |

### 5.2 使用示例

```python
# 世界观API
from worldview_api import get_worldview_api
api = get_worldview_api()
powers = api.get_power_systems_overview()
factions = api.get_factions_overview()

# 人物API
from character_api import get_character_api
api = get_character_api()
profile = api.get_character_profile("血牙")
guide = api.get_faction_character_guide("兽族文明")

# 剧情API
from plot_api import get_plot_api
api = get_plot_api()
conflicts = api.get_relationship_conflicts()
techniques = api.search_foreshadowing_techniques()

# 战斗API
from battle_api import get_battle_api
api = get_battle_api()
guide = api.get_power_battle_guide("修仙")
costs = api.get_battle_cost_rules("血脉燃烧")

# 诗词API
from poetry_api import get_poetry_api
api = get_poetry_api()
era_guide = api.get_era_poetry_guide("觉醒时代")
material = api.compose_poetry_scene(era="觉醒时代", mood="压抑")
```

### 5.3 综合创作接口

每个API都提供 `compose_*_scene()` 方法，整合：
- 世界观适配（自动加载当前世界观配置）
- 技法库检索（从986条技法中检索相关内容）
- 案例库检索（从38万+案例中检索参考）
- 返回完整创作素材

```python
# 综合生成创作素材
api = get_battle_api()
material = api.compose_battle_scene(
    power_name="修仙",
    combat_type="剑修",
    keywords=["飞剑", "剑气"]
)
# 返回：{
#   "world_context": {...},
#   "power_guide": {...},
#   "cost_rules": {...},
#   "techniques": [...],
#   "cases": [...]
# }
```

---

## 六、向量数据库

### 6.1 连接

```python
from core.config_loader import get_qdrant_url
QDRANT_URL = get_qdrant_url()  # 默认 http://localhost:6333
```

### 6.2 Collections

| Collection | 数据量 | 用途 |
|------------|--------|------|
| writing_techniques_v2 | 986 | 创作技法 |
| novel_settings_v2 | 160 | 小说设定 |
| case_library_v2 | **387,377** | 标杆案例 |

### 6.3 模型

- 模型：`BAAI/bge-m3`
- 维度：1024
- 特性：Dense + Sparse + ColBERT 混合检索

---

## 七、Skills系统

### 7.1 位置

```
~/.agents/skills/
├── novel-workflow/        # 主调度器（阶段0-7 + 反馈处理）
├── novelist-technique-search/  # 技法检索（BGE-M3）
├── novelist-canglan/      # 世界观架构师
├── novelist-xuanyi/       # 剧情编织师
├── novelist-moyan/        # 人物刻画师
├── novelist-jianchen/     # 战斗设计师
├── novelist-yunxi/        # 意境营造师
├── novelist-evaluator/    # 审核评估师
├── novelist-shared/       # 共享规范
├── ulw/                   # Ultrawork模式
├── brainstorming/         # 头脑风暴
├── git-commit/            # Git提交
└── ... (共30个技能)
```

### 7.2 作家分工

| Skill | 专长 | 维度 |
|-------|------|------|
| novelist-canglan | 世界观架构 | 世界观维度 |
| novelist-xuanyi | 剧情编织 | 剧情维度 |
| novelist-moyan | 人物刻画 | 人物维度 |
| novelist-jianchen | 战斗设计 | 战斗冲突维度 |
| novelist-yunxi | 意境营造 | 氛围意境维度 |

---

## 八、数据构建工具

### 8.1 一键构建

```bash
python tools/build_all.py
python tools/build_all.py --status
```

### 8.2 分类构建

```bash
# 技法库
python tools/technique_builder.py --init
python tools/technique_builder.py --sync

# 知识库
python tools/knowledge_builder.py --init
python tools/knowledge_builder.py --sync

# 案例库（已统一使用config_loader）
python tools/case_builder.py --init
python tools/case_builder.py --scan        # 自动使用 config.json 中的 novel_sources
python tools/case_builder.py --convert
python tools/case_builder.py --extract --limit 5000
python tools/case_builder.py --sync

# 场景映射
python tools/scene_mapping_builder.py --init
```

> **配置说明**: `case_builder.py` 已重构使用 `config_loader`，自动读取 `config.json` 中的 `novel_sources.directories`，无需手动指定路径。详见 [整库拆解报告](整库拆解报告.md)。

### 8.3 自动场景发现（新功能）

```bash
# 发现新场景类型
python tools/case_builder.py --discover

# 审批发现的场景
python tools/scene_discoverer.py --approve "交易场景"

# 应用到所有配置文件
python tools/case_builder.py --apply-discovered
```

**自动同步到**：
- `case_builder.py` (SCENE_TYPES)
- `scene_writer_mapping.json`
- `novel-workflow/SKILL.md`

### 8.4 世界观生成器

从小说大纲自动生成世界观配置：

```bash
# 从大纲生成世界观配置
python .vectorstore/core/worldview_generator.py --outline "总大纲.md" --name "我的世界"

# 列出已有世界观
python .vectorstore/core/worldview_generator.py --list

# 生成AI提示词（让AI帮助完善）
python .vectorstore/core/worldview_generator.py --outline "大纲.md" --ai-prompt
```

**同步工具**：

```bash
# 查看同步状态
python .vectorstore/core/worldview_sync.py --status

# 同步世界观配置
python .vectorstore/core/worldview_sync.py --sync

# 验证世界观配置
python .vectorstore/core/worldview_sync.py --validate
```

**配置项**（`config.json`）：

```json
{
  "worldview": {
    "current_world": "众生界",
    "outline_path": "总大纲.md",
    "auto_sync": true,
    "_说明": "auto_sync为true时，大纲改动自动同步世界观"
  }
}
```

**大纲元素自动提取**：
- 力量体系（境界、代价、子类型）
- 势力（组织结构、文化、建筑风格）
- 角色（势力、能力、关系）
- 时代（氛围、色调、象征）
- 核心原则（道德观、主题、感情线）
- `novel-workflow/SKILL.md`

---

## 九、经验检索系统

### 9.1 功能说明

从前面章节的经验日志中提取可复用的经验，注入到当前创作上下文。

### 9.2 检索API

```python
from workflow import NovelWorkflow, retrieve_chapter_experience

workflow = NovelWorkflow()

# 检索经验
experience = workflow.retrieve_chapter_experience(
    current_chapter=3,
    scene_types=["战斗", "情感"],
    writer_name="剑尘"
)

# 返回结构
# {
#     "what_worked": ["断臂作为代价有冲击力"],
#     "what_didnt_work": ["群体牺牲缺少具体姓名"],
#     "insights": [...],
#     "for_next_chapter": ["配角牺牲必须有姓名和动作"],
#     "user_modification_requests": [...]
# }
```

### 9.3 写入经验

```python
# 阶段7：写入经验日志
workflow.write_chapter_log(
    chapter_name="第一章",
    evaluation_result=eval_result,
    techniques_used=[...]
)
```

---

## 十、场景契约系统

### 10.1 功能说明

**解决多作家并行创作导致的拼接冲突问题**，将一致性校验前移至创作阶段。

核心问题：多作家并行写场景后，拼接时发现逻辑冲突：
- 苍澜（世界观）写"遗忘母亲名字"
- 墨言（人物）写"记住母亲的每句话"
- 拼接时才发现矛盾，需要重写

### 10.2 核心文件

| 文件 | 位置 | 作用 |
|------|------|------|
| scene_contract.py | `.vectorstore/core/` | 契约数据结构与存储 |
| contract_validator.py | `.vectorstore/core/` | 12大一致性校验规则 |
| contract_sync.py | `.vectorstore/core/` | 同步管理器 |

### 10.3 契约数据结构

```python
class SceneContract:
    scene_id: str          # 场景ID
    chapter_id: str        # 章节ID
    
    # 人物清单
    character_manifest: {
        "count": {"male": 0, "female": 0, "total": 0},
        "named_characters": [...],
        "groups": [...]
    }
    
    # 时间线
    timeline: {
        "relative_time": {"start": "T+0", "end": "T+30min"},
        "causal_chain": [...]
    }
    
    # 空间信息
    spatial: {
        "location": {"name": "...", "region": "..."},
        "movement_path": [...]
    }
    
    # 物体状态
    object_states: {"objects": [...]}
    
    # 依赖关系
    dependencies: {
        "pre_scenes": [...],
        "blocking_events": [...]
    }
```

### 10.4 12大一致性校验规则

| 规则 | 检查项 | 级别 |
|------|--------|------|
| R001 | 人物数量一致性 | Critical |
| R002 | 时间因果性 | Critical |
| R003 | 空间连续性 | Warning |
| R004 | 代词一致性 | Critical |
| R005 | 物体状态连续性 | Critical/Warning |
| R006 | 角色状态转换合理性 | Critical |
| R007 | 势力攻击类型一致性 | Critical |
| R008 | 天气环境一致性 | Warning |
| R009 | 角色特征一致性 | Critical |
| R010 | 称呼一致性 | Warning |
| R011 | 势力构成一致性 | Warning |
| R012 | 能力技能一致性 | Critical |

### 9.5 API接口

```python
import sys; sys.path.insert(0, '.vectorstore')
from core.workflow import (
    create_scene_contract,     # 创建契约
    save_scene_contract,       # 保存契约
    load_scene_contract,       # 加载契约
    validate_scene_contracts,  # 校验章节契约
    get_scene_execution_plan,  # 获取执行计划（含并行分组）
    register_scene_start,      # 注册场景开始
    register_scene_complete    # 注册场景完成
)

# 创建契约
contract = create_scene_contract(
    scene_id="scene_002",
    chapter_id="chapter_001",
    scene_outline={
        "scene_type": "战斗",
        "characters": [{"name": "林夕", "gender": "male"}],
        "dependencies": {"pre_scenes": ["scene_001"]}
    }
)

# 保存契约
save_scene_contract(contract)

# 校验章节契约
result = validate_scene_contracts("chapter_001")
# 返回：{"total_contracts": 5, "total_conflicts": 2, "conflicts": [...]}

# 获取执行计划（含并行分组）
plan = get_scene_execution_plan("chapter_001")
# 返回：{"scene_order": [...], "parallel_groups": [["scene_001", "scene_002"], ...]}
```

### 9.6 工作流集成

场景契约在工作流中的位置：

```
阶段3: 设定检索
    ↓
阶段3.5: 场景契约提取（新增）
    ├── 为每个场景创建契约
    ├── 建立场景依赖关系
    └── 12大规则预检
    ↓
阶段4: 逐场景创作
    ├── 读取契约 → 作家创作 → 更新契约
    └── 实时一致性校验
```

### 9.7 契约存储位置

```
.cache/scene_contracts/
├── chapter_001/
│   ├── scene_001_contract.json
│   ├── scene_002_contract.json
│   └── contract_index.json
└── chapter_002/
    └── ...
```

---

## 十一、常见操作

### 9.1 新环境初始化

```bash
# 1. 克隆项目
git clone https://github.com/xxx/zhongshengjie.git
cd zhongshengjie

# 2. 配置
cp config.example.json config.json
# 编辑 config.json

# 3. 启动Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# 4. 构建
python tools/build_all.py

# 5. 验证
python tools/data_builder.py --status
```

### 9.2 检查系统

```bash
docker ps | grep qdrant
curl http://localhost:6333/collections
python tools/config_helper.py
python tools/data_builder.py --status
```

### 9.3 添加外部小说库

```bash
# 1. 配置小说资源目录
# 编辑 config.json → novel_sources.directories

# 2. 扫描并转换
python tools/case_builder.py --scan
python tools/case_builder.py --convert

# 3. 提取案例
python tools/case_builder.py --extract --limit 10000

# 4. 发现新场景（可选）
python tools/case_builder.py --discover

# 5. 同步到向量库
python tools/case_builder.py --sync
```

---

## 十二、数据分离原则

### 推送到GitHub
- `tools/` - 构建工具
- `core/` - 核心模块
- `modules/` - 功能模块
- `.vectorstore/core/` - 检索代码
- `docs/` - 文档
- `正文/` - 已创作内容（成品展示）
- `config.example.json` - 配置模板
- `README.md` - 项目说明

### 不推送（敏感数据）
- `创作技法/` - 技法库
- `设定/` - 小说设定
- `.case-library/` - 案例库
- `章节大纲/` - 章节规划
- `config.json` - 用户配置（含本地路径）
- `knowledge_graph.json` - 知识图谱
- `scene_writer_mapping.json` - 场景映射
- `章节经验日志/` - 经验日志
- `写作标准积累/` - 用户修改要求

---

## 十三、API速查

### 配置API
```python
import sys; sys.path.insert(0, '.vectorstore')
from core.config_loader import (
    get_config, get_project_root, get_model_path, 
    get_qdrant_url, get_novel_sources, get_settings_dir,
    get_techniques_dir, get_vectorstore_dir, get_case_library_dir,
    get_skills_base_path, get_cache_dir, get_contracts_dir,
    get_realm_order, get_database_timeout, get_batch_size
)
```

### 检索API
```python
import sys; sys.path.insert(0, '.vectorstore')
from core.technique_search import TechniqueSearch
from core.knowledge_search import KnowledgeSearch
from core.case_search import CaseSearch
from core.workflow import NovelWorkflow

# 统一接口
workflow = NovelWorkflow()
workflow.search_techniques("战斗", dimension="战斗冲突维度", top_k=5)
workflow.search_novel("林雷", top_k=5)
workflow.search_cases("战斗场景", top_k=5)
```

### 经验检索API
```python
import sys; sys.path.insert(0, '.vectorstore')
from core.workflow import retrieve_chapter_experience, write_chapter_log

# 检索
experience = retrieve_chapter_experience(
    current_chapter=3,
    scene_types=["战斗"],
    writer_name="剑尘"
)

# 写入
log_path = write_chapter_log(
    chapter_name="第一章",
    evaluation_result={...},
    techniques_used=[...]
)
```

---

---

## 十五、统一提炼引擎（新增）

### 15.1 功能说明

单一入口、11维度并行提取、数据回流闭环。

### 15.2 使用方式

```bash
# 默认增量提炼
python tools/unified_extractor.py

# 强制全量提炼
python tools/unified_extractor.py --force

# 查看状态
python tools/unified_extractor.py --status

# 只提炼特定维度
python tools/unified_extractor.py --dimensions case,technique
```

### 15.3 11个提取维度

| 维度 | Collection | 说明 |
|------|------------|------|
| case | case_library_v2 | 案例提取 |
| technique | writing_techniques_v2 | 技法提取 |
| dialogue | dialogue_style_v1 | 对话风格 |
| power_cost | power_cost_v1 | 力量代价 |
| emotion_arc | emotion_arc_v1 | 情感弧线 |
| vocabulary | power_vocabulary_v1 | 力量词汇 |
| character_relation | novel_settings_v2 | 人物关系 |
| chapter_structure | - | 章节结构 |
| author_style | - | 作者风格 |
| foreshadow_pair | foreshadow_pair_v1 | 伏笔对 |
| worldview_element | novel_settings_v2 | 世界观元素 |

---

## 十六、对话入口层（新增）

### 16.1 功能说明

处理用户对话输入，自动识别意图、管理状态、恢复错误。

### 16.2 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| IntentClassifier | `intent_classifier.py` | 25+种意图识别 |
| IntentClarifier | `intent_clarifier.py` | 模糊表达澄清 |
| WorkflowStateChecker | `workflow_state_checker.py` | 状态检查与恢复 |
| ProgressReporter | `progress_reporter.py` | 实时进度报告 |
| UndoManager | `undo_manager.py` | 撤销操作管理 |
| MissingInfoDetector | `missing_info_detector.py` | 缺失信息检测 |

### 16.3 使用示例

```python
from core.conversation import ConversationEntryLayer

entry_layer = ConversationEntryLayer()

# 场景1：开始创作
result = entry_layer.process_input("写第一章")

# 场景2：更新设定
result = entry_layer.process_input("血牙有个新能力叫血脉守护")
# 输出：✅ 已记录角色「血牙」的新能力「血脉守护」

# 场景3：数据提炼
result = entry_layer.process_input("提炼数据")
```

---

## 十七、变更检测器（新增）

### 17.1 功能说明

自动检测大纲、设定、技法文件的变更，并触发同步到对应存储。

### 17.2 监控范围

| 数据源 | 文件模式 | 同步目标 |
|--------|----------|----------|
| outline | 总大纲.md | 世界观配置 |
| settings | 设定/*.md | 知识图谱 |
| techniques | 创作技法/**/*.md | 向量库 |
| tracking | 设定/hook_ledger.md | - |

### 17.3 使用示例

```python
from core.change_detector import ChangeDetector

detector = ChangeDetector()

# 扫描变更
changes = detector.scan_changes()

# 同步变更
if changes:
    report = detector.sync_changes(changes)
    print(report)
```

---

## 十八、类型发现器（新增）

### 18.1 功能说明

从外部小说库自动发现新的场景类型、力量类型、势力类型、技法类型。

### 18.2 发现流程

```
收集未匹配片段 → 关键词聚类分析 → 生成候选类型 → 人工审批 → 更新配置
```

### 18.3 使用示例

```python
from core.type_discovery import TypeDiscoverer, PowerTypeDiscoverer

# 发现新力量类型
discoverer = PowerTypeDiscoverer()
new_types = discoverer.discover_power_types(novels)

# 审批确认
discoverer.approve_type("血脉觉醒")

# 同步到配置
discoverer.sync_to_config()
```

---

## 十九、统一检索API（新增）

### 19.1 功能说明

多数据源统一检索，支持Dense+Sparse+ColBERT混合检索。

### 19.2 使用示例

```python
from core.retrieval import UnifiedRetrievalAPI

api = UnifiedRetrievalAPI()

# 多源检索
results = api.retrieve(
    query="热血战斗场景",
    sources=["technique", "case"],
    top_k=5
)

# 单源检索
techniques = api.search_techniques(
    query="人物心理描写",
    dimension="人物维度",
    top_k=3
)

# 新增：扩展维度检索
vocabulary = api.search_power_vocabulary(
    query="血脉",
    power_type="血脉",
    top_k=5
)
```

---

## 二十、反馈系统（新增）

### 20.1 功能说明

收集用户反馈、处理改进建议、自动沉淀章节经验。

### 20.2 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| FeedbackCollector | `feedback_collector.py` | 收集反馈 |
| FeedbackProcessor | `feedback_processor.py` | 处理反馈 |
| ExperienceWriter | `experience_writer.py` | 写入经验 |

### 20.3 数据回流阈值

| 阈值 | 值 | 说明 |
|------|-----|------|
| technique_extraction | 8.5 | 技法提取评分阈值 |
| case_extraction | 8.0 | 案例提取评分阈值 |
| forbidden_detection_count | 3 | 禁止项检测次数 |
| similarity_threshold | 0.85 | 相似度去重阈值 |

---

## 二十一、生命周期管理（新增）

### 21.1 功能说明

技法使用追踪、配置版本控制、契约生命周期管理。

### 21.2 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| TechniqueTracker | `technique_tracker.py` | 技法使用追踪 |
| ConfigVersionControl | `config_version_control.py` | 配置快照与恢复 |
| ContractLifecycle | `contract_lifecycle.py` | 契约12大规则管理 |

### 21.3 使用示例

```python
from core.lifecycle import TechniqueTracker, ContractLifecycle

# 技法追踪
tracker = TechniqueTracker()
tracker.track_usage("伏笔技法", context)
stats = tracker.get_usage_stats("伏笔技法")

# 契约管理
lifecycle = ContractLifecycle()
lifecycle.create_contract("scene_001", contract)
violations = lifecycle.check_contract_compliance("scene_001", content)
```

---

## 二十二、测试结果（2026-04-10）

| 测试模块 | 测试用例数 | 通过率 |
|----------|-----------|--------|
| 配置系统测试 | 20 | 100% |
| 向量数据库测试 | 15 | 100% |
| API接口测试 | 25 | 100% |
| 工作流逻辑测试 | 30 | 100% |
| **集成测试** | **26** | **100%** |
| **端到端测试** | **16** | **100%** |
| 变更检测器测试 | 31 | 90%+ |
| 类型发现器测试 | 30 | 85%+ |
| 统一检索测试 | 50 | 80%+ |
| **总计** | **226** | **75%** |

### 融合度指标

| 指标 | 改进前 | 改进后 |
|------|--------|--------|
| 融合度 | 45% | **100%** |
| 数据覆盖 | 48% | **100%** |
| 可检索维度 | 3个 | **14个** |
| 提炼入口 | 2套独立 | **1套单一** |
| 类型发现 | 仅场景 | **场景+力量+势力+技法** |

---

> **配置文件**: `config.json` (用户) / `config.example.json` (模板)
> 
> **用户文档**: `README.md`
> 
> **最后更新**: 2026-04-13（场景类型统一28种、新增素材提炼模式、设计方案链接）