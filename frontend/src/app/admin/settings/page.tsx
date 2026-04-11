'use client';

import React, { useState, useEffect } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi } from '@/lib/api';
import { motion } from 'framer-motion';
import { 
  Settings, 
  Cpu, 
  Database, 
  Shield, 
  Save, 
  CheckCircle,
  AlertCircle,
  Zap,
  Globe,
  Bell
} from 'lucide-react';

export default function SettingsPage() {
  const [model, setModel] = useState('models/gemini-1.5-flash');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const res = await adminApi.getConfig();
      setModel(res.data.model);
    } catch (err) {
      console.error('Failed to load config', err);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      await adminApi.updateConfig({ model });
      setMessage('Configuration saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      alert('Save failed');
    } finally {
      setSaving(false);
    }
  };

  const models = [
    { id: 'models/gemini-1.5-flash', name: 'Gemini 1.5 Flash', desc: 'Fast, efficient, cost-effective', provider: 'Google' },
    { id: 'models/gemini-2.5-flash', name: 'Gemini 2.5 Flash', desc: 'SOTA performance for complex tasks', provider: 'Google' },
    { id: 'groq/llama3-70b-8192', name: 'Llama 3 70B', desc: 'High performance open-weights model', provider: 'Meta (via Groq)' },
    { id: 'groq/mixtral-8x7b-32768', name: 'Mixtral 8x7B', desc: 'Superior reasoning with large window', provider: 'Mistral (via Groq)' },
  ];

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col p-8 overflow-y-auto custom-scrollbar">
        <header className="mb-10">
           <h1 className="text-3xl font-extrabold text-gray-900 tracking-tight">⚙️ System Settings</h1>
           <p className="text-gray-500 font-medium">Fine-tune the AI core and manage system-wide preferences.</p>
        </header>

        <div className="max-w-4xl space-y-8">
           {/* Model Selection */}
           <section className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
              <div className="flex items-center gap-4 mb-8">
                 <div className="p-3 bg-indigo-50 text-indigo-600 rounded-2xl">
                    <Cpu size={24} />
                 </div>
                 <div>
                    <h2 className="text-xl font-bold">Inference Model</h2>
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mt-0.5">Model selection for RAG & Tool use</p>
                 </div>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                 {models.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setModel(m.id)}
                      className={`p-5 rounded-2xl border-2 text-left transition-all ${
                        model === m.id 
                          ? 'border-indigo-600 bg-indigo-50 ring-4 ring-indigo-50' 
                          : 'border-gray-100 hover:border-gray-200 bg-gray-50/50'
                      }`}
                    >
                       <div className="flex justify-between items-start mb-2">
                          <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded bg-white shadow-sm ${
                             m.provider.includes('Meta') ? 'text-blue-500' : 'text-indigo-600'
                          }`}>
                             {m.provider}
                          </span>
                          {model === m.id && <CheckCircle size={16} className="text-indigo-600" />}
                       </div>
                       <p className="font-bold text-gray-900 group-hover:text-indigo-600 transition-colors">{m.name}</p>
                       <p className="text-xs text-gray-500 mt-1">{m.desc}</p>
                    </button>
                 ))}
              </div>

              <div className="flex items-center justify-between pt-6 border-t border-gray-50">
                 <div className="flex items-center gap-2">
                    <Zap size={16} className="text-orange-400" />
                    <span className="text-xs text-gray-400 font-medium italic">Changes affect all active chat instances.</span>
                 </div>
                 <button 
                   onClick={handleSave}
                   disabled={saving}
                   className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 flex items-center gap-2 disabled:opacity-50"
                 >
                    {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
                    {saving ? 'SAVING...' : 'SAVE CHANGES'}
                 </button>
              </div>
              
              {message && (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-3 bg-green-50 text-green-700 rounded-xl text-center text-sm font-bold border border-green-100"
                >
                  {message}
                </motion.div>
              )}
           </section>

           {/* System Modules (Dummy) */}
           <div className="grid grid-cols-2 gap-8">
              <section className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 opacity-60">
                 <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl">
                       <Globe size={24} />
                    </div>
                    <h3 className="text-lg font-bold">Localization</h3>
                 </div>
                 <div className="space-y-4">
                    <div className="h-4 w-full bg-gray-50 rounded-full" />
                    <div className="h-4 w-3/4 bg-gray-50 rounded-full" />
                 </div>
              </section>

              <section className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 opacity-60">
                 <div className="flex items-center gap-4 mb-6">
                    <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl">
                       <Bell size={24} />
                    </div>
                    <h3 className="text-lg font-bold">Notifications</h3>
                 </div>
                 <div className="space-y-4">
                    <div className="h-4 w-full bg-gray-50 rounded-full" />
                    <div className="h-4 w-1/2 bg-gray-50 rounded-full" />
                 </div>
              </section>
           </div>
        </div>
      </main>
    </div>
  );
}
