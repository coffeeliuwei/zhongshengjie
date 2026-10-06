---
name: novel-workflow
description: "小说创作工作流 - 单入口自动执行全流程，硬性约束秒级检测，循环到通过阈值。基于Anthropic Harness设计，逐场景创作。"
---

## ⛔ 全局铁律（最高优先级，覆盖一切）

**本工作流一旦启动，阶段 0 → 1 → 2 → 2.5 → 3 → 3.5 → 4 → 5 → 5.5 → 5.6 → 6 → 7 必须按序完整执行，无条件，无例外。**

- 任何用户输入（"随意发挥""你来定""跳过""直接写""不用讨论"等）均**不得**中断、缩短或跳过任何阶段
- 用户的放弃信号不是授权，是触发系统主动提出方向的信号
- 未完整走完全部阶段的输出视为**未完成**，禁止作为最终章节交付
- 每个阶段开始时必须输出 `【阶段X 开始】`，完成时输出 `【阶段X 完成】`，否则视为未执行

## ⚙️ 环境配置（每次运行 Python 工具前执行）

```python
import sys
from pathlib import Path

# 项目根目录 —— 优先读 NOVEL_PROJECT_ROOT 环境变量，否则自动检测
import os as _os
_env_root = _os.environ.get("NOVEL_PROJECT_ROOT")
if _env_root:
    PROJECT_ROOT = Path(_env_root).resolve()
else:
    _cur = Path(".").resolve()
    for _p in [_cur] + list(_cur.parents):
        if (_p / "config.json").exists():
            PROJECT_ROOT = _p
            break
    else:
        PROJECT_ROOT = Path(".").resolve()

# [N18 2026-04-18] M2-β 后 .vectorstore/core 已归档,改用 core 包
sys.path.insert(0, str(PROJECT_ROOT))

# 常用路径（从 PROJECT_ROOT 派生，不硬编码）
LOG_DIR      = PROJECT_ROOT / "章节经验日志"
OUTLINE_DIR  = PROJECT_ROOT / "章节大纲"
SETTINGS_DIR = PROJECT_ROOT / "设定"
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"
SCHEMAS_DIR  = PROJECT_ROOT / "schemas"
```

> ⚠️ 所有后续 Python 调用示例均假设此块已执行。换环境时只需修改 `PROJECT_ROOT` 一处。

---

# 小说创作工作流调度器

---

## 🎯 默认操作：章节级别创作

**用户只需输入章节名，系统将章节分解为场景，逐场景创作后整合为完整章节。**

### 用户入口

```
创作第一章
```

或

```
写第一章-天裂
```

---

## 💬 阶段0：需求澄清（互相启发讨论）

**所有创作请求都触发讨论，再具体也有灵感涌现的空间。**

### 核心理念

用户和系统**双向协作**，通过对话让模糊方向逐步细化成可执行目标：
- 用户可以提出方向，系统也可以提出方向
- 系统有自己的审美和坚持，不只是被动执行
- 讨论直到双方都满意才进入创作阶段

### 讨论触发（所有请求）

| 输入类型 | 示例 | 系统响应 |
|----------|------|----------|
| **精确** | "写第一章-天裂，重点是血牙目睹母亲死亡的冲击" | 提出补充方向：节奏设计、情感层次、视角切换 |
| **模糊** | "写一个战斗场景，主角觉醒血脉" | 提出澄清问题：觉醒的是什么血脉？代价是什么？对手是谁？ |
| **抽象** | "我想突出牺牲的代价感" | 提出具体路径：群体牺牲有姓名技法、战斗沉淀段落设计 |

### 讨论流程

```
用户提出方向："我想写主角觉醒"
        ↓
系统提出方向/问题：
├── "觉醒的是什么血脉？建议：血脉-天裂（被入侵者破坏的天道残余）"
├── "觉醒的触发场景？建议：目睹母亲被肢解的仇恨爆发"
├── "觉醒的代价？建议：血脉吞噬记忆，忘记母亲的名字"
└── "这是一个方向，你觉得如何？"
        ↓
用户反馈：
├── 接受 → 系统记录，继续细化
├── 修改 → 系统调整，继续讨论
└── 拒绝 → 系统提出新方向
        ↓
循环讨论 → 双方都满意
        ↓
输出：明确的创作目标（写入创作上下文）
        ↓
进入【阶段1：章节大纲解析】
```

### 系统的角色

系统不是被动工具，而是**有审美和坚持的协作方**：
- 可以主动提出方向（不只是回答问题）
- 可以坚持某个技法的使用（如"这个场景必须用有代价胜利技法"）
- 可以挑战用户的设计（如"代价不够重，建议升级"）
- 可以拒绝执行（如"这个方向违反核心设定，建议修改"）

### 阶段0 结束条件（唯一合法出口）

用户对系统提出的创作方向给出任意回应（接受/修改/拒绝/沉默均算）后，系统完成方向记录，**立即无条件进入阶段1**。

⛔ 禁止以下行为作为阶段0的结束：
- 用户说"随意发挥"/"你来定"/"直接写" → 系统必须先主动提出至少3条具体创作方向，等用户任意回应后再进入阶段1
- 系统自行判断"信息足够"而跳过讨论 → 此条件已废除，不存在

---

### 章节工作流总览

```
用户输入："写第一章"
        ↓
【阶段0：需求澄清】（互相启发讨论）
├── 用户提出方向 OR 系统提出方向
├── 系统提问/建议 → 用户反馈
├── 循环讨论 → 双方满意
└── 输出：明确的创作目标
        ↓
【阶段1：章节大纲解析】
├── 读取：章节大纲/第一章-天裂大纲.md
├── 解析：章节信息、5个场景描述
├── 识别：涉及角色、势力、血脉
├── ★ 读取叙事台账多样性约束（新增）
│     import sys; sys.path.insert(0, ".")
│     from tools.narrative_ledger import get_diversity_constraints
│     ledger_block = get_diversity_constraints(next_chapter=章节号)
│     # ledger_block 非空时注入阶段2场景调度，作为额外约束
│     # 数据不足3章时自动返回空字符串（冷启动跳过）
└── 输出：结构化章节数据 + 多样性约束块
        ↓
【阶段2：场景类型识别】
├── 分析每个场景内容
├── 匹配 scene_writer_mapping.json
├── 确定场景类型 → 作家映射
└── 输出：场景调度计划
      ⚠️ 格式要求：每个场景条目必须包含 `type` 字段（字符串，如 "战斗"/"突破"/"情感"），
         供叙事台账 update_chapter() 收集 scene_types 使用。
         示例：{"id": "scene_001", "type": "战斗", "writer": "剑尘", ...}
        ↓
【阶段2.5：经验检索】（新增）
├── 检索：章节经验日志/前几章_log.json
├── 提取：what_worked、what_didnt_work、for_next_chapter
├── 过滤：与当前场景相关的经验
├── 合并：经验上下文 + 设定上下文
└── 输出：完整创作上下文
        ↓
【阶段3：设定自动检索】
├── 检索优先级：Qdrant → 本地数据 → 文件 → 待补充标记
├── 识别角色 → 检索角色设定
├── 识别势力 → 检索势力设定
├── 识别血脉 → 检索力量体系
└── 输出：创作上下文包
        ↓
【阶段3.5：场景契约提取】（新增）
├── 为每个场景创建契约（人物/时间/空间/物体状态）
├── 建立场景依赖关系
├── 12大一致性规则预检
└── 输出：场景契约集合
        ↓
【阶段3.7：作家风格包加载】（新增）
├── 读取 config/writers_style_config.yaml → 本章涉及写手的作家配比
├── 读取 docs/style_collection/author_styles.yaml → 作家档案
├── 按场景类型生成每位写手的风格上下文包
│   ├── 行为约束（按权重采样 6-8 条）
│   ├── 专属语言 quirk（1-2 条，制造人味）
│   ├── 风格锚点（场景类型匹配的段落密度参考）
│   └── AI套句黑名单（并集）
└── 输出：per-writer 风格包（注入 Phase 0 提示词）
        ↓
【阶段4：逐场景创作】

### 前序场景上下文注入（阶段4开头执行一次）

```python
python - <<'EOF'
from core.conversation.checkpoint_manager import CheckpointManager
import sys

session_id = "CURRENT_SESSION"   # 替换为实际 session_id，或从环境变量读取
chapter = CHAPTER_NUMBER          # 替换为当前章节号

mgr = CheckpointManager(session_id)
ctx = mgr.format_summaries_for_prompt(chapter)
if ctx:
    print(ctx)
else:
    print("（本章尚无已完成场景摘要，从第1场开始）")
EOF
```

将上述输出附加到每个场景的创作提示中（"已完成场景摘要"字段）。
⚠️ 严格顺序执行，禁止跨场景并行：场景N完成后才能开始场景N+1
⚠️ 禁止为不同场景启动 background task / subagent，所有场景在当前 session 内依次完成
├── 场景1 → 读取契约 → Phase执行 → 作家协作 → 内容 → 更新契约 → ★作者微确认
├── 场景2 → 读取契约 → Phase执行 → 作家协作 → 内容 → 更新契约 → ★作者微确认
├── 场景3 → 读取契约 → Phase执行 → 作家协作 → 内容 → 更新契约 → ★作者微确认
├── 场景4 → 读取契约 → Phase执行 → 作家协作 → 内容 → 更新契约 → ★作者微确认
└── 场景5 → 读取契约 → Phase执行 → 作家协作 → 内容 → 更新契约 → ★作者微确认
        ↓
【阶段5：整章整合】
├── 合并所有场景内容
├── 云溪全章润色（统一多作家文风，仅此一次）
└── 输出：完整章节
⛔ 禁止：阶段5完成后严禁向用户展示任何"满意/定稿/跳过"选项。无论用户是否表示满意，必须立即进入阶段5.5。
        ↓
【阶段5.5：三方协商 ★ 核心】（鉴赏师 + 评估师 + 作者并列）
├── 鉴赏师：读完整章 → 查反模板约束库(45条创意菜单) → 查记忆点库 → 输出N条创意建议
├── 评估师：只审鉴赏师的建议本身 → 标采纳/驳回/有条件 + 违规风险（不审整章）
├── 作者：三方拍板讨论
└── 输出：创意契约 JSON（preserve_list / rejected_list / 段落级定位 / 13维度豁免映射）
        ↓
【阶段5.6：鉴赏师派单改写 ★】
├── 对每条采纳建议派单：改第N段 → 剑尘/云溪 重写（MUST_PRESERVE标记）
├── 并行收回改写结果
└── 云溪接缝处理（仅被改写段落±1段，守 preserve_list，不做整章润色）
        ↓
【阶段6：整章评估】（带创意契约豁免）
├── 评估师13维度打分
├── preserve_list 区域 → 相关维度豁免（跳过）
├── ≥0.8 → 放行
├── <0.8 第1-2次 → 回5.6局部重写（契约不变）
├── <0.8 第3次 → 对话升级：[a]撤销采纳建议 / [b]author_force_pass / [c]整章重协商(回5.5)
└── 输出：评估通过版本
        ↓
【阶段7：用户确认与智能反馈处理】
├── 用户确认选项：
│   ├── [1] ✅ 满意，定稿
│   ├── [2] ❌ 整体不满意，重新规划（返回阶段0）
│   ├── [3] ✏️ 部分不满意，提供反馈
│   └── [4] 🔄 重写章节
├── 智能反馈处理（选项3）：
│   ├── 意图识别（修改层级 1-4）
│   ├── 反馈解析（满意/不满意分离）
│   ├── 满意度分离（建立内容掩码）
│   ├── 修改范围选择（用户选择策略）
│   ├── 智能修改执行
│   └── 追踪同步
├── 重写处理（选项4）：
│   ├── [A] 剧情保留重写
│   ├── [B] 剧情调整重写
│   ├── [C] 完全重新创作
│   └── [D] 参考原稿创作
└── 输出：用户满意的最终版本
        ↓
**定稿后立即执行——写入正文文件**：

1. 从 `config.json → paths.content_dir` 读取正文目录（默认 `正文/`）
2. 文件命名：`{content_dir}/第{N}章-{章名}.md`（N 与章名从阶段0需求澄清获取）
3. 写入完整章节内容（云溪润色后、经阶段5.6改写后的最终版本）
4. 写入成功后告知用户：

```
📄 章节已保存：正文/第{N}章-{章名}.md
→ 进入阶段8：经验写入
```

5. 若写入失败，告知用户具体错误路径，不阻塞阶段8
        ↓

### 章节 Checkpoint 清理（阶段7确认后执行）

```python
python -c "
from core.conversation.checkpoint_manager import CheckpointManager
n = CheckpointManager('CURRENT_SESSION').clear_chapter_checkpoints(CHAPTER_NUMBER)
print(f'已清理 {n} 个 checkpoint 文件')
"
```

        ↓
【阶段8：经验写入】
├── 记录：techniques_used、what_worked、what_didnt_work
├── 提取：for_next_chapter
├── 写入：章节经验日志/第N章_log.json
└── 输出：章节日志文件
```

---

## 核心架构

基于 Anthropic Harness 设计原则：

| 原则 | 实现方式 |
|------|----------|
| **Generator/Evaluator 分离** | 作家（Generator）专注创作，审核师（Evaluator）独立评估 |
| **任务分解** | 将场景分解为子任务，分配给对应专长的作家 |
| **迭代反馈** | Evaluator 提供具体反馈，Generator 根据反馈修改 |
| **硬性阈值** | 禁止项有明确的通过/失败标准 |

---


**注：以下为简化版阶段图，详细流程见上方章节工作流总览。**

## 工作流阶段

```
┌─────────────────────────────────────────────────────────────┐
│                      阶段0：准备阶段                          │
├─────────────────────────────────────────────────────────────┤
│ 输入：故事大纲、设定文件                                       │
│ 输出：章节任务列表                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      阶段1：创作阶段（Generator）              │
├─────────────────────────────────────────────────────────────┤
│ Step 1.1：任务分解 → 确定需要调用的作家                        │
│ Step 1.2：作家执行 → 按顺序/并行调用                          │
│ Step 1.3：内容整合 → 合并各作家输出                            │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      阶段2：审核阶段（Evaluator）              │
├─────────────────────────────────────────────────────────────┤
│ Step 2.1：禁止项检测 → 硬性阈值                               │
│ Step 2.2：技法评估 → 软性阈值                                 │
│ Step 2.3：生成反馈 → 具体修改建议                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │ 是否通过？       │
                    └─────────────────┘
                     ↓              ↓
                    否              是
                     ↓              ↓
              返回阶段1修改      输出最终版本
```

---

## 阶段2.5：经验检索（新增）

### 目的

从前面章节的经验日志中提取可复用的经验，注入到当前创作上下文。

### 触发条件

- 当前章节 > 1（第一章无前章经验）
- 存在前章经验日志文件

### 检索流程

```
确定当前章节号 N
        ↓
检索前3章日志：N-1, N-2, N-3
        ↓
提取每个日志中的：
├── what_worked（有效做法）
├── what_didnt_work（无效做法）
├── insights（可复用洞察）
└── for_next_chapter（给下一章建议）
        ↓
根据当前场景类型过滤：
├── 战斗场景 → 提取战斗相关经验
├── 人物场景 → 提取人物相关经验
├── 世界观场景 → 提取世界观相关经验
└── ...
        ↓
格式化为上下文
        ↓
注入到作家输入
```

### 检索函数

```python
import json
from pathlib import Path
from typing import List, Dict, Optional

def retrieve_chapter_experience(
    current_chapter: int, 
    scene_types: List[str]
) -> Dict[str, List[str]]:
    """
    检索前几章的经验日志
    
    Args:
        current_chapter: 当前章节号
        scene_types: 当前章节涉及的场景类型列表
    
    Returns:
        经验上下文字典
    """
    import json as _json
    _cfg = _json.loads(open("config.json", encoding="utf-8").read()) if Path("config.json").exists() else {}
    _exp_dir = _cfg.get("paths", {}).get("experience_dir", "章节经验日志")
    _root = _cfg.get("paths", {}).get("project_root", str(Path.cwd()))
    log_dir = Path(_root) / _exp_dir
    
    if not log_dir.exists():
        return {"what_worked": [], "what_didnt_work": [], "for_next_chapter": []}
    
    experiences = {
        "what_worked": [],
        "what_didnt_work": [],
        "insights": [],
        "for_next_chapter": []
    }
    
    # 检索前3章
    for chapter in range(current_chapter - 1, max(0, current_chapter - 4), -1):
        log_file = log_dir / f"第{chapter}章_log.json"
        
        if not log_file.exists():
            continue
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log = json.load(f)
            
            # 提取经验
            experiences["what_worked"].extend(log.get("what_worked", []))
            experiences["what_didnt_work"].extend(log.get("what_didnt_work", []))
            experiences["for_next_chapter"].extend(log.get("for_next_chapter", []))
            
            # 过滤与当前场景相关的洞察
            for insight in log.get("insights", []):
                if is_insight_relevant(insight, scene_types):
                    experiences["insights"].append(insight)
                    
        except Exception as e:
            print(f"[经验检索] 读取日志失败 {log_file}: {e}")
    
    return experiences

def is_insight_relevant(insight: Dict, scene_types: List[str]) -> bool:
    """判断洞察是否与当前场景相关"""
    scene_condition = insight.get("scene_condition", "")
    
    # 场景关键词映射
    scene_keywords = {
        "战斗": ["战斗", "代价", "胜利", "牺牲", "群体"],
        "人物": ["人物", "角色", "情感", "成长", "出场"],
        "世界观": ["世界观", "势力", "设定", "背景"],
        "剧情": ["剧情", "伏笔", "悬念", "反转"],
        "氛围": ["氛围", "意境", "描写", "环境"]
    }
    
    for scene_type in scene_types:
        keywords = scene_keywords.get(scene_type, [])
        for keyword in keywords:
            if keyword in scene_condition or keyword in insight.get("content", ""):
                return True
    
    return False

def format_experience_context(experiences: Dict) -> str:
    """格式化经验上下文"""
    if not any(experiences.values()):
        return ""
    
    context = "【前章经验参考】\n\n"
    
    if experiences["what_worked"]:
        context += "✅ 有效做法（可参考）：\n"
        for item in experiences["what_worked"][:5]:  # 最多5条
            context += f"  - {item}\n"
        context += "\n"
    
    if experiences["what_didnt_work"]:
        context += "⚠️ 避免重复错误：\n"
        for item in experiences["what_didnt_work"][:5]:
            context += f"  - {item}\n"
        context += "\n"
    
    if experiences["insights"]:
        context += "💡 可复用洞察：\n"
        for insight in experiences["insights"][:3]:
            context += f"  - {insight.get('content', '')}\n"
            context += f"    适用：{insight.get('scene_condition', '')}\n"
        context += "\n"
    
    if experiences["for_next_chapter"]:
        context += "📝 前章建议：\n"
        for item in experiences["for_next_chapter"][:5]:
            context += f"  - {item}\n"
    
    return context
```

### 注入作家上下文

```yaml
# 作家接收的输入（新增经验上下文）

任务信息:
  场景ID: "scene_002"
  任务类型: "战斗铺垫"
  目标字数: "1200-1500"
  
上下文:
  前文内容: "..."
  相关设定: "..."
  角色状态: "..."
  
  # 新增：前章经验
  前章经验: |
    【前章经验参考】
    
    ✅ 有效做法（可参考）：
      - 断臂作为代价有冲击力
      - 开场氛围铺垫到位
    
    ⚠️ 避免重复错误：
      - 群体牺牲缺少具体姓名
    
    💡 可复用洞察：
      - 群体牺牲必须有具体姓名和动作，才能产生情感冲击
        适用：当描写群体牺牲场景时
    
    📝 前章建议：
      - 配角牺牲必须有姓名和动作
      - 代价描写要具体化
  
要求:
  - 遵守角色设定
  - 参考前章经验
  - 避免重复前章错误
  - 符合章节大纲目标
```

### 本书一致性检索（search_own_chapters）

> 仅第2章起触发，第1章无已写章节可查。

在经验日志检索完成后，追加调用 `search_own_chapters()` 检索本书已写章节，获取：
- 同场景类型下已用过哪些技法（避免重复）
- 本书的声音/节奏基调（风格一致性参照）

```python
from modules.knowledge_base.search_manager import SearchManager

sm = SearchManager()
own_scenes = sm.search_own_chapters(
    scene_type=current_scene_type,   # 当前场景类型
    novel_name="众生界",
    exclude_chapter=current_chapter,  # 排除当前章节
    top_k=3,
)

# 提取已用技法列表，注入到写手 prompt 的「禁止重复」区
used_techniques = []
for scene in own_scenes:
    used_techniques.extend(scene.get("techniques_used", []))
used_techniques = list(set(used_techniques))  # 去重
```

将 `used_techniques` 注入写手 prompt：

```
【本书已用技法（本场景禁止重复使用）】
- ANTI_001（视角反叛·败者视角）← 第一章场景2已用
- ANTI_015（节奏反转·高潮留白）← 第一章场景3已用
请选择尚未使用的技法，或以不同方式应用。
```

---

## 阶段3.5：场景契约提取（新增）

### 目的

**解决多作家并行创作导致的拼接冲突问题**，将一致性校验前移至创作阶段。

### 核心问题

多作家并行写场景后，拼接时发现逻辑冲突：
- 苍澜（世界观）写"遗忘母亲名字"
- 墨言（人物）写"记住母亲的每句话"
- 拼接时才发现矛盾，需要重写

### 解决方案：场景契约

在每个场景创作前，提取关键一致性数据作为"契约"：
- 人物清单（数量、性别、状态）
- 时间线（相对时间、因果链）
- 空间信息（位置、移动路径）
- 物体状态（数量、位置、状态）
- 依赖关系（前置场景、阻塞事件）

### 契约数据结构

```python
class SceneContract:
    scene_id: str          # 场景ID
    chapter_id: str        # 章节ID
    
    # 人物清单
    character_manifest: {
        "count": {"male": 0, "female": 0, "child": 0, "total": 0},
        "named_characters": [
            {
                "id": "char_林夕",
                "name": "[示例角色B]",
                "gender": "male",
                "status": "alive",
                "pronoun": "他"
            }
        ],
        "groups": [
            {
                "id": "group_1",
                "description": "逃难村民",
                "count": 37,
                "status": "fleeing"
            }
        ]
    }
    
    # 时间线
    timeline: {
        "relative_time": {"start": "T+0", "end": "T+30min"},
        "causal_chain": [
            {"event": "入侵开始", "time": "T+0", "status": "completed"}
        ]
    }
    
    # 空间信息
    spatial: {
        "location": {"name": "[示例地点]", "region": "[势力/区域名]"},
        "movement_path": ["东门", "广场", "西门"]
    }
    
    # 物体状态
    object_states: {
        "objects": [
            {"id": "obj_匕首", "name": "匕首", "state": "hanging", "owner": "[示例角色B]"}
        ]
    }
    
    # 依赖关系
    dependencies: {
        "pre_scenes": ["scene_001"],
        "blocking_events": []
    }
```

### 12大一致性校验规则

| 规则 | 检查项 | 级别 |
|------|--------|------|
| **R001** | 人物数量一致性 | Critical |
| **R002** | 时间因果性 | Critical |
| **R003** | 空间连续性 | Warning |
| **R004** | 代词一致性 | Critical |
| **R005** | 物体状态连续性 | Critical/Warning |
| **R006** | 角色状态转换合理性 | Critical |
| **R007** | 势力攻击类型一致性 | Critical |
| **R008** | 天气环境一致性 | Warning |
| **R009** | 角色特征一致性 | Critical |
| **R010** | 称呼一致性 | Warning |
| **R011** | 势力构成一致性 | Warning |
| **R012** | 能力技能一致性 | Critical |

### 执行流程

```
【阶段3.5：场景契约提取】
        │
        ├── 1. 解析场景大纲
        │   ├── 提取人物列表
        │   ├── 提取时间信息
        │   ├── 提取空间信息
        │   └── 提取物体信息
        │
        ├── 2. 创建契约
        │   ├── create_scene_contract(scene_id, chapter_id, scene_outline)
        │   └── 填充契约数据
        │
        ├── 3. 建立依赖关系
        │   ├── 分析场景顺序
        │   └── 设置 pre_scenes / blocking_events
        │
        ├── 4. 一致性预检
        │   ├── validate_scene_contracts(chapter_id)
        │   └── 检测冲突 → 提示修复
        │
        └── 5. 保存契约
            └── .cache/scene_contracts/{chapter_id}/{scene_id}_contract.json
```

### 接口调用

```python
# 创建契约
from workflow import create_scene_contract

contract = create_scene_contract(
    scene_id="scene_002",
    chapter_id="chapter_001",
    scene_outline={
        "scene_type": "战斗",
        "characters": [
            {"name": "[示例角色B]", "gender": "male", "status": "alive"},
            {"name": "[示例角色A]", "gender": "male", "status": "alive"}
        ],
        "groups": [
            {"description": "入侵者", "count": 5}
        ],
        "location": {"name": "[示例地点]"},
        "dependencies": {"pre_scenes": ["scene_001"]}
    }
)

# 保存契约
from workflow import save_scene_contract
save_scene_contract(contract)

# 校验章节契约
from workflow import validate_scene_contracts
result = validate_scene_contracts("chapter_001")
# 返回：{"total_contracts": 5, "total_conflicts": 2, "conflicts": [...]}

# 获取执行计划（含并行分组）
from workflow import get_scene_execution_plan
plan = get_scene_execution_plan("chapter_001")
# 返回：{"scene_order": [...], "parallel_groups": [["scene_001", "scene_002"], ...]}
```

### 与阶段4的集成

```
【阶段4：逐场景创作】

对于每个场景：
        │
        ├── 1. 注册场景开始
        │   └── register_scene_start(chapter_id, scene_id)
        │       ├── 检查依赖场景是否完成
        │       ├── 检查契约一致性
        │       └── 返回契约数据给作家
        │
        ├── 2. 作家创作
        │   ├── 输入：契约数据 + 设定上下文
        │   └── 输出：场景内容
        │
        └── 3. 注册场景完成
            └── register_scene_complete(chapter_id, scene_id, updated_contract)
                ├── 更新契约（如状态变化）
                └── 记录检查点
```

---

## 阶段3.7：作家风格包加载（新增）

### 目的

在场景循环开始**之前**一次性为全章所有写手生成风格上下文包，避免每场景重复加载 YAML。
同时实现**去AI感**核心机制：让每位写手的输出向真实作家风格靠拢，破除批量感。

### 执行时机

- 阶段3.5（场景契约提取）完成后立即执行
- 阶段4（逐场景创作）开始前必须完成
- 全章只执行一次，输出缓存供所有场景 Phase 0 使用

### 调用方式

```python
from tools.style_injector import build_writer_style_context

# 为本章所有写手生成风格包（seed 用章节号保证同章内一致）
chapter_seed = chapter_number * 100  # 如第3章 → seed=300

style_packages = {}
for writer in ["苍澜", "玄一", "墨言", "剑尘", "云溪"]:
    style_packages[writer] = build_writer_style_context(
        writer=writer,
        scene_type=primary_scene_type,   # 本章主场景类型
        seed=chapter_seed,
    )
```

### 风格包内容结构

每位写手的风格包包含：

| 组件 | 来源 | 作用 |
|------|------|------|
| **行为约束（6-8条）** | `author_styles.yaml` 按配比采样 | 具体可执行的写作规则 |
| **语言 quirk（1-2条）** | 主配比作家的坏习惯 | 制造"人味"的语言特征 |
| **风格锚点** | 按场景类型选最匹配的 | 密度/节奏参考，禁止抄袭 |
| **AI套句黑名单** | 所有配比作家黑名单并集 | Phase 3.5 检测基准 |

### 配比查询与调整

```bash
# 查看写手当前配比
python tools/style_injector.py --writer 剑尘 --show-mix

# 查看可用作家列表
python tools/style_injector.py --writer 墨言 --list-authors
```

用户调整配比时，修改 `config/writers_style_config.yaml` 中对应写手的 `author_mix`，
权重总和无需精确为1，`auto_normalize: true` 会自动归一化。

---

### 作家输入示例（含契约）

```yaml
任务信息:
  场景ID: "scene_002"
  任务类型: "战斗场景"
  
契约数据:
  人物清单:
    命名角色:
      - 林夕 (男, 存活)
      - 血牙 (男, 存活)
    群体:
      - 入侵者 (5人)
  
  时间线:
    相对时间: T+15min ~ T+30min
    前置事件: 母亲死亡 (已完成)
  
  空间:
    位置: 村庄广场
    移动路径: [东门 → 广场]
  
  依赖:
    前置场景: scene_001 (母亲死亡)
  
上下文:
  前文内容: "..."
  相关设定: "..."
  
要求:
  - 遵守契约中的人物数量和状态
  - 时间线必须与前置场景衔接
  - 空间移动必须连续
  - 物体状态保持一致
```

---

## 阶段4：逐场景创作（详细流程）

> ⚠️ **执行约束（硬性，违反即视为流程错误）**：
> - 场景必须**顺序执行**：场景1完成并通过作者微确认 → 场景2 → … 不得跳跃或并行
> - **严禁**为不同场景启动 background task / subagent / 后台任务——即使你认为"不同作家可以同时写"也不行
> - **常见错误**：看到"场景1由玄一写、场景2由墨言写"就派发两个并行任务——这是错的。作家分工是风格标签，不是并行信号
> - Phase 1"并行生成"指**同一场景内**苍澜/玄一/墨言各写一份草稿竞选，不是多场景并行
> - 所有场景在同一 session 内依次完成，context 紧张时可精简草稿长度，但不得外包给后台任务
> - **原因**：场景N+1必须读取场景N写完后更新的场景契约，并行写会导致人物状态/位置/对话断层

### 问题背景

多作家并行输出后直接合并会导致"拼合痕迹"：
- 逻辑冲突（如：苍澜说"遗忘名字"，墨言说"记住每句话"）
- 风格不统一
- 信息矛盾

### 解决方案：检测-融合-统一

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1：并行生成（粗稿）                                     │
│ ├── 苍澜 → 世界观约束草稿                                     │
│ ├── 玄一 → 剧情框架草稿                                      │
│ └── 墨言 → 人物状态草稿                                      │
│                                                             │
│ 输出：标记为"草稿"，需要融合                                   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1.5：一致性检测（自动）                                 │
│                                                             │
│ 检测规则：                                                    │
│ ├── 遗忘 vs 记住 → 逻辑冲突（高）                              │
│ ├── 伏笔 vs 状态不匹配 → 警告（中）                            │
│ ├── 时间线矛盾 → 错误（高）                                    │
│ └── 设定不一致 → 警告（中）                                    │
│                                                             │
│ 输出：冲突清单                                                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1.6：融合调整（主作家）                                 │
│                                                             │
│ 主作家职责：                                                  │
│ ├── 审查三个维度的输出                                        │
│ ├── 解决冲突，选择方向                                        │
│ ├── 统一风格，消除拼合痕迹                                    │
│ └── 输出统一的设定约束包                                      │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2：核心创作                                             │
│                                                             │
│ 输入：统一的设定约束包（无冲突）                               │
│ 主作家：剑尘                                                  │
│ 输出：场景主要内容                                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3：收尾润色                                             │
│                                                             │
│ 云溪执行：                                                    │
│ ├── 整体润色                                                 │
│ ├── 统一语言风格                                              │
│ └── 消除剩余拼合痕迹                                          │
│                                                             │
│ 输出：完整场景                                                │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3.5：质量门控（自动）                                   │
│                                                             │
│ 对云溪润色后的场景文本执行两项检测：                           │
│ ├── Burstiness 检测：句子长度方差 >= 50 -> PASS             │
│ │   方差 < 50 -> 节奏过于均匀（AI感强），输出改写建议          │
│ └── AI套句检测：命中黑名单 <= 3条 -> PASS                   │
│     命中 > 3条 -> 输出命中列表，定向重写对应句子              │
│                                                             │
│ 调用方式（Python模块，直接传文本，无需存文件）：               │
│                                                             │
│   import sys; sys.path.insert(0, ".")                       │
│   from tools.quality_gate import run_quality_gate, format_report│
│   result = run_quality_gate(                                │
│       text=scene_text,   # 云溪润色后的场景文本字符串         │
│       writer=主写手名,    # 例："云溪"                       │
│       chapter=章节号,                                        │
│       scene_index=场景序号,                                  │
│   )                                                         │
│   print(format_report(result))                              │
│                                                             │
│ 结果处理：                                                    │
│ ├── result["passed"]=True  -> 继续写入 Checkpoint           │
│ └── result["passed"]=False -> 读取 result["suggestions"]   │
│     将建议追加到云溪 prompt，触发定向重写                     │
│     （仅重写命中句子，不整场推倒）                            │
│     最多重试 1 次；第2次 FAIL 允许 author_force_pass 放行   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
### 场景摘要写入（每场完成后执行）

```python
python - <<'EOF'
from core.conversation.checkpoint_manager import CheckpointManager

session_id = "CURRENT_SESSION"
chapter = CHAPTER_NUMBER
scene_index = SCENE_INDEX
scene_type = "SCENE_TYPE"
writer_agent = "WRITER_AGENT"

# 以下由 Claude 在确认场景时填写：
summary = "（100-200字场景摘要）"
key_points = ["关键点1", "关键点2", "关键点3"]

mgr = CheckpointManager(session_id)
path = mgr.save_scene_summary(chapter, scene_index, scene_type, summary, key_points, writer_agent)
print(f"摘要已写入：{path}")
EOF
```
        │
        ▼
【下一场景】（读取更新后的契约 + 已完成场景摘要）

---

### Phase 0：质量锚点 + 技法实例（每场景动笔前）

> 在 Phase 1 开始前执行，为写手设定质量目标和技法参照。

> ⚠️ **禁止跳过**：即使本地已有技法文件（如 `创作技法/` 目录下的 .md 文件），Phase 0 也必须执行以下两个检索。技法文件描述**规则**（WHAT TO DO），案例库提供**真实散文写法**（HOW IT LOOKS ON THE PAGE）——两者不可互相替代。有技法文件 ≠ 可以跳过案例库检索。

#### 1. 质量锚点（search_case_quality_anchor）

调用以获取同场景类型中质量最高的案例，作为**本场写作的质量目标**（不是模仿对象，是质量参照线）：

```python
from modules.knowledge_base.search_manager import SearchManager
sm = SearchManager()
anchors = sm.search_case_quality_anchor(
    scene_type=current_scene_type,
    top_k=2,
    min_quality=7.0,
)
```

将最高质量案例的 `content_preview` 注入写手 prompt 顶部：

```
【质量参照】（同场景类型高质量案例，本场写作须达到此水准）
---
[案例内容前200字]
---
注意：不得抄袭句式，只参照质量水准和感官密度。
```

#### 2. 技法实例（search_case_technique_instance）

当本场景选中某条 ANTI_XXX 约束时，检索该约束对应的真实文本实例：

```python
for constraint in selected_constraints:
    instances = sm.search_case_technique_instance(
        constraint_text=constraint["constraint_text"],
        scene_type=current_scene_type,
        top_k=1,
    )
    if instances:
        # 注入写手 prompt 中对应约束的后面
        add_to_prompt(f"【{constraint['id']} 技法示例】\n{instances[0]['content'][:150]}")
```

> 无匹配实例时直接跳过，不阻塞流程。

#### 3. 司法案例（条件触发）

**仅当**章节简述包含以下任意关键词时触发：
`诈骗 / 犯罪 / 案件 / 庭审 / 嫌疑 / 侦查 / 命案 / 杀人 / 盗窃 / 绑架 / 主犯 / 被告 / 审判 / 刑事 / 涉案 / 追查 / 凶手 / 在逃 / 证据`

```python
CRIME_KEYWORDS = [
    "诈骗", "犯罪", "案件", "庭审", "嫌疑", "侦查", "命案", "杀人",
    "盗窃", "绑架", "主犯", "被告", "审判", "刑事", "涉案", "追查", "凶手", "在逃", "证据"
]

if any(kw in chapter_brief for kw in CRIME_KEYWORDS):
    from core.retrieval import UnifiedRetrievalAPI
    api = UnifiedRetrievalAPI()
    judicial_refs = api.search_judicial_cases(query=chapter_brief, top_k=2)
    if judicial_refs:
        refs_text = "\n---\n".join(
            f"【{r['title']}（{r['date']}）】\n{r['content'][:300]}"
            for r in judicial_refs
        )
        add_to_prompt(
            f"【真实司法案例参考】\n{refs_text}\n"
            "注意：以上为真实公开案例，仅参考事件逻辑与细节真实感，"
            "不照抄原文，不出现真实人名/地名/机构名。"
        )
```

> 无匹配或 collection 不存在时直接跳过，不阻塞流程。

#### 4. 作家风格上下文（阶段3.7已加载，此处直接使用）

> **前提**：阶段3.7已在场景循环开始前为每位写手生成风格包，Phase 0 直接引用，无需重新调用。

将阶段3.7输出的 per-writer 风格包注入到本场景各写手的 prompt 末段：

```
【作家风格包：{writer} — {author_A}({weight_A}) × {author_B}({weight_B})】

### 行为约束（本场景必须遵守）
1. {constraint_1}
2. {constraint_2}
...（共6-8条，按权重从配置中采样）

### 专属语言 quirk（适度植入 1-2 处）
- {quirk_1}

### 风格锚点（仅参考密度与节奏，禁止抄袭句式）
{anchor_text}

### AI套句黑名单（命中即重写该句）
  「{phrase_1}」 / 「{phrase_2}」 / ...
```

命令行生成（调试用）：
```bash
python tools/style_injector.py --writer 剑尘 --scene 战斗 --seed {chapter_id}
```

> 若 `authors_styles.yaml` 或 `writers_style_config.yaml` 不存在，跳过本步骤，不阻断流程。

---

### Phase 1：并行生成（粗稿）

> ⚠️ **执行模型说明**：苍澜、玄一、墨言是你（当前AI）扮演的角色视角，**不是独立的agent**。
> 你在同一次响应里依次写出三段内容（苍澜视角 → 玄一视角 → 墨言视角），无需调用任何task/subagent/background task。
> "并行"指逻辑上三个维度同时考量，物理上在同一响应内顺序输出。

#### 设计原则：固定3人前置

**所有场景类型都固定由苍澜、玄一、墨言三人并行执行前置输入。**

| 维度 | 作家 | 说明 |
|------|------|------|
| **世界观约束** | 苍澜 | 力量体系、血脉设定、世界规则 |
| **剧情框架** | 玄一 | 伏笔、悬念、剧情结构 |
| **人物状态** | 墨言 | 情感状态、心理变化、行为动机 |

**为什么固定3人而非动态选择？**

1. **三个维度对所有场景都有价值**
   - 任何场景都发生在某个世界中（世界观约束）
   - 任何场景都有前后文关联（剧情框架）
   - 任何涉及人物的场景都需要情感状态（人物状态）

2. **流程统一，代码简单**
   - 不需要根据场景类型判断调用哪些作家
   - 融合逻辑始终处理3维度，无需分支

3. **"无特殊约束"本身就是有价值的信息**
   - 告诉主作家：这个维度可以自由发挥
   - 或使用默认设定，避免违背已有设定

---

#### "无特殊约束"处理

当某个维度对当前场景无特殊要求时，作家输出"无特殊约束"标记：

```yaml
# 示例：剧情推进场景（玄一主作家）

苍澜输出：
  维度: "世界观约束"
  内容: "无特殊约束"
  说明: "本场景无世界观特殊要求，使用默认设定"
  默认引用: "[力量技能名]"基础设定"

玄一输出：
  维度: "剧情框架"
  内容:
    伏笔: ["母亲临死说出一个秘密"]
    结构: "铺垫→悬念→高潮→收尾"
    钩子: "觉醒后的失控威胁到周围人"

# ⚠️ 主题标注（玄一/墨言必须在草稿末尾附加，格式固定）：
# 写作时须在草稿末尾添加：[主题标注] 块，例如：
#
#   [主题标注]
#   力量的代价: 3
#   身份认同: 1
#
# 深度说明：1=轻触（一笔带过）  2=展开（有铺陈）  3=核心（场景主题）
# 若本场景无明显主题触及，可省略标注块（不影响流程，但台账会以大纲兜底）。
# 同一章内多场景草稿均会被扫描，同主题取深度最大值。

墨言输出：
  维度: "人物状态"
  内容: "无特殊约束"
  说明: "保持当前情感状态，无特殊变化要求"
  默认引用: "林远当前状态"
```

---

#### 融合时的过滤逻辑

```python
def filter_valid_outputs(outputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    过滤掉"无特殊约束"的维度
    
    只对有效维度进行冲突检测
    """
    valid = {}
    for dimension, output in outputs.items():
        content = output.get("内容", "")
        
        # 检查是否为"无特殊约束"
        if content == "无特殊约束" or content == {}:
            continue
        
        # 保留有效输出
        valid[dimension] = output
    
    return valid

# 使用示例
phase1_outputs = {
    "世界观约束": {"内容": "无特殊约束", "说明": "..."},
    "剧情框架": {"内容": {"伏笔": [...], "结构": "..."}},
    "人物状态": {"内容": "无特殊约束", "说明": "..."},
}

valid_outputs = filter_valid_outputs(phase1_outputs)
# 结果：只有"剧情框架"一个有效维度

# 单维度无需融合
if len(valid_outputs) <= 1:
    print("无需融合，直接进入Phase 2")
else:
    conflicts = detect_conflicts(valid_outputs)
```

---

#### 三人同时接收相同的输入上下文，各自专注自己的维度。

```yaml
# 苍澜的输入
任务信息:
  角色: "世界观输入"
  Phase: "前置"
  输出类型: "草稿"  # 标记为草稿，后续需要融合
  
上下文:
  场景描述: "..."
  血脉设定: "[力量技能名]"
  前章经验:
    建议: "代价描写要具体化（肢体/记忆/关系）"

要求:
  - 确定血脉觉醒触发条件
  - 设定觉醒后的代价表现
  - 输出标记为"草稿"

---
# 苍澜输出（草稿）
世界观约束草稿:
  血脉觉醒:
    触发: "目睹至亲被肢解，仇恨值突破阈值"
    代价: "遗忘母亲的名字，只记得仇恨"
```

---

### Phase 1.5：一致性检测（自动）

```python
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class ConflictSeverity(Enum):
    HIGH = "high"      # 必须解决
    MEDIUM = "medium"  # 建议解决
    LOW = "low"        # 可选解决

@dataclass
class Conflict:
    """冲突检测结果"""
    type: str                    # 冲突类型
    severity: ConflictSeverity    # 严重程度
    dimension_a: str             # 维度A
    dimension_b: str             # 维度B
    content_a: str               # 内容A
    content_b: str               # 内容B
    suggestion: str              # 建议解决方案

def detect_conflicts(outputs: Dict[str, Any]) -> List[Conflict]:
    """
    检测三个作家输出之间的冲突
    
    Args:
        outputs: {
            "世界观约束": {...},  # 来自苍澜
            "剧情框架": {...},    # 来自玄一
            "人物状态": {...}     # 来自墨言
        }
    
    Returns:
        冲突列表
    """
    conflicts = []
    
    worldview = outputs.get("世界观约束", {})
    plot = outputs.get("剧情框架", {})
    character = outputs.get("人物状态", {})
    
    # 规则1：遗忘 vs 记住
    conflicts.extend(detect_memory_conflicts(worldview, character))
    
    # 规则2：伏笔与人物状态匹配
    conflicts.extend(detect_foreshadow_conflicts(plot, character))
    
    # 规则3：时间线一致
    conflicts.extend(detect_timeline_conflicts(worldview, plot))
    
    # 规则4：设定一致性
    conflicts.extend(detect_setting_conflicts(worldview, plot, character))
    
    return conflicts

def detect_memory_conflicts(worldview: Dict, character: Dict) -> List[Conflict]:
    """检测遗忘vs记住的冲突"""
    conflicts = []
    
    worldview_text = str(worldview)
    character_text = str(character)
    
    # 检测遗忘
    if "遗忘" in worldview_text:
        # 查找遗忘的内容
        import re
        forget_match = re.search(r"遗忘[的]?([^，。]+)", worldview_text)
        if forget_match:
            forget_content = forget_match.group(1)
            
            # 检测是否要求记住
            if "记住" in character_text or "记住" in character_text:
                remember_match = re.search(r"记住[的]?([^，。]+)", character_text)
                if remember_match:
                    remember_content = remember_match.group(1)
                    
                    conflicts.append(Conflict(
                        type="记忆逻辑冲突",
                        severity=ConflictSeverity.HIGH,
                        dimension_a="世界观约束",
                        dimension_b="人物状态",
                        content_a=f"遗忘{forget_content}",
                        content_b=f"记住{remember_content}",
                        suggestion=f"建议统一：血脉代价遗忘{forget_content}，但保留{remember_content}"
                    ))
    
    return conflicts

def detect_foreshadow_conflicts(plot: Dict, character: Dict) -> List[Conflict]:
    """检测伏笔与人物状态的匹配"""
    conflicts = []
    
    foreshadows = plot.get("伏笔", [])
    character_state = character.get("心理状态", {})
    
    # 检查伏笔是否与人物心理匹配
    # 例如：伏笔是"母亲临死说出秘密"，但人物状态是"崩溃无意识"
    
    return conflicts

def detect_timeline_conflicts(worldview: Dict, plot: Dict) -> List[Conflict]:
    """检测时间线冲突"""
    conflicts = []
    # 实现时间线冲突检测逻辑
    return conflicts

def detect_setting_conflicts(
    worldview: Dict, 
    plot: Dict, 
    character: Dict
) -> List[Conflict]:
    """检测设定一致性"""
    conflicts = []
    # 实现设定一致性检测逻辑
    return conflicts
```

---

### Phase 1.6：融合调整（云溪）

**融合角色由云溪负责，而非主作家剑尘。原因：**
- 云溪专长意境营造，擅长风格统一
- 剑尘专注战斗设计，融合任务会分散精力
- 云溪同时负责 Phase 3 收尾润色，融合和润色一体化更连贯

```yaml
# 云溪的融合任务输入

任务信息:
  角色: "设定融合"
  Phase: "前置-融合"
  
上下文:
  Phase 1 输出（草稿）:
    苍澜:
      血脉觉醒:
        触发: "目睹至亲被肢解"
        代价: "遗忘母亲的名字"
    
    玄一:
      剧情框架:
        结构: "铺垫→悬念→高潮→收尾"
        伏笔: ["母亲临死说出一个秘密"]
    
    墨言:
      人物状态:
        情感重点: "记住母亲的每一句话"
  
  检测到的冲突:
    - type: "记忆逻辑冲突"
      severity: "high"
      问题: "苍澜说'遗忘母亲名字'，墨言说'记住每句话'"
      建议: "统一：遗忘名字，保留嘱托"

要求:
  - 解决所有 HIGH 级别冲突
  - 选择最有利于剧情的方向
  - 统一风格，消除拼合痕迹
  - 输出统一的设定约束包

---
# 云溪的融合输出

统一设定约束包:
  血脉觉醒:
    触发: "目睹母亲被肢解"
    代价: "遗忘母亲的名字，但记住母亲的嘱托'活下去'"
    # 融合决策：遗忘"名字"，保留"嘱托"
  
  剧情框架:
    结构: "铺垫→悬念→高潮→收尾"
    伏笔:
      - 内容: "母亲临死给匕首"
        修改说明: "不是说出秘密，而是给匕首（避免与遗忘冲突）"
  
  人物状态:
    情感重点: "记住母亲的嘱托'活下去'"
    心理变化: "恐惧→震惊→崩溃→仇恨"
  
  融合说明:
    冲突解决:
      - 问题: "遗忘名字 vs 记住每句话"
        决策: "遗忘名字，保留嘱托"
        理由: "血脉代价必须有，但情感内核也要保留"
```

---

### 自动融合机制

**目的：减少作家调用，提升效率。**

当冲突数量少且类型简单时，系统自动融合，不调用作家。

```
冲突数量判断:
├── ≤ 2个冲突 → 自动融合（无需调用作家）
│   ├── LOW 级别 → 直接忽略
│   ├── MEDIUM 级别 → 应用默认规则
│   └── HIGH 级别 → 应用内置解决模板
│
├── 3-5个冲突 → 云溪介入融合
│   ├── HIGH ≥ 1 → 必须云溪解决
│   └── 全 MEDIUM/LOW → 可自动 + 云溪确认
│
└── > 5个冲突 → 提示用户确认
    ├── 输出冲突清单
    ├── 建议用户手动确认方向
    └── 用户确认后继续
```

#### 自动融合规则

| 冲突类型 | 自动解决规则 |
|----------|-------------|
| **记忆逻辑冲突** | 遗忘"细节"，保留"核心情感" |
| **伏笔不匹配** | 伏笔改为"道具传递"而非"对话" |
| **时间线冲突** | 取较早的时间点 |
| **设定不一致** | 取世界观约束优先 |
| **人物矛盾** | 取情感状态优先 |
| **基调冲突** | 添加过渡段落提示 |

#### 自动融合函数

```python
def auto_fuse_conflicts(conflicts: List[Conflict]) -> Dict[str, Any]:
    """
    自动融合冲突（冲突 ≤ 2个时）
    
    Returns:
        统一设定约束包
    """
    if len(conflicts) > 2:
        return None  # 需要云溪介入
    
    fusion_result = {}
    
    for conflict in conflicts:
        # 应用自动解决规则
        rule = AUTO_FUSION_RULES.get(conflict.type)
        
        if rule:
            fusion_result[conflict.type] = rule.apply(
                conflict.content_a,
                conflict.content_b
            )
        else:
            # 无规则，默认取 A
            fusion_result[conflict.type] = conflict.content_a
    
    return fusion_result

# 自动融合规则库
AUTO_FUSION_RULES = {
    "记忆逻辑冲突": MemoryFusionRule(),
    "伏笔不匹配": ForeshadowFusionRule(),
    "时间线冲突": TimelineFusionRule(),
    "设定不一致": SettingFusionRule(),
    "人物矛盾": CharacterFusionRule(),
    "基调冲突": ToneFusionRule(),
}
```

#### 融合效率对比

| 情况 | 传统方案 | 自动融合方案 |
|------|---------|-------------|
| 1个 LOW 冲突 | 调用作家融合 | 自动忽略，0秒 |
| 2个 MEDIUM 冲突 | 调用作家融合 | 自动应用规则，0秒 |
| 3个 HIGH 冲突 | 调用作家融合 | 云溪介入，~30秒 |
| 6个混合冲突 | 调用作家融合 | 用户确认，~60秒 |

**效率提升：约 40-60% 的场景无需调用云溪融合。**

---

### Phase 2：核心创作（使用融合后的约束）

> ⚠️ 你（当前AI）扮演主作家角色直接输出正文，不调用任何task/subagent。

```yaml
# 剑尘的核心创作输入

任务信息:
  角色: "战斗设计"
  Phase: "核心"
  
上下文:
  # 来自 Phase 1.6 的融合输出（无冲突）
  设定约束:
    血脉觉醒:
      触发: "目睹母亲被肢解"
      代价: "遗忘母亲名字，记住嘱托"
    
    剧情框架:
      结构: "铺垫→悬念→高潮→收尾"
      伏笔: ["母亲给匕首"]
    
    人物状态:
      情感重点: "记住嘱托'活下去'"
      心理变化: "恐惧→震惊→崩溃→仇恨"
  
  # 前章经验
  前章经验:
    有效做法: ["代价描写具体化"]
    建议: ["仇恨建立后需要沉淀段落"]

要求:
  - 按融合后的约束创作
  - 无需再处理冲突
  - 专注战斗内容本身
```

---

### 完整流程图

```
场景类型："战斗场景"
        │
        ▼
查表获取作家配置
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1：并行生成                                             │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐                         │
│ │ 苍澜    │ │ 玄一    │ │ 墨言    │                         │
│ │世界观   │ │ 剧情    │ │ 人物   │                         │
│ └─────────┘ └─────────┘ └─────────┘                         │
│      │           │           │                               │
│      ▼           ▼           ▼                               │
│   输出A       输出B       输出C                               │
│  (草稿)      (草稿)      (草稿)                               │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1.5：一致性检测                                         │
│                                                             │
│ 输入: 输出A + 输出B + 输出C                                   │
│ 处理: 自动检测冲突                                           │
│ 输出: 冲突清单                                               │
│                                                             │
│ 示例输出:                                                    │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 冲突1: 记忆逻辑冲突 (HIGH)                              │   │
│ │   维度A: 世界观约束 - "遗忘母亲名字"                     │   │
│ │   维度B: 人物状态 - "记住每句话"                        │   │
│ │   建议: 遗忘名字，保留嘱托                              │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 1.6：融合调整                                          │
│                                                             │
│ 执行者: 云溪（意境营造师）                                     │
│ 输入: Phase 1 输出 + 冲突清单                                 │
│ 处理: 审查 → 决策 → 统一风格                                   │
│ 输出: 统一设定约束包                                          │
│                                                             │
│ 融合策略:                                                    │
│ ├── 冲突 ≤ 2个 → 自动融合（无需调用作家）                      │
│ ├── 冲突 3-5个 → 云溪介入融合                                 │
│ └── 冲突 > 5个 → 提示用户确认                                 │
│                                                             │
│ 示例决策:                                                    │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 冲突: 遗忘 vs 记住                                     │   │
│ │ 决策: 遗忘名字，保留嘱托                               │   │
│ │ 理由: 代价感 + 情感内核                                │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 2：核心创作                                             │
│                                                             │
│ 执行者: 剑尘                                                  │
│ 输入: 统一设定约束包（无冲突）                                 │
│ 输出: 场景主要内容                                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Phase 3：收尾润色                                             │
│                                                             │
│ 执行者: 云溪                                                  │
│ 输入: 场景主要内容                                            │
│ 处理: 润色 + 统一风格                                         │
│ 输出: 完整场景                                                │
└─────────────────────────────────────────────────────────────┘
```

---

### 关键设计点

| 设计点 | 说明 |
|--------|------|
| **固定3人前置** | 所有场景都由苍澜、玄一、墨言并行执行前置，流程统一 |
| **无特殊约束标记** | 某维度无要求时输出"无特殊约束"，而非跳过调用 |
| **输出标记为草稿** | Phase 1 输出不直接使用，标记为"草稿" |
| **自动检测冲突** | Phase 1.5 用规则引擎检测逻辑冲突 |
| **云溪负责融合** | Phase 1.6 由云溪决策（意境营造师擅长风格统一） |
| **自动融合优先** | 冲突≤2个自动处理，减少作家调用 |
| **融合后再创作** | Phase 2 主作家使用融合后的统一约束 |
| **最终润色统一** | Phase 3 云溪统一风格，消除剩余痕迹 |
| **作者微确认** | Phase 3 完成后展示场景摘要，作者30秒确认，备注传入下一场景 |

---

## ★ 作者微确认（每场景必做）

### 触发时机

每个场景 Phase 3 完成后，**在开始下一场景之前**，必须展示微确认卡片，等待作者回复。

> ⚠️ **不得跳过**：未收到作者回复前，禁止开始下一场景。

### 输出格式

```
【场景N 完成 · 作者确认】─────────────────────────────
执笔：[主作家名]  类型：[场景类型]  字数：约XXX字

▌核心内容（3句以内）
[场景发生了什么，关键动作/转折一句话]

▌主要选择
· [本场最关键的一个创作决定，例："用败者视角写战斗"]
· [第二个关键选择，例："结尾留白，无总结句"]

▌契约变化
· [人物/时间/空间状态有何变化，供下一场景继承]

请回复：
  ✓  通过，继续场景N+1
  ✗  重写，原因：___
  +  备注：___（将作为额外约束传入下一场景）
──────────────────────────────────────────────────────
```

### 备注的传递规则

作者回复 `+备注` 时，该备注以"作者指令"级别注入下一场景的写手 prompt 最顶部：

```
【作者指令 · 来自上一场景】
[作者备注原文]
优先级：高于所有其他约束，但不得违反场景契约。
```

### 重写处理

作者回复 `✗重写` 时：
1. 重置当前场景契约至本场景开始前的状态
2. 重新执行 Phase 1 → Phase 3
3. 重新展示微确认卡片

### ⛔ 最后一个场景通过后的强制跳转

当前场景是章节大纲中**最后一个场景**，且作者回复 `✓` 后：

**禁止**展示任何满意/定稿/跳过选项。  
**禁止**等待用户输入。  
**必须**立即输出以下提示并执行阶段5.5：

```
【所有场景已完成 · 自动进入阶段5.5】─────────────────
已完成全部 N 个场景，字数约 XXXX 字。
现在强制执行三方协商，鉴赏师将对完整章节进行评审。
──────────────────────────────────────────────────────
```

然后**不等待任何用户回复**，直接开始执行阶段5.5。

---

## 阶段8：经验写入

### 目的

将本章创作经验写入日志，供后续章节参考。

### 触发时机

- 阶段6（整章评估）完成后
- 无论通过与否，都写入经验

### 写入内容

| 字段 | 来源 | 说明 |
|------|------|------|
| `chapter` | 阶段1 | 章节名称 |
| `created_at` | 系统时间 | 创建时间 |
| `techniques_used` | Evaluator评估结果 | 使用的技法及效果 |
| `what_worked` | Evaluator洞察提取 | 有效做法 |
| `what_didnt_work` | Evaluator洞察提取 | 无效做法 |
| `insights` | Evaluator洞察提取 | 可复用洞察 |
| `for_next_chapter` | Evaluator洞察提取 | 给下一章建议 |
| `scenes` | 本章场景列表 | 格式：`[{scene_type, content, techniques_used, quality_score}]`，触发向量库同步必需 |

### 写入函数

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

def write_chapter_log(
    chapter_name: str,
    evaluation_result: Dict,
    techniques_used: List[Dict]
) -> Path:
    """
    将评估结果写入章节经验日志
    
    Args:
        chapter_name: 章节名称
        evaluation_result: Evaluator输出的评估结果
        techniques_used: 使用的技法列表
    
    Returns:
        日志文件路径
    """
    log_dir = Path("{PROJECT_ROOT}/{experience_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 提取章节号
    import re
    match = re.search(r"第(\d+)章", chapter_name)
    chapter_num = match.group(1) if match else "0"
    
    log_file = log_dir / f"第{chapter_num}章_log.json"
    
    # 提取洞察
    insight_data = evaluation_result.get("反馈", {}).get("洞察提取", {})
    
    # 构建日志内容
    log_content = {
        "chapter": chapter_name,
        "created_at": datetime.now().isoformat(),
        
        "techniques_used": techniques_used,
        
        "what_worked": insight_data.get("有效做法", []),
        
        "what_didnt_work": insight_data.get("无效做法", []),
        
        "insights": [
            {
                "content": i.get("content", ""),
                "scene_condition": i.get("scene_condition", ""),
                "reusable": i.get("可复用", True)
            }
            for i in insight_data.get("可复用洞察", [])
        ],
        
        "for_next_chapter": insight_data.get("给下一章建议", [])
    }
    
    # 写入文件
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log_content, f, ensure_ascii=False, indent=2)
    
    print(f"[经验写入] 已写入: {log_file}")
    return log_file
```

### 向量库同步（必须执行）

调用 `ExperienceWriter.write_chapter_experience()` 时，`experience` 参数必须包含 `scenes` 字段：

```python
experience = {
    "chapter_name": "第二章",     # 章节名
    "novel_name": "众生界",       # 小说名（从 config.json 读取）
    "techniques_used": [...],     # 来自 Evaluator 输出
    "what_worked": [...],
    "what_didnt_work": [...],
    "scenes": [                   # ← 缺少此字段则不同步向量库
        {
            "scene_type": "战斗",          # 场景类型（28种之一）
            "content": "<场景完整文本>",   # 云溪整章润色后的对应段落
            "techniques_used": ["ANTI_001"],
            "quality_score": 0.8,          # 来自 Evaluator overall_score
        },
        # ... 本章所有场景
    ],
}
```

**铁律**：没有 `scenes` 字段 = 当章经验只进 JSON，不进向量库，后续章节无法检索本章案例。

### 叙事台账更新（阶段8末尾执行，在经验写入之后）

#### 数据来源说明

| 字段 | 数据来源 | 收集时机 |
|------|----------|----------|
| `scene_types` | 阶段2场景调度计划，每个场景条目的 `type` 字段 | 阶段8从 `stage2_scene_plan` 提取去重列表 |
| `tension_level` | 阶段6 `综合评分`（0-1浮点），按规则映射到1-5 | 阶段8从 `evaluation_result["overall_score"]` 读取 |
| `themes_touched` | 阶段4 Phase 1 玄一/墨言草稿末尾的 `[主题标注]` 块 | 阶段8解析所有场景草稿中的标注块，取深度最大值 |

```python
import sys, re
sys.path.insert(0, ".")

# ── 1. scene_types：从阶段2场景调度计划提取（去重，保序） ────────────────
# stage2_scene_plan 结构：[{"id": "scene_001", "type": "战斗", ...}, ...]
# 每个条目必须含 type 字段（见阶段2格式规范）
scene_types = list(dict.fromkeys(
    scene["type"] for scene in stage2_scene_plan
))

# ── 2. tension_level：从阶段6综合评分映射（0-1 → 1-5） ──────────────────
# evaluation_result["overall_score"] 来自 novelist-evaluator 的综合评分
def _tension(score: float, stypes: list) -> int:
    high_beats = {"战斗", "高潮", "危机", "对抗", "追杀"}
    if score >= 0.8 and any(s in high_beats for s in stypes):
        return 5
    if score >= 0.8: return 4
    if score >= 0.6: return 3
    if score >= 0.4: return 2
    return 1

overall_score = evaluation_result.get("overall_score", 0.6)  # 阶段6综合评分，默认中等
tension_level = _tension(overall_score, scene_types)

# ── 3. themes_touched：从玄一/墨言草稿的 [主题标注] 块收集 ───────────────
# stage4_drafts 结构：每个场景的玄一/墨言 Phase 1 草稿文本列表
# 格式：[主题标注]\n主题名: 深度\n...  （深度 1=轻触 2=展开 3=核心）
themes_touched: dict = {}

def _parse_theme_block(text: str) -> dict:
    """解析草稿末尾的 [主题标注] 块，返回 {主题名: 深度} 字典"""
    result = {}
    match = re.search(r'\[主题标注\]\s*\n((?:[^\[]+\n?)*)', text)
    if match:
        for line in match.group(1).strip().splitlines():
            line = line.strip()
            if ':' in line or '：' in line:
                parts = re.split(r'[:：]', line, 1)
                theme = parts[0].strip()
                try:
                    depth = int(parts[1].strip())
                    if theme:
                        result[theme] = max(result.get(theme, 0), depth)
                except ValueError:
                    pass
    return result

for draft_text in stage4_drafts:  # 遍历所有场景的玄一/墨言草稿
    for theme, depth in _parse_theme_block(draft_text).items():
        themes_touched[theme] = max(themes_touched.get(theme, 0), depth)

# 兜底：若玄一/墨言均未标注，从章节大纲主题字段提取（默认深度=1）
if not themes_touched:
    for theme in chapter_outline.get("themes", []):
        themes_touched[theme] = 1

# ── 4. 写入叙事台账 ────────────────────────────────────────────────────────
from tools.narrative_ledger import update_chapter

update_chapter(
    chapter=章节号,
    scene_types=scene_types,
    tension_level=tension_level,
    themes_touched=themes_touched,
)
print(f"[台账] 第{章节号}章已更新 | scene_types={scene_types} | tension={tension_level} | themes={list(themes_touched.keys())}")
```

**主题标注方式**（由玄一/墨言在 Phase 1 草稿末尾附加，格式固定）：

```
[主题标注]
力量的代价: 2
身份认同: 1
```

每个场景的所有草稿均会被扫描；同一主题出现多次时取深度最大值。
若所有草稿均未标注，则从章节大纲的 `themes` 字段兜底，深度统一为 1。

### 写入时机流程

```
【阶段5.5：三方协商】→ 创意契约
        ↓
【阶段5.6：派单改写】→ 局部重写 + 云溪接缝处理（仅±1段）
        ↓
【阶段6：整章评估】（带契约豁免）
├── Evaluator 评估
├── 输出：最终版本 + 洞察提取
└── 结论：通过/需修改
        ↓
【阶段7：用户确认】
        ↓
【阶段8：经验写入】
├── 提取洞察数据
├── 构建日志内容
├── 写入：章节经验日志/第N章_log.json
├── ★ 更新叙事台账（新增）
│     from tools.narrative_ledger import update_chapter
│     # scene_types：本章实际使用的场景类型列表（从阶段2场景调度读取）
│     # tension_level：1-5，由 Evaluator overall_score 换算（score>=0.8→4, >=0.6→3, else→2）
│     #   若本章含战斗/高潮/危机 且 score>=0.8 → tension=5
│     # themes_touched：由玄一/墨言在创作中标注（见下方说明）
│     update_chapter(
│         chapter=章节号,
│         scene_types=本章场景类型列表,
│         tension_level=换算后的张力等级,
│         themes_touched=本章主题触碰字典,  # {"力量的代价": 2, ...}
│     )
└── 输出：章节日志文件 + 台账已更新
        ↓
完成本章创作
```

---

## 作家调度矩阵

### 作家专长与调用时机

| 作家 | 专长 | 调用时机 | 输入 | 输出 |
|------|------|----------|------|------|
| **苍澜** | 世界观架构 | 世界观设定、势力构建、血脉体系 | 世界观任务描述 | 世界观设定内容 |
| **玄一** | 剧情编织 | 伏笔设计、悬念布局、章节钩子 | 剧情任务描述 | 剧情内容 |
| **墨言** | 人物刻画 | 人物外貌、性格、矛盾、成长 | 人物任务描述 | 人物描写内容 |
| **剑尘** | 战斗设计 | 战斗节奏、代价设计、弱者胜强 | 战斗任务描述 | 战斗场景内容 |
| **云溪** | 意境营造 + 润色 | 氛围描写、意境营造、章节润色 | 氛围/润色任务描述 | 氛围描写/润色内容 |

### 场景类型与作家分配

| 场景类型 | 主作家 | 辅助作家 | 说明 |
|----------|--------|----------|------|
| **世界观展开** | 苍澜 | 云溪 | 世界观设定 + 氛围渲染 |
| **剧情推进** | 玄一 | - | 伏笔、悬念、钩子 |
| **人物出场/成长** | 墨言 | 云溪 | 人物刻画 + 氛围渲染 |
| **战斗场景** | 剑尘 | 云溪 | 战斗设计 + 氛围渲染 |
| **情感场景** | 墨言 | 云溪 | 情感描写 + 氛围渲染 |
| **章节润色** | 云溪 | - | 最终润色 |

---

## 任务分解规则

### Step 1：场景分析

分析场景内容，识别包含的元素：

```
场景分析输出：
{
  "场景类型": "战斗/世界观/人物/剧情/情感",
  "包含元素": ["世界观", "人物", "战斗", "氛围"],
  "主要作家": "剑尘",
  "辅助作家": ["云溪"],
  "预估字数": "3000-5000"
}
```

### Step 2：任务分解

将场景分解为子任务：

```
任务分解示例（战斗场景）：

任务1：战斗铺垫（剑尘）
  - 输入：对手设定、主角状态、环境设定
  - 输出：铺垫段落（40%字数）
  
任务2：战斗爆发（剑尘）
  - 输入：铺垫输出、战斗目标
  - 输出：爆发段落（45%字数）
  
任务3：战斗沉淀（剑尘）
  - 输入：爆发输出、后续伏笔
  - 输出：沉淀段落（15%字数）
  
任务4：氛围渲染（云溪）
  - 输入：完整战斗内容
  - 输出：氛围增强版本
```

### Step 3：执行顺序

```
顺序执行：
任务1 → 任务2 → 任务3 → 任务4

并行执行（如果无依赖）：
任务A（世界观）┐
任务B（人物）  ├→ 合并 → 任务D（润色）
任务C（剧情）┘
```

---

## 作家协作协议

### 输入格式（标准）

每个作家接收统一格式的输入：

```yaml
任务信息:
  场景ID: "scene_001"
  任务类型: "战斗铺垫"
  目标字数: "1200-1500"
  
上下文:
  前文内容: "..."
  相关设定: "..."
  角色状态: "..."
  
要求:
  - 要求1
  - 要求2
  
参考技法:
  - "技法文件路径"（可选）
```

### 输出格式（标准）

每个作家输出统一格式：

```yaml
输出:
  场景ID: "scene_001"
  任务类型: "战斗铺垫"
  内容: |
    [实际创作内容]
    
元数据:
  实际字数: 1350
  使用技法: ["铺垫五要素", "仇恨值拉满"]
  伏笔埋设: ["对手隐藏底牌"]
  待审核项: ["是否需要增加环境描写"]
```

### 作家间传递

```
苍澜（世界观）→ 输出设定
        ↓
玄一（剧情）→ 基于设定设计剧情
        ↓
墨言（人物）→ 基于剧情刻画人物
        ↓
剑尘（战斗）→ 基于人物设计战斗
        ↓
云溪（润色）→ 最终润色
        ↓
novelist-evaluator（审核）
```

---

## Evaluator 对接

### 触发条件

以下情况触发 Evaluator：
1. 单个任务完成
2. 整合内容完成
3. 用户请求审核

### 输入传递

```yaml
审核请求:
  内容: "[完整内容]"
  作者: ["剑尘", "云溪"]
  场景类型: "战斗"
  特别关注: ["代价描写", "群体牺牲"]
```

### 反馈传递

```yaml
审核结果:
  状态: "需修改"
  
禁止项检测:
  AI味表达: 0
  时间连接词: 2 ["然后...", "就在这时..."]
  结果: "通过"
  
技法评估:
  有代价胜利: 8/10
  群体牺牲有姓名: 5/10 [缺少具体姓名]
  
反馈:
  P0需修改:
    - "群体牺牲缺少具体姓名，建议改为：'三十七个男人。十九个女人...'"
  P1建议:
    - "时间连接词可优化，建议删除'然后'"
```

### 迭代修改

```
Evaluator 输出反馈
       ↓
系统判断：是否通过？
       ↓
否 → 将反馈传递给对应作家
       ↓
作家根据反馈修改
       ↓
重新提交 Evaluator
```

---

## 调度器执行示例

### 示例：战斗场景创作

```
输入：场景大纲
"主角林远与血脉者佣兵对决，林远以弱胜强但付出代价"

Step 1：场景分析
{
  "场景类型": "战斗",
  "包含元素": ["人物", "战斗", "氛围"],
  "主要作家": "剑尘",
  "辅助作家": ["云溪"]
}

Step 2：任务分解
任务1：战斗铺垫（剑尘）- 40%字数
任务2：战斗爆发（剑尘）- 45%字数
任务3：战斗沉淀（剑尘）- 15%字数
任务4：氛围渲染（云溪）- 全文润色

Step 3：执行
剑尘.创作(任务1) → 输出铺垫内容
剑尘.创作(任务2) → 输出爆发内容
剑尘.创作(任务3) → 输出沉淀内容
云溪.润色(合并内容) → 输出润色版本

Step 4：审核
novelist-evaluator.评估(润色版本)
→ 输出评估报告

Step 5：迭代（如需）
剑尘.修改(反馈) → 修改内容
→ 重新审核
```

---

## 关键原则

1. **Generator 不自我评估** - 作家专注创作，不检查技法
2. **Evaluator 独立评估** - 审核师独立于创作过程
3. **具体反馈** - 反馈必须可操作，而非模糊评价
4. **迭代上限** - 最多迭代3次，避免无限循环
5. **技法可选** - 技法笔记是参考，不是强制要求

---

## 技法检索集成

### 技能依赖

```
novelist-technique-search（技法检索）
└── 向量数据库（Qdrant）← 集合：writing_techniques
```

### 检索优先级（与设定检索相同）

技法检索遵循相同的优先级规则：

```
Level 1: Qdrant 向量数据库（writing_techniques 集合）
    ↓ 无结果或不可用
Level 2: 本地数据文件（.cache/db_cache/writing_techniques.json）
    ↓ 无结果
Level 3: 原始技法文件（创作技法/**/*.md）
    ↓ 无结果
Level 4: 标记待补充（技法暂缺）
```

### Generator 阶段技法检索（可选）

作家创作时可调用技法检索，获取相关技法作为参考：

```python
# 调用示例
import sys
# [N18 2026-04-18] 该 sys.path 注入在 M2-β 后失效;.vectorstore/ 已无 .py 框架
# 如需直接检索知识库，请使用 Python API：`from modules.knowledge_base.search_manager import SearchManager`
# 动态检测项目根目录（示例）
_project_root = Path.cwd()  # 实际使用时从 config.json 读取
sys.path.insert(0, str(_project_root))
from technique_search import TechniqueSearcher

searcher = TechniqueSearcher()

# 根据任务类型检索技法
def get_techniques_for_task(task_type: str, content_hint: str):
    dimension_map = {
        "世界观设定": "世界观",
        "伏笔埋设": "剧情",
        "悬念设计": "剧情",
        "人物出场": "人物",
        "战斗铺垫": "战斗",
        "氛围描写": "氛围",
    }
    
    results = searcher.search(
        query=f"{task_type} {content_hint}",
        dimension=dimension_map.get(task_type, ""),
        top_k=3
    )
    
    return results
```

### Evaluator 阶段技法检索（必须）

审核时必须调用技法检索，获取评估标准：

```python
# 调用示例
def get_evaluation_techniques(scene_type: str, evaluation_dimensions: List[str]):
    searcher = TechniqueSearcher()
    
    techniques = []
    for dim in evaluation_dimensions:
        results = searcher.search(
            query=f"{scene_type} {dim}",
            dimension=dimension_map.get(dim, ""),
            top_k=2
        )
        techniques.extend(results)
    
    return techniques

# 维度映射
dimension_map = {
    "历史纵深": "世界观",
    "内在逻辑一致性": "世界观",
    "命运驱动": "剧情",
    "历史回响": "剧情",
    "群像塑造": "人物",
    "道德灰色": "人物",
    "选择代价": "人物",
    "有代价胜利": "战斗",
    "群体牺牲有姓名": "战斗",
    "历史沉淀感": "氛围",
    "静默叙述": "氛围",
}
```

### 工作流集成点

```
Step 1：任务分解
├── 分析场景类型
├── 确定调用作家
└── 【技法检索】为作家准备相关技法参考 ← 可选

Step 2：Generator 执行
├── 作家接收任务
├── 【技法检索】作家可查询技法参考 ← 可选
└── 作家输出内容

Step 3：Evaluator 评估
├── 【技法检索】获取评估标准 ← 必须
├── 禁止项检测
├── 技法评估（基于检索到的技法）
└── 输出反馈
```

### 检索调用时机

| 阶段 | 调用时机 | 是否必须 | 说明 |
|------|----------|----------|------|
| **Generator** | 任务分配时 | 否 | 为作家准备技法参考 |
| **Generator** | 创作过程中 | 否 | 作家主动查询 |
| **Evaluator** | 评估开始时 | 是 | 获取评估标准 |
| **Evaluator** | 生成反馈时 | 是 | 引用具体技法 |

---

## 🔍 检索优先级规则

**信息检索时按层级依次尝试，不跳过。首次降级时通知用户。**

### 优先级层级

```
┌─────────────────────────────────────────────────────────────┐
│ Level 1: Qdrant 向量数据库                                    │
│ ├── 集合：novel_settings, writing_techniques, case_library   │
│ ├── 触发：数据库服务可用（db_manager.status = 'available'）  │
│ ├── 优势：语义检索精准、结构化分类                            │
│ └── 降级条件：连接失败/服务未启动                              │
└─────────────────────────────────────────────────────────────┘
                              ↓ 无结果或不可用
┌─────────────────────────────────────────────────────────────┐
│ Level 2: 本地数据文件                                         │
│ ├── 降级缓存：.cache/db_cache/*.json                         │
│ ├── 知识图谱：.vectorstore/knowledge_graph.json              │
│ ├── 触发：Qdrant 不可用时的降级模式                           │
│ ├── 优势：无外部依赖、离线可用                                │
│ ├── 缺点：仅文本匹配、无语义检索                              │
│ └── 降级条件：文件不存在或无数据                              │
│                                                              │
│ ⚠️ 首次降级时提示用户："数据库降级运行，使用本地数据"         │
└─────────────────────────────────────────────────────────────┘
                              ↓ 无结果
┌─────────────────────────────────────────────────────────────┐
│ Level 3: 原始文件大纲                                         │
│ ├── 总大纲.md                                                │
│ ├── 章节大纲/*.md                                            │
│ ├── 创作技法/**/*.md                                         │
│ ├── 触发：以上层级都无信息                                    │
│ ├── 优势：最原始数据、可直接编辑                              │
│ └── 降级条件：文件不存在或解析失败                            │
└─────────────────────────────────────────────────────────────┘
                              ↓ 无结果
┌─────────────────────────────────────────────────────────────┐
│ Level 4: 标记待补充                                           │
│ ├── 处理：不中断流程，标记缺失项为"待补充"                     │
│ ├── 输出：在创作结果中标注"该设定暂缺，建议补充"               │
│ └── 用户体验：允许试运行用户在无数据时继续使用                 │
└─────────────────────────────────────────────────────────────┘
```

### 数据库状态映射

| db_manager.status | 检索起点 | 说明 |
|-------------------|----------|------|
| `available` | Level 1 | Qdrant 正常运行 |
| `degraded` | Level 2 | Qdrant 不可用，使用本地缓存（首次通知） |
| `unavailable` | Level 3 | 无本地数据，从原始文件读取 |

### 检索示例

```
查询角色 '[示例角色B]'

Step 1: Qdrant(novel_settings) → search("[示例角色B]")
        → 无结果
        
Step 2: .cache/db_cache/novel_settings.json → text_match("[示例角色B]")
        → 无结果
        → 首次降级通知用户
        
Step 3: knowledge_graph.json → 查实体 "[示例角色B]"
        → 无结果
        
Step 4: 总大纲.md → parse_find("[示例角色B]")
        → 无结果
        
Step 5: 标记 "林夕设定暂缺" → 继续创作
```

### 适用范围

| 检索类型 | 集合/文件 | 优先级规则 |
|----------|-----------|------------|
| **小说设定** | novel_settings, knowledge_graph.json | 同上 |
| **创作技法** | writing_techniques | 同上 |
| **标杆案例** | case_library | 同上 |

### 降级通知机制

```
首次检测到降级状态时：
├── 输出提示："⚠️ 数据库降级运行，使用本地数据"
├── 记录降级状态（避免重复通知）
└── 继续执行后续流程

后续检索不再重复通知。
```

### 移植模块关联

移植模块（modules/migration/）会：
- **保留**：scene_writer_mapping.json（场景-作家映射规则）
- **清空**：knowledge_graph.json、.cache/db_cache/（需用户重新填充）
- **清空**：.vectorstore/qdrant/（需重新初始化数据库）

因此移植后的项目：
- Level 1（Qdrant）需要重新初始化
- Level 2（本地数据）可能为空
- 常依赖 Level 3（原始文件）或 Level 4（标记待补充）

---

## 知识检索集成（大纲/设定）

### 知识库内容

| 类型 | 内容 | 检索方法 |
|------|------|----------|
| **角色** | 人物设定 | `get_character(name)` |
| **势力** | 组织/文明 | `get_faction(name)` |
| **派系** | 势力内分支 | `search_novel(query, entity_type="派系")` |
| **力量体系** | 修炼体系 | `search_novel(query, entity_type="力量体系")` |
| **力量派别** | 力量体系分支 | `get_power_branch(name)` |
| **时代** | 时间段 | `search_novel(query, entity_type="时代")` |
| **事件** | 发生的事情 | `search_novel(query, entity_type="事件")` |

### Generator 阶段知识检索

创作前必须获取相关设定：

```python
# 调用示例
import sys
# [N18 2026-04-18] 该 sys.path 注入在 M2-β 后失效;.vectorstore/ 已无 .py 框架
# 如需直接检索知识库，请使用 Python API：`from modules.knowledge_base.search_manager import SearchManager`
# 动态检测项目根目录（示例）
_project_root = Path.cwd()  # 实际使用时从 config.json 读取
sys.path.insert(0, str(_project_root))
from knowledge_search import KnowledgeSearcher

searcher = KnowledgeSearcher()

# 获取章节大纲（通过语义检索）
def get_chapter_outline(chapter_name: str):
    # 示例: get_chapter_outline("第一章")
    results = searcher.search_novel(chapter_name, entity_type="事件", top_k=3)
    return results

# 获取角色设定（涉及该角色时必须调用）
def get_character_setting(character_name: str):
    character = searcher.get_character(character_name)
    return character

# 获取势力设定（涉及该势力时必须调用）
def get_faction_setting(faction_name: str):
    faction = searcher.get_faction(faction_name)
    return faction

# 获取力量派别设定
def get_power_branch_setting(branch_name: str):
    power = searcher.get_power_branch(branch_name)
    return power

# 统一检索（模糊查询）
def search_all(query: str, entity_type: str = None):
    results = searcher.search_novel(query, entity_type=entity_type, top_k=10)
    return results
```

### 工作流知识调用时机

| 阶段 | 调用时机 | 必须 | 说明 |
|------|----------|------|------|
| **准备阶段** | 任务分解时 | 是 | 获取相关设定/事件，确定场景和任务 |
| **Generator** | 涉及角色时 | 是 | 获取角色设定（外貌、性格、能力） |
| **Generator** | 涉及势力时 | 是 | 获取势力设定（背景、关系） |
| **Generator** | 涉及战斗时 | 是 | 获取力量派别设定 |
| **Evaluator** | 检查一致性时 | 推荐 | 验证内容与设定一致 |

### 知识调用集成点

```
Step 0：准备阶段
├── 【知识检索】获取相关设定/事件 ← 必须
├── 分析场景类型
├── 确定涉及角色 → 【知识检索】获取角色设定 ← 必须
├── 确定涉及势力 → 【知识检索】获取势力设定 ← 必须
└── 输出任务列表

Step 1：任务分解
├── 分析场景内容
├── 【知识检索】获取相关设定 ← 必须
└── 输出子任务列表

Step 2：Generator 执行
├── 作家接收任务（含设定信息）
├── 作家输出内容
└── 检查设定一致性

Step 3：Evaluator 评估
├── 【技法检索】获取评估标准 ← 必须
├── 【知识检索】验证设定一致性 ← 推荐
├── 禁止项检测
└── 输出反馈
```

### 输入格式（含知识）

```yaml
任务信息:
  场景ID: "scene_001"
  任务类型: "战斗铺垫"
  目标字数: "1200-1500"
  
上下文:
  前文内容: "..."
  
  # 从知识库获取的设定
  章节大纲:
    章节: "第一章"
    场景: "林远与血脉者佣兵对决"
    目标: "以弱胜强但付出代价"
    
  角色设定:
    - 名称: "林远"
      外貌: "..."
      性格: "..."
      能力: "..."
    - 名称: "[示例角色A]"
      外貌: "..."
      背景: "佣兵联盟成员"
      
  势力设定:
    - 名称: "佣兵联盟"
      背景: "..."
      特点: "..."
      
要求:
  - 遵守角色设定
  - 遵守势力设定
  - 符合章节大纲目标
```

### 数据同步机制

当大纲或设定文件修改时，需要手动同步到数据库：

```python
# 使用 workflow.py 统一入口
import sys
# [N18 2026-04-18] 该 sys.path 注入在 M2-β 后失效;.vectorstore/ 已无 .py 框架
# 如需直接检索知识库，请使用 Python API：`from modules.knowledge_base.search_manager import SearchManager`
# 动态检测项目根目录（示例）
_project_root = Path.cwd()  # 实际使用时从 config.json 读取
sys.path.insert(0, str(_project_root))
from workflow import NovelWorkflow

workflow = NovelWorkflow()

# 查看统计信息
stats = workflow.get_stats()

# 检索小说设定
results = workflow.search_novel("[示例角色B]", entity_type="角色")

# 检索创作技法
techs = workflow.search_techniques("战斗代价", dimension="战斗")
```

**命令行同步**（设定文件更新后执行）：

```bash
cd {PROJECT_ROOT}/.vectorstore

# 同步到向量数据库（双库同步）
python sync_to_vectorstore_v3.py

# 重建知识图谱
python rebuild_knowledge_graph_v2.py

# 生成可视化
python graph_visualizer.py
```

---

## 技能依赖

```
novelist-workflow（调度器）
├── novelist-shared（共享规范）
├── workflow.py（统一工作流入口）
├── knowledge_search.py（小说设定检索）← 角色/势力/力量派别
├── technique_search.py（创作技法检索）← 10维度技法
├── novelist-canglan（苍澜 - 世界观）
├── novelist-xuanyi（玄一 - 剧情）
├── novelist-moyan（墨言 - 人物）
├── novelist-jianchen（剑尘 - 战斗）
├── novelist-yunxi（云溪 - 意境/润色）
└── novelist-evaluator（审核师）
```

### 数据源

| 数据源 | 类型 | 集合/文件 | 内容 | 说明 |
|--------|------|-----------|------|------|
| **Qdrant** | 向量数据库 | `novel_settings` | 势力、角色、力量体系、时代、事件 | 语义检索，首选 |
| **Qdrant** | 向量数据库 | `writing_techniques` | 世界观、剧情、人物等11维度技法 | 语义检索，首选 |
| **Qdrant** | 向量数据库 | `case_library` | 标杆案例库 | 语义检索，首选 |
| **本地缓存** | JSON | `.cache/db_cache/*.json` | 降级模式缓存 | Qdrant不可用时 |
| **知识图谱** | JSON | `knowledge_graph.json` | 实体关系网络 | 移植后需重建 |
| **场景映射** | JSON | `scene_writer_mapping.json` | 场景-作家映射规则 | 移植时保留 |

### 数据库配置

```python
# Qdrant 连接参数
{
    "host": "localhost",
    "port": 6333,
    "url": "http://localhost:6333",
    "vector_dim": 384,
    "distance": "COSINE",
    "embed_model": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

### 移植注意事项

移植后需要：
1. 重新启动 Qdrant Docker
2. 运行 `python -m core kb --sync novel` 同步设定
3. 运行 `python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild` 同步技法
4. 重建知识图谱 `python rebuild_knowledge_graph_v2.py`

---

## 迭代优化机制

### 问题背景

迭代循环导致时间不可控：
- 理想情况：151秒/场景
- 最坏情况：481秒/场景（3次迭代）
- 时间波动：218%

### 优化方案

#### 优化1：迭代风险预测

**在阶段0结束时预测迭代风险，提前预警。**

```python
from modules.creation import IterationPredictor, IterationRisk

predictor = IterationPredictor()
prediction = predictor.predict(
    scene_type="战斗场景",
    scene_description="主角目睹母亲被杀，血脉觉醒",
    experience_count=2,
    setting_completeness=0.7,
    discussion_rounds=2,
)

if prediction.risk_level == IterationRisk.CRITICAL:
    print("⚠️ 高迭代风险，建议继续讨论")
    print(f"风险因素: {prediction.risk_factors}")
    print(f"建议: {prediction.recommendations}")
```

**风险因素权重：**

| 因素 | 权重 | 说明 |
|------|------|------|
| 冲突数量 | 25% | Phase 1 输出冲突数 |
| 场景复杂度 | 20% | 场景类型和描述复杂度 |
| 经验丰富度 | 15% | 前章经验数量 |
| 设定完整度 | 15% | 相关设定完整性 |
| 讨论深度 | 15% | 阶段0讨论轮次 |
| 技法数量 | 10% | 计划使用的技法数 |

**风险等级映射：**

| 风险值 | 等级 | 预期迭代 | 建议 |
|--------|------|----------|------|
| < 0.25 | LOW | 1次 | 正常执行 |
| 0.25-0.5 | MEDIUM | 2次 | 注意监控 |
| 0.5-0.75 | HIGH | 3次 | 建议优化输入 |
| > 0.75 | CRITICAL | 3次 | 建议返回阶段0 |

---

#### 优化2：快速失败机制

**每个 Phase 输出后检查质量，不合格立即返回重做。**

```python
from modules.creation import QuickFailChecker

checker = QuickFailChecker()

# 检查 Phase 1 输出
result = checker.check_phase1_output("世界观约束", phase1_worldview)
if not result.passed:
    print(f"Phase 1 不合格: {result.issues}")
    if result.retry_recommended:
        return {"status": "phase1_retry", "reason": result.retry_reason}

# 检查 Phase 2 输出
result = checker.check_phase2_output(phase2_content, target_word_count=3000)
if not result.passed:
    print(f"Phase 2 不合格: {result.issues}")
```

**检查阈值：**

| Phase | 阈值 | 检查项 |
|-------|------|--------|
| Phase 1 | 0.5 | 输出完整性、逻辑一致性 |
| Phase 2 | 0.6 | 字数、禁止项 |
| Phase 3 | 0.7 | 整体质量 |

---

#### 优化3：动态迭代调整

**根据场景复杂度和实时反馈调整迭代上限。**

```python
from modules.creation import DynamicIterationAdjuster, SceneComplexity

adjuster = DynamicIterationAdjuster()

# 获取最大迭代次数
max_iter = adjuster.get_max_iterations(
    scene_type="战斗场景",
    complexity=SceneComplexity.COMPLEX,
    prediction=prediction,
    user_preference="balanced",  # "speed" / "quality" / "balanced"
)

# 判断是否继续迭代
should_continue, reason = adjuster.should_continue_iteration(
    current_iteration=1,
    max_iterations=max_iter,
    quality_score=0.6,
    improvement_rate=0.1,
)
```

**复杂度基准：**

| 场景类型 | 复杂度 | 默认迭代上限 |
|----------|--------|-------------|
| 章节润色 | SIMPLE | 1次 |
| 剧情推进 | MODERATE | 2次 |
| 战斗场景 | COMPLEX | 3次 |

**终止条件：**
- 达到最大迭代次数
- 质量分数 ≥ 0.8
- 改进率 < 5%（连续迭代无明显改进）

---

#### 优化4：云溪融合润色合并

**将 Phase 1.6（融合）和 Phase 3（润色）合并为一次调用。**

```python
from modules.creation import fuse_and_polish, FusionPolishMode

# 合并调用
result = fuse_and_polish(
    phase1_worldview=worldview,
    phase1_plot=plot,
    phase1_character=character,
    conflicts=conflicts,
    phase2_content=phase2_content,
    mode=FusionPolishMode.FULL,
)

# 结果
print(f"融合说明: {result.fusion_notes}")
print(f"润色字数: {result.word_count}")
print(f"节省时间: {result.time_saved_seconds}秒")
```

**效率提升：**

| 指标 | 传统方案 | 合并方案 | 提升 |
|------|---------|---------|------|
| 调用次数 | 2次 | 1次 | 50% |
| 耗时 | ~60秒 | ~30秒 | 50% |
| 上下文共享 | 否 | 是 | 风格更统一 |

---

### 优化效果预估

| 场景 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 理想情况 | 151秒 | 121秒 | 20% |
| 中等情况 | 250秒 | 180秒 | 28% |
| 最坏情况 | 481秒 | 280秒 | 42% |

**关键改善：**
1. 迭代预测 → 避免 CRITICAL 风险场景的盲目创作
2. 快速失败 → 减少无效后续操作
3. 动态调整 → 简单场景不浪费迭代
4. 云溪合并 → 减少调用开销

---

## 阶段5.5：三方协商（创意契约生成）

### 执行规范

> ⛔ **强制执行，不可跳过**：阶段5完成后必须执行本阶段。禁止因用户表示"满意"或"不需要修改"而跳过。"满意，定稿"选项仅在阶段7出现，阶段5.5/5.6/6/7是必经阶段，不向用户提供任何跳过入口。唯一合法跳过条件：鉴赏师输出0条建议（章节已达到高质量），此时跳过5.5/5.6直接进入阶段6。

> ⚠️ **强制角色分离**：鉴赏师和评估师在此阶段扮演不同角色，必须按顺序执行，不得合并。

#### 第一步：鉴赏师建议生成

鉴赏师读取阶段5输出的完整章节，执行以下操作：
1. 调用 `novelist-connoisseur` SKILL
2. 查阅反模板约束库（45条创意菜单），识别可注入的创意手法
3. 查阅记忆点库（作者审美指纹），匹配作者偏好
4. 输出 N 条创意建议，每条包含：
   - 目标段落（paragraph_index）
   - 引用约束ID（如 ANTI_001）
   - 理由（与记忆点的关联，字数等）

> 边界情况：若鉴赏师输出 **0 条建议**（章节已达到高质量），直接跳过 5.5/5.6，进入阶段6。

#### 第二步：评估师审议建议

评估师**只审鉴赏师的建议本身，不审整章内容**：
- 对每条建议标：`采纳` / `驳回` / `有条件`
- 标违规风险（12大一致性规则 + 其他维度）
- 注明风险会影响哪些评估维度（供 preserve_list 豁免映射用）

#### 第三步：三方拍板讨论

展示给用户：
```
【阶段5.5：三方协商】

鉴赏师建议：
  建议#1：第3段 - 视角反叛（ANTI_001）
    理由：你的记忆点显示败者视角+3爽快，累计7条记录
  建议#2：第7段 - 节奏加速（ANTI_015）
    理由：此段情节密度过低，参考案例X

评估师审议：
  建议#1：采纳 ⚠️ 风险: 主角视角连贯性 -0.1（豁免映射: 维度"视角连贯性"）
  建议#2：驳回 ❌ 理由: 违反12一致性规则#7（时间线连贯）

作者决定：
  请回复：[采纳/驳回] #1, [采纳/驳回] #2
  或输入自定义意见：
```

#### 第四步：生成创意契约

根据作者决定，生成创意契约 JSON 并输出摘要：

```json
{
  "contract_id": "cc_第N章_001",
  "chapter_ref": "第N章",
  "preserve_list": [
    {
      "item_id": "#1",
      "scope": {"paragraph_index": 3},
      "applied_constraint_id": "ANTI_001",
      "rationale": "作者采纳",
      "exempt_dimensions": ["视角连贯性"]
    }
  ],
  "rejected_list": [{"item_id": "#2", "reason": "12一致性规则#7违规"}],
  "writer_assignments": [],
  "iteration_count": 0,
  "max_iterations": 3
}
```

---

## 阶段5.6：鉴赏师派单改写

### 执行规范

> ⚠️ **顺序执行**：在当前 session 内依次执行各派单任务，禁止启动 background task 或 subagent。

#### 第一步：生成派单任务列表

根据 preserve_list，对每条采纳建议确定派单对象：
- 场景级视角/战斗类修改 → 剑尘（`novelist-jianchen`）
- 节奏/情感/过渡类修改 → 云溪（`novelist-yunxi`）
- 对话/心理类修改 → 依场景类型判断

#### 第二步：依次执行各派单任务

每条派单调用对应写手时，**在 prompt 末尾追加创意契约约束块**：

```
【创意契约约束】
本次重写涉及创意契约，请注意：
preserve_list 标注区域（第N段，位置 char_start ~ char_end）：
  - 这是作者已采纳的创意手法（[约束名称]）
  - 你的重写【禁止修改】此区域的核心手法
  - 你只能优化区域内的字词/语流，不能还原成原手法
  - 区域外可正常修改
```

在当前 session 内**逐条执行**，收集改写结果。

#### 第三步：云溪接缝处理（仅限被改写段落±1段）

所有派单任务完成后，云溪**只处理被改写的段落及其上下各1段**（共最多3段/处），用于平滑拼接痕迹：
- 识别本轮被改写的段落编号列表
- 对每处改写：取「改写段落 -1段 / 改写段落本身 / 改写段落 +1段」做局部衔接
- **未被改写的段落一字不动**
- 同样传入创意契约约束块，确保 preserve_list 区域不被破坏

> ⚠️ 禁止整章通读润色——云溪的全局视角会把写手的个性磨平。

#### 输出格式

```
【阶段5.6：派单改写完成】
派单任务：N条
  - #1 → 剑尘：第3段视角重写 ✅
  - #2 → 云溪：节奏调整 ✅
云溪接缝处理：涉及段落 [3,4,5, 8,9,10] ✅（其余段落未动）

改写后章节已就绪，进入阶段6评估。
```

---

## 阶段6：整章评估（带创意契约豁免）

### 执行规范

> ⚠️ **强制循环逻辑**：评估结果决定下一步，不得跳过。

#### 第一步：调用评估师

调用 `novelist-evaluator` 对整章内容进行13维度打分，同时传入创意契约：
- `preserve_list` 中指定的段落/维度 → **跳过评估（豁免）**
- 其余部分正常打分

#### 第二步：按评分结果执行跳转（必须严格遵守）

```
评估完成后：

IF 综合评分 ≥ 0.8:
    → 直接进入【阶段7：用户确认】

ELSE IF 综合评分 < 0.8 AND 迭代次数 == 1:
    迭代次数 = 2
    → 回到【阶段5.6：派单改写】
      · 传入评估师的具体失分维度作为改写目标
      · 契约不变（preserve_list 不修改）
    → 改写完成后重新执行【阶段6】

ELSE IF 综合评分 < 0.8 AND 迭代次数 == 2:
    迭代次数 = 3
    → 回到【阶段5.6：派单改写】（同上）
    → 改写完成后重新执行【阶段6】

ELSE IF 综合评分 < 0.8 AND 迭代次数 == 3:
    → 触发对话升级，向用户展示三个选项：
      [a] 撤销某条采纳建议（将其移入 rejected_list，回阶段5.6）
      [b] author_force_pass（强制通过，标记推翻事件，进入阶段7）
      [c] 整章重协商（清空创意契约，回阶段5.5）
```

#### 第三步：迭代次数追踪

在阶段6开始前初始化（每章重置）：
```
evaluation_iteration = 1  # 第一次评估时为1
```

每次"回5.6再评估"时递增：
```
evaluation_iteration += 1
```

#### 输出格式

```
【阶段6：整章评估 - 第N次】
综合评分: X.XX
豁免维度: [preserve_list中豁免的维度]
失分维度: [具体失分项及原因]

→ 下一步: [放行进阶段7 / 回5.6第N次重写 / 对话升级]
```

---

## 阶段7：用户确认与智能反馈处理（新增）

### 系统定位

**解决的核心问题**：用户对工作流输出不满意时，如何高效修改

**覆盖的场景**：

| 场景 | 用户意图 | 处理方式 |
|------|----------|----------|
| 局部修改 | "这句太AI味了" | 智能反馈处理器 |
| 章节重写 | "重写第一章" | 重写处理器（4种模式） |
| 追踪同步 | 修改后追踪文件自动更新 | 追踪同步层 |

---

### 用户确认流程

```
评估通过（技术指标达标）
        ↓
┌─────────────────────────────────────────────────────────────┐
│ 用户确认                                                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [1] ✅ 满意，定稿                                           │
│     → 进入阶段8（经验写入）                                  │
│                                                             │
│ [2] ❌ 整体不满意，重新规划                                  │
│     → 返回阶段0（需求澄清）                                  │
│                                                             │
│ [3] ✏️ 部分不满意，提供反馈                                 │
│     → 智能反馈处理                                          │
│                                                             │
│ [4] 🔄 重写章节                                             │
│     → 重写处理                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 修改层级体系

| 层级 | 名称 | 影响范围 | 追踪更新 |
|------|------|----------|----------|
| **层级 1** | 文字润色 | 不改变内容，只改表达 | ❌ 不更新 |
| **层级 2** | 内容微调 | 改细节，可能影响追踪 | ⚠️ 检测后决定 |
| **层级 3** | 剧情修改 | 改事件/结局 | ✅ 必须更新 |
| **层级 4** | 设定修改 | 改世界观/人物，全书影响 | ✅ 必须更新 |

---

### 智能反馈处理流程

```
用户输入反馈
        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 意图识别                                             │
├─────────────────────────────────────────────────────────────┤
│ • 识别修改层级（1-4）                                        │
│ • 识别重写模式（A/B/C/D）                                    │
│ • 路由到对应处理器                                          │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 反馈解析                                             │
├─────────────────────────────────────────────────────────────┤
│ • 情感分析：满意/不满意分离                                  │
│ • 内容定位：定位到具体段落/句子                              │
│ • 问题分类：关联评估维度                                    │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 满意度分离                                           │
├─────────────────────────────────────────────────────────────┤
│ • 建立内容掩码（保护/可修改）                                │
│ • 分析修改影响范围                                          │
│ • 生成修改策略建议                                          │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 修改范围选择                                         │
├─────────────────────────────────────────────────────────────┤
│ • 策略 A：只改指定的                                         │
│ • 策略 B：连带调整相关内容                                   │
│ • 策略 C：AI 判断修改范围                                    │
│ • 用户选择策略                                              │
└─────────────────────────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 智能修改执行                                         │
├─────────────────────────────────────────────────────────────┤
│ • 调用对应作家执行修改                                       │
│ • 修改后评估                                                │
│ • 追踪同步                                                  │
└─────────────────────────────────────────────────────────────┘
        ↓
    返回用户确认
```

---

### 重写处理流程

```
用户选择 [4] 重写章节
        ↓
┌─────────────────────────────────────────────────────────────┐
│ 选择重写模式                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [A] 剧情保留重写                                             │
│     → 提取框架 → 约束生成 → 验证一致性                       │
│     → 追踪文件：❌ 不更新                                    │
│                                                             │
│ [B] 剧情调整重写                                             │
│     → 提取框架 → 允许修改 → 追踪更新                         │
│     → 追踪文件：✅ 更新                                      │
│                                                             │
│ [C] 完全重新创作                                             │
│     → 从大纲生成 → 重置追踪                                  │
│     → 追踪文件：✅ 重置                                      │
│                                                             │
│ [D] 参考原稿创作                                             │
│     → 提取优缺点 → 参考生成 → 对比更新                       │
│     → 追踪文件：⚠️ 对比后决定                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
        ↓
执行重写
        ↓
返回用户确认
```

---

### 追踪系统处理策略

| 操作类型 | hook_ledger | timeline_tracking | information_boundary | payoff_tracking |
|----------|-------------|-------------------|----------------------|-----------------|
| 层级 1 修改 | ❌ 不更新 | ❌ 不更新 | ❌ 不更新 | ❌ 不更新 |
| 层级 2 修改 | ⚠️ 检测后决定 | ⚠️ 检测后决定 | ⚠️ 检测后决定 | ⚠️ 检测后决定 |
| 层级 3 修改 | ✅ 更新 | ✅ 更新 | ✅ 更新 | ✅ 更新 |
| 层级 4 修改 | ✅ 更新 | ✅ 更新 | ✅ 更新 | ✅ 更新 |
| 模式 A 重写 | ❌ 不更新 | ❌ 不更新 | ❌ 不更新 | ❌ 不更新 |
| 模式 B 重写 | ✅ 更新 | ✅ 更新 | ✅ 更新 | ✅ 更新 |
| 模式 C 重写 | ✅ 重置 | ✅ 重置 | ✅ 重置 | ✅ 重置 |
| 模式 D 重写 | ⚠️ 对比后决定 | ⚠️ 对比后决定 | ⚠️ 对比后决定 | ⚠️ 对比后决定 |

---

### 核心模块

#### 1. 意图识别器

```python
from enum import Enum
from dataclasses import dataclass

class ModificationLevel(Enum):
    """修改层级"""
    WORD_POLISH = 1      # 文字润色
    CONTENT_TWEAK = 2    # 内容微调
    PLOT_CHANGE = 3      # 剧情修改
    SETTING_CHANGE = 4   # 设定修改

class RewriteMode(Enum):
    """重写模式"""
    PLOT_PRESERVE = "A"      # 剧情保留重写
    PLOT_ADJUST = "B"        # 剧情调整重写
    FULL_RECREATE = "C"      # 完全重新创作
    REFERENCE_BASED = "D"    # 参考原稿创作

@dataclass
class IntentResult:
    """意图识别结果"""
    is_rewrite: bool
    modification_level: ModificationLevel
    rewrite_mode: RewriteMode
    confidence: float
    routing: str  # 路由目标处理器

def recognize_intent(user_input: str, context: dict) -> IntentResult:
    """
    识别用户意图
    
    Args:
        user_input: 用户输入
        context: 当前上下文（章节内容、评估结果等）
    
    Returns:
        意图识别结果
    """
    # 实现意图识别逻辑
    pass
```

#### 2. 反馈解析器

```python
@dataclass
class ParsedFeedback:
    """解析后的反馈"""
    satisfied_parts: List[str]      # 满意的部分
    unsatisfied_parts: List[str]    # 不满意的部分
    locations: List[dict]           # 定位信息
    related_dimensions: List[str]   # 关联的评估维度

def parse_feedback(user_feedback: str, content: str) -> ParsedFeedback:
    """
    解析用户反馈
    
    Args:
        user_feedback: 用户反馈文本
        content: 当前章节内容
    
    Returns:
        解析后的反馈结构
    """
    # 实现反馈解析逻辑
    pass
```

#### 3. 满意度分离器

```python
@dataclass
class ContentMask:
    """内容掩码"""
    protected: List[dict]    # 保护的部分
    modifiable: List[dict]   # 可修改的部分
    influence_range: dict    # 影响范围

def separate_satisfaction(
    parsed_feedback: ParsedFeedback,
    content: str
) -> ContentMask:
    """
    分离满意/不满意内容，建立掩码
    
    Args:
        parsed_feedback: 解析后的反馈
        content: 当前章节内容
    
    Returns:
        内容掩码
    """
    # 实现满意度分离逻辑
    pass
```

#### 4. 智能修改器

```python
from enum import Enum

class ModificationStrategy(Enum):
    """修改策略"""
    EXACT_ONLY = "A"        # 只改指定的
    RELATED_TOO = "B"       # 连带调整相关
    AI_JUDGED = "C"         # AI判断范围

@dataclass
class ModificationResult:
    """修改结果"""
    modified_content: str
    changed_parts: List[dict]
    tracking_updates: dict
    influence_report: str

def smart_modify(
    content: str,
    content_mask: ContentMask,
    strategy: ModificationStrategy,
    user_selection: str
) -> ModificationResult:
    """
    智能修改
    
    Args:
        content: 当前内容
        content_mask: 内容掩码
        strategy: 修改策略
        user_selection: 用户指定的修改
    
    Returns:
        修改结果
    """
    # 实现智能修改逻辑
    pass
```

#### 5. 重写处理器

```python
@dataclass
class PlotFramework:
    """剧情框架"""
    scenes: List[dict]          # 场景列表
    events: List[dict]          # 事件序列
    foreshadows: List[dict]     # 伏笔设置
    character_states: dict      # 角色状态

def extract_plot_framework(content: str) -> PlotFramework:
    """
    从原稿提取剧情框架
    
    Args:
        content: 原稿内容
    
    Returns:
        剧情框架
    """
    # 实现框架提取逻辑
    pass

def process_rewrite(
    mode: RewriteMode,
    original_content: str,
    outline: dict,
    framework: PlotFramework = None
) -> str:
    """
    处理重写请求
    
    Args:
        mode: 重写模式
        original_content: 原稿内容
        outline: 章节大纲
        framework: 剧情框架（模式A/B需要）
    
    Returns:
        重写后的内容
    """
    # 实现重写处理逻辑
    pass
```

#### 6. 追踪同步层

```python
@dataclass
class TrackingUpdate:
    """追踪更新"""
    hook_ledger: dict
    timeline_tracking: dict
    information_boundary: dict
    payoff_tracking: dict
    manual_confirm_needed: List[str]

def sync_tracking(
    original_content: str,
    modified_content: str,
    modification_level: ModificationLevel,
    tracking_files: dict
) -> TrackingUpdate:
    """
    同步追踪文件
    
    Args:
        original_content: 原内容
        modified_content: 修改后内容
        modification_level: 修改层级
        tracking_files: 当前追踪文件
    
    Returns:
        追踪更新结果
    """
    # 实现追踪同步逻辑
    pass
```

#### 7. 影响范围分析器

```python
@dataclass
class InfluenceReport:
    """影响范围报告"""
    current_chapter: List[str]
    tracking_files: List[str]
    future_chapters: List[str]
    global_settings: List[str]
    severity: str  # LOW / MEDIUM / HIGH

def analyze_influence(
    modification_level: ModificationLevel,
    content_changes: dict
) -> InfluenceReport:
    """
    分析修改影响范围
    
    Args:
        modification_level: 修改层级
        content_changes: 内容变化
    
    Returns:
        影响范围报告
    """
    # 实现影响分析逻辑
    pass
```

#### 8. 迭代安全防护

```python
@dataclass
class SafetyCheck:
    """安全检查结果"""
    can_continue: bool
    reason: str
    recommendation: str

def check_iteration_safety(
    iteration_count: int,
    quality_scores: List[float],
    improvement_rate: float
) -> SafetyCheck:
    """
    检查迭代安全性
    
    Args:
        iteration_count: 当前迭代次数
        quality_scores: 历史质量分数
        improvement_rate: 改进率
    
    Returns:
        安全检查结果
    """
    MAX_ITERATIONS = 5
    QUALITY_THRESHOLD = 0.6
    MIN_IMPROVEMENT = 0.05
    
    # 最大迭代次数检查
    if iteration_count >= MAX_ITERATIONS:
        return SafetyCheck(
            can_continue=False,
            reason=f"达到最大迭代次数 {MAX_ITERATIONS}",
            recommendation="建议用户确认当前版本或选择重写"
        )
    
    # 质量下降检查
    if len(quality_scores) >= 2:
        if quality_scores[-1] < quality_scores[-2]:
            return SafetyCheck(
                can_continue=False,
                reason="质量分数下降",
                recommendation="回滚到上一版本"
            )
    
    # 收益递减检查
    if improvement_rate < MIN_IMPROVEMENT:
        return SafetyCheck(
            can_continue=False,
            reason=f"改进率低于阈值 {MIN_IMPROVEMENT}",
            recommendation="迭代收益递减，建议接受当前版本"
        )
    
    return SafetyCheck(can_continue=True, reason="", recommendation="")
```

---

### 与现有系统集成

| 现有模块 | 集成方式 |
|----------|----------|
| novel-workflow | 添加阶段7（用户确认与智能反馈处理） |
| novelist-evaluator | 复用 JSON 问题格式、三级权重体系 |
| novelist-technique-search | 复用维度/场景过滤、技法引用 |
| conflict_detector | 复用冲突检测逻辑 |
| yunxi_fusion_polisher | 复用修改润色能力 |
| iteration_optimizer | 扩展支持用户反馈驱动迭代 |

---

### 实现优先级

| 模块 | 必须实现 | 可选 |
|------|----------|------|
| 意图识别器 | ✅ | |
| 反馈解析器 | ✅ | |
| 满意度分离器 | ✅ | |
| 智能修改器（策略 A+B） | ✅ | |
| 智能修改器（策略 C） | | ✅ |
| 重写处理器（模式 A+B） | ✅ | |
| 重写处理器（模式 C+D） | | ✅ |
| 剧情框架提取器 | ✅ | |
| 追踪同步层 | ✅ | |
| 影响范围分析器 | ✅ | |
| 迭代安全防护 | ✅ | |

---

