import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";
import { Download } from "lucide-react";

type Attachment = {
  name: string;
  size?: number;
  fileKey: string | null;
};

type Row = {
  id: string;
  title: string;
  details: string;
  studentEmail: string | null;
  attachmentCount: number;
  attachments?: Attachment[];
  createdAt: string | null;
};

export function SubmissionsPage() {
  const fetchApi = useStaffFetch();
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/submissions");
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      setRows(j.items || []);
    } catch (e) {
      setErr(String(e));
    }
  }, [fetchApi]);

  useEffect(() => {
    void load();
    const t = setInterval(() => void load(), 5000);
    return () => clearInterval(t);
  }, [load]);

  async function downloadFile(submissionId: string, fileKey: string, displayName: string) {
    const key = `${submissionId}:${fileKey}`;
    setDownloading(key);
    try {
      const r = await fetchApi(
        `/api/files/${encodeURIComponent(submissionId)}/${encodeURIComponent(fileKey)}`,
      );
      if (!r.ok) throw new Error(await r.text());
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = displayName || fileKey;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setErr(String(e));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Đơn từ sinh viên</h2>
          <p className="mt-1 text-sm text-slate-600">
            Bấm tên tệp để tải về máy cán bộ (PDF / Word).
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
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-600">
            <tr>
              <th className="px-4 py-3">Tiêu đề</th>
              <th className="px-4 py-3">SV / email</th>
              <th className="px-4 py-3">Tệp đính kèm</th>
              <th className="px-4 py-3">Thời gian</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  Chưa có đơn.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="align-top hover:bg-slate-50/80">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{r.title}</div>
                    <div className="mt-1 max-w-md whitespace-pre-wrap text-slate-600">
                      {r.details}
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-700">
                    {r.studentEmail || "—"}
                  </td>
                  <td className="px-4 py-3">
                    {(r.attachments?.length ?? 0) === 0 ? (
                      <span className="text-slate-400">—</span>
                    ) : (
                      <ul className="space-y-1">
                        {r.attachments!.map((a) => {
                          const fk = a.fileKey;
                          if (!fk) return null;
                          const busy = downloading === `${r.id}:${fk}`;
                          return (
                            <li key={fk}>
                              <button
                                type="button"
                                disabled={busy}
                                onClick={() =>
                                  void downloadFile(r.id, fk, a.name || fk)
                                }
                                className="inline-flex items-center gap-1 rounded-md px-1 py-0.5 text-left text-brand-700 hover:bg-brand-50 hover:underline disabled:opacity-50"
                              >
                                <Download className="h-3.5 w-3.5 shrink-0" />
                                <span className="max-w-[200px] truncate">
                                  {a.name || fk}
                                  {a.size ? ` (${Math.round(a.size / 1024)} KB)` : ""}
                                </span>
                              </button>
                            </li>
                          );
                        })}
                      </ul>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-500">
                    {r.createdAt
                      ? new Date(r.createdAt).toLocaleString("vi-VN")
                      : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
