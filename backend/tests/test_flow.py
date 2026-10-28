"""End-to-end test of the complete visitor lifecycle.

Runs against the live FastAPI app with an in-memory/ temp SQLite DB and
verifies the full demo scenario:

Receptionist registration -> visitor creation -> AI conversation -> queue
assignment -> staff call -> stage completion -> automatic next-stage
allocation -> notifications -> final completion.
"""
import os
import sys
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/e2e_test.db"
os.environ["TELEGRAM_POLLING"] = "0"  # keep tests offline (no bot polling)
os.environ["AI_PROVIDER"] = "rules"  # deterministic, offline knowledge-base answers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"


def check(name, cond, extra=""):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name} {extra}")
    assert cond, f"{name} failed {extra}"


def main():
    with TestClient(app) as client:
        # ---- Auth -------------------------------------------------------
        print("== Authentication ==")
        r = client.post("/api/auth/login",
                        json={"username": "admin", "password": "wrong"})
        check("rejects bad password", r.status_code == 401)

        admin = login(client, "admin", "admin123")
        reception = login(client, "reception", "reception123")
        priya = login(client, "priya", "staff123")

        # ---- Receptionist: register Raj Kumar --------------------------
        print("== Registration ==")
        depts = client.get("/api/reception/departments",
                           headers=reception).json()
        ece = next(d for d in depts if d["code"] == "ECE")

        r = client.post("/api/reception/visitors", headers=reception, json={
            "full_name": "Raj Kumar",
            "phone": "9876543210",
            "purpose": "Admission",
            "department_id": ece["id"],
            "remarks": "Walk-in parent",
            "needs_help_desk": False,
        })
        check("register visitor ok", r.status_code == 200, str(r.text))
        raj = r.json()
        check("visitor code is V121", raj["visitor_code"] == "V121", raj["visitor_code"])
        check("initial stage is Counselling",
              raj["current_stage_name"] == "Counselling",
              str(raj.get("current_stage_name")))
        check("has queue token", raj["current_queue_entry"] is not None,
              str(raj.get("current_queue_entry")))
        raj_id = raj["id"]
        dvid = raj["current_queue_entry"]["queue_id"]

        # ---- Chat: welcome + AI answers ---------------------------------
        print("== AI Chat ==")
        r = client.get("/api/chat/session", params={"phone": "9876543210"})
        sess = r.json()
        check("session loads visitor", sess["visitor"]["visitor_code"] == "V121")
        check("welcome message present",
              any(m["sender"] == "AI" for m in sess["messages"]))
        welcome = [m for m in sess["messages"] if m["sender"] == "AI"][0]
        check("welcome contains visitor id", "V121" in (welcome["message"] or ""))

        r = client.post("/api/chat/send",
                        json={"phone": "9876543210",
                              "message": "What documents are required for ECE admission?"})
        answer = r.json()["message"]
        check("KB answer for ECE docs", "mark sheet" in answer.lower(),
              answer[:80])

        r = client.post("/api/chat/send",
                        json={"phone": "9876543210",
                              "message": "How many people are before me?"})
        q_ans = r.json()["message"]
        check("queue position answered",
              "ahead" in q_ans.lower() or "next in line" in q_ans.lower(),
              q_ans[:80])

        # ---- Staff: call next -------------------------------------------
        print("== Staff queue actions ==")
        queues = client.get("/api/staff/queues", headers=priya).json()
        ece_queue = next((q for q in queues
                          if "Counselling" in q["stage_name"]
                          and q["workflow_name"] == "ECE Admission"), None)
        check("staff sees ECE counselling queue", ece_queue is not None)

        in_queue = next((e for e in ece_queue["entries"]
                         if e["visitor_code"] == "V121"), None)
        check("V121 is in staff queue", in_queue is not None)

        r = client.post(f"/api/staff/queues/{ece_queue['queue_id']}/call-next",
                        headers=priya)
        check("call next ok", r.status_code == 200, r.text[:120])
        check("called V121", r.json()["entry"]["visitor_code"] == "V121",
              r.text[:120])

        sess = client.get("/api/chat/session",
                          params={"phone": "9876543210"}).json()
        msgs = [m["message"] for m in sess["messages"]]
        check("notification: your turn",
              any("Your turn" in m for m in msgs), str(msgs[-2:]))

        # ---- Complete counselling -> auto next stage ---------------------
        called_entry_id = r.json()["entry"]["id"]
        r = client.post(f"/api/staff/entries/{called_entry_id}/complete",
                        headers=priya)
        check("complete stage ok", r.status_code == 200, r.text[:200])

        checkpoint = client.get(f"/api/reception/visitors/{raj_id}",
                                headers=reception).json()
        check("moved to Eligibility Verification",
              checkpoint["current_stage_name"] == "Eligibility Verification",
              str(checkpoint.get("current_stage_name")))
        check("next stage is Document Verification",
              checkpoint["next_stage_name"] == "Document Verification",
              str(checkpoint.get("next_stage_name")))

        # ---- Walk through the FULL workflow ------------------------------
        print("== Full workflow progression ==")
        expected = ["Eligibility Verification", "Document Verification",
                    "Accounts", "Admission Confirmation", "Registration"]
        completed_ids = {called_entry_id}
        for target in expected:
            staff_user = stage_login(client, target)
            queues = client.get("/api/staff/queues", headers=staff_user).json()
            q = next((x for x in queues if x["stage_name"] == target
                      and x["workflow_name"] == "ECE Admission"), None)
            assert q, f"no queue for {target}"
            entry = next((e for e in q["entries"]
                          if e["visitor_code"] == "V121"), None)
            if entry is not None:
                r = client.post(f"/api/staff/entries/{entry['id']}/complete",
                                headers=staff_user)
            else:
                # V121 is not first in line: call-next until V121 is called
                entry = None
                for _ in range(len(q["entries"]) + 1):
                    r = client.post(
                        f"/api/staff/queues/{q['queue_id']}/call-next",
                        headers=staff_user)
                    check(f"call next at {target}", r.status_code == 200,
                          r.text[:120])
                    if r.json()["entry"]["visitor_code"] == "V121":
                        entry = r.json()["entry"]
                        break
                assert entry, f"could not reach V121 in {target}"
                r = client.post(f"/api/staff/entries/{entry['id']}/complete",
                                headers=staff_user)
            check(f"complete {target}", r.status_code == 200, r.text[:150])
            completed_ids.add(entry["id"])

        check("registration completed visitor status",
              client.get(f"/api/reception/visitors/{raj_id}",
                         headers=reception).json()["status"] == "COMPLETED")

        # final chat notification
        sess = client.get("/api/chat/session",
                          params={"phone": "9876543210"}).json()
        msgs = [m["message"] for m in sess["messages"]]
        check("final completion notification",
              any("complete" in m.lower() for m in msgs))

        # ---- Admin stats -------------------------------------------------
        print("== Admin ==")
        stats = client.get("/api/admin/stats", headers=admin).json()
        check("admin stats present", stats["total_visitors_today"] >= 1,
              str(stats))

        # ---- Second parent: help desk routing ----------------------------
        print("== Help-desk routing ==")
        r = client.post("/api/reception/visitors", headers=reception, json={
            "full_name": "Sundar Kumar",
            "phone": "9876500000",
            "purpose": "Admission",
            "department_id": None,
            "remarks": "Not sure which department",
            "needs_help_desk": True,
        })
        check("help desk registration ok", r.status_code == 200, r.text[:120])
        sundar = r.json()
        check("help desk workflow assigned",
              sundar["current_workflow_name"] == "Counselling / Help Desk",
              str(sundar.get("current_workflow_name")))
        check("help desk stage assigned",
              sundar["current_stage_name"] == "Counselling / Help Desk")

        r = client.post("/api/chat/send",
                        json={"phone": "9876500000",
                              "message": "I don't know which department I need."})
        ans = r.json()["message"].lower()
        check("AI guides to help desk", "help desk" in ans or "counselling" in ans,
              ans[:100])

        # ---- Staff special actions: HOLD / SKIP / REASSIGN ---------------
        print("== Staff special actions ==")
        sundar_entry_id = sundar["current_queue_entry"]["id"]
        h = client.post(f"/api/staff/entries/{sundar_entry_id}/hold",
                        headers=login(client, "divya", "staff123"),
                        json={"reason": "Visitor asked to wait"})
        check("hold ok", h.status_code == 200, h.text[:120])
        check("hold status", h.json()["entry"]["status"] == "HOLD")

        s = client.post(f"/api/staff/entries/{sundar_entry_id}/skip",
                        headers=login(client, "divya", "staff123"),
                        json={"reason": "Visitor rescheduled to afternoon"})
        check("skip ok", s.status_code == 200, s.text[:120])
        check("skip status", s.json()["entry"]["status"] == "SKIPPED")

        r = client.post("/api/reception/visitors", headers=reception, json={
            "full_name": "Kiran Patel",
            "phone": "9876500001",
            "purpose": "Admission",
            "department_id": 2,
            "remarks": "Reassignment test",
        })
        check("reassign source ok", r.status_code == 200, r.text[:120])
        kiran_entry_id = r.json()["current_queue_entry"]["id"]
        stage_map = client.get("/api/reception/stage-map",
                               headers=reception).json()
        target = next((st for st in stage_map
                       if st["workflow_name"] == "ECE Admission"
                       and st["name"] == "Eligibility Verification"), None)
        check("reassign target exists", target is not None)
        r = client.post(f"/api/staff/entries/{kiran_entry_id}/reassign",
                        headers=login(client, "priya", "staff123"),
                        json={"reason": "Moved to eligibility by admin",
                              "new_stage_id": target["id"]})
        check("reassign ok", r.status_code == 200, r.text[:120])
        kiran = client.get(
            f"/api/reception/visitors/{r.json()['entry']['visitor_id']}",
            headers=reception).json()
        check("reassign moved stage",
              kiran["current_stage_name"] == "Eligibility Verification",
              str(kiran.get("current_stage_name")))

        print("\nAll end-to-end checks passed.")


def login(client, username, password):
    r = client.post("/api/auth/login",
                    json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def stage_login(client, stage_name):
    stage = {
        "Eligibility Verification": "arun",
        "Document Verification": "kavita",
        "Accounts": "suresh",
        "Admission Confirmation": "anita",
        "Registration": "vikram",
        "Counselling / Help Desk": "divya",
    }
    return login(client, stage[stage_name], "staff123")


if __name__ == "__main__":
    main()
    sys.exit(0)