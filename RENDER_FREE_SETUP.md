# Render Free Setup

The backend runs Python/FastAPI. `render.yaml` uses Render's Free tier with no
paid disk, database, or paid worker. No external paid database is needed.

## Supported Social Platforms

- **Instagram**: Professional/Creator account publishing via Instagram Graph API.
- **Facebook Page**: Direct photo/caption publishing via Meta Graph API.
- **Threads**: Direct photo/caption publishing via Threads Graph API.

All connected platforms are published automatically upon approval from Telegram.

## Deployment Steps

### 1. Prepare Environment & Tokens Locally

Run the helper script to print all your configured variables and encrypted tokens formatted for Render:

```powershell
.\.venv\Scripts\python.exe .\scripts\export_render_env.py
```

This exports all environment settings, including encrypted tokens:
- `INSTAGRAM_TOKEN_ENCRYPTED`
- `FACEBOOK_TOKEN_ENCRYPTED`
- `THREADS_TOKEN_ENCRYPTED`

These encrypted tokens preserve your authentication across Render Free cold starts/restarts without needing a persistent disk.

### 2. Connect Repository on Render

1. Create a private GitHub repository and push `app/`, `scripts/`, `tests/`, `requirements.txt`, `render.yaml`, and `.gitignore`. (Do **not** commit `.env`, `data/`, `logs/`, or `.venv/`).
2. In Render, choose **New > Blueprint** and select the repository.
3. Verify the service is on the **Free** plan and has no disk attached.
4. Fill in the environment variables using the output from `export_render_env.py`.
5. Set `PUBLIC_BASE_URL` to your Render service URL (e.g. `https://photo-automation.onrender.com`).
6. Deploy the Blueprint.

### 3. Verify Health & URLs

Visit your service endpoints:
- `https://YOUR-SERVICE.onrender.com/health` confirms configuration and connected platform status.
- `https://YOUR-SERVICE.onrender.com/ping` returns lightweight keep-alive status.

### 4. Update Meta Redirect URIs

In Meta App settings (Instagram Login, Facebook Login, Threads Login), add the Render redirect URIs:
- `https://YOUR-SERVICE.onrender.com/auth/instagram/callback`
- `https://YOUR-SERVICE.onrender.com/auth/facebook/callback`
- `https://YOUR-SERVICE.onrender.com/auth/threads/callback`

### 5. Register Telegram Webhook to Render

Set `PUBLIC_BASE_URL=https://YOUR-SERVICE.onrender.com` in your local `.env`, and run:

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_telegram_webhook.py
```

### 6. Test Publishing

1. Send a photo to your Telegram bot.
2. The bot drafts a caption with Gemini and sends a preview with **Approve & publish**, **Edit caption**, **Regenerate**, and **Cancel** buttons.
3. Tap **Approve & publish**. The service publishes to all connected platforms and returns a per-platform publication summary.

## Token Lifecycle & Auto-Renewal

- **Instagram & Threads**: Tokens are valid for 60 days. They can be refreshed at any time before expiration by visiting `https://YOUR-SERVICE.onrender.com/auth/refresh` or running:
  ```powershell
  .\.venv\Scripts\python.exe .\scripts\refresh_tokens.py
  ```
- **Facebook Page**: Page tokens derived from long-lived user tokens do not expire.
- If you reconnect via the web UI on Render, copy the new encrypted token from `/auth/refresh` or re-export into Render's environment settings.

## Media Lifecycle & Ephemeral Storage

Render Free uses ephemeral storage at `DATA_DIR=/tmp/photo-automation`.
- Photos downloaded from Telegram are temporarily stored in `/tmp/photo-automation/media`.
- Once publication completes across connected platforms, the service automatically deletes the image file after a 30-second delay (allowing Meta CDNs sufficient time to fetch the media).
- Any stale media files older than 24 hours are automatically pruned on startup.

## Preventing Cold Starts (Optional)

Render Free web services spin down after 15 minutes of inactivity. To keep the service warm:
- Set up a free ping monitor (such as [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com)) to ping `https://YOUR-SERVICE.onrender.com/ping` every 10–14 minutes.

