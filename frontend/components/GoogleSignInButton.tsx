'use client';

import React, { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';
import { FcGoogle } from 'react-icons/fc';
import { useAuth } from '@/hooks/userAuth';

// Assuming useAuth hook exists; if not, comment out and use fallback

// TypeScript declarations for Google Sign-in
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: GoogleCredentialResponse) => void;
          }) => void;
          renderButton: (
            element: HTMLElement | null,
            options: {
              theme: string;
              size: string;
              width: number;
              type: string;
            }
          ) => void;
        };
      };
    };
  }
}

interface GoogleCredentialResponse {
  credential: string;
}

const GoogleSignInButton: React.FC = () => {
  const router = useRouter();
  // Use useAuth if available; otherwise, define a fallback checkAuth
  const { checkAuth } = useAuth() || {
    checkAuth: async () => {
      console.log('Placeholder checkAuth');
      return true; // Simulate successful auth check
    },
  };

  const handleCredentialResponse = useCallback(
    async (response: GoogleCredentialResponse) => {
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            token: response.credential,
          }),
        });

        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.detail || 'Login failed');
        }

        Cookies.set('access_token', data.token.access_token, {
          expires: 720 / 1440, // 12 hours
        });
        Cookies.set('bot_user', JSON.stringify(data), {
          expires: 720 / 1440,
        });

        await checkAuth();
        router.push('/dashboard');
      } catch (error) {
        console.error('Login failed:', error);
      }
    },
    [checkAuth, router]
  );

  useEffect(() => {
    const initializeGoogleSignIn = async () => {
      try {
        await window.google?.accounts.id.initialize({
          client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
          callback: handleCredentialResponse,
        });

        window.google?.accounts.id.renderButton(
          document.getElementById('google-signin-button') ?? document.body,
          {
            theme: 'outline',
            size: 'large',
            width: 250,
            type: 'standard',
          }
        );
      } catch (error) {
        console.error('Error initializing Google Sign-In:', error);
      }
    };

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = initializeGoogleSignIn;
    document.head.appendChild(script);

    return () => {
      document.head.removeChild(script);
    };
  }, [handleCredentialResponse]);

  return (
    <div className="flex justify-center items-center min-h-[50px]">
      <button
        id="google-signin-button"
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