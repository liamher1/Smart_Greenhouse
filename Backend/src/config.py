from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )

    DB_USER: str = "postgres"
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int
    MQTT_BROKER_IP: str
    MQTT_PORT: int
    MQTT_TOPIC_PREFIX: str = "greenhouse"


config = Settings()
