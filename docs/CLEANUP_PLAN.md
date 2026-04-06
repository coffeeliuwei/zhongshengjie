# 项目文件清理计划

## 清理原则

1. **核心模块不删除** - modules/, core/ 等核心代码
2. **测试文件保留** - tests/ 目录下的测试文件保留
3. **工具脚本分类** - 验证/检查脚本移到 tools/ 目录
4. **历史存档保留** - 存档/ 目录不动
5. **日志文件清理** - .log 文件可清理

---

## 清理分类

### 1. 可删除文件 (无风险)

```
无 .tmp 文件
无 .bak 文件
```

### 2. 可清理的日志文件

```
.case-library/logs/*.log (4个)
├── qdrant_sync.log
├── reextract.log
├── unified_extraction.log
└── batch2_process.log
```

### 3. .vectorstore 目录重构

**当前状态**: 58 个 Python 文件，混合了核心模块、工具脚本、测试文件

**建议结构**:
```
.vectorstore/
├── core/                    # 核心功能 (保留)
│   ├── knowledge_search.py
│   ├── technique_search.py
│   ├── case_search.py
│   ├── workflow.py
│   ├── knowledge_graph.py
│   ├── data_model.py
│   └── vectorizer/
│       ├── knowledge_vectorizer.py
│       └── technique_vectorizer.py
│
├── sync/                    # 同步脚本 (保留)
│   ├── sync_to_vectorstore_v3.py
│   ├── rebuild_knowledge_graph_v2.py
│   └── sync_cases.py
│
├── tools/                   # 工具脚本 (新建)
│   ├── verify/              # 验证工具
│   │   ├── verify_all.py
│   │   └── ...
│   ├── check/               # 检查工具
│   │   ├── check_entity.py
│   │   └── ...
│   └── debug/               # 调试工具
│       └── debug_names.py
│
└── archived/                # 历史版本 (移动)
    ├── sync_to_vectorstore_v2.py
    ├── rebuild_knowledge_graph.py
    └── ...
```

---

## 具体清理操作

### Phase 1: 创建目录结构

```bash
mkdir .vectorstore\core
mkdir .vectorstore\core\vectorizer
mkdir .vectorstore\sync
mkdir .vectorstore\tools
mkdir .vectorstore\tools\verify
mkdir .vectorstore\tools\check
mkdir .vectorstore\tools\debug
mkdir .vectorstore\archived
```

### Phase 2: 移动核心文件

**保留在 .vectorstore/**:
- knowledge_search.py
- technique_search.py
- case_search.py (主版本)
- workflow.py
- knowledge_graph.py
- data_model.py
- knowledge_vectorizer.py
- technique_vectorizer.py

### Phase 3: 移动同步脚本

**移到 .vectorstore/sync/**:
- sync_to_vectorstore_v3.py
- rebuild_knowledge_graph_v2.py
- sync_cases.py
- sync_batch2_cases.py

### Phase 4: 移动工具脚本

**移到 .vectorstore/tools/verify/**:
- verify_all.py
- verify_sync.py
- verify_structures.py
- verify_*.py (10个)

**移到 .vectorstore/tools/check/**:
- check_entity.py
- check_relations.py
- check_*.py (11个)

**移到 .vectorstore/tools/debug/**:
- debug_names.py
- db_viewer.py
- fix_xueya.py

### Phase 5: 移动历史版本

**移到 .vectorstore/archived/**:
- sync_to_vectorstore_v2.py
- sync_to_vectorstore.py
- rebuild_knowledge_graph.py
- migrate_to_qdrant.py
- case_search_json.py
- case_search_qdrant.py (保留最新 case_search.py)

### Phase 6: 移动测试文件

**移到 tests/**:
- test_*.py (5个)

### Phase 7: 清理日志

**可删除**:
- .case-library/logs/*.log

---

## 清理后目录统计

| 目录 | 文件数 | 说明 |
|------|--------|------|
| .vectorstore/ | ~15 | 核心模块 |
| .vectorstore/sync/ | ~5 | 同步脚本 |
| .vectorstore/tools/verify/ | ~10 | 验证工具 |
| .vectorstore/tools/check/ | ~11 | 检查工具 |
| .vectorstore/tools/debug/ | ~3 | 调试工具 |
| .vectorstore/archived/ | ~10 | 历史版本 |
| tests/ | ~7 | 测试文件 |

---

## 不清理的文件

| 文件/目录 | 原因 |
|-----------|------|
| 存档/ | 历史存档，保留 |
| modules/ | 核心模块 |
| core/ | 核心基础设施 |
| tests/system_test.py | 系统测试 |
| CONFIG.md | 配置文件 |
| AI_GUIDE.md | AI 手册 |