'use client';

import { useAuth } from '@/hooks/userAuth';
import React, { useState, useEffect } from 'react';
import ProfileModal from './ProfileModal';


const Header: React.FC = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const { user, logout } = useAuth()

    const toggleModal = () => {
        setIsModalOpen(!isModalOpen);
    };

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 0);
        };

        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <>
            <header
                className={`fixed top-0 left-0 w-full flex justify-between items-center px-6 py-4
                bg-crypto-dark/90 backdrop-blur-sm z-10 transition-shadow
                ${isScrolled ? 'shadow-lg shadow-crypto-blue/20' : ''}`
                }
            >
                <div className="text-2xl font-bold text-white">Cycle Trader</div>
                <div className="flex items-center gap-4">
                    <button
                        onClick={toggleModal}
                        className="text-sm text-crypto-blue hover:text-crypto-blue/80 cursor-pointer
                    transition-colors duration-200 ease-in-out text-gray-300 capitalize">
                        {user?.name.split(' ')[0]}
                    </button>
                    <button
                        onClick={logout}
                        className="text-sm text-crypto-blue hover:text-crypto-blue/80 font-semibold cursor-pointer
                    transition-colors duration-200 ease-in-out">
                        Logout
                    </button>
                </div>
            </header>

            {isModalOpen && (
                <ProfileModal
                    onClose={toggleModal}
                    onSubmitAddress={(address: string) => {
                        console.log('Submitted address:', address);
                        toggleModal();
                    }}
                />
            )}
        </>
    );
};

export default Header;