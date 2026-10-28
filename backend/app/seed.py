"""Demo data seeder.

Seeds:
- departments (CSE, ECE, EEE, Mechanical, MBA)
- rooms/counters
- users (admin, receptionist, staff) with hashed passwords
- staff profiles
- configurable admission workflows + stages + queues
- FAQs and college information (knowledge base)
- sample visitors + queue entries

The seeder intentionally stops at V120 so the first live registration
during the demo produces V121 (Raj Kumar).
"""
from datetime import datetime

from .database import SessionLocal
from .nandha_knowledge import COLLEGE_INFO
from .models import (
    CollegeInformation,
    Department,
    FAQ,
    Queue,
    QueueEntry,
    Room,
    Staff,
    User,
    Visitor,
    VisitorStageHistory,
    Workflow,
    WorkflowStage,
)
from .security import hash_password


def _get_or_create(db, model, **kwargs):
    obj = db.query(model).filter_by(**kwargs).first()
    return obj


def _user(db, username, password, full_name, role, phone=""):
    u = _get_or_create(db, User, username=username)
    if u:
        return u
    u = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=role,
    )
    db.add(u)
    db.flush()
    return u


def _staff(db, user, emp_code, designation, dept):
    s = _get_or_create(db, Staff, employee_code=emp_code)
    if s:
        return s
    s = Staff(
        user_id=user.id,
        employee_code=emp_code,
        designation=designation,
        department_id=dept.id if dept else None,
    )
    db.add(s)
    db.flush()
    return s


def _workflow(db, code, name, dept, description=""):
    return _get_or_create(db, Workflow, code=code) or Workflow(
        code=code, name=name, department_id=dept.id if dept else None,
        description=description,
    )


def _stage(db, wf, name, order, queue_code, room, staff, description=""):
    stage = WorkflowStage(
        workflow_id=wf.id,
        name=name,
        stage_order=order,
        queue_code=queue_code,
        room_id=room.id if room else None,
        staff_id=staff.id if staff else None,
        description=description,
    )
    db.add(stage)
    db.flush()
    queue = _get_or_create(db, Queue, workflow_stage_id=stage.id) or Queue(
        workflow_stage_id=stage.id, name=f"{name} Queue"
    )
    db.add(queue)
    db.flush()
    return stage


def _place(
    db,
    visitor,
    stage,
    token_number,
    status,
    queue_current=None,
    completed_stages_completed=False,
):
    """Place a seeded visitor into a queue with a specific token."""
    queue = (
        db.query(Queue).filter(Queue.workflow_stage_id == stage.id).first()
    )
    if queue is None:
        queue = Queue(workflow_stage_id=stage.id, name=f"{stage.name} Queue")
        db.add(queue)
        db.flush()
    token = f"{stage.queue_code}-{token_number}"
    entry = QueueEntry(
        queue_id=queue.id,
        visitor_id=visitor.id,
        token_number=token_number,
        token_display=token,
        status=status,
        position_order=token_number,
        room_id=stage.room_id,
        completed_at=datetime.utcnow() if status == "COMPLETED" else None,
    )
    db.add(entry)
    db.flush()
    queue.current_token_number = max(queue.current_token_number or 0, token_number)
    if status in ("CALLED", "SERVING"):
        entry.called_at = datetime.utcnow()
    if status == "SERVING":
        entry.served_at = datetime.utcnow()

    history = VisitorStageHistory(
        visitor_id=visitor.id,
        workflow_stage_id=stage.id,
        queue_entry_id=entry.id,
        status="PENDING" if status not in ("COMPLETED",) else "COMPLETED",
        completed_at=entry.completed_at,
    )
    db.add(history)

    visitor.current_workflow_id = stage.workflow_id
    visitor.current_stage_id = stage.id
    visitor.current_queue_entry_id = entry.id
    if status == "COMPLETED":
        visitor.status = "COMPLETED"
        visitor.completed_at = datetime.utcnow()
    return entry


def _mark_previous_completed(db, visitor, stage):
    """Record completed stage history for stages before the current one."""
    history = VisitorStageHistory(
        visitor_id=visitor.id,
        workflow_stage_id=stage.id,
        status="COMPLETED",
        completed_at=datetime.utcnow(),
    )
    db.add(history)


def seed_all():
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            return

        # ---------- Departments ----------
        cse = Department(code="CSE", name="Computer Science & Engineering",
                         description="B.Tech in Computer Science and Engineering")
        ece = Department(code="ECE", name="Electronics & Communication Engineering",
                         description="B.Tech in Electronics and Communication")
        eee = Department(code="EEE", name="Electrical & Electronics Engineering",
                         description="B.Tech in Electrical and Electronics")
        mech = Department(code="MECH", name="Mechanical Engineering",
                          description="B.Tech in Mechanical Engineering")
        mba = Department(code="MBA", name="Master of Business Administration",
                         description="MBA programme")
        db.add_all([cse, ece, eee, mech, mba])
        db.flush()

        # ---------- Rooms / Counters ----------
        rooms = [
            Room(code="R001", name="Reception Hall", building="Main Entrance",
                 floor="Ground Floor", counter="Reception Desk 1",
                 description="Main registration desk"),
            Room(code="R101", name="Counselling Room", building="Academic Block",
                 floor="First Floor", counter="Counselling Counter",
                 description="Admission counselling and guidance"),
            Room(code="R102", name="Eligibility Counter", building="Academic Block",
                 floor="First Floor", counter="Eligibility 1",
                 description="Eligibility verification"),
            Room(code="DV-1", name="Document Verification", building="Academic Block",
                 floor="Second Floor", counter="Document Verification 1",
                 description="Original document verification"),
            Room(code="AC-1", name="Accounts Counter", building="Administrative Block",
                 floor="Ground Floor", counter="Accounts 1",
                 description="Fee payment and receipts"),
            Room(code="AD-1", name="Admission Confirmation Office",
                 building="Administrative Block", floor="First Floor",
                 counter="Confirmation 1", description="Final admission confirmation"),
            Room(code="RG-1", name="Registration Counter", building="Administrative Block",
                 floor="First Floor", counter="Registration 1",
                 description="Enrolment and registration"),
            Room(code="HD-1", name="Help Desk & Counselling", building="Main Entrance",
                 floor="Ground Floor", counter="Help Desk",
                 description="Guidance for visitors who are not sure"),
        ]
        db.add_all(rooms)
        db.flush()
        (reception_room, counselling_room, eligibility_room, doc_room,
         accounts_room, admission_room, registration_room, help_room) = rooms

        # ---------- Users ----------
        admin_u = _user(db, "admin", "admin123", "Dr. Radhika Verma",
                        "ADMIN", "9845010001")
        reception_u = _user(db, "reception", "reception123", "Sneha Receptionist",
                            "RECEPTIONIST", "9845010002")

        priya_u = _user(db, "priya", "staff123", "Mrs. Priya Sharma",
                        "STAFF", "9845010003")
        arun_u = _user(db, "arun", "staff123", "Mr. Arun Verma",
                       "STAFF", "9845010004")
        kavita_u = _user(db, "kavita", "staff123", "Ms. Kavita Nair",
                         "STAFF", "9845010005")
        suresh_u = _user(db, "suresh", "staff123", "Mr. Suresh Menon",
                         "STAFF", "9845010006")
        anita_u = _user(db, "anita", "staff123", "Dr. Anita Rao",
                        "STAFF", "9845010007")
        vikram_u = _user(db, "vikram", "staff123", "Mr. Vikram Patel",
                         "STAFF", "9845010008")
        divya_u = _user(db, "divya", "staff123", "Ms. Divya Nair",
                        "STAFF", "9845010009")

        # ---------- Staff ----------
        counsellor = _staff(db, priya_u, "STF-001", "Admission Counsellor", None)
        eligibility_officer = _staff(db, arun_u, "STF-002", "Eligibility Officer", None)
        doc_officer = _staff(db, kavita_u, "STF-003", "Document Verification Officer", None)
        accounts_officer = _staff(db, suresh_u, "STF-004", "Accounts Officer", None)
        admission_officer = _staff(db, anita_u, "STF-005", "Admission Officer", None)
        registrar = _staff(db, vikram_u, "STF-006", "Registrar", None)
        help_desk_staff = _staff(db, divya_u, "STF-007", "Help Desk Officer", None)

        # ---------- Workflows + Stages ----------
        # ECE  (6 stages)
        ece_wf = _workflow(
            db, "ECE-ADM", "ECE Admission", ece,
            "Full admission workflow for ECE department")
        db.add(ece_wf)
        db.flush()
        ece_couns = _stage(db, ece_wf, "Counselling", 1, "ECE-COUNS",
                           counselling_room, counsellor, "Guidance and counselling")
        ece_elig = _stage(db, ece_wf, "Eligibility Verification", 2, "ECE-ELIG",
                          eligibility_room, eligibility_officer, "Check eligibility")
        ece_doc = _stage(db, ece_wf, "Document Verification", 3, "ECE-DOC",
                         doc_room, doc_officer, "Verify original documents")
        ece_ac = _stage(db, ece_wf, "Accounts", 4, "ECE-AC",
                        accounts_room, accounts_officer, "Fee payment / accounts")
        ece_adm = _stage(db, ece_wf, "Admission Confirmation", 5, "ECE-ADM",
                         admission_room, admission_officer, "Confirm admission")
        ece_reg = _stage(db, ece_wf, "Registration", 6, "ECE-REG",
                         registration_room, registrar, "Final registration")

        # CSE  (7 stages - demonstrates configurable difference)
        cse_wf = _workflow(
            db, "CSE-ADM", "CSE Admission", cse,
            "CSE workflow includes an extra Fee Payment stage")
        db.add(cse_wf)
        db.flush()
        cse_couns = _stage(db, cse_wf, "Counselling", 1, "CSE-COUNS",
                           counselling_room, counsellor)
        cse_elig = _stage(db, cse_wf, "Eligibility Verification", 2, "CSE-ELIG",
                          eligibility_room, eligibility_officer)
        cse_doc = _stage(db, cse_wf, "Document Verification", 3, "CSE-DOC",
                         doc_room, doc_officer)
        cse_ac = _stage(db, cse_wf, "Accounts", 4, "CSE-AC",
                        accounts_room, accounts_officer)
        cse_fee = _stage(db, cse_wf, "Fee Payment", 5, "CSE-FEE",
                         accounts_room, accounts_officer, "Pay admission fee")
        cse_adm = _stage(db, cse_wf, "Admission Confirmation", 6, "CSE-ADM",
                         admission_room, admission_officer)
        cse_reg = _stage(db, cse_wf, "Registration", 7, "CSE-REG",
                         registration_room, registrar)

        # EEE (6 stages)
        eee_wf = _workflow(db, "EEE-ADM", "EEE Admission", eee,
                           "Full admission workflow for EEE")
        db.add(eee_wf)
        db.flush()
        eee_couns = _stage(db, eee_wf, "Counselling", 1, "EEE-COUNS",
                           counselling_room, counsellor)
        eee_elig = _stage(db, eee_wf, "Eligibility Verification", 2, "EEE-ELIG",
                          eligibility_room, eligibility_officer)
        eee_doc = _stage(db, eee_wf, "Document Verification", 3, "EEE-DOC",
                         doc_room, doc_officer)
        eee_ac = _stage(db, eee_wf, "Accounts", 4, "EEE-AC",
                        accounts_room, accounts_officer)
        eee_adm = _stage(db, eee_wf, "Admission Confirmation", 5, "EEE-ADM",
                         admission_room, admission_officer)
        eee_reg = _stage(db, eee_wf, "Registration", 6, "EEE-REG",
                         registration_room, registrar)

        # MECH (6 stages)
        mech_wf = _workflow(db, "MECH-ADM", "Mechanical Admission", mech,
                            "Full admission workflow for Mechanical")
        db.add(mech_wf)
        db.flush()
        mech_couns = _stage(db, mech_wf, "Counselling", 1, "MECH-COUNS",
                            counselling_room, counsellor)
        mech_elig = _stage(db, mech_wf, "Eligibility Verification", 2, "MECH-ELIG",
                           eligibility_room, eligibility_officer)
        mech_doc = _stage(db, mech_wf, "Document Verification", 3, "MECH-DOC",
                          doc_room, doc_officer)
        mech_ac = _stage(db, mech_wf, "Accounts", 4, "MECH-AC",
                         accounts_room, accounts_officer)
        mech_adm = _stage(db, mech_wf, "Admission Confirmation", 5, "MECH-ADM",
                          admission_room, admission_officer)
        mech_reg = _stage(db, mech_wf, "Registration", 6, "MECH-REG",
                          registration_room, registrar)

        # MBA (5 stages - shorter workflow)
        mba_wf = _workflow(
            db, "MBA-ADM", "MBA Admission", mba,
            "MBA has a shorter admission workflow")
        db.add(mba_wf)
        db.flush()
        mba_couns = _stage(db, mba_wf, "Counselling", 1, "MBA-COUNS",
                           counselling_room, counsellor)
        mba_doc = _stage(db, mba_wf, "Document Verification", 2, "MBA-DOC",
                         doc_room, doc_officer)
        mba_ac = _stage(db, mba_wf, "Accounts", 3, "MBA-AC",
                        accounts_room, accounts_officer)
        mba_adm = _stage(db, mba_wf, "Admission Confirmation", 4, "MBA-ADM",
                         admission_room, admission_officer)
        mba_reg = _stage(db, mba_wf, "Registration", 5, "MBA-REG",
                         registration_room, registrar)

        # Help Desk (1 stage, no department)
        help_wf = _workflow(
            db, "HELP-DESK", "Counselling / Help Desk", None,
            "For visitors who are not sure which department or process applies")
        db.add(help_wf)
        db.flush()
        help_stage = _stage(db, help_wf, "Counselling / Help Desk", 1, "HD",
                            help_room, help_desk_staff,
                            "Guidance to choose the right department/process")

        db.flush()

        # ---------- Knowledge base: FAQs ----------
        faqs = [
            FAQ(question="What documents are required for ECE admission?",
                answer="Required documents for ECE (B.Tech):\n"
                       "1. Class 10 and 12 mark sheets & certificates\n"
                       "2. Transfer Certificate (TC)\n3. Conduct Certificate\n"
                       "4. Migration Certificate (if applicable)\n"
                       "5. Entrance exam score card\n6. Income certificate (for scholarships)\n"
                       "7. Caste/category certificate (if applicable)\n"
                       "8. 6 passport-size photos\n"
                       "9. Aadhaar card and ID proof of student & parent",
                category="Admission", keywords="documents,ece,admission,required,mark sheet,certificate",
                department_id=ece.id),
            FAQ(question="What documents are required for CSE admission?",
                answer="Required documents for CSE (B.Tech):\n"
                       "1. Class 10 and 12 mark sheets & certificates\n"
                       "2. Transfer Certificate (TC)\n3. Conduct Certificate\n"
                       "4. Entrance exam score card\n5. Income certificate (if applicable)\n"
                       "6. 6 passport-size photos\n7. Aadhaar card",
                category="Admission", keywords="documents,cse,admission,required,certificate",
                department_id=cse.id),
            FAQ(question="What documents are required for MBA admission?",
                answer="For MBA admission you need:\n"
                       "1. Degree mark sheets (all semesters)\n"
                       "2. Degree/Provisional certificate\n"
                       "3. Entrance exam score card (CAT/MAT/CMAT)\n"
                       "4. Transfer Certificate\n5. 6 passport-size photos\n"
                       "6. Aadhaar card and photo ID",
                category="Admission", keywords="documents,mba,required,degree",
                department_id=mba.id),
            FAQ(question="What is the eligibility for B.Tech admission?",
                answer="General eligibility for B.Tech:\n"
                       "- Class 12 (Science) with Physics, Chemistry and Mathematics\n"
                       "- Minimum aggregate as per university rules (usually 45-60%)\n"
                       "- Valid rank/score in the state/university entrance exam\n"
                       "Department-specific minimums may vary - the eligibility "
                       "counter can confirm for your case.",
                category="Admission", keywords="eligibility,b.tech,qualification,marks"),
            FAQ(question="What is the admission fee structure?",
                answer="Fee structure (indicative):\n"
                       "- B.Tech tuition: Rs. 45,000 - 60,000 per year depending on department\n"
                       "- MBA: Rs. 80,000 per year\n"
                       "- Admission/registration fee: Rs. 5,000 (one-time)\n"
                       "- Hostel fee: Rs. 40,000 - 60,000 per year\n"
                       "Scholarships are available for meritorious and "
                       "economically weaker students.\n"
                       "Please confirm the exact figures at the Accounts counter.",
                category="Fees", keywords="fee,fees,cost,amount,tuition,charges"),
            FAQ(question="Is hostel available?",
                answer="Yes, hostel accommodation is available.\n"
                       "- Separate hostels for boys and girls\n"
                       "- Rooms: shared (2/3 sharing) and limited single rooms\n"
                       "- Facilities: mess, laundry, Wi-Fi, 24x7 security, medical room\n"
                       "- Hostel allotment is done after admission confirmation\n"
                       "Please collect the hostel form at Registration.",
                category="Hostel", keywords="hostel,room,accommodation,staying,hostel availability"),
            FAQ(question="What transport facilities are available?",
                answer="College transport:\n"
                       "- 25+ bus routes covering city and nearby towns\n"
                       "- Monthly bus pass facility\n"
                       "- Pickup/drop timing chart is available at the transport office\n"
                       "- For route details contact the transport desk in the main office.",
                category="Transport", keywords="transport,bus,van,conveyance,route"),
            FAQ(question="What are the college timings?",
                answer="College timings:\n"
                       "- Admission office: 9:00 AM - 5:00 PM (Mon-Sat)\n"
                       "- Classes: 9:00 AM - 4:00 PM\n"
                       "- Accounts counter: 10:00 AM - 4:00 PM\n"
                       "- The college is open on all working days except Sundays "
                       "and gazetted holidays.",
                category="Timings", keywords="timing,timings,time,open,hours,saturday,sunday"),
            FAQ(question="Where is the admission office?",
                answer="The admission office is located in the Administrative Block, "
                       "First Floor (Room AD-1). For help with your admission process "
                       "you can also start at the Help Desk at the main entrance.",
                category="Location", keywords="admission office,where,room,location"),
            FAQ(question="Where is the help desk?",
                answer="The Help Desk is at the main entrance, Ground Floor (Room HD-1). "
                       "Our counsellors will help you choose the right department.",
                category="Location", keywords="help desk,reception,assistance"),
            FAQ(question="Can I get a seat through management quota?",
                answer="Yes, a limited number of seats are available under the "
                       "management quota for each department. Please meet the "
                       "Admission Officer (Room AD-1) for details and counselling.",
                category="Admission", keywords="management quota,seat,reservation"),
            FAQ(question="Which courses are offered?",
                answer="Courses offered:\n"
                       "- B.Tech in CSE, ECE, EEE, Mechanical Engineering\n"
                       "- MBA\n"
                       "Intake and eligibility details are available at the "
                       "Help Desk or in the admission office.",
                category="College", keywords="courses,programmes,degrees,b.tech,mba"),
            FAQ(question="Is there any scholarship available?",
                answer="Scholarships:\n"
                       "- Merit scholarships based on entrance rank / academics\n"
                       "- Government scholarships (SC/ST/OBC/EBC) - documents verified here\n"
                       "- Sports quota scholarships\n"
                       "Submit scholarship forms at the Admission Confirmation stage.",
                category="Fees", keywords="scholarship,financial,concession"),
            FAQ(question="How long does the admission process take?",
                answer="A complete admission usually takes 45 minutes to 2 hours "
                       "depending on queues. You will be guided stage by stage "
                       "by our AI assistant and staff.",
                category="Admission", keywords="how long,duration,takes,time"),
            FAQ(question="Can parents accompany the student during admission?",
                answer="Yes, parents are welcome to accompany students at every stage "
                       "of the admission process. Please carry the required documents.",
                category="Admission", keywords="parents,accompany,guardian"),
            FAQ(question="Where can I pay the admission fee?",
                answer="The fee is paid at the Accounts Counter (Room AC-1) in the "
                       "Administrative Block, Ground Floor. Online payment is also "
                       "accepted after document verification.",
                category="Fees", keywords="pay,fee,accounts,counter,bank"),
            FAQ(question="What is the college uniform/dress code?",
                answer="Dress code:\n"
                       "- Students must wear the prescribed college uniform.\n"
                       "- Uniform details are provided at Registration.\n"
                       "- College ID card is mandatory from the first day.",
                category="College", keywords="uniform,dress code"),
        ]
        db.add_all(faqs)
        # The generic demo FAQs above are scaffolding only. The official
        # Nandha knowledge base (see seed_nandha_knowledge.py) is the single
        # active source of truth, so keep these inactive.
        for faq in faqs:
            faq.is_active = False

        # ---------- Knowledge base: College information ----------
        # Seeded from the official Nandha knowledge module so no generic
        # placeholder ("ABC College") data is ever active.
        college_info = [
            CollegeInformation(
                key=item["key"],
                title=item["title"],
                content=item["content"],
                category=item["category"],
                source_url=item.get("source_url", ""),
                source_type=item.get("source_type", "official_website"),
            )
            for item in COLLEGE_INFO
        ]
        db.add_all(college_info)

        # ---------- Sample visitors ----------
        def visitor(code, name, phone, purpose, dept, remarks=""):
            v = Visitor(
                visitor_code=code, full_name=name, phone=phone,
                purpose=purpose, department_id=dept.id if dept else None,
                remarks=remarks,
            )
            db.add(v)
            db.flush()
            return v

        # CSE visitors
        v101 = visitor("V101", "Ramesh Iyer", "9811010101", "Admission", cse)
        v102 = visitor("V102", "Lakshmi Nair", "9811010102", "Admission", cse)
        v103 = visitor("V103", "Kiran Joshi", "9811010103", "Admission", cse)
        v104 = visitor("V104", "Anil Kumar", "9811010104", "Admission", cse)
        v105 = visitor("V105", "Meera Pillai", "9811010105", "Admission", cse)

        # EEE visitors
        v106 = visitor("V106", "Sanjay Gupta", "9811010106", "Admission", eee)
        v107 = visitor("V107", "Pooja Reddy", "9811010107", "Admission", eee)

        # MECH visitors
        v108 = visitor("V108", "Arjun Nanda", "9811010108", "Admission", mech)
        v109 = visitor("V109", "Neha Kulkarni", "9811010109", "Admission", mech)

        # MBA visitors
        v110 = visitor("V110", "Ravi Shankar", "9811010110", "Admission", mba)
        v111 = visitor("V111", "Sita Devi", "9811010111", "Admission", mba)
        v112 = visitor("V112", "Mohan Das", "9811010112", "Admission", mba)

        # ECE visitors
        v113 = visitor("V113", "Farhan Ali", "9811010113", "Admission", ece)
        v114 = visitor("V114", "Geeta Rani", "9811010114", "Admission", ece)
        v115 = visitor("V115", "Vikas Bhat", "9811010115", "Admission", ece)
        v116 = visitor("V116", "Sunil Rao", "9811010116", "Admission", ece)
        v117 = visitor("V117", "Anita Desai", "9811010117", "Admission", ece)
        v118 = visitor("V118", "Deepa Menon", "9811010118", "Admission", ece)
        v119 = visitor("V119", "Hari Prasad", "9811010119", "Admission", ece)

        # V120 is the current person being served in ECE Counselling, so the
        # next registration (Raj Kumar, the demo parent) becomes V121.
        v120 = visitor("V120", "Rajesh Kumar", "9811010120", "Admission", ece,
                       "Second visit - continues his admission process.")

        # Place visitors into queues ----------------------------------------
        # CSE counselling / eligibility / documents / fee
        _place(db, v101, cse_couns, 140, "WAITING")
        _place(db, v102, cse_couns, 141, "WAITING")
        _place(db, v103, cse_elig, 60, "SERVING")
        _mark_previous_completed(db, v103, cse_couns)
        _place(db, v104, cse_doc, 42, "WAITING")
        _mark_previous_completed(db, v104, cse_couns)
        _mark_previous_completed(db, v104, cse_elig)
        _place(db, v105, cse_fee, 19, "WAITING")
        _mark_previous_completed(db, v105, cse_couns)
        _mark_previous_completed(db, v105, cse_elig)
        _mark_previous_completed(db, v105, cse_doc)
        _mark_previous_completed(db, v105, cse_ac)

        # EEE
        _place(db, v106, eee_couns, 75, "WAITING")
        _place(db, v107, eee_couns, 76, "WAITING")

        # MECH
        _place(db, v108, mech_couns, 50, "SERVING")
        _place(db, v109, mech_doc, 28, "WAITING")
        _mark_previous_completed(db, v109, mech_couns)
        _mark_previous_completed(db, v109, mech_elig)

        # MBA
        _place(db, v110, mba_couns, 90, "WAITING")
        _place(db, v111, mba_doc, 37, "SERVING")
        _mark_previous_completed(db, v111, mba_couns)
        _place(db, v112, mba_ac, 22, "WAITING")
        _mark_previous_completed(db, v112, mba_couns)
        _mark_previous_completed(db, v112, mba_doc)

        # ECE (V113-V120)
        # ECE Counselling has exactly one SERVING visitor (V120). Waiting queue
        # stays empty so the first live registration (Raj Kumar -> V121) is the
        # immediate next person in line during the demo.
        _place(db, v120, ece_couns, 123, "SERVING")

        # ECE Eligibility
        _place(db, v115, ece_elig, 79, "WAITING")
        _mark_previous_completed(db, v115, ece_couns)
        _place(db, v114, ece_elig, 80, "WAITING")
        _mark_previous_completed(db, v114, ece_couns)
        _place(db, v113, ece_elig, 81, "WAITING")
        _mark_previous_completed(db, v113, ece_couns)
        _place(db, v118, ece_elig, 82, "WAITING")
        _mark_previous_completed(db, v118, ece_couns)

        # ECE Document Verification
        _place(db, v117, ece_doc, 43, "WAITING")
        _mark_previous_completed(db, v117, ece_couns)
        _mark_previous_completed(db, v117, ece_elig)
        _place(db, v116, ece_doc, 45, "WAITING")
        _mark_previous_completed(db, v116, ece_couns)
        _mark_previous_completed(db, v116, ece_elig)
        _place(db, v119, ece_doc, 46, "WAITING")
        _mark_previous_completed(db, v119, ece_couns)
        _mark_previous_completed(db, v119, ece_elig)

        db.commit()
    finally:
        db.close()