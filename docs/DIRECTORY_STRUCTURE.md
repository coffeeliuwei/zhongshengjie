# 目录结构优化方案

> 最后更新：2026-04-10

## 一、当前问题诊断

### 1. 根目录文件过多（已清理）

| 文件 | 状态 | 说明 |
|------|------|------|
| `test_api_direct.py` | ✅ 已删除 | 未被引用 |
| `test_skill.py` | ✅ 已删除 | 未被引用 |
| `test_incremental_sync.py` | ✅ 已删除 | 未被引用 |
| `test_output.txt` | ✅ 已删除 | 输出文件 |
| `test_result.txt` | ✅ 已删除 | 输出文件 |
| `temp_handbook.txt` | ✅ 已删除 | 空文件 |
| `verify_improvements.py` | ✅ 已删除 | 未被引用 |
| `fix_test.py` | ✅ 已删除 | 未被引用 |
| `.test_chroma/` | ✅ 已删除 | 测试目录 |

### 2. 配置文件分散（待优化）

| 配置位置 | 问题 | 建议 |
|----------|------|------|
| `config/dimensions/` | ✅ 已统一 | 维度配置集中 |
| `.vectorstore/core/world_configs/` | ⚠️ 与代码混杂 | 移动到 `config/worlds/` |
| `.case-library/scene_types_full.json` | ⚠️ 重复 | 使用 `config/dimensions/scene_types.json` |
| `.vectorstore/knowledge_graph.json` | ⚠️ 重复 | 清理 `sync/` 目录 |

### 3. 大型数据目录（需评估）

| 目录 | 大小 | 说明 |
|------|------|------|
| `.vectorstore/qdrant_docker/` | 数十GB | 1449个文件，考虑迁移到Docker卷 |
| `.case-library/converted/` | ~400MB | 20+个小说文本文件 |

---

## 二、目录职责定义

```
众生界/
├── config/                    # 统一配置目录
│   ├── dimensions/           # 维度类型配置（场景/力量/势力/技法）
│   └── worlds/               # 世界观配置（建议迁移至此）
│
├── core/                     # 核心模块（Python）
│   ├── change_detector/      # 变更检测器
│   ├── conversation/         # 对话入口层
│   ├── feedback/             # 反馈系统
│   ├── lifecycle/            # 生命周期管理
│   ├── retrieval/            # 统一检索API
│   └── type_discovery/       # 类型发现器
│
├── modules/                  # 功能模块
│   ├── knowledge_base/       # 知识库
│   ├── migration/            # 迁移
│   ├── validation/           # 验证
│   └── visualization/        # 可视化
│
├── tools/                    # 工具脚本
├── tests/                    # 测试文件
├── docs/                     # 文档
│
├── .vectorstore/             # 向量存储
│   ├── core/                 # 向量化逻辑
│   ├── data/                 # 运行时数据
│   └── qdrant/               # Qdrant配置
│
├── .case-library/            # 案例库数据
├── .novel-extractor/         # 小说提取器
├── .cache/                   # 缓存（可删除重建）
└── logs/                     # 日志
```

---

## 三、待执行优化

### 短期（低风险）

- [x] 删除根目录临时测试文件
- [x] 更新 `.gitignore` 防止未来积累
- [ ] 清理 `tests/*.bak` 备份文件
- [ ] 清理 `tools/*.bak` 备份文件

### 中期（需修改代码）

- [ ] 将 `world_configs/` 移动到 `config/worlds/`
  - 需修改：`core/config_loader.py` 中的路径
- [ ] 清理重复的知识图谱文件
- [ ] 删除 `.case-library/scene_types_full.json`

### 长期（需评估）

- [ ] 迁移 `qdrant_docker/` 到Docker卷
- [ ] 简化案例库目录结构（使用数据库索引）
- [ ] 统一所有JSON配置到 `config/` 目录

---

## 四、清理命令参考

```bash
# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} +

# 清理备份文件
find . -name "*.bak" -delete
find . -name "*.backup" -delete

# 清理测试输出
rm -f test_*.txt temp_*.txt
```