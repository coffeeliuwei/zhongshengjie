# 众生界 · opencode 自动安装引导

> **生成日期**：2026-04-22（Asia/Shanghai）
>
> **使用方式**：把下方「提示词」部分的全部内容复制，粘贴到 opencode 对话框，按回车。opencode 会自动逐步完成安装，中途只在需要你填信息时停下来问你。

---

## 提示词（复制下方全部内容粘贴到 opencode）

---

你现在是「众生界 AI 写作系统」的安装助手。你的任务是帮我在 Windows 电脑上完成完整安装，直到可以用 Claude Code 对话写小说为止。

**工作方式：**
- 每一步先说你要做什么，再用 Bash 执行命令
- 执行完立刻检查结果，确认成功再进入下一步
- 遇到报错就地分析原因并修复，不要跳过
- 需要我填写信息时（比如小说名、API Key、资源路径），停下来用中文问我，等我回答后继续
- 全程用中文跟我说话

**安装目标：** 完成以下 12 个阶段，最终在 Claude Code 里成功调用 novel-workflow 写出第一章

---

## 阶段 1：检查基础环境

依次检查以下工具是否已安装：

```
python --version        # 期望：Python 3.12.x
git --version           # 期望：任意版本号
docker --version        # 期望：任意版本号
docker ps               # 期望：命令能执行（Docker 守护进程在运行）
```

**判断逻辑：**
- python 版本不是 3.12.x → 告诉我去 https://www.python.org/downloads/ 下载 3.12，安装时勾选"Add python.exe to PATH"，装完让我重新打开 opencode 再粘贴这段提示词
- git 未安装 → 告诉我去 https://git-scm.com/download/win 下载安装，一路 Next
- docker 未安装或 docker ps 报错 → 告诉我去 https://www.docker.com/products/docker-desktop/ 安装 Docker Desktop，安装后重启电脑，重启后桌面右下角会有鲸鱼图标，再重新开始安装
- 全部通过 → 继续阶段 2

---

## 阶段 2：下载项目

问我：
> 老师提供的项目地址是什么？（GitHub 链接，格式类似 https://github.com/xxx/xxx）

等我回答后执行：

```
d:
mkdir novels
cd novels
git clone [我提供的地址]
cd 众生界
dir
```

验证：看到 `core/`、`modules/`、`tools/`、`config/` 等目录 → 成功。

失败情况处理：
- 网络超时 → 建议我使用手机热点或挂代理后重试
- 仓库不存在 → 让我确认老师给的地址是否正确

---

## 阶段 3：安装 Python 依赖

在项目目录内执行：

```
cd /d D:\novels\众生界
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

预计耗时 5-15 分钟。等命令完成后检查最后几行，看到 `Successfully installed` → 成功。

常见失败：
- `No module named pip` → 执行 `python -m ensurepip --upgrade`
- 某个包安装失败 → 单独执行 `pip install [包名] -i https://pypi.tuna.tsinghua.edu.cn/simple`
- MSVC 编译错误（Windows 特有）→ 告诉我需要安装 Visual Studio Build Tools，引导我去下载

---

## 阶段 4：下载 BGE-M3 语言模型（约 2.3 GB）

```
set HF_ENDPOINT=https://hf-mirror.com
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3'); print('BGE-M3 下载完成')"
```

预计耗时 10-30 分钟，取决于网速。

看到 `BGE-M3 下载完成` → 成功。

失败情况：
- 下载中途断开 → 重新执行同样命令，会断点续传
- hf-mirror 也超时 → 换用 `set HF_ENDPOINT=https://mirror.sjtu.edu.cn/hugging-face-models` 再试
- 提示磁盘空间不足 → 告诉我需要至少 3 GB 可用空间，换个磁盘

---

## 阶段 5：配置 Docker 镜像加速并启动 Qdrant

**5.1 检查 Qdrant 是否已在运行**

```
docker ps --filter name=qdrant
```

如果看到 `qdrant` 容器且状态是 `Up` → 跳到阶段 6，Qdrant 已经在运行。

**5.2 配置镜像加速（国内网络必做）**

告诉我：
> 请打开 Docker Desktop → 右上角齿轮图标 → Docker Engine → 在 JSON 配置里加入以下内容，然后点 Apply & Restart，等鲸鱼图标变绿（约 30 秒）：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ]
}
```

等我确认 Docker 重启完成后继续。

**5.3 拉取 Qdrant 镜像**

```
docker pull qdrant/qdrant
```

卡住超过 3 分钟没进度 → 说明镜像加速没生效，让我重新确认步骤 5.2。

**5.4 创建数据目录并启动**

```
mkdir D:\qdrant_data
docker run -d --name qdrant --restart unless-stopped -p 6333:6333 -p 6334:6334 -v D:\qdrant_data:/qdrant/storage qdrant/qdrant
docker ps --filter name=qdrant
```

看到 qdrant 状态是 `Up` → 成功。

验证（可选）：告诉我在浏览器访问 `http://localhost:6333/dashboard`，看到界面说明数据库正常。

---

## 阶段 6：配置 API Key

问我：
> 请提供你的 Claude API Key（格式：sk-ant-api03-...）。老师会统一提供，妥善保管，不要告诉别人。

等我提供后执行：

```
claude config set api-key [我提供的 API Key]
```

然后问我：
> 你是否也安装了 opencode？（你现在就是在用 opencode，所以需要也为 opencode 配置，回答"是"或"否"）

如果我说是：
```
opencode config set anthropic-api-key [我提供的 API Key]
```

---

## 阶段 7：安装技能包（Skills）

问我：
> 老师提供的技能包 ZIP 文件放在哪里了？请告诉我完整路径，比如 D:\Downloads\众生界技能包.zip

等我回答后执行：

```
mkdir C:\Users\%USERNAME%\.agents\skills
```

然后解压 ZIP 到技能目录。使用 PowerShell 执行：

```powershell
Expand-Archive -Path "[我提供的路径]" -DestinationPath "C:\Users\$env:USERNAME\.agents\skills" -Force
```

验证：

```
dir C:\Users\%USERNAME%\.agents\skills\
```

看到 `novelist-canglan`、`novel-workflow`、`novelist-evaluator` 等文件夹 → 成功。

如果 ZIP 内有一层嵌套目录（解压后是 `skills\novelist-canglan\` 而不是直接 `novelist-canglan\`），告诉我并手动处理目录层级。

---

## 阶段 8：创建并配置 config.json

**8.1 问我：**
> 你的小说叫什么名字？（比如：天道余烬）

> 你的力量境界体系是什么？从低到高列出所有境界，用中文逗号分隔。（比如：觉醒期,凝气期,通脉期,融道期,天道期）

等我回答后在项目目录执行：

```
cd /d D:\novels\众生界
copy config.example.json config.json
```

然后用 Python 脚本修改 config.json（避免手动编辑出错）：

```python
import json, re

with open('config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# 修改小说名
cfg['worldview']['current_world'] = '[我的小说名]'

# 修改境界体系
realms = [r.strip() for r in '[我的境界列表]'.split(',')]
cfg['validation']['realm_order'] = realms

with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)

print('config.json 修改完成')
print('当前世界观:', cfg['worldview']['current_world'])
print('境界体系:', cfg['validation']['realm_order'])
```

把脚本里 `[我的小说名]` 和 `[我的境界列表]` 替换成我实际回答的内容后执行。

---

## 阶段 9：初始化数据库

```
cd /d D:\novels\众生界
python tools/data_builder.py --init
```

看到 `初始化完成` 或 `collections created` → 成功。

然后：

```
python tools/build_all.py
```

看到目录结构创建完成的提示 → 成功。

---

## 阶段 10：提炼外部小说库（可选但强烈建议）

问我：
> 你有没有准备好一些 TXT 或 EPUB 格式的小说文件用于提炼？（这些文件会被系统学习，提升写作质量）
> 如果有，告诉我文件夹路径（比如 D:\小说资源\）；如果没有，回答"跳过"。

如果我提供了路径：

首先在 config.json 里配置路径（用 Python 脚本）：

```python
import json

with open('config.json', 'r', encoding='utf-8') as f:
    cfg = json.load(f)

# 根据 config 结构添加外部资源路径
if 'external_resources' not in cfg:
    cfg['external_resources'] = {}
cfg['external_resources']['novel_library_path'] = '[我提供的路径]'

with open('config.json', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
print('外部资源路径已配置')
```

然后执行提炼（可能需要几十分钟）：

```
python tools/unified_extractor.py --dimensions case
python tools/unified_extractor.py --dimensions technique
python tools/unified_extractor.py --status
```

如果我选择跳过：告诉我系统可以正常启动，但写手参考材料会少，写作质量可能偏通用，之后有资源时随时可以补充。

---

## 阶段 11：验证环境

执行完整验证：

```
cd /d D:\novels\众生界
python tools/data_builder.py --status
```

确认各 collection 已创建。然后运行一次基础测试：

```
python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5
```

看到 `passed` 字样 → 环境基本正常。

---

## 阶段 12：启动 Claude Code，进行第一次对话

告诉我：
> 安装完成！现在请打开一个新的命令提示符窗口，执行以下命令启动 Claude Code：

```
d:
cd novels\众生界
claude
```

> 进入对话后，输入以下内容测试：

```
你好，请告诉我当前项目的小说名称是什么。
```

> Claude Code 应该能读出 config.json 里配置的小说名。如果正常回复，安装成功！

> 然后可以试试写第一章：

```
使用 novel-workflow，帮我写第一章，主角是[你的主角名字]，这章我想展示他[你想写的情节]。
```

---

## 安装完成后的注意事项

每次开电脑后需要确认 Qdrant 在运行：
```
docker ps --filter name=qdrant
```
如果没有 → `docker start qdrant`

进入项目目录启动 Claude Code：
```
d:
cd novels\众生界
claude
```

遇到问题可以再次询问我（这个 opencode 对话窗口），我会帮你排查。

---

**现在开始，请先执行阶段 1：检查基础环境。**

---

（提示词结束）
