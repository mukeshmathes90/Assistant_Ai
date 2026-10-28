import React, { useCallback, useEffect, useState } from "react";
import {
  BookOpen, Building2, GraduationCap, Layers, LayoutDashboard,
  MessageSquare, RefreshCw, Settings, Users,
} from "lucide-react";
import Layout from "../components/Layout.jsx";
import { API } from "../lib/api.js";
import {
  Badge, Btn, inputCls, Label, Modal, Spinner, StatCard,
} from "../components/ui.jsx";

const TABS = [
  { key: "overview", label: "Overview", icon: LayoutDashboard },
  { key: "departments", label: "Departments", icon: Layers },
  { key: "rooms", label: "Rooms", icon: Building2 },
  { key: "staff", label: "Staff", icon: Users },
  { key: "workflows", label: "Workflows", icon: BookOpen },
  { key: "faqs", label: "FAQs", icon: MessageSquare },
  { key: "college", label: "College Info", icon: GraduationCap },
  { key: "visitors", label: "Visitors", icon: Settings },
];

export default function Admin() {
  const [tab, setTab] = useState("overview");
  const [stats, setStats] = useState(null);
  const [toast, setToast] = useState("");

  const loadStats = useCallback(async () => {
    try {
      const r = await API.get("/api/admin/stats");
      setStats(r.data);
    } catch {}
  }, []);

  useEffect(() => {
    if (tab === "overview") loadStats();
    const t = setInterval(loadStats, 10000);
    return () => clearInterval(t);
  }, [tab, loadStats]);

  function flash(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  return (
    <Layout title="Admin Dashboard">
      <div className="mb-5 flex flex-wrap gap-1.5 overflow-x-auto border-b border-slate-200 pb-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              tab === t.key
                ? "bg-indigo-600 text-white"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {toast && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
          {toast}
        </div>
      )}

      {tab === "overview" && <Overview stats={stats} onRefresh={loadStats} />}
      {tab === "departments" && <DepartmentsTab flash={flash} />}
      {tab === "rooms" && <RoomsTab flash={flash} />}
      {tab === "staff" && <StaffTab flash={flash} />}
      {tab === "workflows" && <WorkflowsTab flash={flash} />}
      {tab === "faqs" && <FaqTab flash={flash} />}
      {tab === "college" && <CollegeTab flash={flash} />}
      {tab === "visitors" && <VisitorsTab />}
    </Layout>
  );
}

/* ------------------------------------------------------------------ */
/*  Overview                                                          */
/* ------------------------------------------------------------------ */
function Overview({ stats, onRefresh }) {
  if (!stats) return <Spinner />;
  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Btn variant="ghost" onClick={onRefresh}>
          <RefreshCw size={14} /> Refresh
        </Btn>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Today" value={stats.total_visitors_today} accent="text-indigo-600" />
        <StatCard label="Waiting" value={stats.waiting} accent="text-amber-600" />
        <StatCard label="Serving" value={stats.serving} accent="text-sky-600" />
        <StatCard label="Completed" value={stats.completed_today} accent="text-emerald-600" />
      </div>
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-sm font-semibold text-slate-700">By Department</h3>
        {stats.by_department.length === 0 ? (
          <p className="text-sm text-slate-400">No data yet</p>
        ) : (
          <div className="space-y-2">
            {stats.by_department.map((d) => {
              const max = Math.max(...stats.by_department.map((x) => x.count));
              return (
                <div key={d.department} className="flex items-center gap-3">
                  <span className="w-12 text-xs font-semibold text-slate-600">{d.department}</span>
                  <div className="relative h-6 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="absolute inset-y-0 left-0 rounded-full bg-indigo-500"
                      style={{ width: `${(d.count / max) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs font-semibold text-slate-600">{d.count}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Generic CRUD helpers                                              */
/* ------------------------------------------------------------------ */
function useCrud(path) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await API.get(path);
      setItems(r.data);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => { load(); }, [load]);

  async function create(data) {
    await API.post(path, data);
    await load();
  }

  async function update(id, data) {
    const sub = path.includes("/workflows/") ? "" : "";
    await API.put(`${path}/${id}`, data);
    await load();
  }

  async function remove(id) {
    await API.delete(`${path}/${id}`);
    await load();
  }

  return { items, loading, load, create, update, remove };
}

function Table({ headers, children }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
            {headers.map((h, i) => (
              <th key={i} className="px-4 py-2">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Departments                                                       */
/* ------------------------------------------------------------------ */
function DepartmentsTab({ flash }) {
  const { items, loading, load, create, update, remove } = useCrud("/api/admin/departments");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", description: "" });
  const [editId, setEditId] = useState(null);

  function startCreate() {
    setForm({ code: "", name: "", description: "" });
    setEditId(null);
    setOpen(true);
  }

  function startEdit(d) {
    setForm({ code: d.code, name: d.name, description: d.description || "" });
    setEditId(d.id);
    setOpen(true);
  }

  async function save() {
    if (editId) {
      await update(editId, { ...form, is_active: true });
      flash("Department updated");
    } else {
      await create({ ...form, is_active: true });
      flash("Department created");
    }
    setOpen(false);
  }

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <Btn onClick={startCreate}>Add Department</Btn>
      </div>
      {loading ? <Spinner /> : (
        <Table headers={["Code", "Name", "Description", "Actions"]}>
          {items.map((d) => (
            <tr key={d.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2 font-semibold text-indigo-700">{d.code}</td>
              <td className="px-4 py-2">{d.name}</td>
              <td className="px-4 py-2 text-slate-500">{d.description || "—"}</td>
              <td className="px-4 py-2 space-x-1">
                <Btn variant="ghost" className="px-2 py-1 text-xs" onClick={() => startEdit(d)}>Edit</Btn>
                <Btn variant="ghost" className="px-2 py-1 text-xs text-rose-600" onClick={async () => {
                  if (!window.confirm(`Deactivate ${d.code}?`)) return;
                  await remove(d.id);
                  flash("Department deactivated");
                }}>Deactivate</Btn>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-slate-400">No departments</td></tr>}
        </Table>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit Department" : "New Department"}>
        <div className="space-y-3">
          <div>
            <Label>Code *</Label>
            <input className={inputCls} value={form.code} onChange={(e) => setForm({...form, code: e.target.value})} placeholder="e.g. CSE" />
          </div>
          <div>
            <Label>Name *</Label>
            <input className={inputCls} value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} placeholder="e.g. Computer Science" />
          </div>
          <div>
            <Label>Description</Label>
            <input className={inputCls} value={form.description} onChange={(e) => setForm({...form, description: e.target.value})} />
          </div>
          <Btn onClick={save}>Save</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Rooms                                                             */
/* ------------------------------------------------------------------ */
function RoomsTab({ flash }) {
  const { items, loading, load, create, update, remove } = useCrud("/api/admin/rooms");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", building: "Main Building", floor: "Ground Floor", counter: "" });
  const [editId, setEditId] = useState(null);

  function startCreate() { setForm({ code: "", name: "", building: "Main Building", floor: "Ground Floor", counter: "" }); setEditId(null); setOpen(true); }
  function startEdit(r) { setForm({ code: r.code, name: r.name, building: r.building, floor: r.floor, counter: r.counter || "" }); setEditId(r.id); setOpen(true); }
  async function save() {
    if (editId) { await update(editId, { ...form, is_active: true, description: "" }); flash("Room updated"); }
    else { await create({ ...form, is_active: true, description: "" }); flash("Room created"); }
    setOpen(false);
  }

  return (
    <div>
      <div className="mb-4 flex justify-end"><Btn onClick={startCreate}>Add Room</Btn></div>
      {loading ? <Spinner /> : (
        <Table headers={["Code", "Name", "Building", "Floor", "Actions"]}>
          {items.map((r) => (
            <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2 font-mono font-semibold text-indigo-700">{r.code}</td>
              <td className="px-4 py-2">{r.name}</td>
              <td className="px-4 py-2 text-slate-500">{r.building}</td>
              <td className="px-4 py-2 text-slate-500">{r.floor}</td>
              <td className="px-4 py-2 space-x-1">
                <Btn variant="ghost" className="px-2 py-1 text-xs" onClick={() => startEdit(r)}>Edit</Btn>
                <Btn variant="ghost" className="px-2 py-1 text-xs text-rose-600" onClick={async () => {
                  if (!window.confirm(`Deactivate ${r.code}?`)) return;
                  await remove(r.id); flash("Room deactivated");
                }}>Deactivate</Btn>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-slate-400">No rooms</td></tr>}
        </Table>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit Room" : "New Room"}>
        <div className="space-y-3">
          <div><Label>Code *</Label><input className={inputCls} value={form.code} onChange={(e) => setForm({...form, code: e.target.value})} placeholder="e.g. R101" /></div>
          <div><Label>Name *</Label><input className={inputCls} value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Building</Label><input className={inputCls} value={form.building} onChange={(e) => setForm({...form, building: e.target.value})} /></div>
            <div><Label>Floor</Label><input className={inputCls} value={form.floor} onChange={(e) => setForm({...form, floor: e.target.value})} /></div>
          </div>
          <Btn onClick={save}>Save</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Staff                                                             */
/* ------------------------------------------------------------------ */
function StaffTab({ flash }) {
  const { items, loading, load, create, remove } = useCrud("/api/admin/staff");
  const [departments, setDepartments] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", full_name: "", employee_code: "", designation: "", department_id: "", phone: "" });

  useEffect(() => { API.get("/api/admin/departments").then((r) => setDepartments(r.data)); }, []);

  function startCreate() { setForm({ username: "", password: "", full_name: "", employee_code: "", designation: "", department_id: "", phone: "" }); setOpen(true); }
  async function save() {
    await create({ ...form, department_id: form.department_id ? Number(form.department_id) : null, is_active: true });
    flash("Staff member created"); setOpen(false);
  }

  return (
    <div>
      <div className="mb-4 flex justify-end"><Btn onClick={startCreate}>Add Staff</Btn></div>
      {loading ? <Spinner /> : (
        <Table headers={["Employee Code", "Full Name", "Username", "Designation", "Dept", "Actions"]}>
          {items.map((s) => (
            <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2 font-mono font-semibold text-indigo-700">{s.employee_code}</td>
              <td className="px-4 py-2">{s.full_name}</td>
              <td className="px-4 py-2 text-slate-500">{s.username}</td>
              <td className="px-4 py-2 text-slate-500">{s.designation}</td>
              <td className="px-4 py-2 text-slate-500">{s.department_code || "Help Desk"}</td>
              <td className="px-4 py-2 space-x-1">
                <Btn variant="ghost" className="px-2 py-1 text-xs text-rose-600" onClick={async () => {
                  if (!window.confirm("Deactivate this staff?")) return;
                  await remove(s.id); flash("Staff deactivated");
                }}>Deactivate</Btn>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={6} className="p-6 text-center text-slate-400">No staff</td></tr>}
        </Table>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title="Add Staff">
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Username *</Label><input className={inputCls} value={form.username} onChange={(e) => setForm({...form, username: e.target.value})} /></div>
            <div><Label>Password *</Label><input type="password" className={inputCls} value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} /></div>
          </div>
          <div><Label>Full Name *</Label><input className={inputCls} value={form.full_name} onChange={(e) => setForm({...form, full_name: e.target.value})} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Employee Code *</Label><input className={inputCls} value={form.employee_code} onChange={(e) => setForm({...form, employee_code: e.target.value})} /></div>
            <div><Label>Designation</Label><input className={inputCls} value={form.designation} onChange={(e) => setForm({...form, designation: e.target.value})} /></div>
          </div>
          <div><Label>Department</Label>
            <select className={inputCls} value={form.department_id} onChange={(e) => setForm({...form, department_id: e.target.value})}>
              <option value="">Help Desk / General</option>
              {departments.map((d) => <option key={d.id} value={d.id}>{d.code} – {d.name}</option>)}
            </select>
          </div>
          <Btn onClick={save}>Create Staff</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Workflows + Stages                                                */
/* ------------------------------------------------------------------ */
function WorkflowsTab({ flash }) {
  const { items, loading, load, create, update } = useCrud("/api/admin/workflows");
  const [rooms, setRooms] = useState([]);
  const [staff, setStaff] = useState([]);
  const [open, setOpen] = useState(false);
  const [stageOpen, setStageOpen] = useState(false);
  const [wfForm, setWfForm] = useState({ code: "", name: "", department_id: "", description: "" });
  const [editWfId, setEditWfId] = useState(null);
  const [stageForm, setStageForm] = useState({ name: "", queue_code: "", room_id: "", staff_id: "", description: "" });
  const [targetWfId, setTargetWfId] = useState(null);

  useEffect(() => {
    API.get("/api/admin/rooms").then((r) => setRooms(r.data));
    API.get("/api/admin/staff").then((r) => setStaff(r.data));
  }, []);

  async function saveWf() {
    const payload = { ...wfForm, department_id: wfForm.department_id ? Number(wfForm.department_id) : null, is_active: true };
    if (editWfId) { await update(editWfId, payload); flash("Workflow updated"); }
    else { await create(payload); flash("Workflow created"); }
    setOpen(false);
  }

  async function addStage() {
    await API.post(`/api/admin/workflows/${targetWfId}/stages`, {
      ...stageForm,
      room_id: stageForm.room_id ? Number(stageForm.room_id) : null,
      staff_id: stageForm.staff_id ? Number(stageForm.staff_id) : null,
      is_active: true,
    });
    flash("Stage added");
    setStageOpen(false);
    await load();
  }

  return (
    <div>
      <div className="mb-4 flex justify-end"><Btn onClick={() => { setWfForm({ code: "", name: "", department_id: "", description: "" }); setEditWfId(null); setOpen(true); }}>Add Workflow</Btn></div>
      {loading ? <Spinner /> : (
        <div className="space-y-4">
          {items.map((wf) => (
            <div key={wf.id} className="rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between bg-slate-50 rounded-t-xl px-4 py-3">
                <div>
                  <p className="font-semibold text-slate-800">
                    <span className="text-indigo-700">{wf.code}</span> — {wf.name}
                  </p>
                  <p className="text-xs text-slate-500">{wf.department_name || "Help Desk / General"} · {wf.description || ""}</p>
                </div>
                <div className="space-x-2">
                  <Btn variant="ghost" className="text-xs" onClick={() => { setWfForm({ code: wf.code, name: wf.name, department_id: wf.department_id || "", description: wf.description || "" }); setEditWfId(wf.id); setOpen(true); }}>Edit</Btn>
                  <Btn variant="ghost" className="text-xs" onClick={() => { setTargetWfId(wf.id); setStageForm({ name: "", queue_code: "", room_id: "", staff_id: "", description: "" }); setStageOpen(true); }}>+ Stage</Btn>
                </div>
              </div>
              <div className="divide-y divide-slate-50">
                {wf.stages.map((s) => (
                  <div key={s.id} className="flex items-center justify-between px-4 py-2">
                    <div>
                      <p className="text-sm">
                        <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100 text-[11px] font-bold text-indigo-700">
                          {s.stage_order}
                        </span>
                        {s.name}
                        <span className="ml-2 font-mono text-xs text-slate-400">{s.queue_code}</span>
                      </p>
                      <p className="ml-7 text-xs text-slate-500">
                        {s.room_name || "Room TBD"} · Staff: {s.staff_name || "—"}
                      </p>
                    </div>
                    <Badge status={s.is_active ? "ACTIVE" : "CANCELLED"} />
                  </div>
                ))}
                {wf.stages.length === 0 && <p className="px-4 py-4 text-sm text-slate-400">No stages configured</p>}
              </div>
            </div>
          ))}
          {items.length === 0 && <p className="text-center text-sm text-slate-400">No workflows yet</p>}
        </div>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editWfId ? "Edit Workflow" : "New Workflow"}>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Code *</Label><input className={inputCls} value={wfForm.code} onChange={(e) => setWfForm({...wfForm, code: e.target.value})} placeholder="e.g. CSE-ADM" /></div>
            <div><Label>Name *</Label><input className={inputCls} value={wfForm.name} onChange={(e) => setWfForm({...wfForm, name: e.target.value})} /></div>
          </div>
          <div><Label>Department</Label>
            <select className={inputCls} value={wfForm.department_id} onChange={(e) => setWfForm({...wfForm, department_id: e.target.value})}>
              <option value="">General / Help Desk</option>
              {items.length > 0 && <></>}
            </select>
          </div>
          <div><Label>Description</Label><input className={inputCls} value={wfForm.description} onChange={(e) => setWfForm({...wfForm, description: e.target.value})} /></div>
          <Btn onClick={saveWf}>Save</Btn>
        </div>
      </Modal>
      <Modal open={stageOpen} onClose={() => setStageOpen(false)} title="Add Stage">
        <div className="space-y-3">
          <div><Label>Stage Name *</Label><input className={inputCls} value={stageForm.name} onChange={(e) => setStageForm({...stageForm, name: e.target.value})} placeholder="e.g. Document Verification" /></div>
          <div><Label>Queue Code *</Label><input className={inputCls} value={stageForm.queue_code} onChange={(e) => setStageForm({...stageForm, queue_code: e.target.value})} placeholder="e.g. CSE-DOC" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Room</Label>
              <select className={inputCls} value={stageForm.room_id} onChange={(e) => setStageForm({...stageForm, room_id: e.target.value})}>
                <option value="">None</option>
                {rooms.map((r) => <option key={r.id} value={r.id}>{r.code} – {r.name}</option>)}
              </select>
            </div>
            <div><Label>Assigned Staff</Label>
              <select className={inputCls} value={stageForm.staff_id} onChange={(e) => setStageForm({...stageForm, staff_id: e.target.value})}>
                <option value="">None</option>
                {staff.map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.employee_code})</option>)}
              </select>
            </div>
          </div>
          <Btn onClick={addStage}>Add Stage</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  FAQs                                                              */
/* ------------------------------------------------------------------ */
function FaqTab({ flash }) {
  const { items, loading, load, create, update, remove } = useCrud("/api/admin/faqs");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ question: "", answer: "", category: "General", keywords: "", department_id: "" });
  const [editId, setEditId] = useState(null);

  function startCreate() { setForm({ question: "", answer: "", category: "General", keywords: "", department_id: "" }); setEditId(null); setOpen(true); }
  function startEdit(f) { setForm({ question: f.question, answer: f.answer, category: f.category, keywords: f.keywords || "", department_id: f.department_id || "" }); setEditId(f.id); setOpen(true); }
  async function save() {
    const payload = { ...form, department_id: form.department_id ? Number(form.department_id) : null, is_active: true };
    if (editId) { await update(editId, payload); flash("FAQ updated"); }
    else { await create(payload); flash("FAQ created"); }
    setOpen(false);
  }

  return (
    <div>
      <div className="mb-4 flex justify-end"><Btn onClick={startCreate}>Add FAQ</Btn></div>
      {loading ? <Spinner /> : (
        <Table headers={["Question", "Category", "Keywords", "Actions"]}>
          {items.map((f) => (
            <tr key={f.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2">{f.question}</td>
              <td className="px-4 py-2 text-slate-500">{f.category}</td>
              <td className="px-4 py-2 text-xs text-slate-400">{f.keywords || "—"}</td>
              <td className="px-4 py-2 space-x-1">
                <Btn variant="ghost" className="px-2 py-1 text-xs" onClick={() => startEdit(f)}>Edit</Btn>
                <Btn variant="ghost" className="px-2 py-1 text-xs text-rose-600" onClick={async () => {
                  if (!window.confirm("Delete FAQ?")) return;
                  await remove(f.id); flash("FAQ deleted");
                }}>Delete</Btn>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={4} className="p-6 text-center text-slate-400">No FAQs yet</td></tr>}
        </Table>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit FAQ" : "New FAQ"} wide>
        <div className="space-y-3">
          <div><Label>Question *</Label><input className={inputCls} value={form.question} onChange={(e) => setForm({...form, question: e.target.value})} /></div>
          <div><Label>Answer *</Label><textarea className={inputCls} rows={3} value={form.answer} onChange={(e) => setForm({...form, answer: e.target.value})} /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Category</Label><input className={inputCls} value={form.category} onChange={(e) => setForm({...form, category: e.target.value})} /></div>
            <div><Label>Keywords</Label><input className={inputCls} value={form.keywords} onChange={(e) => setForm({...form, keywords: e.target.value})} placeholder="comma separated" /></div>
          </div>
          <Btn onClick={save}>Save</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  College Info                                                      */
/* ------------------------------------------------------------------ */
function CollegeTab({ flash }) {
  const { items, loading, load, create, update, remove } = useCrud("/api/admin/college-info");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ key: "", title: "", content: "", category: "College" });
  const [editId, setEditId] = useState(null);

  function startCreate() { setForm({ key: "", title: "", content: "", category: "College" }); setEditId(null); setOpen(true); }
  function startEdit(i) { setForm({ key: i.key, title: i.title, content: i.content, category: i.category }); setEditId(i.id); setOpen(true); }
  async function save() {
    if (editId) { await update(editId, { ...form, is_active: true }); flash("Updated"); }
    else { await create({ ...form, is_active: true }); flash("Created"); }
    setOpen(false);
  }

  return (
    <div>
      <div className="mb-4 flex justify-end"><Btn onClick={startCreate}>Add Info</Btn></div>
      {loading ? <Spinner /> : (
        <Table headers={["Key", "Title", "Category", "Content", "Actions"]}>
          {items.map((i) => (
            <tr key={i.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2 font-mono font-semibold text-indigo-700">{i.key}</td>
              <td className="px-4 py-2">{i.title}</td>
              <td className="px-4 py-2 text-slate-500">{i.category}</td>
              <td className="px-4 py-2 text-xs text-slate-500 max-w-xs truncate">{i.content}</td>
              <td className="px-4 py-2 space-x-1">
                <Btn variant="ghost" className="px-2 py-1 text-xs" onClick={() => startEdit(i)}>Edit</Btn>
                <Btn variant="ghost" className="px-2 py-1 text-xs text-rose-600" onClick={async () => {
                  if (!window.confirm("Delete?")) return;
                  await remove(i.id); flash("Deleted");
                }}>Delete</Btn>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-slate-400">No entries</td></tr>}
        </Table>
      )}
      <Modal open={open} onClose={() => setOpen(false)} title={editId ? "Edit Info" : "New Info"} wide>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Key *</Label><input className={inputCls} value={form.key} onChange={(e) => setForm({...form, key: e.target.value})} placeholder="e.g. hostel_availability" /></div>
            <div><Label>Category</Label><input className={inputCls} value={form.category} onChange={(e) => setForm({...form, category: e.target.value})} /></div>
          </div>
          <div><Label>Title *</Label><input className={inputCls} value={form.title} onChange={(e) => setForm({...form, title: e.target.value})} /></div>
          <div><Label>Content *</Label><textarea className={inputCls} rows={3} value={form.content} onChange={(e) => setForm({...form, content: e.target.value})} /></div>
          <Btn onClick={save}>Save</Btn>
        </div>
      </Modal>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Visitors (read-only + reassign)                                   */
/* ------------------------------------------------------------------ */
function VisitorsTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("");
  const [stageMap, setStageMap] = useState([]);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [v, m] = await Promise.all([
        API.get("/api/admin/visitors", { params: { q, status: filter } }),
        API.get("/api/staff/stage-map"),
      ]);
      setItems(v.data);
      setStageMap(m.data);
    } finally {
      setLoading(false);
    }
  }, [q, filter]);

  useEffect(() => { load(); }, [load]);

  async function reassignVisitor(v, targetId) {
    await API.post(`/api/admin/visitors/reassign/${v.id}`, { new_stage_id: Number(targetId) });
    setToast(`${v.visitor_code} reassigned ✓`);
    await load();
  }

  return (
    <div>
      {toast && <p className="mb-3 text-sm font-medium text-emerald-600">{toast}</p>}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          className={`${inputCls} min-w-[220px] flex-1`}
          placeholder="Search by name, code, phone…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className={inputCls} value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="COMPLETED">Completed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <Btn variant="secondary" onClick={load}><RefreshCw size={14} /> Refresh</Btn>
      </div>
      {loading ? <Spinner /> : (
        <Table headers={["ID", "Name", "Phone", "Dept", "Stage", "Queue", "Status", "Actions"]}>
          {items.map((v) => (
            <tr key={v.id} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="px-4 py-2 font-semibold text-indigo-700">{v.visitor_code}</td>
              <td className="px-4 py-2">{v.full_name}</td>
              <td className="px-4 py-2 text-slate-500">{v.phone}</td>
              <td className="px-4 py-2 text-slate-500">{v.department_name || "Help Desk"}</td>
              <td className="px-4 py-2">{v.current_stage_name || "—"}</td>
              <td className="px-4 py-2 font-mono text-xs">{v.current_queue_entry?.token_display || "—"}</td>
              <td className="px-4 py-2"><Badge status={v.current_queue_entry?.status || v.status} /></td>
              <td className="px-4 py-2">
                <select
                  className="rounded border border-slate-300 px-1.5 py-1 text-xs"
                  onChange={(e) => {
                    if (e.target.value) reassignVisitor(v, e.target.value);
                    e.target.value = "";
                  }}
                  defaultValue=""
                >
                  <option value="">Reassign…</option>
                  {stageMap.map((s) => (
                    <option key={s.id} value={s.id}>[{s.workflow_name}] {s.name}</option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
          {items.length === 0 && <tr><td colSpan={8} className="p-6 text-center text-slate-400">No visitors found</td></tr>}
        </Table>
      )}
    </div>
  );
}