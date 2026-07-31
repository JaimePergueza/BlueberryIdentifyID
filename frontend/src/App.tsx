import { Navigate, Route, Routes } from "react-router";
import { AppShell } from "./components/AppShell";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AnalysisDetailPage } from "./pages/AnalysisDetailPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LoginPage } from "./pages/LoginPage";
import { NewAnalysisPage } from "./pages/NewAnalysisPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { PreliminaryResultPage } from "./pages/PreliminaryResultPage";
import { ReviewPage } from "./pages/ReviewPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute roles={["admin", "specialist"]}>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="analyses" element={<HistoryPage />} />
        <Route path="analyses/new" element={<NewAnalysisPage />} />
        <Route path="analyses/:analysisRunId" element={<AnalysisDetailPage />} />
        <Route path="analyses/:analysisRunId/preliminary" element={<PreliminaryResultPage />} />
        <Route path="analyses/:analysisRunId/review" element={<ReviewPage />} />
        <Route
          path="admin/users"
          element={
            <ProtectedRoute roles={["admin"]}>
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />
        <Route path="404" element={<NotFoundPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}
