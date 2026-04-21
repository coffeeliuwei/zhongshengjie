# 大纲 × 设定 重叠/冲突审计

本目录存放自动审计的输出与人工分析建议。

## 审计说明

- 数据来源：
  - 大纲：`章节大纲/*.md` 与 `总大纲.md`（使用 `ChapterOutlineParser` 的 `key_settings` 表）
  - 设定：`.vectorstore/knowledge_graph.json`
- 比对策略：以 `entity + field` 为键对齐；值完全一致 → duplicate；不一致 → conflict；仅大纲侧 → outline_only
- 不做任何写入修改，仅输出报告与建议

## 工具

```bash
PYTHONPATH=. python tools/audit_outline_vs_settings.py
# 输出：
# - 控制台摘要
# - .cache/outline_vs_settings_report.json
```

## 当前摘要（最后一次运行）

见 `.cache/outline_vs_settings_report.json`，样例结果：

```json
{
  "stats": {"outline_items": 6},
  "conflicts": [],
  "duplicates": [],
  "outline_only": [
    {"entity": "血牙年龄", "field": "关键设定", "value": "灭族时约10-13岁，现在约23岁（十年后）", "source": "章节大纲/第一章-天裂大纲.md"},
    {"entity": "血牙父亲", "field": "关键设定", "value": "铁牙，在山林中用血脉组成人墙，被打成筛子战死", "source": "章节大纲/第一章-天裂大纲.md"},
    {"entity": "幸存原因", "field": "关键设定", "value": "母亲藏进树洞，血脉压制气息，未被佣兵发现", "source": "章节大纲/第一章-天裂大纲.md"},
    {"entity": "目睹内容", "field": "关键设定", "value": "1) 山林中上吊的妇孺被肢解 2) 村口男人残肢", "source": "章节大纲/第一章-天裂大纲.md"},
    {"entity": "仇恨指向", "field": "关键设定", "value": "佣兵联盟（血牙不知道AI入侵）", "source": "章节大纲/第一章-天裂大纲.md"}
  ]
}
```

## 修复建议（第一批）

将 `outline_only` 转化为设定 PATCH，优先落在：

1) `设定/人物谱.md` → 为“血牙”条目新增“过往经历速查”补充项（年龄、父亲之死、幸存原因、目睹内容、仇恨指向）
2) `设定/角色过往经历与情绪触发.md` → 在“17. 血牙”下对照补齐同 5 项为标准表格行（已存在大纲摘取，可核对一致）

入库规范（严格执行 5.4）：

```bash
# 1) knowledge_graph.json 手工/脚本同步新增属性（血牙实体）
#    - 年龄、父亲之死、幸存原因、目睹内容、仇恨指向（建议嵌套到“过往经历/创伤/仇恨”）

# 2) 跑同步
python -m modules.knowledge_base.sync_manager --target novel

# 3) 校验
python -m modules.knowledge_base.sync_manager --status
# 观察 novel_settings point count 是否增加
```

## 后续批量化

- 扩展解析器映射：允许在大纲“关键设定”表中使用 `实体:字段` 作为键名，更精准对齐图谱字段（例如：`血牙:仇恨指向`、`血牙:幸存原因`）
- 批量章节：遍历所有 `章节大纲/*.md`，生成分章级的合并报告，集中生成 PATCH 草案
