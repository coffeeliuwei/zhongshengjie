"""
力量体系代价提取器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from power_cost_extractor import (
    PowerCostExtractor as _PowerCostExtractor,
    extract_power_costs,
    generate_cost_template,
)


class PowerCostExtractor(_PowerCostExtractor):
    """力量体系代价提取器（代理）"""

    pass


__all__ = ["PowerCostExtractor", "extract_power_costs", "generate_cost_template"]
