#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

sys.stdout.reconfigure(encoding="utf-8")

from sentence_transformers import SentenceTransformer

print("Loading BGE-M3 via sentence-transformers...")
model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
print("Model loaded successfully!")

# Test encoding
test_texts = ["测试文本", "Test text"]
vectors = model.encode(test_texts)
print(f"Vector dimension: {len(vectors[0])}")
print("Test passed!")
