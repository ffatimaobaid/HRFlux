'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  History, 
  AlertTriangle, 
  Files, 
  Settings, 
  Bot,
  LogOut,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export default function AdminSidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  const menuItems = [
    { name: 'Dashboard', icon: <LayoutDashboard size={20} />, href: '/admin' },
    { name: 'Query Logs', icon: <History size={20} />, href: '/admin/logs' },
    { name: 'Escalations', icon: <AlertTriangle size={20} />, href: '/admin/escalations' },
    { name: 'Document Manager', icon: <Files size={20} />, href: '/admin/documents' },
    { name: 'Settings', icon: <Settings size={20} />, href: '/admin/settings' },
    { name: 'Admin ChatBot', icon: <Bot size={20} />, href: '/admin/chat' },
    { name: 'Multi-Modal AI', icon: <ShieldCheck size={20} />, href: '/admin/multimodal' },
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-screen sticky top-0">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-10">
          <div className="bg-indigo-500 p-2 rounded-lg text-white">
            <ShieldCheck size={24} />
          </div>
          <span className="text-xl font-bold tracking-tight">HRFLUX <span className="text-indigo-400">ADMIN</span></span>
        </div>

        <div className="mb-10 p-4 bg-gray-800/50 rounded-2xl flex items-center gap-3 border border-gray-700/50">
          <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center text-white font-bold">
            A
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-bold truncate">Administrator</p>
            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Master Control</p>
          </div>
        </div>

        <nav className="space-y-1">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.name} href={item.href}>
                <motion.div
                  whileHover={{ x: 4 }}
                  className={`flex items-center justify-between p-3.5 rounded-xl transition-all ${
                    isActive 
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-900/20' 
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {item.icon}
                    <span className="font-semibold text-sm">{item.name}</span>
                  </div>
                  {isActive && <ChevronRight size={16} />}
                </motion.div>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="mt-auto p-6 space-y-4">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 p-3.5 text-gray-400 hover:text-white hover:bg-gray-800 rounded-xl transition-all text-sm font-semibold"
        >
          <LogOut size={20} />
          Logout
        </button>
        
        <div className="pt-4 border-t border-gray-800 text-center">
          <p className="text-[10px] text-gray-500 font-medium tracking-widest uppercase">HRFLUX ADMIN V1.0</p>
        </div>
      </div>
    </aside>
  );
}
