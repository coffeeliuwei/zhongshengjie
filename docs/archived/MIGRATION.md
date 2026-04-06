# 众生界项目移植指南

> 本文档提供完整的项目移植流程，支持一键移植和手动移植

---

## 一、移植概述

### 1.1 移植模式

推荐使用 **完整移植框架**：
- ✅ 保留项目目录结构
- ✅ 保留所有工具脚本
- ✅ 保留配置模板
- ❌ 清空小说正文数据
- ❌ 清空设定数据
- ❌ 清空案例库数据

### 1.2 移植步骤概览

```
1. 一键移植（推荐）          2. 手动移植
   ├── 导出模板                ├── 复制核心文件
   ├── 初始化环境              ├── 安装依赖
   ├── 配置资源                ├── 初始化环境
   └── 开始创作                └── 配置资源
```

---

## 二、一键移植（推荐）

### 2.1 Windows 环境

```bash
# 1. 运行移植脚本
migrate.bat D:\new-project

# 2. 进入新项目
cd D:\new-project

# 3. 编辑配置
notepad CONFIG.md
notepad system_config.json

# 4. 启动向量数据库
docker run -p 6333:6333 qdrant/qdrant

# 5. 同步设定
python -m core kb --sync novel

# 6. 开始创作
python -m core create --workflow
```

### 2.2 Linux/Mac 环境

```bash
# 1. 运行移植脚本
chmod +x migrate.sh
./migrate.sh /path/to/new-project

# 2. 进入新项目
cd /path/to/new-project

# 3. 编辑配置
vim CONFIG.md
vim system_config.json

# 4. 启动向量数据库
docker run -p 6333:6333 qdrant/qdrant

# 5. 同步设定
python -m core kb --sync novel

# 6. 开始创作
python -m core create --workflow
```

---

## 三、手动移植

### 3.1 复制核心文件

复制以下目录/文件到新项目：

```
众生界/
├── core/                      ✅ 核心模块（必须）
├── modules/                   ✅ 功能模块（必须）
├── .vectorstore/
│   ├── workflow.py            ✅ 工作流入口（必须）
│   ├── verify_all.py          ✅ 验证入口（必须）
│   ├── checklist_scorer.py    ✅ 评分工具（必须）
│   ├── verification_history.py ✅ 历史管理（必须）
│   └── scene_writer_mapping.json ✅ 场景-作家映射（必须）
├── .case-library/scripts/     ✅ 案例提取工具（必须）
├── CONFIG.md                  ✅ 项目配置（必须）
├── requirements.txt           ✅ 依赖列表（必须）
└── PROJECT_GUIDE.md           ✅ 项目指南（推荐）
```

### 3.2 安装依赖

```bash
pip install -r requirements.txt
```

核心依赖：
- `qdrant-client>=1.3.0` - 向量数据库
- `sentence-transformers>=2.2.0` - 向量嵌入
- `ebooklib>=0.18` - epub处理
- `mobi>=0.3.3` - mobi处理
- `click>=8.0.0` - CLI工具
- `rich>=13.0.0` - 终端美化

### 3.3 初始化环境

```bash
# 创建目录结构
python -m core config --init

# 或使用移植模块
python -m modules.migration.init_environment
```

系统将自动创建：
- 所有必需目录
- 配置文件模板
- 示例设定文件

### 3.4 配置资源

#### 方式A：编辑 system_config.json

```json
{
  "directories": {
    "custom_resources": {
      "玄幻奇幻": "E:\\小说资源\\玄幻奇幻",
      "武侠仙侠": "E:\\小说资源\\武侠仙侠",
      "现代都市": "E:\\小说资源\\现代都市"
    }
  },
  "writers": {
    "skills_base_path": "C:\\Users\\你的用户名\\.agents\\skills"
  }
}
```

#### 方式B：使用CLI命令

```bash
python -m core config --add-resource 玄幻奇幻 "E:\小说资源\玄幻奇幻"
python -m core config --add-resource 武侠仙侠 "E:\小说资源\武侠仙侠"
```

### 3.5 初始化向量数据库

```bash
# 启动Qdrant Docker
docker run -p 6333:6333 qdrant/qdrant

# 初始化集合
python -m core kb --init
```

---

## 四、配置说明

### 4.1 CONFIG.md 配置

编辑 `CONFIG.md` 配置小说基本信息：

```markdown
## 基本信息

| 项目 | 内容 |
|------|------|
| 小说名称 | 你的小说名称 |
| 类型 | 小说类型 |
| 预计篇幅 | 预计字数 |
| 当前状态 | 规划中 |
```

### 4.2 system_config.json 配置

#### 数据库配置

```json
{
  "database": {
    "host": "localhost",
    "port": 6333
  }
}
```

#### 目录配置

```json
{
  "directories": {
    "settings_dir": "设定",
    "techniques_dir": "创作技法",
    "chapters_dir": "章节大纲",
    "content_dir": "正文"
  }
}
```

#### 模块配置

```json
{
  "modules": {
    "knowledge_base_enabled": true,
    "validation_enabled": true,
    "creation_enabled": true,
    "visualization_enabled": true
  }
}
```

#### 作家配置

```json
{
  "writers": {
    "skills_base_path": "C:\\Users\\你的用户名\\.agents\\skills",
    "writer_preferences": {
      "世界观": "novelist-canglan",
      "剧情": "novelist-xuanyi",
      "人物": "novelist-moyan",
      "战斗": "novelist-jianchen",
      "氛围": "novelist-yunxi"
    }
  }
}
```

---

## 五、开始使用

### 5.1 添加设定

编辑以下文件添加你的小说设定：

```
设定/
├── 人物谱.md          # 人物设定
├── 十大势力.md        # 势力设定
├── 力量体系.md        # 力量体系
├── 时间线.md          # 时间线
└── 总大纲.md          # 总大纲
```

### 5.2 同步设定到向量库

```bash
python -m core kb --sync novel
```

系统将自动：
- 解析设定文件
- 提取实体和关系
- 存入向量数据库

### 5.3 提取案例（可选）

如果有小说资源：

```bash
# 同步案例到向量库
python -m core kb --sync case
```

### 5.4 开始创作

```bash
# 执行完整创作流程
python -m core create --workflow

# 或创作指定场景
python -m core create --scene "战斗场景"
```

---

## 六、常见问题

### Q1: 没有小说资源能运行吗？

**A**: 可以。系统初始化时会创建示例数据用于测试。作家工作流依赖设定和技法库，不依赖案例库。

### Q2: 如何修改作家技能路径？

**A**: 编辑 `system_config.json` 中的 `writers.skills_base_path` 字段，指向你的 `.agents/skills` 目录。

### Q3: 如何添加新的小说资源？

**A**: 
```bash
python -m core config --add-resource 资源名称 "资源路径"
```

### Q4: 向量数据库连接失败？

**A**: 确保Qdrant Docker正在运行：
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Q5: 如何重新提取所有案例？

**A**: 
```bash
# 删除案例库数据
rm -rf .case-library/cases/
rm .case-library/unified_index.json

# 重新提取
python -m core kb --sync case
```

### Q6: 支持哪些小说格式？

**A**: 
- `.txt` - 直接处理
- `.epub` - 需先转换
- `.mobi` - 需先转换

转换命令：
```bash
python .case-library/scripts/convert_format.py
```

---

## 七、移植检查清单

移植完成后，请检查以下项目：

- [ ] Python 3.8+ 已安装
- [ ] 依赖库已安装（`pip install -r requirements.txt`）
- [ ] Qdrant Docker 已启动
- [ ] `CONFIG.md` 已配置小说信息
- [ ] `system_config.json` 已配置资源目录
- [ ] `system_config.json` 已配置作家技能路径
- [ ] 设定文件已创建（人物谱、势力等）
- [ ] 设定已同步到向量库（`python -m core kb --sync novel`）
- [ ] 工作流测试通过（`python -m core create --workflow`）

---

## 八、技术支持

### 8.1 文档资源

| 文档 | 路径 | 用途 |
|------|------|------|
| 项目指南 | `PROJECT_GUIDE.md` | 项目总纲 |
| API文档 | `API.md` | 模块和CLI接口 |
| 移植指南 | `MIGRATION.md` | 本文档 |
| 配置文档 | `CONFIG.md` | 配置说明 |

### 8.2 命令速查

```bash
# 配置管理
python -m core config --show
python -m core config --init

# 知识入库
python -m core kb --stats
python -m core kb --sync all

# 验证管理
python -m core validate --all

# 创作管理
python -m core create --workflow

# 移植管理
python -m core migrate --export-template --target <目录>
```

---

*移植版本: 2.0*
*更新时间: 2026-04-02*