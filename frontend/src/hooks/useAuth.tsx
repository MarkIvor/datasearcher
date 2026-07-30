import { useState, useEffect, useCallback, createContext, useContext, type ReactNode } from "react";
import type { AuthUser } from "../api/client";
import * as api from "../api/client";

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const u = await api.getMe();
        if (u && u.id) {
          setUser(u);
        } else {
          const refreshed = await api.refreshToken();
          if (refreshed) {
            setUser(refreshed.user);
          }
        }
      } catch {
        // not logged in
      }
      setLoading(false);
    })();
  }, []);

  const handleLogin = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    setUser(result.user);
  }, []);

  const handleRegister = useCallback(async (email: string, password: string, displayName: string) => {
    const result = await api.register(email, password, displayName);
    setUser(result.user);
  }, []);

  const handleLogout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login: handleLogin, register: handleRegister, logout: handleLogout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
