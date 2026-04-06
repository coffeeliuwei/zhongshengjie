#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

from FlagEmbedding import BGEM3FlagModel

print("Loading BGE-M3...")
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, devices=["cpu"])
print("Model loaded successfully!")

# Test encoding
test_texts = ["测试文本", "Test text"]
embeddings = model.encode(test_texts, return_dense=True)
print(f"Vector dimension: {len(embeddings['dense_vecs'][0])}")
print("Test passed!")
