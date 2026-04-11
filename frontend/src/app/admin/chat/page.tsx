'use client';

import React, { useState, useEffect, useRef } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { chatApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  ArrowRight, 
  Loader2,
  ShieldCheck,
  Terminal,
  Database,
  Search,
  Zap,
  LayoutDashboard,
  ClipboardList,
  AlertTriangle,
  Users
} from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function AdminChat() {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (question: string) => {
    if (!question.trim()) return;
    
    const newMsg: Message = { role: 'user', content: question };
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatApi.adminChat({ 
        user_id: user!.username, 
        question 
      });
      
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: res.data.answer 
      }]);
    } catch (err) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'I encountered an issue accessing the administrative tools. Please try again.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { label: 'Dashboard summary', icon: <LayoutDashboard size={18} /> },
    { label: 'Show pending leaves', icon: <ClipboardList size={18} /> },
    { label: 'Open escalations', icon: <AlertTriangle size={18} /> },
    { label: 'List employees', icon: <Users size={18} /> },
  ];

  return (
    <div className="flex h-screen bg-[#0f172a]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Animated Background Element */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,#1e293b_0%,#0f172a_100%)] z-0" />
        
        {/* Header */}
        <header className="h-20 border-b border-gray-800 bg-gray-900/50 backdrop-blur-xl flex items-center justify-between px-10 relative z-10">
          <div className="flex items-center gap-4">
             <div className="w-10 h-10 bg-indigo-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                <Bot size={24} />
             </div>
             <div>
                <h1 className="text-xl font-black text-white tracking-tight">Admin AI Assistant</h1>
                <div className="flex items-center gap-2">
                   <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                   <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Administrative Access Active</span>
                </div>
             </div>
          </div>
          
          <div className="flex items-center gap-6">
             <div className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded-xl border border-gray-700">
                <Database size={14} className="text-indigo-400" />
                <span className="text-xs font-bold text-gray-300">SQLite Interface</span>
             </div>
             <div className="w-10 h-10 rounded-full border-2 border-gray-700 p-0.5">
                <div className="w-full h-full bg-gray-800 rounded-full flex items-center justify-center text-indigo-400 font-bold">
                   A
                </div>
             </div>
          </div>
        </header>

        {/* Quick Actions Panel */}
        <div className="px-10 pt-8 relative z-10">
           <div className="grid grid-cols-4 gap-6">
              {quickActions.map((action, idx) => (
                <motion.button
                  key={action.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  whileHover={{ y: -4, scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleSend(action.label)}
                  className="flex items-center gap-4 p-5 bg-gray-800/40 border border-gray-700/50 rounded-2xl hover:bg-gray-800 hover:border-indigo-500 transition-all text-left group"
                >
                   <div className="p-3 bg-gray-900 rounded-xl text-indigo-400 group-hover:bg-indigo-500 group-hover:text-white transition-all shadow-xl">
                      {action.icon}
                   </div>
                   <span className="text-sm font-bold text-gray-300 group-hover:text-white transition-colors">
                      {action.label}
                   </span>
                </motion.button>
              ))}
           </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden flex flex-col p-10 pb-6 relative z-10">
           <div 
             ref={scrollRef}
             className="flex-1 overflow-y-auto space-y-8 pr-6 custom-scrollbar-dark"
           >
              {messages.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center text-center opacity-20">
                   <div className="relative mb-8">
                      <Zap size={80} className="text-indigo-500" />
                      <motion.div 
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ repeat: Infinity, duration: 2 }}
                        className="absolute inset-0 bg-indigo-500/20 blur-3xl rounded-full"
                      />
                   </div>
                   <h2 className="text-3xl font-black text-white mb-3 tracking-tighter">Ready for Operations</h2>
                   <p className="max-w-xs text-gray-400 font-medium">Ask about analytics, approvals, or escalations. I have full tool access.</p>
                </div>
              )}
              
              {messages.map((msg, idx) => (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                   <div className={`flex gap-5 max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                      <div className={`w-10 h-10 rounded-2xl flex-shrink-0 flex items-center justify-center text-xs font-bold shadow-2xl ${
                        msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-gray-800 border border-gray-700 text-indigo-400'
                      }`}>
                         {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                      </div>
                      
                      <div className="space-y-3">
                         <div className={`p-6 rounded-3xl text-[15px] leading-relaxed shadow-2xl ${
                           msg.role === 'user' 
                             ? 'bg-indigo-600 text-white rounded-tr-none' 
                             : 'bg-gray-800/80 text-gray-200 border border-gray-700 rounded-tl-none'
                         }`}>
                            {msg.content}
                         </div>
                         
                         {msg.role === 'assistant' && (
                            <div className="flex items-center gap-2 px-2">
                               <div className="w-1 h-1 bg-indigo-500 rounded-full" />
                               <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Admin Logic Verified</span>
                            </div>
                         )}
                      </div>
                   </div>
                </motion.div>
              ))}
              
              {loading && (
                <div className="flex justify-start">
                   <div className="flex gap-5">
                      <div className="w-10 h-10 rounded-2xl bg-gray-800 border border-gray-700 flex items-center justify-center text-indigo-400">
                         <Bot size={20} />
                      </div>
                      <div className="bg-gray-800/80 border border-gray-700 p-6 rounded-3xl rounded-tl-none flex items-center gap-4 shadow-2xl">
                         <div className="flex gap-1.5">
                            <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1 }} className="w-2 h-2 bg-indigo-500 rounded-full" />
                            <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} className="w-2 h-2 bg-indigo-500 rounded-full" />
                            <motion.div animate={{ opacity: [0.3, 1, 0.3] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} className="w-2 h-2 bg-indigo-500 rounded-full" />
                         </div>
                         <span className="text-sm text-gray-400 font-bold uppercase tracking-widest">Accessing Data...</span>
                      </div>
                   </div>
                </div>
              )}
           </div>
        </div>

        {/* Input area */}
        <div className="p-10 pt-4 relative z-10">
           <div className="max-w-5xl mx-auto">
              <div className="relative group">
                 <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-[2.5rem] blur opacity-25 group-focus-within:opacity-50 transition duration-1000 group-hover:duration-200" />
                 <div className="relative flex items-center">
                    <input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
                      placeholder="Enter command or ask a question..."
                      className="w-full bg-gray-900 border border-gray-700 rounded-[2rem] p-6 pr-44 shadow-2xl focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 transition-all text-white font-medium pl-10"
                    />
                    <div className="absolute left-4">
                       <Terminal size={18} className="text-gray-600" />
                    </div>
                    <div className="absolute right-4 flex items-center gap-3">
                       <div className="hidden sm:block text-[9px] font-black text-gray-500 bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700 uppercase tracking-tighter">
                          AUTH: SUDO
                       </div>
                       <button 
                         onClick={() => handleSend(input)}
                         className="p-4 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700 transition-all shadow-xl active:scale-95"
                       >
                          <Send size={20} />
                       </button>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </main>
    </div>
  );
}
