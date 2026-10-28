# AI-Powered Academic Admission Assistance & Visitor Queue Management System

A complete working prototype of a receptionist registration, digital queue, multi-stage workflow, AI-assisted chat and admission system for colleges, with **WhatsApp as the primary messaging channel** and Telegram as an alternative.

## Highlights

- **Visitor lifecycle end-to-end** – register → queue → multi-stage workflow → completion
- **Real digital queues** – every admission stage has its own queue with real positions
- **Configurable multi-stage workflows** – different departments/processes follow different steps
- **AI assistant** – answers FAQs from an admin-managed knowledge base; explains live queue/workflow state; never mutates queue order
- **WhatsApp (primary channel)** – official WhatsApp Cloud API webhook: parents chat with the Gemini assistant, registered visitors are recognised by their number and get live queue status and stage updates; signed, validated, de-duplicated and logged
- **Telegram bot (alternative)** – the same AI assistant and live queue status on Telegram (`@Academic_Nandhabot`); no public URL needed (long polling)
- **Three role-based dashboards** – Receptionist, Staff and Admin
- **Local AI** – works offline out of the box (rules-based); optionally plugs into Ollama for a local LLM

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 · Vite · Tailwind CSS |
| Backend | Python 3.10+ · FastAPI · SQLAlchemy 2 · Pydantic v2 |
| Database | SQLite (can be swapped to PostgreSQL easily) |
| AI | Google Gemini · Ollama-compatible LLM · rules-based fallback |
| Auth | JWT with password hashing (PBKDF2 + PyJWT) |
| WhatsApp (primary) | WhatsApp Cloud API webhook + messaging service (env-configured, not hard-coded) |
| Telegram (alternative) | Bot API long polling (env-configured, no public URL required) |

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── models.py           # All ORM models (15 tables)
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── security.py          # Password hashing + JWT
│   │   ├── seed.py              # Realistic demo data seeder
│   │   ├── routers/             # API route modules
│   │   └── services/
│   │       ├── ai_service.py    # AI layer (rules + Ollama)
│   │       ├── queue_engine.py  # Queue position logic
│   │       ├── workflow_engine.py # Stage ordering logic
│   │       ├── visitor_flow.py  # Registration, complete, reassign
│   │       ├── notification_service.py
│   │       ├── whatsapp_service.py # WhatsApp Cloud API client + signature check
│   │       ├── whatsapp_bot.py  # WhatsApp message handling (primary channel)
│   │       ├── messaging.py     # Phone lookup + live summary shared by both bots
│   │       ├── telegram_service.py # Telegram Bot API client
│   │       ├── telegram_bot.py  # Telegram polling + message handling
│   │       ├── qr_service.py    # LAN IP + QR data URIs
│   │       └── helpers.py       # Visitor serialization
│   ├── tests/
│   │   ├── test_flow.py         # End-to-end test (31 checks)
│   │   ├── test_nandha_ai.py    # Nandha knowledge / AI behaviour (23 checks)
│   │   └── test_whatsapp.py     # WhatsApp webhook + Telegram channel (27 checks)
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py                   # uvicorn launcher
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router + role guards
│   │   ├── pages/
│   │   │   ├── Login.jsx        # Role-based login with demo accounts
│   │   │   ├── Receptionist.jsx # Visitor registration + queues
│   │   │   ├── Staff.jsx        # Live queue console + actions
│   │   │   ├── Admin.jsx        # CRUD for all entities + stats
│   │   │   └── Chat.jsx         # WhatsApp-style parent chat
│   │   ├── components/
│   │   │   ├── Layout.jsx       # Sidebar + topbar shell
│   │   │   └── ui.jsx           # Badge, StatCard, Modal, Btn, etc.
│   │   └── lib/
│   │       ├── api.js           # Axios instance with JWT interceptor
│   │       └── auth.jsx         # AuthContext + useAuth hook
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
└── README.md
```

## Database Tables (15)

| Table | Purpose |
|-------|---------|
| `departments` | CSE, ECE, EEE, Mechanical, MBA |
| `rooms` | Counters / rooms with building + floor |
| `users` | All system users (admin, reception, staff) |
| `staff` | Staff profile linked to a user |
| `workflows` | Admission workflow per department (or general) |
| `workflow_stages` | Ordered stages within a workflow |
| `queues` | One real queue per active stage |
| `queue_entries` | Visitor tokens in a queue |
| `visitors` | Every registered visitor |
| `visitor_stage_history` | Audit trail of stage progression |
| `faqs` | Knowledge base (Nandha official FAQs; `source_url`, `source_type`, `last_updated`) |
| `college_information` | College info (hostel, contact, courses …; with source metadata) |
| `notifications` | Per-visitor notification log |
| `chat_messages` | Chat history (USER / AI / SYSTEM) |
| `telegram_sessions` | Telegram chat → visitor link (`chat_id`, `username`, `visitor_id`) |
| `whatsapp_messages` | WhatsApp traffic log (IN/OUT, unique `wa_message_id` for duplicate protection, delivery status) |

## Quick Start (one command)

On Windows, after copying the project to a machine with **Python 3.10+** and
**Node.js 18+** installed, just double-click / run:

```bat
start_all.bat
```

It creates the Python venv if missing, installs backend and frontend
dependencies, creates `backend/.env` from the example when absent, then opens
the backend (`http://localhost:8000`) and frontend (`http://localhost:5173`)
in separate windows and launches the browser. To stop, close the two
"Nandha ..." windows.

> The Telegram bot starts automatically on the backend and needs no extra
> step (set `TELEGRAM_BOT_TOKEN` in `backend/.env`).

## Installation & Run Instructions

### 1. Backend

```bash
cd backend

# Create virtual environment (Python 3.10+ required)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # macOS / Linux

pip install -r requirements.txt

# Copy and edit .env (defaults work for local demo)
cp .env.example .env

# Run the server (auto-creates DB + seeds demo data on first start)
python run.py
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend

npm install

# Dev server (proxies /api to the backend)
npm run dev
# Open http://localhost:5173
```

### 3. Nandha Engineering College Knowledge Base

The AI assistant answers from the official Nandha Engineering College
(Autonomous) knowledge base, built **only** from <https://nandhaengg.org/>.
The knowledge is stored in the existing `faqs` and `college_information`
tables (no new tables). It is applied automatically on backend startup, and
can also be seeded/updated manually at any time:

```bash
cd backend
python seed_nandha_knowledge.py
```

The script is idempotent (upserts by `key` / `category + question`): running it
again updates records instead of duplicating them. It seeds 22 college-info
records and 68 FAQs across 11 categories (College, Admission, Courses,
Departments, Contact, Transport, Hostel, Placement, Facilities, Academics,
General). Every record stores `source_url`, `source_type` and `last_updated`.
The AI model is **not** trained or fine-tuned - the knowledge base is injected
into the prompt (Ollama `llama3.2`) or answered offline by the rules engine.

> Note: fees, cut-offs, and admission dates are intentionally answered as
> "not published on the website - contact the Admission Office" so the AI
> never invents figures.

### 4. Reception QR Codes (Scan to Chat)

The Reception Desk can show a QR code that opens the visitor web app on a
phone - the AI assistant plus the live queue tracker for that visitor.

- **Desk Chat QR** (button on the Reception Desk) - a general QR that opens
  the Nandha AI admission chat for walk-in visitors.
- **Per-visitor QR** - the QR button on an Active Visitors row, or the QR shown
  automatically after registering a visitor, encodes
  `http://<pc-lan-ip>:5173/chat?phone=<phone>`.

For phone scanning to work, the phone and the PC must be on the same Wi-Fi and
the dev server must be reachable on the LAN (already enabled via `host: true`
in `frontend/vite.config.js`; `npm run dev` prints the `Network:` URL). If you
host the app under a real domain, set `PUBLIC_BASE_URL` in `backend/.env` to
that URL so QR links use it instead of the auto-detected LAN IP.

### 5. Telegram Bot (alternative channel)

The same AI assistant runs on Telegram via the bot **@Academic_Nandhabot**
(<https://t.me/Academic_Nandhabot>). Registration is optional: a walk-in
visitor links their chat to their visit by sending the **mobile number they
registered at the reception**, and can then see their live queue status.

- **Commands** – `/start`, `/help`, `/status`, `/unlink`.
- **Chat flow** – `/start` → send the registered mobile number → the bot links
  the chat to that visitor and answers admission questions plus live queue
  status. Linked messages are stored in `chat_messages`, so they also appear in
  the web chat/dashboard.
- **No public URL required** – the bot uses long polling, so it works behind a
  router/NAT and on a client PC. It starts with the backend.
- **Reception UI** – the **Telegram Bot** button on the Reception Desk shows a
  QR code that opens the bot on a phone.

Configuration in `backend/.env`:

```env
TELEGRAM_BOT_TOKEN=your_token_from_BotFather
TELEGRAM_POLLING=1        # set to 0 to disable the bot
```

> Keep the real token only in `backend/.env` - never commit it. The bot is
> disabled automatically when the token is empty.

### 6. Tests

```bash
cd backend
python tests/test_flow.py        # visitor lifecycle end-to-end (31 checks)
python tests/test_nandha_ai.py   # Nandha knowledge / AI behaviour (23 checks)
```

`test_flow.py` registers V121 (Raj Kumar), runs the AI chat, calls the visitor
through staff, completes all 6 ECE stages automatically, then registers a
help-desk visitor. `test_nandha_ai.py` covers the 18 required college-knowledge
and live-context cases, including hallucination prevention.

## Demo Accounts

| Role | Username | Password |
|------|----------|----------|
| Admin | admin | admin123 |
| Receptionist | reception | reception123 |
| Counsellor (Staff) | priya | staff123 |
| Eligibility Officer | arun | staff123 |
| Document Verification | kavita | staff123 |
| Accounts | suresh | staff123 |
| Admission Officer | anita | staff123 |
| Registrar | vikram | staff123 |
| Help Desk | divya | staff123 |

## Demo Scenario Walkthrough

1. **Receptionist** logs in at `/login` → lands on Reception Desk.
2. Click **Register Visitor** → fill Name: *Raj Kumar*, Phone: *9876543210*, Purpose: *Admission*, Department: *ECE* → **Register Visitor**.
3. System generates **V121**, places them in **ECE Counselling** queue.
4. Open `/chat?phone=9876543210` → parent sees welcome message + live tracker.
5. Ask "What documents are required for ECE admission?" → AI answers from knowledge base.
6. Ask "How many people are before me?" → AI reports live queue position.
7. Staff member logs in (`priya` / `staff123`) → Staff Queues → sees V121 in ECE Counselling queue.
8. Click **Call Next** → V121 is called → parent receives "Your turn" notification.
9. Click **Complete Stage** → system auto-advances V121 to **Eligibility Verification**.
10. Repeat for each subsequent stage (Eligibility → Document Verification → Accounts → Admission Confirmation → Registration).
11. After Registration, visitor status becomes **COMPLETED** and a congratulations notification is sent.
12. Second parent: register with Department: *Not sure / Needs Help Desk* → routed to **Counselling / Help Desk** workflow.

## AI Service Architecture

```
WhatsApp Webhook (primary) / Telegram Bot / Chat UI
        │
    Backend API
        │
    AIService  (abstract interface)
        │
    ┌───┴──────────────────┐
    │                      │
RulesBasedAIService    OllamaAIService
    │                      │
Knowledge Base +      Ollama REST API
Visitor Context       + Knowledge Base
(Fast, offline)       (Optional, local LLM)
```

The AI is read-only: it answers questions but **never** modifies queue positions or workflow state.

To enable Ollama (check your pulled models with `ollama list` first):
```env
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3:8b
```

With Ollama enabled the assistant behaves like a full chatbot: it answers
admission/campus questions from the Nandha knowledge base, reports live queue
status, and handles greetings, small talk and general questions naturally
(English or Tamil/Tanglish). It also remembers the recent conversation. If the
configured `OLLAMA_MODEL` was never pulled, it automatically uses any available
pulled model instead of failing.

## WhatsApp Integration (primary channel)

WhatsApp is the main way parents and students reach the assistant. Telegram
and the web chat keep working as alternatives.

```
Parent WhatsApp ──> Meta ──> POST /api/whatsapp/webhook
                                │ verify X-Hub-Signature-256, validate,
                                │ skip duplicates, log (whatsapp_messages)
                                ▼
                 whatsapp_bot  ──> shared AIService (Gemini + Nandha KB
                                │    + live visitor/queue context)
                                ▼
                 whatsapp_service ──> Graph API /<PHONE_NUMBER_ID>/messages
```

| Endpoint | Purpose |
|----------|---------|
| `GET /api/whatsapp/webhook` | Meta verification handshake (`hub.mode`, `hub.verify_token`, `hub.challenge`) |
| `POST /api/whatsapp/webhook` | Inbound messages + delivery statuses |
| `GET /api/whatsapp/status` | Public channel info + wa.me QR (no secrets) |
| `GET /api/whatsapp/messages` | Recent message log (staff login required) |

**Behaviour**

- A visitor who messages from the number they registered with is recognised
  automatically (no linking step): `status` shows the live queue summary,
  `help` / `menu` shows the welcome, anything else goes to the AI assistant
  with their live context and chat memory. Their messages also appear in the
  web chat history.
- Unregistered numbers get the same AI assistant, with memory taken from the
  WhatsApp log.
- Registration, "your turn", next-stage and completion notifications are sent
  to the visitor's WhatsApp (10-digit numbers get `WHATSAPP_DEFAULT_COUNTRY_CODE`).
- Non-text messages (images, voice, ...) get a polite "text only" reply.

**Security**

- Secrets live only in `backend/.env` / the host's environment; they are never
  returned by the API, sent to the frontend or printed in logs.
- With `WHATSAPP_APP_SECRET` set, every webhook POST must carry a valid
  `X-Hub-Signature-256` (HMAC-SHA256 of the raw body); otherwise 403. Leave it
  empty only for local testing.
- Payloads over 1 MB are rejected, malformed JSON returns 400, events for
  another phone number ID are ignored, and each `wamid` is processed once
  (Meta retries do not produce duplicate replies).
- Replies run in a background task so Meta receives `200 OK` immediately.

**Configuration** (`backend/.env`):

```env
WHATSAPP_ACCESS_TOKEN=          # Meta access token (system-user token in production)
WHATSAPP_PHONE_NUMBER_ID=       # from WhatsApp > API Setup
WHATSAPP_VERIFY_TOKEN=          # any random string, also entered in Meta
WHATSAPP_APP_SECRET=            # App settings > Basic > App secret
WHATSAPP_BUSINESS_NUMBER=       # e.g. 15551234567 (only for the wa.me link / QR)
WHATSAPP_DEFAULT_COUNTRY_CODE=91
WHATSAPP_API_BASE=https://graph.facebook.com/v19.0
```

### Setting up WhatsApp with Meta's test number (development)

1. Create an app at <https://developers.facebook.com> (type **Business**) and
   add the **WhatsApp** product. Meta gives you a free **test phone number**.
2. In **WhatsApp > API Setup** copy the temporary access token and the
   **Phone number ID** into `WHATSAPP_ACCESS_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID`.
   Add up to 5 recipient numbers you will test with (Meta sends each a code);
   the test number can only message these verified numbers.
3. Copy **App settings > Basic > App secret** into `WHATSAPP_APP_SECRET`, and
   choose any `WHATSAPP_VERIFY_TOKEN`.
4. Expose the backend over HTTPS (the deployed Render URL, or ngrok locally)
   and in **WhatsApp > Configuration** set the callback URL to
   `https://<your-host>/api/whatsapp/webhook` with the same verify token.
   Click **Verify and save**, then subscribe to the **messages** field.
5. Restart the backend and send "hi" from a verified number to the test
   number. Check `GET /api/whatsapp/messages` (staff login) if no reply arrives.

The temporary token expires after about 24 hours; replace it or use a
system-user token.

### Going to production

Requires the college's Meta Business account and approvals that this project
cannot assume:

- Business verification in Meta Business Manager and a real phone number
  added to the WhatsApp Business Account (display name approved).
- A **permanent system-user access token** with `whatsapp_business_messaging`
  and `whatsapp_business_management` permissions.
- Free-form replies only work within 24 hours of the user's last message.
  Proactive notifications outside that window (e.g. "your turn" to a visitor
  who never messaged) need **approved message templates**, which are not
  implemented yet.
- App switched to **Live** mode, with a privacy policy URL.

### Public link via ngrok (optional)

When `ngrok` is installed, `start_all.bat` automatically opens a public tunnel
to the **whole web app** (the frontend on port 5173). Because Vite proxies
`/api` to the backend, a single ngrok link exposes the dashboards (login,
receptionist, staff, admin, chat) and the API - including the WhatsApp
webhook:

```text
https://<your-ngrok-url>.ngrok-free.dev                 # the app itself
https://<your-ngrok-url>.ngrok-free.dev/api/whatsapp/webhook   # webhook callback
```

`start_all.bat` also writes the ngrok URL into `PUBLIC_BASE_URL` in
`backend/.env` before starting the backend, so the reception QR codes encode
the public link (visitors can scan from anywhere, not just the Wi-Fi). When
ngrok is not installed, the launcher clears `PUBLIC_BASE_URL` again and QR
codes fall back to the LAN IP.

Set the WhatsApp **Verify Token** to your `WHATSAPP_VERIFY_TOKEN` from
`backend/.env` so the GET verification handshake succeeds.

> ngrok free shows a one-time "Visit Site" interstitial the first time a
> browser opens the link; after clicking through, the app loads normally.

## How the Queue + Workflow Engine Works

1. **Registration** → system picks workflow by department (or Help Desk if unknown) → first stage → visitor enqueued.
2. **Staff calls next** → earliest WAITING entry becomes CALLED → visitor notified.
3. **Staff completes stage** → current queue entry marked COMPLETED → next active stage found → visitor auto-enqueued → next-stage notification sent.
4. **Workflow complete** (no next stage) → visitor status = COMPLETED → congratulations notification.
5. **Reassign** → current entry cancelled → visitor placed in target stage queue.

The AI assistant never calls any of these operations. It only reads state and answers questions.

## Configuration

All secrets and environment-specific settings live in `.env` (copy from `.env.example`). Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | *(must be changed)* | JWT signing key |
| `DATABASE_URL` | `sqlite:///./college_queue.db` | Database connection |
| `AI_PROVIDER` | `rules` | `rules`, `ollama` or `gemini` |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini key (when `AI_PROVIDER=gemini`) |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Gemini model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3:8b` | Model to use (auto-falls back to any pulled model) |
| `WHATSAPP_ACCESS_TOKEN` | *(empty)* | WhatsApp Cloud API token (primary channel) |
| `WHATSAPP_PHONE_NUMBER_ID` | *(empty)* | WhatsApp phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | `college_queue_verify` | Webhook verification token |
| `WHATSAPP_APP_SECRET` | *(empty)* | Meta app secret; enables webhook signature checks |
| `WHATSAPP_BUSINESS_NUMBER` | *(empty)* | College WhatsApp number for the wa.me link / QR |
| `WHATSAPP_DEFAULT_COUNTRY_CODE` | `91` | Added to 10-digit visitor numbers |
| `TELEGRAM_BOT_TOKEN` | *(empty)* | BotFather token (enables the Telegram bot, alternative channel) |
| `TELEGRAM_POLLING` | `1` | `1` to run the bot, `0` to disable |
| `PUBLIC_BASE_URL` | *(empty)* | Public app URL for QR codes; empty = auto LAN IP |

## License

Academic project — for educational and demonstration purposes.
