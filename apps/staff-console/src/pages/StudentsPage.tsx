import { useCallback, useEffect, useState } from "react";
import { useStaffFetch } from "@/lib/api";
import { useStaffAuth } from "@/context/StaffKeyContext";
import { canEditStudentProfiles } from "@/lib/staffRole";
import { Users, Pencil, Save } from "lucide-react";

type UserRow = {
  id: string;
  email: string | null;
  displayName: string | null;
  role: string;
  studentCode: string | null;
  fullName: string | null;
  className: string | null;
  faculty: string | null;
  course: string | null;
  phone: string | null;
  source: string | null;
  updatedAt: string | null;
};

const emptyForm = {
  studentCode: "",
  fullName: "",
  className: "",
  faculty: "",
  course: "",
  phone: "",
  source: "",
};

export function StudentsPage() {
  const { staffProfile } = useStaffAuth();
  const fetchApi = useStaffFetch();
  const canEdit = canEditStudentProfiles(staffProfile?.role, staffProfile?.isSuper);
  const [rows, setRows] = useState<UserRow[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [selected, setSelected] = useState<UserRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setErr(null);
    try {
      const r = await fetchApi("/api/users?role=student");
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

  function openEdit(u: UserRow) {
    setSelected(u);
    setForm({
      studentCode: u.studentCode ?? "",
      fullName: u.fullName ?? "",
      className: u.className ?? "",
      faculty: u.faculty ?? "",
      course: u.course ?? "",
      phone: u.phone ?? "",
      source: u.source ?? "",
    });
  }

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    if (!selected) return;
    setSaving(true);
    setErr(null);
    try {
      const r = await fetchApi(`/api/users/${encodeURIComponent(selected.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          studentCode: form.studentCode || null,
          fullName: form.fullName || null,
          className: form.className || null,
          faculty: form.faculty || null,
          course: form.course || null,
          phone: form.phone || null,
          source: form.source || null,
        }),
      });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || r.statusText);
      setSelected(null);
      setForm(emptyForm);
      await load();
    } catch (e) {
      setErr(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-semibold text-slate-900">
            <Users className="h-7 w-7 text-brand-600" />
            Sinh viên & hồ sơ
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Collection <code className="rounded bg-slate-100 px-1">users</code> — đồng bộ từ app
            khi SV đăng nhập Google; chỉnh sửa hồ sơ học vụ chỉ dành cho quản trị hệ thống.
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

      <div className="grid gap-8 lg:grid-cols-5">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm lg:col-span-3">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase text-slate-600">
              <tr>
                <th className="px-4 py-3">Email / tên</th>
                <th className="hidden px-4 py-3 sm:table-cell">MSSV</th>
                {canEdit ? <th className="w-24 px-4 py-3"></th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 ? (
                <tr>
                  <td colSpan={canEdit ? 3 : 2} className="px-4 py-10 text-center text-slate-500">
                    Chưa có bản ghi users. Đăng nhập app Flutter (SV) để tạo hồ sơ.
                  </td>
                </tr>
              ) : (
                rows.map((u) => (
                  <tr
                    key={u.id}
                    className={
                      selected?.id === u.id
                        ? "bg-brand-50/60"
                        : "hover:bg-slate-50/80"
                    }
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-slate-900">{u.email ?? "—"}</div>
                      <div className="text-slate-600">{u.displayName ?? u.fullName ?? ""}</div>
                    </td>
                    <td className="hidden px-4 py-3 text-slate-700 sm:table-cell">
                      {u.studentCode ?? "—"}
                    </td>
                    {canEdit ? (
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={() => openEdit(u)}
                          className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs font-medium text-brand-700 hover:bg-white"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                          Sửa
                        </button>
                      </td>
                    ) : null}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 lg:col-span-2">
          {!canEdit ? (
            <p className="text-sm text-slate-600">
              Bạn đang xem danh sách ở chế độ <strong>chỉ đọc</strong>. Cập nhật MSSV, lớp, khoa cần tài
              khoản quản trị hệ thống.
            </p>
          ) : !selected ? (
            <p className="text-sm text-slate-500">
              Chọn <strong>Sửa</strong> để cập nhật hồ sơ học vụ (không đổi email Google; không
              đổi role từ đây — dùng custom claims / Admin SDK khi cần).
            </p>
          ) : (
            <form onSubmit={onSave} className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-800">Chỉnh sửa</h3>
              <p className="truncate text-xs text-slate-500">{selected.email}</p>
              {(
                [
                  ["studentCode", "MSSV"],
                  ["fullName", "Họ tên đầy đủ"],
                  ["className", "Lớp"],
                  ["faculty", "Khoa / đơn vị"],
                  ["course", "Khóa / ngành"],
                  ["phone", "Điện thoại"],
                  ["source", "Ghi chú nguồn (sis_import, manual…)"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block">
                  <span className="mb-1 block text-xs font-medium text-slate-600">{label}</span>
                  <input
                    className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none ring-brand-600 focus:ring-2"
                    value={form[key]}
                    onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  />
                </label>
              ))}
              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Đang lưu…" : "Lưu"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSelected(null);
                    setForm(emptyForm);
                  }}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
                >
                  Hủy
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
