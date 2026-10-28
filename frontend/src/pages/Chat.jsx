import React, { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, RefreshCw, Send, Users, Zap } from "lucide-react";
import { API } from "../lib/api.js";
import { Badge, Spinner } from "../components/ui.jsx";

const DEMO_PHONE = [
  { label: "Raj Kumar (ECE)", phone: "9876543210" },
  { label: "Sundar Kumar (Help Desk)", phone: "9876500000" },
];

const QUICK_Q = [
  "What documents are required for ECE admission?",
  "How many people are before me?",
  "What should I do next?",
  "Where is the admission office?",
  "Is hostel available?",
];

export default function Chat() {
  const [phone, setPhone] = useState(
    new URLSearchParams(window.location.search).get("phone") || ""
  );
  const [visitor, setVisitor] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);
  const [whatsappLink, setWhatsappLink] = useState("");

  useEffect(() => {
    API.get("/api/whatsapp/status")
      .then((r) => setWhatsappLink(r.data.chat_link || ""))
      .catch(() => {});
  }, []);

  const load = useCallback(
    async (silent) => {
      if (!phone) return;
      try {
        const r = await API.get("/api/chat/session", { params: { phone } });
        setVisitor(r.data.visitor);
        setMessages(r.data.messages || []);
      } catch {
        if (!silent) {
          setVisitor(null);
          setMessages([]);
        }
      }
    },
    [phone]
  );

  useEffect(() => {
    load(false);
    const t = setInterval(() => load(true), 4000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  async function send(text) {
    const q = text || draft.trim();
    if (!q || !phone) return;
    setDraft("");
    setMessages((m) => [...m, { id: Date.now(), sender: "USER", message: q }]);
    setBusy(true);
    try {
      const r = await API.post("/api/chat/send", { phone, message: q });
      if (r.data.visitor) setVisitor(r.data.visitor);
      setMessages((m) => [
        ...m,
        { id: r.data.id || Date.now() + 1, sender: r.data.sender, message: r.data.message },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, sender: "AI", message: "Sorry, there was an error. Please try again." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function pickPhone(p) {
    setPhone(p);
    setVisitor(null);
    setMessages([]);
    const url = new URL(window.location.href);
    url.searchParams.set("phone", p);
    window.history.replaceState({}, "", url.toString());
  }

  return (
    <div className="flex h-full min-h-screen flex-col bg-slate-100">
      {/* Top bar */}
      <header className="border-b border-slate-200 bg-indigo-600 text-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-500 p-1.5">
              <MessageCircle size={18} />
            </div>
            <div>
              <p className="text-sm font-bold">Nandha Engineering College Admission Assistance</p>
              <p className="text-[11px] text-indigo-200">AI-powered visitor chat</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {whatsappLink && (
              <a
                href={whatsappLink}
                target="_blank"
                rel="noreferrer"
                className="rounded-lg bg-emerald-500 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-emerald-600"
              >
                Chat on WhatsApp
              </a>
            )}
            <a
              href="/login"
              className="rounded-lg border border-indigo-400 px-2.5 py-1 text-[11px] text-indigo-100 hover:bg-indigo-500"
            >
              Staff Login
            </a>
          </div>
        </div>
      </header>

      {/* Phone picker */}
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-3xl px-4 py-3">
          <p className="mb-2 text-xs font-medium text-slate-500">
            <Users size={12} className="mr-1 inline" /> Enter your mobile number to start (or
            pick a demo):
          </p>
          <div className="flex flex-wrap gap-2">
            {DEMO_PHONE.map((d) => (
              <button
                key={d.phone}
                onClick={() => pickPhone(d.phone)}
                className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
                  phone === d.phone
                    ? "border-indigo-400 bg-indigo-50 text-indigo-700"
                    : "border-slate-200 text-slate-600 hover:bg-slate-50"
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input
              className="w-full max-w-xs rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
              placeholder="Enter phone number…"
              value={phone}
              onChange={(e) => pickPhone(e.target.value)}
            />
            <button
              onClick={() => load(false)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Visitor tracker */}
      {visitor && <Tracker v={visitor} />}

      {/* Chat area */}
      <div className="flex-1 overflow-auto chat-scroll">
        <div className="mx-auto max-w-3xl space-y-3 px-4 py-4">
          {messages.length === 0 && phone && !visitor && (
            <p className="text-center text-sm text-slate-400">
              Loading your messages…
            </p>
          )}
          {messages.length === 0 && !phone && (
            <div className="mt-20 text-center text-slate-400">
              <MessageCircle size={48} className="mx-auto mb-3 text-slate-300" />
              <p className="text-base font-medium text-slate-500">
                Welcome to Nandha Engineering College Admission Assistance
              </p>
              <p className="text-sm">
                Enter your phone number above or pick a demo account to get started.
              </p>
            </div>
          )}
          {messages.map((m) => (
            <Bubble key={m.id} m={m} />
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Quick suggestions */}
      {phone && (
        <div className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-3xl overflow-x-auto px-4 py-2">
            <div className="flex gap-2">
              {QUICK_Q.map((q) => (
                <button
                  key={q}
                  onClick={() => send(q)}
                  className="whitespace-nowrap rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-600 hover:border-indigo-400 hover:bg-indigo-50"
                >
                  <Zap size={11} className="mr-1 inline text-indigo-500" />
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t border-slate-200 bg-white">
        <form
          className="mx-auto flex max-w-3xl gap-2 px-4 py-3"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <input
            className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            placeholder={phone ? "Type your question…" : "Enter your phone number first"}
            disabled={!phone}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
          <button
            disabled={!phone || busy}
            className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {busy ? (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            ) : (
              <Send size={16} />
            )}
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

function Bubble({ m }) {
  if (m.sender === "USER") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-sm text-white shadow-sm">
          {m.message}
        </div>
      </div>
    );
  }
  const isSystem = m.sender === "SYSTEM";
  return (
    <div className="flex justify-start">
      <div
        className={`max-w-[85%] rounded-2xl rounded-bl-md px-4 py-2.5 text-sm shadow-sm ${
          isSystem
            ? "border border-amber-200 bg-amber-50 text-amber-800"
            : "bg-white text-slate-800 border border-slate-200"
        }`}
      >
        {isSystem && (
          <p className="mb-1 text-[11px] font-semibold uppercase text-amber-500">
            Notification
          </p>
        )}
        <p className="whitespace-pre-wrap">{m.message}</p>
      </div>
    </div>
  );
}

function Tracker({ v }) {
  return (
    <div className="border-b border-slate-200 bg-white">
      <div className="mx-auto max-w-3xl px-4 py-3">
        <div className="flex flex-wrap items-start gap-4">
          <div className="flex items-center gap-2">
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">
              {v.visitor_code}
            </span>
            <div>
              <p className="text-sm font-semibold text-slate-800">{v.full_name}</p>
              <p className="text-[11px] text-slate-500">{v.purpose}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-3">
            <TrackerItem label="Stage" value={v.current_stage_name || "Done"} />
            <TrackerItem
              label="Queue"
              value={v.current_queue_entry?.token_display || "—"}
              accent="text-indigo-700"
            />
            <TrackerItem
              label="Status"
              value={<Badge status={v.current_queue_entry?.status || v.status} />}
            />
            <TrackerItem
              label="People Ahead"
              value={v.current_queue_entry?.position != null ? v.current_queue_entry.position : "—"}
            />
            <TrackerItem label="Room" value={v.room_name || "—"} />
            <TrackerItem label="Staff" value={v.assigned_staff_name || "—"} />
            {v.next_stage_name && (
              <TrackerItem
                label="Next"
                value={v.next_stage_name}
                accent="text-emerald-700"
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TrackerItem({ label, value, accent }) {
  return (
    <div className="rounded-lg bg-slate-50 px-2.5 py-1.5">
      <p className="text-[10px] font-medium uppercase text-slate-400">{label}</p>
      <p className={`text-xs font-semibold ${accent || "text-slate-800"}`}>{value}</p>
    </div>
  );
}