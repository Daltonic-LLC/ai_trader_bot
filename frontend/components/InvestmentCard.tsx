import { InvestmentData } from '@/utils/interfaces';
import React from 'react';

interface InvestmentCardProps {
    data: InvestmentData;
}

const InvestmentCard: React.FC<InvestmentCardProps> = ({ data }) => {
    const { user_investment } = data;


    return (
        <div className="p-6 rounded-xl shadow-lg border border-crypto-blue/30 bg-[#0F172A] w-full">
            {/* User Investment Section */}
            <div className="mb-6">
                <h3 className="text-xl font-semibold text-white mb-2">User Investment</h3>
                <div className="grid grid-cols-1 gap-4">
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Net Investment</p>
                        <p className="text-white font-medium">
                            ${user_investment.net_investment.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Current Share Value</p>
                        <p className="text-white font-medium">
                            ${user_investment.current_share_value.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Total Gains</p>
                        <p className="text-white font-medium">
                            ${user_investment.total_gains.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Overall Profit/Loss</p>
                        <p className={`font-medium ${user_investment.overall_profit_loss >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            ${Math.abs(user_investment.overall_profit_loss).toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Performance (%)</p>
                        <p className={`font-medium ${user_investment.performance_percentage >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {user_investment.performance_percentage.toFixed(2)}%
                        </p>
                    </div>
                </div>
            </div>

            {/* Coin Performance Section */}
            <div>
                <h3 className="text-xl font-semibold text-white mb-2">Coin Performance</h3>
                <div className="grid grid-cols-1 gap-4">
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Ownership Percentage</p>
                        <p className="text-white font-medium">
                            {user_investment.ownership_percentage.toFixed(2)}%
                        </p>
                    </div>
                    <div className="flex justify-between items-center">
                        <p className="text-gray-400">Profit/Loss</p>
                        <p
                            className={`font-medium ${user_investment.overall_profit_loss >= 0 ? 'text-green-500' : 'text-red-500'
                                }`}
                        >
                            ${Math.abs(user_investment.overall_profit_loss).toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default InvestmentCard;