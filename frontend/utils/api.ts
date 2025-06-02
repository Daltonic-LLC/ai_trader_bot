import Cookies from 'js-cookie'

const BASE_URL = `${process.env.NEXT_PUBLIC_BACKEND_API_URL}`

export const deposit_funds = async (coin: string, amount: number) => {
  try {
    const _user = Cookies.get('bot_user')!
    const parsedUser = JSON.parse(_user) || {}
    const token = parsedUser?.token?.access_token || ''

    const response = await fetch(`${BASE_URL}/auth/balance/deposit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ coin, amount }),
    })

    if (!response.ok) {
      throw new Error('Failed to deposit funds')
    }

    return await response.json()
  } catch (error) {
    console.error('Error depositing funds:', error)
    throw error
  }
}

export const fetchCoins = async (limit: number) => {
  try {
    const response = await fetch(`${BASE_URL}/coin/top_coins?limit=${limit}`)

    if (!response.ok) {
      throw new Error('Failed to deposit funds')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching coins:', error)
    throw error
  }
}

export const fetchCoinReport = async (coin: string) => {
  try {
    const response = await fetch(`${BASE_URL}/coin/report/${coin}`)

    if (!response.ok) {
      throw new Error('Failed to retrieve coin report')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching coin report:', error)
    throw error
  }
}

export const fetchExecutionLog = async () => {
  try {
    const response = await fetch(`${BASE_URL}/coin/execution_log`)

    if (!response.ok) {
      throw new Error('Failed to retrieve coin report')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching coin report:', error)
    throw error
  }
}

export const fetchCoinInvestment = async (coin: string) => {
  try {
    const _user = Cookies.get('bot_user')!
    const parsedUser = JSON.parse(_user) || {}
    const token = parsedUser?.token?.access_token || ''

    const response = await fetch(`${BASE_URL}/auth/investment/${coin}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to retrieve coin report')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching coin report:', error)
    throw error
  }
}

export const fetchUserProfile = async () => {
  try {
    const _user = Cookies.get('bot_user')!
    const parsedUser = JSON.parse(_user) || {}
    const token = parsedUser?.token?.access_token || ''

    const response = await fetch(`${BASE_URL}/auth/profile`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to retrieve user profile')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching user profile:', error)
    throw error
  }
}

export const updateWalletAddress = async (
  coin: string,
  wallet_address: string
) => {
  try {
    const _user = Cookies.get('bot_user')!
    const parsedUser = JSON.parse(_user) || {}
    const token = parsedUser?.token?.access_token || ''

    const response = await fetch(`${BASE_URL}/auth/wallet/add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ coin, wallet_address }),
    })

    if (!response.ok) {
      throw new Error('Failed to add or update wallet address')
    }

    return await response.json()
  } catch (error) {
    console.error('Error updating wallet address:', error)
    throw error
  }
}

export const fetchWalletAddresses = async (coin: string) => {
  try {
    const _user = Cookies.get('bot_user')!
    const parsedUser = JSON.parse(_user) || {}
    const token = parsedUser?.token?.access_token || ''

    const response = await fetch(`${BASE_URL}/auth/wallets/${coin}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    })

    if (!response.ok) {
      throw new Error('Failed to retrieve wallet addresses')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching wallet addresses:', error)
    throw error
  }
}
