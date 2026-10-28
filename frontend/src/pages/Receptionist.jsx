import React, { useCallback, useEffect, useState } from "react";
import {
  ClipboardList, Eye, LayoutList, MessageCircle, QrCode, RefreshCw, Search, Send, UserPlus,
  Users,
} from "lucide-react";
import Layout from "../components/Layout.jsx";
import { API } from "../lib/api.js";
import { Badge, Btn, inputCls, Label, Modal, Spinner } from "../components/ui.jsx";

const PURPOSES = ["Admission", "Enquiry", "Help Desk", "Other"];

export default function Receptionist() {
  const [tab, setTab] = useState("register");
  const [departments, setDepartments] = useState([]);
  const [queues, setQueues] = useState([]);
  const [stageMap, setStageMap] = useState([]);
  const [visitors, setVisitors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deskQr, setDeskQr] = useState(false);
  const [telegramQr, setTelegramQr] = useState(false);
  const [whatsappQr, setWhatsappQr] = useState(false);

  const loadLookups = useCallback(() => {
    API.get("/api/reception/departments").then((r) => setDepartments(r.data));
    API.get("/api/reception/stage-map").then((r) => setStageMap(r.data));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [q, v] = await Promise.all([
        API.get("/api/reception/queues"),
        API.get("/api/reception/visitors/active"),
      ]);
      setQueues(q.data);
      setVisitors(v.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadLookups();
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, [load, loadLookups]);

  return (
    <Layout title="Reception Desk">
      <div className="mb-5 flex flex-wrap gap-2">
        <TabBtn active={tab === "register"} onClick={() => setTab("register")} icon={UserPlus}>
          Register Visitor
        </TabBtn>
        <TabBtn active={tab === "visitors"} onClick={() => setTab("visitors")} icon={Users}>
          Active Visitors
        </TabBtn>
        <TabBtn active={tab === "queues"} onClick={() => setTab("queues")} icon={LayoutList}>
          All Queues
        </TabBtn>
        <button
          onClick={() => setDeskQr(true)}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-100"
        >
          <QrCode size={14} /> Desk Chat QR
        </button>
        <button
          onClick={() => setWhatsappQr(true)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700 hover:bg-emerald-100"
        >
          <MessageCircle size={14} /> WhatsApp
        </button>
        <button
          onClick={() => setTelegramQr(true)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-sky-300 bg-sky-50 px-3 py-1.5 text-sm font-medium text-sky-700 hover:bg-sky-100"
        >
          <Send size={14} /> Telegram Bot
        </button>
        <button
          onClick={load}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {tab === "register" && (
        <RegisterForm
          departments={departments}
          onDone={(v) => {
            load();
            setTab("visitors");
          }}
        />
      )}

      {tab === "visitors" && (
        <VisitorsTab visitors={visitors} stageMap={stageMap} onChanged={load} />
      )}

      {tab === "queues" && (
        <QueuesTab queues={queues} stageMap={stageMap} onChanged={load} />
      )}

      {deskQr && <DeskQrModal onClose={() => setDeskQr(false)} />}
      {whatsappQr && <WhatsAppModal onClose={() => setWhatsappQr(false)} />}
      {telegramQr && <TelegramModal onClose={() => setTelegramQr(false)} />}
    </Layout>
  );
}

function TabBtn({ active, onClick, icon: Icon, children }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
        active
          ? "bg-indigo-600 text-white"
          : "border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
      }`}
    >
      <Icon size={15} /> {children}
    </button>
  );
}

/* ---------------- Register form ---------------- */
function RegisterForm({ departments, onDone }) {
  const [form, setForm] = useState({
    full_name: "",
    phone: "",
    purpose: "Admission",
    department_id: "",
    remarks: "",
    needs_help_desk: false,
  });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function set(k, v) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const payload = {
        ...form,
        department_id: form.department_id ? Number(form.department_id) : null,
        needs_help_desk:
          form.needs_help_desk ||
          !form.department_id ||
          form.purpose === "Help Desk",
      };
      const r = await API.post("/api/reception/visitors", payload);
      setResult(r.data);
      onDone(r.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <div className="max-w-2xl rounded-xl border border-emerald-200 bg-emerald-50 p-6">
        <h3 className="text-lg font-bold text-emerald-800">
          Visitor Registered Successfully
        </h3>
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <Info label="Visitor ID" value={result.visitor_code} big />
          <Info label="Name" value={result.full_name} />
          <Info label="Department" value={result.department_name || "Help Desk / Open"} />
          <Info label="Current Stage" value={result.current_stage_name} />
          <Info label="Queue Number" value={result.current_queue_entry?.token_display} />
          <Info label="Status" value={result.current_queue_entry?.status} />
          <Info label="Room" value={`${result.room_name} (${result.room_code})`} />
          <Info label="Assigned Staff" value={result.assigned_staff_name || "-"} />
        </div>
        <p className="mt-4 text-sm text-emerald-700">{result.welcome_message}</p>
        <QrPanel visitorId={result.id} />
        <div className="mt-5 flex gap-3">
          <a
            href={`/chat?phone=${encodeURIComponent(result.phone)}`}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
          >
            Open this visitor's chat
          </a>
          <Btn variant="secondary" onClick={() => setResult(null)}>
            Register another visitor
          </Btn>
        </div>
      </div>
    );
  }

  return (
    <form
      onSubmit={submit}
      className="max-w-2xl rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <h2 className="mb-4 text-base font-semibold text-slate-800">New Visitor</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <Label>Full Name *</Label>
          <input
            className={inputCls}
            required
            value={form.full_name}
            onChange={(e) => set("full_name", e.target.value)}
            placeholder="e.g. Raj Kumar"
          />
        </div>
        <div>
          <Label>Mobile / WhatsApp Number *</Label>
          <input
            className={inputCls}
            required
            value={form.phone}
            onChange={(e) => set("phone", e.target.value)}
            placeholder="e.g. 9876543210"
          />
        </div>
        <div>
          <Label>Purpose of Visit</Label>
          <select
            className={inputCls}
            value={form.purpose}
            onChange={(e) => set("purpose", e.target.value)}
          >
            {PURPOSES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <Label>Department</Label>
          <select
            className={inputCls}
            value={form.department_id}
            onChange={(e) => set("department_id", e.target.value)}
          >
            <option value="">Not sure / Needs Counselling</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} – {d.name}
              </option>
            ))}
          </select>
        </div>
        <div className="sm:col-span-2">
          <Label>Remarks (optional)</Label>
          <textarea
            className={inputCls}
            rows={2}
            value={form.remarks}
            onChange={(e) => set("remarks", e.target.value)}
            placeholder="Any note for the staff…"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
          <input
            type="checkbox"
            checked={form.needs_help_desk}
            onChange={(e) => set("needs_help_desk", e.target.checked)}
          />
          Visitor needs Counselling / Help Desk guidance
        </label>
      </div>
      {error && (
        <p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>
      )}
      <div className="mt-5">
        <Btn className="w-full sm:w-auto" disabled={busy}>
          {busy ? "Registering…" : "Register Visitor"}
        </Btn>
      </div>
      {(!form.department_id || form.purpose === "Help Desk") && (
        <p className="mt-3 text-xs text-slate-500">
          This visitor will be routed to the Counselling / Help Desk workflow
          instead of a department.
        </p>
      )}
    </form>
  );
}

function Info({ label, value, big }) {
  return (
    <div className="rounded-lg bg-white px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className={`font-semibold text-slate-800 ${big ? "text-xl text-emerald-700" : ""}`}>
        {value || "-"}
      </p>
    </div>
  );
}

/* ---------------- QR code ---------------- */
function QrPanel({ visitorId }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!visitorId) return;
    API.get(`/api/reception/visitors/${visitorId}/qr`)
      .then((r) => setData(r.data))
      .catch(() => {});
  }, [visitorId]);
  if (!data) return null;
  return (
    <div className="mt-5 flex flex-col items-center gap-4 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row">
      <img src={data.qr} alt={`QR for ${data.visitor_code}`} className="h-40 w-40" />
      <div className="text-sm text-slate-600">
        <p className="flex items-center gap-2 font-semibold text-slate-800">
          <QrCode size={16} /> Scan to open the visitor chat
        </p>
        <p className="mt-1 text-xs">
          Ask the visitor to scan this with their phone camera to open the AI
          assistant and live queue tracker.
        </p>
        <p className="mt-2 break-all text-xs text-indigo-600">{data.chat_url}</p>
      </div>
    </div>
  );
}

function QrModal({ visitor, onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    API.get(`/api/reception/visitors/${visitor.id}/qr`)
      .then((r) => setData(r.data))
      .catch(() => {});
  }, [visitor.id]);
  return (
    <Modal open onClose={onClose} title={`Chat QR – ${visitor.visitor_code}`}>
      <div className="flex flex-col items-center gap-3">
        {data ? (
          <img src={data.qr} alt={`QR for ${visitor.visitor_code}`} className="h-56 w-56" />
        ) : (
          <Spinner />
        )}
        <p className="text-sm font-semibold text-slate-800">
          {visitor.full_name} · {visitor.phone}
        </p>
        {data && (
          <p className="break-all text-center text-xs text-indigo-600">{data.chat_url}</p>
        )}
        <p className="text-center text-xs text-slate-500">
          Ask the visitor to scan this with their phone camera to open the AI
          chat and live queue tracker (same Wi-Fi required).
        </p>
      </div>
    </Modal>
  );
}

function DeskQrModal({ onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    API.get("/api/reception/chat-qr")
      .then((r) => setData(r.data))
      .catch(() => {});
  }, []);
  return (
    <Modal open onClose={onClose} title="Reception Chat QR">
      <div className="flex flex-col items-center gap-3">
        {data ? (
          <img src={data.qr} alt="Reception chat QR" className="h-56 w-56" />
        ) : (
          <Spinner />
        )}
        {data && (
          <p className="break-all text-center text-xs text-indigo-600">{data.chat_url}</p>
        )}
        <p className="text-center text-xs text-slate-500">
          Walk-in visitors can scan this to open the Nandha AI admission
          assistant. For an individual visitor, use the QR button on their row.
        </p>
      </div>
    </Modal>
  );
}

function WhatsAppModal({ onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    API.get("/api/whatsapp/status")
      .then((r) => setData(r.data))
      .catch(() => setData({}));
  }, []);
  return (
    <Modal open onClose={onClose} title="WhatsApp Admission Assistant">
      <div className="flex flex-col items-center gap-3">
        {data?.qr ? (
          <img src={data.qr} alt="WhatsApp chat QR" className="h-56 w-56" />
        ) : (
          <p className="py-10 text-center text-sm text-slate-500">
            {!data
              ? "Checking WhatsApp…"
              : data.enabled
              ? "WhatsApp is connected. Set WHATSAPP_BUSINESS_NUMBER to show a QR here."
              : "WhatsApp is not configured yet. Visitors can use the Telegram bot or the web chat meanwhile."}
          </p>
        )}
        {data?.chat_link && (
          <a
            href={data.chat_link}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-emerald-700 hover:underline"
          >
            {data.chat_link}
          </a>
        )}
        <p className="text-center text-xs text-slate-500">
          WhatsApp is the main channel. Visitors who message from the number
          they registered with are recognised automatically: they get the same
          AI assistant, their live queue status (type "status") and stage
          updates.
        </p>
      </div>
    </Modal>
  );
}

function TelegramModal({ onClose }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    API.get("/api/telegram/status")
      .then((r) => setData(r.data))
      .catch(() => {});
  }, []);
  return (
    <Modal open onClose={onClose} title="Telegram Admission Bot">
      <div className="flex flex-col items-center gap-3">
        {data?.qr ? (
          <img src={data.qr} alt="Telegram bot QR" className="h-56 w-56" />
        ) : (
          <p className="py-10 text-center text-sm text-slate-500">
            {!data
              ? "Checking Telegram bot…"
              : data.enabled
              ? "Bot is configured but not reachable right now."
              : "Telegram bot is not configured."}
          </p>
        )}
        {data?.bot_url && (
          <a
            href={data.bot_url}
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-indigo-600 hover:underline"
          >
            {data.bot_url}
          </a>
        )}
        <p className="text-center text-xs text-slate-500">
          Alternative to WhatsApp: visitors can chat with the same AI
          assistant on Telegram and see
          their live queue status. They just send the mobile number they
          registered at the reception.
        </p>
      </div>
    </Modal>
  );
}

/* ---------------- Visitors tab ---------------- */
function VisitorsTab({ visitors, stageMap, onChanged }) {
  const [q, setQ] = useState("");
  const [detail, setDetail] = useState(null);
  const [qrVisitor, setQrVisitor] = useState(null);

  const filtered = visitors.filter(
    (v) =>
      !q ||
      v.full_name.toLowerCase().includes(q.toLowerCase()) ||
      v.visitor_code.toLowerCase().includes(q.toLowerCase()) ||
      v.phone.includes(q)
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-100 p-4">
        <div className="relative min-w-[240px] flex-1">
          <Search size={15} className="absolute left-3 top-2.5 text-slate-400" />
          <input
            className={`${inputCls} pl-9`}
            placeholder="Search by name, visitor ID or phone…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <span className="text-sm text-slate-500">{filtered.length} visitors</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-400">
              <th className="px-4 py-2">ID</th>
              <th className="px-4 py-2">Name</th>
              <th className="px-4 py-2">Phone</th>
              <th className="px-4 py-2">Department</th>
              <th className="px-4 py-2">Stage</th>
              <th className="px-4 py-2">Queue</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((v) => (
              <tr key={v.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="px-4 py-2 font-semibold text-indigo-700">{v.visitor_code}</td>
                <td className="px-4 py-2">{v.full_name}</td>
                <td className="px-4 py-2">{v.phone}</td>
                <td className="px-4 py-2">{v.department_name || "Help Desk"}</td>
                <td className="px-4 py-2">{v.current_stage_name || "—"}</td>
                <td className="px-4 py-2 font-mono text-xs">
                  {v.current_queue_entry?.token_display || "—"}
                </td>
                <td className="px-4 py-2">
                  <Badge status={v.current_queue_entry?.status || v.status} />
                </td>
                <td className="px-4 py-2">
                  <div className="flex gap-1">
                    <Btn variant="ghost" onClick={() => setQrVisitor(v)}>
                      <QrCode size={15} /> QR
                    </Btn>
                    <Btn variant="ghost" onClick={() => setDetail(v)}>
                      <Eye size={15} /> Details
                    </Btn>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={8} className="p-8 text-center text-slate-400">
                  No visitors found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {detail && <VisitorDetail visitor={detail} stageMap={stageMap} onClose={() => setDetail(null)} onChanged={onChanged} />}
      {qrVisitor && <QrModal visitor={qrVisitor} onClose={() => setQrVisitor(null)} />}
    </div>
  );
}

function VisitorDetail({ visitor, stageMap, onClose, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");

  async function reassign(targetId) {
    if (!window.confirm(`Move ${visitor.visitor_code} to the selected stage?`)) return;
    setBusy(true);
    try {
      const entryId = visitor.current_queue_entry?.id;
      if (!entryId) return alert("Visitor has no active queue entry");
      await API.post(`/api/staff/entries/${entryId}/reassign`, {
        new_stage_id: Number(targetId),
        reason: "Reassigned from reception",
      });
      setToast("Visitor reassigned");
      onChanged();
      setTimeout(() => onClose(), 600);
    } catch (err) {
      alert(err.response?.data?.detail || "Reassign failed");
    } finally {
      setBusy(false);
    }
  }

  async function cancelV() {
    if (!window.confirm(`Cancel ${visitor.visitor_code}?`)) return;
    await API.delete(`/api/reception/visitors/${visitor.id}`);
    setToast("Visitor cancelled");
    onChanged();
    setTimeout(() => onClose(), 600);
  }

  return (
    <Modal open onClose={onClose} title={`Visitor ${visitor.visitor_code}`}>
      <div className="grid gap-2 sm:grid-cols-2">
        <Info label="Name" value={visitor.full_name} />
        <Info label="Phone" value={visitor.phone} />
        <Info label="Department" value={visitor.department_name || "Help Desk"} />
        <Info label="Purpose" value={visitor.purpose} />
        <Info label="Current Stage" value={visitor.current_stage_name} />
        <Info label="Next Stage" value={visitor.next_stage_name} />
        <Info label="Queue" value={visitor.current_queue_entry?.token_display} />
        <Info label="Room" value={visitor.room_name} />
        <Info label="Assigned Staff" value={visitor.assigned_staff_name} />
        <Info label="Status" value={visitor.current_queue_entry?.status || visitor.status} />
      </div>
      {visitor.remarks && (
        <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Remarks: {visitor.remarks}
        </p>
      )}
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <Label>Reassign to stage</Label>
          <div className="flex gap-2">
            <select id="reassign-target" className={inputCls}>
              <option value="">Select stage…</option>
              {stageMap.map((s) => (
                <option key={s.id} value={s.id}>
                  [{s.workflow_name}] {s.name} ({s.queue_code})
                </option>
              ))}
            </select>
            <Btn
              variant="secondary"
              disabled={busy}
              onClick={() => {
                const sel = document.getElementById("reassign-target").value;
                if (sel) reassign(sel);
                else alert("Choose a target stage");
              }}
            >
              Reassign
            </Btn>
          </div>
        </div>
        <div className="flex items-end gap-2">
          <Btn variant="danger" onClick={cancelV} disabled={busy}>
            Cancel visitor
          </Btn>
        </div>
      </div>
      {toast && <p className="mt-3 text-sm font-medium text-emerald-600">{toast}</p>}
    </Modal>
  );
}

/* ---------------- Queues tab ---------------- */
function QueuesTab({ queues, stageMap, onChanged }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {queues.map((que) => (
        <div key={que.queue_id} className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between rounded-t-xl bg-slate-50 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-800">
                <ClipboardList size={14} className="mr-1 inline text-slate-400" />
                {que.stage_name}
              </p>
              <p className="text-xs text-slate-500">{que.queue_name}</p>
            </div>
            <div className="text-right text-xs text-slate-500">
              <p>
                Waiting:{" "}
                <span className="font-semibold text-amber-600">{que.waiting}</span>
              </p>
              <p>
                Serving:{" "}
                <span className="font-semibold text-emerald-600">
                  {que.serving_token || "—"}
                </span>
              </p>
            </div>
          </div>
          <div className="divide-y divide-slate-50">
            {(que.entries || []).slice(0, 8).map((e) => (
              <div key={e.id} className="flex items-center justify-between px-4 py-2 text-sm">
                <div>
                  <span className="font-mono font-semibold text-indigo-700">
                    {e.token_display}
                  </span>{" "}
                  <span className="text-slate-600">{e.visitor_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-400">{e.visitor_code}</span>
                  <Badge status={e.status} />
                </div>
              </div>
            ))}
            {(que.entries || []).length === 0 && (
              <p className="p-4 text-center text-sm text-slate-400">Queue is empty</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}