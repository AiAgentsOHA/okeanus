"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Global application settings.

    All values can be overridden via environment variables or a ``.env`` file
    located at the repository root.
    """

    # -- Database --
    database_url: str = "postgresql+asyncpg://okeanus:okeanus@localhost:5432/okeanus"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # -- DuckDB analytics --
    duckdb_path: str = "./data/okeanus.duckdb"

    # -- API --
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False
    log_level: str = "INFO"
    debug: bool = False

    # -- External data-source API keys --
    # CMEMS (registration required)
    cmems_username: str = ""
    cmems_password: str = ""
    # AISStream (free key at aisstream.io)
    ais_api_key: str = ""
    # Global Fishing Watch (free key at globalfishingwatch.org)
    gfw_api_key: str = ""
    # Ocean Networks Canada (free token at oceannetworks.ca)
    onc_api_token: str = ""
    # WDPA / Protected Planet (free token at protectedplanet.net)
    wdpa_api_token: str = ""
    # Copernicus Data Space
    copernicus_api_key: str = ""
    # Sentinel Hub
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""
    # OBIS (optional — works without key but key gives higher rate limits)
    obis_api_key: str = ""
    # GBIF (optional — works without auth)
    gbif_username: str = ""
    gbif_password: str = ""
    # NASA Earthdata (free at urs.earthdata.nasa.gov)
    nasa_earthdata_username: str = ""
    nasa_earthdata_password: str = ""
    # IUCN Red List (free at apiv3.iucnredlist.org)
    iucn_api_token: str = ""

    # -- ML / LLM --
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    llm_provider: str = "anthropic"  # "anthropic" or "claude_cli"
    llm_model: str = "claude-sonnet-4-6"
    llm_max_tokens: int = 4096
    gemini_chat_model: str = "gemini-2.5-flash"
    embedding_model: str = "nomic-ai/nomic-embed-text-v2-moe"
    embedding_dim: int = 768
    graph_auto_build: bool = True

    # -- Investigation --
    investigation_max_depth: int = 4
    investigation_max_concurrent_tasks: int = 5
    investigation_task_timeout_seconds: int = 120

    # -- Auth / JWT --
    jwt_secret: str = "change-me-in-production-use-a-real-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    auth_enabled: bool = False  # Future: toggle global auth requirement

    # -- Behavioral analytics --
    behavioral_window_minutes: int = 30  # trajectory classification window
    behavioral_step_minutes: int = 15  # sliding window step
    encounter_distance_nm: float = 0.5  # proximity threshold for encounters
    encounter_min_duration_minutes: float = 10  # minimum encounter duration
    voyage_port_sog_threshold: float = 0.5  # SOG below this = in port (knots)
    voyage_port_min_duration_minutes: float = 60  # minimum port stay duration

    # -- Risk scoring --
    risk_scoring_enabled: bool = True  # enable composite risk scoring
    risk_ais_gap_hours: int = 72  # lookback window for AIS gap detection
    risk_default_weights: str = ""  # JSON override for factor weights (leave empty for defaults)

    # -- Reports --
    reports_enabled: bool = True  # enable HTML report generation

    # -- Geofence engine --
    geofence_enabled: bool = True  # enable geofence evaluation
    geofence_auto_reload: bool = True  # reload zones on startup

    # -- Redis / Streaming --
    redis_url: str = "redis://localhost:6379/0"
    ais_stream_enabled: bool = False
    ais_stream_api_key: str = ""  # separate from ais_api_key which is for REST
    scheduler_enabled: bool = False
    websocket_heartbeat_seconds: int = 30
    ais_batch_flush_seconds: int = 10
    ais_batch_flush_size: int = 50

    # -- Blue Economy API keys --
    # FRED (free at fred.stlouisfed.org)
    fred_api_key: str = ""
    # USDA GATS (free at apps.fas.usda.gov)
    usda_gats_api_key: str = ""
    # OilPriceAPI (free tier at oilpriceapi.com)
    oilprice_api_key: str = ""
    # USDA AgTransport / Socrata (optional app token)
    usda_bunker_app_token: str = ""
    # Green Climate Fund (free registration)
    gcf_ocean_api_key: str = ""
    # ESVD Ecosystem Services (free registration at esvd.info)
    esvd_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def configured_sources(self) -> list[dict[str, str | bool]]:
        """Return a list of data sources with their configuration status."""
        return [
            # No auth required (always available)
            {"name": "OBIS", "configured": True, "auth": "none"},
            {"name": "GBIF", "configured": True, "auth": "none"},
            {"name": "Argovis", "configured": True, "auth": "none"},
            {"name": "NOAA CO-OPS", "configured": True, "auth": "none"},
            {"name": "NDBC", "configured": True, "auth": "none"},
            {"name": "ERDDAP", "configured": True, "auth": "none"},
            {"name": "Marine Regions", "configured": True, "auth": "none"},
            {"name": "WoRMS", "configured": True, "auth": "none"},
            {"name": "OpenSanctions", "configured": True, "auth": "none"},
            {"name": "iNaturalist", "configured": True, "auth": "none"},
            {"name": "PANGAEA", "configured": True, "auth": "none"},
            {"name": "OBIS-SEAMAP", "configured": True, "auth": "none"},
            {"name": "FishBase", "configured": True, "auth": "none"},
            {"name": "ICES", "configured": True, "auth": "none"},
            {"name": "HAEDAT", "configured": True, "auth": "none"},
            {"name": "HABSOS", "configured": True, "auth": "none"},
            {"name": "BOLD", "configured": True, "auth": "none"},
            {"name": "PSMSL", "configured": True, "auth": "none"},
            {"name": "NOAA Wrecks", "configured": True, "auth": "none"},
            {"name": "InterRidge Vents", "configured": True, "auth": "none"},
            {"name": "Marine Debris", "configured": True, "auth": "none"},
            {"name": "IMB Piracy", "configured": True, "auth": "none"},
            {"name": "CLAV IUU", "configured": True, "auth": "none"},
            {"name": "ECMWF Open Data", "configured": True, "auth": "none"},
            {"name": "argopy (Argo)", "configured": True, "auth": "none"},
            {"name": "OPeNDAP/THREDDS", "configured": True, "auth": "none"},
            {"name": "Marine Heatwave", "configured": True, "auth": "none"},
            {"name": "NOAA Deep-Sea Coral", "configured": True, "auth": "none"},
            {"name": "BOEM Offshore Wind", "configured": True, "auth": "none"},
            {"name": "Global Mangrove Watch", "configured": True, "auth": "none"},
            {"name": "SeaLifeBase", "configured": True, "auth": "none"},
            {"name": "EMODnet Biology", "configured": True, "auth": "none"},
            {"name": "Ocean Tracking Network", "configured": True, "auth": "none"},
            {"name": "Reef Life Survey", "configured": True, "auth": "none"},
            {"name": "USGS Earthquakes", "configured": True, "auth": "none"},
            {"name": "NSIDC Sea Ice", "configured": True, "auth": "none"},
            {"name": "FAO FIRMS", "configured": True, "auth": "none"},
            {"name": "Thetis MRV", "configured": True, "auth": "none"},
            {"name": "NOAA Storm Events", "configured": True, "auth": "none"},
            {"name": "EMODnet Seabed Habitats", "configured": True, "auth": "none"},
            {"name": "EMODnet Human Activities", "configured": True, "auth": "none"},
            {"name": "EMODnet Bathymetry", "configured": True, "auth": "none"},
            {"name": "NOAA ERMA", "configured": True, "auth": "none"},
            {"name": "NASA SeaBASS", "configured": True, "auth": "none"},
            {"name": "Movebank", "configured": True, "auth": "none"},
            {"name": "Ocean Info Hub", "configured": True, "auth": "none"},
            {"name": "GFS Marine Forecast", "configured": True, "auth": "none"},
            {"name": "Smithsonian GVP Volcanoes", "configured": True, "auth": "none"},
            {"name": "NGDC Historical Tsunami", "configured": True, "auth": "none"},
            {"name": "Orcasound Hydrophones", "configured": True, "auth": "none"},
            {"name": "Allen Coral Atlas", "configured": True, "auth": "none"},
            {"name": "US Federal Register", "configured": True, "auth": "none"},
            {"name": "GOA-ON Ocean Acidification", "configured": True, "auth": "none"},
            {"name": "RAM Legacy Stock Assessment", "configured": True, "auth": "none"},
            {"name": "Copernicus Data Space", "configured": True, "auth": "none"},
            # Free registration required
            {
                "name": "CMEMS",
                "configured": bool(self.cmems_username and self.cmems_password),
                "auth": "credentials",
            },
            {
                "name": "AISStream",
                "configured": bool(self.ais_api_key),
                "auth": "api_key",
            },
            {
                "name": "Global Fishing Watch",
                "configured": bool(self.gfw_api_key),
                "auth": "api_key",
            },
            {
                "name": "ONC Hydrophones",
                "configured": bool(self.onc_api_token),
                "auth": "api_token",
            },
            {"name": "WDPA", "configured": bool(self.wdpa_api_token), "auth": "api_token"},
            {"name": "Copernicus", "configured": bool(self.copernicus_api_key), "auth": "api_key"},
            {"name": "IUCN Red List", "configured": bool(self.iucn_api_token), "auth": "api_token"},
            {
                "name": "Sentinel Hub",
                "configured": bool(
                    self.sentinel_hub_client_id and self.sentinel_hub_client_secret
                ),
                "auth": "oauth",
            },
            # -- Blue Economy Phase 1: Government Stats (no auth) --
            {"name": "World Bank WDI", "configured": True, "auth": "none"},
            {"name": "NOAA ENOW", "configured": True, "auth": "none"},
            {"name": "Eurostat Maritime", "configured": True, "auth": "none"},
            {"name": "UNCTAD Maritime", "configured": True, "auth": "none"},
            {"name": "IMF Commodities", "configured": True, "auth": "none"},
            {"name": "ILO Maritime", "configured": True, "auth": "none"},
            {"name": "OECD Ocean", "configured": True, "auth": "none"},
            # Phase 1 with key
            {"name": "FRED", "configured": bool(self.fred_api_key), "auth": "api_key"},
            # -- Blue Economy Phase 2: Trader Layer (no auth) --
            {"name": "SSB Salmon", "configured": True, "auth": "none"},
            {"name": "EUMOFA", "configured": True, "auth": "none"},
            {"name": "NOAA FOSS", "configured": True, "auth": "none"},
            {"name": "SSE Indices", "configured": True, "auth": "none"},
            {"name": "Bunker Index", "configured": True, "auth": "none"},
            # Phase 2 with key
            {"name": "USDA GATS", "configured": bool(self.usda_gats_api_key), "auth": "api_key"},
            {"name": "OilPriceAPI", "configured": bool(self.oilprice_api_key), "auth": "api_key"},
            {"name": "USDA Bunker", "configured": True, "auth": "none (optional token)"},
            # -- Blue Economy Phase 3: Finance Layer --
            {"name": "IATI Ocean", "configured": True, "auth": "none"},
            {"name": "Verra Blue Carbon", "configured": True, "auth": "none"},
            {"name": "WBA Seafood", "configured": True, "auth": "none"},
            {"name": "GCF Ocean", "configured": bool(self.gcf_ocean_api_key), "auth": "api_key"},
            # -- Blue Economy Phase 4: Risk & Infrastructure (no auth) --
            {"name": "FEMA NFIP", "configured": True, "auth": "none"},
            {"name": "BOEM Offshore", "configured": True, "auth": "none"},
            {"name": "Crown Estate", "configured": True, "auth": "none"},
            {"name": "OSPAR Installations", "configured": True, "auth": "none"},
            {"name": "IUU Index", "configured": True, "auth": "none"},
            # -- Blue Economy Phase 5: Fisheries & Ecosystem Economics --
            {"name": "Sea Around Us", "configured": True, "auth": "none"},
            {"name": "ICES SAG", "configured": True, "auth": "none"},
            {"name": "FAO FishStatJ", "configured": True, "auth": "none"},
            {"name": "ISA DeepData", "configured": True, "auth": "none"},
            {"name": "ESVD", "configured": bool(self.esvd_api_key), "auth": "api_key"},
        ]


settings = Settings()
