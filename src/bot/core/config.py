from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class BotConfig(BaseSettings):
    TOKEN: SecretStr
    SUPERUSER_ID: int | None = None

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


class RedisConfig(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_KEY_PREFIX: str = "yadi-lp"

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


class YandexDiskConfig(BaseSettings):
    PUBLIC_ROOT_URL: str
    POLL_INTERVAL: int = 600
    HTTP_TIMEOUT: float = 10.0

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


class NotificationsConfig(BaseSettings):
    """Настройки интервалов для уведомлений."""
    NOTIFICATION_CHECK_INTERVAL: int = 300  # периодичность проверки очереди и планировщика

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")
