# 闭源发布指南

本文档描述如何将众生界核心代码编译为 Cython 闭源版本并发布到 `release-closed` 分支。

## 前置条件

### 1. Python 与依赖

- Windows + Python 3.12.7
- `pip install "cython>=3.0.0,<4.0.0"`

### 2. MSVC C++ Build Tools（必须）

Cython 编译 .pyd 需要 MSVC 编译器。

**安装方式 A · 已装 Visual Studio**：
跳过本段，直接看"激活 MSVC 环境"。

**安装方式 B · 未装**：
下载 [VS Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)（约 2GB），
安装时勾选"使用 C++ 的桌面开发"工作负载。

### 3. 激活 MSVC 环境（每次新 shell 都要做）

找到你的 `vcvarsall.bat`，路径形如：
- `E:\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat`
- `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat`

**方式 A · Developer Command Prompt**（推荐）：
开始菜单 → 搜索 "Developer Command Prompt for VS 2026" → 在该 shell 里跑 `python build.py`

**方式 B · 手动激活**：
```cmd
call "E:\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64
python build.py
```

**判断 MSVC 是否激活**：
```cmd
echo %INCLUDE%
```
若输出含 `MSVC` 或 `Visual Studio` 路径，则已激活。
若输出空，未激活——`build.py` 会拦下并报错（[N12 已加预警检测]）。

### 4. master 分支 tree clean

确保 master 分支无未提交的改动。

---

## 背景

众生界开源版本（master 分支）包含完整的源代码。为了支持闭源分发，我们提供 Cython 编译方案，将 `core/` 目录编译为 `.pyd`（Windows）或 `.so`（Linux/Mac）二进制文件。

## 编译范围

| 目录 | 是否编译 | 原因 |
|------|----------|------|
| `core/` | ✅ 是 | 核心业务逻辑 |
| `modules/` | ❌ 否 | 配置/适配层 |
| `scripts/` | ❌ 否 | 用户脚本 |
| `tools/` | ❌ 否 | 构建工具 |
| `tests/` | ❌ 否 | 测试代码 |
| `__init__.py` | ❌ 否 | 子包导入必需 |
| `__main__.py` | ❌ 否 | CLI 入口 `python -m core` 必须保留 .py 源 |

**编译文件数**: 51 个 `.py` 文件（N12 修正：排除 __main__.py）

## 使用工具

### setup.py - Cython 编译配置

```bash
# 本地编译测试
python setup.py build_ext --inplace
```

### build.py - 编译驱动脚本

```bash
# 编译
python build.py

# 清理编译产物
python build.py --clean

# 查看状态
python build.py --status

# 仅打印将编译的文件（dry-run）
python build.py --dry-run
```

### release.py - 发布自动化（dry-run）

```bash
# 查看完整流程（dry-run）
python release.py --dry-run

# 准备编译产物
python release.py --prepare

# 创建分支步骤（dry-run）
python release.py --create
```

## 发布流程

### Step 1: 确认环境

```bash
# 确认当前在 master 分支
git branch --show-current  # 应输出: master

# 确认 Cython 已安装
pip show cython  # 版本 >= 3.0.0, < 4.0.0
```

### Step 2: 编译

```bash
# 编译 core/ 目录
python build.py

# 验证编译结果
python build.py --status
# 应显示: 已编译 .pyd: 52
```

### Step 3: 创建 release-closed 分支（手动）

```bash
# 创建分支（从 master）
git checkout -b release-closed

# 或切换到已有分支
git checkout release-closed
```

### Step 4: 删除源代码（保留 __init__.py 和 __main__.py）

```bash
# 删除 core/ 下的 .py 文件（排除 __init__.py 和 __main__.py）
# Windows PowerShell:
Get-ChildItem -Path core -Recurse -Filter "*.py" | 
  Where-Object { $_.Name -ne "__init__.py" -and $_.Name -ne "__main__.py" } | 
  Remove-Item

# Linux/Mac:
find core -name "*.py" -not -name "__init__.py" -not -name "__main__.py" -delete
```

### Step 5: 提交变更

```bash
git add -A
git commit -m "Release v14.0 closed-source: compile core/ to .pyd"
git push -u origin release-closed
```

## 编译产物

编译后生成的文件：

| 文件类型 | 数量 | 说明 |
|----------|------|------|
| `.pyd` | 52 | Windows 编译产物 |
| `.c` | 52 | Cython 生成的 C 源码 |
| `build/` | 1 | 构建临时目录 |

**注意**: `.c` 文件和 `build/` 目录不应提交到 Git。

## .gitignore 配置

确保 `.gitignore` 包含：

```gitignore
# Cython 编译产物
*.pyd
*.so
*.c
build/
dist/
*.egg-info/

# 但保留 release-closed 分支的 .pyd
# （在 release-closed 分支时需临时移除 .pyd 排除规则）
```

## 运行编译版本

编译后的代码可直接运行：

```bash
# CLI 功能不变
python -m core kb --stats

# 对话入口不变
python -m core conversation --help
```

## 兼容性

- **Python**: 3.8+
- **Cython**: 3.0.0 - 3.x（不支持 4.x）
- **操作系统**: Windows / Linux / macOS

## 回滚

如需回退到源码版本：

```bash
# 切回 master 分支
git checkout master

# 清理编译产物
python build.py --clean
```

## 安全考虑

- Cython 编译后的 `.pyd` 文件可被逆向（难度较高）
- 核心算法保护建议配合许可证约束
- 不建议编译依赖外部库的代码（如 Qdrant 客户端）

## 版本信息

- **里程碑**: M6
- **版本**: v14.0.0
- **更新**: 2026-04-18