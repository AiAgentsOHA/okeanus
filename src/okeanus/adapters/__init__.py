"""Source adapters -- connectors for ocean data feeds."""

from okeanus.adapters.ais_hub import AisHubAdapter
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
from okeanus.adapters.gebco import GebcoAdapter
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
from okeanus.adapters.port_calls import WorldPortIndexAdapter
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

# --- Session 23: New Adapters (Phase B+C) ---
from okeanus.adapters.rss_feed import RssFeedAdapter
from okeanus.adapters.climate_indices import ClimateIndicesAdapter
from okeanus.adapters.open_meteo_marine import OpenMeteoMarineAdapter
from okeanus.adapters.openfisheries import OpenFisheriesAdapter
from okeanus.adapters.ofac_sdn import OfacSdnAdapter
from okeanus.adapters.nga_msi import NgaMsiAdapter
from okeanus.adapters.un_comtrade import UnComtradeAdapter
from okeanus.adapters.eia_offshore import EiaOffshoreAdapter
from okeanus.adapters.regulations_gov import RegulationsGovAdapter
from okeanus.adapters.wqp import WqpAdapter
from okeanus.adapters.skytruth_cerulean import SkytruthCeruleanAdapter

# --- Session 24: New Adapters (Phase D) ---
from okeanus.adapters.ecfr import EcfrAdapter
from okeanus.adapters.noaa_incident_news import NoaaIncidentNewsAdapter
from okeanus.adapters.noaa_adios_oil import NoaaAdiosOilAdapter
from okeanus.adapters.bsee_spills import BseeSpillsAdapter
from okeanus.adapters.coral_bleaching import CoralBleachingAdapter
from okeanus.adapters.ncei_microplastics import NceiMicroplasticsAdapter
from okeanus.adapters.global_tuna_atlas import GlobalTunaAtlasAdapter

# --- Session 25: New Adapters (Phase E) ---
from okeanus.adapters.ices_noise import IcesNoiseAdapter

# --- Session 26: New Adapters (Phase D continued) ---
from okeanus.adapters.happywhale import HappywhaleAdapter
from okeanus.adapters.uhslc_tides import UhslcTidesAdapter
from okeanus.adapters.ncei_ohc import NceiOhcAdapter
from okeanus.adapters.glodap import GlodapAdapter
from okeanus.adapters.acled_maritime import AcledMaritimeAdapter
from okeanus.adapters.fathomnet import FathomNetAdapter

# --- Session 27: Ocean Model & Physical Oceanography ---
from okeanus.adapters.hycom import HycomAdapter
from okeanus.adapters.noaa_rtofs import NoaaRtofsAdapter
from okeanus.adapters.icoads import IcoadsAdapter
from okeanus.adapters.en4_subsurface import En4SubsurfaceAdapter
from okeanus.adapters.aviso_altimetry import AvisoAltimetryAdapter
from okeanus.adapters.osi_saf import OsiSafAdapter
from okeanus.adapters.cchdo_goship import CchdoGoshipAdapter

# --- Session 27: Fisheries RFMOs & Biology ---
from okeanus.adapters.iccat import IccatAdapter
from okeanus.adapters.iotc import IotcAdapter
from okeanus.adapters.wcpfc import WcpfcAdapter
from okeanus.adapters.ccamlr import CcamlrAdapter
from okeanus.adapters.ebird_marine import EbirdMarineAdapter
from okeanus.adapters.fishsource import FishSourceAdapter
from okeanus.adapters.tara_oceans import TaraOceansAdapter
from okeanus.adapters.cpr_survey import CprSurveyAdapter
from okeanus.adapters.ncbi_marine import NcbiMarineAdapter

# --- Session 27: Governance, Economy & Security ---
from okeanus.adapters.paris_mou_psc import ParisMouPscAdapter
from okeanus.adapters.tokyo_mou_psc import TokyoMouPscAdapter
from okeanus.adapters.ukmto_incidents import UkmtoIncidentsAdapter
from okeanus.adapters.noaa_marine_cadastre import NoaaMarineCadastreAdapter
from okeanus.adapters.irena_offshore import IrenaOffshoreAdapter
from okeanus.adapters.eu_blue_economy import EuBlueEconomyAdapter
from okeanus.adapters.wto_fisheries import WtoFisheriesAdapter
from okeanus.adapters.iaea_maris import IaeaMarisAdapter
from okeanus.adapters.barentswatch import BarentswatchAdapter

__all__ = [
    "AisHubAdapter",
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
    "GebcoAdapter",
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
    "WorldPortIndexAdapter",
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
    # Session 23: New Adapters
    "RssFeedAdapter",
    "ClimateIndicesAdapter",
    "OpenMeteoMarineAdapter",
    "OpenFisheriesAdapter",
    "OfacSdnAdapter",
    "NgaMsiAdapter",
    "UnComtradeAdapter",
    "EiaOffshoreAdapter",
    "RegulationsGovAdapter",
    "WqpAdapter",
    "SkytruthCeruleanAdapter",
    # Session 24: New Adapters
    "EcfrAdapter",
    "NoaaIncidentNewsAdapter",
    "NoaaAdiosOilAdapter",
    "BseeSpillsAdapter",
    "CoralBleachingAdapter",
    "NceiMicroplasticsAdapter",
    "GlobalTunaAtlasAdapter",
    # Session 25: New Adapters
    "IcesNoiseAdapter",
    # Session 26: New Adapters
    "HappywhaleAdapter",
    "UhslcTidesAdapter",
    "NceiOhcAdapter",
    "GlodapAdapter",
    "AcledMaritimeAdapter",
    "FathomNetAdapter",
    # Session 27: Ocean Model & Physical Oceanography
    "HycomAdapter",
    "NoaaRtofsAdapter",
    "IcoadsAdapter",
    "En4SubsurfaceAdapter",
    "AvisoAltimetryAdapter",
    "OsiSafAdapter",
    "CchdoGoshipAdapter",
    # Session 27: Fisheries RFMOs & Biology
    "IccatAdapter",
    "IotcAdapter",
    "WcpfcAdapter",
    "CcamlrAdapter",
    "EbirdMarineAdapter",
    "FishSourceAdapter",
    "TaraOceansAdapter",
    "CprSurveyAdapter",
    "NcbiMarineAdapter",
    # Session 27: Governance, Economy & Security
    "ParisMouPscAdapter",
    "TokyoMouPscAdapter",
    "UkmtoIncidentsAdapter",
    "NoaaMarineCadastreAdapter",
    "IrenaOffshoreAdapter",
    "EuBlueEconomyAdapter",
    "WtoFisheriesAdapter",
    "IaeaMarisAdapter",
    "BarentswatchAdapter",
]

# Registry mapping source names to adapter classes for dynamic lookup
ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "ais_hub": AisHubAdapter,
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
    "gebco": GebcoAdapter,
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
    "port_calls": WorldPortIndexAdapter,
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
    # Session 23: New Adapters
    "rss_feed": RssFeedAdapter,
    "climate_indices": ClimateIndicesAdapter,
    "open_meteo_marine": OpenMeteoMarineAdapter,
    "openfisheries": OpenFisheriesAdapter,
    "ofac_sdn": OfacSdnAdapter,
    "nga_msi": NgaMsiAdapter,
    "un_comtrade": UnComtradeAdapter,
    "eia_offshore": EiaOffshoreAdapter,
    "regulations_gov": RegulationsGovAdapter,
    "wqp": WqpAdapter,
    "skytruth_cerulean": SkytruthCeruleanAdapter,
    # Session 24: New Adapters
    "ecfr": EcfrAdapter,
    "noaa_incident_news": NoaaIncidentNewsAdapter,
    "noaa_adios_oil": NoaaAdiosOilAdapter,
    "bsee_spills": BseeSpillsAdapter,
    "coral_bleaching": CoralBleachingAdapter,
    "ncei_microplastics": NceiMicroplasticsAdapter,
    "global_tuna_atlas": GlobalTunaAtlasAdapter,
    # Session 25: New Adapters
    "ices_noise": IcesNoiseAdapter,
    # Session 26: New Adapters
    "happywhale": HappywhaleAdapter,
    "uhslc_tides": UhslcTidesAdapter,
    "ncei_ohc": NceiOhcAdapter,
    "glodap": GlodapAdapter,
    "acled_maritime": AcledMaritimeAdapter,
    "fathomnet": FathomNetAdapter,
    # Session 27: Ocean Model & Physical Oceanography
    "hycom": HycomAdapter,
    "noaa_rtofs": NoaaRtofsAdapter,
    "icoads": IcoadsAdapter,
    "en4_subsurface": En4SubsurfaceAdapter,
    "aviso_altimetry": AvisoAltimetryAdapter,
    "osi_saf": OsiSafAdapter,
    "cchdo_goship": CchdoGoshipAdapter,
    # Session 27: Fisheries RFMOs & Biology
    "iccat": IccatAdapter,
    "iotc": IotcAdapter,
    "wcpfc": WcpfcAdapter,
    "ccamlr": CcamlrAdapter,
    "ebird_marine": EbirdMarineAdapter,
    "fishsource": FishSourceAdapter,
    "tara_oceans": TaraOceansAdapter,
    "cpr_survey": CprSurveyAdapter,
    "ncbi_marine": NcbiMarineAdapter,
    # Session 27: Governance, Economy & Security
    "paris_mou_psc": ParisMouPscAdapter,
    "tokyo_mou_psc": TokyoMouPscAdapter,
    "ukmto_incidents": UkmtoIncidentsAdapter,
    "noaa_marine_cadastre": NoaaMarineCadastreAdapter,
    "irena_offshore": IrenaOffshoreAdapter,
    "eu_blue_economy": EuBlueEconomyAdapter,
    "wto_fisheries": WtoFisheriesAdapter,
    "iaea_maris": IaeaMarisAdapter,
    "barentswatch": BarentswatchAdapter,
}
