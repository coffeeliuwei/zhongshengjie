# [M5 链路 C 复测 N9 后]
import sys
from pathlib import Path
sys.path.insert(0, '.')

from core.change_detector.sync_manager_adapter import (
    SyncManagerAdapter,
    _MockWorldviewGenerator,
)

# 1. Mock 路径裸调（模拟 M5 §3.3 的失败场景）
gen = _MockWorldviewGenerator()
r1 = gen.sync_from_outline()
print(f"裸调: {r1}")
assert r1.get("synced") == 0

# 2. Mock 路径传参（模拟生产 :107 调用）
r2 = gen.sync_from_outline("总大纲.md")
print(f"传参: {r2}")
assert r2.get("synced") == 0

# 3. SyncManagerAdapter 完整 sync_to_vectorstore 路径（不真改大纲）
adapter = SyncManagerAdapter(project_root=Path("."))
adapter._worldview_generator = None  # 确保懒加载
gen_type = type(adapter._get_worldview_generator()).__name__
print(f"adapter.generator type: {gen_type}")

print("PASS · 链路 C 复测全绿")