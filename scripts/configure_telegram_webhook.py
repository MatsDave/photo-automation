"""Register the Telegram webhook after .env has been configured."""

import os
import secrets

import httpx
from dotenv import load_dotenv

load_dotenv()

token = os.environ["TELEGRAM_BOT_TOKEN"]
secret = os.environ["TELEGRAM_WEBHOOK_SECRET"]
base_url = os.environ["PUBLIC_BASE_URL"].rstrip("/")

response = httpx.post(
    f"https://api.telegram.org/bot{token}/setWebhook",
    json={"url": f"{base_url}/telegram/webhook/{secret}", "secret_token": secret, "allowed_updates": ["message", "callback_query"]},
    timeout=30,
)
response.raise_for_status()
result = response.json()
if not result.get("ok"):
    raise SystemExit("Telegram rejected webhook configuration")
print("Telegram webhook configured successfully.")
