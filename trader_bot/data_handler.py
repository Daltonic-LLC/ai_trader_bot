import pandas as pd
import ta

class DataHandler:
    """Handles loading and preparation of historical data."""
    def __init__(self, file_service, coin, override):
        self.file_service = file_service
        self.coin = coin
        self.override = override

    def load_historical_data(self):
        """Loads historical data for the specified coin."""
        historical_file = (self.file_service.download_file(self.coin) if self.override 
                           else self.file_service.get_latest_file(self.coin))
        df = pd.read_csv(historical_file, sep=';')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.sort_values('timestamp', ascending=True).reset_index(drop=True)

    def prepare_features(self, df):
        """Prepares features from historical data for model training."""
        numerical_cols = ['open', 'high', 'low', 'close', 'volume', 'marketCap']
        df_numerical = df[numerical_cols].copy()
        df_numerical['EMA20'] = ta.trend.ema_indicator(df_numerical['close'], window=20)
        df_numerical['RSI'] = ta.momentum.rsi(df_numerical['close'], window=14)
        df_numerical['MACD'] = ta.trend.macd(df_numerical['close'])
        for i in range(1, 6):
            df_numerical[f'close_t-{i}'] = df_numerical['close'].shift(i)
            df_numerical[f'volume_t-{i}'] = df_numerical['volume'].shift(i)
        return df_numerical