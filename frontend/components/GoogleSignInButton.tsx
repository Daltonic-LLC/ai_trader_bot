'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { FcGoogle } from 'react-icons/fc';
import Cookies from 'js-cookie';

const GoogleSignInButton: React.FC = () => {
  const router = useRouter();

  const handleFakeSignIn = () => {
    // Simulate storing token and user info
    const fakeToken = 'fake_access_token';
    const fakeUser = {
      name: 'Demo User',
      email: 'demo@example.com',
      role: 'admin',
    };

    Cookies.set('access_token', fakeToken, { expires: 0.5 }); // 12 hours
    Cookies.set('bot_user', JSON.stringify(fakeUser), { expires: 0.5 });

    console.log('[FAKE LOGIN] Token and user info set in cookies:', {
      token: fakeToken,
      user: fakeUser,
    });

    // Simulate redirect to dashboard
    router.push('/dashboard');
  };

  return (
    <div className="flex justify-center items-center min-h-[50px]">
      <button
        onClick={handleFakeSignIn}
        className="flex items-center justify-center gap-3 bg-crypto-gray text-white
        py-3 px-8 rounded-lg font-semibold hover:bg-crypto-blue/90 transition-all w-[250px]
        transform hover:scale-105 hover:shadow-crypto-blue/50 shadow-md animate-pulse-slow"
      >
        <FcGoogle className="w-6 h-6" />
        Sign in with Google
      </button>
    </div>
  );
};

export default GoogleSignInButton;
