# 技法管线修复计划
**日期：2026-04-30 00:47（上海时间）**
**起草人：Claude**  
**执行人：opencode（GLM5）**  
**参考协议：docs/opencode_dev_protocol_20260420.md v1**  
**分支：master（禁止创建新分支）**

---

## 背景与问题清单

经过对自学习/自补充功能的端到端分析，发现以下 5 类问题，导致"从小说提炼技法→同步→写手调用"的完整闭环**实际上全部失效**：

| # | 严重 | 问题 | 文件 |
|---|------|------|------|
| P1 | 🔴 CRITICAL | `novel-inspiration-ingest` skill 技法 sync 命令错误，会用无名向量重建集合 | `C:/Users/39477/.agents/skills/novel-inspiration-ingest/SKILL.md` |
| P2 | 🔴 CRITICAL | `UnifiedRetrievalAPI` 缺少 17 个维度专属方法，5 位写手 skill 引用的全部不存在 | `core/retrieval/unified_retrieval_api.py` |
| P3 | 🟠 HIGH | `sync_manager.sync_techniques()` 无 schema 保护，`--target all` 会触发，用无名向量破坏集合 | `modules/knowledge_base/sync_manager.py` |
| P4 | 🟡 MEDIUM | `docs/系统架构.md` 两处错误文档 | `docs/系统架构.md` |
| P5 | 🟡 MEDIUM | `novel-inspiration-ingest` skill 中 `--target novel` 也是旧脚本，与 P1 同文件一并修 | `C:/Users/39477/.agents/skills/novel-inspiration-ingest/SKILL.md` |

---

## 任务一：修复 novel-inspiration-ingest skill 的 sync 命令

**文件**：`C:/Users/39477/.agents/skills/novel-inspiration-ingest/SKILL.md`

### 修改说明

第 365 行（sync 命令表格）和第 375 行（代码块）中，创作技法的 sync 命令写的是：
```
python -m modules.knowledge_base.sync_manager --target technique
```
这会调用 `sync_manager.sync_techniques()`，用**无名向量**（`VectorParams(size=1024)`）重建 `writing_techniques_v2` 集合，导致所有使用 `using="dense"` / `using="sparse"` 的混合检索全部报错。

正确命令是：
```
python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild
```

### 具体改动

**改动 1**：第 365 行表格中的技法 sync 命令

原文（第 365 行）：
```
| `创作技法/**/*.md` | `python -m modules.knowledge_base.sync_manager --target technique` | `writing_techniques_v2` | 直接读目录，无需中间文件 |
```

替换为：
```
| `创作技法/**/*.md` | `python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild` | `writing_techniques_v2` | 混合向量(dense+sparse+colbert)，必须用 hybrid_sync_manager |
```

**改动 2**：第 371-377 行（"技法+案例类 sync" 代码块）

找到以下内容：
```markdown
#### 技法+案例类 sync

```python
# 同步技法到 writing_techniques_v2
python -m modules.knowledge_base.sync_manager --target technique
```
```

替换为：
```markdown
#### 技法+案例类 sync

> ⚠️ **重要**：技法 sync 必须使用 `hybrid_sync_manager`，不能用 `sync_manager`。  
> `sync_manager --target technique` 会用无名向量重建集合，破坏 BGE-M3 混合检索。

```python
# 同步技法到 writing_techniques_v2（混合向量：dense + sparse + colbert）
python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild
```
```

---

## 任务二：修复 sync_manager.sync_techniques() 的 schema 保护

**文件**：`modules/knowledge_base/sync_manager.py`

### 修改说明

`sync_manager.sync_techniques()` 会用无名向量重建 `writing_techniques_v2`，与 `HybridSearchManager` 要求的 colbert+sparse+dense 三向量命名 schema 不兼容。`--target all` 也会触发此函数。需要在函数入口加保护，禁止执行并明确指向正确脚本。

### 具体改动

**文件**：`modules/knowledge_base/sync_manager.py`

找到第 335 行开始的 `sync_techniques` 方法：
```python
    def sync_techniques(self, rebuild: bool = False) -> int:
        """
        同步创作技法

        Args:
            rebuild: 是否重建数据库

        Returns:
            同步数量
        """
        print("\n[同步创作技法]")
```

替换为：
```python
    def sync_techniques(self, rebuild: bool = False) -> int:
        """
        同步创作技法

        ⚠️ 已停用：writing_techniques_v2 使用 BGE-M3 混合向量（dense+sparse+colbert），
        本方法创建的是无名单向量集合，与 HybridSearchManager.search_technique() 不兼容。

        请改用：
            python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild

        Returns:
            0（始终跳过）
        """
        print(
            "\n[sync_techniques] ⚠️ 已停用。\n"
            "  writing_techniques_v2 需要 BGE-M3 混合向量（dense+sparse+colbert）。\n"
            "  请改用：python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild\n"
            "  本次跳过技法同步，其余目标继续执行。"
        )
        return 0
```

同时，找到 CLI 入口附近第 604-605 行：
```python
    if args.target in ("technique", "all"):
        n = sm.sync_techniques(rebuild=args.rebuild)
```

这两行**不需要改动**——`sync_techniques()` 已返回 0 并打印警告，自然跳过。

---

## 任务三：为 UnifiedRetrievalAPI 添加 17 个维度专属方法

**文件**：`core/retrieval/unified_retrieval_api.py`

### 修改说明

5 位写手 skill 引用以下方法，全部不存在于 `UnifiedRetrievalAPI`，调用时会抛 `AttributeError`：

**苍澜（世界观）**：`search_by_keywords`, `get_worldview_expert_techniques`, `search_worldview_techniques`  
**玄一（剧情）**：`search_foreshadowing_techniques`, `search_suspense_techniques`, `search_reversal_techniques`, `get_plot_expert_techniques`, `search_plot_techniques`  
**云溪（氛围）**：`search_poetry_techniques`, `search_poetry_by_keywords`, `get_poetry_expert_techniques`  
**墨言（人物）**：`search_emotion_techniques`, `search_character_techniques`, `get_character_expert_techniques`  
**剑尘（战斗）**：`search_battle_techniques`, `search_battle_by_keywords`, `get_battle_expert_techniques`

所有方法都是 `search_techniques(query, dimension=X)` 的薄封装，不引入新依赖。

### 插入位置

在 `search_techniques` 方法（约第 403-430 行）**之后**，在 `search_cases` 方法**之前**，插入以下完整代码块：

```python
    # ── 维度专属技法检索（各写手 skill 便捷接口）──────────────────────────

    def search_by_keywords(
        self,
        keywords: list,
        dimension: Optional[str] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """关键词列表合并为查询串后检索技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension=dimension, top_k=top_k)

    # ── 世界观维度（苍澜） ──────────────────────────────────────────────────

    def search_worldview_techniques(
        self,
        query: str = "世界观构建",
        dimension: str = "世界观维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索世界观维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def get_worldview_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取世界观专家级技法（史诗级世界观 + 力量体系）"""
        return self.search_techniques(
            "史诗级世界观架构 力量体系设计 世界观自生长",
            dimension="世界观维度",
            top_k=top_k,
        )

    # ── 剧情维度（玄一） ────────────────────────────────────────────────────

    def search_plot_techniques(
        self,
        query: str = "剧情推进",
        dimension: str = "剧情维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索剧情维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_foreshadowing_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索伏笔设置技法"""
        return self.search_techniques(
            "伏笔设置 埋线技法 伏笔回收",
            dimension="剧情维度",
            top_k=top_k,
        )

    def search_suspense_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索悬念制造技法"""
        return self.search_techniques(
            "悬念制造 钩子设计 读者好奇心",
            dimension="叙事维度",
            top_k=top_k,
        )

    def search_reversal_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索反转技法"""
        return self.search_techniques(
            "剧情反转 意外结局 逆转时机",
            dimension="剧情维度",
            top_k=top_k,
        )

    def get_plot_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取剧情专家级技法"""
        return self.search_techniques(
            "史诗级剧情架构 伏笔回收 三幕结构 高潮设计",
            dimension="剧情维度",
            top_k=top_k,
        )

    # ── 氛围意境维度（云溪） ────────────────────────────────────────────────

    def search_poetry_techniques(
        self,
        query: str = "氛围意境",
        dimension: str = "氛围意境维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索氛围意境维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_poetry_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词检索氛围意境技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension="氛围意境维度", top_k=top_k)

    def get_poetry_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取氛围意境专家级技法"""
        return self.search_techniques(
            "诗意氛围 意境营造 五感写作 留白技法",
            dimension="氛围意境维度",
            top_k=top_k,
        )

    # ── 人物维度（墨言） ────────────────────────────────────────────────────

    def search_character_techniques(
        self,
        query: str = "人物刻画",
        dimension: str = "人物维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索人物维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_emotion_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索情感描写技法"""
        return self.search_techniques(
            "情感描写 情绪渲染 内心独白",
            dimension="情感维度",
            top_k=top_k,
        )

    def get_character_expert_techniques(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取人物塑造专家级技法"""
        return self.search_techniques(
            "史诗级人物塑造 角色弧光 创伤成长 群像技法",
            dimension="人物维度",
            top_k=top_k,
        )

    # ── 战斗冲突维度（剑尘） ────────────────────────────────────────────────

    def search_battle_techniques(
        self,
        query: str = "战斗描写",
        dimension: str = "战斗冲突维度",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """检索战斗冲突维度技法"""
        return self.search_techniques(query, dimension=dimension, top_k=limit)

    def search_battle_by_keywords(
        self, keywords: list, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词检索战斗技法"""
        query = " ".join(str(k) for k in keywords)
        return self.search_techniques(query, dimension="战斗冲突维度", top_k=top_k)

    def get_battle_expert_techniques(
        self, power_system: str = "", top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """获取战斗冲突专家级技法，可按力量体系过滤"""
        query = f"史诗级战斗设计 力量体系对抗 弱胜强技法 {power_system}".strip()
        return self.search_techniques(query, dimension="战斗冲突维度", top_k=top_k)
```

---

## 任务四：修复 docs/系统架构.md 的两处文档错误

**文件**：`docs/系统架构.md`

### 错误 1：第 71 行表格中的错误 sync 命令

找到（第 71 行附近）：
```markdown
| 技法 | `创作技法/99-从小说提取/{维度}.md` | `python -m modules.knowledge_base.sync_manager --target technique` | `writing_techniques_v2` |
```

替换为：
```markdown
| 技法 | `创作技法/99-从小说提取/{维度}.md` | `python -m modules.knowledge_base.hybrid_sync_manager --sync technique --rebuild` | `writing_techniques_v2` |
```

### 错误 2：第 224 行和第 267 行的虚构路径

找到（第 224 行附近）：
```
  technique → writing_techniques_v2    → 更新 SCENE_TYPES
```

替换为：
```
  （technique 维度不经 unified_extractor，由 hybrid_sync_manager 从 创作技法/**/*.md 直接同步）
```

找到（第 267 行附近）：
```markdown
| `writing_techniques_v2` | inspiration-ingest(技法) / unified_extractor(technique) | 技法检索 |
```

替换为：
```markdown
| `writing_techniques_v2` | inspiration-ingest(技法) → 创作技法/**/*.md → hybrid_sync_manager | 技法检索（混合向量 dense+sparse+colbert） |
```

### 错误 3：第 317 行附近的 sync 命令列表

找到：
```
│  sync_manager --target novel/technique                   │
```

替换为：
```
│  sync_manager --target novel（设定）                      │
│  hybrid_sync_manager --sync technique --rebuild（技法）   │
```

---

## 验证步骤（4 阶段）

### 阶段 1：静态验证
```bash
cd D:/动画/众生界
python -c "
from core.retrieval.unified_retrieval_api import UnifiedRetrievalAPI
api = UnifiedRetrievalAPI.__new__(UnifiedRetrievalAPI)
methods = ['search_by_keywords','search_worldview_techniques','get_worldview_expert_techniques',
           'search_plot_techniques','search_foreshadowing_techniques','search_suspense_techniques',
           'search_reversal_techniques','get_plot_expert_techniques',
           'search_poetry_techniques','search_poetry_by_keywords','get_poetry_expert_techniques',
           'search_character_techniques','search_emotion_techniques','get_character_expert_techniques',
           'search_battle_techniques','search_battle_by_keywords','get_battle_expert_techniques']
missing = [m for m in methods if not hasattr(api, m)]
print('缺失方法：', missing if missing else '无，全部存在 ✅')
"
```
预期输出：`缺失方法：无，全部存在 ✅`

### 阶段 2：单元测试
```bash
python -m pytest tests/test_validation_metrics.py tests/test_validation_judge.py tests/test_validation_runner.py -v 2>&1 | tee logs/test_technique_fix_$(TZ=Asia/Shanghai date +%Y%m%d_%H%M%S).log
```
预期：所有已有测试通过（27 个），无回归。

### 阶段 3：sync_manager 保护验证
```bash
python -c "
from modules.knowledge_base.sync_manager import SyncManager
sm = SyncManager.__new__(SyncManager)
# 直接调用应打印警告并返回 0，不报错，不触发 QdrantClient
result = sm.sync_techniques.__doc__
print('方法文档含已停用说明：', '已停用' in result)
"
```
注意：`sync_techniques` 现在打印警告并返回 0，但其内部不再尝试连接 Qdrant（因为函数在连接前就 return），所以无需 mock。如果实现中保留了连接代码，需要用 mock 测试。

### 阶段 4：提交
```bash
git add core/retrieval/unified_retrieval_api.py \
        modules/knowledge_base/sync_manager.py \
        docs/系统架构.md
# skill 文件在用户主目录，不属于 git 仓库，改完即生效，无需 add

git commit -m "fix: 修复技法管线——UnifiedRetrievalAPI 补全 17 个写手专属方法，sync_manager 加停用保护，架构文档纠错"
```

---

## 注意事项

1. **skill 文件不在 git 仓库内**：`C:/Users/39477/.agents/skills/novel-inspiration-ingest/SKILL.md` 改动后直接生效，无需 git 操作。
2. **不要在改动 sync_manager.sync_techniques() 时删除其他 sync 目标**（novel/case）——仅修改 technique 方法。
3. **`search_suspense_techniques` 的 dimension 用 `叙事维度`**（悬念属叙事层），不是 `剧情维度`，确认 TECHNIQUE_DIMENSIONS 包含此值后再写入。
4. **不要改 hybrid_sync_manager.py**，它是正确的，不动。
5. 所有新方法不加除函数签名必须以外的注释，保持代码库风格一致。
