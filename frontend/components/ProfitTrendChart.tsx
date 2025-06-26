import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MdTrendingUp, MdTrendingDown, MdCopyAll } from "react-icons/md";
import { Coin, ExecutionLog, PortfolioData } from '@/utils/interfaces';

interface ProfitTrendCardProps {
    data: PortfolioData[];
    coin: Coin | null;
    executionLog?: ExecutionLog | null;
}

// Define the chart data point structure
interface ChartDataPoint {
    time: string;
    fullTime: string;
    totalGains: number;
    performancePercentage: number;
    portfolioValue: number;
    price: number;
}

// Define the props for CustomTooltip
interface CustomTooltipProps {
    active?: boolean;
    payload?: Array<{ payload: ChartDataPoint }>;
}

const ProfitTrendChart: React.FC<ProfitTrendCardProps> = ({
    data,
    coin,
    executionLog
}) => {
    if (!data || data.length === 0) {
        return (
            <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/20 text-gray-400 text-center">
                No P&L data available
            </div>
        );
    }

    // Get the latest data point for current metrics 
    const latestData = data[data.length - 1];
    const { global } = latestData;

    // Prepare chart data
    const chartData = data.map(item => ({
        time: new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        fullTime: new Date(item.timestamp).toLocaleString(),
        totalGains: item.global.total_gains,
        performancePercentage: item.global.performance_percentage * 100,
        portfolioValue: item.global.total_portfolio_value,
        price: item.price
    }));

    // Determine trend direction
    const isPositive = global.total_gains >= 0;
    const trendColor = isPositive ? 'text-crypto-green' : 'text-red-500';
    const trendIcon = isPositive ? MdTrendingUp : MdTrendingDown;

    // Format currency values
    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
    };

    // Format percentage
    const formatPercentage = (value: number) => {
        return `${value >= 0 ? '+' : ''}${value.toFixed(4)}%`;
    };

    // Custom tooltip for the chart
    const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="bg-crypto-gray border border-crypto-blue/30 rounded-lg p-3 shadow-lg">
                    <p className="text-white text-sm font-medium">{data.fullTime}</p>
                    <p className="text-gray-300 text-sm">
                        P&L: <span className={data.totalGains >= 0 ? 'text-crypto-green' : 'text-red-500'}>
                            {formatCurrency(data.totalGains)}
                        </span>
                    </p>
                    <p className="text-gray-300 text-sm">
                        Performance: <span className={data.performancePercentage >= 0 ? 'text-crypto-green' : 'text-red-500'}>
                            {formatPercentage(data.performancePercentage)}
                        </span>
                    </p>
                    <p className="text-gray-300 text-sm">
                        Portfolio Value: {formatCurrency(data.portfolioValue)}
                    </p>
                    <p className="text-gray-300 text-sm">
                        {coin?.symbol} Price: {formatCurrency(data.price)}
                    </p>
                </div>
            );
        }
        return null;
    };

    const copyPnLData = () => {
        const summaryData = {
            currentMetrics: {
                totalGains: global.total_gains,
                performancePercentage: global.performance_percentage,
                portfolioValue: global.total_portfolio_value,
                positionValue: global.position_value,
                currentCapital: global.current_capital,
                totalInvestments: global.total_net_investments
            },
            historicalData: data,
            generatedAt: new Date().toISOString()
        };
        navigator.clipboard.writeText(JSON.stringify(summaryData, null, 2));
    };

    return (
        <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/30 hover:border-crypto-blue transition-all relative w-full">
            {/* Header */}
            <div className="flex justify-between items-center bg-gradient-to-r from-crypto-blue to-crypto-green text-white rounded-t-xl -m-5 mb-4 p-4">
                <div className="flex items-center gap-2">
                    {React.createElement(trendIcon, { className: `w-6 h-6 ${trendColor}` })}
                    <h2 className="text-xl font-semibold">{coin?.name} P&L Trend</h2>
                </div>
                <button
                    type="button"
                    className="p-2 rounded hover:bg-white/10 transition cursor-pointer"
                    title="Copy P&L data to clipboard"
                    onClick={copyPnLData}
                >
                    <MdCopyAll className="w-5 h-5" />
                </button>
            </div>

            {/* Current Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Total P&L</span>
                        <span className={`font-bold text-lg ${trendColor}`}>
                            {formatCurrency(global.total_gains)}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Performance</span>
                        <span className={`font-medium ${trendColor}`}>
                            {formatPercentage(global.performance_percentage * 100)}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Portfolio Value</span>
                        <span className="text-white font-medium">
                            {formatCurrency(global.total_portfolio_value)}
                        </span>
                    </div>
                </div>
                <div className="space-y-3">
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Position Value</span>
                        <span className="text-white font-medium">
                            {formatCurrency(global.position_value)}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Available Capital</span>
                        <span className="text-white font-medium">
                            {formatCurrency(global.current_capital)}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <span className="text-gray-300">Total Invested</span>
                        <span className="text-white font-medium">
                            {formatCurrency(global.total_net_investments)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Chart */}
            <div className="h-64 mb-4">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                        <XAxis
                            dataKey="time"
                            stroke="#9CA3AF"
                            fontSize={12}
                        />
                        <YAxis
                            stroke="#9CA3AF"
                            fontSize={12}
                            tickFormatter={(value) => `$${value.toFixed(0)}`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Line
                            type="monotone"
                            dataKey="totalGains"
                            stroke={isPositive ? "#10B981" : "#EF4444"}
                            strokeWidth={2}
                            dot={{ r: 4, fill: isPositive ? "#10B981" : "#EF4444" }}
                            activeDot={{ r: 6, fill: isPositive ? "#10B981" : "#EF4444" }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            {/* Footer */}
            <div className="flex justify-between items-center text-gray-300 text-xs pt-3">
                <span>
                    Last Updated: {' '} {executionLog?.last_execution
                        ? new Date(executionLog.last_execution).toLocaleString()
                        : 'N/A'}
                </span>
                <span>
                    {coin?.symbol}: {formatCurrency(latestData.price)}
                </span>
            </div>
        </div>
    );
};


export default ProfitTrendChart;