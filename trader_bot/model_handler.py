import pandas as pd
from sklearn.ensemble import RandomForestRegressor

class ModelHandler:
    """Manages model training and price prediction."""
    def train_model(self, df_features):
        """Trains a RandomForestRegressor on the provided features."""
        df_features = df_features.dropna()
        feature_cols = [col for col in df_features.columns if col != 'close']
        X = df_features[feature_cols]
        y = df_features['close']
        train_size = int(0.8 * len(df_features))
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        return model, feature_cols

    def predict_close(self, model, df_features, feature_cols):
        """Predicts the next closing price using the trained model."""
        latest_features = df_features.iloc[-1][feature_cols]
        # Convert to a DataFrame to preserve feature names
        latest_features_df = pd.DataFrame([latest_features], columns=feature_cols)
        return model.predict(latest_features_df)[0]