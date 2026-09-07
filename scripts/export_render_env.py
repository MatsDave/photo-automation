"""Export environment variables and encrypted token files for Render Free deployment."""

import os
from pathlib import Path
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"

IG_TOKEN_FILE = DATA_DIR / "instagram_token.enc"
FB_TOKEN_FILE = DATA_DIR / "facebook_page_token.enc"
TH_TOKEN_FILE = DATA_DIR / "threads_token.enc"


def main() -> None:
    print("=" * 60)
    print("RENDER FREE DEPLOYMENT ENVIRONMENT VARIABLES EXPORT")
    print("=" * 60)
    print("\nCopy the key-value pairs below into your Render Web Service Environment settings:\n")

    env = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}

    # Render standard config
    print("# Service Paths and Models")
    print("DATA_DIR=/tmp/photo-automation")
    print(f"GEMINI_MODEL={env.get('GEMINI_MODEL', 'gemini-3.6-flash')}")
    print("PUBLIC_BASE_URL=https://YOUR-SERVICE.onrender.com")
    print("INSTAGRAM_REDIRECT_URI=https://YOUR-SERVICE.onrender.com/auth/instagram/callback")
    print("FACEBOOK_REDIRECT_URI=https://YOUR-SERVICE.onrender.com/auth/facebook/callback")
    print("THREADS_REDIRECT_URI=https://YOUR-SERVICE.onrender.com/auth/threads/callback")

    print("\n# Security & Session Keys")
    print(f"SESSION_SECRET={env.get('SESSION_SECRET', '')}")
    print(f"TOKEN_ENCRYPTION_KEY={env.get('TOKEN_ENCRYPTION_KEY', '')}")

    print("\n# Telegram & Gemini Credentials")
    print(f"TELEGRAM_BOT_TOKEN={env.get('TELEGRAM_BOT_TOKEN', '')}")
    print(f"TELEGRAM_WEBHOOK_SECRET={env.get('TELEGRAM_WEBHOOK_SECRET', '')}")
    print(f"AUTHORIZED_TELEGRAM_USER_ID={env.get('AUTHORIZED_TELEGRAM_USER_ID', '')}")
    print(f"GEMINI_API_KEY={env.get('GEMINI_API_KEY', '')}")

    print("\n# Meta App IDs and Secrets")
    print(f"INSTAGRAM_APP_ID={env.get('INSTAGRAM_APP_ID', '')}")
    print(f"INSTAGRAM_APP_SECRET={env.get('INSTAGRAM_APP_SECRET', '')}")
    print(f"FACEBOOK_APP_ID={env.get('FACEBOOK_APP_ID', '')}")
    print(f"FACEBOOK_APP_SECRET={env.get('FACEBOOK_APP_SECRET', '')}")
    print(f"THREADS_APP_ID={env.get('THREADS_APP_ID', '')}")
    print(f"THREADS_APP_SECRET={env.get('THREADS_APP_SECRET', '')}")

    print("\n# Encrypted Saved Tokens (for persistent auth across Render Free restarts)")
    if IG_TOKEN_FILE.exists():
        ig_enc = IG_TOKEN_FILE.read_bytes().decode("ascii")
        print(f"INSTAGRAM_TOKEN_ENCRYPTED={ig_enc}")
    else:
        print("# INSTAGRAM_TOKEN_ENCRYPTED= (Connect Instagram locally first or via Render)")

    if FB_TOKEN_FILE.exists():
        fb_enc = FB_TOKEN_FILE.read_bytes().decode("ascii")
        print(f"FACEBOOK_TOKEN_ENCRYPTED={fb_enc}")
    else:
        print("# FACEBOOK_TOKEN_ENCRYPTED= (Connect Facebook locally first or via Render)")

    if TH_TOKEN_FILE.exists():
        th_enc = TH_TOKEN_FILE.read_bytes().decode("ascii")
        print(f"THREADS_TOKEN_ENCRYPTED={th_enc}")
    else:
        print("# THREADS_TOKEN_ENCRYPTED= (Connect Threads locally first or via Render)")

    print("\n" + "=" * 60)
    print("IMPORTANT: Replace YOUR-SERVICE with your actual Render service hostname.")
    print("=" * 60)


if __name__ == "__main__":
    main()
