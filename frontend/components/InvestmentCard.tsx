import { InvestmentData } from '@/utils/interfaces';
import React from 'react';

interface InvestmentCardProps {
    data: InvestmentData;
}

const InvestmentCard: React.FC<InvestmentCardProps> = ({ data }) => {
    const { user_investment, coin_performance } = data;

    const formatCurrency = (value: number) => {
        return value.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    };

    const formatPercentage = (value: number) => {
        return value.toFixed(2);
    };

    return (
        <div className="p-6 rounded-xl shadow-lg border border-crypto-blue/30 bg-[#0F172A] relative w-full">
            <div className='max-h-92 overflow-y-auto'>

                {/* User Investment Section */}
                <div className="mb-6">
                    <h3 className="text-xl font-semibold text-white mb-4">Your Investment</h3>
                    <div className="grid grid-cols-1 gap-4">
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Original Investment</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.original_investment)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Total Deposits</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.total_deposits)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Total Withdrawals</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.total_withdrawals)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Net Investment</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.net_investment)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Current Share Value</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.current_share_value)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Ownership Percentage</p>
                            <p className="text-white font-medium">
                                {formatPercentage(user_investment.ownership_percentage)}%
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Realized Gains</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.realized_gains)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Unrealized Gains</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.unrealized_gains)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Total Gains</p>
                            <p className="text-white font-medium">
                                ${formatCurrency(user_investment.total_gains)}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Overall Profit/Loss</p>
                            <p className={`font-medium ${user_investment.overall_profit_loss >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                ${formatCurrency(Math.abs(user_investment.overall_profit_loss))}
                            </p>
                        </div>
                        <div className="flex justify-between items-center">
                            <p className="text-gray-400">Performance</p>
                            <p className={`font-medium ${user_investment.performance_percentage >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                {formatPercentage(user_investment.performance_percentage)}%
                            </p>
                        </div>
                    </div>
                </div>

                {/* Portfolio Breakdown Section */}
                {user_investment.portfolio_breakdown && (
                    <div className="mb-6">
                        <h3 className="text-xl font-semibold text-white mb-4">Portfolio Breakdown</h3>
                        <div className="grid grid-cols-1 gap-4">
                            <div className="flex justify-between items-center">
                                <p className="text-gray-400">Cash Portion</p>
                                <p className="text-white font-medium">
                                    ${formatCurrency(user_investment.portfolio_breakdown.cash_portion)}
                                </p>
                            </div>
                            <div className="flex justify-between items-center">
                                <p className="text-gray-400">Position Portion</p>
                                <p className="text-white font-medium">
                                    ${formatCurrency(user_investment.portfolio_breakdown.position_portion)}
                                </p>
                            </div>
                            <div className="flex justify-between items-center">
                                <p className="text-gray-400">Total Portfolio Value</p>
                                <p className="text-white font-medium">
                                    ${formatCurrency(user_investment.portfolio_breakdown.total_value)}
                                </p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Global Coin Performance Section */}
                {coin_performance && (
                    <div className="mb-6">
                        <h3 className="text-xl font-semibold text-white mb-4">Global Coin Performance</h3>

                        {/* Market Data */}
                        <div className="mb-4">
                            <h4 className="text-lg font-medium text-white mb-2">Market Data</h4>
                            <div className="grid grid-cols-1 gap-4">
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Current Price</p>
                                    <p className="text-white font-medium">
                                        ${typeof coin_performance.current_price === 'number' ? formatCurrency(coin_performance.current_price) : coin_performance.current_price}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">24h Price Change</p>
                                    <p className={`font-medium ${typeof coin_performance.price_change_24h === 'number' && coin_performance.price_change_24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                        {typeof coin_performance.price_change_24h === 'number' ? `${formatPercentage(coin_performance.price_change_24h)}%` : coin_performance.price_change_24h}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">24h Volume</p>
                                    <p className="text-white font-medium">
                                        {typeof coin_performance.volume_24h === 'number' ? `$${formatCurrency(coin_performance.volume_24h)}` : coin_performance.volume_24h}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Market Cap</p>
                                    <p className="text-white font-medium">
                                        {typeof coin_performance.market_cap === 'number' ? `$${formatCurrency(coin_performance.market_cap)}` : coin_performance.market_cap}
                                    </p>
                                </div>
                            </div>
                        </div>

                        {/* Global Portfolio Performance */}
                        <div>
                            <h4 className="text-lg font-medium text-white mb-2">Global Portfolio Stats</h4>
                            <div className="grid grid-cols-1 gap-4">
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Deposits</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_deposits)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Withdrawals</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_withdrawals)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Net Deposits</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.net_deposits)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Current Capital</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.current_capital)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Position Quantity</p>
                                    <p className="text-white font-medium">
                                        {formatCurrency(coin_performance.position_quantity)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Position Value</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.position_value)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Portfolio Value</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_portfolio_value)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Realized Profits</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_realized_profits)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Unrealized Gains</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_unrealized_gains)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Total Gains</p>
                                    <p className="text-white font-medium">
                                        ${formatCurrency(coin_performance.total_gains)}
                                    </p>
                                </div>
                                <div className="flex justify-between items-center">
                                    <p className="text-gray-400">Overall Performance</p>
                                    <p className={`font-medium ${coin_performance.overall_performance >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                        {formatPercentage(coin_performance.overall_performance)}%
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 text-gray-400 text-xs pt-3">
                Scroll for more
            </div>
        </div>
    );
};

export default InvestmentCard;