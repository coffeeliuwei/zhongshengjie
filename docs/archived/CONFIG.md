# 众生界 - 项目配置

## 基本信息

| 项目 | 内容 |
|------|------|
| 小说名称 | 众生界 |
| 类型 | 玄幻/科幻融合 |
| 预计篇幅 | 超长篇 |
| 当前状态 | 第一章创作中 |

---

## 文风配置

| 配置项 | 值 |
|--------|-----|
| 文风基调 | 平实厚重 |
| 禁止风格 | 古龙式极简风格 |
| 字数规则 | 上不封顶，情节优先 |

---

## 作家偏好

| 场景类型 | 作家 | 技能名称 |
|----------|------|----------|
| 世界观/势力 | 苍澜 | novelist-canglan |
| 人物/情感 | 墨言 | novelist-moyan |
| 战斗场景 | 剑尘 | novelist-jianchen |
| 氛围/润色 | 云溪 | novelist-yunxi |
| 剧情/伏笔 | 玄一 | novelist-xuanyi |

---

## 评估阈值

| 维度 | 阈值 |
|------|------|
| 世界自洽 | ≥7 |
| 人物立体 | ≥6 |
| 情感真实 | ≥6 |
| 战斗逻辑 | ≥6 |
| 文风克制 | ≥6 |
| 剧情张力 | ≥6 |

---

## 设定文件映射

| 设定类型 | 文件路径 |
|----------|----------|
| 总大纲 | `总大纲.md` |
| 人物谱 | `设定/人物谱.md` |
| 势力设定 | `设定/十大势力.md` |
| 时间线 | `设定/时间线.md` |

---

## 核心主题

**「我是谁」身份认同**

### 三层追问

| 层次 | 问题 |
|------|------|
| 第一层 | 我身边的人还是原来的人吗？ |
| 第二层 | 我自己有没有被入侵过？ |
| 第三层 | 如果我被入侵了，原来的"我"还存在吗？ |

---

## 迭代规则

```
迭代阶梯：3 → 6 → 9 → 12 → ...
最小3次，不满意则加3次
```

---

## 目录配置

| 目录类型 | 路径 | 说明 |
|----------|------|------|
| 设定目录 | `设定/` | 世界观设定文件 |
| 技法目录 | `创作技法/` | 11维度技法体系 |
| 章节目录 | `章节大纲/` | 章节规划文件 |
| 正文目录 | `正文/` | 小说正文 |
| 向量库目录 | `.vectorstore/` | 向量数据库和工作流 |
| 案例库目录 | `.case-library/` | 案例库系统 |
| 模块目录 | `modules/` | 功能模块（重构后） |
| 日志目录 | `logs/` | 运行日志 |
| 缓存目录 | `.cache/` | 临时缓存 |
| 存档目录 | `存档/` | 历史存档 |

### 自定义资源目录

可配置外部小说资源目录，用于案例提取：

```json
{
  "custom_resources": {
    "玄幻奇幻": "E:\\小说资源\\玄幻奇幻",
    "武侠仙侠": "E:\\小说资源\\武侠仙侠",
    "现代都市": "E:\\小说资源\\现代都市"
  }
}
```

**配置方式**：
1. 编辑 `system_config.json` 文件
2. 或使用CLI命令：`python -m core config --add-resource 玄幻奇幻 "E:\小说资源\玄幻奇幻"`

---

## 数据库配置

| 配置项 | 值 |
|--------|-----|
| 向量数据库 | Qdrant |
| 主机地址 | localhost |
| 端口 | 6333 |
| 连接URL | http://localhost:6333 |

### 集合配置

| 集合名称 | 用途 | 数量 |
|----------|------|------|
| `novel_settings` | 小说设定库 | 143条 |
| `writing_techniques` | 创作技法库 | 1,122条 |
| `case_library` | 案例库 | 256,083条 |
| `creation_context` | 作家上下文存储 | 新增 |

---

## 模块配置

### 入库模块 (knowledge_base)

| 配置项 | 值 |
|--------|-----|
| 启用状态 | ✅ 已启用 |
| 自动同步 | ❌ 手动触发 |
| 同步命令 | `python -m core kb --sync all` |

### 验证模块 (validation)

| 配置项 | 值 |
|--------|-----|
| 启用状态 | ✅ 已启用 |
| 验证阈值 | 见评估阈值表 |
| 验证命令 | `python -m core validate --all` |

### 创作模块 (creation)

| 配置项 | 值 |
|--------|-----|
| 启用状态 | ✅ 已启用 |
| 最大迭代次数 | 3次 |
| 并行执行 | ✅ 支持 |
| 最大并行作家数 | 3个 |
| 作家超时时间 | 300秒/个 |

### 可视化模块 (visualization)

| 配置项 | 值 |
|--------|-----|
| 启用状态 | ✅ 已启用 |
| 知识图谱 | ✅ 已实现 |
| 统计可视化 | ⚙️ 开发中 |

---

## 作家工作流配置

### 场景-作家映射文件

路径：`.vectorstore/scene_writer_mapping.json`

### 作家技能路径

路径：`C:\Users\39477\.agents\skills\`

### 作家偏好映射

| 场景类型 | 主责作家 | 技能名称 |
|----------|----------|----------|
| 世界观/势力 | 苍澜 | `novelist-canglan` |
| 剧情/伏笔 | 玄一 | `novelist-xuanyi` |
| 人物/情感 | 墨言 | `novelist-moyan` |
| 战斗场景 | 剑尘 | `novelist-jianchen` |
| 氛围/润色 | 云溪 | `novelist-yunxi` |

### 工作流设计原则

基于 **Anthropic Harness** 设计：

| 原则 | 说明 |
|------|------|
| Generator/Evaluator分离 | 创作家不自我评估 |
| 任务分解 | 场景分解为Phase执行 |
| 迭代反馈 | 最多3次迭代优化 |
| 硬性阈值 | 技法评分达标即通过 |

---

## 移植配置

### 移植模式

推荐使用 **完整移植框架**：保留目录结构和工具，清空数据。

### 移植工具

| 工具 | 文件 | 功能 |
|------|------|------|
| 环境初始化 | `modules/migration/init_environment.py` | 初始化新环境 |
| 模板导出 | `modules/migration/export_template.py` | 导出项目模板 |
| 一键脚本 | `migrate.sh` / `migrate.bat` | 一键移植 |

### 移植步骤

```bash
# 1. 初始化新环境
python -m core migrate --init-environment

# 2. 配置资源目录
python -m core config --add-resource 玄幻奇幻 "路径"

# 3. 提取案例（可选）
python -m core kb --sync case

# 4. 开始创作
python -m core create --workflow
```

---

## 命令速查

### CLI 命令（新）

```bash
# 配置管理
python -m core config --show          # 显示配置
python -m core config --init          # 初始化配置

# 入库管理
python -m core kb --stats             # 数据库统计
python -m core kb --sync all          # 同步所有数据
python -m core kb --search-novel "关键词"

# 验证管理
python -m core validate --all         # 运行所有验证
python -m core validate --chapter "第一章-天裂"

# 创作管理
python -m core create --workflow      # 执行完整工作流
python -m core create --scene "战斗场景"

# 移植管理
python -m core migrate --export-template
python -m core migrate --init-environment
```

### 原有命令（保留）

```bash
cd .vectorstore

# 工作流入口
python workflow.py --stats
python workflow.py --search-novel "关键词"

# 验证入口
python verify_all.py
python checklist_scorer.py
```

---

## 配置文件说明

### CONFIG.md（本文件）

- 项目基本信息
- 文风配置
- 作家偏好
- 评估阈值
- 核心主题

### system_config.json（自动生成）

- 数据库详细配置
- 目录完整配置
- 模块功能配置
- 作家工作流参数
- 自定义资源配置

**生成方式**：
- 运行 `python -m core config --init` 自动生成
- 或手动创建 JSON 配置文件

---

*配置版本: 2.0*
*更新时间: 2026-04-02*
*重构支持: CLI统一接口 + 模块化架构*