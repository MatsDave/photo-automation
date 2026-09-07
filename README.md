# Photo Automation Backend

This is the first implementation slice for the social-posting automation: a
secure Instagram OAuth callback. It connects a Professional Instagram account
and stores the resulting token encrypted on the local machine. Telegram intake
and publishing will be added next.

It also includes the Facebook Page and Threads OAuth callbacks. Configure their
app credentials in `.env` before opening their connection links.

## Instagram approval workflow

Set the Telegram and Gemini values in `.env`, then register the webhook:

```powershell
.\.venv\Scripts\python.exe .\scripts\configure_telegram_webhook.py
```

The webhook URL must stay public and HTTPS. Forward a photo to the approved
Telegram bot user: it creates a caption draft and sends Approve, Edit,
Regenerate, and Cancel buttons. Only Approve triggers Instagram publishing.

For free hosting follow [RENDER_FREE_SETUP.md](RENDER_FREE_SETUP.md).
The included render.yaml uses Free compute and temporary storage, with no disk.

## Run locally

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Create `.env` by copying `.env.example`, then generate the two local secrets:

   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

4. Start the service:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

`http://127.0.0.1:8000/health` confirms that the service is running. It is not
yet usable by Instagram because OAuth requires a public HTTPS callback URL.

## Expose the callback for development

With a tunnel such as Cloudflare Tunnel, run:

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

It prints a temporary URL similar to `https://example.trycloudflare.com`.
Set this in `.env`:

```text
INSTAGRAM_REDIRECT_URI=https://example.trycloudflare.com/auth/instagram/callback
```

Then save the **exact same** URL in Meta's Instagram **Redirect URL** field.
Restart Uvicorn after changing `.env`.

Visit `https://example.trycloudflare.com/auth/instagram/connect` and log in as
the accepted Instagram Tester. On success, the encrypted local token is stored
at `data/instagram_token.enc`.

## Security

- Keep the app in Development mode for this test.
- Do not put app secrets/tokens in Telegram, screenshots, Git, or source code.
- A temporary tunnel URL changes every time it is restarted; update both `.env`
  and Meta when it changes.
- For production, replace the local encrypted file with a managed secret store
  and use a stable HTTPS domain.
