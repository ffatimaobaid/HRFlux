'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { authApi } from '@/lib/api';

interface User {
  username: string;
  employee_id: string;
  role: 'admin' | 'employee';
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => { },
});

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('hrflux_token');

      if (!token && pathname !== '/login') {
        router.push('/login');
        setLoading(false);
        return;
      }

      if (token) {
        try {
          // Verify token with backend
          const res = await authApi.getMe();
          setUser({
            username: res.data.username,
            employee_id: res.data.employee_id,
            role: res.data.username === 'ADMIN' ? 'admin' : 'employee',
          });
        } catch (err) {
          console.error('Session expired', err);
          logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [pathname]);

  const logout = () => {
    localStorage.removeItem('hrflux_token');
    localStorage.removeItem('hrflux_user');
    localStorage.removeItem('hrflux_employee_id');
    localStorage.removeItem('hrflux_dismissed_notifs');
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
