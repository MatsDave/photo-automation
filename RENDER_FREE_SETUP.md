# Render Free setup (replaces the earlier paid deployment plan)

The backend remains Python/FastAPI. render.yaml now selects Free and has no
disk, database, or paid worker. No Supabase is needed.

## Deploy

1. Create a private GitHub repository. Upload app/, scripts/, requirements.txt,
   render.yaml, and .gitignore. Exclude .env, data/, logs/, and .venv/.
2. In Render choose New > Blueprint and connect the repository. Verify Free is
   selected and no disk is listed. The code has not yet been uploaded/deployed.
3. Copy Instagram, Telegram, Gemini and encryption/session settings from local
   .env into Render Environment. Keep Gemini billing disabled for free quotas.
4. Open data/instagram_token.enc locally; paste its encrypted contents into
   Render's INSTAGRAM_TOKEN_ENCRYPTED variable. Use the same TOKEN_ENCRYPTION_KEY
   as locally. Never commit these values. This keeps credentials across restarts.
5. Set these URLs using the actual hostname assigned by Render:

```text
PUBLIC_BASE_URL=https://YOUR-SERVICE.onrender.com
INSTAGRAM_REDIRECT_URI=https://YOUR-SERVICE.onrender.com/auth/instagram/callback
DATA_DIR=/tmp/photo-automation
```

6. Deploy and verify /health. This verifies configuration, not remote credentials.
7. Add the new Instagram callback URI in Meta for future reconnections. A valid
   existing token can still be used without reconnecting just to change hosts.
8. Set PUBLIC_BASE_URL in local .env to the Render URL and make sure the Telegram
   webhook secret matches Render. Run locally:

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_telegram_webhook.py
```

9. Send a photo to @Mitsys_bot, review and approve the caption. After verifying
   publication, stop the local backend and Cloudflare tunnel.

## Runtime

Build: pip install -r requirements.txt

Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-access-log

The service uses temporary files for images and SQLite drafts; no permanent
photo storage is provisioned. Files currently stay until the instance is
recycled; immediate post-publication cleanup is not implemented. Restarting may
lose drafts and in-process jobs. Resend photos if needed. Render Free sleeps
when idle, so initial replies may be delayed; it is not continuously running.

The Instagram token still expires. Automatic renewal is not yet implemented;
future reconnection tokens must also be saved into the Render environment.

Sources: https://render.com/docs/free and https://render.com/docs/deploy-fastapi
