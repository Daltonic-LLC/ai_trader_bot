// ActionButtons.tsx
import { useGlobalContext } from '@/contexts/GlobalContext';
import React from 'react';// Adjust the import path

interface ActionButtonsProps {
    isCoinSelected: boolean;
}

const ActionButtons: React.FC<ActionButtonsProps> = ({ isCoinSelected }) => {
    const { setIsDepositOpen, setIsWithdrawOpen } = useGlobalContext();

    const handleDeposit = () => {
        if (isCoinSelected && setIsDepositOpen) {
            setIsDepositOpen(true);
        }
    };

    const handleWithdraw = () => {
        if (isCoinSelected && setIsWithdrawOpen) {
            setIsWithdrawOpen(true);
        }
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
        </div>
    );
};

export default ActionButtons;