import React, { useState } from 'react';
import { Coin } from '@/utils/interfaces';

interface CoinSelectorProps {
    coins: Coin[];
    selectedCoin: Coin | null;
    onCoinChange: (coin: Coin | null) => void;
}

const CoinSelector: React.FC<CoinSelectorProps> = ({ coins, selectedCoin, onCoinChange }) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleSelect = (coin: Coin) => {
        onCoinChange(coin);
        setIsOpen(false);
    };

    return (
        <div className="relative mb-6">
            <div className="p-4 rounded-xl shadow-lg border
            border-crypto-blue/30 hover:border-crypto-blue transition-all">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="w-full flex justify-between items-center text-white font-semibold
                    py-2 px-4 rounded-lg bg-gradient-to-r from-crypto-blue/20 to-crypto-green/20
                    hover:from-crypto-blue/30 hover:to-crypto-green/30 transition-all cursor-pointer"
                >
                    <span>{selectedCoin ? `${selectedCoin.name} (${selectedCoin.symbol})` : 'Select a Coin'}</span>
                    <svg
                        className={`w-5 h-5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
                {isOpen && (
                    <div className="absolute top-full left-0 mt-2 w-full bg-[#0F172A] 
                    rounded-xl shadow-lg border border-crypto-blue/30 z-10 max-h-60 overflow-y-auto">
                        {coins.map((coin) => (
                            <button
                                key={coin.slug}
                                onClick={() => handleSelect(coin)}
                                className="w-full text-left px-4 py-3 text-white hover:bg-gradient-to-r
                                hover:from-crypto-blue/50 hover:to-crypto-green/50 hover:border-l-4 cursor-pointer
                                hover:border-crypto-blue hover:scale-105 transition-all transform duration-200"
                            >
                                {coin.name} ({coin.symbol})
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default CoinSelector;