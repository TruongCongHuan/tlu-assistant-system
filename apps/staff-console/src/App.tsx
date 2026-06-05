import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AppLayout } from "./layout/AppLayout";
import { DashboardHome } from "./pages/DashboardHome";
import { StudentsPage } from "./pages/StudentsPage";
import { SubmissionsPage } from "./pages/SubmissionsPage";
import { FeedbackPage } from "./pages/FeedbackPage";
import { VectorDocsPage } from "./pages/VectorDocsPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { DepartmentChatPage } from "./pages/DepartmentChatPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LoginPage } from "./pages/LoginPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { useStaffAuth } from "./context/StaffKeyContext";
import { canAccessPath } from "./lib/staffRole";

function RequireAuthShell({ children }: { children: React.ReactNode }) {
  const { accessToken } = useStaffAuth();
  const location = useLocation();
  if (!accessToken.trim()) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: `${location.pathname}${location.search}` }}
      />
    );
  }
  return <>{children}</>;
}

function RoleGate({ children }: { children: React.ReactNode }) {
  const { staffProfile } = useStaffAuth();
  const { pathname } = useLocation();
  if (!canAccessPath(staffProfile?.role, pathname, staffProfile?.isSuper)) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <RequireAuthShell>
            <AppLayout />
          </RequireAuthShell>
        }
      >
        <Route
          index
          element={
            <RoleGate>
              <DashboardHome />
            </RoleGate>
          }
        />
        <Route
          path="students"
          element={
            <RoleGate>
              <StudentsPage />
            </RoleGate>
          }
        />
        <Route
          path="chat"
          element={
            <RoleGate>
              <DepartmentChatPage />
            </RoleGate>
          }
        />
        <Route
          path="notifications"
          element={
            <RoleGate>
              <NotificationsPage />
            </RoleGate>
          }
        />
        <Route
          path="submissions"
          element={
            <RoleGate>
              <SubmissionsPage />
            </RoleGate>
          }
        />
        <Route
          path="feedback"
          element={
            <RoleGate>
              <FeedbackPage />
            </RoleGate>
          }
        />
        <Route
          path="vectors"
          element={
            <RoleGate>
              <VectorDocsPage />
            </RoleGate>
          }
        />
        <Route
          path="audit"
          element={
            <RoleGate>
              <AuditLogsPage />
            </RoleGate>
          }
        />
        <Route
          path="settings"
          element={
            <RoleGate>
              <SettingsPage />
            </RoleGate>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
