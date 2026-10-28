"""Official knowledge base for Nandha Engineering College (Autonomous), Erode.

All facts in this module were collected ONLY from the official website
https://nandhaengg.org/ and its official pages. Nothing here is transcribed
from blogs, coaching sites, Wikipedia or third-party portals.

The data is consumed by:
  * backend/seed_nandha_knowledge.py  (upserts into the FAQ / CollegeInformation
    tables - the existing knowledge-base tables, no new tables are created)
  * backend/app/services/ai_service.py (department intent detection + prompt)

IMPORTANT: This module contains DATA, not AI logic. No model is trained or
fine-tuned anywhere in this system.
"""
import re
from datetime import datetime

# The data was last verified against the official website on this date.
KNOWLEDGE_CAPTURED_ON = datetime(2026, 9, 18)

COLLEGE_NAME = "Nandha Engineering College (Autonomous)"
COLLEGE_SHORT_NAME = "Nandha Engineering College"
COLLEGE_WEBSITE = "https://nandhaengg.org/"

# Official source pages.
SOURCE = {
    "home": "https://nandhaengg.org/",
    "about": "https://nandhaengg.org/about-us/",
    "admission": "https://nandhaengg.org/admission/",
    "departments": "https://nandhaengg.org/departments/",
    "placement": "https://nandhaengg.org/placement/",
    "facilities": "https://nandhaengg.org/facilities/",
    "contact": "https://nandhaengg.org/contact-us/",
}

# ---------------------------------------------------------------------------
# Department intent detection (natural-language synonyms -> canonical code).
# Only unambiguous terms are mapped. "it" is matched as a whole word only so it
# never fires inside words such as "admission".
# ---------------------------------------------------------------------------
DEPARTMENT_SYNONYMS = {
    "CSE": [
        "cse", "computer science", "computer science and engineering",
        "computer science & engineering", "computers", "software engineering",
    ],
    "IT": [
        "it", "information technology", "information tech",
    ],
    "ECE": [
        "ece", "electronics", "communication", "electronics and communication",
        "electronics & communication", "e&c", "vlsi", "embedded systems",
    ],
    "EEE": [
        "eee", "electrical", "electrical and electronics",
        "electrical & electronics", "e&e", "power systems",
    ],
    "MECH": [
        "mech", "mechanical", "mechanical engineering", "automobile",
    ],
    "CIVIL": [
        "civil", "civil engineering", "construction",
    ],
    "BME": [
        "biomedical", "bio medical", "bio-medical", "bme", "medical engineering",
    ],
    "AGRI": [
        "agricultural", "agriculture", "agri", "agricultural engineering",
    ],
    "CHEM": [
        "chemical", "chemical engineering",
    ],
    "AI&DS": [
        "ai", "aids", "ai and ds", "ai & ds", "ai&ds", "artificial intelligence",
        "data science", "machine learning",
    ],
    "CSE-CYBER": [
        "cyber", "cyber security", "cybersecurity", "cse cyber", "ethical hacking",
    ],
    "CSE-IOT": [
        "iot", "internet of things", "cse iot",
    ],
    "MBA": [
        "mba", "business administration",
    ],
    "MCA": [
        "mca", "computer applications",
    ],
    "ME-CSE": [
        "m.e", "m.e.", "me cse", "m.e cse", "master of engineering",
    ],
}

DEPARTMENT_DISPLAY_NAMES = {
    "CSE": "Computer Science & Engineering (CSE)",
    "IT": "Information Technology (IT)",
    "ECE": "Electronics & Communication Engineering (ECE)",
    "EEE": "Electrical & Electronics Engineering (EEE)",
    "MECH": "Mechanical Engineering",
    "CIVIL": "Civil Engineering",
    "BME": "Biomedical Engineering",
    "AGRI": "Agricultural Engineering",
    "CHEM": "Chemical Engineering",
    "AI&DS": "Artificial Intelligence & Data Science (AI & DS)",
    "CSE-CYBER": "CSE (Cyber Security)",
    "CSE-IOT": "CSE (Internet of Things)",
    "MBA": "Master of Business Administration (MBA)",
    "MCA": "Master of Computer Applications (MCA)",
    "ME-CSE": "M.E. Computer Science & Engineering",
}

# Tanglish / Tamil hints -> English synonym appended during matching so common
# Tamil/Tanglish phrasings still resolve to the right knowledge record.
TANGLISH_HINTS = {
    "irukka": "available",
    "irukkuma": "available",
    "iruka": "available",
    "kidaikkuma": "available",
    "enge": "where",
    "enga": "where",
    "engae": "where",
    "evlo": "fee",
    "evvalavu": "fee",
    "evvolavu": "fee",
    "kattanam": "fee",
    "selavu": "fee",
    "peyar": "name",
    "vilasam": "address",
    "mugavari": "address",
    "thangum": "hostel",
    "thangi": "hostel",
    "vanakkam": "hello",
    "nandri": "thanks",
    "padikkalam": "course",
    "padipu": "course",
    "vela": "placement",
    "velai": "placement",
    "phone": "contact",
    "number": "contact",
}


def _normalized_words(text: str) -> set:
    cleaned = re.sub(r"[^a-z0-9&\s]", " ", (text or "").lower())
    return set(cleaned.split())


def detect_department(text: str):
    """Return a canonical department code for a natural-language query, or None.

    Multi-word / symbol aliases are matched as substrings; short single-word
    aliases must match a whole token to avoid false positives.
    """
    if not text:
        return None
    lowered = re.sub(r"[^a-z0-9&\s]", " ", text.lower())
    lowered = re.sub(r"\s+", " ", lowered).strip()
    words = set(lowered.split())
    for code, aliases in DEPARTMENT_SYNONYMS.items():
        for alias in aliases:
            if any(ch in alias for ch in (" ", "&", ".")):
                if alias in lowered:
                    return code
            elif "." in alias:
                if alias in lowered:
                    return code
            else:
                if alias in words:
                    return code
    return None


def expand_tanglish(text: str) -> str:
    """Append English synonyms for common Tamil/Tanglish words in a query."""
    if not text:
        return text
    words = _normalized_words(text)
    extra = [eng for ta, eng in TANGLISH_HINTS.items() if ta in words]
    if extra:
        return f"{text} {' '.join(sorted(set(extra)))}"
    return text


# ---------------------------------------------------------------------------
# Structured college information (one record per key).
# ---------------------------------------------------------------------------

CONTACT_LINE = (
    "Phone: 04294 - 225585 / 226393 | Mobile: 7373714477 / 7373723722 | "
    "Admission: 7373714477 (also WhatsApp) | Email: info@nandhaengg.org | "
    "Admission email: aotechcampus@nandhainstitutions.org | "
    "Address: Erode - Perundurai Main Road, Vaikkaalmedu, Erode - 638 052, "
    "Tamil Nadu | Website: https://nandhaengg.org/"
)

COLLEGE_INFO = [
    dict(
        key="college_name",
        title="Nandha Engineering College (Autonomous)",
        category="College",
        source_url=SOURCE["home"],
        content=(
            "Nandha Engineering College (Autonomous) is an engineering institution "
            "in Erode, Tamil Nadu, run by the Sri Nandha Educational Trust. It is "
            "approved by AICTE, New Delhi; affiliated to Anna University, Chennai; "
            "and accredited by NAAC with A+ Grade and by NBA. Counselling Code: 2715."
        ),
    ),
    dict(
        key="college_overview",
        title="About Nandha Engineering College",
        category="College",
        source_url=SOURCE["about"],
        content=(
            "Nandha Engineering College was established in 2001 by the Sri Nandha "
            "Educational Trust (formed in 1992) under the leadership of Chairman "
            "Thiru. V. Shanmugan. The college is autonomous and is in its 25th year "
            "(Silver Jubilee), with about 4,015 students and 12 engineering and "
            "technology departments on a 25-acre campus on the Erode-Perundurai "
            "Main Road."
        ),
    ),
    dict(
        key="accreditation",
        title="Approvals & accreditation",
        category="College",
        source_url=SOURCE["home"],
        content=(
            "Nandha Engineering College (Autonomous) is approved by AICTE, New "
            "Delhi, and affiliated to Anna University, Chennai. It is accredited "
            "by NAAC with A+ Grade (CGPA 3.38) and several programmes are NBA "
            "accredited. The institution offers UG, PG and research programmes."
        ),
    ),
    dict(
        key="location",
        title="Campus address",
        category="Location",
        source_url=SOURCE["contact"],
        content=(
            "Nandha Engineering College (Autonomous), Erode - Perundurai Main Road, "
            "Vaikkaalmedu, Erode - 638 052, Tamil Nadu, India. The campus is spread "
            "over about 25 acres."
        ),
    ),
    dict(
        key="contact",
        title="Contact information",
        category="Contact",
        source_url=SOURCE["contact"],
        content=CONTACT_LINE,
    ),
    dict(
        key="admission_office",
        title="Admission office & counselling code",
        category="Admission",
        source_url=SOURCE["admission"],
        content=(
            "Counselling Code: 2715. Admissions are handled by the Admission "
            "Office. Admission contact: Mr. A.K. Velusamy, Administrative Officer - "
            "Mobile 7373714477 (also WhatsApp), Phone 04294-226393 / 225585, Email "
            "aotechcampus@nandhainstitutions.org. For candidates from other states: "
            "7373722199, admissionotherstates@nandhainstitutions.org."
        ),
    ),
    dict(
        key="help_desk",
        title="Counselling / Help Desk",
        category="Location",
        source_url=SOURCE["contact"],
        content=(
            "If you are not sure which department or course suits you, the "
            "counselling / help desk team will guide you based on your interests "
            "and marks. Contact the Admission Office: 7373714477, "
            "04294-226393 / 225585, email aotechcampus@nandhainstitutions.org."
        ),
    ),
    dict(
        key="reception",
        title="Reception / Front office",
        category="Location",
        source_url=SOURCE["contact"],
        content=(
            "The college front office / reception is at the main campus, "
            "Erode - Perundurai Main Road, Vaikkaalmedu, Erode - 638 052. "
            "Reception phone: 04294 - 225585 / 226393. For admission guidance, "
            "ask for the Admission Office."
        ),
    ),
    dict(
        key="timings",
        title="Office timings",
        category="Timings",
        source_url=SOURCE["contact"],
        content=(
            "The college functions on working days. Official office and admission "
            "timings are not published on the website, so please confirm current "
            "timings by calling 04294 - 225585 / 226393 or 7373714477 before "
            "visiting."
        ),
        source_type="not_published",
    ),
    dict(
        key="hostel",
        title="Hostel facilities",
        category="Hostel",
        source_url=SOURCE["facilities"],
        content=(
            "Separate hostels are available for men and women. Men's hostel: 94 "
            "rooms with capacity for about 336 students. Women's hostel: 81 rooms. "
            "Facilities include attached washrooms, cot, table and chair, almirah, "
            "Wi-Fi, RO drinking water, solar hot water, mess, hospital access, "
            "24x7 security, power backup, laundry (paid) and indoor/outdoor games. "
            "Hostel contacts: Boys - 9942216806 / 9942216805; "
            "Girls - 9095292168 / 7373710103."
        ),
    ),
    dict(
        key="transport",
        title="Transport / bus facilities",
        category="Transport",
        source_url=SOURCE["facilities"],
        content=(
            "The college runs a fleet of about 49 buses plus 1 emergency vehicle. "
            "Buses cover a radius of about 85 km, with routes to Tirupur, Avinashi, "
            "Tiruchengode, Sankari and nearby towns. Transport contact: 9842717278, "
            "email transport@nandhainstitutions.org. Bus route and fee details are "
            "available at the transport office."
        ),
    ),
    dict(
        key="placement",
        title="Placements",
        category="Placement",
        source_url=SOURCE["placement"],
        content=(
            "Placement highlights (as stated by the college): highest salary 44 LPA; "
            "100% career settlement; 150+ regular recruiters; 51 offers above "
            "7 LPA; about 200 companies visit the campus. In 2025, 139 companies "
            "participated with about 90% placement. Placement contact: "
            "placement@nandhainstitutions.org, 99655 26397. Placement Head: "
            "Dr. S. Sivaramakrishnan."
        ),
    ),
    dict(
        key="facilities",
        title="Campus facilities",
        category="Facilities",
        source_url=SOURCE["facilities"],
        content=(
            "Campus facilities: 25-acre campus, 76 classrooms, 102 laboratories, a "
            "central library (10,800 sq ft, 64,060 books, 20,541 titles), separate "
            "boys' and girls' hostels, a 2,000-seat auditorium, canteen, Indian Bank "
            "ATM, sports grounds on more than 10 acres, a yoga centre and a gym."
        ),
    ),
    dict(
        key="library",
        title="Central Library",
        category="Facilities",
        source_url=SOURCE["facilities"],
        content=(
            "The Central Library is about 10,800 sq ft with 64,060 books, 20,541 "
            "titles and access to journals and digital resources. It supports "
            "students and staff across all departments."
        ),
    ),
    dict(
        key="courses_ug",
        title="Undergraduate (UG) programmes & intake",
        category="Courses",
        source_url=SOURCE["departments"],
        content=(
            "UG programmes and sanctioned intake: B.E. Electronics & Communication "
            "Engineering (ECE) - 180; B.E. Computer Science & Engineering (CSE) - "
            "240; B.Tech Information Technology (IT) - 120; B.E. Electrical & "
            "Electronics Engineering (EEE) - 60; B.E. Mechanical Engineering - 60; "
            "B.E. Civil Engineering - 30; B.Tech Agricultural Engineering - 60; "
            "B.Tech Chemical Engineering - 30; B.Tech Biomedical Engineering - 60; "
            "B.Tech Artificial Intelligence & Data Science (AI & DS) - 120; B.Tech "
            "CSE (Cyber Security) - 60; B.Tech CSE (Internet of Things) - 60. Total "
            "UG intake about 1,080."
        ),
    ),
    dict(
        key="courses_pg",
        title="Postgraduate (PG) programmes",
        category="Courses",
        source_url=SOURCE["departments"],
        content=(
            "PG programmes: M.E. Computer Science & Engineering (intake 6), MBA "
            "(intake 60) and MCA (intake 60). The college also offers research "
            "programmes (Ph.D.) in several departments."
        ),
    ),
    dict(
        key="departments_list",
        title="Departments",
        category="Departments",
        source_url=SOURCE["departments"],
        content=(
            "The college has 12 engineering and technology departments covering "
            "ECE, CSE, IT, EEE, Mechanical, Civil, Agricultural, Chemical, "
            "Biomedical, AI & DS, CSE (Cyber Security) and CSE (IoT), along with "
            "Management (MBA), Computer Applications (MCA) and research centres."
        ),
    ),
    dict(
        key="research",
        title="Research & Development",
        category="Academics",
        source_url=SOURCE["about"],
        content=(
            "Nandha Engineering College has an R&D Cell and recognised research "
            "centres offering Ph.D. programmes in several disciplines. It promotes "
            "research, consultancy and innovation through its laboratories and "
            "Idea Lab."
        ),
    ),
    dict(
        key="academics_support",
        title="Academic support",
        category="Academics",
        source_url=SOURCE["about"],
        content=(
            "Academic support includes Outcome-Based Education (OBE), a Higher "
            "Education & Competitive Examination Cell (HE & CEC) that trains "
            "students for competitive exams and higher studies, and departmental "
            "academic support systems."
        ),
    ),
    dict(
        key="fees",
        title="Fees",
        category="Fees",
        source_url=SOURCE["admission"],
        content=(
            "Tuition and hostel fees are not published on the official website. "
            "Fee details are provided by the college at the time of "
            "admission/counselling. Please contact the Admission Office at "
            "7373714477 / 04294 - 226393 / 225585 or email "
            "aotechcampus@nandhainstitutions.org for the current fee structure."
        ),
        source_type="not_published",
    ),
    dict(
        key="management",
        title="Management",
        category="College",
        source_url=SOURCE["about"],
        content=(
            "Nandha Engineering College is run by the Sri Nandha Educational Trust "
            "(established 1992). Chairman: Thiru. V. Shanmugan. Principal: "
            "Dr. U.S. Ragupathy (principal@nandhaengg.org, 7373712234)."
        ),
    ),
    dict(
        key="website",
        title="Official website",
        category="College",
        source_url=SOURCE["home"],
        content=(
            "The only official website is https://nandhaengg.org/ . Please always "
            "verify admission information from this official website or the "
            "Admission Office."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Structured FAQs (category, question, answer, keywords, optional dept_code).
# ---------------------------------------------------------------------------

_DOC_CHECKLIST = (
    "Documents required for admission (original + photocopies):\n"
    "1. SSLC (10th) mark sheet\n"
    "2. HSC (+2) mark sheet\n"
    "3. Transfer Certificate (TC)\n"
    "4. Community / category certificate (if applicable)\n"
    "5. Aadhaar card (student and parent)\n"
    "6. Passport-size photographs\n"
    "7. Income certificate (for government scholarships, if applicable)\n"
    "8. Diploma mark sheets (for lateral entry) or Degree certificate (for PG)\n"
    "9. Nativity certificate (if required)\n"
    "10. Counselling allotment order (for government counselling candidates)\n"
    "For the exact checklist, contact 7373714477 / 04294-226393."
)

FAQS = [
    # ---------------- Admission ----------------
    dict(
        category="Admission",
        question="What is the admission procedure / how do I apply?",
        answer=(
            "Admission process:\n"
            "1. Apply through Tamil Nadu Government / Anna University counselling "
            "(Counselling Code: 2715) or contact the Admission Office.\n"
            "2. Register and get your documents verified (10th, 12th mark sheets, "
            "TC, etc.).\n"
            "3. Eligibility verification as per Anna University / Tamil Nadu "
            "Government norms.\n"
            "4. Pay the fees at the Accounts section.\n"
            "5. Confirm admission and complete registration.\n"
            "For help call 7373714477 / 04294-226393 / 225585 or email "
            "aotechcampus@nandhainstitutions.org."
        ),
        keywords=(
            "admission,procedure,apply,process,how to join,steps,application,"
            "counselling code,2715"
        ),
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What is the eligibility for B.E. / B.Tech (UG) admission?",
        answer=(
            "UG (B.E./B.Tech) eligibility as per Anna University / Tamil Nadu "
            "Government norms:\n"
            "- Pass in Higher Secondary (HSC) Academic with Mathematics, Physics "
            "and Chemistry.\n"
            "- Minimum average marks in Maths, Physics & Chemistry: OC 45%, "
            "BC & BCM 40%, MBC & DNC 40%, SC/SCA/ST 40%.\n"
            "- For the vocational stream the same minimum marks apply.\n"
            "Cut-off = Maths + (Physics + Chemistry)/2 for the academic stream.\n"
            "The Admission Office can confirm your eligibility: 7373714477 / "
            "04294-226393 / 225585."
        ),
        keywords=(
            "ug admission,eligibility,b.tech,b.e,hsc,12th,marks,percentage,"
            "physics,chemistry,maths,science stream,vocational"
        ),
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What is the eligibility for lateral entry (diploma holders)?",
        answer=(
            "Lateral entry admission (3rd semester) is available:\n"
            "- Diploma holders can join the 3rd semester of the relevant "
            "B.E./B.Tech programme.\n"
            "- B.Sc. graduates with Mathematics can also join the 3rd semester and "
            "must additionally study two engineering subjects.\n"
            "Contact the Admission Office (7373714477) to confirm the branch and "
            "procedure."
        ),
        keywords=(
            "lateral entry,diploma,direct second year,3rd semester,2nd year,"
            "b.sc"
        ),
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What is the eligibility for MBA admission?",
        answer=(
            "MBA eligibility: a recognised Bachelor's degree of at least 3 years "
            "with minimum 50% aggregate (45% for reserved category candidates of "
            "Tamil Nadu). Admission is through the TANCA / Government counselling "
            "process. Contact the Admission Office for current criteria: "
            "7373714477."
        ),
        keywords="mba,eligibility,master of business administration,50%,tanca,pg",
        source_url=SOURCE["admission"],
        dept_code="MBA",
    ),
    dict(
        category="Admission",
        question="What is the eligibility for MCA admission?",
        answer=(
            "MCA eligibility: a pass in BCA, B.Sc. (IT/Computer Science) or any "
            "Bachelor's degree with Mathematics at 10+2 level or at graduation "
            "level, with minimum 50% aggregate (45% for reserved category "
            "candidates of Tamil Nadu). Admission is through TANCA / Government "
            "counselling. Contact the Admission Office for details."
        ),
        keywords="mca,eligibility,master of computer applications,mathematics,bca,pg",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What is the eligibility for M.E. admission?",
        answer=(
            "M.E. eligibility: a relevant B.E./B.Tech degree. Admission is through "
            "the TANCA (Tamil Nadu Common Admissions) process. For M.E. Computer "
            "Science & Engineering, candidates from ECE/IT/CSE/Software/Computer & "
            "Communication branches are eligible. Contact the Admission Office for "
            "current criteria."
        ),
        keywords="m.e,me,post graduate,pg admission,master of engineering,tanca",
        source_url=SOURCE["admission"],
        dept_code="ME-CSE",
    ),
    dict(
        category="Admission",
        question="What documents are required for admission?",
        answer=_DOC_CHECKLIST,
        keywords=(
            "documents,required,mark sheet,sslc,10th,12th,hsc,transfer "
            "certificate,tc,aadhaar,photos,certificate"
        ),
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What documents are required for ECE admission?",
        answer=_DOC_CHECKLIST,
        keywords="documents,ece,electronics,admission,required,mark sheet,certificate",
        source_url=SOURCE["admission"],
        dept_code="ECE",
    ),
    dict(
        category="Admission",
        question="What documents are required for CSE admission?",
        answer=_DOC_CHECKLIST,
        keywords="documents,cse,computer science,admission,required,mark sheet,certificate",
        source_url=SOURCE["admission"],
        dept_code="CSE",
    ),
    dict(
        category="Admission",
        question="What documents are required for MBA admission?",
        answer=(
            "For MBA admission you need:\n"
            "1. Degree mark sheets (all semesters)\n"
            "2. Degree / Provisional certificate\n"
            "3. Transfer Certificate (TC)\n"
            "4. Community / category certificate (if applicable)\n"
            "5. Aadhaar card and photo ID\n"
            "6. Passport-size photographs\n"
            "7. Counselling allotment order (for government counselling)\n"
            "Contact the Admission Office (7373714477) for the exact checklist."
        ),
        keywords="documents,mba,required,degree,mark sheet,certificate",
        source_url=SOURCE["admission"],
        dept_code="MBA",
    ),
    dict(
        category="Admission",
        question="Is there a management quota for admission?",
        answer=(
            "Admission to Nandha Engineering College is made through the Tamil Nadu "
            "Government / Anna University counselling and through the college "
            "management quota as permitted by the Government. Exact seat "
            "availability and eligibility under management quota are announced by "
            "the college. Please contact the Admission Office: 7373714477 / "
            "04294-226393 / 225585."
        ),
        keywords="management quota,seat,quota,direct admission",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="What is the cut-off mark?",
        answer=(
            "The cut-off for UG admission is calculated as: Marks in Mathematics + "
            "(Physics + Chemistry) / 2 (academic stream). The minimum required "
            "average is 45% for OC, 40% for BC/BCM/MBC/DNC and 40% for SC/SCA/ST. "
            "The college does not publish a separate department-wise cut-off list; "
            "contact the Admission Office at 7373714477 for guidance."
        ),
        keywords="cutoff,cut off,cut-off,minimum marks,mark required",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="When does admission start / what is the last date?",
        answer=(
            "Admission dates are notified by the Tamil Nadu Government and Anna "
            "University counselling each year, and are not published on this "
            "website. Please check https://nandhaengg.org/ or contact the Admission "
            "Office at 7373714477 / 04294-226393 / 225585 for the current admission "
            "schedule."
        ),
        keywords="admission date,last date,start date,when admission,deadline,schedule",
        source_url=SOURCE["admission"],
        source_type="not_published",
    ),
    dict(
        category="Admission",
        question="Can students from other states apply?",
        answer=(
            "Yes. Candidates from other states can apply. For out-of-state "
            "admissions, contact 7373722199 or email "
            "admissionotherstates@nandhainstitutions.org. You can also call the "
            "main Admission Office at 7373714477 / 04294-226393."
        ),
        keywords="other state,other states,outside tamil nadu,out of state,nri",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="Are scholarships available?",
        answer=(
            "Government and other scholarships (such as SC/ST/OBC/EBC and merit "
            "scholarships) can be availed as per Tamil Nadu Government and central "
            "norms. The college helps students apply and verifies documents. "
            "Scholarship-specific details are not published on the website, so "
            "please contact the Admission Office (7373714477 / 04294-226393) for "
            "current information."
        ),
        keywords="scholarship,financial,concession,government scholarship,fee concession",
        source_url=SOURCE["admission"],
        source_type="not_published",
    ),
    dict(
        category="Admission",
        question="What is the fee structure / tuition fee?",
        answer=(
            "The tuition fee and other fees are not published on the official "
            "website. Fee details are given by the college during "
            "counselling/admission. Please contact the Admission Office at "
            "7373714477 / 04294-226393 / 225585 or email "
            "aotechcampus@nandhainstitutions.org for the current fee structure."
        ),
        keywords="fee,fees,tuition,structure,cost,amount,how much,charges",
        source_url=SOURCE["admission"],
        source_type="not_published",
    ),
    dict(
        category="Admission",
        question="What is the hostel fee?",
        answer=(
            "The hostel fee is not published on the official website. Please "
            "contact the hostel office - Boys: 9942216806 / 9942216805; Girls: "
            "9095292168 / 7373710103 - or the Admission Office at 7373714477 for "
            "current hostel fees."
        ),
        keywords="hostel fee,hostel fees,hostel charges,room rent",
        source_url=SOURCE["facilities"],
        source_type="not_published",
    ),
    dict(
        category="Admission",
        question="Is there any entrance exam for admission?",
        answer=(
            "UG admission is based on Class 12 marks and the Tamil Nadu "
            "Government / Anna University counselling process. PG admissions (MBA, "
            "MCA, M.E.) are through TANCA / Government counselling. The college does "
            "not conduct its own entrance exam. Contact 7373714477 for guidance."
        ),
        keywords="entrance exam,entrance,exam,test,neet,jee,competitive",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="Can parents accompany the student?",
        answer=(
            "Yes, parents/guardians are welcome to accompany students during "
            "counselling and admission. Please carry the required original "
            "documents."
        ),
        keywords="parents,accompany,guardian,father,mother",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Admission",
        question="How long does the admission process take?",
        answer=(
            "At the campus the admission process is handled stage by stage "
            "(counselling, eligibility, document verification, accounts, "
            "confirmation and registration). The time taken depends on the queue at "
            "each stage. You can track your stage and queue number in this chat."
        ),
        keywords="how long,duration,take,time,process time",
        source_url=SOURCE["admission"],
    ),
    # ---------------- Courses & Departments ----------------
    dict(
        category="Courses",
        question="What courses are offered at Nandha Engineering College?",
        answer=(
            "UG: B.E. ECE, CSE, EEE, Mechanical, Civil, Biomedical; B.Tech IT, "
            "AI & DS, Agricultural, Chemical, CSE (Cyber Security), CSE (IoT).\n"
            "PG: M.E. CSE, MBA and MCA.\n"
            "The college also offers Ph.D./research programmes in several "
            "departments. Counselling Code: 2715."
        ),
        keywords="courses,programmes,degrees,b.tech,b.e,mba,mca,branches,offered,streams",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Courses",
        question="What are the UG courses and intake?",
        answer=(
            "UG programmes and intake: ECE 180; CSE 240; IT 120; EEE 60; "
            "Mechanical 60; Civil 30; Agricultural 60; Chemical 30; Biomedical 60; "
            "AI & DS 120; CSE (Cyber Security) 60; CSE (IoT) 60. Total about 1,080."
        ),
        keywords="ug courses,intake,seats,sanctioned intake,how many seats,undergraduate",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Courses",
        question="What are the PG courses?",
        answer=(
            "PG programmes: M.E. Computer Science & Engineering (intake 6), MBA "
            "(intake 60) and MCA (intake 60). Admission is through TANCA / "
            "Government counselling."
        ),
        keywords="pg courses,postgraduate,m.e,mba,mca,masters,intake",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Which departments are offered?",
        answer=(
            "Nandha Engineering College has 12 engineering and technology "
            "departments: ECE (Electronics & Communication), CSE (Computer "
            "Science), IT (Information Technology), EEE (Electrical & "
            "Electronics), Mechanical, Civil, Agricultural, Chemical, Biomedical, "
            "AI & DS (Artificial Intelligence & Data Science), CSE (Cyber "
            "Security) and CSE (IoT), along with MBA, MCA and research centres. "
            "Counselling Code: 2715."
        ),
        keywords=(
            "departments,department,available,list,branches,how many departments,"
            "which departments"
        ),
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about the ECE department",
        answer=(
            "Electronics & Communication Engineering (ECE) is one of the founding "
            "departments (started 2001) with an intake of 180. It covers "
            "electronics, communication systems, VLSI, embedded systems and signal "
            "processing. For admission details contact 7373714477."
        ),
        keywords="ece,electronics,communication,electronics and communication,vlsi,embedded",
        source_url=SOURCE["departments"],
        dept_code="ECE",
    ),
    dict(
        category="Departments",
        question="Tell me about the CSE department",
        answer=(
            "Computer Science & Engineering (CSE) started in 2001 with an intake of "
            "240. It covers programming, data structures, AI, networks, databases "
            "and software engineering. For admission details contact 7373714477."
        ),
        keywords="cse,computer science,computers,software,programming",
        source_url=SOURCE["departments"],
        dept_code="CSE",
    ),
    dict(
        category="Departments",
        question="Tell me about CSE (Cyber Security)",
        answer=(
            "B.Tech CSE (Cyber Security) was introduced in 2022 with an intake of "
            "60. It focuses on network security, ethical hacking, cryptography and "
            "digital forensics. For admission details contact 7373714477."
        ),
        keywords="cyber,cyber security,cybersecurity,cse cyber,ethical hacking,security",
        source_url=SOURCE["departments"],
        dept_code="CSE",
    ),
    dict(
        category="Departments",
        question="Tell me about CSE (IoT)",
        answer=(
            "B.Tech CSE (Internet of Things) was introduced in 2022 with an intake "
            "of 60. It covers IoT architecture, sensors, embedded systems and "
            "connected devices. For admission details contact 7373714477."
        ),
        keywords="iot,internet of things,cse iot,embedded,sensors",
        source_url=SOURCE["departments"],
        dept_code="CSE",
    ),
    dict(
        category="Departments",
        question="Tell me about the IT department",
        answer=(
            "Information Technology (IT) started in 2001 with an intake of 120. It "
            "covers software development, networking, web technologies and "
            "information systems. For admission details contact 7373714477."
        ),
        keywords="it,information technology,software,networking,web",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about AI & DS",
        answer=(
            "B.Tech Artificial Intelligence & Data Science (AI & DS) started in "
            "2021 with an intake of 120. It covers machine learning, deep learning, "
            "data science and AI applications. For admission details contact "
            "7373714477."
        ),
        keywords="ai,aids,ai and ds,artificial intelligence,data science,machine learning",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about the EEE department",
        answer=(
            "Electrical & Electronics Engineering (EEE) started in 2002 with an "
            "intake of 60. It covers power systems, electrical machines, power "
            "electronics and control systems. For admission details contact "
            "7373714477."
        ),
        keywords="eee,electrical,electrical and electronics,power",
        source_url=SOURCE["departments"],
        dept_code="EEE",
    ),
    dict(
        category="Departments",
        question="Tell me about the Mechanical department",
        answer=(
            "Mechanical Engineering started in 2005 with an intake of 60. It covers "
            "thermodynamics, manufacturing, CAD/CAM, automobile and thermal "
            "engineering. For admission details contact 7373714477."
        ),
        keywords="mechanical,mech,manufacturing,cad,automobile",
        source_url=SOURCE["departments"],
        dept_code="MECH",
    ),
    dict(
        category="Departments",
        question="Tell me about the Civil department",
        answer=(
            "Civil Engineering started in 2009 with an intake of 30. It covers "
            "structural, geotechnical, transportation and environmental "
            "engineering. For admission details contact 7373714477."
        ),
        keywords="civil,construction,structural",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about the Biomedical department",
        answer=(
            "Biomedical Engineering started in 2018 with an intake of 60. It "
            "combines engineering with medical science, covering medical "
            "instrumentation, biomaterials and imaging. For admission details "
            "contact 7373714477."
        ),
        keywords="biomedical,bio medical,bme,medical engineering",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about Agricultural Engineering",
        answer=(
            "B.Tech Agricultural Engineering started in 2017 with an intake of 60. "
            "It covers farm machinery, soil and water conservation, and "
            "agricultural processing. For admission details contact 7373714477."
        ),
        keywords="agricultural,agriculture,agri,farm",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Tell me about Chemical Engineering",
        answer=(
            "B.Tech Chemical Engineering started in 2017 with an intake of 30. It "
            "covers process engineering, thermodynamics and chemical plant design. "
            "For admission details contact 7373714477."
        ),
        keywords="chemical,process,chemistry",
        source_url=SOURCE["departments"],
    ),
    dict(
        category="Departments",
        question="Does the college offer MBA and MCA?",
        answer=(
            "Yes. MBA (intake 60) and MCA (intake 60) are offered, admitted through "
            "TANCA / Government counselling. MBA eligibility: recognised "
            "Bachelor's degree with 50% (45% reserved). MCA eligibility: BCA / "
            "B.Sc. IT/CS or any degree with Maths, 50% (45% reserved)."
        ),
        keywords="mba,mca,management,computer applications,pg",
        source_url=SOURCE["departments"],
        dept_code="MBA",
    ),
    # ---------------- Contact ----------------
    dict(
        category="Contact",
        question="What is the contact number of the college?",
        answer=(
            "Phone: 04294 - 225585 / 226393. Mobile: 7373714477 / 7373723722. "
            "Admission: 7373714477 (also WhatsApp). Email: info@nandhaengg.org. "
            "Admission email: aotechcampus@nandhainstitutions.org."
        ),
        keywords="contact,phone,number,mobile,telephone,call,email,reach",
        source_url=SOURCE["contact"],
    ),
    dict(
        category="Contact",
        question="What is the admission office contact?",
        answer=(
            "Admission contact: Mr. A.K. Velusamy, Administrative Officer - "
            "Mobile/WhatsApp 7373714477, Phone 04294-226393 / 225585, Email "
            "aotechcampus@nandhainstitutions.org. Out-of-state candidates: "
            "7373722199."
        ),
        keywords="admission contact,admission office,whom to contact,admission phone",
        source_url=SOURCE["admission"],
    ),
    dict(
        category="Contact",
        question="What is the email address?",
        answer=(
            "General email: info@nandhaengg.org. Admission: "
            "aotechcampus@nandhainstitutions.org. Out-of-state admission: "
            "admissionotherstates@nandhainstitutions.org. Placement: "
            "placement@nandhainstitutions.org. Transport: "
            "transport@nandhainstitutions.org."
        ),
        keywords="email,mail,id,address",
        source_url=SOURCE["contact"],
    ),
    dict(
        category="Contact",
        question="Who is the principal?",
        answer=(
            "The Principal of Nandha Engineering College is Dr. U.S. Ragupathy. "
            "Email: principal@nandhaengg.org, Phone: 7373712234."
        ),
        keywords="principal,head,college head",
        source_url=SOURCE["contact"],
    ),
    dict(
        category="Contact",
        question="Where is the college located?",
        answer=(
            "Nandha Engineering College (Autonomous), Erode - Perundurai Main Road, "
            "Vaikkaalmedu, Erode - 638 052, Tamil Nadu. The campus is about 25 "
            "acres on the Erode-Perundurai main road."
        ),
        keywords="location,address,where is,college address,place,distance",
        source_url=SOURCE["contact"],
    ),
    # ---------------- Transport ----------------
    dict(
        category="Transport",
        question="Is college transport / bus facility available?",
        answer=(
            "Yes. The college operates about 49 buses plus 1 emergency vehicle, "
            "covering a radius of about 85 km. Routes connect Tirupur, Avinashi, "
            "Tiruchengode, Sankari and nearby towns. Contact the transport office: "
            "9842717278, transport@nandhainstitutions.org."
        ),
        keywords="transport,bus,van,facility,conveyance,bus facility",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Transport",
        question="What are the bus routes and timings?",
        answer=(
            "Bus routes cover about an 85 km radius including Tirupur, Avinashi, "
            "Tiruchengode and Sankari. Exact route charts and pickup timings are "
            "available from the transport office. Contact 9842717278 or "
            "transport@nandhainstitutions.org."
        ),
        keywords="bus route,routes,timing,timings,pickup,drop,transport route",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Transport",
        question="Whom to contact for transport?",
        answer=(
            "Transport contact: 9842717278, email "
            "transport@nandhainstitutions.org."
        ),
        keywords="transport contact,transport office,bus contact",
        source_url=SOURCE["facilities"],
    ),
    # ---------------- Hostel ----------------
    dict(
        category="Hostel",
        question="Is hostel available?",
        answer=(
            "Yes. Separate hostels are available for men and women. Men's hostel: "
            "94 rooms (about 336 students); Women's hostel: 81 rooms. Facilities "
            "include attached washrooms, cot, table and chair, almirah, Wi-Fi, RO "
            "water, solar hot water, mess, 24x7 security, power backup and games. "
            "Hostel fee is not published; contact Boys 9942216806 / 9942216805, "
            "Girls 9095292168 / 7373710103."
        ),
        keywords="hostel,accommodation,staying,room,hostel available,dormitory",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Hostel",
        question="What are the hostel facilities?",
        answer=(
            "Hostel facilities: attached washrooms, bed/cot, table and chair, "
            "almirah, Wi-Fi, RO drinking water, solar hot water, dining/mess, "
            "hospital access, 24x7 security, power backup, laundry (paid) and "
            "indoor/outdoor games. Separate hostels for boys and girls."
        ),
        keywords="hostel facilities,hostel room,amenities,hostel facilities",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Hostel",
        question="Whom to contact for hostel?",
        answer=(
            "Hostel contacts - Boys: 9942216806 / 9942216805; Girls: 9095292168 / "
            "7373710103."
        ),
        keywords="hostel contact,hostel office,warden",
        source_url=SOURCE["facilities"],
    ),
    # ---------------- Placement ----------------
    dict(
        category="Placement",
        question="What are the placement opportunities?",
        answer=(
            "Placement highlights (as stated by the college): highest salary 44 "
            "LPA, 100% career settlement, 150+ regular recruiters and about 200 "
            "companies visiting campus. In 2025, 139 companies participated with "
            "about 90% placement. Contact: placement@nandhainstitutions.org, "
            "99655 26397."
        ),
        keywords="placement,placements,job,campus placement,recruitment,companies",
        source_url=SOURCE["placement"],
    ),
    dict(
        category="Placement",
        question="What is the highest salary / package?",
        answer=(
            "As per the college's placement information, the highest salary offered "
            "is 44 LPA and there are 51 offers above 7 LPA. For current details "
            "contact the Placement Cell: 99655 26397."
        ),
        keywords="highest salary,package,highest package,lpa,salary,ctc",
        source_url=SOURCE["placement"],
    ),
    dict(
        category="Placement",
        question="How many companies recruit students?",
        answer=(
            "About 200 companies visit the campus, with 150+ regular recruiters. In "
            "2025, 139 companies participated. Contact the Placement Cell at "
            "99655 26397 or placement@nandhainstitutions.org."
        ),
        keywords="companies,recruiters,recruit,how many companies",
        source_url=SOURCE["placement"],
    ),
    dict(
        category="Placement",
        question="Whom to contact for placement?",
        answer=(
            "Placement contact: placement@nandhainstitutions.org, 99655 26397. "
            "Placement Head: Dr. S. Sivaramakrishnan."
        ),
        keywords="placement contact,placement cell,placement office",
        source_url=SOURCE["placement"],
    ),
    # ---------------- Facilities ----------------
    dict(
        category="Facilities",
        question="What facilities are available on campus?",
        answer=(
            "Campus facilities include 76 classrooms, 102 laboratories, a central "
            "library (64,060 books, 20,541 titles), separate hostels, a 2,000-seat "
            "auditorium, canteen, Indian Bank ATM, sports grounds over 10 acres, a "
            "yoga centre and a gym, on a 25-acre campus."
        ),
        keywords="facilities,campus,infrastructure,amenities",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Facilities",
        question="Is there a library?",
        answer=(
            "Yes. The central library is about 10,800 sq ft with 64,060 books, "
            "20,541 titles, journals and digital resources."
        ),
        keywords="library,books,journals,digital library,study",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Facilities",
        question="Is there a canteen / ATM / auditorium?",
        answer=(
            "Yes. The campus has a canteen, an Indian Bank ATM, a 2,000-seat "
            "auditorium, sports grounds, a yoga centre and a gym."
        ),
        keywords="canteen,food,atm,bank,auditorium,sports,gym,yoga",
        source_url=SOURCE["facilities"],
    ),
    dict(
        category="Facilities",
        question="Is Wi-Fi available on campus?",
        answer="Yes, Wi-Fi and internet facilities are provided on campus and in the hostels.",
        keywords="wifi,wi-fi,internet,network",
        source_url=SOURCE["facilities"],
    ),
    # ---------------- College ----------------
    dict(
        category="College",
        question="What is the name of the college?",
        answer=(
            "Nandha Engineering College (Autonomous), Erode, Tamil Nadu. "
            "Counselling Code: 2715."
        ),
        keywords="name,college name,which college",
        source_url=SOURCE["home"],
    ),
    dict(
        category="College",
        question="Is Nandha Engineering College autonomous?",
        answer=(
            "Yes. Nandha Engineering College is an autonomous institution "
            "affiliated to Anna University, Chennai, and approved by AICTE, New "
            "Delhi."
        ),
        keywords="autonomous,autonomy,affiliation,anna university,aicte",
        source_url=SOURCE["home"],
    ),
    dict(
        category="College",
        question="Is Nandha Engineering College NAAC accredited?",
        answer=(
            "Yes. The college is accredited by NAAC with A+ Grade (CGPA 3.38) and "
            "several programmes are NBA accredited."
        ),
        keywords="naac,accreditation,nba,grade,accredited",
        source_url=SOURCE["home"],
    ),
    dict(
        category="College",
        question="When was Nandha Engineering College established?",
        answer=(
            "Nandha Engineering College was established in 2001 by the Sri Nandha "
            "Educational Trust (formed in 1992). It is in its 25th year (Silver "
            "Jubilee)."
        ),
        keywords="established,when,founded,year,history,silver jubilee",
        source_url=SOURCE["about"],
    ),
    dict(
        category="College",
        question="Who is the chairman of the college?",
        answer=(
            "The Chairman of Nandha Institutions is Thiru. V. Shanmugan. The "
            "college is run by the Sri Nandha Educational Trust."
        ),
        keywords="chairman,trust,founder,management",
        source_url=SOURCE["about"],
    ),
    dict(
        category="College",
        question="What is the counselling code?",
        answer="The counselling code of Nandha Engineering College is 2715.",
        keywords="counselling code,code,2715,tn counselling",
        source_url=SOURCE["admission"],
    ),
    # ---------------- Academics ----------------
    dict(
        category="Academics",
        question="Does the college offer Ph.D. / research programmes?",
        answer=(
            "Yes. The college has recognised research centres and offers Ph.D. "
            "programmes in several engineering and science disciplines, supported "
            "by an R&D Cell."
        ),
        keywords="phd,ph.d,research,doctorate,research center",
        source_url=SOURCE["about"],
    ),
    dict(
        category="Academics",
        question="What is OBE?",
        answer=(
            "OBE stands for Outcome-Based Education. The college follows OBE, where "
            "courses are designed around defined learning outcomes for students."
        ),
        keywords="obe,outcome based education,learning outcomes",
        source_url=SOURCE["about"],
    ),
    # ---------------- General ----------------
    dict(
        category="General",
        question="What is the college timing / working hours?",
        answer=(
            "The college functions on working days. Official office and admission "
            "timings are not published on the website. Please confirm by calling "
            "04294 - 225585 / 226393 or 7373714477 before visiting."
        ),
        keywords="college timing,working hours,office hours,open time,open,close",
        source_url=SOURCE["contact"],
        source_type="not_published",
    ),
    dict(
        category="General",
        question="What is the dress code / uniform?",
        answer=(
            "Uniform and dress-code details are provided by the college at the time "
            "of admission/registration. Please follow the college's prescribed "
            "dress code and carry your ID card."
        ),
        keywords="uniform,dress code,dress",
        source_url=SOURCE["home"],
        source_type="not_published",
    ),
    dict(
        category="General",
        question="Can I visit the campus?",
        answer=(
            "Yes, you are welcome to visit the campus at Erode - Perundurai Main "
            "Road, Vaikkaalmedu, Erode - 638 052. Please confirm the current office "
            "timings before visiting by calling 04294-225585 / 226393 or "
            "7373714477."
        ),
        keywords="visit,campus visit,come to college,tour",
        source_url=SOURCE["contact"],
    ),
    dict(
        category="General",
        question="How do I reach the college?",
        answer=(
            "The college is on the Erode-Perundurai Main Road at Vaikkaalmedu, "
            "Erode - 638 052. It is well connected by road and college buses also "
            "cover nearby towns. For help call 04294-225585 / 226393 or 7373714477."
        ),
        keywords="how to reach,reach college,direction,directions,route,way",
        source_url=SOURCE["contact"],
    ),
]


# ---------------------------------------------------------------------------
# Knowledge-base categories exposed to the AI / admin.
# ---------------------------------------------------------------------------
KB_CATEGORIES = [
    "College",
    "Admission",
    "Courses",
    "Departments",
    "Contact",
    "Transport",
    "Hostel",
    "Placement",
    "Facilities",
    "Academics",
    "General",
]
