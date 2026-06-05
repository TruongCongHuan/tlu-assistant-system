import { useStaffAuth } from "@/context/StaffKeyContext";
import { apiUrl } from "@/lib/apiUrl";

export async function staffFetch(
  accessToken: string,
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (accessToken.trim()) {
    headers.set("Authorization", `Bearer ${accessToken.trim()}`);
  }
  return fetch(apiUrl(path), { ...init, headers });
}

export function useStaffFetch() {
  const { accessToken } = useStaffAuth();
  return (path: string, init?: RequestInit) => staffFetch(accessToken, path, init);
}
