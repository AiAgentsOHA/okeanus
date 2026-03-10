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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

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
            {
                "name": "Sentinel Hub",
                "configured": bool(
                    self.sentinel_hub_client_id and self.sentinel_hub_client_secret
                ),
                "auth": "oauth",
            },
        ]


settings = Settings()
