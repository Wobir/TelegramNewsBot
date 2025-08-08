import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config: Dict[str, Any] = {}
        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            logger.error(f"Файл конфигурации {config_path} не найден")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Ошибка в файле конфигурации {config_path}: {e}")
            raise

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        return self.config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        if key not in self.config:
            raise KeyError(f"Ключ '{key}' не найден в конфигурации")
        return self.config[key]

# Глобальный экземпляр конфигурации
try:
    config_instance = Config()
    API_TOKEN = config_instance["api_token"]
    OWNER_ID = config_instance["owner_id"]
    CHANNEL_ID = config_instance["channel_id"]
    MEDIA_TIMEOUT = config_instance.get("media_timeout", 20)
except Exception as e:
    logger.error(f"Ошибка загрузки конфигурации: {e}")
    raise