import type { PropsWithChildren } from "react";
import { Navigate, useLocation } from "react-router";
import { useAuth } from "../lib/auth";
import type { UserRole } from "../types/api";

interface ProtectedRouteProps extends PropsWithChildren {
  roles?: UserRole[];
}

export function ProtectedRoute({ children, roles }: ProtectedRouteProps) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (roles && !roles.includes(user.role)) {
    return <Navigate to="/" replace />;
  }
  return children;
}
