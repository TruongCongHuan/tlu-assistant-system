import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";
import { Upload } from "lucide-react";

type Doc = {
  id: string;
  name: string;
  chunk_count: number;
  created_at: string;
};

type JobState = {
  job_id: string;
  status: string;
  error: string | null;
} | null;

export function VectorDocsPage() {
  const fetchApi = useStaffFetch();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [job, setJob] = useState<JobState>(null);

  const refresh = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/rag/documents");
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || (typeof j === "string" ? j : r.statusText));
      setDocs(j.documents ?? []);
    } catch (e) {
      setErr(String(e));
    }
  }, [fetchApi]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!job || job.status === "completed" || job.status === "failed") return;
    const t = setInterval(async () => {
      try {
        const r = await fetchApi(
          `/api/rag/ingest-jobs/${encodeURIComponent(job.job_id)}`,
        );
        const j = await r.json();
        if (!r.ok) return;
        setJob({
          job_id: j.job_id,
          status: j.status,
          error: j.error ?? null,
        });
        if (j.status === "completed" || j.status === "failed") void refresh();
      } catch {
        /* ignore */
      }
    }, 900);
    return () => clearInterval(t);
  }, [job, fetchApi, refresh]);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const r = await fetchApi("/api/rag/documents", { method: "POST", body: fd });
      const text = await r.text();
      let j: { job_id?: string };
      try {
        j = JSON.parse(text) as { job_id?: string };
      } catch {
        throw new Error(text || r.statusText);
      }
      if (!r.ok) throw new Error((j as { error?: string }).error || text);
      if (j.job_id) setJob({ job_id: j.job_id, status: "pending", error: null });
    } catch (e) {
      setErr(String(e));
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Xóa tài liệu và toàn bộ vector trong Chroma?")) return;
    try {
      const r = await fetchApi(`/api/rag/documents/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      if (!r.ok) throw new Error(await r.text());
      await refresh();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Vector & tài liệu RAG</h2>
        <p className="mt-1 text-sm text-slate-600">
          Upload qua BFF tới RAG API (PDF, Markdown, TXT). Khóa Admin RAG được cấu hình trên
          server — không lộ ra trình duyệt.
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {err}
        </div>
      )}

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
          <Upload className="h-4 w-4" />
          Tải lên
        </h3>
        <input
          type="file"
          accept=".pdf,.md,.txt,.markdown"
          onChange={(e) => void onFile(e)}
          className="block w-full max-w-md text-sm text-slate-700 file:mr-4 file:rounded-lg file:border-0 file:bg-brand-50 file:px-4 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
        />
        {job && (
          <p className="mt-3 text-sm text-slate-600">
            Job <code className="rounded bg-slate-100 px-1">{job.job_id}</code>:{" "}
            <strong>{job.status}</strong>
            {job.error && <span className="text-rose-700"> — {job.error}</span>}
          </p>
        )}
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-3">
          <h3 className="text-sm font-semibold text-slate-800">Tài liệu đã index</h3>
          <button
            type="button"
            onClick={() => void refresh()}
            className="text-sm font-medium text-brand-700 hover:underline"
          >
            Làm mới
          </button>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 text-xs font-semibold uppercase text-slate-600">
            <tr>
              <th className="px-4 py-3">Tên</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Tạo lúc</th>
              <th className="w-24 px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {docs.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  Chưa có tài liệu.
                </td>
              </tr>
            ) : (
              docs.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3 font-medium text-slate-900" title={d.id}>
                    {d.name}
                  </td>
                  <td className="px-4 py-3 text-slate-700">{d.chunk_count}</td>
                  <td className="px-4 py-3 text-slate-500">{d.created_at}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => void onDelete(d.id)}
                      className="rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50"
                    >
                      Xóa
                    </button>
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
