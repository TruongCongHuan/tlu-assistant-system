import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

const STORAGE_JWT = "tlu_staff_access_token";
const STORAGE_PROFILE = "tlu_staff_profile";

export type StaffProfile = {
  id: string;
  email: string;
  loginId?: string | null;
  fullName: string;
  staffCode: string;
  departmentId: string;
  departmentName: string;
  /** super_admin | staff | auditor */
  role: string;
  /** @deprecated dùng role === 'super_admin' */
  isSuper?: boolean;
};

type Ctx = {
  accessToken: string;
  setAccessToken: (t: string) => void;
  staffProfile: StaffProfile | null;
  setStaffProfile: (p: StaffProfile | null) => void;
  persistStaffSession: (token: string, profile: StaffProfile) => void;
  clearStaffSession: () => void;
};

const StaffAuthContext = createContext<Ctx | null>(null);

function loadProfile(): StaffProfile | null {
  try {
    const raw = localStorage.getItem(STORAGE_PROFILE);
    if (!raw) return null;
    const p = JSON.parse(raw) as StaffProfile;
    if (!p.role && p.isSuper) p.role = "super_admin";
    if (!p.role) p.role = "staff";
    return p;
  } catch {
    return null;
  }
}

export function StaffAuthProvider({ children }: { children: React.ReactNode }) {
  const [accessToken, setAccessToken] = useState(
    () => localStorage.getItem(STORAGE_JWT) || "",
  );
  const [staffProfile, setStaffProfile] = useState<StaffProfile | null>(
    () => loadProfile(),
  );

  const persistStaffSession = useCallback((token: string, profile: StaffProfile) => {
    const t = token.trim();
    setAccessToken(t);
    setStaffProfile(profile);
    localStorage.setItem(STORAGE_JWT, t);
    localStorage.setItem(STORAGE_PROFILE, JSON.stringify(profile));
  }, []);

  const clearStaffSession = useCallback(() => {
    setAccessToken("");
    setStaffProfile(null);
    localStorage.removeItem(STORAGE_JWT);
    localStorage.removeItem(STORAGE_PROFILE);
  }, []);

  const value = useMemo(
    () => ({
      accessToken,
      setAccessToken,
      staffProfile,
      setStaffProfile,
      persistStaffSession,
      clearStaffSession,
    }),
    [accessToken, staffProfile, persistStaffSession, clearStaffSession],
  );

  return (
    <StaffAuthContext.Provider value={value}>{children}</StaffAuthContext.Provider>
  );
}

/** Tên cũ cho `main.tsx` */
export const StaffKeyProvider = StaffAuthProvider;

export function useStaffAuth() {
  const ctx = useContext(StaffAuthContext);
  if (!ctx) throw new Error("useStaffAuth outside provider");
  return ctx;
}

/** @deprecated alias */
export function useStaffKey() {
  const a = useStaffAuth();
  return {
    staffKey: "",
    setStaffKey: () => {},
    persistKey: () => {},
  };
}
