/**
 * URL gọi BFF. Để trống = cùng origin (Docker :3000 hoặc Vite dev proxy /api).
 * Chỉ set VITE_API_BASE_URL khi UI và API khác origin (vd: http://127.0.0.1:3001).
 */
export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim().replace(/\/$/, "") ?? "";
  if (!base) return p;
  return `${base}${p}`;
}
