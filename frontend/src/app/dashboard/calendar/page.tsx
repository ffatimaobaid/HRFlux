'use client';

import React, { useState, useEffect } from 'react';
import Calendar from 'react-calendar';
import 'react-calendar/dist/Calendar.css';
import Sidebar from '@/components/Sidebar';
import { taskApi, authApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  CheckCircle2,
  Clock,
  Calendar as CalIcon,
  Tag,
  AlertCircle,
  CheckCircle,
  ClipboardList,
  Sparkles,
  Loader2
} from 'lucide-react';
import { format, isSameDay } from 'date-fns';

interface Task {
  id: number;
  title: string;
  description: string;
  deadline: string;
  event_type: string;
  status: 'pending' | 'completed';
}

export default function CalendarPage() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(true);

  // Form state
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [type, setType] = useState('task');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      loadTasks();
    }
  }, [user]);

  const loadTasks = async () => {
    try {
      const res = await taskApi.getTasks(user!.employee_id);
      setTasks(res.data);
    } catch (err) {
      console.error('Failed to load tasks', err);
    } finally {
      setLoading(false);
    }
  };

  const addTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await taskApi.createTask({
        employee_id: user!.employee_id,
        title,
        description: desc,
        deadline: format(selectedDate, 'yyyy-MM-dd'),
        event_type: type
      });
      setShowAddForm(false);
      setTitle('');
      setDesc('');
      loadTasks();
    } catch (err) {
      alert('Failed to add task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const completeTask = async (id: number) => {
    try {
      await taskApi.updateTask(id, { status: 'completed' });
      loadTasks();
    } catch (err) {
      alert('Failed to update task');
    }
  };

  const dailyTasks = tasks.filter(t =>
    t.deadline === format(selectedDate, 'yyyy-MM-dd')
  );

  const tileContent = ({ date, view }: any) => {
    if (view === 'month') {
      const dayTasks = tasks.filter(t => t.deadline === format(date, 'yyyy-MM-dd'));
      if (dayTasks.length > 0) {
        return (
          <div className="flex justify-center gap-0.5 mt-1">
            {dayTasks.slice(0, 3).map((t, i) => (
              <div
                key={i}
                className={`w-1.5 h-1.5 rounded-full ${t.status === 'completed' ? 'bg-green-400' : 'bg-indigo-500'
                  }`}
              />
            ))}
          </div>
        );
      }
    }
    return null;
  };

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <Sidebar />

      <main className="flex-1 flex flex-col overflow-hidden p-8">
        <header className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">📅 Calendar & Tasks</h1>
            <p className="text-gray-500 font-medium">Manage your schedule and daily objectives.</p>
          </div>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowAddForm(!showAddForm)}
            className="bg-indigo-600 text-white px-6 py-3 rounded-2xl font-bold flex items-center gap-2 shadow-lg shadow-indigo-100 transition-all"
          >
            <Plus size={20} />
            Add New Event
          </motion.button>
        </header>

        <div className="flex-1 flex gap-8 min-h-0">
          {/* Left: Interactive Calendar */}
          <section className="flex-[3] bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col">
            <style>{`
              .react-calendar {
                width: 100% !important;
                border: none !important;
                background: transparent !important;
                font-family: inherit !important;
              }
              .react-calendar__tile {
                padding: 1.5em 0.5em !important;
                border-radius: 1rem !important;
                transition: all 0.2s ease !important;
              }
              .react-calendar__tile--active {
                background: #4f46e5 !important;
                color: white !important;
                box-shadow: 0 4px 20px -6px #4f46e5 !important;
              }
              .react-calendar__tile--now {
                background: #f0f9ff !important;
                color: #0369a1 !important;
              }
              .react-calendar__navigation button {
                font-weight: bold !important;
                font-size: 1.1rem !important;
                border-radius: 0.75rem !important;
              }
              .react-calendar__month-view__weekdays__weekday {
                text-transform: uppercase !important;
                font-weight: 800 !important;
                font-size: 0.7rem !important;
                color: #94a3b8 !important;
                padding-bottom: 2rem !important;
              }
              .react-calendar__tile:hover {
                background-color: #f8fafc !important;
              }
            `}</style>
            <Calendar
              onChange={(d: any) => setSelectedDate(d)}
              value={selectedDate}
              tileContent={tileContent}
              className="flex-1"
            />
          </section>

          {/* Right: Task List */}
          <aside className="flex-[2] flex flex-col gap-6 overflow-hidden">
            <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col flex-1 overflow-hidden">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                <ClipboardList className="text-indigo-600" />
                Schedule for {format(selectedDate, 'MMM dd')}
              </h2>

              <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                <AnimatePresence mode="popLayout">
                  {dailyTasks.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="h-full flex flex-col items-center justify-center text-center py-12"
                    >
                      <CalIcon size={48} className="text-gray-200 mb-4" />
                      <p className="text-gray-400 font-medium">No tasks for this day.</p>
                      <button
                        onClick={() => setShowAddForm(true)}
                        className="text-indigo-600 text-sm font-bold mt-2 hover:underline"
                      >
                        Plan something?
                      </button>
                    </motion.div>
                  ) : (
                    dailyTasks.map((t) => (
                      <motion.div
                        layout
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        key={t.id}
                        className={`p-4 rounded-2xl border ${t.status === 'completed'
                            ? 'bg-green-50 border-green-100 grayscale-[0.5]'
                            : 'bg-white border-gray-100 hover:border-indigo-100'
                          } transition-all group`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className={`mt-1 p-2 rounded-xl ${t.status === 'completed' ? 'bg-green-200 text-green-700' : 'bg-gray-100 text-gray-500'
                              }`}>
                              {t.event_type === 'meeting' ? <Clock size={16} /> : <Tag size={16} />}
                            </div>
                            <div>
                              <h3 className={`font-bold text-sm ${t.status === 'completed' ? 'line-through text-gray-500' : 'text-gray-800'}`}>
                                {t.title}
                              </h3>
                              <p className="text-xs text-gray-500 mt-1">{t.description}</p>
                            </div>
                          </div>
                          {t.status === 'pending' && (
                            <button
                              onClick={() => completeTask(t.id)}
                              className="text-gray-300 hover:text-green-500 transition-colors"
                            >
                              <CheckCircle2 size={24} />
                            </button>
                          )}
                          {t.status === 'completed' && (
                            <CheckCircle size={24} className="text-green-500" />
                          )}
                        </div>
                      </motion.div>
                    ))
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Quick Stats / Legend */}
            <div className="bg-indigo-900 rounded-3xl p-6 text-white shadow-xl">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-indigo-800 rounded-2xl">
                  <Sparkles size={24} className="text-indigo-300" />
                </div>
                <div>
                  <p className="text-xs text-indigo-300 font-bold uppercase tracking-wider">Productivity</p>
                  <p className="text-lg font-bold">You have {tasks.filter(t => t.status === 'pending').length} tasks pending.</p>
                </div>
              </div>
            </div>
          </aside>
        </div>

        {/* Add Task Modal */}
        <AnimatePresence>
          {showAddForm && (
            <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <motion.div
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.9, opacity: 0 }}
                className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl"
              >
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-2xl font-bold">Add New Entry</h2>
                  <div className="text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full text-xs font-bold">
                    For {format(selectedDate, 'MMM dd')}
                  </div>
                </div>

                <form onSubmit={addTask} className="space-y-6">
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-2">Event Title</label>
                    <input
                      type="text"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Project Review"
                      className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all text-sm"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-2">Description</label>
                    <textarea
                      value={desc}
                      onChange={(e) => setDesc(e.target.value)}
                      placeholder="Details about this task..."
                      className="w-full p-4 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all text-sm min-h-[100px]"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-2">Category</label>
                    <div className="grid grid-cols-2 gap-3">
                      {['task', 'meeting', 'deadline', 'event'].map((cat) => (
                        <button
                          key={cat}
                          type="button"
                          onClick={() => setType(cat)}
                          className={`p-3 rounded-xl border text-sm font-bold capitalize transition-all ${type === cat
                              ? 'bg-indigo-600 border-indigo-600 text-white shadow-md'
                              : 'bg-white border-gray-200 text-gray-600 hover:border-indigo-200'
                            }`}
                        >
                          {cat}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex gap-4 pt-4">
                    <button
                      type="button"
                      onClick={() => setShowAddForm(false)}
                      className="flex-1 p-4 rounded-2xl font-bold bg-gray-100 text-gray-600 hover:bg-gray-200 transition-all"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="flex-[2] p-4 rounded-2xl font-bold bg-indigo-600 text-white shadow-lg shadow-indigo-100 hover:bg-indigo-700 disabled:opacity-75 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 size={20} className="animate-spin" />
                          Creating...
                        </>
                      ) : (
                        'Create Entry'
                      )}
                    </button>
                  </div>
                </form>
              </motion.div>
            </div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
