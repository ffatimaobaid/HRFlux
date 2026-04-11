
'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sparkles, 
  AlertTriangle, 
  Info, 
  CheckCircle2, 
  Clock,
  ArrowRight
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
            className={`relative overflow-hidden transition-all group ${
              isDropdown 
                ? 'p-4 border-b border-gray-100 last:border-0 hover:bg-gray-50' 
                : `rounded-3xl p-6 shadow-xl border-2 mb-4 ${
                    notif.type === 'critical' ? 'bg-red-50 border-red-200' :
                    notif.type === 'warning' ? 'bg-orange-50 border-orange-200' :
                    notif.type === 'success' ? 'bg-green-50 border-green-200' :
                    'bg-indigo-50 border-indigo-200'
                  }`
            }`}
          >
            {/* Background Glow Effect - only on dashboard mode */}
            {!isDropdown && (
              <div className={`absolute -right-10 -top-10 w-32 h-32 rounded-full blur-3xl opacity-20 ${
                notif.type === 'critical' ? 'bg-red-400' :
                notif.type === 'warning' ? 'bg-orange-400' :
                notif.type === 'success' ? 'bg-green-400' :
                'bg-indigo-400'
              }`} />
            )}

            <div className={`relative z-10 flex items-start ${isDropdown ? 'gap-3' : 'gap-5'}`}>
              <div className={`rounded-2xl transition-transform ${isDropdown ? 'p-2' : 'p-4 shadow-lg group-hover:rotate-12'} ${
                notif.type === 'critical' ? 'bg-red-500 text-white' :
                notif.type === 'warning' ? 'bg-orange-500 text-white' :
                notif.type === 'success' ? 'bg-green-500 text-white' :
                'bg-indigo-600 text-white'
              }`}>
                {notif.type === 'critical' ? <Clock size={isDropdown ? 16 : 24} /> :
                 notif.type === 'warning' ? <AlertTriangle size={isDropdown ? 16 : 24} /> :
                 notif.type === 'success' ? <CheckCircle2 size={isDropdown ? 16 : 24} /> :
                 <Sparkles size={isDropdown ? 16 : 24} />}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h3 className={`font-black tracking-tight truncate ${isDropdown ? 'text-sm' : 'text-lg'} ${
                    notif.type === 'critical' ? 'text-red-900' :
                    notif.type === 'warning' ? 'text-orange-900' :
                    notif.type === 'success' ? 'text-green-900' :
                    'text-indigo-900'
                  }`}>
                    {notif.title}
                  </h3>
                  <button 
                    onClick={() => onClose(idx)}
                    className="p-1 hover:bg-black/5 rounded-lg transition-colors flex-shrink-0"
                  >
                    <Info size={12} className="opacity-40" />
                  </button>
                </div>
                <p className={`font-medium text-gray-700 leading-relaxed ${isDropdown ? 'text-[11px] line-clamp-2 mb-2' : 'text-sm mb-4'}`}>
                  {notif.message}
                </p>

                {notif.action_label && (
                   <button
                     onClick={() => onAction && onAction(notif.action_id || '')}
                     className={`flex items-center gap-2 rounded-xl font-bold shadow-lg transition-all active:scale-95 ${
                        isDropdown ? 'px-3 py-1.5 text-[10px]' : 'px-5 py-2.5 text-sm'
                     } ${
                        notif.type === 'critical' ? 'bg-red-600 text-white hover:bg-red-700 shadow-red-200' :
                        notif.type === 'warning' ? 'bg-orange-600 text-white hover:bg-orange-700 shadow-orange-200' :
                        notif.type === 'success' ? 'bg-green-600 text-white hover:bg-green-700 shadow-green-200' :
                        'bg-indigo-600 text-white hover:bg-indigo-700 shadow-indigo-200'
                     }`}
                   >
                     {notif.action_label} <ArrowRight size={isDropdown ? 12 : 16} />
                   </button>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
