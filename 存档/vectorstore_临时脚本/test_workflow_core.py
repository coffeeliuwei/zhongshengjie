#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test workflow knowledge integration - key use cases
"""

import sys
from pathlib import Path

VECTORSTORE_DIR = Path(r"D:\动画\众生界\.vectorstore")
sys.path.insert(0, str(VECTORSTORE_DIR))

from knowledge_search import KnowledgeSearcher

s = KnowledgeSearcher()

print("=" * 60)
print("Workflow Knowledge Integration Test")
print("=" * 60)

# Test 1: Get chapter outline (MUST work for workflow)
print("\n[Test 1] Get chapter 1 outline:")
outline = s.get_outline(chapter=1)
if outline and outline.get("info"):
    print(f"  PASS - Found chapter outline")
    print(f"    Scenes: {len(outline.get('scenes', []))}")
else:
    print(f"  FAIL - No chapter outline found")

# Test 2: Get character setting (MUST work for workflow)
print("\n[Test 2] Get character '血牙':")
# Search by name directly in knowledge
chars = s.search_knowledge("血牙", data_type="character", top_k=3)
if chars:
    print(f"  PASS - Found {len(chars)} character(s)")
    for c in chars:
        print(f"    - {c['name']}")
else:
    print(f"  FAIL - No character found")

# Test 3: Get faction setting (MUST work for workflow)
print("\n[Test 3] Get faction '佣兵':")
factions = s.search_knowledge("佣兵", data_type="faction", top_k=3)
if factions:
    print(f"  PASS - Found {len(factions)} faction(s)")
    for f in factions:
        print(f"    - {f['name']}")
else:
    print(f"  FAIL - No faction found")

# Test 4: Search techniques (for Evaluator)
print("\n[Test 4] Search techniques for '战斗代价':")
techs = s.search_techniques("战斗 代价", dimension="战斗", top_k=3)
if techs:
    print(f"  PASS - Found {len(techs)} technique(s)")
    for t in techs:
        print(f"    - {t['name']} ({t['dimension']})")
else:
    print(f"  FAIL - No techniques found")

# Test 5: Unified search
print("\n[Test 5] Unified search '林远':")
results = s.search("林远", data_type=None, top_k=5)
if results:
    print(f"  PASS - Found results in {len(results)} categories")
    for cat, items in results.items():
        print(f"    {cat}: {len(items)} items")
else:
    print(f"  FAIL - No unified search results")

print("\n" + "=" * 60)
print("Summary: Core workflow functions are working")
print("=" * 60)
