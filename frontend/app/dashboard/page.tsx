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
import { fetchCoinReport, fetchCoins, fetchExecutionLog } from '@/utils/api';
import { Coin, ExecutionLog } from '@/utils/interfaces';
import React, { useEffect } from 'react';

const DashboardPage: React.FC = () => {
  const [report, setReport] = React.useState<string | null>(null);
  const [lastTrade, setLastTrade] = React.useState<ExecutionLog | null>(null);
  const [lastReport, setLastReport] = React.useState<ExecutionLog | null>(null);

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

  const getExecutionLog = async () => {
    const log = await fetchExecutionLog();
    if (log.data && Object.keys(log.data).length > 0) {
      setLastTrade(log.data.data_cleanup);
      setLastReport(log.data.coin_history);
    }
  }

  const getCoinReport = async (coin: string) => {
    const report = await fetchCoinReport(coin)

    if (report.data && Object.keys(report.data).length > 0) {
      setReport(report.data.report);
    } else {
      setReport('');
    }
  }

  const getCoins = async () => fetchCoins(15)
    .then(async (data) => {
      if (data.data.length > 0) {
        if (setCurrencies) {
          setCurrencies(data.data! as Coin[]);
        }
        if (setSelectedCoin) {
          setSelectedCoin(data.data[0] as Coin);
          await getCoinReport(data.data[0].slug)
        }
      }
    })
    .catch((error) => {
      console.error('Error fetching coins:', error);
    });

  useEffect(() => {
    getCoins()
    getExecutionLog()
  }, []);

  return (
    <div className="min-h-screen bg-crypto-dark pt-20 px-6">
      <Header />
      <div className="flex flex-col lg:flex-row justify-center lg:space-x-6 sm:w-4/5 mx-auto mt-10">
        {/* Left Section: Selector */}
        <div className="lg:w-1/5">
          <CoinSelector
            coins={coins || []}
            selectedCoin={selectedCoin ?? null}
            onCoinChange={(coin: Coin | null) => {
              if (coin) getCoinReport(coin.slug);
              if (setSelectedCoin) {
                setSelectedCoin(coin);
              }
            }}
            balances={user?.balances || null}
          />
          <ActionButtons isCoinSelected={selectedCoin !== null} />
        </div>

        {/* Right Section: Coin Details */}
        <div className="flex-1 mt-6 lg:mt-0">
          <CoinDetailsCard coin={selectedCoin ?? null} balances={user?.balances || null} executionLog={lastTrade || null} />
        </div>

        <div className="lg:w-1/3">
          <RecentTradeReportCard
            report={report || ''} executionLog={lastReport || null}
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