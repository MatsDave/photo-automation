# Render Deployment Plan

> Superseded: use [RENDER_FREE_SETUP.md](RENDER_FREE_SETUP.md). The user requires
> free services only. render.yaml now uses Free and no persistent disk.

## Objective

Run the existing FastAPI Telegram-to-Instagram backend on a persistent HTTPS
Render service and remove the temporary Cloudflare Tunnel dependency.

The backend already exists in `app/main.py`. This migration adds a Render
Blueprint in `render.yaml` and makes the data directory configurable. No new
application backend is needed.

## Why the paid Render service is the production choice

The current application stores three things locally: the SQLite post database,
downloaded media, and encrypted social tokens. Render Free web services sleep
after inactivity and lose local filesystem changes on restarts/redeploys. A
Telegram webhook needs a service that stays available, and the current local
storage needs a persistent disk.

The Blueprint therefore uses:

- A Render Python Web Service.
- The `starter` paid compute plan so it does not sleep.
- A 1 GB persistent disk mounted at `/var/data`.
- `DATA_DIR=/var/data`, so the database, media, tokens, and logs survive restarts.
- The Singapore region, close to the current timezone and users.

If a free trial is required, deploy without the disk only for a temporary
test. It is not a reliable production setup for this workflow.

## Deployment sequence

### 1. Prepare the repository

1. Create a private GitHub repository and push this project.
2. Include `app/`, `scripts/`, `requirements.txt`, `render.yaml`, `README.md`,
   and this plan.
3. Do not commit `.env`, `data/`, `logs/`, `.venv/`, or token files. They are
   already excluded by `.gitignore`.

### 2. Create the Render service

1. Open Render Dashboard → **New → Blueprint**.
2. Connect the private repository and choose the branch containing `render.yaml`.
3. Render will show the `photo-automation` Web Service and ask for every
   `sync: false` value.
4. Select the paid `starter` plan and keep the persistent disk enabled.
5. Enter the current Instagram, Telegram, and Gemini values from the local
   `.env`. Leave Facebook and Threads blank until those integrations are built.
6. Deploy the Blueprint.

The service URL will look like:

```text
https://photo-automation.onrender.com
```

The exact hostname displayed by Render is authoritative.

### 3. Set production URLs

After Render gives the service URL, update these Render environment variables:

```text
PUBLIC_BASE_URL=https://YOUR-RENDER-HOST.onrender.com
INSTAGRAM_REDIRECT_URI=https://YOUR-RENDER-HOST.onrender.com/auth/instagram/callback
```

Save and redeploy. The service health check must return JSON with `ok: true`:

```text
https://YOUR-RENDER-HOST.onrender.com/health
```

### 4. Update Meta

In the Instagram Business Login settings, remove the temporary Cloudflare
callback and add exactly:

```text
https://YOUR-RENDER-HOST.onrender.com/auth/instagram/callback
```

Reconnect Instagram through:

```text
https://YOUR-RENDER-HOST.onrender.com/auth/instagram/connect
```

This creates a fresh long-lived token on the Render disk. The existing local
token is not copied automatically; reconnecting is safer and avoids moving a
secret file through Git.

### 5. Move Telegram to Render

Update the local `.env` temporarily with the production values for
`PUBLIC_BASE_URL` and `TELEGRAM_WEBHOOK_SECRET`, then run:

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_telegram_webhook.py
```

The script registers:

```text
https://YOUR-RENDER-HOST.onrender.com/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>
```

Verify Telegram's `getWebhookInfo` reports the Render URL and no delivery error.
The local Cloudflare process can then be stopped.

### 6. Production test

1. Open `/health` and confirm Instagram and Telegram workflow configuration are
   true.
2. Send one image to `@himalayanmeditationNZ`.
3. Confirm Gemini returns a quote-first caption.
4. Edit or regenerate once, then approve.
5. Confirm Instagram publishes after media processing completes.
6. Restart/redeploy the Render service and confirm the connected token and post
   history remain available on the persistent disk.

## Environment variable checklist

Required for the active Instagram workflow:

```text
INSTAGRAM_APP_ID
INSTAGRAM_APP_SECRET
INSTAGRAM_REDIRECT_URI
SESSION_SECRET
TOKEN_ENCRYPTION_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
AUTHORIZED_TELEGRAM_USER_ID
GEMINI_API_KEY
GEMINI_MODEL=gemini-3.6-flash
PUBLIC_BASE_URL
DATA_DIR=/var/data
```

Facebook and Threads variables can remain empty until those publishers are
enabled.

## Rollback and operations

- Render keeps deploy history and supports rollback to a previous deploy.
- Use `/health` for the deployment health check.
- Use Render service logs for runtime errors; application logs are also written
  under `/var/data/logs`.
- Rotate the Telegram token immediately if it is ever exposed.
- Rotate the Instagram connection by deleting/reconnecting the token only after
  the new Render callback is saved in Meta.

## Later improvements

1. Replace local SQLite with Render Postgres for easier backups and future
   multi-instance scaling.
2. Move images to S3-compatible object storage instead of the single disk.
3. Add Facebook Page and Threads publishers after their access requirements are
   complete.
4. Add a custom domain so OAuth callback URLs do not change with hosting.
