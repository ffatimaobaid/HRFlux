'use client';

import React from 'react';
import AdminSidebar from '@/components/AdminSidebar';

export default function MultimodalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen bg-[#f1f2f6]">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto custom-scrollbar">
        {children}
      </main>
    </div>
  );
}
