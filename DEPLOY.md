# Deploying (one free Render service)

The `Dockerfile` builds the React frontend and serves it from the FastAPI
backend, so the chat, staff/admin pages, API and WhatsApp webhook all run on
one URL.

1. **Database (free, keeps data):** create a project at https://neon.tech and
   copy its connection string (`postgresql://...`).
2. **GitHub:** push this folder to a GitHub repository. `.gitignore` keeps
   `backend/.env`, the venvs, `node_modules` and the local `.db` out of it.
3. **Render:** https://dashboard.render.com -> New -> Blueprint -> pick the
   repository. Render reads `render.yaml` and asks for the secret values:
   - `GEMINI_API_KEY` - your Gemini key
   - `DATABASE_URL` - the Neon connection string
   - `WHATSAPP_*` - WhatsApp Cloud API values (primary channel; see README)
   - `TELEGRAM_BOT_TOKEN` - optional alternative channel
4. Open `https://<your-service>.onrender.com/chat` once the deploy is live.
   Health check: `/api/health`, API docs: `/docs`.

Notes
- The free plan sleeps after ~15 minutes idle; the first request after that
  takes about a minute. The Telegram bot only listens while it is awake.
- Only one copy of the app may poll the same Telegram bot. Set
  `TELEGRAM_POLLING=0` in your local `backend/.env` while the hosted one runs.
- WhatsApp webhook URL (Meta > WhatsApp > Configuration):
  `https://<your-service>.onrender.com/api/whatsapp/webhook`. Because the
  free plan sleeps, the first message after a pause may be answered late;
  Meta retries and duplicates are ignored.
- Reception QR codes use the Render URL automatically
  (override with `PUBLIC_BASE_URL`).
