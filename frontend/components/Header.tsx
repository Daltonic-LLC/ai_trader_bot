'use client';

import { useAuth } from '@/hooks/userAuth';
import React, { useState, useEffect } from 'react';


const Header: React.FC = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const { user, logout } = useAuth()

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 0);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <header
            className={`fixed top-0 left-0 w-full flex justify-between items-center px-6 py-4
                bg-crypto-dark/90 backdrop-blur-sm z-10 transition-shadow
                ${isScrolled ? 'shadow-lg shadow-crypto-blue/20' : ''}`
            }
        >
            <div className="text-2xl font-bold text-white">Cycle Trader</div>
            <div className="flex items-center gap-4">
                <span className="text-gray-300 text-sm capitalize">{user?.name.split(' ')[0]}</span>
                <button
                    onClick={logout}
                    className="text-sm text-crypto-blue hover:text-crypto-blue/80 font-semibold cursor-pointer
                    transition-colors duration-200 ease-in-out">
                    Logout
                </button>
            </div>
        </header>
    );
};

export default Header;