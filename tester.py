from trader_bot.coin_trader import CoinTrader

if __name__ == "__main__":
    trader = CoinTrader("xrp", override=False)
    report = trader.run()
    print(report)