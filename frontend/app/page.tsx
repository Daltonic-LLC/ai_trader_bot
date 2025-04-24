"use client";
import GoogleSignInButton from "@/components/GoogleSignInButton";

export default function Home() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-crypto-dark px-5">
      <div className="p-8 bg-crypto-gray rounded-xl shadow-lg max-w-md w-full border border-crypto-blue/20">
        <h1 className="text-3xl font-bold text-center text-white mb-6">
          AI Crypto Trader
        </h1>
        <p className="text-gray-400 text-center mb-6">
          Sign in to manage your AI-powered trading bot
        </p>
        <GoogleSignInButton />
      </div>
    </div>
  );
}
