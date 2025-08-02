import yaml

# === Config ===
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

API_TOKEN = config["api_token"]
OWNER_ID = config["owner_id"]
CHANNEL_ID = config["channel_id"]
MEDIA_TIMEOUT = config.get("media_timeout", 20)
