# M6 里程碑验收报告

## 里程碑概述

**目标**: 完成闭源分发工具链（Cython 编译 + release-closed 分支架构）

**执行时间**: 2026-04-18

**状态**: ✅ 完成

---

## §1 集合名统一（N11）

### §1.1 sync_manager.py + search_manager.py

**修改前**:
```python
# sync_manager.py (已改)
NOVEL_COLLECTION = "novel_settings"
TECHNIQUE_COLLECTION = "writing_techniques"
CASE_COLLECTION = "case_library"

# search_manager.py (待改)
NOVEL_COLLECTION = "novel_settings"
TECHNIQUE_COLLECTION = "writing_techniques"
CASE_COLLECTION = "case_library"
```

**修改后**:
```python
# 两文件统一使用 v2 版本
NOVEL_COLLECTION = "novel_settings_v2"
TECHNIQUE_COLLECTION = "writing_techniques_v2"
CASE_COLLECTION = "case_library_v2"
```

**验收**:
- [N11-A] grep 确认三集合都带 `_v2`: ✅ 通过
- [N11-B] CLI `python -m core kb --stats` 显示真实 count: ✅ 通过

**CLI 验证结果**:
```
小说设定库: 160
创作技法库: 986
案例库: 387377
```

---

## §2 Cython 兼容性预检

### §2.1 扫描危险模式

**扫描范围**: `core/` 目录（62 个 .py 文件）

**扫描模式**: `__import__|eval(|exec(|getattr(.*, ['"]|setattr(.*, ['"]`

**扫描结果**:
- 发现 1 处: `__import__("datetime")` 在 `missing_info_detector.py`
- **安全性**: ✅ 安全（固定模块名，Cython 可处理）

### §2.2 编译范围确认

| 目录 | 文件数 | 是否编译 |
|------|--------|----------|
| `core/` | 62 | ✅ 排除 __init__.py |
| `modules/worldview/` | - | ❌ 目录不存在 |

**实际编译文件数**: 52 个（排除 10 个 __init__.py）

---

## §3 Cython 安装

**命令**: `pip install "cython>=3.0.0,<4.0.0"`

**安装结果**: ✅ Cython 3.2.4

---

## §4 编译工具链

### §4.1 setup.py

**功能**: Cython 编译配置，定义 52 个 Extension

**验收**: ✅ 文件存在，语法正确

### §4.2 build.py

**功能**: 编译驱动脚本，支持 `--clean/--status/--dry-run`

**验收**:
- `build.py --dry-run`: ✅ 打印 52 个文件
- 无 emoji 编码错误: ✅ 已修复

### §4.3 release.py

**功能**: 发布自动化（dry-run 模式），master → release-closed

**验收**:
- `release.py --dry-run`: ✅ 打印完整流程
- 保留 10 个 `__init__.py`: ✅ 确认

### §4.4 RELEASE.md

**功能**: 闭源发布流程文档

**验收**: ✅ 文件存在，内容完整

---

## §5 .gitignore 更新

**追加内容**:
```gitignore
# Cython 编译产物（M6 闭源分发）
*.pyd
*.c
```

**验收**: ✅ 已追加

---

## §6 Dry-Run 演练

### §6.1 build.py --dry-run

**输出**:
```
[DRY-RUN] 将编译 52 个文件
  core\__main__.py
  core\change_detector\change_detector.py
  ...
[WARN] 未实际编译（dry-run 模式）
```

**验收**: ✅ 通过

### §6.2 release.py --dry-run

**输出**:
```
[STEP-1] 当前分支 = master
[STEP-2] 编译（可选，可跳过）
[STEP-3] Git 操作（dry-run）
  删除 52 个 .py 文件
  保留 10 个 __init__.py
[WARN] 所有操作都是 dry-run，请手动执行
```

**验收**: ✅ 通过

---

## 验收清单

| 验收项 | 状态 | 说明 |
|--------|------|------|
| N11-A | ✅ | grep 三集合带 _v2 |
| N11-B | ✅ | CLI stats 显示 160/986/387377 |
| N12-A | ✅ | setup.py 存在 |
| N12-B | ✅ | build.py --dry-run 成功 |
| N12-C | ✅ | release.py --dry-run 成功 |
| N12-D | ✅ | RELEASE.md 存在 |
| N12-E | ✅ | .gitignore 有 *.pyd/*.c |
| N12-F | ✅ | Cython 3.2.4 安装 |
| N12-G | ✅ | 52 个文件待编译确认 |
| N12-H | ✅ | 10 个 __init__.py 保留确认 |

---

## 约束遵守情况

| 约束 | 遵守情况 |
|------|----------|
| 不 git commit | ✅ 无 commit |
| 不真切到 release-closed | ✅ 仅 dry-run |
| 不编译 __init__.py | ✅ 已排除 |
| 不编译 modules/scripts/tools/tests | ✅ 仅编译 core/ |
| 不在 master 留下 .pyd/.c/build/ | ✅ 仅 dry-run |
| 不装 Cython 4.x | ✅ 安装 3.2.4 |

---

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `modules/knowledge_base/search_manager.py` | 修改 | 三集合常量加 `_v2` |
| `modules/knowledge_base/sync_manager.py` | 修改 | 三集合常量加 `_v2`（之前已完成） |
| `setup.py` | 新增 | Cython 编译配置 |
| `build.py` | 新增 | 编译驱动脚本 |
| `release.py` | 新增 | 发布自动化脚本 |
| `RELEASE.md` | 新增 | 闭源发布文档 |
| `.gitignore` | 修改 | 追加 *.pyd/*.c |

---

## 后续操作

用户需手动执行以下操作：

1. **审核所有改动**（M1-M6）
2. **统一提交**: `git add -A && git commit -m "Complete M1-M6 milestones"`
3. **创建 release-closed 分支**（可选）:
   ```bash
   git checkout -b release-closed
   python build.py  # 实际编译
   # 删除 core/ 下的 .py 文件（保留 __init__.py）
   git add -A
   git commit -m "Release v14.0 closed-source"
   git push -u origin release-closed
   ```

---

## 版本信息

- **里程碑**: M6
- **版本**: v14.0
- **日期**: 2026-04-18