# M5 端到端验证 · 前快照

**时间**：2026-04-18 14:37:00 (UTC+8)
**git HEAD**：8365fe21ae9bf8200446c5f87cba08cbb188ec59
**git status --short**：32 条 R（rename）记录 + M3/M4 新增修改（详见 git status）

## Qdrant 三集合 point count

| Collection | Pre-count |
|---|---|
| novel_settings_v2 | 160 |
| writing_techniques_v2 | 986 |
| case_library_v2 | 387377 |

## 关键文件 mtime + sha256（前 8 位）

| 文件 | mtime | sha256[:8] |
|---|---|---|
| 总大纲.md | 2026-04-16T20:18:35 | dd2cc5f3 |
| .vectorstore/knowledge_graph.json | 2026-04-18T03:58:15 | 0a21c1e0 |
| config/intent_patterns.json | 2026-04-18T13:58:52 | 6a37ec1e |

## 用户许可确认

**自动模式**：链路 B（作家工作流，需 LLM 调用）已跳过，记录于 link_b_skipped.md。

---

## 环境检查记录

### 1.1 Qdrant 服务可达
```
尝试连接: http://localhost:6333
OK，13 个 collection: ['writing_techniques_v2', 'character_relation_v1', 'case_library_v2', 'novel_settings_v2', 'poetry_imagery_v2', 'power_cost_v1', 'worldview_element_v1', 'dialogue_style_v1', 'emotion_arc_v1', 'foreshadow_pair_v1', 'evaluation_criteria_v1', 'author_style_v1', 'power_vocabulary_v1']
```

### 1.2 BGE-M3 模型可加载
```
model_path: E:/huggingface_cache/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181
模型路径校验通过
```

### 1.3 配置完整性
```
  novel_settings -> novel_settings_v2
  writing_techniques -> writing_techniques_v2
  case_library -> case_library_v2
OK
```