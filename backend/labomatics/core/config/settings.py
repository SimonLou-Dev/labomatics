"""Configuration de l'applciation."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Représentation de la configuration de l'applciation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    time_zone: str = Field(default="Europe/Paris", alias="TIMEZONE")

    # --- Database ---
    database_host: str = Field(alias="DATABASE_HOST")
    database_port: int = Field(default=5432, alias="DATABASE_PORT")
    database_user: str = Field(alias="DATABASE_USER")
    database_password: str = Field(alias="DATABASE_PASSWORD")
    database_name: str = Field(alias="DATABASE_NAME")

    def get_async_db_url(self) -> str:
        """Obtenir l'url postgres async."""
        return f"postgresql+asyncpg://{self.database_user!s}:{self.database_password!s}@{self.database_host}:{self.database_port}/{self.database_name}"

    def get_sync_db_url(self) -> str:
        """Obtenir l'url postgres sync."""
        return f"postgresql+psycopg2://{self.database_user!s}:{self.database_password!s}@{self.database_host}:{self.database_port}/{self.database_name}"

    # --- Redis (for task queue, cache…) ---
    redis_url: str = Field(
        default="redis://redis:6379/0",
        alias="REDIS_URL",
    )

    # --- Keycloak / Auth ---
    keycloak_url: str = Field(default="http://keycloak:8080/", alias="KEYCLOAK_URL")
    keycloak_realm: str = Field(alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(alias="KEYCLOAK_CLIENT_SECRET")

    # --- Security ---
    encryption_key: str = Field(
        default="changeme-super-secret-key-32bytes",  # doit faire 32 bytes
        alias="ENCRYPTION_KEY",
    )

    app_url: str = Field(alias="APP_URL", default="localhost:8000")
    url_prefix: str | None = Field(alias="URL_PREFIX", default=None)

    # --- Keycloak admin ---
    keycloak_admin_username: str = Field(alias="KEYCLOAK_ADMIN_USERNAME")
    keycloak_admin_password: str = Field(alias="KEYCLOAK_ADMIN_PASSWORD")

    # --- Cluster Config ---
    cluster_config_path: str | None = Field(default=None, alias="CLUSTER_CONFIG_PATH")

    # --- Misc ---
    environment: str = Field(default="development", alias="ENVIRONMENT")


settings = Settings()
