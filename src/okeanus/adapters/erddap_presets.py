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
