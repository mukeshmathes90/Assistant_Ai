import React, { useCallback, useEffect, useState } from "react";
import { Bell, ClipboardList, Eye, PhoneCall, RefreshCw } from "lucide-react";
import Layout from "../components/Layout.jsx";
import { API } from "../lib/api.js";
import { Badge, Btn, inputCls, Label, Modal, Spinner } from "../components/ui.jsx";

export default function Staff() {
  const [queues, setQueues] = useState([]);
  const [stageMap, setStageMap] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");

  const load = useCallback(async () => {
    try {
      const [q, m] = await Promise.all([
        API.get("/api/staff/queues"),
        API.get("/api/staff/stage-map"),
      ]);
      setQueues(q.data);
      setStageMap(m.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  function flash(msg) {
    setToast(msg);
    setTimeout(() => setToast(""), 4000);
  }

  async function act(fn, doneMsg) {
    try {
      await fn();
      await load();
      flash(doneMsg);
    } catch (err) {
      alert(err.response?.data?.detail || "Action failed");
    }
  }

  return (
    <Layout title="Staff Queue Console">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Live queue console · auto-refreshes every 5 seconds
        </p>
        <button
          onClick={load}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {toast && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
          <Bell size={15} /> {toast}
        </div>
      )}

      {loading ? (
        <Spinner />
      ) : queues.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
          No queues assigned to your account yet.
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          {queues.map((q) => (
            <QueueCard
              key={q.queue_id}
              q={q}
              stageMap={stageMap}
              act={act}
              onDetail={setDetail}
            />
          ))}
        </div>
      )}

      {detail && <DetailModal entry={detail} onClose={() => setDetail(null)} />}
    </Layout>
  );
}

function QueueCard({ q, stageMap, act, onDetail }) {
  const serving = q.serving;
  const hasActive = q.entries.some((e) => e.status === "CALLED" || e.status === "SERVING");

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
        <div>
          <p className="text-sm font-semibold text-slate-800">{q.stage_name}</p>
          <p className="text-xs text-slate-500">
            {q.workflow_name} · {q.room_name || q.room_code || "Room TBD"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs text-slate-500">Waiting</p>
          <p className="text-xl font-bold text-amber-600">{q.waiting_count}</p>
        </div>
      </div>

      <div className="border-b border-slate-100 px-4 py-3">
        <button
          onClick={() =>
            act(() => API.post(`/api/staff/queues/${q.queue_id}/call-next`), "Next visitor called ✓")
          }
          disabled={hasActive || q.waiting_count === 0}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-40"
        >
          <PhoneCall size={15} /> Call Next
        </button>
      </div>

      <div className="divide-y divide-slate-50">
        {(q.entries || []).length === 0 && (
          <p className="p-5 text-center text-sm text-slate-400">No entries in this queue</p>
        )}
        {(q.entries || []).map((e) => (
          <Row
            key={e.id}
            e={e}
            q={q}
            stageMap={stageMap}
            act={act}
            onDetail={onDetail}
            isServing={e.status === "CALLED" || e.status === "SERVING"}
          />
        ))}
      </div>
    </div>
  );
}

function Row({ e, q, stageMap, act, onDetail, isServing }) {
  const [reassignId, setReassignId] = useState("");
  return (
    <div className={`px-4 py-2.5 ${isServing ? "bg-emerald-50/60" : ""}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm">
            <span className="font-mono font-semibold text-indigo-700">{e.token_display}</span>{" "}
            <span className="font-medium text-slate-700">{e.visitor_name}</span>{" "}
            <span className="text-xs text-slate-400">({e.visitor_code})</span>
          </p>
          <p className="text-xs text-slate-500">
            {e.room_name || "Room TBD"} · {e.phone}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge status={e.status} />
          <Btn variant="ghost" onClick={() => onDetail(e)} title="View details">
            <Eye size={15} />
          </Btn>
        </div>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        {isServing && (
          <Btn
            variant="success"
            className="px-2.5 py-1 text-xs"
            onClick={() =>
              act(() => API.post(`/api/staff/entries/${e.id}/complete`), `${e.visitor_code} completed → next stage ✓`)
            }
          >
            Complete Stage
          </Btn>
        )}
        {isServing && (
          <Btn
            variant="secondary"
            className="px-2.5 py-1 text-xs"
            onClick={() => {
              const reason = window.prompt("Reason for hold (optional)", "Waiting for document");
              act(() => API.post(`/api/staff/entries/${e.id}/hold`, { reason: reason || "" }), "Held ✓");
            }}
          >
            Hold
          </Btn>
        )}
        {isServing && (
          <Btn
            variant="secondary"
            className="px-2.5 py-1 text-xs"
            onClick={() => {
              if (!window.confirm(`Skip ${e.visitor_code}?`)) return;
              act(() => API.post(`/api/staff/entries/${e.id}/skip`, { reason: "Skipped" }), "Skipped ✓");
            }}
          >
            Skip
          </Btn>
        )}
        <div className="ml-1 flex items-center gap-1.5">
          <select
            className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
            value={reassignId}
            onChange={(ev) => setReassignId(ev.target.value)}
          >
            <option value="">Reassign to…</option>
            {stageMap
              .filter((s) => s.id !== q.stage_id)
              .map((s) => (
                <option key={s.id} value={s.id}>
                  [{s.workflow_name}] {s.name}
                </option>
              ))}
          </select>
          <Btn
            variant="secondary"
            className="px-2.5 py-1 text-xs"
            disabled={!reassignId}
            onClick={() =>
              act(
                () =>
                  API.post(`/api/staff/entries/${e.id}/reassign`, {
                    new_stage_id: Number(reassignId),
                    reason: "Reassigned by staff",
                  }),
                `${e.visitor_code} reassigned ✓`
              )
            }
          >
            Go
          </Btn>
        </div>
      </div>
    </div>
  );
}

function DetailModal({ entry, onClose }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    API.get(`/api/staff/visitors/${entry.visitor_id}`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.detail || "Failed to load"));
  }, [entry.visitor_id]);

  return (
    <Modal open onClose={onClose} title={`Visitor ${entry.visitor_code} — details`}>
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {!data && !error && <Spinner />}
      {data && (
        <div>
          <div className="grid gap-2 sm:grid-cols-2">
            <Info label="Name" value={data.visitor.full_name} />
            <Info label="Phone" value={data.visitor.phone} />
            <Info label="Department" value={data.visitor.department_name || "Help Desk"} />
            <Info label="Purpose" value={data.visitor.purpose} />
            <Info label="Current Stage" value={data.visitor.current_stage_name} />
            <Info label="Queue" value={data.visitor.current_queue_entry?.token_display} />
            <Info label="Previous Stage" value={data.previous_stage} />
            <Info label="Next Stage" value={data.next_stage} />
            <Info label="Room" value={`${data.visitor.room_name || ""} ${data.visitor.room_code || ""}`} />
            <Info label="Assigned Staff" value={data.visitor.assigned_staff_name} />
          </div>
          <p className="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Stage History
          </p>
          <ul className="mt-1 divide-y divide-slate-100 rounded-lg border border-slate-100">
            {(data.history || []).map((h, i) => (
              <li key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                <span className="text-slate-700">{h.stage}</span>
                <Badge status={h.status} />
              </li>
            ))}
            {!data.history?.length && (
              <li className="px-3 py-2 text-sm text-slate-400">No history yet</li>
            )}
          </ul>
        </div>
      )}
    </Modal>
  );
}

function Info({ label, value }) {
  return (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="font-semibold text-slate-800">{value || "-"}</p>
    </div>
  );
}