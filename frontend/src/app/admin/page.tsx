'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi, hrApi } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, 
  Clock, 
  AlertCircle, 
  CheckCircle2, 
  XCircle,
  ArrowUpRight,
  TrendingUp,
  Briefcase,
  ExternalLink
} from 'lucide-react';
import { format } from 'date-fns';

interface Stats {
  total_employees: number;
  pending_leaves: number;
  active_escalations: number;
}

interface PendingLeave {
  id: number;
  employee_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  total_days: number;
  reason: string;
  status: string;
  full_name?: string;
  department?: string;
}

interface Escalation {
  id: string; // Unified ID prefixed with WF- or CH-
  db_id: number;
  type: 'workflow' | 'chat';
  source: string;
  employee_id: string;
  description: string;
  query?: string;
  status: string;
  created_at: string;
}

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({ total_employees: 0, pending_leaves: 0, active_escalations: 0 });
  const [pendingLeaves, setPendingLeaves] = useState<PendingLeave[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsRes, leavesRes, escalationsRes] = await Promise.all([
        adminApi.getStats(),
        adminApi.getPendingLeaves(),
        adminApi.getActiveEscalations()
      ]);
      setStats(statsRes.data);
      setPendingLeaves(leavesRes.data || []);
      setEscalations(escalationsRes.data || []);
    } catch (err) {
      console.error('Failed to load admin data', err);
    } finally {
      setLoading(false);
    }
  };

  const processLeave = async (id: number, action: 'approve' | 'reject') => {
    try {
      await adminApi.processLeave(id, action, "Processed via Next.js Admin Portal");
      loadData();
    } catch (err) {
      alert('Failed to process leave');
    }
  };

  const kpiCards = [
    { label: 'Total Employees', value: stats.total_employees, icon: <Users />, color: 'bg-indigo-50 text-indigo-600', trend: '+2% from last month' },
    { label: 'Pending Leaves', value: stats.pending_leaves, icon: <Clock />, color: 'bg-orange-50 text-orange-600', trend: '-5% from last week' },
    { label: 'Active Escalations', value: stats.active_escalations, icon: <AlertCircle />, color: 'bg-red-50 text-red-600', trend: 'Critical attention' },
  ];

  return (
    <div className="flex h-screen bg-[#f1f2f6]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col overflow-y-auto p-8 custom-scrollbar">
        <header className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">🏢 Admin Dashboard</h1>
            <p className="text-gray-500 font-medium mt-1">Real-time overview of HR operations and system health.</p>
          </div>
          <div className="flex gap-3">
             <button className="px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-bold shadow-sm hover:bg-gray-50 transition-all flex items-center gap-2">
               <TrendingUp size={16} /> Reports
             </button>
             <button className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-100 hover:bg-indigo-700 transition-all flex items-center gap-2">
               <Briefcase size={16} /> Hire New
             </button>
          </div>
        </header>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-10">
          {kpiCards.map((card, idx) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              key={card.label}
              className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100/50 group hover:shadow-xl hover:shadow-indigo-900/5 transition-all"
            >
              <div className="flex items-start justify-between mb-6">
                <div className={`p-4 rounded-2xl ${card.color}`}>
                  {React.cloneElement(card.icon as React.ReactElement, { size: 28 })}
                </div>
                <div className="p-2 bg-gray-50 rounded-lg group-hover:bg-indigo-50 transition-colors">
                  <ArrowUpRight size={20} className="text-gray-400 group-hover:text-indigo-500" />
                </div>
              </div>
              <h3 className="text-4xl font-black text-gray-900 mb-1">{card.value}</h3>
              <p className="text-sm font-bold text-gray-400 uppercase tracking-widest">{card.label}</p>
              <div className="mt-6 pt-6 border-t border-gray-50 flex items-center justify-between">
                 <span className="text-xs font-bold text-gray-400">{card.trend}</span>
                 <span className="text-[10px] bg-gray-100 px-2 py-1 rounded text-gray-500 font-black uppercase tracking-tighter">View Detail</span>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Main Section */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* Pending Approvals List */}
          <section className="xl:col-span-2 bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col min-h-[500px]">
             <div className="flex items-center justify-between mb-8">
                <h2 className="text-xl font-bold flex items-center gap-2">
                   <Clock className="text-orange-500" /> Pending Leave Approvals
                </h2>
                <button className="text-indigo-600 text-sm font-bold hover:underline flex items-center gap-1">
                   View all <ExternalLink size={14} />
                </button>
             </div>

             <div className="flex-1 space-y-4">
                {pendingLeaves.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center opacity-40 py-20">
                     <CheckCircle2 size={48} className="text-green-500 mb-4" />
                     <p className="text-gray-500 font-bold">All caught up! No pending requests.</p>
                  </div>
                ) : (
                  pendingLeaves.map((req) => (
                    <motion.div 
                      layout
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      key={req.id}
                      className="p-6 bg-gray-50 rounded-2xl border border-gray-100 flex items-center justify-between group hover:bg-white hover:shadow-lg transition-all"
                    >
                       <div className="flex items-center gap-4">
                          <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-indigo-600 font-black">
                            {(req.full_name || req.employee_id).substring(0, 2)}
                          </div>
                          <div>
                             <h4 className="font-bold text-gray-900">{req.full_name || req.employee_id}</h4>
                             <p className="text-[10px] text-indigo-600 font-black uppercase tracking-widest">{req.department || 'Employee'}</p>
                             <p className="text-xs text-gray-500 font-medium mt-1">
                                {req.leave_type.toUpperCase()} • {req.total_days} Days ({format(new Date(req.start_date), 'MMM dd')} - {format(new Date(req.end_date), 'MMM dd')})
                             </p>
                             <p className="text-[11px] text-gray-400 italic mt-1 italic">"{req.reason}"</p>
                          </div>
                       </div>
                       
                       <div className="flex items-center gap-2">
                          <button 
                            onClick={() => processLeave(req.id, 'reject')}
                            className="p-3 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                          >
                             <XCircle size={22} />
                          </button>
                          <button 
                            onClick={() => processLeave(req.id, 'approve')}
                            className="p-3 text-gray-400 hover:text-green-500 hover:bg-green-50 rounded-xl transition-all"
                          >
                             <CheckCircle2 size={22} />
                          </button>
                       </div>
                    </motion.div>
                  ))
                )}
             </div>
          </section>

          {/* Quick Actions / System Status */}
          <aside className="space-y-8">
             <div className="bg-indigo-600 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
                <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-indigo-500 rounded-full blur-3xl opacity-50" />
                <div className="relative z-10">
                   <h3 className="text-xl font-bold mb-4">Quick Insights</h3>
                   <div className="space-y-6">
                      <div className="flex items-center gap-4">
                         <div className="w-10 h-10 bg-indigo-500/50 rounded-xl flex items-center justify-center">
                            <TrendingUp size={20} />
                         </div>
                         <div>
                            <p className="text-[10px] text-indigo-200 font-bold uppercase tracking-widest">Efficiency</p>
                            <p className="text-sm font-bold">94% response rate today</p>
                         </div>
                      </div>
                      <button className="w-full bg-white text-indigo-600 p-4 rounded-2xl font-bold hover:bg-indigo-50 transition-all text-sm shadow-lg">
                         Run System Audit
                      </button>
                   </div>
                </div>
             </div>
             
             <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col">
                 <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-red-50 text-red-500 rounded-xl flex items-center justify-center">
                       <AlertCircle size={20} />
                    </div>
                    <h3 className="text-lg font-bold">Active Escalations</h3>
                 </div>
                 
                 <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {escalations.length === 0 ? (
                      <p className="text-xs text-gray-400 text-center py-10 font-bold">No active escalations.</p>
                    ) : (
                      escalations.map((esc) => (
                        <div key={esc.id} className="p-4 bg-gray-50 rounded-2xl border border-gray-100 hover:border-red-100 transition-all">
                           <div className="flex items-center justify-between mb-2">
                              <span className={`text-[9px] px-2 py-0.5 rounded font-black uppercase tracking-widest ${
                                esc.type === 'chat' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                              }`}>
                                {esc.type === 'chat' ? 'SENSITIVE AI' : 'STALE WORKFLOW'}
                              </span>
                              <span className="text-[10px] text-gray-400 font-bold">#{esc.db_id}</span>
                           </div>
                           <p className="text-xs font-bold text-gray-900 mb-1">{esc.source}</p>
                           <p className="text-[11px] text-gray-500 line-clamp-2">{esc.description}</p>
                           {esc.query && (
                             <p className="text-[10px] text-gray-400 mt-2 bg-white/50 p-2 rounded-lg border border-gray-50 italic">"{esc.query}"</p>
                           )}
                           <div className="mt-3 pt-3 border-t border-gray-50 flex items-center justify-between">
                              <span className="text-[9px] text-gray-400 font-bold italic">{format(new Date(esc.created_at), 'MMM dd, HH:mm')}</span>
                              <Link href="/admin/escalations" className="text-[10px] text-indigo-600 font-black hover:underline">Review Details</Link>
                           </div>
                        </div>
                      ))
                    )}
                 </div>
             </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
