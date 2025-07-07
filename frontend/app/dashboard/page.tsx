// DashboardPage.tsx
'use client';

import ActionButtons from '@/components/ActionButtons';
import CoinDetailsCard from '@/components/CoinDetailsCard';
import CoinSelector from '@/components/CoinSelector';
import DepositModal from '@/components/DepositeModal';
import Header from '@/components/Header';
import InvestmentCard from '@/components/InvestmentCard';
import ProfitTrendChart from '@/components/ProfitTrendChart';
import RecentTradeReportCard from '@/components/RecentTradeReport';
import WithdrawModal from '@/components/WithdrawModal';
import { useGlobalContext } from '@/contexts/GlobalContext';
import { fetchCoinInvestment, fetchCoinReport, fetchCoins, fetchExecutionLog, fetchProfitTrend } from '@/utils/api';
import { Coin, ExecutionLog, InvestmentData, PortfolioData } from '@/utils/interfaces';
import React, { useEffect, useState } from 'react';

const MAX_COINS: number = Number(process.env.NEXT_PUBLIC_MAX_COINS) || 0;

const DashboardPage: React.FC = () => {
  const [report, setReport] = React.useState<string | null>(null);
  const [lastTrade, setLastTrade] = React.useState<ExecutionLog | null>(null);
  const [lastReport, setLastReport] = React.useState<ExecutionLog | null>(null);
  const [portfolioData, setPortfolioData] = React.useState<PortfolioData[] | null>(null);
  const [investmentData, setInvestmentData] = React.useState<InvestmentData | null>(null);
  const [isLoading, setIsLoading] = useState(true); // Add loading state

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

  const getExecutionLog = async () => {
    const log = await fetchExecutionLog();
    if (log.data && Object.keys(log.data).length > 0) {
      setLastTrade(log.data.trading_bot);
      setLastReport(log.data.news_sentiment);
    }
  };

  const getCoinReport = async (coin: string) => {
    const report = await fetchCoinReport(coin);
    if (report.data && Object.keys(report.data).length > 0) {
      setReport(report.data.report);
    } else {
      setReport('');
    }
  };

  const getProfitTrend = async (coin: string) => {
    try {
      const data = await fetchProfitTrend(coin);
      if (data && Object.keys(data).length > 0) {
        setPortfolioData(data);
      }
    } catch (error) {
      console.error('Error fetching coin profit trend:', error);
      setPortfolioData(null);
    }
  };

  const getCoinInvestment = async (coin: string) => {
    try {
      const data = await fetchCoinInvestment(coin);
      if (data && Object.keys(data).length > 0) {
        setInvestmentData(data);
      }
    } catch (error) {
      console.error('Error fetching coin investment:', error);
      setInvestmentData(null);
    }
  };

  const getCoins = async () => {
    try {
      const data = await fetchCoins(MAX_COINS);
      if (data.data.length > 0) {
        if (setCurrencies) {
          setCurrencies(data.data! as Coin[]);
        }
        if (setSelectedCoin) {
          setSelectedCoin(data.data[0] as Coin);
          // Wait for all coin-specific data to be fetched
          await Promise.all([
            getCoinReport(data.data[0].slug),
            getProfitTrend(data.data[0].slug),
            getCoinInvestment(data.data[0].slug)
          ]);
        }
      }
    } catch (error) {
      console.error('Error fetching coins:', error);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      try {
        // Wait for both coins (and its dependent data) and execution logs to load
        await Promise.all([getCoins(), getExecutionLog()]);
      } catch (error) {
        console.error('Error loading data:', error);
      } finally {
        setIsLoading(false); // Set loading to false regardless of success or failure
      }
    };
    loadData();
  }, []);

  // Show loading indicator while data is being fetched
  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Render the full dashboard once data is loaded
  return (
    <div className="min-h-screen bg-crypto-dark pt-20 px-6">
      <Header />
      <div className='flex flex-col lg:flex-row justify-center lg:space-x-6 sm:w-11/12 mx-auto mt-10'>
        {/* Left Section: Selector */}
        <div className="lg:w-3/12 mb-6 lg:mb-0">
          <CoinSelector
            coins={coins || []}
            selectedCoin={selectedCoin ?? null}
            onCoinChange={(coin: Coin | null) => {
              if (coin) {
                getCoinReport(coin.slug);
                getCoinInvestment(coin.slug);
                getProfitTrend(coin.slug);
              }
              if (setSelectedCoin) {
                setSelectedCoin(coin);
              }
            }}
          />
          <ActionButtons isCoinSelected={selectedCoin !== null} />
        </div>
        <div className="flex flex-col lg:space-x-6 space-y-4 sm:w-4/5 mx-auto w-full">
          <div className='flex-1 flex flex-col lg:flex-row lg:space-x-6 space-y-6 lg:space-y-0 mr-0'>
            {/* Right Section: Coin Details */}
            <div className="flex-1 lg:mt-0">
              <CoinDetailsCard coin={selectedCoin ?? null} executionLog={lastTrade || null} />
            </div>
            {investmentData && investmentData.user_investment && (
              <div className="lg:w-5/12">
                <InvestmentCard data={investmentData} />
              </div>
            )}
          </div>
          {portfolioData && portfolioData.length > 0 && (
            <div className='flex flex-col lg:flex-row lg:space-x-6 space-y-6 lg:space-y-0 mr-0'>
              <ProfitTrendChart data={portfolioData} coin={selectedCoin ?? null} executionLog={lastTrade || null} />
            </div>
          )}
          <div className='flex flex-col lg:flex-row lg:space-x-6 space-y-6 lg:space-y-0'>
            <RecentTradeReportCard report={report || ''} executionLog={lastReport || null} />
          </div>
        </div>
      </div>
      {isDepositOpen && selectedCoin && setIsDepositOpen && (
        <DepositModal
          coin={selectedCoin}
          currentBalance={
            investmentData?.user_investment?.net_investment
              ? parseFloat(investmentData.user_investment.net_investment.toFixed(2))
              : 0
          }
          onClose={() => setIsDepositOpen(false)}
          onDeposit={() => {
            getCoinInvestment(selectedCoin.slug);
          }}
        />
      )}
      {isWithdrawOpen && selectedCoin && setIsWithdrawOpen && (
        <WithdrawModal
          coin={selectedCoin}
          currentBalance={
            investmentData?.user_investment?.net_investment
              ? parseFloat(investmentData.user_investment.net_investment.toFixed(2))
              : 0
          }
          onClose={() => setIsWithdrawOpen(false)}
          onWithdraw={() => {
            getCoinInvestment(selectedCoin.slug);
          }}
        />
      )}
    </div>
  );
};

export default DashboardPage;