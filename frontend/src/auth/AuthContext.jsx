import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import {
  getCurrentUser,
  loginWithSession,
  logoutSession,
} from "../api/auth";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionError, setSessionError] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadSession() {
      try {
        const currentUser = await getCurrentUser();
        if (isMounted) setUser(currentUser?.is_staff ? currentUser : null);
      } catch (error) {
        if (isMounted && !(error instanceof ApiError && error.status === 403)) {
          setSessionError("Não foi possível verificar a sessão.");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (credentials) => {
    const response = await loginWithSession(credentials);
    if (!response.user?.is_staff) {
      throw new ApiError("Não foi possível autenticar.", 403);
    }
    setUser(response.user);
    setSessionError("");
    return response.user;
  }, []);

  const logout = useCallback(async () => {
    await logoutSession();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, isLoading, sessionError, login, logout }),
    [user, isLoading, sessionError, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
