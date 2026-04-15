import json, tempfile
from pathlib import Path
from unittest.mock import patch
from core.type_discovery.power_type_discoverer import PowerTypeDiscoverer
from core.type_discovery.type_discoverer import DiscoveredType

td = tempfile.mkdtemp()
tdp = Path(td)
cp = tdp / "config" / "dimensions"
cp.mkdir(parents=True)
data = {"power_types": {"修仙": {"description": "修仙体系", "keywords": ["灵气"]}, "魔法": {"description": "魔法体系", "keywords": ["魔力"]}}, "updated_at": "2025-01-01"}
(cp / "power_types.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

patcher = patch("core.type_discovery.type_discoverer.CONFIG_DIMENSIONS_DIR", cp)
patcher.start()

d = PowerTypeDiscoverer()
d.discovered_types = [
    DiscoveredType(
        name="血脉力量",
        category="power",
        keywords=["血脉", "觉醒"],
        sample_count=50,
        sample_sources=["小说1"],
        confidence=0.8,
        status="approved",
    )
]
synced = d.sync_to_config()
print(f"synced={synced}")

r = json.loads((cp / "power_types.json").read_text(encoding="utf-8"))
print(f"keys={list(r['power_types'].keys())}")
print(f"血脉力量 in config = {'血脉力量' in r['power_types']}")

patcher.stop()
