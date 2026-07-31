import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { apiRequest, clearStoredToken, formBody, getStoredToken, storeToken } from "./api";
import type { LoginResponse, User } from "../types/api";

const USER_KEY = "blueberry-microid.user";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadStoredUser(): User | null {
  const raw = sessionStorage.getItem(USER_KEY);
  if (!raw || !getStoredToken()) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    sessionStorage.removeItem(USER_KEY);
    clearStoredToken();
    return null;
  }
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(() => loadStoredUser());

  const clearSession = useCallback(() => {
    clearStoredToken();
    sessionStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  useEffect(() => {
    const expire = () => clearSession();
    window.addEventListener("blueberry-auth-expired", expire);
    return () => window.removeEventListener("blueberry-auth-expired", expire);
  }, [clearSession]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await apiRequest<LoginResponse>(
      "/api/v1/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formBody({ username, password }),
      },
      { authenticated: false },
    );
    storeToken(response.access_token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(response.user));
    setUser(response.user);
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiRequest<{ message: string }>("/api/v1/auth/logout", { method: "POST" });
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, isAuthenticated: user !== null, login, logout }),
    [user, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
