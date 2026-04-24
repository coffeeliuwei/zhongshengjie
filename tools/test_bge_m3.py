#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test BGE-M3 model loading and encoding in offline mode"""

import os

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from FlagEmbedding import BGEM3FlagModel

print("Loading BGE-M3 model (offline mode)...")
model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")
print("Model loaded successfully!")

# Test encoding
print("Testing encoding...")
output = model.encode(
    ["test query"], return_dense=True, return_sparse=True, return_colbert_vecs=True
)
print(f"Dense dim: {len(output['dense_vecs'][0])}")
print(f"Sparse keys: {len(output['lexical_weights'][0])}")
print("All tests passed!")
