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
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/coin/top_coins?limit=${limit}`
    )

    if (!response.ok) {
      throw new Error('Failed to deposit funds')
    }

    return await response.json()
  } catch (error) {
    console.error('Error fetching coins:', error)
    throw error
  }
}
