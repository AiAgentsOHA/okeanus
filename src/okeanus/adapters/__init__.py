"""Source adapters -- connectors for ocean data feeds."""

from okeanus.adapters.ais_stream import AisStreamAdapter
from okeanus.adapters.argovis import ArgovisAdapter
from okeanus.adapters.argopy_adapter import ArgopyAdapter
from okeanus.adapters.base import BaseAdapter
from okeanus.adapters.boem_wind import BoemWindAdapter
from okeanus.adapters.bold import BoldAdapter
from okeanus.adapters.clav_iuu import ClavIuuAdapter
from okeanus.adapters.cmems import CmemsAdapter
from okeanus.adapters.earthaccess_adapter import EarthaccessAdapter
from okeanus.adapters.ecmwf_open import EcmwfOpenAdapter
from okeanus.adapters.emodnet_biology import EmodnetBiologyAdapter
from okeanus.adapters.erddap import ErddapAdapter
from okeanus.adapters.fao_fisheries import FaoFisheriesAdapter
from okeanus.adapters.fishbase import FishBaseAdapter
from okeanus.adapters.gbif import GbifAdapter
from okeanus.adapters.global_fishing_watch import GlobalFishingWatchAdapter
from okeanus.adapters.global_mangrove import GlobalMangroveAdapter
from okeanus.adapters.haedat import HaedatAdapter
from okeanus.adapters.habsos import HabsosAdapter
from okeanus.adapters.ices import IcesAdapter
from okeanus.adapters.imb_piracy import ImbPiracyAdapter
from okeanus.adapters.inaturalist import INaturalistAdapter
from okeanus.adapters.interridge import InterRidgeAdapter
from okeanus.adapters.marine_debris import MarineDebrisAdapter
from okeanus.adapters.marine_heatwave import MarineHeatwaveAdapter
from okeanus.adapters.marine_regions import MarineRegionsAdapter
from okeanus.adapters.ndbc import NdbcAdapter
from okeanus.adapters.noaa_coops import NoaaCoopsAdapter
from okeanus.adapters.noaa_deep_coral import NoaaDeepCoralAdapter
from okeanus.adapters.noaa_storm_events import NoaaStormEventsAdapter
from okeanus.adapters.noaa_wrecks import NoaaWrecksAdapter
from okeanus.adapters.nsidc_sea_ice import NsidcSeaIceAdapter
from okeanus.adapters.obis import ObisAdapter
from okeanus.adapters.obis_seamap import ObisSeamapAdapter
from okeanus.adapters.ocean_tracking import OceanTrackingAdapter
from okeanus.adapters.onc import OncAdapter
from okeanus.adapters.opendap import OpendapAdapter
from okeanus.adapters.open_sanctions import OpenSanctionsAdapter
from okeanus.adapters.pangaea import PangaeaAdapter
from okeanus.adapters.psmsl import PsmslAdapter
from okeanus.adapters.reef_life_survey import ReefLifeSurveyAdapter
from okeanus.adapters.sealifebase import SeaLifeBaseAdapter
from okeanus.adapters.thetis_mrv import ThetisMrvAdapter
from okeanus.adapters.usgs_quakes import UsgsQuakesAdapter
from okeanus.adapters.wdpa import WdpaAdapter
from okeanus.adapters.worms import WormsAdapter

__all__ = [
    "AisStreamAdapter",
    "ArgovisAdapter",
    "ArgopyAdapter",
    "BaseAdapter",
    "BoemWindAdapter",
    "BoldAdapter",
    "ClavIuuAdapter",
    "CmemsAdapter",
    "EarthaccessAdapter",
    "EcmwfOpenAdapter",
    "EmodnetBiologyAdapter",
    "ErddapAdapter",
    "FaoFisheriesAdapter",
    "FishBaseAdapter",
    "GbifAdapter",
    "GlobalFishingWatchAdapter",
    "GlobalMangroveAdapter",
    "HaedatAdapter",
    "HabsosAdapter",
    "IcesAdapter",
    "ImbPiracyAdapter",
    "INaturalistAdapter",
    "InterRidgeAdapter",
    "MarineDebrisAdapter",
    "MarineHeatwaveAdapter",
    "MarineRegionsAdapter",
    "NdbcAdapter",
    "NoaaCoopsAdapter",
    "NoaaDeepCoralAdapter",
    "NoaaStormEventsAdapter",
    "NoaaWrecksAdapter",
    "NsidcSeaIceAdapter",
    "ObisAdapter",
    "ObisSeamapAdapter",
    "OceanTrackingAdapter",
    "OncAdapter",
    "OpendapAdapter",
    "OpenSanctionsAdapter",
    "PangaeaAdapter",
    "PsmslAdapter",
    "ReefLifeSurveyAdapter",
    "SeaLifeBaseAdapter",
    "ThetisMrvAdapter",
    "UsgsQuakesAdapter",
    "WdpaAdapter",
    "WormsAdapter",
]

# Registry mapping source names to adapter classes for dynamic lookup
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "aisstream": AisStreamAdapter,
    "argovis": ArgovisAdapter,
    "argopy": ArgopyAdapter,
    "boem_wind": BoemWindAdapter,
    "bold": BoldAdapter,
    "clav_iuu": ClavIuuAdapter,
    "cmems": CmemsAdapter,
    "earthaccess": EarthaccessAdapter,
    "ecmwf_open": EcmwfOpenAdapter,
    "emodnet_biology": EmodnetBiologyAdapter,
    "erddap": ErddapAdapter,
    "fao_fisheries": FaoFisheriesAdapter,
    "fishbase": FishBaseAdapter,
    "gbif": GbifAdapter,
    "gfw": GlobalFishingWatchAdapter,
    "global_mangrove": GlobalMangroveAdapter,
    "haedat": HaedatAdapter,
    "habsos": HabsosAdapter,
    "ices": IcesAdapter,
    "imb_piracy": ImbPiracyAdapter,
    "inaturalist": INaturalistAdapter,
    "interridge": InterRidgeAdapter,
    "marine_debris": MarineDebrisAdapter,
    "marine_heatwave": MarineHeatwaveAdapter,
    "marine_regions": MarineRegionsAdapter,
    "ndbc": NdbcAdapter,
    "noaa_coops": NoaaCoopsAdapter,
    "noaa_deep_coral": NoaaDeepCoralAdapter,
    "noaa_storm_events": NoaaStormEventsAdapter,
    "noaa_wrecks": NoaaWrecksAdapter,
    "nsidc_sea_ice": NsidcSeaIceAdapter,
    "obis": ObisAdapter,
    "obis_seamap": ObisSeamapAdapter,
    "ocean_tracking": OceanTrackingAdapter,
    "onc": OncAdapter,
    "opendap": OpendapAdapter,
    "opensanctions": OpenSanctionsAdapter,
    "pangaea": PangaeaAdapter,
    "psmsl": PsmslAdapter,
    "reef_life_survey": ReefLifeSurveyAdapter,
    "sealifebase": SeaLifeBaseAdapter,
    "thetis_mrv": ThetisMrvAdapter,
    "usgs_quakes": UsgsQuakesAdapter,
    "wdpa": WdpaAdapter,
    "worms": WormsAdapter,
}
