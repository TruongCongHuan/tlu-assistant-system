import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { canManageNotifications } from "@/lib/staffRole";
import { Plus, Trash2 } from "lucide-react";

type Row = {
  id: string;
  title: string;
  body: string;
  link: string | null;
  createdAt: string | null;
};

export function NotificationsPage() {
  const { staffProfile } = useStaffAuth();
  const fetchApi = useStaffFetch();
  const canManage = canManageNotifications(staffProfile?.role, staffProfile?.isSuper);
  const [rows, setRows] = useState<Row[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [link, setLink] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/notifications");
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

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setErr(null);
    try {
      const r = await fetchApi("/api/notifications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          body,
          link: link.trim() || null,
        }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      setTitle("");
      setBody("");
      setLink("");
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  async function onDelete(id: string) {
    if (!confirm("Xóa thông báo này?")) return;
    try {
      const r = await fetchApi(`/api/notifications/${encodeURIComponent(id)}`, {
        method: "DELETE",
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      await load();
    } catch (e) {
      setErr(String(e));
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Thông báo trường</h2>
        <p className="mt-1 text-sm text-slate-600">
          Collection <code className="rounded bg-slate-100 px-1">school_notifications</code>{" "}
          — luôn có trường <code className="rounded bg-slate-100 px-1">createdAt</code>.
        </p>
      </div>

      {err && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {err}
        </div>
      )}

      {!canManage && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Tài khoản của bạn chỉ được <strong>xem</strong> danh sách thông báo. Tạo và xóa chỉ dành cho quản
          trị hệ thống.
        </p>
      )}

      {canManage && (
        <form
          onSubmit={onCreate}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Plus className="h-4 w-4" />
            Đăng thông báo mới
          </h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-xs font-medium text-slate-600">Tiêu đề</span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-brand-600 focus:ring-2"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ví dụ: Lịch đăng ký học phần…"
                required
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-xs font-medium text-slate-600">Nội dung</span>
              <textarea
                className="min-h-[100px] w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-brand-600 focus:ring-2"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="Nội dung hiển thị trong app…"
              />
            </label>
            <label className="block sm:col-span-2">
              <span className="mb-1 block text-xs font-medium text-slate-600">
                Liên kết (tuỳ chọn)
              </span>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none ring-brand-600 focus:ring-2"
                value={link}
                onChange={(e) => setLink(e.target.value)}
                placeholder="https://…"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-brand-700 disabled:opacity-50"
          >
            {saving ? "Đang lưu…" : "Xuất bản"}
          </button>
        </form>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-600">
            <tr>
              <th className="px-4 py-3">Tiêu đề</th>
              <th className="hidden px-4 py-3 md:table-cell">Tạo lúc</th>
              {canManage ? <th className="w-24 px-4 py-3 text-right"></th> : null}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 ? (
              <tr>
                <td colSpan={canManage ? 3 : 2} className="px-4 py-8 text-center text-slate-500">
                  Chưa có thông báo.
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.id} className="hover:bg-slate-50/80">
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{r.title || "—"}</div>
                    <div className="mt-0.5 line-clamp-2 text-slate-600">{r.body}</div>
                    {r.link && (
                      <a
                        href={r.link}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-1 inline-block text-xs text-brand-600 hover:underline"
                      >
                        {r.link}
                      </a>
                    )}
                  </td>
                  <td className="hidden whitespace-nowrap px-4 py-3 text-slate-500 md:table-cell">
                    {r.createdAt ? formatDt(r.createdAt) : "—"}
                  </td>
                  {canManage ? (
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => void onDelete(r.id)}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-rose-700 hover:bg-rose-50"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Xóa
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatDt(iso: string) {
  try {
    return new Date(iso).toLocaleString("vi-VN");
  } catch {
    return iso;
  }
}
