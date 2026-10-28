"""WhatsApp Cloud API channel tests (offline - the Graph API is mocked).

Covers: webhook verification, signature check, payload validation,
duplicate-event protection, AI replies through the shared assistant,
registered-visitor status, unsupported message types, delivery statuses,
registration notifications, message logging and the public status endpoint.
"""
import hashlib
import hmac
import json
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/whatsapp.db"
os.environ["AI_PROVIDER"] = "rules"
os.environ["TELEGRAM_POLLING"] = "0"  # keep tests offline (no bot polling)
os.environ["WHATSAPP_ACCESS_TOKEN"] = "test-access-token"
os.environ["WHATSAPP_PHONE_NUMBER_ID"] = "1234567890"
os.environ["WHATSAPP_VERIFY_TOKEN"] = "test-verify-token"
os.environ["WHATSAPP_APP_SECRET"] = "test-app-secret"
os.environ["WHATSAPP_BUSINESS_NUMBER"] = "+1 555 000 1111"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ChatMessage, WhatsAppMessage  # noqa: E402

CHECKS = {"passed": 0, "failed": 0}
SENT = []  # outbound Graph API calls captured by the fake httpx.post
_real_post = httpx.post


def check(name, cond, extra=""):
    if cond:
        CHECKS["passed"] += 1
        print(f"  [PASS] {name}")
    else:
        CHECKS["failed"] += 1
        print(f"  [FAIL] {name} {extra}")
    assert cond, f"{name} failed {extra}"


def fake_post(url, *args, **kwargs):
    if "graph.facebook.com" not in str(url):
        return _real_post(url, *args, **kwargs)
    SENT.append({"url": url, "json": kwargs.get("json"),
                 "headers": kwargs.get("headers")})
    return httpx.Response(
        200,
        json={"messages": [{"id": f"wamid.OUT{len(SENT)}"}]},
        request=httpx.Request("POST", url),
    )


def sign(body: bytes) -> str:
    return "sha256=" + hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()


def text_event(wa_id, phone, text, msg_type="text"):
    msg = {"from": phone, "id": wa_id, "timestamp": "1700000000", "type": msg_type}
    if msg_type == "text":
        msg["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "WABA",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550001111",
                                 "phone_number_id": "1234567890"},
                    "contacts": [{"wa_id": phone, "profile": {"name": "Parent"}}],
                    "messages": [msg],
                },
            }],
        }],
    }


def post_event(client, payload, signed=True):
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signed:
        headers["X-Hub-Signature-256"] = sign(body)
    return client.post("/api/whatsapp/webhook", content=body, headers=headers)


def last_reply_to(phone):
    for call in reversed(SENT):
        if call["json"]["to"] == phone:
            return call["json"]["text"]["body"]
    return None


def login(client, username, password):
    r = client.post("/api/auth/login",
                    json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main():
    httpx.post = fake_post
    try:
        run()
    finally:
        httpx.post = _real_post
    print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
    assert CHECKS["failed"] == 0


def run():
    with TestClient(app) as client:
        print("== Webhook verification ==")
        r = client.get("/api/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": "test-verify-token",
            "hub.challenge": "CHALLENGE_123"})
        check("verify echoes challenge as plain text",
              r.status_code == 200 and r.text == "CHALLENGE_123", r.text)
        r = client.get("/api/whatsapp/webhook", params={
            "hub.mode": "subscribe", "hub.verify_token": "wrong",
            "hub.challenge": "x"})
        check("wrong verify token rejected", r.status_code == 403)

        print("== Security + validation ==")
        payload = text_event("wamid.A1", "919000000001", "Is hostel available?")
        r = post_event(client, payload, signed=False)
        check("unsigned POST rejected", r.status_code == 403)
        body = json.dumps(payload).encode()
        r = client.post("/api/whatsapp/webhook", content=body, headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=" + "0" * 64})
        check("bad signature rejected", r.status_code == 403)
        bad = b"{not json"
        r = client.post("/api/whatsapp/webhook", content=bad,
                        headers={"X-Hub-Signature-256": sign(bad)})
        check("invalid JSON rejected", r.status_code == 400)
        other = text_event("wamid.OTHER", "919000000001", "hi")
        other["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = "999"
        r = post_event(client, other)
        check("event for another phone number ignored",
              r.status_code == 200 and r.json()["queued"] == 0, r.text)

        print("== AI reply (unregistered number) ==")
        r = post_event(client, payload)
        check("signed message accepted", r.status_code == 200
              and r.json()["queued"] == 1, r.text)
        reply = last_reply_to("919000000001")
        check("reply sent through the Cloud API", reply is not None)
        check("reply comes from the college knowledge base",
              reply and "hostel" in reply.lower(), (reply or "")[:120])
        call = SENT[-1]
        check("sent to configured phone number id",
              "/1234567890/messages" in call["url"], call["url"])
        check("access token only in the Authorization header",
              call["headers"]["Authorization"] == "Bearer test-access-token"
              and "test-access-token" not in json.dumps(call["json"]))

        print("== Duplicate protection ==")
        before = len(SENT)
        r = post_event(client, payload)
        check("duplicate event not answered twice",
              r.status_code == 200 and r.json()["queued"] == 0
              and len(SENT) == before, r.text)

        print("== Unsupported type ==")
        r = post_event(client, text_event("wamid.IMG", "919000000001", "", "image"))
        check("image gets a text-only notice",
              "text messages" in (last_reply_to("919000000001") or ""))

        print("== Registered visitor (reuses reception + queue data) ==")
        reception = login(client, "reception", "reception123")
        depts = client.get("/api/reception/departments", headers=reception).json()
        ece = next(d for d in depts if d["code"] == "ECE")
        before = len(SENT)
        r = client.post("/api/reception/visitors", headers=reception, json={
            "full_name": "Priya S", "phone": "9876500001", "purpose": "Admission",
            "department_id": ece["id"], "remarks": "WhatsApp test",
            "needs_help_desk": False})
        check("visitor registered", r.status_code == 200, r.text[:120])
        visitor = r.json()
        check("registration notification sent on WhatsApp with country code",
              any(c["json"]["to"] == "919876500001" for c in SENT[before:]))

        post_event(client, text_event("wamid.S1", "919876500001", "status"))
        reply = last_reply_to("919876500001") or ""
        check("status command shows live summary",
              visitor["visitor_code"] in reply and "Stage" in reply, reply[:160])

        post_event(client, text_event("wamid.S2", "919876500001",
                                      "What is my current stage?"))
        reply = last_reply_to("919876500001") or ""
        check("AI answers with live visitor context", "Counselling" in reply,
              reply[:160])

        db = SessionLocal()
        try:
            chat_rows = db.query(ChatMessage).filter(
                ChatMessage.visitor_id == visitor["id"],
                ChatMessage.sender.in_(["USER", "AI"])).count()
            check("WhatsApp chat mirrored to the visitor's chat history",
                  chat_rows >= 4, str(chat_rows))
            inbound = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.wa_message_id == "wamid.S2").one()
            check("inbound message logged as REPLIED with visitor link",
                  inbound.status == "REPLIED"
                  and inbound.visitor_id == visitor["id"], inbound.status)
            out_id = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.direction == "OUT").order_by(
                WhatsAppMessage.id.desc()).first().wa_message_id
        finally:
            db.close()

        print("== Delivery statuses ==")
        status_event = {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {
                "metadata": {"phone_number_id": "1234567890"},
                "statuses": [{"id": out_id, "status": "read",
                              "recipient_id": "919876500001"}]}}]}],
        }
        r = post_event(client, status_event)
        db = SessionLocal()
        try:
            row = db.query(WhatsAppMessage).filter(
                WhatsAppMessage.wa_message_id == out_id).one()
            check("read receipt updates outbound log", row.status == "READ",
                  row.status)
        finally:
            db.close()

        print("== Status + logs endpoints ==")
        s = client.get("/api/whatsapp/status").json()
        check("status shows primary channel + wa.me link",
              s["enabled"] and s["primary"]
              and s["chat_link"] == "https://wa.me/15550001111?text=Hi"
              and s["qr"].startswith("data:image/png"), str(s)[:160])
        check("status never exposes secrets",
              "test-access-token" not in json.dumps(s)
              and "test-app-secret" not in json.dumps(s))
        r = client.get("/api/whatsapp/messages")
        check("message log requires login", r.status_code == 401, r.status_code)
        r = client.get("/api/whatsapp/messages", headers=reception)
        check("staff can read the message log",
              r.status_code == 200 and len(r.json()) >= 5, r.status_code)

        print("== Telegram still available ==")
        r = client.get("/api/telegram/status", headers=reception)
        check("telegram status endpoint unchanged", r.status_code == 200,
              r.status_code)

        from app.services import telegram_bot
        from app.services.telegram_service import get_telegram_service

        tg_sent = []
        tg = get_telegram_service()
        original_send = tg.send_text
        tg.send_text = lambda chat_id, text: tg_sent.append((chat_id, text))
        db = SessionLocal()
        try:
            telegram_bot.handle_update(db, {"message": {
                "chat": {"id": 555}, "from": {"username": "parent"},
                "text": "9876500001"}})
            telegram_bot.handle_update(db, {"message": {
                "chat": {"id": 555}, "text": "Is hostel available?"}})
        finally:
            db.close()
            tg.send_text = original_send
        check("telegram links a visitor by mobile number",
              tg_sent and visitor["visitor_code"] in tg_sent[0][1],
              str(tg_sent[:1])[:160])
        check("telegram answers through the same AI service",
              len(tg_sent) == 2 and "hostel" in tg_sent[1][1].lower(),
              str(tg_sent[1:])[:160])


if __name__ == "__main__":
    main()
    sys.exit(0)
