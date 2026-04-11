'use client';

import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '@/components/AdminSidebar';
import { adminApi } from '@/lib/api';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Upload, 
  Files, 
  Trash2, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Search,
  BookOpen
} from 'lucide-react';
import { format } from 'date-fns';

interface DocMetadata {
  id: string;
  filename: string;
  uploaded_at: string;
  avg_tokens: number;
}

export default function DocumentManager() {
  const [docs, setDocs] = useState<DocMetadata[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  useEffect(() => {
    loadDocs();
  }, []);

  const loadDocs = async () => {
    setLoading(true);
    try {
      const res = await adminApi.getDocuments();
      setDocs(res.data);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document? This will remove all associated embeddings.')) return;
    try {
      await adminApi.deleteDocument(id);
      loadDocs();
    } catch (err) {
      alert('Delete failed');
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setUploadProgress(0);

    try {
      await adminApi.uploadDocument(formData);
      loadDocs();
    } catch (err) {
      alert('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const filteredDocs = docs.filter(d => 
    d.filename.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <AdminSidebar />
      
      <main className="flex-1 flex flex-col p-8 overflow-y-auto custom-scrollbar">
        <header className="mb-8">
           <h1 className="text-3xl font-bold text-gray-900 tracking-tight">📂 Knowledge Base Manager</h1>
           <p className="text-gray-500 font-medium">Upload, index, and manage HR policy training data.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           {/* Upload Component */}
           <section className="lg:col-span-1 space-y-6">
              <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col items-center text-center">
                 <div className="w-20 h-20 bg-indigo-50 text-indigo-600 rounded-3xl flex items-center justify-center mb-6">
                    {uploading ? <Loader2 size={40} className="animate-spin" /> : <Upload size={40} />}
                 </div>
                 <h3 className="text-xl font-bold mb-2">Upload Document</h3>
                 <p className="text-xs text-gray-500 mb-8 font-medium">Supported: PDF, DOCX, Images, Video, Audio. AI will auto-ingest content.</p>
                 
                 <label className="w-full">
                    <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
                    <div className={`p-4 rounded-2xl font-bold transition-all text-sm border-2 border-dashed cursor-pointer ${
                      uploading ? 'bg-gray-50 border-gray-100 text-gray-400' : 'bg-indigo-50 border-indigo-200 text-indigo-600 hover:bg-indigo-100'
                    }`}>
                       {uploading ? 'INGESTING CONTENT...' : 'SELECT FILE'}
                    </div>
                 </label>

                 {uploading && (
                   <motion.div 
                     initial={{ opacity: 0 }}
                     animate={{ opacity: 1 }}
                     className="mt-6 w-full space-y-2"
                   >
                      <div className="flex justify-between text-[10px] font-bold text-indigo-600 uppercase">
                         <span>AI Processing</span>
                         <span>Scanning...</span>
                      </div>
                      <div className="h-1.5 w-full bg-indigo-50 rounded-full overflow-hidden">
                         <motion.div 
                           className="h-full bg-indigo-600"
                           animate={{ width: ['0%', '95%'] }}
                           transition={{ duration: 15, ease: "linear" }}
                         />
                      </div>
                   </motion.div>
                 )}
              </div>

              <div className="bg-gray-900 rounded-3xl p-8 text-white shadow-xl">
                 <div className="flex items-center gap-4 mb-4">
                    <div className="p-2 bg-gray-800 rounded-xl">
                       <BookOpen size={20} className="text-indigo-400" />
                    </div>
                    <p className="text-sm font-bold">Indexing Status</p>
                 </div>
                 <p className="text-xs text-gray-400 font-medium leading-relaxed">
                    Once uploaded, documents are split into chunks, embedded using SOTA models, and stored in the vector database for RAG operations.
                 </p>
              </div>
           </section>

           {/* Document Table */}
           <section className="lg:col-span-2 bg-white rounded-3xl p-8 shadow-sm border border-gray-100 min-h-[600px]">
              <div className="flex items-center justify-between mb-8">
                 <div className="relative group flex-1 max-w-sm">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-indigo-500 transition-colors" size={18} />
                    <input 
                      type="text" 
                      placeholder="Search knowledge base..." 
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full bg-gray-50 border border-gray-100 rounded-2xl py-3 pl-12 pr-4 focus:outline-none focus:ring-4 focus:ring-indigo-100 focus:border-indigo-400 transition-all font-medium text-sm"
                    />
                 </div>
                 <p className="text-xs font-bold text-gray-400 ml-4 py-2 px-4 bg-gray-50 rounded-xl">
                    {docs.length} DOCUMENTS
                 </p>
              </div>

              <div className="overflow-hidden">
                 <AnimatePresence mode="popLayout">
                    {loading ? (
                      <div className="py-20 flex flex-col items-center justify-center text-gray-400">
                         <Loader2 size={40} className="animate-spin mb-4" />
                         <p className="font-bold">Syncing Knowledge Base...</p>
                      </div>
                    ) : filteredDocs.length === 0 ? (
                      <div className="py-20 flex flex-col items-center justify-center text-center text-gray-400">
                         <Files size={48} className="mb-4 opacity-20" />
                         <p className="font-bold">No documents found matching your search.</p>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {filteredDocs.map((doc) => (
                           <motion.div
                             key={doc.id}
                             layout
                             initial={{ opacity: 0 }}
                             animate={{ opacity: 1 }}
                             exit={{ opacity: 0, scale: 0.95 }}
                             className="p-5 bg-gray-50 rounded-2xl border border-gray-100 flex items-center justify-between group hover:bg-white hover:shadow-xl hover:shadow-indigo-900/5 transition-all"
                           >
                              <div className="flex items-center gap-4">
                                 <div className="p-3 bg-white rounded-xl shadow-sm group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-all text-gray-400">
                                    <FileText size={20} />
                                 </div>
                                 <div>
                                    <h4 className="font-bold text-sm text-gray-900 max-w-[300px] truncate">{doc.filename}</h4>
                                    <div className="flex gap-4 mt-1">
                                       <span className="text-[10px] font-bold text-gray-400 flex items-center gap-1 uppercase tracking-tight">
                                          <Upload size={10} /> {format(new Date(doc.uploaded_at), 'yyyy-MM-dd')}
                                       </span>
                                       <span className="text-[10px] font-bold text-indigo-400 flex items-center gap-1 uppercase tracking-tight">
                                          <CheckCircle size={10} /> {doc.avg_tokens.toFixed(0)} Avg Tokens
                                       </span>
                                    </div>
                                 </div>
                              </div>
                              <button 
                                onClick={() => handleDelete(doc.id)}
                                className="p-3 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-xl transition-all"
                              >
                                 <Trash2 size={20} />
                              </button>
                           </motion.div>
                        ))}
                      </div>
                    )}
                 </AnimatePresence>
              </div>
           </section>
        </div>
      </main>
    </div>
  );
}
