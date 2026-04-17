'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi, hrApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
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
  ExternalLink,
  Bot
} from 'lucide-react';
import { format } from 'date-fns';
import { Button, Modal, Input as AntInput, Select, App } from 'antd';
import { Megaphone } from 'lucide-react';

interface Stats {
  total_employees: number;
  pending_leaves: number;
  active_escalations: number;
  avg_resolution_time: number;
  resolution_rate: number;
  hr_hours_saved: number;
  avg_escalation_time: number;
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
  conversation_summary?: string;
}

export default function AdminDashboard() {
  const { user, loading: authLoading } = useAuth();

  // Strict lockdown: Never show admin dashboard to an employee
  if (authLoading || (user && user.role !== 'admin')) {
    return <div className="h-screen bg-[#f1f2f6] flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-[#7b2ff7] border-t-transparent rounded-full animate-spin" />
    </div>;
  }

  const [stats, setStats] = useState<Stats>({
    total_employees: 0,
    pending_leaves: 0,
    active_escalations: 0,
    avg_resolution_time: 0,
    resolution_rate: 0,
    hr_hours_saved: 0,
    avg_escalation_time: 0
  });
  const [pendingLeaves, setPendingLeaves] = useState<PendingLeave[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);

  // Announcement state
  const [isAnnModalOpen, setIsAnnModalOpen] = useState(false);
  const [annTitle, setAnnTitle] = useState('');
  const [annContent, setAnnContent] = useState('');
  const [annPriority, setAnnPriority] = useState('medium');
  const [publishing, setPublishing] = useState(false);

  const { message } = App.useApp();

  // Leave processing state
  const [isProcessModalOpen, setIsProcessModalOpen] = useState(false);
  const [currentLeave, setCurrentLeave] = useState<PendingLeave | null>(null);
  const [processAction, setProcessAction] = useState<'approve' | 'reject'>('approve');
  const [processReason, setProcessReason] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);

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

  const handleProcessClick = (leave: PendingLeave, action: 'approve' | 'reject') => {
    setCurrentLeave(leave);
    setProcessAction(action);
    setProcessReason('');
    setIsProcessModalOpen(true);
  };

  const submitProcessLeave = async () => {
    if (!currentLeave) return;
    if (!processReason.trim()) {
      message.error("Please provide a reason/comment for this action");
      return;
    }

    setIsProcessing(true);
    try {
      await adminApi.processLeave(currentLeave.id, processAction, processReason);
      message.success(`Leave request ${processAction}d successfully`);
      setIsProcessModalOpen(false);
      loadData();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || `Failed to ${processAction} leave`;
      message.error(errorMsg);
    } finally {
      setIsProcessing(false);
    }
  };

  const publishAnnouncement = async () => {
    if (!annTitle || !annContent) {
      message.error("Please fill in both title and content");
      return;
    }
    setPublishing(true);
    try {
      await adminApi.createAnnouncement({
        title: annTitle,
        content: annContent,
        priority: annPriority
      });
      message.success("Announcement broadcasted successfully!");
      setIsAnnModalOpen(false);
      setAnnTitle('');
      setAnnContent('');
    } catch (err) {
      message.error("Failed to broadcast announcement");
    } finally {
      setPublishing(false);
    }
  };

  const kpiCards = [
    { label: 'Total Employees', value: stats.total_employees, icon: <Users />, color: 'bg-[#f4effc] text-[#7b2ff7]', trend: '+2% from last month' },
    { label: 'Resolution Rate', value: `${stats.resolution_rate}%`, icon: <CheckCircle2 />, color: 'bg-green-50 text-green-600', trend: 'Global efficiency' },
    { label: 'Avg Resolution', value: `${stats.avg_resolution_time}d`, icon: <Clock />, color: 'bg-[#f4effc] text-[#7b2ff7]', trend: 'Target: < 2.0d' },
    { label: 'HR Hours Saved', value: stats.hr_hours_saved, icon: <TrendingUp />, color: 'bg-orange-50 text-orange-600', trend: 'AI productivity impact' },
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
            <Button
              type="primary"
              size="large"
              className="font-bold rounded-xl shadow-md bg-orange-500 hover:bg-orange-600 border-none"
              icon={<Megaphone size={16} />}
              onClick={() => setIsAnnModalOpen(true)}
            >
              Broadcast
            </Button>
          </div>
        </header>

        {/* KPI Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-10">
          {kpiCards.map((card, idx) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              key={card.label}
              className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100/50 group hover:shadow-xl hover:shadow-[#3E1287]/5 transition-all"
            >
              <div className="flex items-start justify-between mb-6">
                <div className={`p-4 rounded-2xl ${card.color}`}>
                  {React.cloneElement(card.icon as React.ReactElement<any>, { size: 28 })}
                </div>
                <div className="p-2 bg-gray-50 rounded-lg group-hover:bg-[#f4effc] transition-colors">
                  <ArrowUpRight size={20} className="text-gray-400 group-hover:text-[#904df9]" />
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
              <button className="text-[#7b2ff7] text-sm font-bold hover:underline flex items-center gap-1">
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
                      <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-[#7b2ff7] font-black">
                        {(req.full_name || req.employee_id).substring(0, 2)}
                      </div>
                      <div>
                        <h4 className="font-bold text-gray-900">{req.full_name || req.employee_id}</h4>
                        <p className="text-[10px] text-[#7b2ff7] font-black uppercase tracking-widest">{req.department || 'Employee'}</p>
                        <p className="text-xs text-gray-500 font-medium mt-1">
                          {req.leave_type.toUpperCase()} • {req.total_days} Days ({format(new Date(req.start_date), 'MMM dd')} - {format(new Date(req.end_date), 'MMM dd')})
                        </p>
                        <p className="text-[11px] text-gray-400 italic mt-1 italic">"{req.reason}"</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleProcessClick(req, 'reject')}
                        className="p-3 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                      >
                        <XCircle size={22} />
                      </button>
                      <button
                        onClick={() => handleProcessClick(req, 'approve')}
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
            <div className="bg-[#7b2ff7] rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
              <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-[#f4effc]0 rounded-full blur-3xl opacity-50" />
              <div className="relative z-10">
                <h3 className="text-xl font-bold mb-4">Quick Insights</h3>
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-[#f4effc]0/50 rounded-xl flex items-center justify-center">
                      <TrendingUp size={20} />
                    </div>
                    <div>
                      <p className="text-[10px] text-indigo-200 font-bold uppercase tracking-widest">Efficiency</p>
                      <p className="text-sm font-bold">94% response rate today</p>
                    </div>
                  </div>
                  <button className="w-full bg-white text-[#7b2ff7] p-4 rounded-2xl font-bold hover:bg-[#f4effc] transition-all text-sm shadow-lg">
                    Run System Audit
                  </button>
                </div>
              </div>
            </div>

            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/5 blur-[50px] rounded-full pointer-events-none" />
              <div className="flex items-center justify-between mb-6 relative z-10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-red-50 to-orange-50 text-red-500 rounded-xl flex items-center justify-center shadow-sm border border-red-100">
                    <AlertCircle size={20} />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">Priority Escalations</h3>
                    <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wider mt-0.5">Needs immediate action</p>
                  </div>
                </div>
                {escalations.length > 0 && (
                  <span className="bg-red-100 text-red-600 text-xs font-black px-2.5 py-1 rounded-lg">
                    {escalations.length} Active
                  </span>
                )}
              </div>

              <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar relative z-10">
                {escalations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-10 opacity-60">
                    <CheckCircle2 size={32} className="text-green-500 mb-3" />
                    <p className="text-xs text-gray-500 font-bold uppercase tracking-widest">No active escalations</p>
                  </div>
                ) : (
                  escalations.map((esc) => (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      key={esc.id}
                      className="group relative p-5 bg-white rounded-2xl border border-gray-100 hover:border-red-200 shadow-sm hover:shadow-md hover:shadow-red-900/5 transition-all duration-300"
                    >
                      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-0 bg-red-500 rounded-r-full group-hover:h-3/4 transition-all duration-300" />
                      <div className="flex items-start justify-between mb-3">
                        <span className={`text-[10px] px-2.5 py-1 rounded-lg font-bold flex items-center gap-1.5 shadow-sm border ${esc.type === 'chat'
                          ? 'bg-red-50 text-red-600 border-red-100'
                          : 'bg-orange-50 text-orange-600 border-orange-100'
                          }`}>
                          {esc.type === 'chat' ? <Bot size={12} /> : <Clock size={12} />}
                          {esc.type === 'chat' ? 'SENSITIVE AI' : 'STALE WORKFLOW'}
                        </span>
                        <span className="text-[10px] text-gray-400 font-bold bg-gray-50 px-2 py-0.5 rounded-md border border-gray-100">ID: {esc.db_id}</span>
                      </div>

                      <h4 className="text-sm font-bold text-gray-900 mb-1 group-hover:text-red-600 transition-colors">{esc.source}</h4>
                      <p className="text-[12px] text-gray-600 line-clamp-2 leading-relaxed mb-4">{esc.description}</p>

                      <div className="mt-4 pt-4 border-t border-gray-50 flex items-center justify-between">
                        <span className="text-[10px] text-gray-500 font-medium bg-gray-50 px-2 py-1 rounded-md border border-gray-100">
                          {format(new Date(esc.created_at), 'MMM dd, HH:mm')}
                        </span>
                        <Link
                          href="/admin/escalations"
                          className="flex items-center gap-1 text-[11px] text-[#7b2ff7] bg-[#f4effc] px-3 py-1.5 rounded-lg font-bold group-hover:bg-[#7b2ff7] group-hover:text-white transition-all shadow-sm"
                        >
                          View Details <ArrowUpRight size={12} className="opacity-70" />
                        </Link>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>

        {/* Leave Processing Modal */}
        <Modal
          title={<div className="flex items-center gap-2 text-xl font-black italic uppercase tracking-tight text-gray-900">
            {processAction === 'approve' ? <CheckCircle2 className="text-green-500" /> : <XCircle className="text-red-500" />}
            {processAction} Leave Request
          </div>}
          open={isProcessModalOpen}
          onCancel={() => setIsProcessModalOpen(false)}
          onOk={submitProcessLeave}
          confirmLoading={isProcessing}
          okText={processAction === 'approve' ? "Confirm Approval" : "Confirm Rejection"}
          okButtonProps={{
            className: `rounded-xl font-bold h-10 ${processAction === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`,
            danger: processAction === 'reject'
          }}
          cancelButtonProps={{ className: 'rounded-xl font-bold h-10' }}
          centered
          width={500}
        >
          <div className="py-4 space-y-4">
            {currentLeave && (
              <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100 mb-4">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Applying Employee</p>
                <p className="font-bold text-gray-900">{currentLeave.full_name || currentLeave.employee_id}</p>
                <p className="text-xs text-gray-500">{currentLeave.leave_type} ({currentLeave.total_days} days)</p>
              </div>
            )}
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Administrative Reason / Remarks</p>
              <AntInput.TextArea
                placeholder={`Why are you ${processAction}ing this request?`}
                rows={4}
                value={processReason}
                onChange={(e) => setProcessReason(e.target.value)}
                className="rounded-xl p-3"
              />
              <p className="text-[10px] text-gray-400 mt-2 italic">This comment will be visible in the system logs and leave records.</p>
            </div>
          </div>
        </Modal>

        {/* Announcement Modal */}
        <Modal
          title={<div className="flex items-center gap-2 text-xl font-black italic uppercase tracking-tight text-gray-900"><Megaphone className="text-orange-500" /> New Broadcast</div>}
          open={isAnnModalOpen}
          onCancel={() => setIsAnnModalOpen(false)}
          onOk={publishAnnouncement}
          confirmLoading={publishing}
          okText="Broadcast to All"
          okButtonProps={{ className: 'bg-[#7b2ff7] rounded-xl font-bold h-10' }}
          cancelButtonProps={{ className: 'rounded-xl font-bold h-10' }}
          centered
          width={600}
        >
          <div className="py-4 space-y-6">
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Headline</p>
              <AntInput
                placeholder="What is the big news?"
                value={annTitle}
                onChange={(e) => setAnnTitle(e.target.value)}
                className="rounded-xl p-3 font-bold"
              />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Announcement Details</p>
              <AntInput.TextArea
                placeholder="Details of the announcement..."
                rows={4}
                value={annContent}
                onChange={(e) => setAnnContent(e.target.value)}
                className="rounded-xl p-3"
              />
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Priority Level</p>
              <Select
                defaultValue="medium"
                className="w-full"
                onChange={(val) => setAnnPriority(val)}
                options={[
                  { value: 'low', label: 'Low - Information Only' },
                  { value: 'medium', label: 'Medium - Normal Update' },
                  { value: 'high', label: 'High - Critical Action Required' },
                ]}
              />
            </div>
          </div>
        </Modal>
      </main>
    </div>
  );
}
