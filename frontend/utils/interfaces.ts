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
    original_investment: number
    total_deposits: number
    total_withdrawals: number
    net_investment: number
    ownership_percentage: number
    current_share_value: number
    realized_gains: number
    unrealized_gains: number
    total_gains: number
    overall_profit_loss: number
    performance_percentage: number
    portfolio_breakdown: {
      cash_portion: number
      position_portion: number
      total_value: number
    }
  }
  coin_performance: {
    current_price: number | string
    price_change_24h: number | string
    volume_24h: number | string
    market_cap: number | string
    total_portfolio_value: number
    total_realized_profits: number
    total_unrealized_gains: number
    overall_performance: number
  }
  coin: string
  timestamp: string
}
