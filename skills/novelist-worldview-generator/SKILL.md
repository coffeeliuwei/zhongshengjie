---
name: novelist-worldview-generator
description: "世界观生成器 - 从小说大纲自动提取并生成世界观配置。支持多用户、大纲同步、配置更新。"
---

# 世界观生成器

## 身份

世界观生成器，从小说大纲自动提取并生成世界观配置的专家工具。

**核心功能**：
- 从大纲提取力量体系、势力、角色、时代等元素
- 自动生成 `.vectorstore/core/world_configs/*.json` 配置
- 支持大纲改动时自动同步世界观配置
- 与统一API层无缝集成

---

## 一、配置入口

### config.json 配置

```json
{
  "worldview": {
    "current_world": "众生界",
    "outline_path": "总大纲.md",
    "auto_sync": true,
    "_说明": "current_world: 当前世界观名称；outline_path: 大纲文件路径；auto_sync: 大纲改动时是否自动同步"
  }
}
```

---

## 二、命令行工具

### 生成世界观配置

```bash
# 从大纲生成世界观配置
python .vectorstore/core/worldview_generator.py --outline "总大纲.md" --name "众生界"

# 列出已有世界观
python .vectorstore/core/worldview_generator.py --list

# 生成AI提示词（让AI帮助完善）
python .vectorstore/core/worldview_generator.py --outline "总大纲.md" --ai-prompt
```

### 同步世界观

```bash
# 从大纲同步更新世界观配置
python .vectorstore/core/worldview_sync.py --sync

# 验证世界观配置
python .vectorstore/core/worldview_sync.py --validate
```

---

## 三、大纲元素提取规则

### 3.1 力量体系提取

**识别关键词**：
- 修仙、魔法、神术、科技、兽力、异能、AI力
- 境界、等级、层次、阶段
- 修炼、突破、进阶

**提取内容**：
```json
{
  "力量体系名称": {
    "source": "力量来源（天地灵气/魔力源泉/神明赐予等）",
    "cultivation": "修炼方式",
    "combat_style": "战斗风格",
    "costs": ["代价1", "代价2"],
    "realms": ["境界1", "境界2", "..."],
    "subtypes": {
      "子类型": {
        "abilities": ["能力1", "能力2"],
        "cost": "代价描述"
      }
    }
  }
}
```

### 3.2 势力提取

**识别关键词**：
- 宗门、家族、朝廷、商会、教派
- 势力、组织、阵营
- 东/西/南/北/中

**提取内容**：
```json
{
  "势力名称": {
    "structure": "组织结构（宗门体系/学院体系等）",
    "political": ["政治层级"],
    "economy": ["经济来源"],
    "culture": ["文化特征"],
    "architecture": "建筑风格",
    "style_features": ["风格特点"]
  }
}
```

### 3.3 角色提取

**识别关键词**：
- 主角、配角、反派
- 角色、人物
- 【角色名】格式

**提取内容**：
```json
{
  "角色名": {
    "faction": "所属势力",
    "power": "力量体系",
    "subtype": "子类型",
    "abilities": ["能力1", "能力2"],
    "invasion_status": "入侵状态（众生界特有）"
  }
}
```

### 3.4 时代提取

**识别关键词**：
- 时代、纪元、时期、年代
- 觉醒、蛰伏、风暴、变革、终局

**提取内容**：
```json
{
  "时代名": {
    "mood": "氛围",
    "color": "色调",
    "symbols": "象征意象"
  }
}
```

### 3.5 核心原则提取

**识别关键词**：
- 主题、核心、立意
- 正邪、善恶、立场
- 感情线、爱情

**提取内容**：
```json
{
  "moral_view": "道德观（如：无正邪，只有立场）",
  "core_theme": "核心主题",
  "romance_rule": "感情线原则"
}
```

---

## 四、AI辅助生成提示词

当自动提取不完整时，使用以下提示词让AI补充：

```
请根据以下小说大纲，生成完整的世界观配置。

大纲内容：
[大纲内容]

请按照以下格式输出JSON：
{
  "world_name": "世界观名称",
  "power_systems": {...},
  "factions": {...},
  "key_characters": {...},
  "eras": {...},
  "core_principles": {...}
}

要求：
1. 所有力量体系必须有明确的代价
2. 势力有独特的文化和建筑风格
3. 角色能力与力量体系匹配
4. 核心原则贯穿整个世界观
```

---

## 五、同步机制

### 5.1 自动同步

当 `config.json` 中 `worldview.auto_sync = true` 时：

1. 每次系统启动时检查大纲文件修改时间
2. 如果大纲比世界观配置更新，自动触发同步
3. 同步时保留用户手动添加的内容

### 5.2 手动同步

```bash
# 查看同步状态
python .vectorstore/core/worldview_sync.py --status

# 执行同步
python .vectorstore/core/worldview_sync.py --sync

# 强制覆盖（谨慎使用）
python .vectorstore/core/worldview_sync.py --sync --force
```

### 5.3 同步策略

| 场景 | 处理方式 |
|------|----------|
| 大纲新增元素 | 自动添加到配置 |
| 大纲修改元素 | 提示用户确认后更新 |
| 大纲删除元素 | 保留配置，标记为"待确认" |
| 配置独有元素 | 保留不变 |

---

## 六、与统一API层集成

生成/更新世界观配置后，自动可用于统一API：

```python
# 自动加载最新配置
from worldview_api import get_worldview_api

api = get_worldview_api()
powers = api.get_power_systems_overview()
factions = api.get_factions_overview()
```

---

## 七、多用户支持

### 7.1 不同项目使用不同世界观

每个项目有自己的 `config.json`：

```json
// 项目A - 众生界
{
  "worldview": {
    "current_world": "众生界",
    "outline_path": "总大纲.md"
  }
}

// 项目B - 科幻小说
{
  "worldview": {
    "current_world": "星际时代",
    "outline_path": "大纲.md"
  }
}
```

### 7.2 创建新世界观

```bash
# 1. 创建新项目目录
mkdir 新小说

# 2. 编写大纲
echo "# 我的科幻小说大纲..." > 新小说/大纲.md

# 3. 生成世界观配置
cd 新小说
python ../众生界/.vectorstore/core/worldview_generator.py --outline "大纲.md" --name "星际时代"

# 4. 配置项目
echo '{
  "worldview": {
    "current_world": "星际时代",
    "outline_path": "大纲.md"
  }
}' > config.json
```

---

## 八、工作流程

### 8.1 新项目初始化

```
1. 创建项目目录
2. 编写小说大纲
3. 运行世界观生成器
4. 配置 config.json
5. 开始创作
```

### 8.2 大纲更新流程

```
1. 修改大纲文件
2. 系统检测到变更（如果启用 auto_sync）
3. 提取变更元素
4. 更新世界观配置
5. 通知用户确认
```

### 8.3 配置验证流程

```
1. Schema格式验证
2. 必填字段检查
3. 逻辑一致性检查（代价必须存在、势力必须有建筑风格等）
4. 与大纲一致性检查
```

---

## 九、文件结构

```
.vectorstore/core/
├── world_configs/
│   ├── 众生界.json          # 世界观配置
│   ├── 修仙世界示例.json
│   └── ...
├── worldview_generator.py    # 生成器工具
├── worldview_sync.py         # 同步工具
├── world_config_loader.py   # 配置加载器
└── config_loader.py          # 已更新支持 worldview 配置
```

---

## 十、示例

### 从众生界大纲提取的结果

```json
{
  "world_name": "众生界",
  "world_type": "multi-power-fantasy",
  "power_systems": {
    "修仙": {
      "source": "天地灵气",
      "realms": ["炼气期", "筑基期", "金丹期", "元婴期", "化神期", "渡劫期"],
      "costs": ["真气耗尽", "经脉受损", "神识透支"]
    },
    "魔法": {
      "source": "魔力源泉",
      "grades": ["一级魔法", "二级魔法", "...", "五级魔法（禁咒级）"],
      "costs": ["魔力枯竭", "精神损耗", "反噬风险"]
    }
    // ... 7个力量体系
  },
  "factions": {
    "东方修仙": {
      "structure": "宗门体系",
      "architecture": "仙山楼阁"
    }
    // ... 10个势力
  },
  "key_characters": {
    "林夕": {
      "faction": "东方修仙",
      "power": "修仙",
      "subtype": "剑丹双修"
    }
    // ... 20个角色
  },
  "eras": {
    "觉醒时代": {"mood": "震惊、迷茫、愤怒、绝望", "color": "血红、暗灰"}
    // ... 5个时代
  },
  "core_principles": {
    "moral_view": "无正邪，只有立场",
    "core_theme": "「我是谁」身份认同贯穿始终"
  }
}
```

---

## 调用方式

### 作为Python模块

```python
from worldview_generator import WorldviewGenerator

generator = WorldviewGenerator()
result = generator.generate_from_outline("总大纲.md", "众生界")
print(f"已生成: {result['file_path']}")
```

### 作为AI对话命令

```
用户: 根据大纲生成世界观配置
AI: [调用此技能] → 解析大纲 → 生成配置 → 保存到 world_configs/
```

---

## 注意事项

1. **首次生成后需人工审核**：AI提取约80%准确，需用户确认
2. **保留原文引用**：每个配置项可追溯回大纲原文
3. **同步是增量的**：大纲修改只更新变化的部分
4. **备份旧配置**：同步前自动备份到 `.cache/worldview_backup/`