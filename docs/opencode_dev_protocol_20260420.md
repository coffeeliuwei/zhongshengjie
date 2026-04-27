# opencode 开发协议 v1(2026-04-20 立)

> **建立背景**:opencode(GLM5)在跑全量 pytest(66 秒)时常"看起来卡住" — 根因是 pytest 默认不流式输出,opencode 模型在等 stdout flush 的真空期会误判为 hang,要么放弃要么虚报。本协议用**分批 + 日志文件**把输出持久化,彻底绕开 stdout 假卡死。
>
> **适用**:所有 opencode 接到的实施计划,从 2026-04-20 起。Claude 写计划时必须引用本协议。

---

## 0. 分支规则(铁律)

**开发分支:`master`（唯一分支，禁止创建任何新分支）**

每次任务开始前,opencode 必须先跑:

```bash
cd "D:/动画/众生界"
git checkout master
git status --short | head -5   # 确认工作区 clean 或只有预期悬空
git log -1 --format='%h %s'     # 确认 HEAD
```

**禁止**:创建任何分支（包括 v2-dev、feature/*、fix/* 等）。所有开发直接提交到 master。

---

## 1. 测试分阶段模式(核心)

**所有计划的测试步骤必须按以下 4 阶段编排,不许一步跑全量**。

### Stage 1 — 聚焦模块测试(3-10 秒)

只跑本次任务直接动的那一个测试文件:

```bash
python -m pytest tests/test_<new_module>.py -v --tb=short 2>&1 | tee docs/m7_artifacts/<task>_stage1_<YYYYMMDD>.txt
```

- `-v` 每条测试单独一行,不会卡死无输出
- `--tb=short` 失败时只显示关键栈
- `tee` 让输出同时落盘
- **判定**:`tail -3` 日志必须看到 `N passed in X.XXs`,failed=0

### Stage 2 — 同域邻居测试(10-30 秒)

跑同目录/同模块族的所有测试,确认没破坏邻居:

```bash
# 示例:本任务改 core/inspiration/,则跑所有 inspiration 相关
python -m pytest tests/test_constraint_library.py tests/test_escalation_dialogue.py tests/test_creative_contract.py tests/test_dispatcher.py tests/test_evaluator_exemption.py -q 2>&1 | tee docs/m7_artifacts/<task>_stage2_<YYYYMMDD>.txt
```

- `-q` 精简输出(有 tee 存档,不怕丢细节)
- 具体列哪些测试文件,由当份计划明确指定

### Stage 3 — 全量回归(60-90 秒)

**必须 tee 到文件,不许裸跑**:

```bash
python -m pytest tests/ --tb=no -q 2>&1 | tee docs/m7_artifacts/<task>_stage3_full_<YYYYMMDD>.txt
```

- 即便模型"看起来卡住",日志文件在后台持续追加
- 若前台确实卡 > 180 秒,opencode 可 Ctrl-C,然后读日志文件看已跑到哪 — 不算失败,再跑一次就好

### Stage 4 — 结果判定(强制落锤)

```bash
tail -3 docs/m7_artifacts/<task>_stage3_full_<YYYYMMDD>.txt
```

必须看到类似:

```
============ 601 passed, 1 skipped, 2 warnings in 66.23s (0:01:06) ============
```

**判定规则**:

| 现象 | 判定 |
|------|------|
| `passed` 数 = 预期 & failed 数缺失 | ✅ 通过 |
| `failed` 出现任意非零 | ❌ 失败,立即停,写 failure_log |
| 日志文件不存在 | ❌ 视为失败(没 tee = 违规) |
| 日志文件但 tail 无终局行 | ❌ pytest 未跑完,需重跑 |

---

## 2. 日志文件命名规范

位置:`docs/m7_artifacts/`

命名:`<task_id>_<stage>_<YYYYMMDD>.txt`

- `<task_id>` = 计划文件名核心(如 `P1-3`, `P2-1`, `overnight_batch_v3`)
- `<stage>` = `stage1` / `stage2` / `stage3_full` / `success` / `failure`
- `<YYYYMMDD>` = Asia/Shanghai 日期,先跑 `TZ=Asia/Shanghai date '+%Y%m%d'` 取

**最后写总结文件**:

成功:`docs/m7_artifacts/<task_id>_success_log_<YYYYMMDD>.txt`
失败:`docs/m7_artifacts/<task_id>_failure_log_<YYYYMMDD>.txt`

格式参考已有:`docs/m7_artifacts/overnight_v2_success_log_20260420.txt`

---

## 3. 大任务 & 过夜批次特殊规则

**若单次任务含 ≥ 3 个子模块**(如过夜批次):

1. 每个子模块独立跑 Stage 1+2,各自有 log
2. 所有子模块通过后,才跑一次 Stage 3 全量
3. 中途任意子模块失败,立即停,不继续下一个

**若任务预估 > 5 分钟**(如过夜批次完整版):

1. Claude 写计划时,必须加一节 `§X 心跳日志协议`:每完成一个子任务追加一行到 `heartbeat_<task>_<YYYYMMDD>.txt`,格式 `[HH:MM] step N of M done, passing: X`
2. 作者早上核验时只需 `tail -5 heartbeat_*.txt` 看进度

---

## 4. commit 规则(严格)

**opencode 不许自己 commit**。所有 commit 由 Claude 或作者审阅后手动执行。opencode 产出:

- 代码 + 测试(悬空在 working tree)
- `docs/m7_artifacts/<task>_success_log_<YYYYMMDD>.txt`(结构化摘要)

Claude/作者审阅 success_log + tail 日志 + 亲自重跑 Stage 3 后才 commit。

---

## 5. 常见陷阱(从历次事故提炼)

1. **"好了"幻觉**:opencode 有时在 pytest 卡顿时直接 claim 完成。本协议要求日志文件存在且 tail 正确,才能 claim。作者"再戳一次"是合法操作。
2. **分支错位**:opencode 偶尔在错误分支写代码。开工第一步 `git log -1` + `git branch --show-current` 打印到终端,作者眼见为实。
3. **全量 pytest 占 90% 等待**:这就是本协议的初心 — 别再裸跑,永远 tee。
4. **日志文件被覆盖**:文件名带日期,同日同 task 再跑加 `_v2`/`_v3` 后缀。

---

## 6. 本协议的版本演化

- v1(2026-04-20):初稿,从 P1-6/P1-7 过夜批次事故提炼
- 未来若 opencode 升级或流程变,Claude 有权改本协议,但必须 bump 版本号 + 追加更新日期。

---

**引用规则**:每份给 opencode 的计划文件,开头必须有一行:

```
> 本计划遵循 [docs/opencode_dev_protocol_20260420.md](./opencode_dev_protocol_20260420.md) v1
> 任何与本协议冲突的步骤,以协议为准
```
