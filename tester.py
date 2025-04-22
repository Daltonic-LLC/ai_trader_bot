from trader_bot.coin_trader import CoinTrader
from services.capital_manager import CapitalManager

if __name__ == "__main__":
    coin = "solana"
    # Initialize CapitalManager with the current coin (bnb) and its initial capital
    capital_manager = CapitalManager(coin=coin)
    
    # Run CoinTrader for BNB
    trader = CoinTrader(coin=coin, override=False, capital_manager=capital_manager)
    report = trader.run()
    print(report)
    
    # Optionally, add another coin (e.g., XRP) by depositing funds or initializing a new trader
    # capital_manager.deposit("xrp", 1000.0)  # Allocate capital for XRP
    # trader_xrp = CoinTrader(coin="xrp", override=True, capital_manager=capital_manager)
    # report_xrp = trader_xrp.run()
    # print(report_xrp)