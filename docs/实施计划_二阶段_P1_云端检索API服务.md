# 实施计划 P1：云端检索 API 服务

> 本任务遵循 AGENTS.md v1.1 + docs/opencode_dev_protocol_20260420.md v1
> 涉及配置/文件/导入的报告必须完成 Phase 0-3 验证流程
> 与 docs/系统架构.md 冲突时，以系统架构.md 为准

---

## 任务目标

在项目根目录新建 `zsj-api/` 子目录，写入云端检索 API 服务所需的 3 个文件，供后续构建 Docker 镜像并部署到阿里云 SAE。

**本计划对应实训指导书第五步 5.1 节「准备检索 API 代码」。**
完成本计划后，回到实训指导书继续执行 5.2（开通 ACR）→ 5.3（Docker 构建推送）→ 5.4（SAE 创建）。

> ⚠️ **对照现行阿里云（与实训指导书第五步修正一致）**：① ACR 镜像仓库与 SAE 应用**必须同地域**——自 2026-02-01 起 SAE 不再支持跨地域拉取 ACR 个人版镜像，本项目统一用 `cn-hangzhou`（镜像地址前缀 `registry-vpc.cn-hangzhou...`）。② 现行 SAE 2.0 控制台创建应用要先选 **轻量版/标准版**，再填镜像地址。详见实训指导书 5.3／5.5 的 ⚠️ 提示。

---

## 前置条件

- 已完成实训指导书第一步至第四步（注册阿里云、VPC、ECS+Qdrant、OSS）
- 本机 Python 环境：`E:\anaconda3\envs\python13\python.exe`
- 本机已安装 Docker Desktop（用于 5.3 节构建和推送镜像）

---

## 文件分发规则

| 目标路径 | 操作 | 说明 |
|---------|------|------|
| `zsj-api/main.py` | **新建** | FastAPI 检索服务主程序，运行在 SAE 容器内 |
| `zsj-api/requirements.txt` | **新建** | Python 依赖声明，构建镜像时安装 |
| `zsj-api/Dockerfile` | **新建** | 容器镜像构建文件 |

> 注意：`zsj-api/` 目录存放的是独立微服务代码，不在众生界主 Python 包结构中（无 `__init__.py`），部署到 SAE 后独立运行，不通过本机 Python 环境执行。

---

## 实施步骤

### Step 1：创建目录

```powershell
cd D:\动画\众生界
mkdir zsj-api
```

---

### Step 2：创建 `zsj-api/main.py`

完整内容如下，**直接写入**，不需要修改任何占位符（运行时通过 SAE 环境变量注入配置）：

```python
"""
众生界云端检索 API 服务
运行在阿里云 SAE，通过 API 网关对外提供检索服务。
环境变量（SAE 控制台注入）：
  QDRANT_HOST     - ECS 内网 IP，如 192.168.1.58
  QDRANT_PORT     - 默认 6333
  QDRANT_API_KEY  - Qdrant 密码
"""
import os
import time
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Filter, FieldCondition, MatchValue,
    NamedVector, NamedSparseVector, SparseVector,
)

QDRANT_HOST    = os.environ["QDRANT_HOST"]
QDRANT_PORT    = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]

logging.basicConfig(level="INFO", format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zsj-api")

app    = FastAPI(title="众生界检索 API", version="1.0.0")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, api_key=QDRANT_API_KEY)


# ── 请求数据模型 ──────────────────────────────────────────────────────────────

class DenseSearchReq(BaseModel):
    vector: list[float]       = Field(..., description="本地 BGE-M3 生成的查询向量")
    collection: str           = Field(..., description="目标 collection 名称")
    top_k: int                = Field(5, ge=1, le=50)
    score_threshold: float    = Field(0.0, ge=0.0, le=1.0)
    filter_field: Optional[str] = None
    filter_value: Optional[str] = None
    vector_name: Optional[str]  = Field(None, description="多向量时指定，如 dense")


class SparseVec(BaseModel):
    indices: list[int]
    values:  list[float]


class HybridSearchReq(BaseModel):
    dense_vector:  list[float]
    sparse_vector: Optional[SparseVec] = None
    collection:    str
    top_k:         int = Field(5, ge=1, le=50)
    filter_field:  Optional[str] = None
    filter_value:  Optional[str] = None


# ── API 接口 ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """健康检查：API 网关和 SAE 存活探针都会调用此接口"""
    try:
        qdrant.get_collections()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


@app.get("/collections")
def list_collections():
    """列出所有 collection 及其点数，用于验收测试"""
    cols = qdrant.get_collections().collections
    result = []
    for c in cols:
        try:
            info = qdrant.get_collection(c.name)
            result.append({"name": c.name, "points_count": info.points_count})
        except Exception:
            result.append({"name": c.name, "points_count": -1})
    return {"collections": result}


@app.post("/search/dense")
def search_dense(req: DenseSearchReq):
    """密集向量检索（适用于 case_library_v2 等单向量 collection）"""
    qfilter = None
    if req.filter_field and req.filter_value:
        qfilter = Filter(must=[FieldCondition(
            key=req.filter_field,
            match=MatchValue(value=req.filter_value),
        )])
    t0 = time.time()
    try:
        if req.vector_name:
            results = qdrant.search(
                collection_name=req.collection,
                query_vector=NamedVector(name=req.vector_name, vector=req.vector),
                limit=req.top_k, score_threshold=req.score_threshold,
                query_filter=qfilter, with_payload=True,
            )
        else:
            results = qdrant.search(
                collection_name=req.collection,
                query_vector=req.vector,
                limit=req.top_k, score_threshold=req.score_threshold,
                query_filter=qfilter, with_payload=True,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    latency = round((time.time() - t0) * 1000, 1)
    logger.info(f"dense | {req.collection} top_k={req.top_k} {latency}ms")
    return {
        "results": [{"id": r.id, "score": r.score, "payload": r.payload} for r in results],
        "latency_ms": latency,
    }


@app.post("/search/hybrid")
def search_hybrid(req: HybridSearchReq):
    """混合检索（dense + sparse RRF 融合，适用于 writing_techniques_v2）"""
    qfilter = None
    if req.filter_field and req.filter_value:
        qfilter = Filter(must=[FieldCondition(
            key=req.filter_field,
            match=MatchValue(value=req.filter_value),
        )])
    t0 = time.time()
    try:
        dense_res = qdrant.search(
            collection_name=req.collection,
            query_vector=NamedVector(name="dense", vector=req.dense_vector),
            limit=req.top_k * 2, query_filter=qfilter, with_payload=True,
        )
        sparse_res = []
        if req.sparse_vector:
            sparse_res = qdrant.search(
                collection_name=req.collection,
                query_vector=NamedSparseVector(
                    name="sparse",
                    vector=SparseVector(
                        indices=req.sparse_vector.indices,
                        values=req.sparse_vector.values,
                    ),
                ),
                limit=req.top_k * 2, query_filter=qfilter, with_payload=True,
            )
        # RRF 融合（Reciprocal Rank Fusion）：dense 权重 0.7，sparse 权重 0.3
        scores:   dict = {}
        payloads: dict = {}
        for rank, r in enumerate(dense_res):
            scores[r.id]   = scores.get(r.id, 0) + 0.7 / (rank + 60)
            payloads[r.id] = r.payload
        for rank, r in enumerate(sparse_res):
            scores[r.id] = scores.get(r.id, 0) + 0.3 / (rank + 60)
            if r.id not in payloads:
                payloads[r.id] = r.payload
        fused = sorted(scores.items(), key=lambda x: -x[1])[:req.top_k]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    latency = round((time.time() - t0) * 1000, 1)
    return {
        "results": [{"id": uid, "score": s, "payload": payloads.get(uid, {})} for uid, s in fused],
        "latency_ms": latency,
    }
```

---

### Step 3：创建 `zsj-api/requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
qdrant-client==1.11.3
pydantic==2.9.2
```

---

### Step 4：创建 `zsj-api/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 先复制依赖文件再安装，利用 Docker 层缓存（代码改动不重装依赖）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 测试验收（4 阶段）

### Stage 1：聚焦测试 — 文件完整性

```powershell
cd D:\动画\众生界

# 确认三个文件都存在
ls zsj-api\

# 预期输出：Dockerfile  main.py  requirements.txt

# Python 语法检查
E:\anaconda3\envs\python13\python.exe -c `
    "import ast; ast.parse(open('zsj-api/main.py').read()); print('语法检查通过')"
```

### Stage 2：邻居测试 — 依赖声明一致性

```powershell
# 检查 requirements.txt 中的包名与 main.py 中的 import 一致
# fastapi ← from fastapi import ...
# uvicorn ← CMD 里调用
# qdrant-client ← from qdrant_client import ...
# pydantic ← from pydantic import ...
E:\anaconda3\envs\python13\python.exe -c "
reqs = open('zsj-api/requirements.txt').read()
for pkg in ['fastapi', 'uvicorn', 'qdrant-client', 'pydantic']:
    assert pkg in reqs, f'缺失依赖：{pkg}'
print('依赖声明验证通过')
"
```

### Stage 3：全量测试 — Dockerfile 语法

```powershell
# 如果已安装 Docker Desktop，验证 Dockerfile 语法
docker build --no-cache -t zsj-api-test:local zsj-api\ 2>&1 | Tee-Object docs\m7_artifacts\P1_stage3_build.txt
```

### Stage 4：判定

| 检查项 | 通过标准 |
|--------|---------|
| `zsj-api/` 目录存在 | `ls zsj-api\` 返回 3 个文件 |
| Python 语法检查 | 无 SyntaxError |
| 依赖完整 | 4 个包均在 requirements.txt |
| Docker 构建（可选） | `Successfully built ...` |

---

## 完成后的下一步

回到实训指导书 **第五步 5.2 节**，继续执行云控制台操作（开通 ACR → 创建镜像仓库），然后按 5.3 节执行 `docker login` / `docker build` / `docker push`。
