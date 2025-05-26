// GlobalContext.tsx
'use client'

import { createContext, useContext, useState, ReactNode } from 'react';

// Define the shape of the global context with optional fields
interface GlobalContextType {
    isDepositOpen?: boolean;
    setIsDepositOpen?: (open: boolean) => void;
    isWithdrawOpen?: boolean;
    setIsWithdrawOpen?: (open: boolean) => void;
    userBalance?: number;
    setUserBalance?: (amount: number) => void;
    // Add other optional fields as needed in the future
    // e.g., user?: User; setUser?: (user: User) => void;
}

const GlobalContext = createContext<GlobalContextType | undefined>(undefined);

export const GlobalProvider = ({ children }: { children: ReactNode }) => {
    const [isDepositOpen, setIsDepositOpen] = useState<boolean>(false);
    const [isWithdrawOpen, setIsWithdrawOpen] = useState<boolean>(false);
    const [userBalance, setUserBalance] = useState<number>(0);

    // Context value with optional fields
    const value: GlobalContextType = {
        isDepositOpen,
        setIsDepositOpen,
        isWithdrawOpen,
        setIsWithdrawOpen,
        userBalance,
        setUserBalance,
    };

    return <GlobalContext.Provider value={value}>{children}</GlobalContext.Provider>;
};

export const useGlobalContext = () => {
    const context = useContext(GlobalContext);
    if (!context) {
        throw new Error('useGlobalContext must be used within a GlobalProvider');
    }
    return context;
};