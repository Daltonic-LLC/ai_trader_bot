// contexts/AuthContext.tsx
'use client'

import { createContext, ReactNode, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Cookies from 'js-cookie'

interface User {
    id: string
    email: string
    name: string
    role: string
    balances?: Record<string, number>
}

interface AuthContextType {
    user: User | null
    loading: boolean
    logout: () => void
    checkAuth: () => Promise<void>
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [loading, setLoading] = useState(true)
    const router = useRouter()

    const checkAuth = async () => {
        try {
            if (typeof window === 'undefined') return

            const bot_user = Cookies.get('bot_user')

            if (!bot_user) {
                setLoading(false)
                return
            }

            let token = ''
            try {
                const parsedUser = JSON.parse(bot_user) || {}
                token = parsedUser?.token?.access_token || ''
            } catch (error) {
                console.error('Invalid JSON in bot_user cookie:', error)
                Cookies.remove('bot_user')
                setLoading(false)
                return
            }

            if (!token) {
                setLoading(false)
                return
            }

            const response = await fetch(
                `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/users/me`,
                {
                    method: 'GET',
                    headers: {
                        Authorization: `Bearer ${token}`,
                    },
                }
            )

            if (response.ok) {
                const userData = await response.json()
                setUser(userData)
                
            } else {
                Cookies.remove('bot_user')
                console.log('Failed to retrieve user data.')
            }
        } catch (error) {
            console.error('Auth check failed:', error)
        } finally {
            setLoading(false)
        }
    }

    const logout = () => {
        Cookies.remove('bot_user')
        setUser(null)
        router.push('/')
    }

    useEffect(() => {
        if (typeof window !== 'undefined') {
            checkAuth()
        }
    }, [])

    return (
        <AuthContext.Provider value={{ user, loading, logout, checkAuth }}>
            {children}
        </AuthContext.Provider>
    )
}