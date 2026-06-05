import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { useStaffFetch } from "@/lib/api";
import { ToastStack, type ToastItem } from "@/components/ToastStack";
import { MessageSquare } from "lucide-react";

const DEPARTMENTS = [
  { id: "co_van", name: "Cố vấn học tập" },
  { id: "ct_sv", name: "Phòng Công tác Chính trị Sinh viên" },
  { id: "dao_tao", name: "Phòng Đào tạo" },
  { id: "tai_chinh", name: "Phòng Tài chính - Kế toán" },
  { id: "tam_ly", name: "Phòng Tham vấn tâm lý" },
];

const THREADS_POLL_MS = 2000;
const MESSAGES_POLL_MS = 1200;

type Thread = {
  id: string;
  studentUid: string;
  studentEmail: string | null;
  studentName?: string | null;
  departmentId: string;
  departmentTitle: string;
  preview: string;
  lastMessageAt: string | null;
  status: string;
  unreadForStaff?: number;
};

type Msg = {
  id: string;
  text: string;
  senderRole: string;
  senderName: string | null;
  createdAt: string | null;
};

function threadListKey(items: Thread[]) {
  return items
    .map(
      (t) =>
        `${t.id}:${t.preview}:${t.lastMessageAt}:${t.unreadForStaff ?? 0}`,
    )
    .join("|");
}

function messageListKey(items: Msg[]) {
  return items.map((m) => `${m.id}:${m.text}`).join("|");
}

function formatFetchError(e: unknown): string {
  const msg = String(e instanceof Error ? e.message : e);
  if (msg.includes("Failed to fetch")) {
    return "Không kết nối được máy chủ. Kiểm tra docker compose (staff-console :3000) và đăng nhập lại.";
  }
  return msg;
}

function Badge({ n }: { n: number }) {
  if (!n || n <= 0) return null;
  return (
    <span className="ml-auto inline-flex min-w-[1.25rem] shrink-0 items-center justify-center rounded-full bg-rose-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
      {n > 99 ? "99+" : n}
    </span>
  );
}

export function DepartmentChatPage() {
  const fetchApi = useStaffFetch();
  const { staffProfile } = useStaffAuth();
  const [threads, setThreads] = useState<Thread[]>([]);
  const [selectedDept, setSelectedDept] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [reply, setReply] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const activeIdRef = useRef<string | null>(null);
  const selectedDeptRef = useRef<string | null>(null);
  const prevUnreadRef = useRef<Record<string, number>>({});
  const threadsKeyRef = useRef("");
  const messagesKeyRef = useRef("");
  const deptInitRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  activeIdRef.current = activeId;
  selectedDeptRef.current = selectedDept;

  const isCrossDept =
    staffProfile?.isSuper ||
    staffProfile?.role === "super_admin" ||
    staffProfile?.departmentId === "all";

  const visibleDepts = useMemo(() => {
    if (isCrossDept) return DEPARTMENTS;
    const id = staffProfile?.departmentId;
    return DEPARTMENTS.filter((d) => d.id === id);
  }, [isCrossDept, staffProfile?.departmentId]);

  useEffect(() => {
    if (!deptInitRef.current && visibleDepts.length > 0) {
      deptInitRef.current = true;
      setSelectedDept(visibleDepts[0].id);
    }
  }, [visibleDepts]);

  const pushToast = useCallback((thread: Thread) => {
    const toastId = `thread-${thread.id}`;
    setToasts((old) => {
      const rest = old.filter((x) => x.id !== toastId);
      return [
        ...rest.slice(-2),
        {
          id: toastId,
          title: `Tin mới · ${thread.departmentTitle}`,
          body: `${thread.studentEmail || "Sinh viên"}: ${thread.preview || "…"}`,
        },
      ];
    });
  }, []);

  const loadThreads = useCallback(
    async (opts?: { reportError?: boolean }) => {
      try {
        const dept = selectedDeptRef.current;
        const q =
          dept && !isCrossDept ? `?departmentId=${encodeURIComponent(dept)}` : "";
        const r = await fetchApi(`/api/chat/threads${q}`);
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || r.statusText);
        const items: Thread[] = j.items || [];

        const key = threadListKey(items);
        if (key !== threadsKeyRef.current) {
          threadsKeyRef.current = key;
          setThreads(items);
        }

        for (const t of items) {
          const prev = prevUnreadRef.current[t.id] ?? 0;
          const cur = t.unreadForStaff ?? 0;
          if (cur > prev && t.id !== activeIdRef.current) {
            pushToast(t);
          }
          prevUnreadRef.current[t.id] = cur;
        }
        if (opts?.reportError) setErr(null);
      } catch (e) {
        if (opts?.reportError) {
          setErr(formatFetchError(e));
        }
      }
    },
    [fetchApi, isCrossDept, pushToast],
  );

  const loadMessages = useCallback(
    async (threadId: string, scrollIfNew = false, reportError = false) => {
      try {
        const r = await fetchApi(
          `/api/chat/threads/${encodeURIComponent(threadId)}/messages`,
        );
        const j = await r.json();
        if (!r.ok) throw new Error(j.error || r.statusText);
        const items: Msg[] = j.items || [];
        const key = messageListKey(items);
        if (key !== messagesKeyRef.current) {
          messagesKeyRef.current = key;
          setMessages(items);
          if (scrollIfNew) {
            requestAnimationFrame(() => {
              messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
            });
          }
        }
        prevUnreadRef.current[threadId] = 0;
        if (reportError) setErr(null);
      } catch (e) {
        if (reportError) {
          setErr(formatFetchError(e));
        }
      }
    },
    [fetchApi],
  );

  useEffect(() => {
    void loadThreads();
    const t = setInterval(() => void loadThreads(), THREADS_POLL_MS);
    return () => clearInterval(t);
  }, [loadThreads]);

  useEffect(() => {
    if (!activeId) {
      messagesKeyRef.current = "";
      setMessages([]);
      return;
    }
    void loadMessages(activeId, true);
    const t = setInterval(
      () => void loadMessages(activeId, false),
      MESSAGES_POLL_MS,
    );
    return () => clearInterval(t);
  }, [activeId, loadMessages]);

  const deptThreads = useMemo(
    () =>
      threads
        .filter((t) => !selectedDept || t.departmentId === selectedDept)
        .sort((a, b) =>
          (b.lastMessageAt || "").localeCompare(a.lastMessageAt || ""),
        ),
    [threads, selectedDept],
  );

  const deptUnread = useMemo(() => {
    const m: Record<string, number> = {};
    for (const d of visibleDepts) {
      m[d.id] = threads
        .filter((t) => t.departmentId === d.id)
        .reduce((s, t) => s + (t.unreadForStaff ?? 0), 0);
    }
    return m;
  }, [threads, visibleDepts]);

  function selectDepartment(deptId: string) {
    setSelectedDept(deptId);
    setActiveId(null);
    messagesKeyRef.current = "";
    setMessages([]);
  }

  function selectThread(threadId: string) {
    setActiveId(threadId);
    setToasts((t) => t.filter((x) => x.id !== `thread-${threadId}`));
  }

  async function onSendReply(e: React.FormEvent) {
    e.preventDefault();
    if (!activeId || !reply.trim()) return;
    setSending(true);
    setErr(null);
    try {
      const r = await fetchApi(
        `/api/chat/threads/${encodeURIComponent(activeId)}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: reply.trim() }),
        },
      );
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      setReply("");
      messagesKeyRef.current = "";
      await Promise.all([
        loadMessages(activeId, true, true),
        loadThreads({ reportError: true }),
      ]);
    } catch (e) {
      setErr(formatFetchError(e));
    } finally {
      setSending(false);
    }
  }

  const activeThread = threads.find((t) => t.id === activeId);

  return (
    <div className="relative space-y-4">
      <ToastStack
        toasts={toasts}
        onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))}
      />

      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-semibold text-slate-900">
            <MessageSquare className="h-7 w-7 text-brand-600" />
            Chat phòng ban
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Chọn phòng ban → sinh viên → hội thoại.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void loadThreads({ reportError: true })}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
        >
          Làm mới
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          {err}
          <button
            type="button"
            className="ml-2 underline"
            onClick={() => setErr(null)}
          >
            Đóng
          </button>
        </div>
      )}

      <div className="grid min-h-[520px] gap-0 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm lg:grid-cols-12">
        <div className="flex flex-col border-b border-slate-200 lg:col-span-3 lg:border-b-0 lg:border-r">
          <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase text-slate-500">
            Phòng ban
          </div>
          <div className="max-h-[480px] flex-1 overflow-y-auto overscroll-contain">
            {visibleDepts.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => selectDepartment(d.id)}
                className={
                  "flex w-full items-center gap-2 border-b border-slate-100 px-3 py-3 text-left text-sm hover:bg-slate-50 " +
                  (selectedDept === d.id
                    ? "bg-brand-50 font-medium text-brand-900"
                    : "text-slate-800")
                }
              >
                <span className="line-clamp-2 flex-1">{d.name}</span>
                <Badge n={deptUnread[d.id] ?? 0} />
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col border-b border-slate-200 lg:col-span-3 lg:border-b-0 lg:border-r">
          <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase text-slate-500">
            Sinh viên ({deptThreads.length})
          </div>
          <div className="max-h-[480px] flex-1 overflow-y-auto overscroll-contain">
            {deptThreads.length === 0 ? (
              <p className="p-4 text-sm text-slate-500">Chưa có hội thoại ở phòng này.</p>
            ) : (
              deptThreads.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => selectThread(t.id)}
                  className={
                    "flex w-full items-start gap-2 border-b border-slate-100 px-3 py-3 text-left text-sm hover:bg-slate-50 " +
                    (activeId === t.id
                      ? "bg-brand-50 font-medium text-brand-900"
                      : "text-slate-800")
                  }
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">
                      {t.studentEmail || t.studentUid}
                    </div>
                    <div className="mt-1 line-clamp-2 text-xs text-slate-600">
                      {t.preview || "—"}
                    </div>
                  </div>
                  <Badge n={t.unreadForStaff ?? 0} />
                </button>
              ))
            )}
          </div>
        </div>

        <div className="flex flex-col lg:col-span-6">
          {!activeId ? (
            <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
              Chọn sinh viên để xem và trả lời tin nhắn.
            </div>
          ) : (
            <>
              <div className="border-b border-slate-100 px-4 py-2">
                <div className="text-sm font-semibold text-slate-900">
                  {activeThread?.departmentTitle}
                </div>
                <div className="text-xs text-slate-500">
                  {activeThread?.studentEmail || activeThread?.studentUid}
                </div>
              </div>
              <div className="max-h-[340px] flex-1 space-y-3 overflow-y-auto overscroll-contain p-4">
                {messages.map((m) => (
                  <div
                    key={m.id}
                    className={
                      m.senderRole === "staff"
                        ? "ml-8 rounded-lg bg-brand-50 px-3 py-2 text-sm text-slate-800"
                        : "mr-8 rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-800"
                    }
                  >
                    <div className="mb-0.5 text-[10px] font-semibold uppercase text-slate-500">
                      {m.senderRole === "staff"
                        ? m.senderName || "Cán bộ"
                        : m.senderName || "Sinh viên"}
                    </div>
                    <div className="whitespace-pre-wrap">{m.text}</div>
                  </div>
                ))}
                <div ref={messagesEndRef} />
              </div>
              <form onSubmit={onSendReply} className="border-t border-slate-100 p-4">
                <label className="block text-xs font-medium text-slate-600">
                  Trả lời
                </label>
                <textarea
                  className="mt-1 min-h-[72px] w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  placeholder="Nhập phản hồi cho sinh viên…"
                />
                <button
                  type="submit"
                  disabled={sending || !reply.trim()}
                  className="mt-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
                >
                  {sending ? "Đang gửi…" : "Gửi trả lời"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
