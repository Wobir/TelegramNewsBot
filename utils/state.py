from collections import defaultdict

# Кэш сообщений, ожидающих модерации
ideas_cache = {}

# Последние медиа для подписи
user_last_media = defaultdict(dict)

# Альбомы
media_groups = defaultdict(list)
media_group_tasks = {}
