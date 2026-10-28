"""Application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Reads configuration from environment variables / .env file."""

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-to-a-long-random-secret")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480")
    )

    # SQLite locally; a hosted Postgres URL (e.g. Neon) in production so data
    # survives restarts. SQLAlchemy needs "postgresql://", not "postgres://".
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./college_queue.db"
    ).replace("postgres://", "postgresql://", 1)

    # College identity (used by the AI assistant branding / fallbacks)
    COLLEGE_NAME: str = os.getenv(
        "COLLEGE_NAME", "Nandha Engineering College (Autonomous)"
    )
    COLLEGE_WEBSITE: str = os.getenv("COLLEGE_WEBSITE", "https://nandhaengg.org/")

    # Public base URL of the visitor web app, used to build QR-code chat links.
    # Leave empty to auto-detect this machine's LAN IP (http://<lan-ip>:5173),
    # so phones on the same Wi-Fi can scan and open the app.
    # On Render, RENDER_EXTERNAL_URL (set automatically) is used as the default.
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "") or os.getenv(
        "RENDER_EXTERNAL_URL", ""
    )

    # AI  (rules | ollama | gemini)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "rules").lower()
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")

    # Google Gemini (used when AI_PROVIDER=gemini). Keep the key in .env only.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_API_BASE: str = os.getenv(
        "GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta"
    )

    # WhatsApp Cloud API - primary messaging channel (Telegram is secondary)
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "college_queue_verify")
    WHATSAPP_API_BASE: str = os.getenv(
        "WHATSAPP_API_BASE", "https://graph.facebook.com/v19.0"
    )
    # Meta App Secret: when set, every webhook POST must carry a valid
    # X-Hub-Signature-256 header (HMAC-SHA256 of the raw body).
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")
    # Public WhatsApp number visitors message (digits with country code, e.g.
    # 15551234567 for Meta's test number). Only used for the wa.me link / QR.
    WHATSAPP_BUSINESS_NUMBER: str = os.getenv("WHATSAPP_BUSINESS_NUMBER", "")
    # Country code added to 10-digit numbers stored at the reception desk.
    WHATSAPP_DEFAULT_COUNTRY_CODE: str = os.getenv(
        "WHATSAPP_DEFAULT_COUNTRY_CODE", "91"
    )

    # Telegram Bot API (optional). Uses long polling, so no public URL /
    # webhook is required - it works on a laptop or a client machine as-is.
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_API_BASE: str = os.getenv(
        "TELEGRAM_API_BASE", "https://api.telegram.org"
    )
    TELEGRAM_POLLING: bool = os.getenv("TELEGRAM_POLLING", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


settings = Settings()