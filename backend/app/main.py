"""FastAPI application entry point."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import BASE_DIR, settings
from .database import init_db
from .routers import (
    admin_routes,
    auth_routes,
    chat_routes,
    reception_routes,
    staff_routes,
    telegram_routes,
    whatsapp_routes,
)
from .seed import seed_all

app = FastAPI(
    title="AI-Powered Academic Admission Assistance & Visitor Queue System",
    version="1.0.0",
    description=(
        "Receptionist registration, AI assistance, multi-stage admission "
        "workflows, digital queues and WhatsApp-ready communication."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    # Also allow the app served over the LAN IP (phone scanning a reception QR).
    allow_origin_regex=r"https?://[\w.\-]+(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    seed_all()
    # Apply/refresh the official Nandha Engineering College knowledge base.
    # Idempotent - safe on every startup; never trains or replaces the model.
    try:
        from seed_nandha_knowledge import seed_nandha_knowledge

        seed_nandha_knowledge()
    except Exception as exc:  # pragma: no cover - startup must not crash
        print(f"[seed] Nandha knowledge base not applied: {exc}")
    # Start the Telegram bot (long polling) when a token is configured.
    # No-op when disabled/unconfigured; never affects the WhatsApp channel.
    try:
        from .services.telegram_bot import start_telegram_bot

        start_telegram_bot()
    except Exception as exc:  # pragma: no cover - startup must not crash
        print(f"[telegram] bot not started: {exc}")


@app.on_event("shutdown")
def on_shutdown():
    try:
        from .services.telegram_bot import stop_telegram_bot

        stop_telegram_bot()
    except Exception:  # pragma: no cover
        pass


app.include_router(auth_routes.router)
app.include_router(reception_routes.router)
app.include_router(staff_routes.router)
app.include_router(admin_routes.router)
app.include_router(chat_routes.router)
app.include_router(whatsapp_routes.router)
app.include_router(telegram_routes.router)


@app.get("/api/health")
def health():
    return {
        "app": "AI-Powered Academic Admission Assistance & Visitor Queue System",
        "docs": "/docs",
        "status": "running",
    }


# Single-server deployment: when the React app has been built
# (frontend/dist), serve it from here so the whole system runs on one URL.
# In local development (no build) "/" keeps returning the status JSON and the
# Vite dev server on :5173 serves the UI as before.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

if (FRONTEND_DIST / "index.html").is_file():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        file = (FRONTEND_DIST / full_path).resolve()
        if full_path and file.is_file() and FRONTEND_DIST.resolve() in file.parents:
            return FileResponse(file)
        # Client-side routes (/chat, /login, /admin, ...) all load index.html.
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/")
    def root():
        return health()
