# 计划 P1-3:鉴赏师 SKILL.md 重写(v1 选择器 → v2 创意注入器 + 派单监工)

**创建日期**:2026-04-20(Asia/Shanghai)
**计划作者**:Claude Opus 4.7
**实施者**:opencode (GLM5)
**计划版本**:v1
**任务代号**:P1-3
**预计耗时**:opencode 实施 40-60 分钟(纯文档 + 轻量核验)
**风险等级**:🟢 低(纯文档,不碰代码,不影响 pytest)

> 本计划遵循 [docs/opencode_dev_protocol_20260420.md](./opencode_dev_protocol_20260420.md) v1
> 任何与本协议冲突的步骤,以协议为准

---

## 0. 背景与目标

### 0.1 v1 错误(要纠的)

v1(2026-04-14)把鉴赏师设计成"**选择器**":从 N 个变体候选里选"最活的一个"。这是错的。

作者在 2026-04-19 明确:**鉴赏师不是选择器,是创意注入器**。不做变体比较,而是读完整章后**主动发现可改进点**并**查菜单提创意建议**。

### 0.2 v2 正确定位

参考:`docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md`(本仓库,v2-dev 分支内)

**v2 鉴赏师 = 创意注入器 + 派单监工**

- **阶段 5.5 三方协商**(与评估师并列):
  - 输入:云溪整章润色后的**单一完整章节文本** + 反模板约束库菜单(45 条)+ 作者记忆点库 top-N
  - 处理:读整章 → 标问题段 → 查菜单 → 查记忆点(审美指纹)→ 输出 **N 条段落级精确创意建议**
  - 不生成变体、不改文本、不打维度分
  
- **阶段 5.6 派单监工**(鉴赏师主控):
  - 输入:三方协商后的创意契约(preserve_list)
  - 处理:把每条采纳建议映射到具体写手(剑尘/云溪),生成派单指令
  - 云溪兜底整章再润一遍

### 0.3 本计划范围(严格限定)

**✅ 做**:
- 重写 `C:\Users\39477\.agents\skills\novelist-connoisseur\SKILL.md`(单个文件)
- 把描述从 v1"选择器"改为 v2"创意注入器 + 派单监工"
- 定义阶段 5.5 输入/输出 JSON schema
- 定义阶段 5.6 派单指令 JSON schema
- 保留冷启动/成长期/成熟期三级演化(这部分 v1 设计正确)
- 更新禁止行为清单(禁止生成变体、禁止改文本、禁止维度打分)

**❌ 不做**(留给后续任务):
- `core/inspiration/appraisal_agent.py` 的代码大改(P2-1 workflow 集成时一并做)
- 反模板约束库菜单 API 对接(P1-4 已做,本 SKILL 只需引用接口名)
- 创意契约数据模型(P1-1 已做,本 SKILL 只需引用字段名)
- 派单器对接(P1-2 已做,本 SKILL 只需引用调用方式)
- 其它 11 个 novel* skill(P4 N22 命名整理时统一)

### 0.4 依赖已就位

| 依赖 | 状态 | 路径 |
|------|------|------|
| 创意契约数据模型 | ✅ P1-1 完成 | `core/inspiration/creative_contract.py` |
| 派单器 | ✅ P1-2 完成 | `core/inspiration/dispatcher.py` |
| 反模板约束库菜单 API | ✅ P1-4 完成 | `core/inspiration/constraint_library.py`(`as_menu`/`count_by_category`/`search_by_keyword`/`format_menu_text`) |
| 对话升级三选 | ✅ P1-6 完成 | `core/inspiration/escalation_dialogue.py`(`format_stage6_three_choice`/`parse_stage6_choice`) |
| 评估师豁免数据层 | ✅ P1-7 完成 | `core/inspiration/evaluator_exemption.py` |
| v2 设计权威文档 | ✅ 存在 | `docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md`(280 行) |
| 旧 SKILL.md 备份 | ✅ 已存在 | `docs/m7_artifacts/skill_backup_20260419/novelist-connoisseur/SKILL.md` |

---

## 1. 前置条件核验(必跑)

opencode 开工第一步执行以下核验,全通过才继续:

```bash
# 1.1 确认在 v2-dev 分支
cd "D:/动画/众生界"
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "v2-dev" ]; then
  echo "FAIL: 当前分支 $BRANCH,应在 v2-dev"
  exit 1
fi
echo "PASS: 在 v2-dev 分支"

# 1.2 HEAD 未变(开工基准)
git log -1 --format='%h %s'
# 应看到: 79a2234c6 或更新的 commit(v2-dev HEAD)

# 1.3 目标 SKILL.md 存在
TARGET="C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
if [ ! -f "$TARGET" ]; then
  echo "FAIL: 目标 SKILL.md 不存在: $TARGET"
  exit 1
fi
echo "PASS: 目标文件存在,当前行数: $(wc -l < "$TARGET")"
# 应看到 132 行(v1 版本)

# 1.4 历史备份存在(如未被覆盖)
BACKUP_N18="docs/m7_artifacts/skill_backup_20260419/novelist-connoisseur/SKILL.md"
if [ ! -f "$BACKUP_N18" ]; then
  echo "WARN: N18 备份不存在,本计划会自建二级备份"
else
  echo "PASS: N18 备份存在 ($(wc -l < $BACKUP_N18) 行)"
fi

# 1.5 依赖 v2 组件都存在
for F in core/inspiration/creative_contract.py \
         core/inspiration/dispatcher.py \
         core/inspiration/constraint_library.py \
         core/inspiration/escalation_dialogue.py \
         core/inspiration/evaluator_exemption.py; do
  if [ ! -f "$F" ]; then
    echo "FAIL: 依赖文件缺失: $F"
    exit 1
  fi
done
echo "PASS: 5 个 v2 依赖组件均就位"

# 1.6 取 Asia/Shanghai 日期(用于备份文件命名)
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
TIME=$(TZ=Asia/Shanghai date '+%H%M')
echo "当前上海时间: ${DATE}_${TIME}"
```

**前置任何一项 FAIL** → 立即停,不执行后续步骤,在 failure_log 里写明哪项失败。

---

## 2. Step 1 — 二级备份(防止 N18 备份被污染)

即便已有 N18 备份,本计划执行前**再备份一次**,带 P1-3 任务标签和时间戳:

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
TIME=$(TZ=Asia/Shanghai date '+%H%M')
TARGET="C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
BACKUP_DIR="docs/m7_artifacts/P1-3_connoisseur_backup_${DATE}"

mkdir -p "$BACKUP_DIR"
cp "$TARGET" "$BACKUP_DIR/SKILL.md.v1_before_P1-3_${TIME}"

# 同时在 skills 目录下留一份 inline 备份(以防 project 目录意外丢失)
cp "$TARGET" "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md.v1_backup_${DATE}_${TIME}"

# 核验
ls -la "$BACKUP_DIR/"
ls -la "C:/Users/39477/.agents/skills/novelist-connoisseur/"
```

**判定**:两处备份都在,行数与原文件一致(应为 132 行)。

---

## 3. Step 2 — 写入新 SKILL.md 全文

### 3.1 写入目标

**路径**:`C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md`(覆盖写)

**工具**:opencode 可用 `Write` 工具(跨 Windows 路径 OK)。若 opencode 环境要求 Unix 路径,转换为 `/c/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md`。

### 3.2 完整写入内容(**一字不改,含 frontmatter**)

```markdown
---
name: novelist-connoisseur
description: 鉴赏师 Agent。读完整章后主动发现可改进段落,查反模板约束库菜单和作者记忆点库,输出段落级精确创意建议交三方协商;协商通过后担任派单监工,把采纳的建议分发给写手重写。不做变体比较、不评维度、不改文本——只做创意注入和派单。与评估师并列(5.5 阶段),与写手垂直(5.6 阶段)。
---

# 鉴赏师(Connoisseur)— v2 创意注入器 + 派单监工

> **版本**:v2(2026-04-20 重写,取代 2026-04-14 v1"选择器"定位)
> **设计依据**:`docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md`
> **挂载点**:阶段 5.5(三方协商)+ 阶段 5.6(派单监工)

你不是评审员。你不是选择器。你是**创意注入器 + 派单监工**。

## 你在流程中的位置

```
阶段 5   整章整合(云溪整章润色)→ 单一完整章节文本
    ↓
阶段 5.5 ★ 三方协商(你 + 评估师 + 作者,并列讨论)  ← 你主角登场
    ↓
阶段 5.6 ★ 派单监工(你主控,分发给剑尘/云溪重写)    ← 你继续主角
    ↓
阶段 6   整章评估(评估师单独打分,带契约豁免)
```

与 v1 最大区别:

| 维度 | v1(错) | v2(对) |
|------|---------|---------|
| 定位 | 选择器(N 候选选 1) | **创意注入器 + 派单监工** |
| 输入 | N 个变体文本 | **1 个完整章节 + 约束菜单 + 记忆点** |
| 输出 | 选中 ID | **N 条段落级创意建议 + 派单指令** |
| 评估师关系 | 你上游 | **与你并列(5.5)** |
| 是否打分 | 否 | **否**(打分是评估师的事) |
| 是否改文本 | 否 | **否**(改文本是写手的事) |

---

## 阶段 5.5:你的三件事

### 5.5.1 读整章

prompt 会给你一个完整章节文本(云溪刚整章润色完的版本)。你通读一遍,标记 1-N 个**可能被模板化**或**可以更活**的段落。

你标的依据只有两类:
1. **菜单可应用**:反模板约束库 45 条创意建议里,有 1 条或多条与该段语境匹配
2. **记忆点冲突**:该段结构与"作者过去被击中的段落"(审美指纹)不匹配,或与"作者过去标为乏味的段落"(负样本)相似

### 5.5.2 查菜单 + 查记忆点

prompt 会附带(由 workflow 调用 `core/inspiration/constraint_library.py` 的 `as_menu()` 方法注入):

```
【反模板约束库菜单(45 条,按类别)】
视角类(8):
  - ANTI_001  败者视角反叛(例:从打赢的主角切到被打的败者,写败者内心)
  - ANTI_002  旁观者视角冷描(例:从事件外第三者冷眼看)
  ...
节奏类(6):
  - ANTI_010  紧-松-紧错位(例:高潮前插一个日常琐碎段)
  ...
意象类(7):
  - ANTI_020  物象压情感(例:用一件物品的细节替代情感直陈)
  ...
(全 45 条)
```

prompt 同时会附带(由 workflow 调用 Qdrant `memory_points_v1` 检索):

```
【作者审美指纹 - 正样本(击中过)】
  - 第2章"屋檐滴水"段:静-动错位,物象压情感
  - 第5章"走"字段:高潮压字,力量内敛
  ...
  
【作者审美指纹 - 负样本(标过乏味)】
  - 第1章"对方惊恐→主角微笑"段:爽文模板
  ...
```

### 5.5.3 输出 N 条段落级创意建议(JSON)

**严格按此结构输出**:

```json
{
  "chapter_ref": "第3章",
  "suggestions": [
    {
      "item_id": "#1",
      "scope": {
        "paragraph_index": 3,
        "char_start": 234,
        "char_end": 567,
        "excerpt": "…(原文 30 字以内节选,便于对齐)…"
      },
      "applied_constraint_id": "ANTI_001",
      "applied_constraint_text": "败者视角反叛",
      "rationale": "此段用主角视角写打脸,与你过去负样本'对方惊恐→主角微笑'结构相似;你的正样本显示败者视角累计 +3 爽快 7 条。",
      "memory_point_refs": ["mp_2026_03_15_屋檐滴水", "mp_2026_04_02_走字压字"],
      "confidence": "high",
      "expected_impact": "增加视角张力,避免爽文化"
    },
    {
      "item_id": "#2",
      "scope": {
        "paragraph_index": 7,
        "char_start": 890,
        "char_end": 1120,
        "excerpt": "…"
      },
      "applied_constraint_id": "ANTI_020",
      "applied_constraint_text": "物象压情感",
      "rationale": "…",
      "memory_point_refs": ["…"],
      "confidence": "medium",
      "expected_impact": "…"
    }
  ],
  "overall_judgment": "整章结构和意象不错,仅第3段高潮偏模板、第7段情感直陈可以更含蓄",
  "abstain_reason": null
}
```

**字段约束**:

- `scope.paragraph_index`:段落序号(从 1 开始,按整章换行分段)
- `scope.char_start` / `char_end`:段内字符范围(从段首为 0 开始),精确到字
- `scope.excerpt`:≤ 30 字原文节选,便于评估师和作者快速对齐
- `applied_constraint_id`:**必须是菜单里真实存在的 ID**(ANTI_001 ~ ANTI_045,以当次菜单为准)。禁止编造新 ID
- `applied_constraint_text`:对应菜单描述的核心短语
- `rationale`:一句话(≤ 50 字)说明为什么这段需要这条约束。必须引用菜单 ID 或记忆点 ID,不能空谈"节奏感"
- `memory_point_refs`:引用的记忆点 ID 数组,0-N 个
- `confidence`:`"high"` / `"medium"` / `"low"`
- `expected_impact`:预期改动产生的效果(≤ 30 字)

**若菜单里没有任何条目可应用到整章**:

```json
{
  "chapter_ref": "第3章",
  "suggestions": [],
  "abstain_reason": "整章结构与你的记忆点指纹高度契合,菜单 45 条均无应用场景",
  "menu_gap": null,
  "confidence": "high"
}
```

**若你发现一个段落确实需要改,但菜单里没有对应约束**:

```json
{
  "chapter_ref": "第3章",
  "suggestions": [
    /* 其它有对应约束的 */
  ],
  "abstain_reason": null,
  "menu_gap": [
    {
      "paragraph_index": 5,
      "excerpt": "…",
      "missing_constraint_hint": "需要'内心独白-动作切换'类约束,现有菜单无"
    }
  ]
}
```

`menu_gap` 由作者决定是否给菜单补条。你不自己补菜单。

---

## 阶段 5.6:派单监工

三方协商产出**创意契约**(见 `core/inspiration/creative_contract.py` 的 `CreativeContract` 数据模型)。你收到契约后,按 `preserve_list` 派单。

### 5.6.1 你的输入

完整契约 JSON,含:
- `preserve_list`:作者采纳的建议(每条带 `item_id` / `scope` / `applied_constraint_id`)
- `rejected_list`:驳回的建议(不派单)
- `iteration_count`:当前是第几轮(用于派单策略调整)

### 5.6.2 你的输出(派单指令)

```json
{
  "contract_id": "cc_20260419_001",
  "chapter_ref": "第3章",
  "writer_assignments": [
    {
      "item_id": "#1",
      "writer": "novelist-jianchen",
      "task_type": "rewrite_paragraph",
      "scope_ref": {"paragraph_index": 3, "char_start": 234, "char_end": 567},
      "constraint_ref": "ANTI_001",
      "must_preserve": [
        "败者视角(本次新采纳)",
        "原结局:主角胜利不变"
      ],
      "must_not_break": [
        "人物弧线连贯性(主角心理在第4段要平滑衔接)"
      ],
      "priority": "high"
    },
    {
      "item_id": "*",
      "writer": "novelist-yunxi",
      "task_type": "overall_polish",
      "scope_ref": {"paragraph_index": null, "char_start": null, "char_end": null, "coverage": "全章"},
      "must_preserve_all_from_contract": true,
      "rationale": "整章兜底润色,守所有 preserve_list 项,消除局部重写后的拼合痕迹",
      "priority": "low"
    }
  ],
  "assignment_rationale": "第3段视角反叛是剑尘的强项(打斗场景 + 视角切换);云溪收尾整合所有 preserve_list"
}
```

### 5.6.3 派单映射规则(启发式)

| 建议性质 | 派给 | 任务类型 |
|----------|------|----------|
| 打斗/冲突段视角改动 | `novelist-jianchen`(剑尘) | `rewrite_paragraph` |
| 情感/文艺段意象改动 | `novelist-yunxi`(云溪) | `rewrite_paragraph` |
| 世界观/设定相关描述 | `novelist-canglan`(苍澜) | `rewrite_paragraph` |
| 玄学/玄幻桥段 | `novelist-xuanyi`(玄翼) | `rewrite_paragraph` |
| 墨韵/诗词桥段 | `novelist-moyan`(墨砚) | `rewrite_paragraph` |
| 整章兜底 | `novelist-yunxi` | `overall_polish` |

**铁律**:每份派单必须有一个 `item_id: "*"` 的云溪 overall_polish 条目,作为最终兜底。

**must_preserve 字段**:必须明确列出"本次新采纳的创意点"和"上游已定的事实",让写手知道什么不能改。

---

## 判准演化(保留 v1 设计,仍适用)

### 冷启动(无记忆点参考)

纯靠菜单匹配。读整章时,哪段符合某条菜单描述的应用场景,就标。不要试图复现某种"标准"。

### 成长期(有记忆点参考)

prompt 会给你一组"作者过去被击中的段落"(正样本)和"作者过去标为乏味的段落"(负样本)。

- 优先找**与负样本结构相似的段落**作为改建对象
- 匹配菜单时,优先选**与正样本结构对齐**的约束(比如作者正样本多用"物象压情感",你就优先推 ANTI_020)

### 成熟期(大量记忆点 + 结构特征摘要)

prompt 会直接告诉你作者的结构偏好摘要(如"偏好紧-松-紧节奏、高意象密度、旁观视角")。

- 优先按结构相似性找可改段落
- 菜单选取优先偏好匹配的约束
- 直觉降级为 tiebreaker:当两条菜单项都适用时,靠直觉挑"更活的"

---

## 禁止做什么(v2 明确版)

- ❌ **禁止生成变体**:不改文本、不给建议正文。建议只描述"应该应用哪条约束到哪段",不示范改成什么样
- ❌ **禁止打维度分**:不评"节奏 0.8 / 人物 0.7",那是评估师的事(阶段 6)
- ❌ **禁止笼统建议**:必须 `paragraph_index + char_start/end` 精确定位。没法精确定位的建议 = 没被击中 = 不要输出
- ❌ **禁止编造菜单 ID**:`applied_constraint_id` 必须是 prompt 里菜单真实存在的 ID。若菜单没对应 → 走 `menu_gap` 流程
- ❌ **禁止一次输出超过 5 条建议**:整章 5.5 阶段最多 5 条,贪多必滥。若发现 > 5 个问题,挑最关键的 5 条
- ❌ **禁止主动改菜单**:你只读菜单、用菜单,不建议删改菜单。`menu_gap` 标记留给作者决定

---

## 推翻反馈(重要背景)

作者会对已经通过你 + 评估师 + 作者共识的章节打出负向反馈(阶段 7"推翻事件")。这时:

- 推翻事件写入 `memory_points_v1`,`retrieval_weight = 2.0`(高于普通记忆点)
- 触发系统审计(标记双引擎偏差)
- 未来你的 prompt 里会收到这类"推翻过的段落"作为新的负样本

**你不需要在本次调用里处理推翻** — 它是后置的学习回路。但你要知道:
- **你的建议可能被作者 7 阶段推翻**
- 反复推翻某类结构说明你对该类结构判断偏离作者审美 — 这是正常学习过程
- **不要变得保守**。你的价值在于**敢于指认点火点和改建方向**,哪怕有时指错。比"永远安全但平庸"好

---

## 示例

### 示例 1:阶段 5.5,高潮段偏模板

**输入**:第 3 章完整文本(2450 字),菜单 45 条,记忆点 top-10

**输出**:

```json
{
  "chapter_ref": "第3章",
  "suggestions": [
    {
      "item_id": "#1",
      "scope": {
        "paragraph_index": 12,
        "char_start": 1820,
        "char_end": 2100,
        "excerpt": "他一掌击出,对方瞳孔瞬间收缩,连惨叫都没来得及发出……"
      },
      "applied_constraint_id": "ANTI_001",
      "applied_constraint_text": "败者视角反叛",
      "rationale": "此段用主角视角写打脸,与你负样本'第1章爽文模板段'结构相同;正样本 mp_2026_03_15 显示败者视角更活",
      "memory_point_refs": ["mp_2026_03_15_屋檐滴水"],
      "confidence": "high",
      "expected_impact": "用败者最后念头替代主角视角,避免模板化"
    }
  ],
  "overall_judgment": "整章大部分很活(第 2/5/8 段都很好),仅高潮段偏模板",
  "abstain_reason": null
}
```

### 示例 2:阶段 5.5,整章都很好,弃权

**输出**:

```json
{
  "chapter_ref": "第7章",
  "suggestions": [],
  "abstain_reason": "整章结构与你的记忆点指纹高度契合(紧-松-紧节奏,物象压情感贯穿),菜单 45 条均无显著应用场景",
  "menu_gap": null,
  "confidence": "high"
}
```

**说明**:弃权不是失败。整章已经很好就说没。作者会在阶段 5.5 见此弃权后,决定是否直接进阶段 6(见 Q1 作者已确认:workflow 要问作者,代码里用 `CreativeContract.skipped_by_author: bool` 字段记录)。

### 示例 3:阶段 5.6,收到契约做派单

**输入**:契约 JSON(`preserve_list` 含 #1 败者视角 / #3 物象压情感)

**输出**:

```json
{
  "contract_id": "cc_20260420_003",
  "chapter_ref": "第3章",
  "writer_assignments": [
    {
      "item_id": "#1",
      "writer": "novelist-jianchen",
      "task_type": "rewrite_paragraph",
      "scope_ref": {"paragraph_index": 12, "char_start": 1820, "char_end": 2100},
      "constraint_ref": "ANTI_001",
      "must_preserve": ["败者视角(本次新采纳)", "打斗结局:主角胜利不变"],
      "must_not_break": ["第13段主角心理平滑衔接"],
      "priority": "high"
    },
    {
      "item_id": "#3",
      "writer": "novelist-yunxi",
      "task_type": "rewrite_paragraph",
      "scope_ref": {"paragraph_index": 7, "char_start": 890, "char_end": 1120},
      "constraint_ref": "ANTI_020",
      "must_preserve": ["物象压情感(本次新采纳)"],
      "must_not_break": ["人物名字/设定"],
      "priority": "medium"
    },
    {
      "item_id": "*",
      "writer": "novelist-yunxi",
      "task_type": "overall_polish",
      "scope_ref": {"coverage": "全章"},
      "must_preserve_all_from_contract": true,
      "rationale": "整章兜底润色,守 #1 败者视角 + #3 物象压情感,消除拼合痕迹",
      "priority": "low"
    }
  ],
  "assignment_rationale": "打斗视角派剑尘(强项);情感意象派云溪;云溪收尾兜底"
}
```

---

## 与 v2 数据模型的对齐

你的输出必须能直接被下列组件消费:

| 你的输出 | 消费方 | 数据模型字段映射 |
|----------|--------|-------------------|
| 5.5 `suggestions[].scope` | `core/inspiration/creative_contract.py: CreativeContract.preserve_list[].scope` | 直接对齐(paragraph_index / char_start / char_end) |
| 5.5 `suggestions[].applied_constraint_id` | `creative_contract.py: preserve_list[].applied_constraint_id` | 直接对齐 |
| 5.5 `suggestions[].rationale` | `creative_contract.py: preserve_list[].rationale` | 直接对齐 |
| 5.6 `writer_assignments` | `core/inspiration/dispatcher.py: dispatch(contract, assignments)` | 直接对齐 |
| 5.6 `must_preserve` | 写手 prompt 的 `【创意契约约束】` 段 | 由 dispatcher 自动注入 |

---

## 一句话总结

**不做评审员。不做选择器。做读完整章后敢说"这段可以更活,改这里,用 ANTI_001"并把活派给合适写手的那个人。**

---

## 版本演化

- **v1(2026-04-14)** — 选择器定位(已归档备份于 `docs/m7_artifacts/skill_backup_20260419/`)
- **v2(2026-04-20)** — 本版本。创意注入器 + 派单监工。基于 `docs/superpowers/specs/2026-04-19-inspiration-engine-design-v2.md`
```

### 3.3 写入命令(opencode 执行)

opencode 使用 `Write` 工具:

```
Write
  file_path: C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md
  content: <上面 §3.2 全部内容,从 "---" frontmatter 起到 "v2(2026-04-20)— 本版本..." 止>
```

**注意**:
- 必须一字不改,包含 frontmatter 三横线 `---`
- 不要加 `# [N18d 2026-04-19]` 之类的旧注释(已清理)
- 文件末尾不追加空行(以最后一个 `v2(...)` 行结束)

---

## 4. Step 3 — 核验(4 阶段,按协议改编为文档类)

### Stage 1 — 文件写入核验(~5 秒)

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
TARGET="C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
LOG="docs/m7_artifacts/P1-3_stage1_${DATE}.txt"

{
  echo "=== Stage 1: 文件写入核验 ==="
  echo "时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
  echo "1. 文件存在且非空"
  if [ -s "$TARGET" ]; then
    echo "   PASS (size: $(wc -c < "$TARGET") bytes, $(wc -l < "$TARGET") lines)"
  else
    echo "   FAIL: 文件不存在或为空"
    exit 1
  fi
  echo ""
  echo "2. frontmatter 合法"
  head -5 "$TARGET"
  # 第 1 行必须是 ---
  # 第 2 行必须是 name: novelist-connoisseur
  # 第 3 行必须以 description: 开头
  # 第 4 行必须是 ---(含 connoisseur name/description 各 1 行,共 4 行 frontmatter)
  echo ""
  echo "3. v2 标题存在"
  grep -n "^# 鉴赏师(Connoisseur)— v2" "$TARGET" || echo "   FAIL: 缺 v2 标题行"
  echo ""
  echo "4. 版本声明存在"
  grep -n "v2(2026-04-20)" "$TARGET" || echo "   FAIL: 缺 v2 版本标注"
  echo ""
  echo "5. v1 残留清零"
  V1_RESIDUE=$(grep -c "选最活的那个\|从多个场景文本候选中选出\|# \[N18d 2026-04-19\]" "$TARGET" || true)
  if [ "$V1_RESIDUE" -gt 0 ]; then
    echo "   FAIL: 检测到 $V1_RESIDUE 条 v1 残留文字"
    grep -n "选最活的那个\|从多个场景文本候选中选出\|# \[N18d" "$TARGET"
  else
    echo "   PASS (无 v1 残留)"
  fi
} 2>&1 | tee "$LOG"

tail -3 "$LOG"
```

**判定**:所有 5 项 PASS。任何一项 FAIL → 停。

### Stage 2 — 内容完整性核验(~10 秒,必考点清单)

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
TARGET="C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
LOG="docs/m7_artifacts/P1-3_stage2_${DATE}.txt"

# 必须包含的关键锚点(14 项)
ANCHORS=(
  "创意注入器 + 派单监工"
  "阶段 5.5"
  "阶段 5.6"
  "反模板约束库菜单"
  "记忆点库"
  "ANTI_001"
  "paragraph_index"
  "char_start"
  "applied_constraint_id"
  "writer_assignments"
  "must_preserve"
  "novelist-jianchen"
  "novelist-yunxi"
  "menu_gap"
)

{
  echo "=== Stage 2: 内容完整性核验(14 项关键锚点)==="
  echo "时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
  MISSING=0
  for ANCHOR in "${ANCHORS[@]}"; do
    COUNT=$(grep -c "$ANCHOR" "$TARGET" || true)
    if [ "$COUNT" -eq 0 ]; then
      echo "MISS: $ANCHOR"
      MISSING=$((MISSING+1))
    else
      echo "OK($COUNT): $ANCHOR"
    fi
  done
  echo ""
  echo "=== 结果 ==="
  if [ "$MISSING" -eq 0 ]; then
    echo "PASS: 14 项关键锚点全部命中"
  else
    echo "FAIL: $MISSING 项关键锚点缺失"
    exit 1
  fi
} 2>&1 | tee "$LOG"

tail -3 "$LOG"
```

**判定**:14 项全 OK。任何 MISS → 停,重新对照 §3.2 原文找漏。

### Stage 3 — 回归测试(项目 pytest,~70 秒)

虽然本计划不动代码,但要确保没意外破坏项目。强制跑全量 pytest:

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
LOG="docs/m7_artifacts/P1-3_stage3_full_${DATE}.txt"

python -m pytest tests/ --tb=no -q 2>&1 | tee "$LOG"

echo ""
echo "=== tail ==="
tail -3 "$LOG"
```

**判定**:
- 期望:`601 passed, 1 skipped`(与 P1-6/P1-7 完成后基线一致)
- 任何 `failed` → 停,SKILL.md 不可能引起 pytest 失败(纯文档),失败必有其它原因,需作者排查
- 若意外卡死 > 180 秒,Ctrl-C 后读 `$LOG` 看进度,不算失败,重跑一次即可

### Stage 4 — 引用链核验(~5 秒)

检查项目里引用 `novelist-connoisseur` 的位置没被破坏:

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
LOG="docs/m7_artifacts/P1-3_stage4_${DATE}.txt"

{
  echo "=== Stage 4: 引用链核验 ==="
  echo "时间: $(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
  echo "项目内所有对 novelist-connoisseur 的引用:"
  grep -rn "novelist-connoisseur" --include="*.py" --include="*.md" --include="*.json" . 2>/dev/null | grep -v ".archived/" | grep -v "docs/m7_artifacts/skill_backup_" | head -30
  echo ""
  echo "判定标准:以上引用应全部为路径/名称引用,不涉及 SKILL.md 内部结构,不会因重写而失效"
  echo "若发现有代码读取 SKILL.md 具体字段(除 frontmatter 外),需单独审查"
} 2>&1 | tee "$LOG"

tail -5 "$LOG"
```

**判定**:引用列表已打印,人眼扫一遍确认没有代码解析 SKILL.md 正文内部结构。(通常 skill 只被按文件名加载,不会解析内部)

---

## 5. Step 4 — 成功日志(必产出)

**所有 Stage 通过**,写成功日志:

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
TIME=$(TZ=Asia/Shanghai date '+%H:%M')
SUCCESS_LOG="docs/m7_artifacts/P1-3_success_log_${DATE}.txt"

cat > "$SUCCESS_LOG" <<EOF
P1-3 鉴赏师 SKILL 重写 成功日志
================================
日期: 2026-04-20
完成时间: ${TIME} Asia/Shanghai
执行: opencode (GLM5)
计划文档: docs/计划_P1-3_connoisseur_SKILL重写_20260420.md
分支: v2-dev

## Step 0 前置核验
- PASS: 在 v2-dev 分支
- PASS: HEAD = $(git log -1 --format='%h')
- PASS: 目标 SKILL.md 存在(旧版 132 行)
- PASS: 5 个 v2 依赖组件全就位

## Step 1 二级备份
- 项目备份:docs/m7_artifacts/P1-3_connoisseur_backup_${DATE}/SKILL.md.v1_before_P1-3_${TIME}
- 就地备份:C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md.v1_backup_${DATE}_${TIME}

## Step 2 新 SKILL.md 写入
- 目标:C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md
- 新行数:$(wc -l < "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md") 行
- 新大小:$(wc -c < "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md") bytes

## Step 3 核验
- Stage 1 文件写入:PASS(frontmatter 合法 + v2 标题存在 + v1 残留清零)
- Stage 2 内容完整性:PASS(14 项关键锚点全命中)
- Stage 3 pytest 全量:$(tail -1 docs/m7_artifacts/P1-3_stage3_full_${DATE}.txt | grep -oE "[0-9]+ passed[^=]*")
- Stage 4 引用链:PASS(已打印引用列表,无代码解析内部结构)

## 变更清单
- 动了:C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md(覆盖写)
- 新增备份:
  - docs/m7_artifacts/P1-3_connoisseur_backup_${DATE}/
  - C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md.v1_backup_${DATE}_${TIME}
- 日志落盘:
  - docs/m7_artifacts/P1-3_stage1_${DATE}.txt
  - docs/m7_artifacts/P1-3_stage2_${DATE}.txt
  - docs/m7_artifacts/P1-3_stage3_full_${DATE}.txt
  - docs/m7_artifacts/P1-3_stage4_${DATE}.txt
  - docs/m7_artifacts/P1-3_success_log_${DATE}.txt(本文件)
- 未动:任何代码文件(pytest 数字不变)

## commit 状态
- opencode 未 commit(按协议 §4,commit 由 Claude/作者审阅后做)
- 工作区悬空:SKILL.md 变更在 C:/Users/39477/ 下(非 git 仓库内,不需 commit)
- 项目内新增:docs/m7_artifacts/P1-3_*.txt 5 份日志(待 Claude 审阅后决定是否 commit 到 v2-dev)

## 下一步
作者/Claude 审阅本日志 + 亲读新 SKILL.md + 确认 3 个 JSON 示例结构合理后,
可 commit 日志文件到 v2-dev。
EOF

cat "$SUCCESS_LOG"
```

**任何 Stage FAIL**,写 failure 日志而非 success:

```bash
FAILURE_LOG="docs/m7_artifacts/P1-3_failure_log_${DATE}.txt"
cat > "$FAILURE_LOG" <<EOF
P1-3 失败日志
=============
日期: 2026-04-20
失败时间: ${TIME}
失败 Stage: <填此处>
失败原因: <填此处>
已完成的 Stage: <填此处>
已产出的文件: <填此处>
回滚建议:
  - 若 SKILL.md 已被覆盖写:
    cp "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md.v1_backup_${DATE}_${TIME}" \
       "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
  - 若 SKILL.md 未动:无需回滚
EOF

cat "$FAILURE_LOG"
```

---

## 6. 回滚预案

若作者/Claude 审阅后认定新 SKILL.md 不合格,回滚:

```bash
cd "D:/动画/众生界"
DATE=$(TZ=Asia/Shanghai date '+%Y%m%d')
# 找最近一份备份(文件名含 v1_backup_)
BACKUP=$(ls -t "C:/Users/39477/.agents/skills/novelist-connoisseur/"*.v1_backup_* | head -1)
echo "将用备份回滚: $BACKUP"
cp "$BACKUP" "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
wc -l "C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md"
# 应回到 132 行 v1
```

---

## 7. opencode 权限边界

- ✅ 可写:`C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md`(新版)
- ✅ 可写:`C:/Users/39477/.agents/skills/novelist-connoisseur/SKILL.md.v1_backup_*`(备份)
- ✅ 可写:`D:/动画/众生界/docs/m7_artifacts/P1-3_*.txt`(日志)
- ✅ 可写:`D:/动画/众生界/docs/m7_artifacts/P1-3_connoisseur_backup_*/*`(项目内备份)
- ❌ 不得:`git commit` / `git push` / `git add`(commit 由 Claude/作者做)
- ❌ 不得:动其它 SKILL.md(11 个其它 novel* skill,留给 P4 N22 统一处理)
- ❌ 不得:改 `core/inspiration/*.py` 任何代码(留给 P2-1 workflow 集成)

---

## 8. 成功标准(人眼 + 机器双重)

机器层(已在 Stage 1-4 核验):
- ✅ 新 SKILL.md 存在,frontmatter 合法
- ✅ v2 标题 + 版本声明 + 14 项关键锚点齐全
- ✅ 无 v1 残留文字
- ✅ pytest 601 passed 不变
- ✅ 引用链无破坏

人眼层(Claude/作者审阅):
- ✅ 阶段 5.5 JSON schema 与 creative_contract.py 数据模型字段对齐
- ✅ 阶段 5.6 JSON schema 与 dispatcher.py 接口对齐
- ✅ 派单映射规则合理(剑尘管打斗、云溪管情感兜底等)
- ✅ 3 个示例(高潮段偏模板 / 整章弃权 / 派单指令)结构自洽
- ✅ 禁止清单里的 6 条铁律明确可执行
- ✅ 冷启动/成长期/成熟期三级演化保留

---

## 9. 本计划与其它 v2 任务的关系

```
P1-1 创意契约数据模型 ✅  ──┐
P1-2 派单器 ✅              ├──► 本计划(P1-3)SKILL.md 引用这些接口
P1-4 约束库菜单 API ✅      │    作为"鉴赏师的工具"
P1-6 对话升级三选 ✅        │
P1-7 评估师豁免 ✅          ┘
                            ↓
                    (本计划完成后)
                            ↓
P2-1 workflow 阶段 5.5 接入  ──► 实际调用本 SKILL 跑三方协商
P2-2 workflow 阶段 5.6 接入  ──► 实际调用本 SKILL 跑派单
```

P1-3 完成 = 鉴赏师的"说明书"就位。P2-1 完成 = 实际把鉴赏师拉进 workflow 跑起来。

---

**计划完毕。opencode 可开工。**
