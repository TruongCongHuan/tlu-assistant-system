import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";

type Row = {
  id: string;
  action: string;
  resourceType: string;
  resourceId: string;
  payloadSummary: string;
  at: string | null;
  actorUid: string | null;
  actorEmail: string | null;
  actorRole: string | null;
};

export function AuditLogsPage() {
  const fetchApi = useStaffFetch();
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/audit-logs");
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
          <h2 className="text-2xl font-semibold text-slate-900">Nhật ký thao tác</h2>
          <p className="mt-1 text-sm text-slate-600">
            <code className="rounded bg-slate-100 px-1">audit_logs</code> — ghi khi đăng / xóa
            thông báo từ console.
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

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[800px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-600">
            <tr>
              <th className="px-4 py-3">Thời gian</th>
              <th className="px-4 py-3">Actor</th>
              <th className="px-4 py-3">Hành động</th>
              <th className="px-4 py-3">Tài nguyên</th>
              <th className="px-4 py-3">Mô tả</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Chưa có bản ghi.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="align-top hover:bg-slate-50/80">
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                    {r.at ? new Date(r.at).toLocaleString("vi-VN") : "—"}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    {r.actorEmail || r.actorUid || r.actorRole || "—"}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">{r.action}</td>
                  <td className="px-4 py-3 text-slate-700">
                    <div className="text-xs text-slate-500">{r.resourceType}</div>
                    <code className="text-xs">{r.resourceId}</code>
                  </td>
                  <td className="max-w-md px-4 py-3 text-slate-700">{r.payloadSummary}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
