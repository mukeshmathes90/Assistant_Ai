"""Seed / update the official Nandha Engineering College knowledge base.

Usage (from the backend directory):

    D:\\python\\python.exe seed_nandha_knowledge.py

The script is IDEMPOTENT and safe to re-run:
  * CollegeInformation rows are upserted by their unique ``key``.
  * FAQ rows are upserted by (``category``, ``question``).
  * Only the original generic demo FAQs (created by app/seed.py) are
    deactivated; Nandha records are inserted/updated and set active.

No AI model is trained or fine-tuned here - this only stores official
website data into the existing FAQ / CollegeInformation tables.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models import CollegeInformation, Department, FAQ  # noqa: E402
from app.nandha_knowledge import (  # noqa: E402
    COLLEGE_INFO,
    FAQS,
    KNOWLEDGE_CAPTURED_ON,
)

# Questions created by the original generic demo seeder (app/seed.py). These
# are the only FAQs this script will deactivate, so anything an admin adds
# later is preserved.
LEGACY_FAQ_QUESTIONS = {
    "What documents are required for ECE admission?",
    "What documents are required for CSE admission?",
    "What documents are required for MBA admission?",
    "What is the eligibility for B.Tech admission?",
    "What is the admission fee structure?",
    "Is hostel available?",
    "What transport facilities are available?",
    "What are the college timings?",
    "Where is the admission office?",
    "Where is the help desk?",
    "Can I get a seat through management quota?",
    "Which courses are offered?",
    "Is there any scholarship available?",
    "How long does the admission process take?",
    "Can parents accompany the student during admission?",
    "Where can I pay the admission fee?",
    "What is the college uniform/dress code?",
}


def _department_map(db):
    return {d.code: d.id for d in db.query(Department).all()}


def upsert_college_info(db):
    added = updated = 0
    for item in COLLEGE_INFO:
        row = (
            db.query(CollegeInformation)
            .filter(CollegeInformation.key == item["key"])
            .first()
        )
        fields = dict(
            title=item["title"],
            content=item["content"],
            category=item["category"],
            source_url=item.get("source_url", ""),
            source_type=item.get("source_type", "official_website"),
            last_updated=KNOWLEDGE_CAPTURED_ON,
            is_active=True,
        )
        if row is None:
            db.add(CollegeInformation(key=item["key"], **fields))
            added += 1
        else:
            for k, v in fields.items():
                setattr(row, k, v)
            updated += 1
    return added, updated


def upsert_faqs(db):
    dept_map = _department_map(db)
    added = updated = 0
    nandha_keys = set()
    for item in FAQS:
        key = (item["category"], item["question"])
        nandha_keys.add(key)
        dept_code = item.get("dept_code")
        fields = dict(
            answer=item["answer"],
            keywords=item.get("keywords", ""),
            department_id=dept_map.get(dept_code) if dept_code else None,
            source_url=item.get("source_url", ""),
            source_type=item.get("source_type", "official_website"),
            last_updated=KNOWLEDGE_CAPTURED_ON,
            is_active=True,
        )
        row = (
            db.query(FAQ)
            .filter(FAQ.category == item["category"], FAQ.question == item["question"])
            .first()
        )
        if row is None:
            db.add(
                FAQ(category=item["category"], question=item["question"], **fields)
            )
            added += 1
        else:
            for k, v in fields.items():
                setattr(row, k, v)
            updated += 1

    # Retire only the original generic demo FAQs (now superseded by official
    # Nandha records). Admin-created FAQs are left untouched.
    retired = 0
    for faq in db.query(FAQ).all():
        if (
            faq.question in LEGACY_FAQ_QUESTIONS
            and (faq.category, faq.question) not in nandha_keys
            and faq.is_active
        ):
            faq.is_active = False
            retired += 1
    return added, updated, retired


def seed_nandha_knowledge(db=None):
    """Upsert the Nandha knowledge base. Returns a stats dict."""
    own_session = db is None
    if own_session:
        init_db()
        db = SessionLocal()
    try:
        ci_added, ci_updated = upsert_college_info(db)
        faq_added, faq_updated, faq_retired = upsert_faqs(db)
        db.commit()
        return {
            "college_info_added": ci_added,
            "college_info_updated": ci_updated,
            "faqs_added": faq_added,
            "faqs_updated": faq_updated,
            "faqs_retired": faq_retired,
            "categories": sorted({f["category"] for f in FAQS}),
        }
    finally:
        if own_session:
            db.close()


def main():
    stats = seed_nandha_knowledge()
    print("Nandha knowledge base seeded/updated:")
    print(f"  CollegeInformation added   : {stats['college_info_added']}")
    print(f"  CollegeInformation updated : {stats['college_info_updated']}")
    print(f"  FAQs added                 : {stats['faqs_added']}")
    print(f"  FAQs updated               : {stats['faqs_updated']}")
    print(f"  Legacy FAQs retired        : {stats['faqs_retired']}")
    print(f"  Categories                 : {', '.join(stats['categories'])}")


if __name__ == "__main__":
    main()
