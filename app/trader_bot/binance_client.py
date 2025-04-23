from binance.client import Client
import math
import itertools
from typing import Optional, Tuple, List, Dict
import time

class BinanceClient:
    """Handles trading on Binance Testnet with versatile triangular arbitrage."""

    def __init__(self, api_key: str, api_secret: str, top_coins: list, base_currency: str = "USDT"):
        self.client = Client(api_key, api_secret, testnet=True)
        self.trading_fee = 0.001  # 0.1% fee per trade
        self.top_coins = top_coins
        self.base_currency = base_currency
        self.all_tickers = {}
        self.last_ticker_update = 0
        self.ticker_cache_duration = 10  # Refresh tickers every 10 seconds
        self.symbol_filters_cache = {}  # Cache for symbol filters

    def get_all_tickers(self) -> dict:
        """Fetches current prices for all trading pairs."""
        try:
            tickers = self.client.get_all_tickers()
            return {ticker['symbol']: float(ticker['price']) for ticker in tickers}
        except Exception as e:
            print(f"Error fetching tickers: {e}")
            return {}

    def refresh_tickers_if_needed(self):
        """Refreshes tickers if the cache duration has elapsed."""
        current_time = time.time()
        if current_time - self.last_ticker_update > self.ticker_cache_duration:
            self.all_tickers = self.get_all_tickers()
            self.last_ticker_update = current_time

    def get_symbol_filters(self, symbol: str) -> dict:
        """Fetches trading filters for a symbol, using a cache to avoid repeated API calls."""
        if symbol not in self.symbol_filters_cache:
            try:
                exchange_info = self.client.get_exchange_info()
                symbol_info = next(s for s in exchange_info['symbols'] if s['symbol'] == symbol)
                self.symbol_filters_cache[symbol] = {f['filterType']: f for f in symbol_info['filters']}
            except Exception as e:
                print(f"Error fetching filters for {symbol}: {e}")
                return {}
        return self.symbol_filters_cache[symbol]

    def adjust_quantity(self, symbol: str, quantity: float, price: float) -> float:
        """Adjusts quantity based on NOTIONAL and LOT_SIZE filters."""
        filters = self.get_symbol_filters(symbol)
        if not filters:
            return quantity
        min_notional = float(filters.get('MIN_NOTIONAL', {}).get('minNotional', 10.0))
        min_quantity = min_notional / price
        adjusted_quantity = max(quantity, min_quantity)
        step_size = float(filters.get('LOT_SIZE', {}).get('stepSize', 0.000001))
        if step_size > 0:
            adjusted_quantity = math.ceil(adjusted_quantity / step_size) * step_size
        return round(adjusted_quantity, 8)

    def calculate_arbitrage_profit(self, triangle: tuple, direction: str) -> float:
        """Calculates profit for a triangular arbitrage loop."""
        base, coin1, coin2 = triangle
        if direction == "clockwise":  # USDT -> coin1 -> coin2 -> USDT
            pair1 = f"{coin1}{base}"  # e.g., BTCUSDT
            pair2 = f"{coin1}{coin2}"  # e.g., BTCETH
            pair3 = f"{coin2}{base}"  # e.g., ETHUSDT
        else:  # USDT -> coin2 -> coin1 -> USDT
            pair1 = f"{coin2}{base}"
            pair2 = f"{coin2}{coin1}"
            pair3 = f"{coin1}{base}"

        if not all(pair in self.all_tickers for pair in [pair1, pair2, pair3]):
            return 0.0

        price1 = self.all_tickers[pair1]
        price2 = self.all_tickers[pair2]
        price3 = self.all_tickers[pair3]

        start_amount = 1.0  # Start with 1 USDT
        if direction == "clockwise":
            amount_coin1 = start_amount / price1
            amount_coin2 = amount_coin1 * price2
            final_amount = amount_coin2 * price3
        else:
            amount_coin2 = start_amount / price1
            amount_coin1 = amount_coin2 * price2
            final_amount = amount_coin1 * price3

        final_amount_after_fees = final_amount * (1 - self.trading_fee * 3)  # 3 trades
        profit = final_amount_after_fees - start_amount
        return profit if profit > 0 else 0.0

    def find_best_arbitrage_opportunity(self, specific_coin: str) -> Tuple[Optional[tuple], str, float, List[Dict]]:
        """Finds the most profitable arbitrage opportunity for triangles involving a specific coin."""
        self.refresh_tickers_if_needed()  # Ensure fresh ticker data
        opportunities = []
        best_profit = 0.0
        best_triangle = None
        best_direction = None

        # Only check triangles involving the specific coin
        for coin2 in self.top_coins:
            if coin2 == specific_coin:
                continue
            triangle = (self.base_currency, specific_coin, coin2)
            for direction in ["clockwise", "counterclockwise"]:
                profit = self.calculate_arbitrage_profit(triangle, direction)
                is_profitable = profit > 0
                opportunities.append({
                    'triangle': triangle,
                    'direction': direction,
                    'profit': profit,
                    'is_profitable': is_profitable
                })
                if profit > best_profit:
                    best_profit = profit
                    best_triangle = triangle
                    best_direction = direction

        if best_triangle:
            print(f"Best opportunity: {best_triangle} ({best_direction}), Profit: {best_profit:.2%}")
        else:
            print("No profitable arbitrage opportunity found.")
        return best_triangle, best_direction, best_profit, opportunities

    def execute_arbitrage(self, triangle: tuple, direction: str, amount: float) -> float:
        """Executes the arbitrage trade in either clockwise or counterclockwise direction."""
        self.refresh_tickers_if_needed()  # Ensure fresh prices before execution
        base, coin1, coin2 = triangle
        try:
            if direction == "clockwise":
                pair1 = f"{coin1}{base}"
                pair2 = f"{coin1}{coin2}"
                pair3 = f"{coin2}{base}"
                # Buy coin1 with USDT
                price1 = self.all_tickers[pair1]
                qty1 = self.adjust_quantity(pair1, amount / price1, price1)
                order1 = self.client.create_order(symbol=pair1, side=Client.SIDE_BUY, type=Client.ORDER_TYPE_MARKET, quantity=qty1)
                # Sell coin1 for coin2
                price2 = self.all_tickers[pair2]
                qty2 = self.adjust_quantity(pair2, qty1, price2)
                order2 = self.client.create_order(symbol=pair2, side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=qty1)
                # Sell coin2 for USDT
                price3 = self.all_tickers[pair3]
                qty3 = self.adjust_quantity(pair3, qty2 * price2, price3)
                order3 = self.client.create_order(symbol=pair3, side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=qty2)
                final_usdt = qty3 * price3
                print(f"Executed: {order1}, {order2}, {order3}")
            else:  # counterclockwise
                pair1 = f"{coin2}{base}"
                pair2 = f"{coin2}{coin1}"
                pair3 = f"{coin1}{base}"
                # Buy coin2 with USDT
                price1 = self.all_tickers[pair1]
                qty1 = self.adjust_quantity(pair1, amount / price1, price1)
                order1 = self.client.create_order(symbol=pair1, side=Client.SIDE_BUY, type=Client.ORDER_TYPE_MARKET, quantity=qty1)
                # Sell coin2 for coin1
                price2 = self.all_tickers[pair2]
                qty2 = self.adjust_quantity(pair2, qty1, price2)
                order2 = self.client.create_order(symbol=pair2, side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=qty1)
                # Sell coin1 for USDT
                price3 = self.all_tickers[pair3]
                qty3 = self.adjust_quantity(pair3, qty2 * price2, price3)
                order3 = self.client.create_order(symbol=pair3, side=Client.SIDE_SELL, type=Client.ORDER_TYPE_MARKET, quantity=qty2)
                final_usdt = qty3 * price3
                print(f"Executed: {order1}, {order2}, {order3}")
            return final_usdt
        except Exception as e:
            print(f"Error executing arbitrage trade: {e}")
            return amount