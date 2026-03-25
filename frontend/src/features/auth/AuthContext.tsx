import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import api from '../../lib/api';
import type { AuthState, User } from '../../lib/types';

const AuthContext = createContext<AuthState | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Validate token on mount by calling /auth/me
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedEmail = localStorage.getItem('user_email');
    if (storedToken && storedEmail) {
      // Validate token is still valid
      api
        .get<{ user_id: string }>('/auth/me', {
          headers: { Authorization: `Bearer ${storedToken}` },
        })
        .then((res) => {
          setToken(storedToken);
          setUser({ id: res.data.user_id, email: storedEmail });
        })
        .catch(() => {
          localStorage.removeItem('token');
          localStorage.removeItem('user_email');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const params = new URLSearchParams();
    params.set('username', email);
    params.set('password', password);

    const { data } = await api.post<{ access_token: string; token_type: string }>(
      '/auth/login',
      params,
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } },
    );

    const accessToken = data.access_token;
    localStorage.setItem('token', accessToken);
    localStorage.setItem('user_email', email);
    setToken(accessToken);

    // Fetch user_id from /auth/me
    const meRes = await api.get<{ user_id: string }>('/auth/me', {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    setUser({ id: meRes.data.user_id, email });
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await api.post('/auth/register', { email, password });
    // Auto-login after successful registration
    await login(email, password);
  }, [login]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_email');
    setToken(null);
    setUser(null);
  }, []);

  const value: AuthState = {
    user,
    token,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };

  if (loading) {
    return null;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuthContext must be used within AuthProvider');
  }
  return ctx;
}
