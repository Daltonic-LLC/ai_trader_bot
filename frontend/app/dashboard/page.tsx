import Header from '@/components/Header';
import TradingInstanceCard from '@/components/TradingInstanceCard';
import React from 'react';

// Define interface for trading instance
interface TradingInstance {
  id: number;
  coin: string;
  capital: number;
  position: number;
  lastRecommendation: 'BUY' | 'SELL' | 'HOLD';
}

// Static sample data
const sampleInstances: TradingInstance[] = [
  {
    id: 1,
    coin: 'btc',
    capital: 1000.0,
    position: 0.05,
    lastRecommendation: 'BUY',
  },
  {
    id: 2,
    coin: 'eth',
    capital: 500.0,
    position: 0.0,
    lastRecommendation: 'SELL',
  },
  {
    id: 3,
    coin: 'ltc',
    capital: 200.0,
    position: 1.2,
    lastRecommendation: 'HOLD',
  },
];

const Page: React.FC = () => {
  return (
    <div className="min-h-screen bg-crypto-dark pt-20 px-6">
      <Header />
      <div className="mb-6">
        <button className="bg-gradient-to-r from-crypto-blue to-crypto-green text-white
        px-6 py-3 rounded-lg font-semibold hover:from-crypto-blue/80 hover:to-crypto-green/80
        transition-all shadow-md hover:shadow-lg">
          Create New Trading Instance
        </button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {sampleInstances.map((instance) => (
          <TradingInstanceCard key={instance.id} instance={instance} />
        ))}
      </div>
    </div>
  );
};

export default Page;