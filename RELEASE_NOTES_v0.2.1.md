# Release Notes — v0.2.1 (2026-04-21)

## 发布主题：多小说解耦完整实施（M8）

### 核心变更

#### 新增 `core/world_loader.py`
任意克隆的新机器，只需修改 `config.json → worldview.current_world`，即可切换到不同小说世界观，无需修改任何 skill 文件。

主要 API：
- `get_world_config(world_name, project_root)` — 加载指定世界观配置
- `get_current_world_name(project_root)` — 读取当前激活世界观
- `switch_world(new_world_name, project_root)` — 切换世界观（修改 config.json）
- `list_available_worlds(project_root)` — 列出 config/worlds/ 下所有可用世界观

#### CLI `switch-world` 子命令
```bash
python -m core switch-world 星海纪元       # 切换到星海纪元
python -m core switch-world --list        # 列出所有可用世界观
```

#### Skill 文件硬编码清理
- **B/C 类（4 处）**：novel-workflow、novelist-evaluator（×2）、novel-inspiration-ingest 中的绝对路径 → 改为从 `config.json` 动态读取
- **A 类（~200 处）**：批量替换世界观专属名词（血牙/林夕/村庄广场/血脉-天裂/东方修仙界等）为通用占位符

#### 示例世界观配置
`config/worlds/` 新增 4 个示例：修仙世界示例、星海纪元、科幻世界示例、西方奇幻示例

### 验收测试
```
pytest 666 passed, 2 skipped, 0 failed
test_m8_world_agnostic.py: 23 passed（skill卫生 + world_loader + switch_world 全绿）
```

### 升级方式
```bash
git pull origin master
```
无 breaking change，无需修改现有 `config.json`。

---

*发布者：coffeeliuwei / Claude Sonnet 4.6*
