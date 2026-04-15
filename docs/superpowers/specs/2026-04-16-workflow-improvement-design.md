# 工作流全面改进设计

**日期**：2026-04-16  
**状态**：已批准，待实施

---

## 目标

解决当前对话驱动创作工作流中的 7 类问题，按用户影响频率优先排序。所有改动均服务于同一运行模式：**OpenCode/Claude 是主程序，Python 是工具层**。

---

## 架构定位

### 改动边界

```
Skill 层（C:\Users\39477\.agents\skills\）
  novel-workflow/SKILL.md     ← P1/P2/P3/P4/P5/P6/P7 均有改动
  novelist-shared/SKILL.md    ← 不动
  novelist-*/SKILL.md         ← 不动
  novelist-evaluator/SKILL.md ← 不动

Python 工具层（D:\动画\众生界\）
  .vectorstore/core/workflow.py              ← P2 修复 sys.path 说明
  .vectorstore/core/creation_context_api.py  ← P6 新增
  core/feedback/experience_writer.py         ← P1 加 schema 验证
  schemas/experience_log_schema.json         ← P1 新增
  scripts/chapter_state_tracker.py           ← P5 新增
  chapter_states.json（项目根）              ← P5 新增（运行时生成）
```

### 核心原则

- Skill 文件改动**只在现有节点上插入新规则**，不重写现有流程结构
- Python 工具层**只提供更好的工具**，不改变 OpenCode 是决策主体这一事实
- 每个改进点独立可验证，完成一个可单独测试

---

## P1：经验日志 Schema 标准化

### 问题

`novel-workflow/SKILL.md` 阶段8写入的 JSON 格式无定义。阶段2.5 读取时用 `.get()` 静默吞掉格式错误，积累几章后经验检索完全失效。

### 改动

**新增 `D:\动画\众生界\schemas\experience_log_schema.json`：**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema",
  "type": "object",
  "required": ["chapter", "scene_types", "what_worked", "what_didnt_work", "for_next_chapter"],
  "properties": {
    "chapter": {
      "type": "string",
      "description": "章节标识，如"第1章""
    },
    "scene_types": {
      "type": "array",
      "items": {"type": "string"},
      "description": "本章涉及的场景类型列表"
    },
    "what_worked": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["content", "scene_type"],
        "properties": {
          "content": {"type": "string"},
          "scene_type": {"type": "string"}
        }
      }
    },
    "what_didnt_work": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["content", "scene_type"],
        "properties": {
          "content": {"type": "string"},
          "scene_type": {"type": "string"}
        }
      }
    },
    "insights": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["content", "scene_condition"],
        "properties": {
          "content": {"type": "string"},
          "scene_condition": {"type": "string"}
        }
      }
    },
    "for_next_chapter": {
      "type": "array",
      "items": {"type": "string"}
    }
  }
}
```

**修改 `core/feedback/experience_writer.py`：**

在 `write_chapter_experience()` 方法写入前加 schema 校验。校验失败时抛出 `ValueError` 并打印缺失字段名，不静默跳过。

**修改 `novel-workflow/SKILL.md` 阶段8：**

在"经验写入"步骤末尾加入：

```
⚠️ 写入格式要求：
- 必须包含字段：chapter、scene_types、what_worked、what_didnt_work、for_next_chapter
- what_worked / what_didnt_work 每条必须有 content 和 scene_type
- insights 每条必须有 content 和 scene_condition
- 参考 schemas/experience_log_schema.json

完整示例：
{
  "chapter": "第1章",
  "scene_types": ["战斗", "人物"],
  "what_worked": [
    {"content": "断臂作为代价有冲击力", "scene_type": "战斗"},
    {"content": "母亲死亡场景平静叙述反而更震撼", "scene_type": "人物"}
  ],
  "what_didnt_work": [
    {"content": "群体牺牲缺少具体姓名", "scene_type": "战斗"}
  ],
  "insights": [
    {"content": "群体牺牲必须有具体姓名和动作才能产生情感冲击",
     "scene_condition": "当描写群体牺牲场景时"}
  ],
  "for_next_chapter": [
    "配角牺牲必须有姓名和动作",
    "代价描写要具体化"
  ]
}
```

---

## P2：workflow.py import 路径修复

### 问题

`novel-workflow/SKILL.md` 里的调用示例：
```python
from workflow import create_scene_contract
```
直接执行会失败，因为 `.vectorstore/core/` 不在 Python 默认路径中。

实际确认：`create_scene_contract`、`save_scene_contract`、`validate_scene_contracts`、`get_scene_execution_plan`、`register_scene_start`、`register_scene_complete` 这六个模块级函数**已存在于 `workflow.py`**，无需新增。只需修复路径问题。

### 改动

**修改 `novel-workflow/SKILL.md`**，将所有 `from workflow import` 示例统一替换为：

```python
import sys
sys.path.insert(0, "D:/动画/众生界/.vectorstore/core")
sys.path.insert(0, "D:/动画/众生界")

from workflow import (
    create_scene_contract,
    save_scene_contract,
    validate_scene_contracts,
    get_scene_execution_plan,
    register_scene_start,
    register_scene_complete,
)
```

在 Skill 文件开头（四层架构调用之前）加入"环境准备"块，说明每次调用 Python 工具前需要先执行上述 path 设置。

---

## P3：Stage 0 退出机制

### 问题

阶段0讨论无终止条件，容易无限循环。

### 改动

**修改 `novel-workflow/SKILL.md` 阶段0**，在"讨论结束条件"部分增加：

#### 强制退出触发器（优先于其他条件）

| 触发 | 行动 |
|------|------|
| 用户说"可以开始了"/"就这样写"/"开始吧"/"行了" | 立即宣布进入阶段1，不再追问 |
| 用户提供了章节大纲文件路径 | 跳过讨论，直接读文件进入阶段1 |
| 讨论已进行 ≥ 3 轮且本轮无新信息 | OpenCode 主动宣布"信息足够，进入创作" |

#### 最小信息包定义

进入阶段1**只需要满足**：
1. 知道章节名（或编号）
2. 有大致的场景目标（一句话即可）

其余信息（具体冲突设计、代价形式、视角选择）在创作过程中补充，不需要在阶段0全部确定。

#### OpenCode 的角色边界

阶段0中 OpenCode 可以提出方向、挑战设计、坚持技法，但**不得以"信息不足"为由阻止进入创作**。最小信息包满足即可推进。

---

## P4：Phase 1.5 结构化冲突检测清单

### 问题

三个写手草稿的冲突检测完全依赖 OpenCode 自由判断，无结构化规则，易漏判。

### 改动

**修改 `novel-workflow/SKILL.md` Phase 1.5 部分**，将现有"检测规则"替换为强制执行的清单：

```
【Phase 1.5 冲突检测清单】（必须逐项检查，不可跳过）

□ R1 角色记忆/认知一致性
  检查：苍澜（世界观约束）与墨言（人物状态）对同一角色的描述是否矛盾
  示例冲突：苍澜说"血脉燃烧导致记忆消失"，墨言说"血牙清晰记得母亲每句话"

□ R2 物体状态一致性
  检查：三稿中提到的同一物体，其存在/位置/状态是否一致
  示例冲突：苍澜提到匕首已碎，剑尘（若参与）写"他拔出匕首"

□ R3 时间线因果性
  检查：三稿描述的事件顺序是否与场景契约中的 causal_chain 一致
  示例冲突：玄一说"觉醒发生在母亲死后"，苍澜说"觉醒触发了母亲死亡"

□ R4 能力边界一致性
  检查：角色使用的能力是否超出力量体系设定（参考当前章节的设定检索结果）
  示例冲突：血牙此时只是幼年，不应有成年血脉战士的能力

□ R5 人物数量一致性
  检查：三稿中出场人数是否与场景契约 character_manifest 的 total 一致
  示例冲突：契约登记 5 名入侵者，苍澜草稿写成了"七八个人"

检测结果格式：
✅ R1 无冲突
⚠️ R3 有冲突：[具体描述冲突内容]
...

判断规则：
- 0 个冲突 → 直接进入 Phase 2
- 1-2 个冲突 → 进入 Phase 1.6，主作家融合解决
- ≥ 3 个冲突 → 返回三写手重写（告知冲突清单）
```

---

## P5：跨章节人物状态追踪

### 问题

场景契约只管当前章节内的一致性。跨章节的人物状态（受伤、持有物品、关系变化）依赖 OpenCode 记忆，超出上下文窗口后自动遗忘。

### 改动

**新增 `D:\动画\众生界\scripts\chapter_state_tracker.py`：**

```python
"""跨章节人物状态追踪工具

维护 chapter_states.json，记录每章定稿后各角色的持续状态。
供 novel-workflow 阶段8写入、阶段3读取。
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

STATE_FILE = Path("D:/动画/众生界/chapter_states.json")

def load_states() -> Dict[str, Any]:
    """加载当前状态文件"""
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))

def update_character_state(
    character: str,
    chapter: str,
    updates: Dict[str, Any]
) -> None:
    """更新单个角色状态

    Args:
        character: 角色名
        chapter: 更新来源章节，如"第3章"
        updates: 要更新的字段，如 {"injuries": ["左臂骨折"], "items": ["龙晶×1"]}
    """
    states = load_states()
    if character not in states:
        states[character] = {}
    states[character].update(updates)
    states[character]["last_updated"] = chapter
    STATE_FILE.write_text(
        json.dumps(states, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def get_character_state(character: str) -> Optional[Dict[str, Any]]:
    """获取角色当前状态"""
    return load_states().get(character)

def get_all_active_states() -> Dict[str, Any]:
    """获取所有角色的当前状态，用于注入创作上下文"""
    return load_states()

def clear_resolved_states(chapter: str, characters: List[str]) -> None:
    """清除已解决的临时状态（如伤势痊愈）"""
    states = load_states()
    for char in characters:
        if char in states:
            states[char]["last_updated"] = chapter
    STATE_FILE.write_text(
        json.dumps(states, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
```

**状态文件结构（`chapter_states.json`）：**

```json
{
  "林枫": {
    "status": "alive",
    "injuries": ["左臂骨折（第3章受伤，预计第5章痊愈）"],
    "items": ["龙晶×1"],
    "relationships": ["血牙：结义兄弟（第2章）"],
    "last_updated": "第3章"
  },
  "血牙": {
    "status": "alive",
    "injuries": [],
    "items": [],
    "relationships": ["林枫：结义兄弟（第2章）"],
    "last_updated": "第2章"
  }
}
```

**修改 `novel-workflow/SKILL.md`：**

在**阶段3（设定自动检索）**开头加入：

```
【跨章节状态注入】
执行（章节 > 1 时）：
  from scripts.chapter_state_tracker import get_all_active_states
  states = get_all_active_states()

将 states 注入创作上下文，格式：
【角色持续状态（来自前章）】
- 林枫：左臂骨折（第3章受伤），持有龙晶×1
- 血牙：无持续伤势
```

在**阶段8（经验写入）**末尾加入：

```
【更新角色状态】
对本章发生了状态变化的角色，调用：
  from scripts.chapter_state_tracker import update_character_state
  update_character_state("角色名", "第N章", {
      "injuries": ["新增伤势或清空已痊愈"],
      "items": ["获得/失去的物品"],
      "relationships": ["新增关系"]
  })
```

---

## P6：Qdrant 上下文缓存（creation_context）

### 问题

9个阶段全在一个对话里，长篇小说到后期对话窗口满载，早期阶段的产出被挤出上下文。

### 方案

激活 Qdrant 作为阶段间的**工作记忆**：每个阶段完成后将关键产出向量化存入新建的 `creation_context` collection；下一阶段开始时按语义检索所需内容，不依赖对话历史。

### 改动

**新增 `.vectorstore/core/creation_context_api.py`：**

```python
"""创作上下文缓存 API

将每个阶段的关键产出存入 Qdrant creation_context collection，
供后续阶段按需检索，替代对对话历史的依赖。
"""
import json
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.config_loader import get_qdrant_url, get_model_path

COLLECTION_NAME = "creation_context"
VECTOR_SIZE = 1024


def _get_client():
    """获取 Qdrant 客户端"""
    from qdrant_client import QdrantClient
    return QdrantClient(url=get_qdrant_url())


def _get_embedder():
    """获取 BGE-M3 嵌入模型（懒加载）"""
    from FlagEmbedding import FlagModel
    model_path = get_model_path()
    return FlagModel(model_path, use_fp16=True)


def ensure_collection() -> None:
    """确保 creation_context collection 存在"""
    from qdrant_client.http import models
    client = _get_client()
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE
            )
        )


def save_stage_output(
    chapter: str,
    stage: str,
    content: Dict[str, Any]
) -> str:
    """将阶段产出存入 creation_context

    Args:
        chapter: 章节标识，如"第1章"
        stage: 阶段标识，如"stage0_goal"、"stage3_settings"、"scene_001_result"
        content: 要存储的内容字典

    Returns:
        存储的点 ID
    """
    ensure_collection()
    client = _get_client()
    embedder = _get_embedder()

    # 将 content 序列化为文本用于嵌入
    text = json.dumps(content, ensure_ascii=False)
    embedding = embedder.encode(text).tolist()

    point_id = str(uuid.uuid4())
    from qdrant_client.http import models
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "chapter": chapter,
                    "stage": stage,
                    "content": content,
                    "text_preview": text[:200],
                }
            )
        ]
    )
    return point_id


def query_context(
    chapter: str,
    query: str,
    top_k: int = 5,
    stage_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """检索与 query 最相关的上下文片段

    Args:
        chapter: 只检索该章节的上下文
        query: 语义查询，如"血牙的情感状态"
        top_k: 返回条数
        stage_filter: 可选，只检索特定阶段的产出

    Returns:
        按相关度排序的 content 列表
    """
    ensure_collection()
    client = _get_client()
    embedder = _get_embedder()

    embedding = embedder.encode(query).tolist()

    from qdrant_client.http import models
    filters = [models.FieldCondition(
        key="chapter",
        match=models.MatchValue(value=chapter)
    )]
    if stage_filter:
        filters.append(models.FieldCondition(
            key="stage",
            match=models.MatchValue(value=stage_filter)
        ))

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k,
        query_filter=models.Filter(must=filters)
    )
    return [r.payload["content"] for r in results]


def clear_chapter_context(chapter: str) -> int:
    """章节定稿后清理该章节的所有缓存

    Args:
        chapter: 章节标识

    Returns:
        删除的点数量
    """
    from qdrant_client.http import models
    client = _get_client()
    result = client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(
                    key="chapter",
                    match=models.MatchValue(value=chapter)
                )]
            )
        )
    )
    return result.operation_id
```

**修改 `novel-workflow/SKILL.md`**，在每个阶段加入存入/检索指令：

| 阶段 | 完成时存入 | 下阶段开始时检索 |
|------|-----------|----------------|
| 阶段0 | `save_stage_output(chapter, "stage0_goal", {"goal": ..., "decisions": ...})` | — |
| 阶段1 | `save_stage_output(chapter, "stage1_outline", {"scenes": ..., "characters": ...})` | 检索 stage0_goal |
| 阶段3 | `save_stage_output(chapter, "stage3_settings", {"characters": ..., "factions": ...})` | 检索 stage1_outline |
| 场景N完成 | `save_stage_output(chapter, f"scene_{N}_result", {"summary": ..., "contract_updates": ...})` | 检索前序场景结果 |
| 阶段6评审 | — | 检索所有 scene_*_result |
| 阶段7定稿后 | — | 调用 `clear_chapter_context(chapter)` 清理 |

**Skill 文件中的调用模板：**

```python
import sys
sys.path.insert(0, "D:/动画/众生界/.vectorstore/core")
from creation_context_api import save_stage_output, query_context, clear_chapter_context

# 存入（阶段完成时）
save_stage_output("第1章", "stage0_goal", {
    "goal": "血牙目睹母亲死亡，触发血脉初觉醒",
    "key_decisions": ["觉醒代价：遗忘母亲的名字", "视角：血牙第一视角"]
})

# 检索（新阶段开始时）
context = query_context("第1章", "血牙的情感状态和关键决策", top_k=3)
```

---

## P7：路径硬编码清理

### 问题

`novel-workflow/SKILL.md` 内有硬编码绝对路径，如：
```python
log_dir = Path("D:/动画/众生界/章节经验日志")
```
换环境即失效。

### 改动

**修改 `novel-workflow/SKILL.md`**，在文件最顶部（frontmatter 之后）加入项目根目录声明块：

```python
# ⚙️ 环境配置（每次运行前执行）
import sys
from pathlib import Path

# 项目根目录（修改此处适配新环境）
PROJECT_ROOT = Path("D:/动画/众生界")

# 工具路径注册
sys.path.insert(0, str(PROJECT_ROOT / ".vectorstore/core"))
sys.path.insert(0, str(PROJECT_ROOT))

# 常用路径（从 PROJECT_ROOT 派生，不硬编码）
LOG_DIR = PROJECT_ROOT / "章节经验日志"
OUTLINE_DIR = PROJECT_ROOT / "章节大纲"
SETTINGS_DIR = PROJECT_ROOT / "设定"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
SCHEMAS_DIR = PROJECT_ROOT / "schemas"
```

将文件中所有出现的 `"D:/动画/众生界/..."` 路径替换为 `PROJECT_ROOT / "..."` 的形式。

**修改 `scripts/chapter_state_tracker.py`（P5新增文件）**：

将 `STATE_FILE` 定义改为：

```python
import os
_project_root = Path(os.environ.get("NOVEL_PROJECT_ROOT", "D:/动画/众生界"))
STATE_FILE = _project_root / "chapter_states.json"
```

支持通过环境变量 `NOVEL_PROJECT_ROOT` 覆盖，不改代码即可适配新路径。

---

## 成功标准

| 改进点 | 验证方式 |
|--------|---------|
| P1 Schema | 写一条格式错误的经验日志，experience_writer.py 应抛出 ValueError 而非静默写入 |
| P2 Import | 在项目根目录执行 `python -c "import sys; sys.path.insert(0,'D:/动画/众生界/.vectorstore/core'); from workflow import create_scene_contract; print('OK')"` |
| P3 退出机制 | 在阶段0说"可以开始了"，OpenCode 不再追问直接进入阶段1 |
| P4 冲突检测 | Phase 1.5 产出中必须包含 R1-R5 逐项的 ✅/⚠️ 标记 |
| P5 状态追踪 | 第2章开始时，OpenCode 主动展示前章角色状态摘要 |
| P6 上下文缓存 | 第3章开始时，第1章的 stage0_goal 已从 Qdrant 检索，不依赖对话历史 |
| P7 路径清理 | `novel-workflow/SKILL.md` 中不再出现 `"D:/动画/众生界"` 的硬编码字符串 |

---

## 实施顺序

P1 → P2 → P3 → P4 → P5 → P6 → P7

每个改进点独立提交，完成验证后再进入下一个。P6 依赖 Qdrant 服务运行，实施前确认 Docker Qdrant 已启动。
