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
    VISION_MODEL_PATH: str = "/home/pi/greenhouse/models/strawberry.pt"
    IMAGE_SAVE_DIR: str = "/home/pi/greenhouse/images"
    DEVICE_ID: str = "esp32-gh-01"
    VISION_DEVICE_ID: str = "rpi-gh-01"


config = Settings()
