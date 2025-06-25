import React, { useState } from 'react';
import { Coin } from '@/utils/interfaces';
import { toast } from 'react-toastify';

interface WithdrawModalProps {
    coin: Coin;
    currentBalance: number;
    onClose: () => void;
    onWithdraw: (amount: number) => void;
}

// Fake withdrawal API simulation
const fakeWithdrawFunds = async (coinSlug: string, amount: number): Promise<void> => {
    return new Promise((resolve) => {
        setTimeout(() => {
            console.log(`[FAKE API] Withdrew ${amount} from ${coinSlug}`);
            resolve();
        }, 1000); // Simulates 1 second delay
    });
};

const WithdrawModal: React.FC<WithdrawModalProps> = ({
    coin,
    currentBalance,
    onClose,
    onWithdraw,
}) => {
    const [amount, setAmount] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAmount(e.target.value);
        setError('');
    };

    const setMaxAmount = () => {
        setAmount(currentBalance.toString());
        setError('');
    };

    const handleWithdraw = async () => {
        const numAmount = parseFloat(amount);
        if (isNaN(numAmount) || numAmount <= 0) {
            setError('Please enter a valid positive amount.');
            return;
        }
        if (numAmount > currentBalance) {
            setError('Insufficient balance.');
            return;
        }

        setLoading(true);
        try {
            await fakeWithdrawFunds(coin.slug, numAmount);
            toast.success(`Successfully withdrew ${numAmount} ${coin.symbol}!`);
            onWithdraw(numAmount);
            setAmount('');
            onClose();
        } catch (error: unknown) {
            const errorMessage =
                error instanceof Error ? error.message : 'An unknown error occurred.';
            setError(errorMessage);
            toast.error(`Withdrawal failed: ${errorMessage}`);
            console.error('Withdrawal error:', error);
        } finally {
            setLoading(false);
        }
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
                            disabled={loading}
                        />
                        <button
                            onClick={setMaxAmount}
                            className="ml-2 px-3 py-1 bg-crypto-green text-white rounded hover:bg-crypto-green/80 transition"
                            disabled={loading}
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
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleWithdraw}
                        className="px-4 py-2 bg-crypto-blue text-white rounded hover:bg-crypto-blue/80 transition cursor-pointer"
                        disabled={loading}
                    >
                        {loading ? 'Processing...' : 'Withdraw'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default WithdrawModal;
