#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

# 设置环境变量（当前进程生效）
# 使用配置加载器获取 HuggingFace 缓存目录
sys.path.insert(0, str(__file__).rsplit(".vectorstore", 1)[0])
from core.config_loader import get_hf_cache_dir

hf_cache = get_hf_cache_dir()
if hf_cache:
    os.environ["HF_HOME"] = hf_cache
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

sys.stdout.reconfigure(encoding="utf-8")

print("=" * 50)
print("下载 BGE-M3 模型")
print("=" * 50)
print(f"缓存目录: {os.environ['HF_HOME']}")
print(f"镜像地址: {os.environ['HF_ENDPOINT']}")
print()

from sentence_transformers import SentenceTransformer

print("正在下载 BGE-M3 (约2GB)...")
model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
print("模型加载成功！")

# 测试
test_texts = ["测试文本", "Test text for BGE-M3"]
vectors = model.encode(test_texts)
print(f"\n向量维度: {len(vectors[0])}")
print("测试通过！")
