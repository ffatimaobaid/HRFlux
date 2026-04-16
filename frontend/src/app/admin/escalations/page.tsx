'use client';

import React, { useState, useEffect } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi } from '@/lib/api';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  CheckCircle2,
  Bot,
  ArrowUpRight
} from 'lucide-react';
import { Table, Tag, Button, Modal, Input as AntInput, App } from 'antd';

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
  conversation_summary?: string;
  full_history?: string;
}

export default function EscalationsPage() {
  const [allEscalations, setAllEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'all' | 'workflow' | 'chat'>('all');

  // Resolution state
  const [isEscModalOpen, setIsEscModalOpen] = useState(false);
  const [selectedEsc, setSelectedEsc] = useState<Escalation | null>(null);
  const [resolutionNote, setResolutionNote] = useState('');
  const { message } = App.useApp();
  const [isResolving, setIsResolving] = useState(false);

  useEffect(() => {
    loadEscalations();
  }, []);

  const loadEscalations = async () => {
    setLoading(true);
    try {
      const res = await adminApi.getActiveEscalations();
      setAllEscalations(res.data);
    } catch (err) {
      message.error('Failed to load escalations');
    } finally {
      setLoading(false);
    }
  };

  const handleEscalationResolve = async () => {
    if (!selectedEsc || !resolutionNote) {
      message.error("Please provide resolution notes");
      return;
    }
    setIsResolving(true);
    try {
      if (selectedEsc.type === 'chat') {
        await adminApi.resolveChatEscalation(selectedEsc.db_id, resolutionNote);
      } else {
        await adminApi.resolveWorkflowEscalation(selectedEsc.db_id, resolutionNote);
      }
      message.success("Escalation resolved successfully");
      setIsEscModalOpen(false);
      setResolutionNote('');
      loadEscalations();
    } catch (err) {
      message.error("Failed to resolve escalation");
    } finally {
      setIsResolving(false);
    }
  };

  const parseEscalationDetails = (esc: Escalation) => {
    const desc = esc.description;

    if (esc.type === 'workflow') {
      return {
        ticketId: esc.id,
        category: 'WORKFLOW',
        urgency: 'MEDIUM',
        assignedTo: 'HR Manager',
        cleanDesc: desc.replace('STALE REQUEST: ', '')
      };
    }

    const idMatch = desc.match(/\[(HRF-.*?)\]/);
    const categoryMatch = desc.match(/\] (.*?) -/);
    const urgencyMatch = desc.match(/- (.*?) urgency/);
    const assignedMatch = desc.match(/Assigned to: (.*)/);

    return {
      ticketId: idMatch ? idMatch[1] : esc.id,
      category: categoryMatch ? categoryMatch[1].trim() : 'GENERAL',
      urgency: urgencyMatch ? urgencyMatch[1].trim() : 'MEDIUM',
      assignedTo: assignedMatch ? assignedMatch[1].trim() : 'HR Officer',
      cleanDesc: esc.query || desc
    };
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency.toUpperCase()) {
      case 'CRITICAL': return '#ff4d4f';
      case 'HIGH': return '#fa8c16';
      case 'MEDIUM': return '#7b2ff7';
      default: return '#52c41a';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category.toUpperCase()) {
      case 'PAYROLL_ISSUE': return 'gold';
      case 'HARASSMENT': return 'red';
      case 'COMPLAINT': return 'magenta';
      case 'TECHNICAL': return 'blue';
      case 'POLICY_DISPUTE': return 'cyan';
      default: return 'purple';
    }
  };

  const escalationColumns = [
    {
      title: 'Ticket ID',
      key: 'id',
      render: (_: any, esc: Escalation) => {
        const details = parseEscalationDetails(esc);
        return <span className="font-black text-gray-900 font-mono text-[13px]">{details.ticketId}</span>;
      }
    },
    {
      title: 'Type',
      key: 'category',
      render: (_: any, esc: Escalation) => {
        const details = parseEscalationDetails(esc);
        return <Tag color={getCategoryColor(details.category)} className="font-bold border-none px-3 py-0.5 rounded-lg text-[11px]">{details.category.replace('_', ' ')}</Tag>;
      }
    },
    {
      title: 'Employee',
      dataIndex: 'source',
      key: 'source',
      render: (text: string) => <span className="font-bold text-gray-700 text-[13px]">{text}</span>
    },
    {
      title: 'Urgency',
      key: 'urgency',
      render: (_: any, esc: Escalation) => {
        const details = parseEscalationDetails(esc);
        return (
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full animate-pulse`} style={{ backgroundColor: getUrgencyColor(details.urgency) }} />
            <span className="text-[12px] font-black uppercase tracking-tighter" style={{ color: getUrgencyColor(details.urgency) }}>{details.urgency}</span>
          </div>
        );
      }
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, esc: Escalation) => (
        <Button
          type="primary"
          size="middle"
          ghost
          className="border-[#7b2ff7] text-[#7b2ff7] hover:bg-[#7b2ff7] hover:text-white rounded-xl font-bold text-[11px]"
          onClick={() => {
            setSelectedEsc(esc);
            setIsEscModalOpen(true);
          }}
        >
          RESOLVE TICKET
        </Button>
      )
    }
  ];

  const filteredEscalations = activeTab === 'all'
    ? allEscalations
    : allEscalations.filter(e => e.type === activeTab);

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <AdminSidebar />

      <main className="flex-1 flex flex-col p-8 overflow-hidden">
        <header className="mb-10 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">🚨 Escalation Management</h1>
            <p className="text-gray-500 font-medium mt-1">Enterprise overview of critical system alerts and sensitive queries.</p>
          </div>
          <div className="flex bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100">
            <button
              onClick={() => setActiveTab('all')}
              className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'all' ? 'bg-[#7b2ff7] text-white shadow-lg' : 'text-gray-500 hover:bg-gray-50'}`}
            >
              All Tickets
            </button>
            <button
              onClick={() => setActiveTab('workflow')}
              className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'workflow' ? 'bg-[#7b2ff7] text-white shadow-lg' : 'text-gray-500 hover:bg-gray-50'}`}
            >
              📜 Workflow
            </button>
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-5 py-2.5 rounded-xl text-sm font-bold transition-all ${activeTab === 'chat' ? 'bg-[#7b2ff7] text-white shadow-lg' : 'text-gray-500 hover:bg-gray-50'}`}
            >
              💬 Sensitive Queries
            </button>
          </div>
        </header>

        <section className="flex-1 bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-500/5 blur-[80px] rounded-full pointer-events-none" />

          <div className="p-8 flex-1 overflow-auto custom-scrollbar relative z-10">
            {loading ? (
              <div className="h-full flex items-center justify-center">
                <div className="w-8 h-8 border-4 border-[#7b2ff7] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : filteredEscalations.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center opacity-60">
                <CheckCircle2 size={48} className="text-green-500 mb-4" />
                <p className="font-bold text-gray-900 text-lg">ALL CLEAR</p>
                <p className="text-sm text-gray-500 mt-2 tracking-widest uppercase font-black">No active escalations</p>
              </div>
            ) : (
              <Table
                dataSource={filteredEscalations}
                columns={escalationColumns}
                pagination={false}
                rowKey="id"
                className="custom-admin-table w-full"
                expandable={{
                  expandedRowRender: (record: Escalation) => (
                    <div className="p-6 bg-[#7b2ff7]/5 rounded-2xl border border-[#7b2ff7]/10 mb-4 ml-8 mr-4 relative overflow-hidden">
                      <div className="absolute -left-10 -top-10 w-32 h-32 bg-[#7b2ff7]/10 blur-2xl rounded-full pointer-events-none" />
                      <p className="text-[10px] font-black text-[#7b2ff7] uppercase tracking-widest mb-3 flex items-center gap-2 relative z-10">
                        <Bot size={14} /> AI CONVERSATION OVERVIEW
                      </p>

                      <div className="bg-white p-5 rounded-xl border border-[#7b2ff7]/10 shadow-sm relative z-10">
                        <p className="text-[13px] text-gray-800 leading-relaxed font-medium">
                          {record.conversation_summary || record.description}
                        </p>

                        {record.query && (
                          <div className="mt-4 pt-4 border-t border-gray-50">
                            <p className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1.5">Triggering Query</p>
                            <p className="text-[12px] text-gray-600 italic">"{record.query}"</p>
                          </div>
                        )}

                        {record.full_history && !record.conversation_summary && (
                          <div className="mt-4 pt-4 border-t border-gray-50">
                            <p className="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-1.5">Raw Context</p>
                            <div className="bg-gray-50 p-3 rounded-lg text-[10px] text-gray-500 whitespace-pre-wrap max-h-32 overflow-y-auto">
                              {record.full_history}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="mt-4 flex justify-end relative z-10">
                        <span className="text-[10px] text-gray-500 font-black bg-gray-50 px-3 py-1.5 rounded-lg border border-gray-100 tracking-wider">
                          ASSIGNED TO: {parseEscalationDetails(record).assignedTo.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ),
                  rowExpandable: (record: Escalation) => true,
                }}
              />
            )}
          </div>
        </section>

        {/* Escalation Resolution Modal */}
        <Modal
          title={<div className="flex items-center gap-2 text-xl font-black italic uppercase tracking-tight text-gray-900"><AlertCircle className="text-red-500" /> Resolve Ticket</div>}
          open={isEscModalOpen}
          onCancel={() => setIsEscModalOpen(false)}
          onOk={handleEscalationResolve}
          confirmLoading={isResolving}
          okText="Mark as Resolved"
          okButtonProps={{ className: 'bg-[#7b2ff7] rounded-xl font-bold h-10' }}
          cancelButtonProps={{ className: 'rounded-xl font-bold h-10' }}
          centered
          width={500}
        >
          <div className="py-4 space-y-4">
            {selectedEsc && (
              <div className="p-4 bg-gray-50 rounded-2xl border border-gray-100">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Ticket being Resolved</p>
                <div className="flex items-center justify-between">
                  <p className="font-bold text-gray-900 text-lg">{parseEscalationDetails(selectedEsc).ticketId}</p>
                  <Tag color={getCategoryColor(parseEscalationDetails(selectedEsc).category)} className="font-bold border-none">
                    {parseEscalationDetails(selectedEsc).category}
                  </Tag>
                </div>
                <p className="text-xs text-gray-500 mt-1">Submitted by: <span className="font-bold">{selectedEsc.source}</span></p>
              </div>
            )}
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Resolution Remarks</p>
              <AntInput.TextArea
                placeholder="How was this issue resolved? (e.g. Discussed with payroll team, grievance addressed)"
                rows={4}
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                className="rounded-xl p-3"
              />
              <p className="text-[10px] text-gray-400 mt-2 italic">These remarks will be permanently stored in the employee's escalation history.</p>
            </div>
          </div>
        </Modal>
      </main>
    </div>
  );
}
