from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_path: str = "model.pkl"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8003

    use_mlflow: bool = False
    mlflow_tracking_uri: str = "sqlite:///mlflow.db"
    mlflow_model_name: str = "moderation_model"
    mlflow_stage: str = "Production"

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int
    postgres_host: str = "localhost"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
