'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('hrflux_token');
    const userString = localStorage.getItem('hrflux_user');

    if (!token) {
      router.replace('/login');
    } else {
      // Basic check for admin vs employee
      if (userString === 'ADMIN') {
        router.replace('/admin');
      } else {
        router.replace('/dashboard');
      }
    }
  }, [router]);

  return (
    <div className="flex h-screen items-center justify-center bg-[#e3e6ff]">
      <div className="flex flex-col items-center gap-4 animate-pulse">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-indigo-600 font-bold tracking-tighter">AUTHENTICATING...</p>
      </div>
    </div>
  );
}
