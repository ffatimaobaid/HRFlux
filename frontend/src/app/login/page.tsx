'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { authApi } from '@/lib/api';
import { LogIn, UserPlus, Bot, Users } from 'lucide-react';
import { Input, Button } from 'antd';

export default function LoginPage() {
  const router = useRouter();
  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      if (isSignup) {
        await authApi.signup({ username, password });
        setIsSignup(false);
        setError('Account created! Please login.');
      } else {
        const res = await authApi.login({ username: email, password });
        localStorage.setItem('hrflux_token', res.data.token);
        localStorage.setItem('hrflux_user', res.data.username);
        localStorage.setItem('hrflux_employee_id', res.data.employee_id);
        
        const userRole = res.data.role || 'employee';
        const isAdmin = userRole === 'admin';
        
        // Immediate cookie setting for middleware sync
        document.cookie = `hrflux_role=${userRole}; path=/; max-age=86400; samesite=lax`;
        
        // Small delay to ensure cookie is processed by browser
        setTimeout(() => {
          if (isAdmin) {
            router.push('/admin');
          } else {
            router.push('/dashboard');
          }
        }, 100);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'An error occurred during authentication');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#faf5ff] items-center justify-center p-4">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex w-full max-w-4xl bg-white rounded-3xl overflow-hidden shadow-2xl"
      >
        {/* Left Side: Form */}
        <div className="flex-1 p-12">
          <div className="flex items-center gap-3 mb-8">
            <div className="bg-black p-2 rounded-lg text-white">
              <Bot size={24} />
            </div>
            <span className="text-2xl font-bold tracking-tight">HRFLUX</span>
          </div>

          <h2 className="text-3xl font-bold mb-2">
            {isSignup ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="text-gray-500 mb-8">
            {isSignup 
              ? 'Sign up to start using your AI-powered HR assistant.' 
              : 'AI-powered HR assistant, tailored to your workplace.'}
          </p>

          <form onSubmit={handleAuth} className="space-y-4">
            {isSignup && (
              <div className="mb-4">
                <label className="block text-[13px] font-semibold text-gray-700 mb-1.5 px-0.5">Username</label>
                <Input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full text-base"
                  size="large"
                  placeholder="Choose a username"
                  required
                />
              </div>
            )}
            <div className="mb-4">
              <label className="block text-[13px] font-semibold text-gray-700 mb-1.5 px-0.5">
                {isSignup ? 'Email' : 'Username / Email'}
              </label>
              <Input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full text-base"
                size="large"
                placeholder={isSignup ? 'Enter your email' : 'Enter your email or username'}
                required
              />
            </div>
            <div className="mb-2">
              <label className="block text-[13px] font-semibold text-gray-700 mb-1.5 px-0.5">Password</label>
              <Input.Password
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full text-base"
                size="large"
                placeholder="Enter your password"
                required
              />
            </div>

            {!isSignup && (
              <div className="text-right mb-4">
                <button type="button" className="text-[13px] text-[#7b2ff7] font-medium hover:underline">
                  Forgot your password?
                </button>
              </div>
            )}

            {error && (
              <div className={`p-3 rounded-xl text-sm ${error.includes('created') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                {error}
              </div>
            )}

            <Button
              type="primary"
              htmlType="submit"
              size="large"
              loading={loading}
              className="w-full mt-4 font-bold h-12 text-base transition-opacity hover:opacity-90 active:scale-[0.98]"
              icon={isSignup ? <UserPlus size={18} /> : <LogIn size={18} />}
            >
              {isSignup ? 'Create Account' : 'Login'}
            </Button>
          </form>

          <div className="mt-8 text-center px-4">
            <button
              type="button"
              onClick={() => setIsSignup(!isSignup)}
              className="text-gray-500 text-sm font-medium hover:text-[#7b2ff7] transition-colors"
            >
              {isSignup ? 'Already have an account? Login' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>

        {/* Right Side: Visual */}
        <div className="hidden lg:flex flex-1 bg-[#7b2ff7] p-12 items-center justify-center">
          <div className="max-w-xs text-white text-center">
            <motion.div 
              animate={{ y: [0, -10, 0] }}
              transition={{ repeat: Infinity, duration: 4 }}
              className="text-7xl mb-6 flex justify-center"
            >
              {isSignup ? <Users size={80} /> : <Bot size={80} />}
            </motion.div>
            <h3 className="text-2xl font-bold mb-4">
              {isSignup ? 'Welcome to HRFLUX.' : 'AI-Powered HR Tailored for You.'}
            </h3>
            <p className="text-indigo-100 opacity-80 leading-relaxed">
              Get instant answers to HR questions, policies, and workplace queries.
            </p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
