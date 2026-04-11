#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from knowledge_search import KnowledgeSearcher

s = KnowledgeSearcher()
r = s.search_knowledge("血脉", data_type="power", top_k=3)
print(f"Power results: {len(r)}")
for i in r:
    print(f"  - {i['name']} (ID: {i['id']})")
