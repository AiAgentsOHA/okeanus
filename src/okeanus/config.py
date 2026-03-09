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
    cmems_username: str = ""
    cmems_password: str = ""
    ais_api_key: str = ""
    obis_api_key: str = ""
    gbif_username: str = ""
    gbif_password: str = ""
    copernicus_api_key: str = ""
    sentinel_hub_client_id: str = ""
    sentinel_hub_client_secret: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
