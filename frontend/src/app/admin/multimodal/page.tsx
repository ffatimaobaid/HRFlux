'use client';

import React, { useState, useEffect } from 'react';
import { 
  Upload, 
  Search, 
  Image as ImageIcon, 
  FileText, 
  Mic, 
  Video, 
  BarChart3, 
  Search as SearchIcon,
  Plus,
  Trash2,
  FileUp,
  History,
  ShieldCheck,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/hooks/useAuth';

export default function AdminMultiModal() {
  const [activeTab, setActiveTab] = useState<'upload' | 'search' | 'gallery' | 'analytics'>('upload');
  const [files, setFiles] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<any>(null);
  const { token } = useAuth();

  const fetchFiles = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/admin/multimodal/files', {
        headers: { Authorization: token || '' }
      });
      const data = await res.json();
      if (data.success) setFiles(data.files);
    } catch (err) {
      console.error('Failed to fetch files:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/admin/multimodal/stats', {
        headers: { Authorization: token || '' }
      });
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchFiles();
      fetchStats();
    }
  }, [token]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await fetch('http://localhost:8000/api/admin/multimodal/search', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          Authorization: token || '' 
        },
        body: JSON.stringify({ query: searchQuery })
      });
      const data = await res.json();
      if (data.success) setSearchResults(data.results);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setIsUploading(true);
    setUploadStatus({ message: 'Uploading and processing file...', type: 'info' });
    
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('http://localhost:8000/api/admin/multimodal/upload', {
        method: 'POST',
        headers: { Authorization: token || '' },
        body: formData
      });
      const data = await res.json();
      if (data.doc_id) {
        setUploadStatus({ message: `Successfully indexed ${file.name}`, type: 'success' });
        fetchFiles();
        fetchStats();
      } else {
        setUploadStatus({ message: `Error: ${data.detail || 'Internal error'}`, type: 'error' });
      }
    } catch (err) {
      setUploadStatus({ message: 'Failed to upload file', type: 'error' });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto min-h-screen bg-gray-50/50">
      <div className="flex flex-col gap-2 mb-10">
        <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight flex items-center gap-3">
          <ShieldCheck className="text-indigo-600 w-10 h-10" />
          Multi-Modal RAG <span className="text-indigo-600">Studio</span>
        </h1>
        <p className="text-gray-500 font-medium">Upload documents, images, audio, or video for intelligent HR analysis.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1.5 bg-gray-200/50 rounded-2xl mb-8 w-fit">
        {[
          { id: 'upload', icon: <FileUp size={18} />, label: 'Upload Studio' },
          { id: 'search', icon: <SearchIcon size={18} />, label: 'AI Discovery' },
          { id: 'gallery', icon: <ImageIcon size={18} />, label: 'Media Assets' },
          { id: 'analytics', icon: <BarChart3 size={18} />, label: 'RAG Insights' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2.5 px-6 py-2.5 rounded-xl font-bold text-sm transition-all duration-300 ${
              activeTab === tab.id 
                ? 'bg-white text-indigo-600 shadow-xl shadow-indigo-500/10' 
                : 'text-gray-500 hover:text-gray-900 hover:bg-white/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="bg-white rounded-3xl border border-gray-100 shadow-2xl shadow-gray-200/50 p-8 min-h-[500px]"
        >
          {activeTab === 'upload' && (
            <div className="max-w-2xl mx-auto space-y-12 py-10">
              <div className="text-center space-y-4">
                <div className="w-24 h-24 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-6 border-4 border-indigo-100 animate-pulse">
                  <Upload className="text-indigo-600 w-10 h-10" />
                </div>
                <h2 className="text-3xl font-extrabold text-gray-900">Ingest Media</h2>
                <p className="text-gray-500 font-medium">Extract insights from any format. PDFs, scanned images, voice memos, or video clips.</p>
              </div>

              <div className="relative group">
                <input 
                  type="file" 
                  onChange={handleFileUpload}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                  disabled={isUploading}
                />
                <div className={`border-4 border-dashed rounded-[40px] p-16 text-center transition-all duration-500 ${
                  isUploading ? 'bg-gray-50 border-gray-200' : 'bg-indigo-50/20 border-indigo-100 group-hover:border-indigo-400 group-hover:bg-indigo-50/50 shadow-inner'
                }`}>
                  <Plus className={`mx-auto w-16 h-16 mb-4 transition-transform duration-500 ${isUploading ? 'animate-spin text-gray-400' : 'text-indigo-300 group-hover:scale-110 group-hover:rotate-90 text-indigo-500'}`} />
                  <p className="text-gray-600 font-bold text-xl">{isUploading ? 'Processing...' : 'Click or Drop Multi-Modal Content'}</p>
                  <p className="text-gray-400 font-medium mt-2">Support for PDF, JPG, PNG, MP3, WAV, MP4</p>
                </div>
              </div>

              {uploadStatus && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`p-6 rounded-3xl flex items-center gap-4 border-2 ${
                    uploadStatus.type === 'success' ? 'bg-emerald-50 border-emerald-100 text-emerald-800' : 
                    uploadStatus.type === 'error' ? 'bg-rose-50 border-rose-100 text-rose-800' : 
                    'bg-indigo-50 border-indigo-100 text-indigo-800'
                  }`}
                >
                  {uploadStatus.type === 'success' ? <CheckCircle2 /> : uploadStatus.type === 'error' ? <AlertCircle /> : <div className="w-5 h-5 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />}
                  <span className="font-bold">{uploadStatus.message}</span>
                </motion.div>
              )}
            </div>
          )}

          {activeTab === 'search' && (
            <div className="space-y-10">
              <form onSubmit={handleSearch} className="max-w-3xl mx-auto flex gap-4">
                <div className="relative flex-1">
                  <SearchIcon className="absolute left-6 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={24} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search across all media (e.g., 'leave policy draft in audio')"
                    className="w-full bg-gray-50 border-2 border-gray-100 rounded-3xl py-6 pl-16 pr-6 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-bold text-lg shadow-sm"
                  />
                </div>
                <button 
                  type="submit"
                  disabled={isSearching}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white font-black px-10 rounded-3xl transition-all shadow-xl shadow-indigo-200 disabled:bg-gray-400 active:scale-95"
                >
                  {isSearching ? 'SEEKING...' : 'DISCOVER'}
                </button>
              </form>

              <div className="grid grid-cols-1 gap-6">
                {searchResults.map((result, i) => (
                  <motion.div
                    key={result.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex gap-8 bg-gray-50/50 p-8 rounded-[40px] border border-gray-100 hover:shadow-2xl transition-all group"
                  >
                    <div className="w-20 h-20 bg-white rounded-3xl flex items-center justify-center text-indigo-600 shadow-lg border border-gray-100 flex-shrink-0 group-hover:scale-110 transition-transform duration-500">
                      {result.metadata.file_type === 'images' ? <ImageIcon size={32} /> : 
                       result.metadata.file_type === 'audio' ? <Mic size={32} /> :
                       result.metadata.file_type === 'video' ? <Video size={32} /> :
                       <FileText size={32} />}
                    </div>
                    <div className="space-y-3 flex-1 overflow-hidden">
                      <div className="flex justify-between items-start">
                        <h4 className="font-black text-2xl text-gray-900 truncate">{result.metadata.filename}</h4>
                        <span className="bg-indigo-100 text-indigo-700 px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wider">
                          {(1 - result.distance).toFixed(2)} Match
                        </span>
                      </div>
                      <p className="text-gray-500 font-semibold line-clamp-3 leading-relaxed">
                        {result.document}
                      </p>
                      <div className="flex gap-4 pt-4">
                        <span className="flex items-center gap-2 text-xs font-black text-gray-400 uppercase tracking-widest">
                          <History size={14} /> Indexed: {new Date(result.metadata.upload_timestamp).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
                {searchResults.length === 0 && !isSearching && searchQuery && (
                  <div className="text-center py-20 bg-gray-50 rounded-[40px] border-2 border-dashed border-gray-200">
                    <SearchIcon size={64} className="mx-auto mb-6 text-gray-200" />
                    <p className="text-gray-400 font-bold text-2xl uppercase tracking-tighter">No relevant patterns discovered</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'gallery' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {files.map((file) => (
                <div key={file.doc_id} className="bg-gray-50 rounded-[40px] overflow-hidden border border-gray-100 hover:shadow-2xl transition-all group relative">
                  <div className="h-56 bg-white flex items-center justify-center border-b border-gray-100">
                    {file.file_type === 'images' ? <ImageIcon size={64} className="text-gray-200" /> : 
                     file.file_type === 'audio' ? <Mic size={64} className="text-gray-200" /> :
                     file.file_type === 'video' ? <Video size={64} className="text-gray-200" /> :
                     <FileText size={64} className="text-gray-200" />}
                  </div>
                  <div className="p-8 space-y-4">
                    <h5 className="font-black text-xl text-gray-900 truncate">{file.filename}</h5>
                    <div className="flex justify-between items-center text-xs font-bold text-gray-500 uppercase tracking-widest">
                      <span className="bg-white px-3 py-1 rounded-full border border-gray-200">{file.file_type}</span>
                      <span>{(file.file_size / 1024).toFixed(1)} KB</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'analytics' && stats && (
            <div className="space-y-12">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div className="bg-indigo-600 rounded-[50px] p-10 text-white shadow-2xl shadow-indigo-900/40 relative overflow-hidden group">
                  <div className="absolute -right-10 -bottom-10 opacity-10 group-hover:scale-110 transition-transform duration-700">
                    <FileText size={200} />
                  </div>
                  <p className="text-indigo-200 font-black text-xs uppercase tracking-widest mb-4">Total Multi-Modal Chunks</p>
                  <h6 className="text-6xl font-black tracking-tighter">{stats.total_chunks}</h6>
                  <p className="text-indigo-100 font-bold mt-4">Search-optimized fragments</p>
                </div>
                <div className="bg-gray-900 rounded-[50px] p-10 text-white shadow-2xl shadow-gray-900/40 relative overflow-hidden group">
                  <div className="absolute -right-10 -bottom-10 opacity-10 group-hover:scale-110 transition-transform duration-700">
                    <ImageIcon size={200} />
                  </div>
                  <p className="text-gray-400 font-black text-xs uppercase tracking-widest mb-4">Master Media Index</p>
                  <h6 className="text-6xl font-black tracking-tighter">{stats.total_files}</h6>
                  <p className="text-gray-500 font-bold mt-4">Files across all modalities</p>
                </div>
                <div className="bg-white rounded-[50px] p-10 border-4 border-indigo-50 shadow-2xl shadow-indigo-500/5 relative overflow-hidden group">
                  <div className="absolute -right-10 -bottom-10 opacity-5 group-hover:scale-110 transition-transform duration-700">
                    <BarChart3 size={200} />
                  </div>
                  <p className="text-indigo-500 font-black text-xs uppercase tracking-widest mb-4">Storage Footprint</p>
                  <h6 className="text-6xl font-black text-gray-900 tracking-tighter">{stats.storage_used_mb.toFixed(2)}<span className="text-2xl ml-1">MB</span></h6>
                  <p className="text-gray-400 font-bold mt-4">Media vault consumption</p>
                </div>
              </div>

              <div className="bg-gray-50/50 rounded-[40px] p-10 border border-gray-100">
                <h3 className="font-black text-2xl text-gray-900 mb-8 flex items-center gap-3">
                  <History className="text-indigo-600" />
                  Recent Ingestion Stream
                </h3>
                <div className="space-y-4">
                  {files.slice(0, 5).map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-white p-6 rounded-3xl border border-gray-100 hover:shadow-xl transition-all">
                      <div className="flex items-center gap-4">
                        <div className="bg-indigo-50 p-3 rounded-2xl text-indigo-600">
                           {file.file_type === 'images' ? <ImageIcon size={20} /> : <FileText size={20} />}
                        </div>
                        <div>
                          <p className="font-bold text-gray-900">{file.filename}</p>
                          <p className="text-xs font-semibold text-gray-400">{new Date(file.upload_timestamp).toLocaleString()}</p>
                        </div>
                      </div>
                      <span className="text-xs font-black text-gray-300 uppercase tracking-widest">{file.doc_id}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
