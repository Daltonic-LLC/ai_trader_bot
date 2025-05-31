export interface Coin {
  rank: string
  name: string
  slug: string
  symbol: string
  market_cap: string
  price: string
  circulating_supply: string
  volume_24h: string
  percent_1h: string
  percent_24h: string
  percent_7d: string
}

export interface ExecutionLog {
  job_name: string
  last_execution: string
  next_execution: string
}

export interface InvestmentData {
  user_investment: {
    investment: number
    ownership_percentage: number
    current_share: number
    profit_loss: number
  }
  coin_performance: {
    current_price: number
    price_change_24h: number
    volume_24h: number
    market_cap: number
  }
}
