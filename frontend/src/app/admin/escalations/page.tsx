'use client';

import React, { useState, useEffect } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AlertTriangle, 
  MessageSquare, 
  Clock, 
  User, 
  CheckCircle2, 
  XSquare,
  ShieldAlert,
  ChevronRight,
  Info
} from 'lucide-react';
import { format } from 'date-fns';

interface Escalation {
  id: string;
  db_id: number;
  type: 'workflow' | 'chat';
  source: string;
  employee_id: string;
  description: string;
  query?: string;
  status: string;
  created_at: string;
  sensitivity_score?: number;
  full_history?: string;
  username?: string; // for compatibility with chat fields
}

export default function EscalationsPage() {
  const [allEscalations, setAllEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'chat' | 'workflow'>('chat');
  const [resolutionNote, setResolutionNote] = useState('');
  const [selectedEsc, setSelectedEsc] = useState<Escalation | null>(null);

  useEffect(() => {
    loadEscalations();
  }, []);

  const loadEscalations = async () => {
    setLoading(true);
    try {
      // Use the unified active-escalations endpoint
      const res = await adminApi.getActiveEscalations();
      // Ensure we map fields consistently for the UI
      const mapped = res.data.map((e: any) => ({
        ...e,
        username: e.source // UI uses 'username' in some places
      }));
      setAllEscalations(mapped);
    } catch (err) {
      console.error('Failed to load escalations', err);
    } finally {
      setLoading(false);
    }
  };

  const resolveEscalation = async (id: string, db_id: number, type: 'chat' | 'workflow') => {
    if (!resolutionNote) return alert('Please enter a resolution note.');
    try {
      if (type === 'chat') {
        await adminApi.resolveChatEscalation(db_id, resolutionNote);
      } else {
        await adminApi.resolveWorkflowEscalation(db_id, resolutionNote);
      }
      setResolutionNote('');
      setSelectedEsc(null);
      loadEscalations();
    } catch (err) {
      alert('Failed to resolve escalation');
    }
  };

  // Filter based on tab
  const filteredEscalations = allEscalations.filter(e => e.type === activeTab);

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col p-8 overflow-hidden">
        <header className="mb-10 flex items-center justify-between">
           <div>
              <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">🚨 Escalation Management</h1>
              <p className="text-gray-500 font-medium mt-1">Review and resolve critical system alerts and sensitive queries.</p>
           </div>
           <div className="flex bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100">
              <button 
                onClick={() => setActiveTab('workflow')}
                className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'workflow' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:bg-gray-50'}`}
              >
                📜 Workflow
              </button>
              <button 
                onClick={() => setActiveTab('chat')}
                className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'chat' ? 'bg-indigo-600 text-white shadow-lg' : 'text-gray-500 hover:bg-gray-50'}`}
              >
                💬 Sensitive Queries
              </button>
           </div>
        </header>

        <div className="flex-1 flex gap-8 min-h-0">
           {/* Alerts List */}
           <section className="flex-1 bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col">
              <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                 <AnimatePresence mode="popLayout">
                    {loading ? (
                       <div className="h-full flex items-center justify-center text-gray-300">
                          <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 2 }}>
                             <ShieldAlert size={48} />
                          </motion.div>
                       </div>
                    ) : filteredEscalations.length === 0 ? (
                       <div className="h-full flex flex-col items-center justify-center opacity-30 text-center py-20">
                          <CheckCircle2 size={64} className="text-green-500 mb-4" />
                          <p className="font-bold text-gray-900">NO PENDING ISSUES</p>
                          <p className="text-xs text-gray-500 max-w-[200px] mt-2">All system escalations have been resolved.</p>
                       </div>
                    ) : (
                       filteredEscalations.map((esc) => (
                          <motion.div
                            key={esc.id}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            onClick={() => setSelectedEsc(esc)}
                            className={`p-5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                              selectedEsc?.id === esc.id 
                                ? 'bg-red-50 border-red-200' 
                                : 'bg-gray-50 border-gray-100 hover:border-indigo-200 hover:bg-white hover:shadow-xl hover:shadow-indigo-900/5'
                            }`}
                          >
                             <div className="flex items-center gap-4">
                                <div className={`p-3 rounded-xl transition-all ${
                                   selectedEsc?.id === esc.id ? 'bg-red-500 text-white shadow-lg shadow-red-200' : 'bg-white text-orange-500 shadow-sm'
                                }`}>
                                   <AlertTriangle size={20} />
                                </div>
                                <div>
                                   <h4 className="font-bold text-sm text-gray-900">{esc.description}</h4>
                                   <div className="flex gap-3 mt-1">
                                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-tight flex items-center gap-1">
                                         <User size={10} /> {esc.username}
                                      </span>
                                      <span className="text-[10px] font-bold text-red-400 uppercase tracking-tight flex items-center gap-1">
                                         <Clock size={10} /> {format(new Date(esc.created_at), 'MM-dd HH:mm')}
                                      </span>
                                   </div>
                                </div>
                             </div>
                             <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                                selectedEsc?.id === esc.id ? 'bg-red-500 text-white' : 'bg-white border border-gray-100 text-gray-300'
                             }`}>
                                <ChevronRight size={16} />
                             </div>
                          </motion.div>
                       ))
                    )}
                 </AnimatePresence>
              </div>
           </section>

           {/* Resolution Inspector */}
           <aside className="w-[450px] bg-white rounded-3xl shadow-2xl border border-gray-100 flex flex-col overflow-hidden">
              <AnimatePresence mode="wait">
                 {selectedEsc ? (
                    <motion.div
                       key={selectedEsc.id}
                       initial={{ opacity: 0, scale: 0.98 }}
                       animate={{ opacity: 1, scale: 1 }}
                       exit={{ opacity: 0, scale: 0.95 }}
                       className="flex-1 flex flex-col"
                    >
                       {/* Header */}
                       <div className="p-8 bg-gray-900 text-white">
                          <div className="flex items-center justify-between mb-6">
                             <div className="bg-red-500 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest leading-none">
                                {selectedEsc.type === 'chat' ? 'SENSITIVE AI' : 'STALE FLOW'}
                             </div>
                             <span className="text-xs font-black text-gray-500">
                                {selectedEsc.type === 'chat' ? `SCORE: ${selectedEsc.sensitivity_score?.toFixed(2)}` : 'PRIORITY: HIGH'}
                             </span>
                          </div>
                          <h3 className="text-xl font-bold mb-2">{selectedEsc.description}</h3>
                          <p className="text-xs text-gray-400 font-medium">Issue reported at {format(new Date(selectedEsc.created_at), 'MMM dd, HH:mm')}</p>
                       </div>

                       {/* Content */}
                       <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar">
                          {selectedEsc.type === 'chat' && (
                             <div>
                                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3">User Query</p>
                                <div className="bg-red-50 p-4 rounded-2xl border border-red-100 text-sm font-bold text-red-900 italic">
                                   "{selectedEsc.query}"
                                </div>
                             </div>
                          )}

                          {selectedEsc.type === 'chat' && (
                             <div>
                                <div className="flex items-center justify-between mb-3">
                                   <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Conversation Context</p>
                                   <MessageSquare size={14} className="text-gray-300" />
                                </div>
                                <div className="bg-gray-50 p-6 rounded-2xl border border-gray-100 text-xs font-medium text-gray-600 leading-relaxed whitespace-pre-wrap max-h-[250px] overflow-y-auto custom-scrollbar">
                                   {selectedEsc.full_history}
                                </div>
                             </div>
                          )}

                          <div className="pt-4 border-t border-gray-100">
                             <label className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-3 block">Resolution Notes</label>
                             <textarea 
                                value={resolutionNote}
                                onChange={(e) => setResolutionNote(e.target.value)}
                                placeholder="State actions taken or system update notes..."
                                className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-4 focus:ring-red-100 focus:border-red-400 transition-all text-sm font-medium min-h-[120px]"
                             />
                          </div>
                       </div>

                       {/* Action */}
                       <div className="p-8 pt-4 flex gap-4">
                          <button 
                            onClick={() => setSelectedEsc(null)}
                            className="flex-1 p-4 bg-gray-100 text-gray-600 font-bold rounded-2xl hover:bg-gray-200 transition-all"
                          >
                             Back
                          </button>
                          <button 
                             onClick={() => resolveEscalation(selectedEsc.id, selectedEsc.db_id, selectedEsc.type)}
                             className="flex-[2] p-4 bg-indigo-600 text-white font-bold rounded-2xl shadow-lg shadow-indigo-100 hover:bg-indigo-700 transition-all flex items-center justify-center gap-2"
                           >
                             <CheckCircle2 size={18} /> Resolve Issue
                          </button>
                       </div>
                    </motion.div>
                 ) : (
                    <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-20">
                       <ShieldAlert size={64} className="mb-6" />
                       <h3 className="text-xl font-bold">No Escalation Selected</h3>
                       <p className="text-sm mt-2">Pick an alert from the list to view full context and sensitivity analysis.</p>
                       <div className="mt-8 flex gap-2">
                          <div className="w-2 h-2 rounded-full bg-gray-400" />
                          <div className="w-2 h-2 rounded-full bg-gray-400" />
                          <div className="w-2 h-2 rounded-full bg-gray-400" />
                       </div>
                    </div>
                 )}
              </AnimatePresence>
           </aside>
        </div>
      </main>
    </div>
  );
}
