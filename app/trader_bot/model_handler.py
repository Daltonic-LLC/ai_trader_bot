import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

class ModelHandler:
    """Manages model training and price prediction."""

    def train_model(self, df_features):
        """Trains a RandomForestRegressor on the provided features."""
        # Remove rows with missing values
        df_features = df_features.dropna()
        # Define feature columns (exclude target 'close')
        feature_cols = [col for col in df_features.columns if col != 'close']
        X = df_features[feature_cols]
        y = df_features['close']
        # Split into training and testing sets (80% train, 20% test)
        train_size = int(0.8 * len(df_features))
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]
        # Initialize and train the model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        return model, feature_cols

    def predict_close(self, model, df_features, feature_cols):
        """Predicts the next closing price and its uncertainty using the trained model."""
        # Get the latest feature values
        latest_features = df_features.iloc[-1][feature_cols]
        # Convert to a 2D numpy array (shape: 1 x number of features)
        latest_features_array = latest_features.values.reshape(1, -1)
        # Collect predictions from all trees for uncertainty estimation
        tree_predictions = [tree.predict(latest_features_array)[0] for tree in model.estimators_]
        # Calculate mean prediction and uncertainty
        predicted_close = np.mean(tree_predictions)
        uncertainty = np.std(tree_predictions)
        return predicted_close, uncertainty