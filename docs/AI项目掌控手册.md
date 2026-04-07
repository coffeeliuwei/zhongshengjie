# AI项目掌控手册

> 本文档帮助AI快速理解项目全貌，包含流程、配置、数据、API等一切必要信息
> 
> **AI新环境快速启动**：阅读本文档后即可配置运行项目
> 
> **最后更新**：2026-04-07

---

## 一、项目概述

### 1.1 项目定位

多Agent协作小说创作辅助系统，核心能力：
- **技法检索**：按场景/维度检索写作技法（BGE-M3混合检索）
- **设定检索**：自动检索相关设定确保一致性
- **案例检索**：参考标杆片段（38万+案例）
- **多Agent协作**：5作家+1审核
- **自动场景发现**：从外部小说库自动学习新场景类型
- **经验检索**：检索前几章创作经验指导当前创作

### 1.2 技术架构

```
用户输入 → Skills (novel-*) → 向量检索 → 生成内容 → 评估 → 输出
                ↑
         配置加载器 (core/config_loader.py)
                ↑
         config.json (用户配置)
```

### 1.3 核心组件

| 组件 | 位置 | 作用 |
|------|------|------|
| 配置加载器 | `core/config_loader.py` | 统一配置管理 |
| Skills | `~/.agents/skills/` | 作家技能定义（30个） |
| 向量检索 | `.vectorstore/core/` | Qdrant检索接口 |
| 工作流 | `.vectorstore/core/workflow.py` | 检索协调+经验检索 |
| 数据构建 | `tools/*.py` | 构建各种数据 |
| 场景发现 | `tools/scene_discoverer.py` | 自动发现新场景类型 |

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
    
    # 校验配置
    get_realm_order,      # 境界等级顺序 list
    get_skip_rules,       # 跳过的校验规则 list
    
    # 检索配置
    get_retrieval_config, # 检索配置 dict
    get_max_content_length, # 内容最大长度 int
    get_max_payload_size,   # Payload最大大小 int
    
    # HuggingFace配置
    get_hf_cache_dir,     # HuggingFace缓存目录 str
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

### 3.1 完整流程（7阶段+反馈处理）

```
阶段0: 需求澄清 → 阶段1: 大纲解析 → 阶段2: 场景识别
→ 阶段2.5: 经验检索（新增） → 阶段3: 设定检索 
→ 阶段4: 逐场景创作（Phase 1-3） → 阶段5: 整章评估
→ 阶段6: 用户确认 → 阶段7: 经验写入（新增）
```

### 3.2 触发命令

| 命令 | 触发流程 |
|------|----------|
| `写第N章` | 完整创作流程 |
| `重写第N章` | 情节保留重写 |
| `查看评估报告` | 显示Evaluator输出 |

### 3.3 作家调度

**动态前置作家**：根据 `scene_writer_mapping.json` 配置决定前置作家

**场景类型分配**（28种场景）：
- 开篇/结尾 → 云溪
- 人物/情感 → 墨言
- 战斗/修炼 → 剑尘
- 悬念/转折 → 玄一
- 世界观展开 → 苍澜

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
| 场景类型 | **28种** |
| 接口 | `.vectorstore/core/case_search.py` |

---

## 五、向量数据库

### 5.1 连接

```python
from core.config_loader import get_qdrant_url
QDRANT_URL = get_qdrant_url()  # 默认 http://localhost:6333
```

### 5.2 Collections

| Collection | 数据量 | 用途 |
|------------|--------|------|
| writing_techniques_v2 | 986 | 创作技法 |
| novel_settings_v2 | 160 | 小说设定 |
| case_library_v2 | **387,377** | 标杆案例 |

### 5.3 模型

- 模型：`BAAI/bge-m3`
- 维度：1024
- 特性：Dense + Sparse + ColBERT 混合检索

---

## 六、Skills系统

### 6.1 位置

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

### 6.2 作家分工

| Skill | 专长 | 维度 |
|-------|------|------|
| novelist-canglan | 世界观架构 | 世界观维度 |
| novelist-xuanyi | 剧情编织 | 剧情维度 |
| novelist-moyan | 人物刻画 | 人物维度 |
| novelist-jianchen | 战斗设计 | 战斗冲突维度 |
| novelist-yunxi | 意境营造 | 氛围意境维度 |

---

## 七、数据构建工具

### 7.1 一键构建

```bash
python tools/build_all.py
python tools/build_all.py --status
```

### 7.2 分类构建

```bash
# 技法库
python tools/technique_builder.py --init
python tools/technique_builder.py --sync

# 知识库
python tools/knowledge_builder.py --init
python tools/knowledge_builder.py --sync

# 案例库
python tools/case_builder.py --init
python tools/case_builder.py --scan "E:/小说资源"
python tools/case_builder.py --convert
python tools/case_builder.py --extract --limit 5000
python tools/case_builder.py --sync

# 场景映射
python tools/scene_mapping_builder.py --init
```

### 7.3 自动场景发现（新功能）

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

---

## 八、经验检索系统（新功能）

### 8.1 功能说明

从前面章节的经验日志中提取可复用的经验，注入到当前创作上下文。

### 8.2 检索API

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

### 8.3 写入经验

```python
# 阶段7：写入经验日志
workflow.write_chapter_log(
    chapter_name="第一章",
    evaluation_result=eval_result,
    techniques_used=[...]
)
```

---

## 九、场景契约系统（新功能）

### 9.1 功能说明

**解决多作家并行创作导致的拼接冲突问题**，将一致性校验前移至创作阶段。

核心问题：多作家并行写场景后，拼接时发现逻辑冲突：
- 苍澜（世界观）写"遗忘母亲名字"
- 墨言（人物）写"记住母亲的每句话"
- 拼接时才发现矛盾，需要重写

### 9.2 核心文件

| 文件 | 位置 | 作用 |
|------|------|------|
| scene_contract.py | `.vectorstore/core/` | 契约数据结构与存储 |
| contract_validator.py | `.vectorstore/core/` | 12大一致性校验规则 |
| contract_sync.py | `.vectorstore/core/` | 同步管理器 |

### 9.3 契约数据结构

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

### 9.4 12大一致性校验规则

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

## 十四、测试结果（2026-04-06）

| 测试模块 | 通过率 | 状态 |
|----------|--------|------|
| 文件文本测试 | 100% | ✅ |
| 配置系统测试 | 100% (13/13) | ✅ |
| 向量数据库测试 | 100% (10/10) | ✅ |
| API接口测试 | 94.7% (18/19) | ✅ |
| 工作流逻辑测试 | 75% (18/24) | ✅ |
| 数据构建工具测试 | 100% | ✅ |

**整体通过率**：85%+，系统可用

---

> **配置文件**: `config.json` (用户) / `config.example.json` (模板)
> 
> **用户文档**: `README.md`