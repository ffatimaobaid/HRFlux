
'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  AlertTriangle,
  Info,
  CheckCircle2,
  Clock,
  X
} from 'lucide-react';

export interface ProactiveNotification {
  id?: number;
  type: 'info' | 'warning' | 'success' | 'critical';
  title: string;
  message: string;
  action_label?: string;
  action_id?: string;
}

interface SmartNotificationProps {
  notifications: ProactiveNotification[];
  onAction?: (actionId: string) => void;
  onClose: (index: number) => void;
  isDropdown?: boolean;
}

export default function SmartNotification({ notifications, onAction, onClose, isDropdown = false }: SmartNotificationProps) {
  if (!notifications || notifications.length === 0) return null;

  return (
    <div className={`w-full ${isDropdown ? 'max-h-[70vh] overflow-y-auto px-1' : 'space-y-4 mb-6'}`}>
      <AnimatePresence>
        {notifications.map((notif, idx) => (
          <motion.div
            key={`${notif.title}-${idx}`}
            initial={isDropdown ? { opacity: 0, x: 20 } : { opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
            className={`relative overflow-hidden transition-all group ${isDropdown
              ? 'p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50'
              : `rounded-2xl p-4 shadow-md border mb-3 ${notif.type === 'critical' ? 'bg-red-50 border-red-200' :
                notif.type === 'warning' ? 'bg-orange-50 border-orange-200' :
                  notif.type === 'success' ? 'bg-green-50 border-green-200' :
                    'bg-indigo-50 border-indigo-200'
              }`
              }`}
          >
            {/* Background Glow Effect - only on dashboard mode */}
            {!isDropdown && (
              <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-20 ${notif.type === 'critical' ? 'bg-red-400' :
                notif.type === 'warning' ? 'bg-orange-400' :
                  notif.type === 'success' ? 'bg-green-400' :
                    'bg-indigo-400'
                }`} />
            )}

            <div className={`relative z-10 flex items-start ${isDropdown ? 'gap-2' : 'gap-4'}`}>
              <div className={`rounded-xl transition-transform ${isDropdown ? 'p-1.5' : 'p-3 shadow-md group-hover:rotate-12'} ${notif.type === 'critical' ? 'bg-red-500 text-white' :
                notif.type === 'warning' ? 'bg-orange-500 text-white' :
                  notif.type === 'success' ? 'bg-green-500 text-white' :
                    'bg-indigo-600 text-white'
                }`}>
                {notif.type === 'critical' ? <Clock size={isDropdown ? 14 : 20} /> :
                  notif.type === 'warning' ? <AlertTriangle size={isDropdown ? 14 : 20} /> :
                    notif.type === 'success' ? <CheckCircle2 size={isDropdown ? 14 : 20} /> :
                      <Sparkles size={isDropdown ? 14 : 20} />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <h3 className={`font-bold tracking-tight truncate ${isDropdown ? 'text-xs' : 'text-sm'} ${notif.type === 'critical' ? 'text-red-900' :
                    notif.type === 'warning' ? 'text-orange-900' :
                      notif.type === 'success' ? 'text-green-900' :
                        'text-indigo-900'
                    }`}>
                    {notif.title}
                  </h3>
                  <button
                    onClick={() => onClose(idx)}
                    className="p-1 hover:bg-black/10 rounded-lg transition-colors flex-shrink-0"
                    title="Dismiss"
                  >
                    <X size={14} className="opacity-60 text-gray-700" />
                  </button>
                </div>
                <p className={`font-medium text-gray-600 leading-relaxed ${isDropdown ? 'text-[10px] line-clamp-2 mb-1.5' : 'text-xs mb-3'}`}>
                  {notif.message}
                </p>


              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
