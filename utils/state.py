from collections import defaultdict
from typing import Dict, Any, List
import asyncio

class StateManager:
    def __init__(self):
        # Кэш сообщений, ожидающих модерации
        self.ideas_cache: Dict[int, Dict[str, Any]] = {}
        
        # Последние медиа для подписи
        self.user_last_media: Dict[int, Dict[str, Any]] = defaultdict(dict)
        
        # Альбомы
        self.media_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.media_group_tasks: Dict[str, asyncio.Task] = {}
    
    def clear_expired_data(self, max_age: int = 3600) -> None:
        """Очистка устаревших данных из кэша"""
        import time
        current_time = time.time()
        
        # Очистка ideas_cache
        expired_keys = [
            key for key, value in self.ideas_cache.items()
            if current_time - value.get('timestamp', 0) > max_age
        ]
        for key in expired_keys:
            self.ideas_cache.pop(key, None)
        
        # Очистка user_last_media
        expired_users = [
            user_id for user_id, data in self.user_last_media.items()
            if current_time - data.get('time', 0) > max_age
        ]
        for user_id in expired_users:
            self.user_last_media.pop(user_id, None)

# Глобальный экземпляр менеджера состояний
state_manager = StateManager()