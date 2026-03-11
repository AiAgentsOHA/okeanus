"""ERDDAP presets — known dataset configurations for major ocean data sources.

Each preset maps a short name to a server URL, dataset ID, variable list,
and obs_type so users can fetch data without knowing ERDDAP internals.

Usage:
    from okeanus.adapters.erddap_presets import PRESETS, get_preset_adapter
    adapter = get_preset_adapter("coastwatch_sst")
    results = await adapter.fetch(bbox, t0, t1)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from okeanus.adapters.erddap import ErddapAdapter

# Well-known ERDDAP servers
COASTWATCH = "https://coastwatch.pfeg.noaa.gov/erddap"
OSMC = "https://osmc.noaa.gov/erddap"
IOOS_GLIDERS = "https://gliders.ioos.us/erddap"
NCEI = "https://www.ncei.noaa.gov/erddap"
PMEL = "https://data.pmel.noaa.gov/pmel/erddap"
OOI = "https://erddap.dataexplorer.oceanobservatories.org/erddap"
CIOOSATLANTIC = "https://cioosatlantic.ca/erddap"
IFREMER = "https://www.ifremer.fr/erddap"
BCODMO = "https://erddap.bco-dmo.org/erddap"
PODAAC = "https://podaac-tools.jpl.nasa.gov/erddap"
EMODNET_PHYSICS = "https://erddap.emodnet-physics.eu/erddap"
EMODNET_CHEMISTRY = "https://erddap.emodnet-chemistry.eu/erddap"
IMOS = "https://thredds.aodn.org.au/thredds/erddap"
CIOOS_PACIFIC = "https://data.cioospacific.ca/erddap"
HYCOM = "https://ncss.hycom.org/thredds"
NSIDC = "https://nsidc.org/erddap"


@dataclass(frozen=True)
class ErddapPreset:
    """Configuration for a known ERDDAP dataset."""

    name: str
    description: str
    server: str
    dataset_id: str
    variables: str  # comma-separated ERDDAP variable list
    obs_type: str = "physical"
    category: str = "physical"


# ------------------------------------------------------------------
# Presets organized by domain
# ------------------------------------------------------------------

PRESETS: dict[str, ErddapPreset] = {
    # --- Sea Surface Temperature ---
    "coastwatch_sst": ErddapPreset(
        name="NOAA CoastWatch SST",
        description="Global daily OISST v2.1 (0.25 deg)",
        server=COASTWATCH,
        dataset_id="ncdcOisst21Agg_LonPM180",
        variables="time,latitude,longitude,sst,anom",
        category="physical",
    ),
    "jplmur_sst": ErddapPreset(
        name="JPL MUR SST",
        description="Multi-scale ultra-high res SST (0.01 deg)",
        server=COASTWATCH,
        dataset_id="jplMURSST41",
        variables="time,latitude,longitude,analysed_sst",
        category="physical",
    ),
    # --- Waves & Weather ---
    "ndbc_stdmet": ErddapPreset(
        name="NDBC Standard Meteorological",
        description="NDBC buoy stations: wind, waves, pressure, temperature",
        server=COASTWATCH,
        dataset_id="cwwcNDBCMet",
        variables=(
            "time,latitude,longitude,station,wd,wspd,"
            "wvht,dpd,apd,wtmp,atmp,dewp"
        ),
        category="physical",
    ),
    "wavewatch3": ErddapPreset(
        name="WAVEWATCH III Global",
        description="NOAA WW3 global wave model (0.5 deg)",
        server=COASTWATCH,
        dataset_id="NWW3_Global_Best",
        variables=(
            "time,latitude,longitude,"
            "Thgt,Tper,Tdir"
        ),
        category="physical",
    ),
    # --- Ocean Currents & Physical ---
    "oscar_currents": ErddapPreset(
        name="OSCAR Ocean Currents",
        description="Near-surface ocean currents (1/3 deg, 5-day)",
        server=COASTWATCH,
        dataset_id="erdOscar5d",
        variables="time,latitude,longitude,u,v",
        category="physical",
    ),
    # --- Drifters & Floats ---
    "global_drifters": ErddapPreset(
        name="Global Drifter Program",
        description="Surface drifting buoy observations",
        server=OSMC,
        dataset_id="gdp_v2.01_sst1",
        variables=(
            "time,latitude,longitude,ID,"
            "sst,sst1,ve,vn"
        ),
        category="physical",
    ),
    "ioos_gliders": ErddapPreset(
        name="IOOS Glider DAC",
        description="Underwater glider profiles (T, S, depth)",
        server=IOOS_GLIDERS,
        dataset_id="allDatasets",
        variables="",  # varies per dataset
        category="physical",
    ),
    # --- Biogeochemistry & Biology ---
    "calcofi": ErddapPreset(
        name="CalCOFI Bottle Data",
        description=(
            "California Cooperative Fisheries — 75+ years"
        ),
        server=COASTWATCH,
        dataset_id="erdCalCOFIlrvcntAtoAM",
        variables="time,latitude,longitude",
        obs_type="biological",
        category="biological",
    ),
    "coral_reef_watch": ErddapPreset(
        name="NOAA Coral Reef Watch",
        description="Satellite coral bleaching thermal stress",
        server=COASTWATCH,
        dataset_id="NOAA_DHW",
        variables=(
            "time,latitude,longitude,"
            "CRW_SST,CRW_SSTANOMALY,CRW_HOTSPOT,"
            "CRW_BAA,CRW_DHW"
        ),
        category="biological",
    ),
    # --- Satellite ---
    "erdap_chlorophyll": ErddapPreset(
        name="MODIS Aqua Chlorophyll",
        description="NASA MODIS chlorophyll-a (4km, 8-day)",
        server=COASTWATCH,
        dataset_id="erdMH1chla8day",
        variables="time,latitude,longitude,chlorophyll",
        category="satellite",
    ),
    "erdap_sst_modis": ErddapPreset(
        name="MODIS Aqua SST",
        description="NASA MODIS SST (4km, monthly)",
        server=COASTWATCH,
        dataset_id="erdMH1sstdmday",
        variables="time,latitude,longitude,sst",
        category="physical",
    ),
    # --- PMEL / TAO ---
    "tao_buoys": ErddapPreset(
        name="TAO/TRITON Tropical Buoys",
        description="Tropical moored buoy array (Pacific/Atlantic)",
        server=PMEL,
        dataset_id="sd1001_metdba_2022_e54f_e4c1_ae73",
        variables="time,latitude,longitude",
        category="physical",
    ),
    # --- Carbon / Chemistry ---
    "socat": ErddapPreset(
        name="SOCAT Surface CO2",
        description="Surface Ocean CO2 Atlas observations",
        server=COASTWATCH,
        dataset_id="soaborc_v2024",
        variables=(
            "time,latitude,longitude,"
            "fCO2rec,SST,salinity"
        ),
        obs_type="physical",
        category="chemical",
    ),
    # --- BCO-DMO Research ---
    "bcodmo": ErddapPreset(
        name="BCO-DMO Research Data",
        description=(
            "Biological & Chemical Oceanography datasets"
        ),
        server=BCODMO,
        dataset_id="allDatasets",
        variables="",
        obs_type="biological",
        category="biological",
    ),
    # --- Canadian Oceans ---
    "cioos_atlantic": ErddapPreset(
        name="CIOOS Atlantic",
        description="Canadian Integrated Ocean Observing System",
        server=CIOOSATLANTIC,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- OOI Cabled Array ---
    "ooi_cabled": ErddapPreset(
        name="OOI Cabled Array",
        description=(
            "Ocean Observatories Initiative deep-sea sensors"
        ),
        server=OOI,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- Wave 3 additions ---
    # --- NCEI World Ocean Database ---
    "ncei_wod": ErddapPreset(
        name="NCEI World Ocean Database",
        description="Historical T/S profiles from WOD (1.5M+ casts since 1772)",
        server=NCEI,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- OceanSITES fixed-point ---
    "oceansites": ErddapPreset(
        name="OceanSITES Fixed-Point Time Series",
        description="Deep-ocean reference stations for climate monitoring",
        server=COASTWATCH,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- DART Tsunami Buoys ---
    "dart_tsunami": ErddapPreset(
        name="DART Tsunami Buoys",
        description="Deep-ocean bottom pressure recorders for tsunami detection",
        server=PMEL,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- Sea Surface Height ---
    "podaac_ssh": ErddapPreset(
        name="PO.DAAC Sea Surface Height",
        description="Satellite altimetry sea surface height anomalies",
        server=PODAAC,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- EGO Gliders (Europe) ---
    "ego_gliders": ErddapPreset(
        name="EGO European Gliders",
        description="European glider profiles from Ifremer (T, S, depth)",
        server=IFREMER,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- PMEL Acoustics ---
    "pmel_acoustics": ErddapPreset(
        name="NOAA PMEL Acoustics",
        description="Pacific ambient ocean noise levels from hydrophones",
        server=PMEL,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="acoustic",
    ),
    # --- Ocean Acidification ---
    "noaa_oa_buoys": ErddapPreset(
        name="NOAA Ocean Acidification Buoys",
        description="Surface CO2 + pH from MAPCO2/IPACOA network",
        server=PMEL,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="chemical",
    ),
    # --- OCADS Carbon ---
    "ocads_carbon": ErddapPreset(
        name="NCEI Ocean Carbon Data (OCADS)",
        description="Global ocean dissolved inorganic carbon observations",
        server=NCEI,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="chemical",
    ),
    # --- EMODnet Physics ---
    "emodnet_physics": ErddapPreset(
        name="EMODnet Physics",
        description="EU in-situ ocean physics (T, S, waves, currents, sea level)",
        server=EMODNET_PHYSICS,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- EMODnet Chemistry ---
    "emodnet_chemistry": ErddapPreset(
        name="EMODnet Chemistry",
        description="EU ocean chemistry (nutrients, contaminants, eutrophication)",
        server=EMODNET_CHEMISTRY,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="chemical",
    ),
    # --- NCEI Microplastics (from OCADS) ---
    "ncei_microplastics": ErddapPreset(
        name="NCEI Global Microplastics",
        description="Global ocean microplastics concentration database",
        server=NCEI,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="chemical",
    ),
    # --- PSMSL Sea Level ---
    "psmsl_sea_level": ErddapPreset(
        name="PSMSL Tide Gauge Sea Level",
        description="Monthly mean sea level from 2000+ tide gauges since 1807",
        server=COASTWATCH,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # ------------------------------------------------------------------
    # Wave 4 additions
    # ------------------------------------------------------------------
    # --- Satellite Ocean Color ---
    "viirs_chlorophyll": ErddapPreset(
        name="VIIRS Chlorophyll-a",
        description="Suomi-NPP VIIRS chlorophyll-a (4km, 8-day composite)",
        server=COASTWATCH,
        dataset_id="nesdisVHNSQchlaMonthly",
        variables="time,latitude,longitude,chlor_a",
        category="satellite",
    ),
    "aqua_modis_par": ErddapPreset(
        name="MODIS Aqua PAR",
        description="Photosynthetically active radiation (4km, 8-day)",
        server=COASTWATCH,
        dataset_id="erdMH1par08day",
        variables="time,latitude,longitude,par",
        category="satellite",
    ),
    # --- Sea Surface Salinity ---
    "smap_sss": ErddapPreset(
        name="SMAP Sea Surface Salinity",
        description="NASA SMAP L3 sea surface salinity (0.25 deg, 8-day)",
        server=COASTWATCH,
        dataset_id="nasa_jpl_c6b0_a4e6_5a60",
        variables="time,latitude,longitude,sss",
        category="physical",
    ),
    # --- Geostationary SST ---
    "goes_sst": ErddapPreset(
        name="GOES Geostationary SST",
        description="GOES-16/17 SST for western hemisphere (hourly, 2km)",
        server=COASTWATCH,
        dataset_id="goes16SST",
        variables="time,latitude,longitude,sst",
        category="satellite",
    ),
    # --- High-Res SST ---
    "ghrsst": ErddapPreset(
        name="GHRSST L4 Global Foundation SST",
        description="Group for High-Res SST blended product (0.01 deg daily)",
        server=COASTWATCH,
        dataset_id="jplMURSST41anom1day",
        variables="time,latitude,longitude,sstAnom,analysed_sst",
        category="physical",
    ),
    # --- Wind ---
    "ccmp_wind": ErddapPreset(
        name="CCMP Cross-Calibrated Wind",
        description="Multi-platform ocean surface wind vectors (0.25 deg, 6-hourly)",
        server=COASTWATCH,
        dataset_id="erdQMstress3dayanom",
        variables="time,latitude,longitude",
        category="physical",
    ),
    # --- BGC-Argo ---
    "argo_bgc": ErddapPreset(
        name="BGC-Argo Biogeochemistry",
        description="Biogeochemical Argo profiles (O2, nitrate, pH, chlorophyll, POC)",
        server=IFREMER,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="chemical",
    ),
    # --- Saildrone ---
    "saildrone": ErddapPreset(
        name="Saildrone Uncrewed Surface Vehicle",
        description="NOAA Saildrone USV observations (wind, SST, salinity, CO2)",
        server=PMEL,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- IBTrACS Tropical Cyclones ---
    "ibtracs": ErddapPreset(
        name="IBTrACS Tropical Cyclones",
        description="International Best Track Archive — global tropical cyclone data since 1842",
        server=NCEI,
        dataset_id="allDatasets",
        variables="",
        obs_type="physical",
        category="physical",
    ),
    # --- Australian Oceans ---
    "imos_sst": ErddapPreset(
        name="IMOS Australian SST",
        description="IMOS satellite SST for Australian waters",
        server=IMOS,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- Canadian Pacific ---
    "cioos_pacific": ErddapPreset(
        name="CIOOS Pacific",
        description="Canadian Integrated Ocean Observing — Pacific region",
        server=CIOOS_PACIFIC,
        dataset_id="allDatasets",
        variables="",
        category="physical",
    ),
    # --- Bathymetry ---
    "gebco_bathymetry": ErddapPreset(
        name="GEBCO Global Bathymetry",
        description="GEBCO gridded bathymetry/topography (15 arc-second)",
        server=COASTWATCH,
        dataset_id="GEBCO_2024",
        variables="time,latitude,longitude,elevation",
        category="physical",
    ),
    # ------------------------------------------------------------------
    # Wave 5 additions — Session 8
    # ------------------------------------------------------------------
    # --- Long-Term SST Records ---
    "hadisst": ErddapPreset(
        name="HadISST Sea Surface Temperature",
        description="Hadley Centre monthly SST (1870–present, 1 deg)",
        server=COASTWATCH,
        dataset_id="erdHadISST",
        variables="time,latitude,longitude,sst",
        category="physical",
    ),
    "pathfinder_sst": ErddapPreset(
        name="AVHRR Pathfinder SST",
        description="Long-term satellite SST record (4km, 1981–present)",
        server=NCEI,
        dataset_id="pathfinderAgg_day",
        variables="time,latitude,longitude,sea_surface_temperature",
        category="physical",
    ),
    "blended_sst_anomaly": ErddapPreset(
        name="NOAA Blended SST Anomaly",
        description="Blended sea surface temperature anomaly (5-day composite)",
        server=COASTWATCH,
        dataset_id="noaacwBlendedSstAnom5day",
        variables="time,latitude,longitude,sstAnomaly",
        category="physical",
    ),
    # --- Sea Level / Altimetry ---
    "blended_ssh": ErddapPreset(
        name="NOAA Blended Sea Surface Height",
        description="Blended multi-mission sea surface height (daily, 0.25 deg)",
        server=COASTWATCH,
        dataset_id="noaacwBlendedSshDaily",
        variables="time,latitude,longitude,ssh",
        category="physical",
    ),
    # --- Wind Stress ---
    "quikscat_wind_stress": ErddapPreset(
        name="QuikSCAT Wind Stress",
        description="Ocean surface wind stress from QuikSCAT scatterometer (daily)",
        server=COASTWATCH,
        dataset_id="erdQAstress1day",
        variables="time,latitude,longitude,taux,tauy",
        category="physical",
    ),
    # --- Historical Ocean Color ---
    "seawifs_chlorophyll": ErddapPreset(
        name="SeaWiFS Chlorophyll-a",
        description="SeaWiFS ocean color chlorophyll (1997–2010, 9km)",
        server=COASTWATCH,
        dataset_id="erdSW2018chla8day",
        variables="time,latitude,longitude,chlorophyll",
        category="satellite",
    ),
    # --- World Ocean Atlas Climatology ---
    "woa_temperature": ErddapPreset(
        name="World Ocean Atlas Temperature",
        description="WOA18 annual temperature climatology (1 deg, 102 depth levels)",
        server=NCEI,
        dataset_id="nodc_woa18_t_an01_04",
        variables="latitude,longitude,depth,t_an",
        category="physical",
    ),
    "woa_salinity": ErddapPreset(
        name="World Ocean Atlas Salinity",
        description="WOA18 annual salinity climatology (1 deg, 102 depth levels)",
        server=NCEI,
        dataset_id="nodc_woa18_s_an01_04",
        variables="latitude,longitude,depth,s_an",
        category="physical",
    ),
}


def get_preset_adapter(
    preset_name: str, **kwargs: Any,
) -> ErddapAdapter:
    """Instantiate an ErddapAdapter from a preset name."""
    preset = PRESETS[preset_name]
    return ErddapAdapter(
        server_url=preset.server,
        dataset_id=preset.dataset_id,
        **kwargs,
    )


def list_presets() -> list[dict[str, str]]:
    """Return all presets as a list of dicts for the CLI."""
    return [
        {
            "name": key,
            "description": p.description,
            "server": p.server,
            "dataset_id": p.dataset_id,
            "category": p.category,
        }
        for key, p in PRESETS.items()
    ]
