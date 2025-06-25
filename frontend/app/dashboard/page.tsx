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
import { Coin, ExecutionLog, InvestmentData } from '@/utils/interfaces';
import React, { useEffect } from 'react';

// Fake data matching the provided interfaces
const fakeCoins: Coin[] = [
  {
    rank: "1",
    name: "Bitcoin",
    slug: "bitcoin",
    symbol: "BTC",
    market_cap: "1200000000000",
    price: "60000",
    circulating_supply: "19000000",
    volume_24h: "30000000000",
    percent_1h: "0.5",
    percent_24h: "2.3",
    percent_7d: "-1.2"
  },
  {
    rank: "2",
    name: "Ethereum",
    slug: "ethereum",
    symbol: "ETH",
    market_cap: "400000000000",
    price: "3000",
    circulating_supply: "120000000",
    volume_24h: "15000000000",
    percent_1h: "0.3",
    percent_24h: "1.8",
    percent_7d: "0.5"
  }
];

const fakeTradingBotLog: ExecutionLog = {
  job_name: "trading_bot",
  last_execution: "2023-05-01T12:00:00Z",
  next_execution: "2023-05-02T12:00:00Z"
};

const fakeNewsSentimentLog: ExecutionLog = {
  job_name: "news_sentiment",
  last_execution: "2023-05-01T00:00:00Z",
  next_execution: "2023-05-02T00:00:00Z"
};

const fakeReports: { [key: string]: string } = {
  bitcoin: "Report for BITCOIN:\n        - Current Price: $105949.99\n        - 24h Price Change: 1.94%\n        - 24h Low: $103712.61\n        - 24h High: $106316.83\n        - 24h Volume: $56,690,000,000.00\n        - Market Cap: $2,100,000,000,000.00\n        - Predicted Close: $65911.22\n        - News Sentiment: 0.40\n        - News Text: $BTC 🚀 Bitcoin Breaks Above $105K! 🚨 JUST IN: BlackRock buys 2,113 $BTC worth $222 million, pushing total holdings to a staggering 685,000 Bitcoin. $BTC Dominance Faces Critical Rejection Zone! BREAKING : Trump said Iran and Israel agree to a ceasefire. $BTC testing key value area low. 📢 #TRUMP Media...\n        - Recommendation: BUY\n- Current Capital: $5.97\nTrade Details:\nSimulated BUY: 0.000084 BITCOIN at $105949.99\nAction: Manually buy on an exchange.",
  ethereum: "Report for ETHEREUM:\n        - Current Price: $2441.17\n        - 24h Price Change: 3.79%\n        - 24h Low: $2338.83\n        - 24h High: $2481.22\n        - 24h Volume: $23,670,000,000.00\n        - Market Cap: $294,690,000,000.00\n        - Predicted Close: $2499.81\n        - News Sentiment: 0.20\n        - News Text: 🚨 CMC News: Ethereum Whales Open $100 Million Leveraged Positions Amid Global Uncertainty. ETH: Percent Supply in Profit $ETH Outlook 🔵 Ethereum developers issue proposal to halve block slot time to boost transaction speed Analyzing Ethereum’s 8% rebound - Will Q3 push ETH to $3K? I'm bullish on $ETH Ethereum...\n        - Recommendation: SELL\n- Current Capital: $74.02\nTrade Details:\nHOLD: Profit margin 1.15% below tier thresholds."
};



const fakeInvestmentDatas: { [key: string]: InvestmentData } = {
  bitcoin: {
    user_investment: {
      original_investment: 10000,
      total_deposits: 15000,
      total_withdrawals: 2000,
      net_investment: 13000,
      ownership_percentage: 100,
      current_share_value: 15000,
      realized_gains: 1000,
      unrealized_gains: 4000,
      total_gains: 5000,
      overall_profit_loss: 2000,
      performance_percentage: 15.38,
      portfolio_breakdown: {
        cash_portion: 3000,
        position_portion: 12000,
        total_value: 15000
      }
    },
    coin_performance: {
      current_price: "60000",
      price_change_24h: "2.3",
      volume_24h: "30000000000",
      market_cap: "1200000000000",
      total_deposits: 15000,
      total_withdrawals: 2000,
      net_deposits: 13000,
      current_capital: 15000,
      position_quantity: 0.2,
      position_value: 12000,
      total_portfolio_value: 15000,
      total_realized_profits: 1000,
      total_unrealized_gains: 4000,
      total_gains: 5000,
      overall_performance: 15.38
    },
    coin: "bitcoin",
    timestamp: "2023-05-01T12:00:00Z"
  },
  ethereum: {
    user_investment: {
      original_investment: 5000,
      total_deposits: 7000,
      total_withdrawals: 1000,
      net_investment: 6000,
      ownership_percentage: 100,
      current_share_value: 7500,
      realized_gains: 500,
      unrealized_gains: 2000,
      total_gains: 2500,
      overall_profit_loss: 1500,
      performance_percentage: 25.0,
      portfolio_breakdown: {
        cash_portion: 1500,
        position_portion: 6000,
        total_value: 7500
      }
    },
    coin_performance: {
      current_price: "3000",
      price_change_24h: "1.8",
      volume_24h: "15000000000",
      market_cap: "400000000000",
      total_deposits: 7000,
      total_withdrawals: 1000,
      net_deposits: 6000,
      current_capital: 7500,
      position_quantity: 2.0,
      position_value: 6000,
      total_portfolio_value: 7500,
      total_realized_profits: 500,
      total_unrealized_gains: 2000,
      total_gains: 2500,
      overall_performance: 25.0
    },
    coin: "ethereum",
    timestamp: "2023-05-01T12:00:00Z"
  }
};

const MAX_COINS: number = Number(process.env.NEXT_PUBLIC_MAX_COINS) || 0;

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
    const log = {
      data: {
        trading_bot: fakeTradingBotLog,
        news_sentiment: fakeNewsSentimentLog
      }
    };
    if (log.data && Object.keys(log.data).length > 0) {
      setLastTrade(log.data.trading_bot);
      setLastReport(log.data.news_sentiment);
    }
  };

  const getCoinReport = async (coin: string) => {
    const reportText = fakeReports[coin] || '';
    setReport(reportText);
  };

  const getCoinInvestment = async (coin: string) => {
    const data = fakeInvestmentDatas[coin] || null;
    setInvestmentData(data);
  };

  const getCoins = async () => {
    const data = { data: fakeCoins.slice(0, MAX_COINS || fakeCoins.length) };
    if (data.data.length > 0) {
      if (setCurrencies) {
        setCurrencies(data.data as Coin[]);
      }
      if (setSelectedCoin) {
        setSelectedCoin(data.data[0] as Coin);
        await getCoinReport(data.data[0].slug);
        await getCoinInvestment(data.data[0].slug);
      }
    }
  };

  useEffect(() => {
    getCoins();
    getExecutionLog();
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
                getCoinInvestment(coin.slug);
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