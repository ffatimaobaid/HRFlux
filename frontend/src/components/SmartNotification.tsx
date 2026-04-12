
'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  AlertTriangle,
  Info,
  CheckCircle2,
  Clock,
  X,
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

  const getTheme = (type: string) => {
    switch (type) {
      case 'critical': return { bg: 'bg-red-500/10', border: 'border-red-500/20', icon: 'bg-red-500', text: 'text-red-900', shadow: 'shadow-red-500/10', glow: 'bg-red-500' };
      case 'warning': return { bg: 'bg-orange-500/10', border: 'border-orange-500/20', icon: 'bg-orange-500', text: 'text-orange-900', shadow: 'shadow-orange-500/10', glow: 'bg-orange-500' };
      case 'success': return { bg: 'bg-green-500/10', border: 'border-green-500/20', icon: 'bg-green-500', text: 'text-green-900', shadow: 'shadow-green-500/10', glow: 'bg-green-500' };
      default: return { bg: 'bg-indigo-500/10', border: 'border-indigo-500/20', icon: 'bg-[#7b2ff7]', text: 'text-indigo-950', shadow: 'shadow-indigo-500/10', glow: 'bg-[#904df9]' };
    }
  };

  return (
    <div className={`w-full ${isDropdown ? 'max-h-[70vh] overflow-y-auto px-1' : 'space-y-4 mb-6'}`}>
      <style>{`
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .shimmer-effect {
          position: relative;
          overflow: hidden;
        }
        .shimmer-effect::after {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 50%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
          transform: skewX(-20deg);
          animation: shimmer 3s infinite linear;
        }
      `}</style>
      
      <AnimatePresence>
        {notifications.map((notif, idx) => {
          const theme = getTheme(notif.type);
          return (
            <motion.div
              key={`${notif.title}-${idx}`}
              layout
              initial={{ opacity: 0, x: isDropdown ? 20 : -30, scale: 0.9 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8, x: 20 }}
              whileHover={!isDropdown ? { y: -5, scale: 1.02, rotateX: 2, rotateY: -2 } : {}}
              transition={{ type: 'spring', damping: 20, stiffness: 300 }}
              className={`relative overflow-hidden group backdrop-blur-xl ${
                isDropdown 
                  ? 'p-4 border-b border-gray-100 last:border-0 hover:bg-gray-50/80 transition-colors' 
                  : `rounded-[2.5rem] p-8 shadow-2xl border ${theme.border} ${theme.bg} ${theme.shadow} shimmer-effect`
              }`}
            >
              {/* Liquid Blobs - Creative Background */}
              {!isDropdown && (
                <>
                  <motion.div 
                    animate={{ x: [0, 20, 0], y: [0, -20, 0] }}
                    transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
                    className={`absolute -right-16 -top-16 w-48 h-48 rounded-full blur-[64px] opacity-30 ${theme.glow}`} 
                  />
                  <motion.div 
                    animate={{ x: [0, -30, 0], y: [0, 40, 0] }}
                    transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                    className={`absolute -left-20 -bottom-20 w-64 h-64 rounded-full blur-[80px] opacity-20 ${theme.glow}`} 
                  />
                </>
              )}

              <div className={`relative z-10 flex items-start ${isDropdown ? 'gap-3' : 'gap-6'}`}>
                {/* Animated Icon Container */}
                <motion.div 
                  initial={{ rotate: -20, scale: 0 }}
                  animate={{ rotate: 0, scale: 1 }}
                  transition={{ delay: 0.1 }}
                  className={`rounded-2xl flex items-center justify-center shrink-0 ${isDropdown ? 'p-2' : 'p-4 shadow-xl group-hover:scale-110 group-hover:rotate-12 transition-all duration-300'} ${theme.icon} text-white`}
                >
                  {notif.type === 'critical' ? <Clock size={isDropdown ? 16 : 24} className="animate-pulse" /> :
                   notif.type === 'warning' ? <AlertTriangle size={isDropdown ? 16 : 24} /> :
                   notif.type === 'success' ? <CheckCircle2 size={isDropdown ? 16 : 24} /> :
                   <Sparkles size={isDropdown ? 16 : 24} />}
                </motion.div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <motion.h3 
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 }}
                      className={`font-black tracking-tight truncate ${isDropdown ? 'text-xs' : 'text-lg'} ${theme.text}`}
                    >
                      {notif.title}
                    </motion.h3>
                    <button
                      onClick={() => onClose(idx)}
                      className="p-1.5 hover:bg-black/5 rounded-xl transition-all duration-200 flex-shrink-0 group/close"
                    >
                      <X size={14} className="opacity-40 group-hover/close:opacity-100 group-hover/close:scale-110 transition-all" />
                    </button>
                  </div>

                  <motion.p 
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className={`font-medium ${isDropdown ? 'text-[10px] text-gray-500 line-clamp-2' : 'text-sm text-gray-700 leading-relaxed mb-4 opacity-80'}`}
                  >
                    {notif.message}
                  </motion.p>

                  {notif.action_label && (
                     <motion.button
                       initial={{ opacity: 0, scale: 0.9 }}
                       animate={{ opacity: 1, scale: 1 }}
                       transition={{ delay: 0.4 }}
                       onClick={() => onAction && onAction(notif.action_id || '')}
                       className={`flex items-center gap-2 rounded-2xl font-black shadow-lg shadow-black/5 transition-all active:scale-95 group/btn ${
                          isDropdown ? 'px-3 py-1.5 text-[10px]' : 'px-6 py-3 text-sm'
                       } ${
                          notif.type === 'critical' ? 'bg-red-600 text-white hover:bg-red-700' :
                          notif.type === 'warning' ? 'bg-orange-600 text-white hover:bg-orange-700' :
                          notif.type === 'success' ? 'bg-green-600 text-white hover:bg-green-700' :
                          'bg-[#7b2ff7] text-white hover:bg-[#5b1ab5]'
                       }`}
                     >
                       {notif.action_label} 
                       <ArrowRight size={isDropdown ? 12 : 16} className="group-hover/btn:translate-x-1 transition-transform" />
                     </motion.button>
                  )}
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
