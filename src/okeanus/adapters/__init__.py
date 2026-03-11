"""Source adapters -- connectors for ocean data feeds."""

from okeanus.adapters.ais_stream import AisStreamAdapter
from okeanus.adapters.allen_coral import AllenCoralAdapter
from okeanus.adapters.argovis import ArgovisAdapter
from okeanus.adapters.argopy_adapter import ArgopyAdapter
from okeanus.adapters.base import BaseAdapter
from okeanus.adapters.boem_wind import BoemWindAdapter
from okeanus.adapters.bold import BoldAdapter
from okeanus.adapters.clav_iuu import ClavIuuAdapter
from okeanus.adapters.cmems import CmemsAdapter
from okeanus.adapters.copernicus_dataspace import CopernicusDataspaceAdapter
from okeanus.adapters.earthaccess_adapter import EarthaccessAdapter
from okeanus.adapters.ecmwf_open import EcmwfOpenAdapter
from okeanus.adapters.emodnet_bathymetry import EmodnetBathymetryAdapter
from okeanus.adapters.emodnet_biology import EmodnetBiologyAdapter
from okeanus.adapters.emodnet_human import EmodnetHumanAdapter
from okeanus.adapters.emodnet_seabed import EmodnetSeabedAdapter
from okeanus.adapters.erddap import ErddapAdapter
from okeanus.adapters.fao_fisheries import FaoFisheriesAdapter
from okeanus.adapters.fed_register import FedRegisterAdapter
from okeanus.adapters.fishbase import FishBaseAdapter
from okeanus.adapters.gbif import GbifAdapter
from okeanus.adapters.gfs_forecast import GfsForecastAdapter
from okeanus.adapters.global_fishing_watch import GlobalFishingWatchAdapter
from okeanus.adapters.global_mangrove import GlobalMangroveAdapter
from okeanus.adapters.goaon import GoaOnAdapter
from okeanus.adapters.haedat import HaedatAdapter
from okeanus.adapters.habsos import HabsosAdapter
from okeanus.adapters.ices import IcesAdapter
from okeanus.adapters.imb_piracy import ImbPiracyAdapter
from okeanus.adapters.inaturalist import INaturalistAdapter
from okeanus.adapters.interridge import InterRidgeAdapter
from okeanus.adapters.iucn_redlist import IucnRedlistAdapter
from okeanus.adapters.marine_debris import MarineDebrisAdapter
from okeanus.adapters.marine_heatwave import MarineHeatwaveAdapter
from okeanus.adapters.marine_regions import MarineRegionsAdapter
from okeanus.adapters.movebank import MovebankAdapter
from okeanus.adapters.ndbc import NdbcAdapter
from okeanus.adapters.ngdc_tsunami import NgdcTsunamiAdapter
from okeanus.adapters.noaa_coops import NoaaCoopsAdapter
from okeanus.adapters.noaa_deep_coral import NoaaDeepCoralAdapter
from okeanus.adapters.noaa_erma import NoaaErmaAdapter
from okeanus.adapters.noaa_storm_events import NoaaStormEventsAdapter
from okeanus.adapters.noaa_wrecks import NoaaWrecksAdapter
from okeanus.adapters.nsidc_sea_ice import NsidcSeaIceAdapter
from okeanus.adapters.obis import ObisAdapter
from okeanus.adapters.obis_seamap import ObisSeamapAdapter
from okeanus.adapters.ocean_info_hub import OceanInfoHubAdapter
from okeanus.adapters.ocean_tracking import OceanTrackingAdapter
from okeanus.adapters.onc import OncAdapter
from okeanus.adapters.opendap import OpendapAdapter
from okeanus.adapters.open_sanctions import OpenSanctionsAdapter
from okeanus.adapters.orcasound import OrcasoundAdapter
from okeanus.adapters.pangaea import PangaeaAdapter
from okeanus.adapters.psmsl import PsmslAdapter
from okeanus.adapters.ram_legacy import RamLegacyAdapter
from okeanus.adapters.reef_life_survey import ReefLifeSurveyAdapter
from okeanus.adapters.seabass import SeaBassAdapter
from okeanus.adapters.sealifebase import SeaLifeBaseAdapter
from okeanus.adapters.smithsonian_volcanoes import SmithsonianVolcanoesAdapter
from okeanus.adapters.thetis_mrv import ThetisMrvAdapter
from okeanus.adapters.usgs_quakes import UsgsQuakesAdapter
from okeanus.adapters.wdpa import WdpaAdapter
from okeanus.adapters.worms import WormsAdapter

# --- Blue Economy Phase 1: Government Stats ---
from okeanus.adapters.world_bank import WorldBankAdapter
from okeanus.adapters.fred import FredAdapter
from okeanus.adapters.noaa_enow import NoaaEnowAdapter
from okeanus.adapters.eurostat_blue import EurostatBlueAdapter
from okeanus.adapters.unctad import UnctadAdapter
from okeanus.adapters.imf_commodities import ImfCommoditiesAdapter
from okeanus.adapters.ilo_maritime import IloMaritimeAdapter
from okeanus.adapters.oecd_ocean import OecdOceanAdapter

# --- Blue Economy Phase 2: Trader Layer ---
from okeanus.adapters.ssb_salmon import SsbSalmonAdapter
from okeanus.adapters.eumofa import EumofaAdapter
from okeanus.adapters.usda_gats import UsdaGatsAdapter
from okeanus.adapters.noaa_foss import NoaaFossAdapter
from okeanus.adapters.sse_indices import SseIndicesAdapter
from okeanus.adapters.bunker_index import BunkerIndexAdapter
from okeanus.adapters.oilprice_api import OilPriceApiAdapter
from okeanus.adapters.usda_bunker import UsdaBunkerAdapter

# --- Blue Economy Phase 3: Finance Layer ---
from okeanus.adapters.iati_ocean import IatiOceanAdapter
from okeanus.adapters.gcf_ocean import GcfOceanAdapter
from okeanus.adapters.verra_blue import VerraBlueAdapter
from okeanus.adapters.wba_seafood import WbaSeafoodAdapter

# --- Blue Economy Phase 4: Risk & Infrastructure ---
from okeanus.adapters.fema_nfip import FemaNfipAdapter
from okeanus.adapters.boem_offshore import BoemOffshoreAdapter
from okeanus.adapters.crown_estate import CrownEstateAdapter
from okeanus.adapters.ospar_installations import OsparInstallationsAdapter
from okeanus.adapters.iuu_index import IuuIndexAdapter

# --- Blue Economy Phase 5: Fisheries & Ecosystem Economics ---
from okeanus.adapters.sea_around_us import SeaAroundUsAdapter
from okeanus.adapters.ices_sag import IcesSagAdapter
from okeanus.adapters.fao_fishstat import FaoFishstatAdapter
from okeanus.adapters.esvd import EsvdAdapter
from okeanus.adapters.isa_deepdata import IsaDeepDataAdapter

__all__ = [
    "AisStreamAdapter",
    "AllenCoralAdapter",
    "ArgovisAdapter",
    "ArgopyAdapter",
    "BaseAdapter",
    "BoemWindAdapter",
    "BoldAdapter",
    "ClavIuuAdapter",
    "CmemsAdapter",
    "CopernicusDataspaceAdapter",
    "EarthaccessAdapter",
    "EcmwfOpenAdapter",
    "EmodnetBathymetryAdapter",
    "EmodnetBiologyAdapter",
    "EmodnetHumanAdapter",
    "EmodnetSeabedAdapter",
    "ErddapAdapter",
    "FaoFisheriesAdapter",
    "FedRegisterAdapter",
    "FishBaseAdapter",
    "GbifAdapter",
    "GfsForecastAdapter",
    "GlobalFishingWatchAdapter",
    "GlobalMangroveAdapter",
    "GoaOnAdapter",
    "HaedatAdapter",
    "HabsosAdapter",
    "IcesAdapter",
    "ImbPiracyAdapter",
    "INaturalistAdapter",
    "InterRidgeAdapter",
    "IucnRedlistAdapter",
    "MarineDebrisAdapter",
    "MarineHeatwaveAdapter",
    "MarineRegionsAdapter",
    "MovebankAdapter",
    "NdbcAdapter",
    "NgdcTsunamiAdapter",
    "NoaaCoopsAdapter",
    "NoaaDeepCoralAdapter",
    "NoaaErmaAdapter",
    "NoaaStormEventsAdapter",
    "NoaaWrecksAdapter",
    "NsidcSeaIceAdapter",
    "ObisAdapter",
    "ObisSeamapAdapter",
    "OceanInfoHubAdapter",
    "OceanTrackingAdapter",
    "OncAdapter",
    "OpendapAdapter",
    "OpenSanctionsAdapter",
    "OrcasoundAdapter",
    "PangaeaAdapter",
    "PsmslAdapter",
    "RamLegacyAdapter",
    "ReefLifeSurveyAdapter",
    "SeaBassAdapter",
    "SeaLifeBaseAdapter",
    "SmithsonianVolcanoesAdapter",
    "ThetisMrvAdapter",
    "UsgsQuakesAdapter",
    "WdpaAdapter",
    "WormsAdapter",
    # Blue Economy Phase 1
    "WorldBankAdapter",
    "FredAdapter",
    "NoaaEnowAdapter",
    "EurostatBlueAdapter",
    "UnctadAdapter",
    "ImfCommoditiesAdapter",
    "IloMaritimeAdapter",
    "OecdOceanAdapter",
    # Blue Economy Phase 2
    "SsbSalmonAdapter",
    "EumofaAdapter",
    "UsdaGatsAdapter",
    "NoaaFossAdapter",
    "SseIndicesAdapter",
    "BunkerIndexAdapter",
    "OilPriceApiAdapter",
    "UsdaBunkerAdapter",
    # Blue Economy Phase 3
    "IatiOceanAdapter",
    "GcfOceanAdapter",
    "VerraBlueAdapter",
    "WbaSeafoodAdapter",
    # Blue Economy Phase 4
    "FemaNfipAdapter",
    "BoemOffshoreAdapter",
    "CrownEstateAdapter",
    "OsparInstallationsAdapter",
    "IuuIndexAdapter",
    # Blue Economy Phase 5
    "SeaAroundUsAdapter",
    "IcesSagAdapter",
    "FaoFishstatAdapter",
    "EsvdAdapter",
    "IsaDeepDataAdapter",
]

# Registry mapping source names to adapter classes for dynamic lookup
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "aisstream": AisStreamAdapter,
    "allen_coral": AllenCoralAdapter,
    "argovis": ArgovisAdapter,
    "argopy": ArgopyAdapter,
    "boem_wind": BoemWindAdapter,
    "bold": BoldAdapter,
    "clav_iuu": ClavIuuAdapter,
    "cmems": CmemsAdapter,
    "copernicus_dataspace": CopernicusDataspaceAdapter,
    "earthaccess": EarthaccessAdapter,
    "ecmwf_open": EcmwfOpenAdapter,
    "emodnet_bathymetry": EmodnetBathymetryAdapter,
    "emodnet_biology": EmodnetBiologyAdapter,
    "emodnet_human": EmodnetHumanAdapter,
    "emodnet_seabed": EmodnetSeabedAdapter,
    "erddap": ErddapAdapter,
    "fao_fisheries": FaoFisheriesAdapter,
    "fed_register": FedRegisterAdapter,
    "fishbase": FishBaseAdapter,
    "gbif": GbifAdapter,
    "gfs_forecast": GfsForecastAdapter,
    "gfw": GlobalFishingWatchAdapter,
    "global_mangrove": GlobalMangroveAdapter,
    "goaon": GoaOnAdapter,
    "haedat": HaedatAdapter,
    "habsos": HabsosAdapter,
    "ices": IcesAdapter,
    "imb_piracy": ImbPiracyAdapter,
    "inaturalist": INaturalistAdapter,
    "interridge": InterRidgeAdapter,
    "iucn_redlist": IucnRedlistAdapter,
    "marine_debris": MarineDebrisAdapter,
    "marine_heatwave": MarineHeatwaveAdapter,
    "marine_regions": MarineRegionsAdapter,
    "movebank": MovebankAdapter,
    "ndbc": NdbcAdapter,
    "ngdc_tsunami": NgdcTsunamiAdapter,
    "noaa_coops": NoaaCoopsAdapter,
    "noaa_deep_coral": NoaaDeepCoralAdapter,
    "noaa_erma": NoaaErmaAdapter,
    "noaa_storm_events": NoaaStormEventsAdapter,
    "noaa_wrecks": NoaaWrecksAdapter,
    "nsidc_sea_ice": NsidcSeaIceAdapter,
    "obis": ObisAdapter,
    "obis_seamap": ObisSeamapAdapter,
    "ocean_info_hub": OceanInfoHubAdapter,
    "ocean_tracking": OceanTrackingAdapter,
    "onc": OncAdapter,
    "opendap": OpendapAdapter,
    "opensanctions": OpenSanctionsAdapter,
    "orcasound": OrcasoundAdapter,
    "pangaea": PangaeaAdapter,
    "psmsl": PsmslAdapter,
    "ram_legacy": RamLegacyAdapter,
    "reef_life_survey": ReefLifeSurveyAdapter,
    "seabass": SeaBassAdapter,
    "sealifebase": SeaLifeBaseAdapter,
    "smithsonian_volcanoes": SmithsonianVolcanoesAdapter,
    "thetis_mrv": ThetisMrvAdapter,
    "usgs_quakes": UsgsQuakesAdapter,
    "wdpa": WdpaAdapter,
    "worms": WormsAdapter,
    # Blue Economy Phase 1: Government Stats
    "world_bank": WorldBankAdapter,
    "fred": FredAdapter,
    "noaa_enow": NoaaEnowAdapter,
    "eurostat_blue": EurostatBlueAdapter,
    "unctad": UnctadAdapter,
    "imf_commodities": ImfCommoditiesAdapter,
    "ilo_maritime": IloMaritimeAdapter,
    "oecd_ocean": OecdOceanAdapter,
    # Blue Economy Phase 2: Trader Layer
    "ssb_salmon": SsbSalmonAdapter,
    "eumofa": EumofaAdapter,
    "usda_gats": UsdaGatsAdapter,
    "noaa_foss": NoaaFossAdapter,
    "sse_indices": SseIndicesAdapter,
    "bunker_index": BunkerIndexAdapter,
    "oilprice_api": OilPriceApiAdapter,
    "usda_bunker": UsdaBunkerAdapter,
    # Blue Economy Phase 3: Finance Layer
    "iati_ocean": IatiOceanAdapter,
    "gcf_ocean": GcfOceanAdapter,
    "verra_blue": VerraBlueAdapter,
    "wba_seafood": WbaSeafoodAdapter,
    # Blue Economy Phase 4: Risk & Infrastructure
    "fema_nfip": FemaNfipAdapter,
    "boem_offshore": BoemOffshoreAdapter,
    "crown_estate": CrownEstateAdapter,
    "ospar_installations": OsparInstallationsAdapter,
    "iuu_index": IuuIndexAdapter,
    # Blue Economy Phase 5: Fisheries & Ecosystem Economics
    "sea_around_us": SeaAroundUsAdapter,
    "ices_sag": IcesSagAdapter,
    "fao_fishstat": FaoFishstatAdapter,
    "esvd": EsvdAdapter,
    "isa_deepdata": IsaDeepDataAdapter,
}
