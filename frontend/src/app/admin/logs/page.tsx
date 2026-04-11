'use client';

import React, { useState, useEffect } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  Filter, 
  User, 
  MessageSquare, 
  Calendar,
  MessageCircle,
  MoreVertical,
  Terminal,
  Activity,
  History
} from 'lucide-react';
import { format } from 'date-fns';

interface Log {
  id: number;
  user: string;
  question: string;
  answer: string;
  timestamp: string;
}

export default function QueryLogs() {
  const [logs, setLogs] = useState<Log[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedLog, setSelectedLog] = useState<Log | null>(null);

  useEffect(() => {
    loadLogs();
  }, []);

  const loadLogs = async () => {
    try {
      const res = await adminApi.getLogs();
      setLogs(res.data);
    } catch (err) {
      console.error('Failed to load logs', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredLogs = logs.filter(l => 
    l.user.toLowerCase().includes(search.toLowerCase()) || 
    l.question.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-[#f1f2f6]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col p-8 overflow-hidden">
        <header className="mb-10 flex items-center justify-between">
           <div>
              <h1 className="text-3xl font-black text-gray-900 tracking-tight">📜 Query Logs & Monitoring</h1>
              <p className="text-gray-500 font-medium mt-1">Review user interactions and AI performance across the system.</p>
           </div>
           <div className="flex items-center gap-4 py-2 px-6 bg-white border border-gray-200 rounded-2xl shadow-sm">
              <Activity size={20} className="text-indigo-600" />
              <div className="text-[10px] font-black text-gray-400 leading-tight uppercase tracking-widest">
                 Live Feed • Active
              </div>
           </div>
        </header>

        <div className="flex-[1] flex gap-8 min-h-0">
           {/* Table Section */}
           <section className="flex-[3] bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col">
              <div className="flex items-center justify-between mb-8 gap-4">
                 <div className="relative flex-1 group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-500 transition-colors" size={20} />
                    <input 
                      type="text" 
                      placeholder="Search logs by user or query..." 
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full bg-gray-50 border border-transparent rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:bg-white focus:border-indigo-400 transition-all font-medium text-sm"
                    />
                 </div>
                 <button className="p-4 bg-gray-50 rounded-2xl text-gray-400 hover:text-indigo-600 transition-all">
                    <Filter size={20} />
                 </button>
              </div>

              <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                 {loading ? (
                    <div className="h-full flex items-center justify-center">
                       <Terminal className="animate-pulse text-indigo-200 w-16 h-16" />
                    </div>
                 ) : filteredLogs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-20">
                       <History size={64} className="mb-4" />
                       <p className="font-black text-xl">NO RECORDS</p>
                    </div>
                 ) : (
                    <div className="space-y-3">
                       {filteredLogs.map((log) => (
                          <motion.div
                            key={log.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            onClick={() => setSelectedLog(log)}
                            className={`p-5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                              selectedLog?.id === log.id 
                                ? 'bg-indigo-50 border-indigo-200 shadow-md translate-x-2' 
                                : 'bg-gray-50 border-transparent hover:border-gray-200 hover:bg-white hover:shadow-lg'
                            }`}
                          >
                             <div className="flex items-center gap-6">
                                <div className="p-3 bg-white rounded-xl shadow-sm group-hover:bg-indigo-600 group-hover:text-white transition-all text-gray-400 flex items-center justify-center">
                                   <User size={18} />
                                </div>
                                <div className="space-y-1">
                                   <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{log.user}</p>
                                   <p className="text-sm font-bold text-gray-900 group-hover:text-indigo-600 transition-all max-w-[400px] truncate">{log.question}</p>
                                </div>
                             </div>
                             <div className="flex items-center gap-6 text-right">
                                <div>
                                   <p className="text-[10px] font-black text-gray-400 uppercase tracking-tight">{format(new Date(log.timestamp), 'MMM dd, HH:mm')}</p>
                                   <p className="text-[10px] font-bold text-indigo-400 uppercase mt-1">SUCCESS</p>
                                </div>
                                <MoreVertical size={18} className="text-gray-300" />
                             </div>
                          </motion.div>
                       ))}
                    </div>
                 )}
              </div>
           </section>

           {/* Inspector Section */}
           <aside className="flex-[2] bg-gray-900 rounded-3xl p-8 text-white shadow-2xl flex flex-col overflow-hidden">
              <AnimatePresence mode="wait">
                 {selectedLog ? (
                    <motion.div
                       key={selectedLog.id}
                       initial={{ opacity: 0, x: 20 }}
                       animate={{ opacity: 1, x: 0 }}
                       exit={{ opacity: 0, x: -20 }}
                       className="flex-1 flex flex-col h-full"
                    >
                       <div className="flex items-start justify-between mb-10">
                          <div className="flex items-center gap-4">
                             <div className="p-3 bg-indigo-500 rounded-2xl">
                                <MessageCircle size={28} />
                             </div>
                             <div>
                                <h3 className="text-xl font-bold">Query Explorer</h3>
                                <p className="text-xs text-indigo-300 font-bold uppercase tracking-widest">Metadata Loaded</p>
                             </div>
                          </div>
                          <button onClick={() => setSelectedLog(null)} className="text-gray-500 hover:text-white pb-3">
                             Close
                          </button>
                       </div>

                       <div className="space-y-10 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                          <div>
                             <p className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-4">The Question</p>
                             <div className="bg-gray-800 p-6 rounded-2xl border border-gray-700/50">
                                <p className="text-sm leading-relaxed font-bold italic opacity-90">"{selectedLog.question}"</p>
                             </div>
                          </div>

                          <div>
                             <p className="text-[10px] font-black text-green-400 uppercase tracking-[0.2em] mb-4">The Answer</p>
                             <div className="bg-gray-800/50 p-6 rounded-2xl border border-indigo-500/10">
                                <p className="text-sm leading-relaxed opacity-80 whitespace-pre-wrap">{selectedLog.answer}</p>
                             </div>
                          </div>

                          <div className="grid grid-cols-2 gap-4">
                             <div className="bg-indigo-600/10 p-4 rounded-xl border border-indigo-500/20">
                                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">Latency</p>
                                <p className="text-lg font-black">1.2s</p>
                             </div>
                             <div className="bg-indigo-600/10 p-4 rounded-xl border border-indigo-500/20">
                                <p className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-1">Tokens</p>
                                <p className="text-lg font-black">~432</p>
                             </div>
                          </div>
                       </div>
                    </motion.div>
                 ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center opacity-30">
                       <Terminal size={48} className="mb-6" />
                       <h3 className="text-xl font-bold mb-2">Inspector Inactive</h3>
                       <p className="text-sm max-w-[200px]">Select a log record from the entries to inspect detailed data flows.</p>
                    </div>
                 )}
              </AnimatePresence>
           </aside>
        </div>
      </main>
    </div>
  );
}
