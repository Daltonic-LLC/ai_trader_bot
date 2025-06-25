'use client';

import React, { useState, useEffect } from 'react';
import { toast } from 'react-toastify';

interface ProfileModalProps {
    onClose: () => void;
    onSubmitAddress: (address: string) => void;
}

// Fake API: Simulates fetching an existing USDT wallet address
const fakeFetchWalletAddress = async (): Promise<{ wallet: string }> => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({ wallet: 'T9qG8xLJHJkWjEyfKUSiNfPZho12345678' });
        }, 1000); // Simulate 1 second delay
    });
};

// Fake API: Simulates updating the USDT wallet address
const fakeUpdateWalletAddress = async (coin: string, address: string): Promise<void> => {
    return new Promise((resolve) => {
        setTimeout(() => {
            console.log(`[FAKE API] Updated ${coin.toUpperCase()} wallet to: ${address}`);
            resolve();
        }, 1000); // Simulate 1 second delay
    });
};

const ProfileModal: React.FC<ProfileModalProps> = ({ onClose, onSubmitAddress }) => {
    const [address, setAddress] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const getDefaultAddress = async () => {
            try {
                const data = await fakeFetchWalletAddress();
                if (data.wallet) setAddress(data.wallet);
            } catch (err) {
                console.error('[FAKE API] Failed to fetch wallet:', err);
            }
        };

        getDefaultAddress();
    }, []);

    const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAddress(e.target.value);
        setError('');
    };

    const handleSubmit = async () => {
        if (!address.trim()) {
            setError('Please enter a valid address.');
            return;
        }

        setLoading(true);
        try {
            await fakeUpdateWalletAddress('usdt', address);
            toast.success('Wallet address updated successfully!');
            onSubmitAddress(address);
            onClose();
        } catch (error) {
            console.error('[FAKE API] Update error:', error);
            setError('Failed to update wallet address. Please try again.');
            toast.error('Failed to update wallet address.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-[#0F172A]/65 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-[#0F172A] p-6 rounded-xl shadow-lg border border-crypto-blue/30 w-96">
                <h2 className="text-2xl font-semibold text-white mb-4">USDT Coin</h2>

                <div className="mb-4">
                    <label className="block text-gray-300 mb-2">USDT Address:</label>
                    <input
                        type="text"
                        value={address}
                        onChange={handleAddressChange}
                        className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-crypto-blue focus:outline-none"
                        placeholder="Enter USDT address"
                        disabled={loading}
                    />
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
                        onClick={handleSubmit}
                        className="px-4 py-2 bg-crypto-blue text-white rounded hover:bg-crypto-blue/80 transition cursor-pointer"
                        disabled={loading}
                    >
                        {loading ? 'Saving...' : 'Submit'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ProfileModal;
