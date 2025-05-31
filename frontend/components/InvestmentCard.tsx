import { InvestmentData } from '@/utils/interfaces';
import React from 'react';

interface InvestmentCardProps {
    data: InvestmentData;
}

const InvestmentCard: React.FC<InvestmentCardProps> = ({ data }) => {
    const { user_investment, coin_performance } = data;


    return (
        <div className="p-6 rounded-xl shadow-lg border border-crypto-blue/30 bg-[#0F172A] w-full">

            {/* User Investment Section */}
            <div className="mb-6">
                <h3 className="text-xl font-semibold text-white mb-2">User Investment</h3>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-gray-400">Investment Amount</p>
                        <p className="text-white font-medium">
                            ${user_investment.investment.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">Ownership Percentage</p>
                        <p className="text-white font-medium">
                            {user_investment.ownership_percentage.toFixed(2)}%
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">Current Share Value</p>
                        <p className="text-white font-medium">
                            ${user_investment.current_share.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">Profit/Loss</p>
                        <p
                            className={`font-medium ${user_investment.profit_loss >= 0 ? 'text-green-500' : 'text-red-500'
                                }`}
                        >
                            ${Math.abs(user_investment.profit_loss).toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                </div>
            </div>

            {/* Coin Performance Section */}
            <div>
                <h3 className="text-xl font-semibold text-white mb-2">Coin Performance</h3>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-gray-400">Current Price</p>
                        <p className="text-white font-medium">
                            ${coin_performance.current_price.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">24h Price Change</p>
                        <p
                            className={`font-medium ${coin_performance.price_change_24h >= 0
                                ? 'text-green-500'
                                : 'text-red-500'
                                }`}
                        >
                            {coin_performance.price_change_24h.toFixed(2)}%
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">24h Volume</p>
                        <p className="text-white font-medium">
                            ${coin_performance.volume_24h.toLocaleString('en-US', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                            })}
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">Market Cap</p>
                        <p className="text-white font-medium">
                            ${coin_performance.market_cap.toLocaleString('en-US', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 0,
                            })}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default InvestmentCard;