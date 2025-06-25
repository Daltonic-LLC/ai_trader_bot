'use client';

import React, { useState } from 'react';

interface ActionButtonsProps {
    isCoinSelected: boolean;
    onDepositClick: () => void;
    onWithdrawClick: () => void;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({ isCoinSelected }) => {
    const [isDepositOpen, setIsDepositOpen] = useState(false);
    const [isWithdrawOpen, setIsWithdrawOpen] = useState(false);

    const handleDeposit = () => {
        if (isCoinSelected) setIsDepositOpen(true);
    };

    const handleWithdraw = () => {
        if (isCoinSelected) setIsWithdrawOpen(true);
    };

    const closeModal = () => {
        setIsDepositOpen(false);
        setIsWithdrawOpen(false);
    };

    return (
        <div className="flex flex-col justify-center items-center space-y-4 mt-4 w-full">
            <div className="flex flex-col md:flex-row justify-center items-center space-y-4 lg:space-y-0 lg:space-x-4 w-full">
                <button
                    onClick={handleDeposit}
                    disabled={!isCoinSelected}
                    className={`w-full bg-gradient-to-r from-crypto-green to-crypto-blue text-white
            py-3 px-6 rounded-lg font-semibold hover:shadow-crypto-green/50 hover:scale-105
            active:scale-95 transition-all duration-200 animate-pulse-slow border border-crypto-green/50
            hover:border-crypto-green shadow-md cursor-pointer ${!isCoinSelected ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                >
                    Deposit
                </button>
                <button
                    onClick={handleWithdraw}
                    disabled={!isCoinSelected}
                    className={`w-full bg-gradient-to-r from-crypto-blue to-crypto-gray text-white
            py-3 px-6 rounded-lg font-semibold hover:shadow-crypto-blue/50 hover:scale-105
            active:scale-95 transition-all duration-200 animate-pulse-slow border border-crypto-blue/50
            hover:border-crypto-blue shadow-md cursor-pointer ${!isCoinSelected ? 'opacity-50 cursor-not-allowed' : ''
                        }`}
                >
                    Withdraw
                </button>
            </div>

            {/* FAKE Deposit Modal */}
            {isDepositOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 text-black">
                        <h2 className="text-xl font-bold mb-4">Fake Deposit Modal</h2>
                        <p>This is a fake deposit modal for teaching purposes.</p>
                        <button onClick={closeModal} className="mt-4 px-4 py-2 bg-blue-500 text-white rounded">
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* FAKE Withdraw Modal */}
            {isWithdrawOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 text-black">
                        <h2 className="text-xl font-bold mb-4">Fake Withdraw Modal</h2>
                        <p>This is a fake withdraw modal for teaching purposes.</p>
                        <button onClick={closeModal} className="mt-4 px-4 py-2 bg-blue-500 text-white rounded">
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ActionButtons;
