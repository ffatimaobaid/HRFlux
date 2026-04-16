'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';

export default function Home() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen bg-[#faf5ff] items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center max-w-2xl text-center"
      >
        <h2 className="text-3xl sm:text-4xl font-bold mb-8">
          Welcome To
        </h2>

        <div className="flex flex-col items-center mb-10">
          <div className="mb-2">
            <img src="/logo.jpeg" alt="HRFlux Logo" className="w-24 h-24 object-contain" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-widest uppercase">
            HRFLUX
          </h1>
        </div>

        <h2 className="text-4xl sm:text-5xl font-bold mb-6">
          Your Smart HR Assistant
        </h2>

        <p className="text-gray-700 text-lg sm:text-xl mb-12 max-w-md mx-auto leading-relaxed">
          Your AI-powered HR assistant, making workplace tasks simple, quick, and effortless.
        </p>

        <button
          onClick={() => router.push('/login')}
          className="bg-[#7b2ff7] hover:opacity-90 text-white font-semibold py-3 px-16 rounded-2xl transition-all duration-200 text-lg shadow-sm active:scale-[0.98]"
        >
          Continue
        </button>
      </motion.div>
    </div>
  );
}
