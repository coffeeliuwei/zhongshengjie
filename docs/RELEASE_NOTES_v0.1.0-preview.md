# 众生界 v0.1.0-preview 发布说明

**发布日期**:2026-04-20(Asia/Shanghai)
**版本定位**:首个公开预览版 — 面向学生、写作爱好者、AI 辅助创作研究者

---

## 🎯 这是什么

**众生界**是一个**AI 辅助小说创作系统**,基于 Anthropic Harness 多智能体架构构建:

- 🖊️ **5 位专业作家** + 1 位审核评估师协作创作
- 🔍 **四层专家架构**:方法论 → 统一 API → 技法/案例库 → 世界观适配
- 🧠 **BGE-M3 混合检索**:Dense + Sparse 向量融合,章节经验自动沉淀
- 💬 **对话式工作流**:意图识别 / 状态管理 / 错误恢复 / 用户反馈闭环
- 📚 **场景契约系统**:12 大一致性规则,解决多作家并行创作拼接冲突

---

## ✨ 预览版包含

- 核心工作流(大纲 → 章节生成 → 评估 → 反馈)完整可跑
- 9 个 Skill(5 写手 + 评估师 + 共享组件 + 技法检索 + 世界观生成)
- 统一提炼引擎(11 维度并行提取)
- Qdrant 向量检索 + 章节经验日志
- 自动类型发现(场景/力量/势力/技法 4 大类型、28 种场景子类型)
- 基线测试套件:506 passed

## ⚠️ 已知限制

| 限制 | 说明 |
|------|------|
| 🧬 世界观耦合 | 当前系统面向"众生界"设定设计,其他小说需手动替换配置 |
| 📦 大文件不推 | 案例库数据(~113K 文件)和 Qdrant 向量数据(~20G)需自行构建 |
| 🧪 非 CLI 优先 | 推荐在 Claude Code / OpenCode 环境下操作,独立 CLI 仍在完善中 |
| 🔧 配置路径 | 需按本地目录修改 `config.json`,详见 README |
| 🪟 Windows 首选 | 主要在 Windows 11 + PowerShell/Bash 下验证过,Linux/Mac 可跑但测试较少 |

---

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/coffeeliuwei/zhongshengjie.git
cd zhongshengjie

# 2. 装依赖
pip install -r requirements.txt

# 3. 启 Qdrant
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# 4. 配置
cp config.example.json config.json   # 编辑路径字段

# 5. 安装 Skills
cp -r skills/* ~/.agents/skills/      # Linux/Mac
# Copy-Item -Recurse skills/* $env:USERPROFILE\.agents\skills\  # Windows

# 6. 构建数据系统
python tools/build_all.py

# 7. 进入系统
python -m core
```

完整指引见 [README.md](../README.md)。

---

## 🔭 v2 预告(开发中)

本预览版是 **v1 最后一个稳定版本**。v2 正在开发,核心改造:

- **三方协商**:鉴赏师 + 评估师 + 作者共同拍板单章创意契约
- **创意锁定**:`preserve_list` 机制保证采纳的创意不被后续评审覆盖
- **派单监工**:鉴赏师从"选择器"升级为"创意注入器 + 派单监工"
- **豁免评估**:评估师按契约 `preserve_list` 豁免对应维度
- **推翻事件回流**:作者手动推翻双引擎判断时自动写入 memory_points
- **M8 多小说解耦**:系统可写任意小说(远期)

预计发布:**v1.0.0**(v2 闭合后,数周内)

---

## 🐛 报告问题 / 反馈

- GitHub Issues:https://github.com/coffeeliuwei/zhongshengjie/issues
- 欢迎 Pull Request

单机项目,所有数据保留本地。学生/爱好者可自由多次试错,升级版本直接 `git pull` 或重下 ZIP 即可。

---

## 📜 许可证

MIT License — 详见 [LICENSE](../LICENSE)

---

## 🙏 致谢

- Anthropic Harness 架构
- Qdrant 向量数据库
- BGE-M3 嵌入模型(BAAI)
- Claude Code / OpenCode 工具链
