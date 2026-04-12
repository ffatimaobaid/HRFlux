'use client';

import React, { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useRouter } from 'next/navigation';
import { Skeleton } from 'antd';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (!user || user.role !== 'admin') {
        console.warn('Unauthorized access attempt to admin area');
        router.push('/dashboard');
      }
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="p-20">
        <Skeleton active paragraph={{ rows: 10 }} />
      </div>
    );
  }

  if (!user || user.role !== 'admin') {
    return null; // Don't even render the children if not admin
  }

  return <>{children}</>;
}
