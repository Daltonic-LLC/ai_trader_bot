from app.trader_bot.coin_trader import CoinTrader
from app.services.capital_manager import CapitalManager

if __name__ == "__main__":
    coin = "sui"
    # Initialize CapitalManager with the current coin (bnb) and its initial capital
    capital_manager = CapitalManager()
    
    # Run CoinTrader for BNB
    trader = CoinTrader(coin=coin, override=False, capital_manager=capital_manager)
    report = trader.run()
    print(report)