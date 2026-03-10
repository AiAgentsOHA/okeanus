"""Source adapters -- connectors for ocean data feeds."""

from okeanus.adapters.base import BaseAdapter
from okeanus.adapters.cmems import CmemsAdapter
from okeanus.adapters.marine_regions import MarineRegionsAdapter
from okeanus.adapters.worms import WormsAdapter

__all__ = [
    "BaseAdapter",
    "CmemsAdapter",
    "MarineRegionsAdapter",
    "WormsAdapter",
]
