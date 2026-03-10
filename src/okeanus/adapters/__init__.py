"""Source adapters -- connectors for ocean data feeds."""

from okeanus.adapters.ais_stream import AisStreamAdapter
from okeanus.adapters.argovis import ArgovisAdapter
from okeanus.adapters.base import BaseAdapter
from okeanus.adapters.cmems import CmemsAdapter
from okeanus.adapters.erddap import ErddapAdapter
from okeanus.adapters.gbif import GbifAdapter
from okeanus.adapters.global_fishing_watch import GlobalFishingWatchAdapter
from okeanus.adapters.marine_regions import MarineRegionsAdapter
from okeanus.adapters.ndbc import NdbcAdapter
from okeanus.adapters.noaa_coops import NoaaCoopsAdapter
from okeanus.adapters.obis import ObisAdapter
from okeanus.adapters.onc import OncAdapter
from okeanus.adapters.open_sanctions import OpenSanctionsAdapter
from okeanus.adapters.wdpa import WdpaAdapter
from okeanus.adapters.worms import WormsAdapter

__all__ = [
    "AisStreamAdapter",
    "ArgovisAdapter",
    "BaseAdapter",
    "CmemsAdapter",
    "ErddapAdapter",
    "GbifAdapter",
    "GlobalFishingWatchAdapter",
    "MarineRegionsAdapter",
    "NdbcAdapter",
    "NoaaCoopsAdapter",
    "ObisAdapter",
    "OncAdapter",
    "OpenSanctionsAdapter",
    "WdpaAdapter",
    "WormsAdapter",
]

# Registry mapping source names to adapter classes for dynamic lookup
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "aisstream": AisStreamAdapter,
    "argovis": ArgovisAdapter,
    "cmems": CmemsAdapter,
    "erddap": ErddapAdapter,
    "gbif": GbifAdapter,
    "gfw": GlobalFishingWatchAdapter,
    "marine_regions": MarineRegionsAdapter,
    "ndbc": NdbcAdapter,
    "noaa_coops": NoaaCoopsAdapter,
    "obis": ObisAdapter,
    "onc": OncAdapter,
    "opensanctions": OpenSanctionsAdapter,
    "wdpa": WdpaAdapter,
    "worms": WormsAdapter,
}
