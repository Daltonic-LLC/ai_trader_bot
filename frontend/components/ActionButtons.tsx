import React from 'react';

const ActionButtons: React.FC = () => {
    const handleDeposit = () => {
        // Placeholder for deposit logic
        console.log('Deposit button clicked');
    };

    const handleWithdraw = () => {
        // Placeholder for withdraw logic
        console.log('Withdraw button clicked');
    };

    return (
        <div className="flex flex-col lg:flex-row justify-center items-center space-y-4 lg:space-y-0 lg:space-x-4 mt-4 w-full">
            <button
                onClick={handleDeposit}
                className="w-full bg-gradient-to-r from-crypto-green to-crypto-blue text-white py-3 px-6 rounded-lg font-semibold hover:shadow-crypto-green/50 hover:scale-105 active:scale-95 transition-all duration-200 animate-pulse-slow border border-crypto-green/50 hover:border-crypto-green shadow-md"
            >
                Deposit
            </button>
            <button
                onClick={handleWithdraw}
                className="w-full bg-gradient-to-r from-crypto-blue to-crypto-gray text-white py-3 px-6 rounded-lg font-semibold hover:shadow-crypto-blue/50 hover:scale-105 active:scale-95 transition-all duration-200 animate-pulse-slow border border-crypto-blue/50 hover:border-crypto-blue shadow-md"
            >
                Withdraw
            </button>
        </div>
    );
};

export default ActionButtons;