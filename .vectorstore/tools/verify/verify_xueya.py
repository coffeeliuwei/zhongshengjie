# -*- coding: utf-8 -*-
"""验证血牙血脉信息"""

import sys

sys.stdout.reconfigure(encoding="utf-8")
from workflow import NovelWorkflow
import json

wf = NovelWorkflow()

print("=== 验证血牙血脉信息 ===")
results = wf.search_novel("血牙", entity_type="角色", top_k=3)
for r in results:
    print(f"名称: {r['name']}")
    print(f"类型: {r['type']}")
    # properties是整个实体对象的JSON
    props = json.loads(r.get("properties", "{}"))
    # props包含: id, 名称, 类型, 属性
    attrs = props.get("属性", {})
    print(f"势力: {attrs.get('势力')}")
    print(f"初始派别: {attrs.get('初始派别')}")
    print(f"初始能力: {attrs.get('初始能力')}")
    print(f"得分: {r['score']:.3f}")
    print()
