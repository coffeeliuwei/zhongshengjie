# Qdrant Docker迁移指南

## 当前状态

- 本地模式：316,865向量点（92.6%）
- 问题：scroll遍历31万点超时
- 解决：迁移到Docker Qdrant server

---

## 迁移步骤

### Step 1: 启用Virtual Machine Platform

**管理员权限运行PowerShell：**

```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

或在 **控制面板 → 程序 → 启用或关闭Windows功能 → Virtual Machine Platform**

### Step 2: 重启电脑

**必须重启才能生效！**

### Step 3: 启动Docker Desktop

重启后，启动Docker Desktop：
- 路径：`C:\Program Files\Docker\Docker\Docker Desktop.exe`
- 等待Docker图标显示为绿色（Running状态）

### Step 4: 启动Qdrant容器

运行启动脚本：

```powershell
cd D:\动画\众生界\.case-library\scripts
.\start_qdrant_docker.ps1
```

或手动执行：

```powershell
docker run -d -p 6333:6333 -p 6334:6334 `
    -v "D:\动画\众生界\.vectorstore\qdrant_docker:/qdrant/storage" `
    --name qdrant-server `
    qdrant/qdrant
```

验证：

```powershell
docker ps
curl http://localhost:6333/collections
```

### Step 5: 同步案例到Docker Qdrant

```powershell
cd D:\动画\众生界\.case-library\scripts

# Docker模式完整同步（推荐）
python sync_to_qdrant.py --docker --no-resume

# 或测试同步（先同步1000个）
python sync_to_qdrant.py --docker --limit 1000

# 查看状态
python sync_to_qdrant.py --docker --stats
```

### Step 6: 验证同步完成

```powershell
# 查看Qdrant Dashboard
Start-Process "http://localhost:6333/dashboard"

# 检查向量点数量
python sync_to_qdrant.py --docker --stats
```

---

## 预期结果

| 指标 | 本地模式 | Docker模式 |
|------|----------|------------|
| scroll遍历 | 1-2分钟 | **<5秒** |
| 同步速度 | 慢/超时 | **快/稳定** |
| 向量点上限 | ~2万 | **数百万** |
| 适合生产 | ❌ | ✅ |

---

## 已修改文件

1. `sync_to_qdrant.py` - 新增 `--docker` 参数
2. `start_qdrant_docker.ps1` - Docker启动脚本

---

## 常用命令

```powershell
# 查看容器状态
docker ps -a

# 停止容器
docker stop qdrant-server

# 重启容器
docker restart qdrant-server

# 查看容器日志
docker logs qdrant-server

# 进入容器
docker exec -it qdrant-server bash

# 删除容器（会清除数据）
docker rm -f qdrant-server
```

---

## 数据存储位置

- **Docker Qdrant数据**: `D:\动画\众生界\.vectorstore\qdrant_docker`
- **本地Qdrant数据**: `D:\动画\众生界\.vectorstore\qdrant` (可删除)

---

执行完成后，项目将具备生产级向量数据库，为后续重构奠定基础。