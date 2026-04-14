'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Sidebar from '@/components/Sidebar';
import SmartNotification, { ProactiveNotification } from '@/components/SmartNotification';
import { chatApi, hrApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import {
  Send,
  Bot,
  User,
  Loader2,
  Calendar,
  ClipboardList,
  FileText,
  AlertCircle,
  Download,
  FileDown,
  Bell,
  Megaphone,
  ArrowRight
} from 'lucide-react';
import { format } from 'date-fns';
import { Input, Button, notification } from 'antd';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  suggestions?: string[];
  pdfDownload?: { filename: string; url: string } | null;
}

// Detect if a bot reply contains a PDF download URL
function extractPdfDownload(content: string): { filename: string; url: string } | null {
  const match = content.match(/\/download_document\/([\w.\-]+\.pdf)/i);
  if (match) {
    return {
      filename: match[1],
      url: `http://localhost:8000/download_document/${match[1]}`,
    };
  }
  return null;
}

// Strip the raw download URL from visible message text
function cleanMessageContent(content: string): string {
  return content
    .replace(/\/download_document\/[\w.\-]+\.pdf/gi, '')
    .replace(/Click the download link to save it:\s*/gi, '')
    .replace(/Download it here:\s*/gi, '')
    .trim();
}

// PDF Download Card
function PdfDownloadCard({ filename, url }: { filename: string; url: string }) {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const token = localStorage.getItem('hrflux_token');
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Download error:', err);
      alert('Download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const docLabel = filename
    .replace(/_\d{8}_\d{6}\.pdf$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 flex items-center gap-4 bg-gradient-to-r from-red-50 to-orange-50 border border-red-100 rounded-2xl p-4 shadow-sm max-w-sm"
    >
      <div className="flex-shrink-0 w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
        <FileDown size={24} className="text-red-600" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-bold text-red-700 uppercase tracking-wide">PDF Ready</p>
        <p className="text-sm font-semibold text-gray-800 truncate">{docLabel}</p>
        <p className="text-[11px] text-gray-400 truncate">{filename}</p>
      </div>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="flex-shrink-0 flex items-center gap-2 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-xs font-bold px-4 py-2 rounded-xl transition-all active:scale-95 shadow"
      >
        {downloading ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Download size={14} />
        )}
        {downloading ? 'Saving...' : 'Download'}
      </button>
    </motion.div>
  );
}

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  
  // Strict lockdown: Never show employee dashboard to an admin
  if (authLoading || (user && user.role !== 'employee')) {
    return <div className="h-screen bg-[#f8f9ff] flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-[#7b2ff7] border-t-transparent rounded-full animate-spin" />
    </div>;
  }

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState<ProactiveNotification[]>([]);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const notifRef = useRef<HTMLDivElement>(null);
  const lastSeenNotifs = useRef<Set<number>>(new Set());
  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [isAnnOpen, setIsAnnOpen] = useState(false);
  const annRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(event.target as Node)) {
        setIsNotifOpen(false);
      }
    }
    if (isNotifOpen || isAnnOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isNotifOpen]);

  useEffect(() => {
    if (user) {
      loadHistory();
      loadNotifications();
      loadAnnouncements();

      // Poll for new notifications every 30 seconds
      const interval = setInterval(() => {
        loadNotifications();
        loadAnnouncements();
      }, 30000);
      return () => clearInterval(interval);
    }
  }, [user]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const getDismissedIds = (): Set<number> => {
    try {
      const raw = localStorage.getItem('hrflux_dismissed_notifs');
      return new Set(raw ? JSON.parse(raw) : []);
    } catch {
      return new Set();
    }
  };

  const addDismissedId = (id: number) => {
    const ids = getDismissedIds();
    ids.add(id);
    localStorage.setItem('hrflux_dismissed_notifs', JSON.stringify([...ids]));
  };

  const loadNotifications = async () => {
    try {
      const dismissed = getDismissedIds();
      const res = await hrApi.getProactiveNotifications();
      const visible = (res.data as ProactiveNotification[]).filter(
        (n) => !n.id || !dismissed.has(n.id)
      );
      
      // Check for new "Approved" notifications to show a Toast
      visible.forEach(n => {
        if (n.id && !lastSeenNotifs.current.has(n.id)) {
          lastSeenNotifs.current.add(n.id);
          if (n.title.includes('Approved') || n.type === 'success') {
            notification.success({
              message: n.title,
              description: n.message,
              placement: 'topRight',
              duration: 10,
              style: { borderRadius: '24px', border: '1px solid #b7eb8f', backgroundColor: '#f6ffed' }
            });
          }
        }
      });

      setNotifications(visible);
    } catch (err) {
      console.error('Failed to load notifications', err);
    }
  };

  const loadAnnouncements = async () => {
    try {
      const res = await hrApi.getAnnouncements();
      setAnnouncements(res.data || []);
    } catch (err) {
      console.error('Failed to load announcements', err);
    }
  };

  const handleCloseNotification = async (index: number) => {
    const notif = notifications[index];
    if (notif?.id) {
      // Track dismissal permanently on this browser
      addDismissedId(notif.id);
    }
    setNotifications(prev => prev.filter((_, i) => i !== index));
  };

  const loadHistory = async () => {
    try {
      const res = await chatApi.getHistory(user!.employee_id);
      const history = res.data.history.flatMap((m: any) => [
        { role: 'user', content: m.question },
        {
          role: 'assistant',
          content: cleanMessageContent(m.answer),
          pdfDownload: extractPdfDownload(m.answer),
        },
      ]);
      setMessages(history);
    } catch (err) {
      console.error('Failed to load history', err);
    }
  };

  const handleSend = async (question: string) => {
    if (!question.trim()) return;
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setInput('');
    setLoading(true);

    try {
      const res = await chatApi.employeeChat({ user_id: user!.employee_id, question });
      const rawAnswer: string = res.data.answer;
      const pdfDownload = extractPdfDownload(rawAnswer);
      const cleanedAnswer = pdfDownload ? cleanMessageContent(rawAnswer) : rawAnswer;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: cleanedAnswer,
          suggestions: res.data.suggestions,
          pdfDownload,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = async () => {
    if (confirm('Are you sure you want to clear your chat history?')) {
      await chatApi.clearHistory(user!.employee_id);
      setMessages([]);
    }
  };

  const handleNotifAction = (actionId: string) => {
    const actionMap: Record<string, string> = {
      check_in: 'I want to check in for today',
      view_tasks: 'Show my tasks for today',
      view_leaves: 'Check my leave balance',
      view_policy_wellness: 'Tell me about the wellness policy',
    };
    if (actionMap[actionId]) {
      handleSend(actionMap[actionId]);
      setNotifications((prev) => prev.filter((n) => n.action_id !== actionId));
    }
  };

  const dismissNotif = (index: number) => {
    setNotifications((prev) => prev.filter((_, i) => i !== index));
  };

  const quickActions = [
    { label: 'My leave balance', icon: <Calendar size={18} />, color: 'bg-blue-50 text-blue-600' },
    { label: 'Apply for leave', icon: <ClipboardList size={18} />, color: 'bg-green-50 text-green-600' },
    { label: 'Request a document', icon: <FileText size={18} />, color: 'bg-purple-50 text-purple-600' },
    { label: 'Report an issue', icon: <AlertCircle size={18} />, color: 'bg-red-50 text-red-600' },
  ];

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <Sidebar onClearChat={clearChat} />

      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b border-gray-100 bg-white flex items-center justify-between px-8">
          <h1 className="text-xl font-bold text-gray-800">🤖 Chat Assistant</h1>
          {/* Proactive Notifications Header Icon */}
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-500">Model: Gemini 1.5 Flash</span>
          
          {/* Notification Bell */}
          <div className="relative" ref={notifRef}>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setIsNotifOpen(!isNotifOpen)}
              className="p-2.5 bg-gray-50 text-gray-400 hover:text-[#7b2ff7] hover:bg-[#f4effc] rounded-xl transition-all relative"
            >
              <Bell size={20} />
              {notifications.length > 0 && (
                <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full" />
              )}
            </motion.button>

            <AnimatePresence>
              {isNotifOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 mt-3 w-80 bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden z-[100]"
                >
                  <div className="p-4 border-b border-gray-50 flex items-center justify-between bg-gray-50/50">
                    <h4 className="font-black text-gray-800 tracking-tight">Notifications</h4>
                    <span className="text-[10px] font-bold bg-[#e0d4fc] text-[#5b1ab5] px-2 py-0.5 rounded-full uppercase">
                      {notifications.length} New
                    </span>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.length > 0 ? (
                      <SmartNotification 
                        isDropdown 
                        notifications={notifications}
                        onAction={handleNotifAction}
                        onClose={handleCloseNotification}
                      />
                    ) : (
                      <div className="p-8 text-center">
                        <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-3">
                          <Bell size={20} className="text-gray-300" />
                        </div>
                        <p className="text-sm font-bold text-gray-400">All caught up!</p>
                      </div>
                    )}
                  </div>
                  {notifications.length > 0 && (
                    <div className="p-3 bg-gray-50 border-t border-gray-100 text-center">
                      <button className="text-[10px] font-black text-[#7b2ff7] hover:text-[#5b1ab5] uppercase tracking-widest">
                        Clear All
                      </button>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Announcement Hub */}
          <div className="relative" ref={annRef}>
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={() => setIsAnnOpen(!isAnnOpen)}
              className={`p-2.5 rounded-xl transition-all relative ${
                announcements.some(a => a.priority === 'high')
                  ? 'bg-orange-500 text-white shadow-lg shadow-orange-500/30'
                  : 'bg-gray-50 text-gray-400 hover:text-orange-500 hover:bg-orange-50'
              }`}
            >
              <Megaphone size={20} className={announcements.length > 0 ? "animate-bounce" : ""} />
              {announcements.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-600 text-[8px] font-black text-white px-1.5 py-0.5 rounded-full border-2 border-white">
                  {announcements.length}
                </span>
              )}
            </motion.button>

            <AnimatePresence>
              {isAnnOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute right-0 mt-3 w-96 bg-white rounded-3xl shadow-2xl border border-gray-100 overflow-hidden z-[100]"
                >
                  <div className="p-5 border-b border-gray-50 bg-orange-50/30 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                       <div className="p-2 bg-orange-100 text-orange-600 rounded-lg">
                          <Megaphone size={16} />
                       </div>
                       <h4 className="font-black text-gray-800 tracking-tight">Company Broadcasts</h4>
                    </div>
                  </div>
                  <div className="max-h-[500px] overflow-y-auto p-4 space-y-4 custom-scrollbar">
                    {announcements.length > 0 ? (
                      announcements.map((ann, idx) => (
                        <div key={idx} className={`p-4 rounded-2xl border ${
                          ann.priority === 'high' ? 'bg-red-50 border-red-100' : 'bg-gray-50 border-gray-100'
                        }`}>
                           <div className="flex items-center justify-between mb-2">
                              <span className={`text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest ${
                                ann.priority === 'high' ? 'bg-red-600 text-white' : 'bg-gray-200 text-gray-500'
                              }`}>
                                {ann.priority} Priority
                              </span>
                              <span className="text-[10px] text-gray-400 font-bold">{format(new Date(ann.created_at), 'MMM dd, HH:mm')}</span>
                           </div>
                           <h5 className="font-black text-gray-900 mb-1 leading-tight">{ann.title}</h5>
                           <p className="text-xs text-gray-600 leading-relaxed">{ann.content}</p>
                        </div>
                      ))
                    ) : (
                      <div className="py-20 text-center opacity-40">
                         <Megaphone size={48} className="mx-auto mb-4 text-gray-300" />
                         <p className="font-bold">No active broadcasts</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <div className="w-10 h-10 rounded-full border-2 border-[#e0d4fc] p-0.5">
              <div className="w-full h-full bg-[#f4effc] rounded-full flex items-center justify-center text-[#7b2ff7] font-bold">
                {user?.username?.charAt(0).toUpperCase()}
              </div>
            </div>
          </div>
        </header>

        {/* The proactive notifications and latest announcement section has been removed to keep the chat area clean. */}

        {/* Quick Actions */}
        <div className="px-8 pt-6">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Quick Actions</p>
          <div className="grid grid-cols-4 gap-4">
            {quickActions.map((action) => (
              <motion.button
                key={action.label}
                whileHover={{ scale: 1.02, y: -2 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSend(action.label)}
                className="flex items-center gap-3 p-4 bg-white rounded-2xl border border-gray-100 hover:border-indigo-200 transition-all text-left group shadow-sm"
              >
                <div className={`p-2 rounded-xl ${action.color}`}>{action.icon}</div>
                <span className="text-sm font-bold text-gray-700 group-hover:text-[#7b2ff7] transition-colors">
                  {action.label}
                </span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-hidden flex flex-col p-8 pb-4">
          <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-6 pr-4 custom-scrollbar">


            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center opacity-40">
                <Bot size={64} className="mb-4 text-[#7b2ff7]" />
                <h2 className="text-2xl font-bold mb-2">Hello, {user?.username}!</h2>
                <p className="max-w-xs">
                  I am your AI HR assistant. Ask me anything about policies, leaves, or documents.
                </p>
              </div>
            )}

            {messages.map((msg, idx) => (
              <motion.div
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div
                    className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${
                      msg.role === 'user'
                        ? 'bg-[#7b2ff7] text-white'
                        : 'bg-white border border-gray-200 text-[#7b2ff7]'
                    }`}
                  >
                    {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                  </div>

                  <div className="space-y-2">
                    {/* Message bubble */}
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm whitespace-pre-wrap ${
                        msg.role === 'user'
                          ? 'bg-[#7b2ff7] text-white rounded-tr-none'
                          : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                      }`}
                    >
                      {msg.content}
                    </div>

                    {/* PDF Download Card */}
                    {msg.role === 'assistant' && msg.pdfDownload && (
                      <PdfDownloadCard filename={msg.pdfDownload.filename} url={msg.pdfDownload.url} />
                    )}

                    {/* Suggested follow-ups */}
                    {msg.suggestions && msg.suggestions.length > 0 && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        <p className="w-full text-[10px] font-bold text-gray-400 uppercase tracking-widest pl-1">
                          Suggested:
                        </p>
                        {msg.suggestions.map((sug, sidx) => (
                          <button
                            key={sidx}
                            onClick={() => handleSend(sug)}
                            className="text-xs bg-[#f4effc] text-[#5b1ab5] font-semibold px-3 py-1.5 rounded-full hover:bg-[#e0d4fc] transition-colors border border-[#e0d4fc]"
                          >
                            {sug}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}

            {loading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-white border border-gray-200 flex items-center justify-center text-[#7b2ff7]">
                    <Bot size={16} />
                  </div>
                  <div className="bg-white border border-gray-100 p-4 rounded-2xl rounded-tl-none flex items-center gap-2">
                    <Loader2 size={16} className="animate-spin text-indigo-500" />
                    <span className="text-sm text-gray-500 font-medium">Thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Input area */}
        <div className="p-8 pt-0">
          <div className="relative group">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend(input)}
              placeholder="Ask about HR policies..."
              size="large"
              className="w-full rounded-2xl p-4 pr-32 font-medium"
              style={{ boxShadow: '0 4px 12px rgba(123, 47, 247, 0.05)' }}
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2 z-10">
              <div className="p-1 px-2 bg-[#f4effc] text-[#7b2ff7] rounded-lg text-[10px] font-bold tracking-tight">
                AI ACTIVE
              </div>
              <Button
                type="primary"
                onClick={() => handleSend(input)}
                className="h-10 w-10 flex items-center justify-center rounded-xl shadow-md"
                icon={<Send size={16} />}
              />
            </div>
          </div>
          <p className="text-center text-[10px] text-gray-400 mt-4 font-medium tracking-wide">
            HRFLUX AI ASSISTANT MAY PROVIDE INFORMATION BASED ON UPLOADED POLICIES. ALWAYS VERIFY CRITICAL INFO.
          </p>
        </div>
      </main>
    </div>
  );
}
