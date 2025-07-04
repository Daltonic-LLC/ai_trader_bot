import { Coin, ExecutionLog } from '@/utils/interfaces';
import React from 'react';
import { MdCopyAll } from "react-icons/md";

interface CoinDetailsCardProps {
    coin: Coin | null;
    executionLog?: ExecutionLog | null;
}

const CoinDetailsCard: React.FC<CoinDetailsCardProps> = ({ coin, executionLog }) => {
    if (!coin) {
        return (
            <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/20 text-gray-400 text-center">
                Select a coin to view details
            </div>
        );
    }

    const copyAllDetails = () => {
        const coinData = {
            ...coin,
            executedAt: executionLog?.last_execution
                ? new Date(executionLog.last_execution).toLocaleString()
                : 'N/A'
        };
        navigator.clipboard.writeText(JSON.stringify(coinData, null, 2));
    };

    return (
        <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/30 hover:border-crypto-blue transition-all relative">
            <div className="flex justify-between items-center bg-gradient-to-r from-crypto-blue to-crypto-green text-white rounded-t-xl">
                <h2 className="text-xl font-semibold">
                    {`${coin.name}`}
                </h2>

                <button
                    type="button"
                    className="p-2 rounded hover:bg-white/10 transition cursor-pointer"
                    title="Copy all coin details to clipboard"
                    onClick={copyAllDetails}
                >
                    <MdCopyAll className="w-5 h-5" />
                </button>
            </div>
            <div className="mt-4 space-y-3">
                <div className="flex justify-between items-center text-gray-300">
                    <span>Rank</span>
                    <span className="font-medium text-white">{coin.rank}</span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>Price</span>
                    <span className="font-medium text-white">{coin.price}</span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>Market Cap</span>
                    <span className="font-medium text-white">{coin.market_cap}</span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>Circulating Supply</span>
                    <span className="font-medium text-white">{coin.circulating_supply}</span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>24h Volume</span>
                    <span className="font-medium text-white">{coin.volume_24h}</span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>1h Change</span>
                    <span
                        className={`font-medium flex items-center gap-1 ${coin.percent_1h.startsWith('-') ? 'text-red-500' : 'text-crypto-green'
                            }`}
                    >
                        {coin.percent_1h.startsWith('-') ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                            </svg>
                        )}
                        {coin.percent_1h}
                    </span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>24h Change</span>
                    <span
                        className={`font-medium flex items-center gap-1 ${coin.percent_24h.startsWith('-') ? 'text-red-500' : 'text-crypto-green'
                            }`}
                    >
                        {coin.percent_24h.startsWith('-') ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                            </svg>
                        )}
                        {coin.percent_24h}
                    </span>
                </div>
                <div className="flex justify-between items-center text-gray-300">
                    <span>7d Change</span>
                    <span
                        className={`font-medium flex items-center gap-1 ${coin.percent_7d.startsWith('-') ? 'text-red-500' : 'text-crypto-green'
                            }`}
                    >
                        {coin.percent_7d.startsWith('-') ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                            </svg>
                        ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                            </svg>
                        )}
                        {coin.percent_7d}
                    </span>
                </div>
            </div>

            <div className="text-gray-400 text-xs pt-3">
                Executed at {' '} {executionLog?.last_execution
                    ? new Date(executionLog.last_execution).toLocaleString()
                    : 'N/A'}
            </div>
        </div>
    );
};

export default CoinDetailsCard;