"""Nandha Engineering College AI knowledge-base tests.

Covers the 18 required cases:
  1 college name          2 address            3 courses
  4 departments           5 UG admission       6 PG admission
  7 admission contact     8 transport          9 hostel
 10 placement            11 unknown (safe)    12 visitor ID
 13 queue position       14 current stage     15 next workflow stage
 16 unknown department   17 Tamil/Tanglish    18 hallucination prevention

Runs against the live FastAPI app with a temporary SQLite DB. The app startup
seeds the demo data and then the official Nandha knowledge base (rules provider;
no model is trained or fine-tuned).
"""
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/nandha_ai.db"
os.environ["AI_PROVIDER"] = "rules"
os.environ["TELEGRAM_POLLING"] = "0"  # keep tests offline (no bot polling)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CollegeInformation, FAQ  # noqa: E402
from app.nandha_knowledge import COLLEGE_INFO, FAQS  # noqa: E402

CHECKS = {"passed": 0, "failed": 0}


def check(name, cond, extra=""):
    if cond:
        CHECKS["passed"] += 1
        print(f"  [PASS] {name}")
    else:
        CHECKS["failed"] += 1
        print(f"  [FAIL] {name} {extra}")
    assert cond, f"{name} failed {extra}"


def ask(client, phone, message):
    r = client.post("/api/chat/send", json={"phone": phone, "message": message})
    assert r.status_code == 200, r.text
    return r.json()


def login(client, username, password):
    r = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main():
    with TestClient(app) as client:
        # ---- Seed verification ------------------------------------------
        print("== Knowledge base seeded ==")
        db = SessionLocal()
        active_faqs = db.query(FAQ).filter(FAQ.is_active.is_(True)).count()
        active_info = (
            db.query(CollegeInformation)
            .filter(CollegeInformation.is_active.is_(True))
            .count()
        )
        official_faqs = (
            db.query(FAQ)
            .filter(FAQ.is_active.is_(True), FAQ.source_url != "")
            .count()
        )
        db.close()
        check("Nandha FAQs seeded", active_faqs >= len(FAQS),
              f"active={active_faqs} expected>={len(FAQS)}")
        check("all Nandha FAQs carry a source URL", official_faqs >= len(FAQS))
        check("Nandha college info seeded", active_info >= len(COLLEGE_INFO))

        unregistered = "9000000000"

        # ---- 1-10: general college knowledge (no visitor) ---------------
        print("== College knowledge ==")
        a = ask(client, unregistered, "What is the name of the college?")["message"]
        check("1. college name", "Nandha" in a, a[:80])

        a = ask(client, unregistered, "Where is the college located?")["message"]
        check("2. address", "Erode" in a and ("638 052" in a or "638052" in a), a[:120])

        a = ask(client, unregistered, "What courses are offered?")["message"]
        check("3. courses", "B.Tech" in a and "MBA" in a, a[:120])

        a = ask(client, unregistered, "Which departments are offered?")["message"]
        check("4. departments", "ECE" in a and ("CSE" in a or "Computer" in a), a[:120])

        a = ask(client, unregistered,
                "What is the eligibility for B.Tech admission?")["message"]
        check("5. UG admission", "Physics" in a and "45%" in a, a[:160])

        a = ask(client, unregistered,
                "What is the eligibility for MBA admission?")["message"]
        check("6. PG admission", "MBA" in a and "50%" in a, a[:160])

        a = ask(client, unregistered,
                "What is the admission office contact?")["message"]
        check("7. admission contact",
              "7373714477" in a or "04294" in a, a[:140])

        a = ask(client, unregistered, "Is college transport available?")["message"]
        check("8. transport", "bus" in a.lower() or "49" in a, a[:140])

        a = ask(client, unregistered, "Is hostel available?")["message"]
        check("9. hostel", "hostel" in a.lower()
              and ("Boys" in a or "boys" in a or "men" in a.lower()), a[:160])

        a = ask(client, unregistered,
                "What are the placement opportunities?")["message"]
        check("10. placement",
              "placement" in a.lower() and ("44" in a or "LPA" in a), a[:160])

        # ---- 11: unknown question must not hallucinate ------------------
        print("== Safety ==")
        a = ask(client, unregistered,
                "Do you provide a helicopter shuttle service to the campus?")["message"]
        check("11. unknown question handled safely",
              ("not available" in a.lower()) or ("admission office" in a.lower()),
              a[:160])

        # ---- 18: fee must never be invented -----------------------------
        a = ask(client, unregistered, "What is the tuition fee?")["message"]
        check("18. no invented fees",
              "not published" in a.lower()
              and "45,000" not in a and "45 000" not in a and "Rs." not in a,
              a[:160])

        # ---- 17: Tamil/Tanglish ----------------------------------------
        a = ask(client, unregistered, "Hostel irukka?")["message"]
        check("17. Tamil/Tanglish query", "hostel" in a.lower(), a[:140])

        # ---- Register a visitor for live-context cases ------------------
        print("== Live visitor context ==")
        reception = login(client, "reception", "reception123")
        depts = client.get(
            "/api/reception/departments", headers=reception
        ).json()
        ece = next(d for d in depts if d["code"] == "ECE")
        r = client.post(
            "/api/reception/visitors",
            headers=reception,
            json={
                "full_name": "Raj Kumar",
                "phone": "9876543210",
                "purpose": "Admission",
                "department_id": ece["id"],
                "remarks": "Nandha AI test",
                "needs_help_desk": False,
            },
        )
        check("visitor registered", r.status_code == 200, r.text[:120])
        visitor = r.json()
        check("visitor code is V121", visitor["visitor_code"] == "V121",
              visitor["visitor_code"])

        phone = "9876543210"
        a = ask(client, phone, "What is my Visitor ID?")["message"]
        check("12. visitor ID", "V121" in a, a[:120])

        a = ask(client, phone, "How many people are ahead of me?")["message"]
        check("13. queue position",
              "ahead" in a.lower() or "next in line" in a.lower(), a[:140])

        a = ask(client, phone, "What is my current stage?")["message"]
        check("14. current stage", "Counselling" in a, a[:140])

        a = ask(client, phone, "What is the next step?")["message"]
        check("15. next workflow stage (Eligibility Verification)",
              "Eligibility Verification" in a, a[:160])

        # ---- 16: unsure about department -> help desk -------------------
        a = ask(client, phone,
                "I don't know which department I should choose.")["message"]
        check("16. unknown department guidance",
              "help desk" in a.lower() or "counselling" in a.lower(), a[:160])

    print(f"\n{CHECKS['passed']} passed, {CHECKS['failed']} failed")
    assert CHECKS["failed"] == 0


if __name__ == "__main__":
    main()
    sys.exit(0)
