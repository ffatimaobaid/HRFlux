'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MessageSquare, 
  Calendar, 
  User, 
  LogOut, 
  Bell, 
  Trash2,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '@/hooks/useAuth';

export default function Sidebar({ onClearChat }: { onClearChat?: () => void }) {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  const menuItems = [
    { name: 'Chat', icon: <MessageSquare size={20} />, href: '/dashboard' },
    { name: 'Calendar & Tasks', icon: <Calendar size={20} />, href: '/dashboard/calendar' },
    { name: 'My Profile', icon: <User size={20} />, href: '/dashboard/profile' },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-8">
          <div className="bg-indigo-600 p-2 rounded-lg text-white">
            <MessageSquare size={20} />
          </div>
          <span className="text-xl font-bold tracking-tight">HRFLUX</span>
        </div>

        <div className="mb-8 p-4 bg-indigo-50 rounded-2xl flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-200 rounded-full flex items-center justify-center text-indigo-700 font-bold">
            {user?.username?.charAt(0).toUpperCase()}
          </div>
          <div className="overflow-hidden">
            <p className="text-sm font-bold text-indigo-900 truncate">{user?.username}</p>
            <p className="text-xs text-indigo-600">Employee</p>
          </div>
        </div>

        <nav className="space-y-2">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.name} href={item.href}>
                <motion.div
                  whileHover={{ x: 4 }}
                  className={`flex items-center justify-between p-3 rounded-xl transition-all ${
                    isActive 
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200' 
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
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
        {onClearChat && (
          <button
            onClick={onClearChat}
            className="w-full flex items-center gap-3 p-3 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all text-sm font-semibold"
          >
            <Trash2 size={20} />
            Clear Chat
          </button>
        )}
        
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 p-3 text-gray-500 hover:text-gray-900 hover:bg-gray-50 rounded-xl transition-all text-sm font-semibold"
        >
          <LogOut size={20} />
          Logout
        </button>
        
        <div className="pt-4 border-t border-gray-100 text-center">
          <p className="text-[10px] text-gray-400 font-medium">© 2024 HRFLUX SYSTEM</p>
        </div>
      </div>
    </aside>
  );
}
