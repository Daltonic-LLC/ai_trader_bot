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

// Updated interfaces to match the new API response structure

export interface PortfolioBreakdown {
  cash_portion: number
  position_portion: number
  total_value: number
}

export interface UserInvestment {
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
  portfolio_breakdown: PortfolioBreakdown
}

export interface CoinPerformance {
  // Market data
  current_price: number | string
  price_change_24h: number | string
  volume_24h: number | string
  market_cap: number | string

  // Global portfolio performance
  total_deposits: number
  total_withdrawals: number
  net_deposits: number
  current_capital: number
  position_quantity: number
  position_value: number
  total_portfolio_value: number
  total_realized_profits: number
  total_unrealized_gains: number
  total_gains: number
  overall_performance: number
}

export interface InvestmentData {
  user_investment: UserInvestment
  coin_performance: CoinPerformance
  coin: string
  timestamp: string
}

export interface PortfolioData {
  timestamp: string
  price: number
  global: {
    realized_profits: number
    unrealized_gains: number
    total_gains: number
    performance_percentage: number
    total_portfolio_value: number
    current_capital: number
    position_value: number
    total_net_investments: number
  }
}
