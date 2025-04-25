import React, { useState } from 'react';
import { Coin } from '@/utils/interfaces';

interface DepositModalProps {
    coin: Coin;
    currentBalance: number;
    onClose: () => void;
    onDeposit: (amount: number) => void;
}

const DepositModal: React.FC<DepositModalProps> = ({ coin, currentBalance, onClose, onDeposit }) => {
    const [amount, setAmount] = useState('');
    const [error, setError] = useState('');

    const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAmount(e.target.value);
        setError('');
    };

    const handleDeposit = () => {
        const numAmount = parseFloat(amount);
        if (isNaN(numAmount) || numAmount <= 0) {
            setError('Please enter a valid positive amount.');
            return;
        }
        onDeposit(numAmount);
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-[#0F172A]/65 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-[#0F172A] p-6 rounded-xl shadow-lg border border-crypto-blue/30 w-96">
                <h2 className="text-2xl font-semibold text-white mb-4">
                    Deposit {coin.symbol}
                </h2>
                <div className="mb-4">
                    <p className="text-gray-300">Current Balance:</p>
                    <p className="text-white font-medium">
                        {currentBalance} {coin.symbol}
                    </p>
                </div>
                <div className="mb-4">
                    <label className="block text-gray-300 mb-2">Amount to deposit:</label>
                    <input
                        type="number"
                        value={amount}
                        onChange={handleAmountChange}
                        className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-crypto-blue focus:outline-none"
                        placeholder="Enter amount"
                    />
                </div>
                {error && <p className="text-red-500 mb-4">{error}</p>}
                <div className="flex justify-end space-x-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleDeposit}
                        className="px-4 py-2 bg-crypto-blue text-white rounded hover:bg-crypto-blue/80 transition"
                    >
                        Deposit
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DepositModal;