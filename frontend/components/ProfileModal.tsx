import { updateWalletAddress } from '@/utils/api';
import React, { useState } from 'react';
import { fetchWalletAddresses } from '@/utils/api';
import { useEffect } from 'react';

interface ProfileModalProps {
    onClose: () => void;
    onSubmitAddress: (address: string) => void;
}

const ProfileModal: React.FC<ProfileModalProps> = ({ onClose, onSubmitAddress }) => {
    const [address, setAddress] = useState('');
    const [error, setError] = useState('');

    const getDefaultAddress = async () => {
        try {
            const data = await fetchWalletAddresses('USDT');
            // Assuming the API returns an array of wallets or an object with a 'usdt' property
            // Adjust the following line based on the actual API response structure
            if(data.wallet) setAddress(data.wallet);

        } catch (err) {
            // Optionally handle error
            console.log(err)
        }
    };

    useEffect(() => {
        getDefaultAddress();
    }, []);

    // Handle address input changes
    const handleAddressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setAddress(e.target.value);
        setError('');
    };

    // Handle address submission
    const handleSubmit = async () => {
        if (!address.trim()) {
            setError('Please enter a valid address.');
            return;
        }

        try {
            // Call the updateWalletAddress function with 'USDT' as the coin
            await updateWalletAddress('usdt', address);
            // Notify the parent component of successful submission
            onSubmitAddress(address);
            // Close the modal
            onClose();
        } catch (error) {
            // Display an error message if the API call fails
            console.log(error);

            setError('Failed to update wallet address. Please try again.');
        }
    };

    return (
        <div className="fixed inset-0 bg-[#0F172A]/65 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-[#0F172A] p-6 rounded-xl shadow-lg border border-crypto-blue/30 w-96">
                <h2 className="text-2xl font-semibold text-white mb-4">
                    USDT Coin
                </h2>
                <div className="mb-4">
                    <label className="block text-gray-300 mb-2">USDT Address:</label>
                    <input
                        type="text"
                        value={address}
                        onChange={handleAddressChange}
                        className="w-full p-2 rounded bg-gray-700 text-white border border-gray-600 focus:border-crypto-blue focus:outline-none"
                        placeholder="Enter USDT address"
                    />
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
                        onClick={handleSubmit}
                        className="px-4 py-2 bg-crypto-blue text-white rounded hover:bg-crypto-blue/80 transition cursor-pointer"
                    >
                        Submit
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ProfileModal;