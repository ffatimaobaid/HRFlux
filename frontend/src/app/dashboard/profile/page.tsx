'use client';

import React, { useState, useEffect } from 'react';
import Sidebar from '@/components/Sidebar';
import { hrApi } from '@/lib/api';
import { useAuth } from '@/hooks/useAuth';
import { motion } from 'framer-motion';
import { 
  User, 
  Mail, 
  Briefcase, 
  MapPin, 
  Calendar, 
  DollarSign, 
  ShieldCheck,
  Activity,
  Heart,
  Clock
} from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuth();
  const [employee, setEmployee] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.employee_id) {
      loadProfile();
    }
  }, [user]);

  const loadProfile = async () => {
    try {
      const res = await hrApi.getEmployee(user!.employee_id);
      setEmployee(res.data);
    } catch (err) {
      console.error('Failed to load profile', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-[#f8f9ff] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-indigo-600 font-bold">Loading Profile...</p>
        </div>
      </div>
    );
  }

  const profileStats = [
    { label: 'Casual Leave', value: employee?.casual_leave_balance, icon: <Activity className="text-blue-500" />, bg: 'bg-blue-50' },
    { label: 'Sick Leave', value: employee?.sick_leave_balance, icon: <Heart className="text-red-500" />, bg: 'bg-red-50' },
    { label: 'Annual Leave', value: employee?.annual_leave_balance, icon: <Clock className="text-emerald-500" />, bg: 'bg-emerald-50' },
  ];

  return (
    <div className="flex h-screen bg-[#f8f9ff]">
      <Sidebar />
      
      <main className="flex-1 flex flex-col overflow-y-auto p-8 custom-scrollbar">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 tracking-tight">👤 My Profile</h1>
          <p className="text-gray-500 font-medium">Your personal and professional information.</p>
        </header>

        <div className="grid grid-cols-3 gap-8">
          {/* Left Column: Avatar & Basic Info */}
          <section className="col-span-1 space-y-8">
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col items-center text-center">
              <div className="w-32 h-32 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 text-4xl font-bold mb-6 border-4 border-white shadow-lg">
                {employee?.full_name?.charAt(0).toUpperCase()}
              </div>
              <h2 className="text-2xl font-bold text-gray-900">{employee?.full_name}</h2>
              <p className="text-indigo-600 font-bold text-sm tracking-widest uppercase mt-1">{employee?.designation}</p>
              
              <div className="w-full h-px bg-gray-100 my-8" />
              
              <div className="w-full space-y-4 text-left">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-50 rounded-xl text-gray-400">
                    <Briefcase size={18} />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Employee ID</p>
                    <p className="text-sm font-bold text-gray-700">{employee?.employee_id}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-50 rounded-xl text-gray-400">
                    <Mail size={18} />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Email Address</p>
                    <p className="text-sm font-bold text-gray-700">{employee?.email}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-50 rounded-xl text-gray-400">
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-gray-400 uppercase">Department</p>
                    <p className="text-sm font-bold text-gray-700">{employee?.department}</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-indigo-600 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden group">
              <div className="relative z-10">
                <div className="p-3 bg-indigo-500/30 rounded-2xl w-fit mb-4">
                  <DollarSign size={24} className="text-indigo-100" />
                </div>
                <p className="text-indigo-200 font-bold text-xs uppercase tracking-widest">Monthly Salary</p>
                <p className="text-3xl font-black mt-1">${employee?.salary?.toLocaleString()}</p>
              </div>
              {/* Abstract Design Elements */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-16 -mt-16 group-hover:scale-125 transition-transform duration-700" />
              <div className="absolute bottom-0 left-0 w-16 h-16 bg-white/5 rounded-full -ml-8 -mb-8" />
            </div>
          </section>

          {/* Right Columns: Stats & Extended Details */}
          <section className="col-span-2 space-y-8">
            <div className="grid grid-cols-3 gap-6">
              {profileStats.map((stat, idx) => (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                  key={stat.label}
                  className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col gap-4"
                >
                  <div className={`w-12 h-12 rounded-2xl ${stat.bg} flex items-center justify-center`}>
                    {stat.icon}
                  </div>
                  <div>
                    <p className="text-3xl font-black text-gray-900">{stat.value}</p>
                    <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mt-1">{stat.label}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
              <h3 className="text-xl font-bold mb-8 flex items-center gap-2">
                <MapPin className="text-indigo-600" />
                Employment Details
              </h3>
              
              <div className="grid grid-cols-2 gap-y-10 gap-x-8">
                <div className="space-y-1">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                    <Calendar size={14} /> Joining Date
                  </p>
                  <p className="text-lg font-bold text-gray-800">{employee?.joining_date}</p>
                </div>
                
                <div className="space-y-1">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                    <ShieldCheck size={14} /> Employment Status
                  </p>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <p className="text-lg font-bold text-gray-800 capitalize">{employee?.status}</p>
                  </div>
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Reporting Manager ID</p>
                  <p className="text-lg font-bold text-gray-800">{employee?.manager_id || 'Not Assigned'}</p>
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Username</p>
                  <p className="text-lg font-bold text-gray-800">@{employee?.username}</p>
                </div>
              </div>

              <div className="mt-12 p-6 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
                <h4 className="text-sm font-bold text-gray-700 mb-2">Note:</h4>
                <p className="text-xs text-gray-500 leading-relaxed italic">
                  Some details are restricted for edits. Please contact HR Department at <span className="text-indigo-600 font-bold">hr@hrflux.ai</span> for any corrections or information updates regarding your profile.
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
