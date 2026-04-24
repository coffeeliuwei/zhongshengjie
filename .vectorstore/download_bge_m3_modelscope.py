#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用ModelScope下载BGE-M3模型
"""

import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# 设置缓存目录到E盘
os.environ["MODELSCOPE_CACHE"] = "E:/modelscope_cache"

print("=" * 60)
print("使用ModelScope下载BGE-M3")
print("=" * 60)
print(f"缓存目录: {os.environ['MODELSCOPE_CACHE']}")
print()

from modelscope import snapshot_download

print("开始下载 BGE-M3...")
print("模型大小约 2GB，请耐心等待...")
print()

# 下载模型
model_dir = snapshot_download(
    "Xorbits/bge-m3",  # ModelScope模型ID
    cache_dir="E:/modelscope_cache",
    revision="master",
)

print()
print("=" * 60)
print("下载完成!")
print("=" * 60)
print(f"模型路径: {model_dir}")

# 测试加载
print()
print("测试加载模型...")
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(model_dir, trust_remote_code=True)

test_texts = ["测试文本", "Test text"]
vectors = model.encode(test_texts)
print(f"向量维度: {len(vectors[0])}")
print()
print("模型测试通过！")
print()
print(f"请在代码中使用模型路径: {model_dir}")
