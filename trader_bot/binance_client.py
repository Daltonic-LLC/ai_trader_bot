from binance.client import Client
import math

class BinanceClient:
    """Handles trading operations on Binance Testnet."""
    
    def __init__(self, api_key: str, api_secret: str):
        """Initializes the Binance Testnet client."""
        self.client = Client(api_key, api_secret, testnet=True)

    def get_symbol_filters(self, symbol: str) -> dict:
        """Fetches the trading filters for a given symbol from Binance Testnet."""
        try:
            exchange_info = self.client.get_exchange_info()
            symbol_info = next(s for s in exchange_info['symbols'] if s['symbol'] == symbol)
            filters = {f['filterType']: f for f in symbol_info['filters']}
            return filters
        except Exception as e:
            print(f"AI Agent: Failed to fetch symbol filters for {symbol}: {str(e)}")
            return {}

    def adjust_quantity(self, symbol: str, quantity: float, price: float) -> float:
        """Adjusts the quantity to meet NOTIONAL and LOT_SIZE filters."""
        filters = self.get_symbol_filters(symbol)
        if not filters:
            return quantity  # Fallback to original quantity if filters can't be fetched

        # Get MIN_NOTIONAL filter
        min_notional_filter = filters.get('MIN_NOTIONAL', {})
        min_notional = float(min_notional_filter.get('minNotional', 10.0))  # Default to $10 if not found

        # Calculate minimum quantity based on notional value
        min_quantity = min_notional / price
        adjusted_quantity = max(quantity, min_quantity)  # Use the larger of the desired or minimum quantity

        # Get LOT_SIZE filter to adjust for step size
        lot_size_filter = filters.get('LOT_SIZE', {})
        step_size = float(lot_size_filter.get('stepSize', 0.000001))  # Default step size if not found
        min_qty = float(lot_size_filter.get('minQty', 0.0))

        # Ensure quantity meets minimum and aligns with step size
        if step_size > 0:
            adjusted_quantity = max(min_quantity, min_qty)
            adjusted_quantity = math.ceil(adjusted_quantity / step_size) * step_size

        # Round to avoid precision issues (Binance typically accepts up to 8 decimal places)
        adjusted_quantity = round(adjusted_quantity, 8)

        return adjusted_quantity

    def buy(self, coin: str, quantity: float, current_price: float) -> tuple[str, bool]:
        """Executes a buy order on Binance Testnet and returns the decision with success status."""
        try:
            symbol = f"{coin.upper()}USDT"
            # Adjust quantity based on NOTIONAL and LOT_SIZE filters
            adjusted_quantity = self.adjust_quantity(symbol, quantity, current_price)
            order = self.client.create_order(
                symbol=symbol,
                side=Client.SIDE_BUY,
                type=Client.ORDER_TYPE_MARKET,
                quantity=adjusted_quantity
            )
            print(f"AI Agent: Bought {adjusted_quantity} {coin.upper()} on Binance Testnet: {order}")
            return "BUY", True
        except Exception as e:
            print(f"AI Agent: Failed to buy {coin.upper()} on Binance Testnet: {str(e)}")
            return "HOLD", False

    def sell(self, coin: str, quantity: float, current_price: float) -> tuple[str, bool]:
        """Executes a sell order on Binance Testnet and returns the decision with success status."""
        try:
            symbol = f"{coin.upper()}USDT"
            # Adjust quantity based on NOTIONAL and LOT_SIZE filters
            adjusted_quantity = self.adjust_quantity(symbol, quantity, current_price)
            order = self.client.create_order(
                symbol=symbol,
                side=Client.SIDE_SELL,
                type=Client.ORDER_TYPE_MARKET,
                quantity=adjusted_quantity
            )
            print(f"AI Agent: Sold {adjusted_quantity} {coin.upper()} on Binance Testnet: {order}")
            return "SELL", True
        except Exception as e:
            print(f"AI Agent: Failed to sell {coin.upper()} on Binance Testnet: {str(e)}")
            return "HOLD", False