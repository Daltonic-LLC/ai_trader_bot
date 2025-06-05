// DashboardPage.tsx
'use client';

import ActionButtons from '@/components/ActionButtons';
import CoinDetailsCard from '@/components/CoinDetailsCard';
import CoinSelector from '@/components/CoinSelector';
import DepositModal from '@/components/DepositeModal';
import Header from '@/components/Header';
import InvestmentCard from '@/components/InvestmentCard';
import RecentTradeReportCard from '@/components/RecentTradeReport';
import WithdrawModal from '@/components/WithdrawModal';
import { useGlobalContext } from '@/contexts/GlobalContext';
import { fetchCoinInvestment, fetchCoinReport, fetchCoins, fetchExecutionLog } from '@/utils/api';
import { Coin, ExecutionLog, InvestmentData } from '@/utils/interfaces';
import React, { useEffect } from 'react';

const DashboardPage: React.FC = () => {
  const [report, setReport] = React.useState<string | null>(null);
  const [lastTrade, setLastTrade] = React.useState<ExecutionLog | null>(null);
  const [lastReport, setLastReport] = React.useState<ExecutionLog | null>(null);
  const [investmentData, setInvestmentData] = React.useState<InvestmentData | null>(null);

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
  }

  const getCoinReport = async (coin: string) => {
    const report = await fetchCoinReport(coin)

    if (report.data && Object.keys(report.data).length > 0) {
      setReport(report.data.report);
    } else {
      setReport('');
    }
  }

  const getCoinInvestment = async (coin: string) => fetchCoinInvestment(coin)
    .then((data) => {
      if (data && Object.keys(data).length > 0) {

        setInvestmentData(data);
      }
    })
    .catch((error) => {
      console.error('Error fetching coin investment:', error);
      setInvestmentData(null);
    });

  const getCoins = async () => fetchCoins(15)
    .then(async (data) => {
      if (data.data.length > 0) {
        if (setCurrencies) {
          setCurrencies(data.data! as Coin[]);
        }
        if (setSelectedCoin) {
          setSelectedCoin(data.data[0] as Coin);
          await getCoinReport(data.data[0].slug)
          await getCoinInvestment(data.data[0].slug);
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
      <div className='flex flex-col lg:flex-row justify-center lg:space-x-6 sm:w-11/12 mx-auto mt-10'>
        {/* Left Section: Selector */}
        <div className="lg:w-3/12 mb-6 lg:mb-0">
          <CoinSelector
            coins={coins || []}
            selectedCoin={selectedCoin ?? null}
            onCoinChange={(coin: Coin | null) => {
              if (coin) {
                getCoinReport(coin.slug);
                getCoinInvestment(coin.slug)
              }

              if (setSelectedCoin) {
                setSelectedCoin(coin);
              }
            }}
          />
          <ActionButtons isCoinSelected={selectedCoin !== null} />
          {/* <div className='pt-4'></div> */}
        </div>
        <div className="flex flex-col lg:space-x-6 space-y-4 sm:w-4/5 mx-auto w-full">

          <div className='flex-1 flex flex-col lg:flex-row lg:space-x-6 space-y-6 lg:space-y-0 mr-0'>
            {/* Right Section: Coin Details */}
            <div className="flex-1 lg:mt-0">
              <CoinDetailsCard coin={selectedCoin ?? null} executionLog={lastTrade || null} />
            </div>

            {investmentData && investmentData.user_investment &&
              <div className="lg:w-5/12">
                <InvestmentCard data={investmentData} />
              </div>
            }
          </div>

          <div className='flex flex-col lg:flex-row lg:space-x-6 space-y-6 lg:space-y-0'>
            <RecentTradeReportCard
              report={report || ''} executionLog={lastReport || null}
            />
          </div>
        </div>

      </div>

      {isDepositOpen && selectedCoin && setIsDepositOpen && (
        <DepositModal
          coin={selectedCoin}
          currentBalance={
            investmentData?.user_investment?.investment
              ? parseFloat(investmentData.user_investment.investment.toFixed(2))
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
            investmentData?.user_investment?.investment
              ? parseFloat(investmentData.user_investment.investment.toFixed(2))
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