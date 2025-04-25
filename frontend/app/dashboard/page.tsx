// DashboardPage.tsx
'use client';

import ActionButtons from '@/components/ActionButtons';
import CoinDetailsCard from '@/components/CoinDetailsCard';
import CoinSelector from '@/components/CoinSelector';
import DepositModal from '@/components/DepositeModal';
import Header from '@/components/Header';
import WithdrawModal from '@/components/WithdrawModal';
import { useGlobalContext } from '@/contexts/GlobalContext';
import { Coin } from '@/utils/interfaces';
import React, { useEffect, useState } from 'react';

const DashboardPage: React.FC = () => {
  const [coins, setCoins] = useState<Coin[]>([]);
  const [selectedCoin, setSelectedCoin] = useState<Coin | null>(null);
  const { isDepositOpen, setIsDepositOpen, isWithdrawOpen, setIsWithdrawOpen } =
    useGlobalContext();

  const fetchCoins = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/coin/top_coins?limit=15`
      );
      const data = await response.json();
      setCoins(data.data);
      setSelectedCoin(data.data[0]);
    } catch (error) {
      console.error('Error fetching coins:', error);
    }
  };

  useEffect(() => {
    fetchCoins();
  }, []);

  return (
    <div className="min-h-screen bg-crypto-dark pt-20 px-6">
      <Header />
      <div className="flex flex-col lg:flex-row justify-center lg:space-x-6 sm:w-2/3 mx-auto mt-10">
        {/* Left Section: Selector */}
        <div className="lg:w-1/3">
          <CoinSelector
            coins={coins}
            selectedCoin={selectedCoin}
            onCoinChange={setSelectedCoin}
          />
          <ActionButtons isCoinSelected={selectedCoin !== null} />
        </div>

        {/* Right Section: Coin Details */}
        <div className="flex-1 mt-6 lg:mt-0">
          <CoinDetailsCard coin={selectedCoin} />
        </div>
      </div>

      {isDepositOpen && selectedCoin && setIsDepositOpen && (
        <DepositModal
          coin={selectedCoin}
          currentBalance={0}
          onClose={() => setIsDepositOpen(false)}
          onDeposit={() => { }}
        />
      )}
      {isWithdrawOpen && selectedCoin && setIsWithdrawOpen && (
        <WithdrawModal
          coin={selectedCoin}
          currentBalance={0}
          onClose={() => setIsWithdrawOpen(false)}
          onWithdraw={() => { }}
        />
      )}
    </div>
  );
};

export default DashboardPage;