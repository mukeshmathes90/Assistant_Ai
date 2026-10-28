"""QR-code helpers for visitor chat links.

Generates a scannable QR that opens the visitor web chat (AI assistant +
live queue tracker) for a registered phone number. The link uses this
machine's LAN IP by default so a visitor's phone on the same Wi-Fi can open it.
"""
import base64
import io
import socket
from urllib.parse import quote

from ..config import settings


def lan_ip() -> str:
    """Best-effort detection of this machine's LAN IP address."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()
    except OSError:
        return "127.0.0.1"


def chat_base_url() -> str:
    """Public base URL of the visitor app (config override or LAN IP)."""
    base = (settings.PUBLIC_BASE_URL or "").strip().rstrip("/")
    if base:
        return base
    return f"http://{lan_ip()}:5173"


def visitor_chat_url(phone: str) -> str:
    return f"{chat_base_url()}/chat?phone={quote(str(phone))}"


def qr_data_uri(text: str) -> str:
    """Return a ``data:image/png;base64,...`` QR image for ``text``."""
    import qrcode

    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
