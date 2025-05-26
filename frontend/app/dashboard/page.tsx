// DashboardPage.tsx
'use client';

import ActionButtons from '@/components/ActionButtons';
import CoinDetailsCard from '@/components/CoinDetailsCard';
import CoinSelector from '@/components/CoinSelector';
import DepositModal from '@/components/DepositeModal';
import Header from '@/components/Header';
import RecentTradeReportCard from '@/components/RecentTradeReport';
import WithdrawModal from '@/components/WithdrawModal';
import { useGlobalContext } from '@/contexts/GlobalContext';
import { useAuth } from '@/hooks/userAuth';
import { fetchCoins } from '@/utils/api';
import { Coin } from '@/utils/interfaces';
import React, { useEffect } from 'react';

const DashboardPage: React.FC = () => {
  const {
    isDepositOpen,
    setIsDepositOpen,
    isWithdrawOpen,
    setIsWithdrawOpen,
    setCurrencies,
    setSelectedCoin,
    currencies: coins,
    selectedCoin
  } = useGlobalContext();

  const { user, checkAuth } = useAuth()


  useEffect(() => {
    fetchCoins(15)
      .then((data) => {
        if (data.data.length > 0) {
          if (setCurrencies) {
            setCurrencies(data.data! as Coin[]);
          }
          if (setSelectedCoin) {
            setSelectedCoin(data.data[0] as Coin);
          }
        }
      })
      .catch((error) => {
        console.error('Error fetching coins:', error);
      });
  }, []);

  return (
    <div className="min-h-screen bg-crypto-dark pt-20 px-6">
      <Header />
      <div className="flex flex-col lg:flex-row justify-center lg:space-x-6 sm:w-2/3 mx-auto mt-10">
        {/* Left Section: Selector */}
        <div className="lg:w-1/4">
          <CoinSelector
            coins={coins || []}
            selectedCoin={selectedCoin ?? null}
            onCoinChange={setSelectedCoin ?? (() => { })}
            balances={user?.balances || null}
          />
          <ActionButtons isCoinSelected={selectedCoin !== null} />
        </div>

        {/* Right Section: Coin Details */}
        <div className="flex-1 mt-6 lg:mt-0">
          <CoinDetailsCard coin={selectedCoin ?? null} balances={user?.balances || null} />
        </div>

        <div className="lg:w-1/4">
          <RecentTradeReportCard
            report={''}
          />
        </div>
      </div>

      {isDepositOpen && selectedCoin && setIsDepositOpen && (
        <DepositModal
          coin={selectedCoin}
          currentBalance={user?.balances?.[selectedCoin.symbol] ? parseFloat(user.balances[selectedCoin.symbol].toFixed(2)) : 0}
          onClose={() => setIsDepositOpen(false)}
          onDeposit={() => checkAuth()}
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