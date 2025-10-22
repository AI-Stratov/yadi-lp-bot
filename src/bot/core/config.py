from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Загружаем .env из корня проекта
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


class BotConfig(BaseSettings):
    TOKEN: SecretStr

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


class RedisConfig(BaseSettings):
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


class YandexDiskConfig(BaseSettings):
    PUBLIC_ROOT_URL: str
    POLL_INTERVAL: int = 60
    HTTP_TIMEOUT: float = 10.0

    model_config = SettingsConfigDict(env_file=str(env_path), env_file_encoding="utf-8", extra="allow")


bot_config = BotConfig()
redis_config = RedisConfig()
yadisk_config = YandexDiskConfig()
