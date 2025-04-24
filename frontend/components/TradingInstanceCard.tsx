import React from 'react';

// Define interface for trading instance
interface TradingInstance {
    id: number;
    coin: string;
    capital: number;
    position: number;
    lastRecommendation: 'BUY' | 'SELL' | 'HOLD';
}

interface TradingInstanceCardProps {
    instance: TradingInstance;
}

const TradingInstanceCard: React.FC<TradingInstanceCardProps> = ({ instance }) => {
    const recommendationColor =
        instance.lastRecommendation === 'BUY'
            ? 'text-crypto-green'
            : instance.lastRecommendation === 'SELL'
                ? 'text-red-500'
                : 'text-gray-400';

    return (
        <div className="p-5 bg-crypto-gray rounded-xl shadow-lg hover:shadow-crypto-blue/30 transition-all border border-crypto-blue/20">
            <h2 className="text-xl font-semibold text-white mb-3">
                {instance.coin.toUpperCase()}
            </h2>
            <p className="text-gray-300">
                Capital: <span className="font-medium">${instance.capital.toFixed(2)}</span>
            </p>
            <p className="text-gray-300">
                Position:{' '}
                <span className="font-medium">
                    {instance.position.toFixed(4)} {instance.coin.toUpperCase()}
                </span>
            </p>
            <p className={`text-gray-300 ${recommendationColor}`}>
                Recommendation:{' '}
                <span className="font-semibold">{instance.lastRecommendation}</span>
            </p>
            <button className="mt-4 text-crypto-blue hover:text-crypto-blue/80 font-semibold">
                View Details
            </button>
        </div>
    );
};

export default TradingInstanceCard;