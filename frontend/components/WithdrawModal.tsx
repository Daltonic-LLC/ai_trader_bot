import React, { useState } from 'react';
import { Coin } from '@/utils/interfaces';
import { withdraw_funds } from '@/utils/api';

interface WithdrawModalProps {
    coin: Coin;
    currentBalance: number;
    onClose: () => void;
    onWithdraw: (amount: number) => void;
}

const WithdrawModal: React.FC<WithdrawModalProps> = ({ coin, currentBalance, onClose, onWithdraw }) => {
    const [amount, setAmount] = useState('');
    const [error, setError] = useState('');

    const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAmount(e.target.value);
        setError('');
    };

    const handleWithdraw = () => {
        const numAmount = parseFloat(amount);
        if (isNaN(numAmount) || numAmount <= 0) {
            setError('Please enter a valid positive amount.');
            return;
        }
        if (numAmount > currentBalance) {
            setError('Insufficient balance.');
            return;
        }

        withdraw_funds(coin.slug, numAmount)
            .then(() => {
                setAmount('');
                onWithdraw(numAmount);
                onClose();
            })
            .catch((error) => {
                setError(error.message);
            });

    };

    const setMaxAmount = () => {
        setAmount(currentBalance.toString());
        setError('');
    };

    return (
        <div className="fixed inset-0 bg-[#0F172A]/65 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-crypto-gray p-6 rounded-xl shadow-lg border border-crypto-blue/30 w-96">
                <h2 className="text-2xl font-semibold text-white mb-4">
                    Withdraw {coin.symbol}
                </h2>
                <div className="mb-4">
                    <p className="text-gray-300">Current Balance:</p>
                    <p className="text-white font-medium">
                        {currentBalance} {coin.symbol}
                    </p>
                </div>
                <div className="mb-4">
                    <label className="block text-gray-300 mb-2">Amount to withdraw:</label>
                    <div className="flex items-center">
                        <input
                            type="number"
                            value={amount}
                            onChange={handleAmountChange}
                            className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-crypto-blue focus:outline-none"
                            placeholder="Enter amount"
                        />
                        <button
                            onClick={setMaxAmount}
                            className="ml-2 px-3 py-1 bg-crypto-green text-white rounded hover:bg-crypto-green/80 transition"
                        >
                            Max
                        </button>
                    </div>
                </div>
                {error && <p className="text-red-500 mb-4">{error}</p>}
                <div className="flex justify-end space-x-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition cursor-pointer"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleWithdraw}
                        className="px-4 py-2 bg-crypto-blue text-white rounded hover:bg-crypto-blue/80 transition cursor-pointer"
                    >
                        Withdraw
                    </button>
                </div>
            </div>
        </div>
    );
};

export default WithdrawModal;