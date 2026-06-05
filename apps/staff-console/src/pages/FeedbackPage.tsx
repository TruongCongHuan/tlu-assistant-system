import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";

type Row = {
  id: string;
  subject: string;
  body: string;
  anonymous: boolean;
  studentLabel: string | null;
  studentEmail: string | null;
  createdAt: string | null;
};

export function FeedbackPage() {
  const fetchApi = useStaffFetch();
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/feedback");
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      setRows(j.items || []);
    } catch (e) {
      setErr(String(e));
    }
  }, [fetchApi]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Góp ý / thư sinh viên</h2>
          <p className="mt-1 text-sm text-slate-600">
            <code className="rounded bg-slate-100 px-1">feedback_letters</code>
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
        >
          Làm mới
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {err}
        </div>
      )}

      <div className="space-y-4">
        {rows.length === 0 ? (
          <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 py-12 text-center text-slate-500">
            Chưa có góp ý.
          </p>
        ) : (
          rows.map((r) => (
            <article
              key={r.id}
              className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <h3 className="font-semibold text-slate-900">{r.subject}</h3>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {r.anonymous ? (
                    <span className="rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-900 ring-1 ring-amber-200">
                      Ẩn danh
                    </span>
                  ) : (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-slate-700">
                      {r.studentLabel || r.studentEmail || "Có danh"}
                    </span>
                  )}
                  <span className="text-slate-500">
                    {r.createdAt
                      ? new Date(r.createdAt).toLocaleString("vi-VN")
                      : ""}
                  </span>
                </div>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm text-slate-700">{r.body}</p>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
