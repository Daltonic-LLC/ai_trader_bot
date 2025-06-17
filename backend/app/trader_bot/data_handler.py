import pandas as pd
import ta
import os


class DataHandler:
    """Handles loading and preparation of historical data."""

    def __init__(self, history_service, coin, override, skip_download=False):
        self.history_service = history_service
        self.coin = coin
        self.override = override
        self.skip_download = skip_download  # New parameter to control download behavior

    def load_historical_data(self):
        """Loads historical data for the specified coin."""
        if self.skip_download:
            # Try to load cached data only
            historical_file = self.history_service.get_latest_history(self.coin)
            if historical_file is None or not os.path.exists(historical_file):
                raise ValueError(f"No cached historical data available for {self.coin}")
        else:
            # Use override to decide whether to download or use cached data
            historical_file = (
                self.history_service.download_history(self.coin)
                if self.override
                else self.history_service.get_latest_history(self.coin)
            )
            if historical_file is None or not os.path.exists(historical_file):
                raise ValueError(
                    f"No historical data available for {self.coin} after download attempt"
                )

        df = pd.read_csv(historical_file, sep=";")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df.sort_values("timestamp", ascending=True).reset_index(drop=True)

    def prepare_features(self, df):
        """Prepares features from historical data for model training."""
        numerical_cols = ["open", "high", "low", "close", "volume", "marketCap"]
        df_numerical = df[numerical_cols].copy()
        df_numerical["EMA20"] = ta.trend.ema_indicator(df_numerical["close"], window=20)
        df_numerical["RSI"] = ta.momentum.rsi(df_numerical["close"], window=14)
        df_numerical["MACD"] = ta.trend.macd(df_numerical["close"])
        for i in range(1, 6):
            df_numerical[f"close_t-{i}"] = df_numerical["close"].shift(i)
            df_numerical[f"volume_t-{i}"] = df_numerical["volume"].shift(i)
        return df_numerical

    def calculate_volatility(self, df, window=30):
        """Calculates the standard deviation of daily returns over the given window."""
        df["daily_return"] = df["close"].pct_change()
        volatility = df["daily_return"].rolling(window).std().iloc[-1]
        return volatility if not pd.isna(volatility) else 0.01
