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

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
