import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.losses import Huber
from tensorflow.keras.metrics import RootMeanSquaredError
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2

from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler


def load_and_preprocess_data(parking_file_path, precipitation_file_path=None, use_precipitation=False):
    """
    Load and preprocess parking lot data, and optionally precipitation data.

    Parameters:
    - parking_file_path (str): Path to the parking lot CSV file.
    - precipitation_file_path (str, optional): Path to the precipitation CSV file.
    - use_precipitation (bool, optional): Whether to include precipitation data.

    Returns:
    - df_features (pd.DataFrame): DataFrame containing selected features.
    - df_merged (pd.DataFrame): DataFrame containing the full merged data.
    """
    # Load parking lot data
    df_parking = pd.read_csv(parking_file_path)
    # Select required columns
    df_parking = df_parking[['update_datetime', 'lots_available']]
    df_parking['update_datetime'] = pd.to_datetime(df_parking['update_datetime'])
    df_parking = df_parking.sort_values('update_datetime')
    df_parking.set_index('update_datetime', inplace=True)
    df_parking['lots_available'] = df_parking['lots_available'].ffill()

    # Initialize precipitation data as None
    df_precipitation_resampled = None

    if use_precipitation and precipitation_file_path:
        # Load precipitation data
        df_precipitation = pd.read_csv(precipitation_file_path)
        df_precipitation = df_precipitation[['timestamp', 'precipitation']]
        df_precipitation['timestamp'] = pd.to_datetime(df_precipitation['timestamp'])
        df_precipitation = df_precipitation.sort_values('timestamp')
        df_precipitation.set_index('timestamp', inplace=True)
        df_precipitation['precipitation'] = df_precipitation['precipitation'].ffill()

        # Resample precipitation data to 15-minute intervals
        df_precipitation_resampled = df_precipitation.resample('15min').mean()
        df_precipitation_resampled['precipitation'] = df_precipitation_resampled['precipitation'].interpolate()

    # Resample parking data to 15-minute intervals
    df_parking_resampled = df_parking.resample('15min').mean()
    df_parking_resampled['lots_available'] = df_parking_resampled['lots_available'].ffill()

    # Merge data
    if use_precipitation and df_precipitation_resampled is not None:
        df_merged = pd.merge(df_parking_resampled, df_precipitation_resampled, left_index=True, right_index=True,
                             how='left')
        # Handle potential missing values after merging
        df_merged['precipitation'] = df_merged['precipitation'].interpolate().ffill().bfill()
    else:
        df_merged = df_parking_resampled
        # If not using precipitation feature, create a placeholder column
        df_merged['precipitation'] = 0  # Or choose to drop this column

    # Reset index to ensure consistent indexing
    df_merged = df_merged.reset_index().set_index('update_datetime')

    # Add time features
    df_merged['hour'] = df_merged.index.hour
    df_merged['minute'] = df_merged.index.minute
    df_merged['day_of_week'] = df_merged.index.dayofweek
    df_merged['day_of_month'] = df_merged.index.day
    df_merged['month'] = df_merged.index.month
    df_merged['is_weekend'] = df_merged['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

    # Cyclical encoding of time features
    df_merged['hour_sin'] = np.sin(2 * np.pi * df_merged['hour'] / 24)
    df_merged['hour_cos'] = np.cos(2 * np.pi * df_merged['hour'] / 24)
    df_merged['minute_sin'] = np.sin(2 * np.pi * df_merged['minute'] / 60)
    df_merged['minute_cos'] = np.cos(2 * np.pi * df_merged['minute'] / 60)
    df_merged['day_sin'] = np.sin(2 * np.pi * df_merged['day_of_week'] / 7)
    df_merged['day_cos'] = np.cos(2 * np.pi * df_merged['day_of_week'] / 7)
    df_merged['day_of_month_sin'] = np.sin(2 * np.pi * df_merged['day_of_month'] / 31)
    df_merged['day_of_month_cos'] = np.cos(2 * np.pi * df_merged['day_of_month'] / 31)
    df_merged['month_sin'] = np.sin(2 * np.pi * df_merged['month'] / 12)
    df_merged['month_cos'] = np.cos(2 * np.pi * df_merged['month'] / 12)

    df_merged['time_index'] = (df_merged.index - df_merged.index[0]).total_seconds() / 60  # In minutes

    # Define feature list
    features = [
        'lots_available',
        'hour_sin', 'hour_cos',
        'minute_sin', 'minute_cos',
        'day_sin', 'day_cos',
        'day_of_month_sin', 'day_of_month_cos',
        'month_sin', 'month_cos',
        'is_weekend',
        'time_index',
    ]

    # If using precipitation feature, add it to the feature list
    if use_precipitation:
        features.insert(1, 'precipitation')  # Insert 'precipitation' after 'lots_available'

    return df_merged[features], df_merged  # Return the processed data


def create_sequences(data, window_size, forecast_horizon=1):
    """
    Create sequences for time series data.

    Parameters:
    - data (np.array): Input data array.
    - window_size (int): Size of the input window.
    - forecast_horizon (int): Number of future steps to predict.

    Returns:
    - X (np.array): Input sequences.
    - y (np.array): Target sequences.
    """
    X = []
    y = []
    for i in range(len(data) - window_size - forecast_horizon + 1):
        X.append(data[i:i + window_size])
        if forecast_horizon == 1:
            y.append(data[i + window_size][0])  # Single-step prediction
        else:
            y.append(data[i + window_size:i + window_size + forecast_horizon, 0])  # Multi-step prediction
    X = np.array(X)
    y = np.array(y)
    return X, y


def train_model(model_name, df_features, df_full, use_precipitation=False, forecast_horizon=1):
    """
    Train the model and save it.

    Parameters:
    - model_name (str): Name of the model for saving files.
    - df_features (pd.DataFrame): DataFrame containing feature data.
    - df_full (pd.DataFrame): DataFrame containing full data (unused but kept for potential future needs).
    - use_precipitation (bool): Whether to use precipitation feature.
    - forecast_horizon (int): Forecast horizon; 1 for single-step prediction, >1 for multi-step prediction.

    Returns:
    - model: Trained model.
    - scaler_X: Scaler for input features.
    - scaler_y: Scaler for target variable.
    - X_test_scaled: Scaled test input data.
    - y_test_scaled: Scaled test target data.
    - dates_test: Dates corresponding to the test data.
    """
    window_size = 20  # Window size

    # Create time series sequences
    X, y = create_sequences(df_features.values, window_size, forecast_horizon=forecast_horizon)

    # Create corresponding datetime labels
    if forecast_horizon == 1:
        dates = df_features.index[window_size:]
    else:
        dates = df_features.index[window_size + forecast_horizon - 1:]

    # Check if there is enough data
    if len(X) == 0 or len(y) == 0:
        print(f"Insufficient data to train model {model_name}.")
        return

    # Split the dataset into training, validation, and test sets
    X_train, X_temp, y_train, y_temp, dates_train, dates_temp = train_test_split(
        X, y, dates, test_size=0.3, shuffle=False)
    X_val, X_test, y_val, y_test, dates_val, dates_test = train_test_split(
        X_temp, y_temp, dates_temp, test_size=0.5, shuffle=False)

    # Normalize features (fit only on training data)
    scaler_X = MinMaxScaler()
    # Reshape to 2D for scaler, then reshape back to 3D
    X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
    X_val_reshaped = X_val.reshape(-1, X_val.shape[-1])
    X_test_reshaped = X_test.reshape(-1, X_test.shape[-1])

    X_train_scaled = scaler_X.fit_transform(X_train_reshaped).reshape(X_train.shape[0], window_size, X_train.shape[2])
    X_val_scaled = scaler_X.transform(X_val_reshaped).reshape(X_val.shape[0], window_size, X_val.shape[2])
    X_test_scaled = scaler_X.transform(X_test_reshaped).reshape(X_test.shape[0], window_size, X_test.shape[2])

    # Normalize target variable
    scaler_y = MinMaxScaler()
    if forecast_horizon == 1:
        y_train_scaled = scaler_y.fit_transform(y_train.reshape(-1, 1)).flatten()
        y_val_scaled = scaler_y.transform(y_val.reshape(-1, 1)).flatten()
        y_test_scaled = scaler_y.transform(y_test.reshape(-1, 1)).flatten()
    else:
        y_train_scaled = scaler_y.fit_transform(y_train)
        y_val_scaled = scaler_y.transform(y_val)
        y_test_scaled = scaler_y.transform(y_test)

    # Define the model
    model = Sequential()
    model.add(LSTM(64, kernel_regularizer=l2(0.0005), input_shape=(window_size, X_train_scaled.shape[2])))
    model.add(Dense(8, activation='relu'))
    if forecast_horizon == 1:
        model.add(Dense(1, activation='linear'))
    else:
        model.add(Dense(forecast_horizon))  # Output forecast_horizon predictions

    model.summary()

    checkpoint_path = f'best_model_W187{model_name}.keras'
    checkpoint = ModelCheckpoint(checkpoint_path, monitor='val_loss', save_best_only=True, verbose=1)

    # Compile the model
    model.compile(loss=Huber(),
                  optimizer=Adam(learning_rate=0.001),
                  metrics=[RootMeanSquaredError()])

    start_time = time.time()
    history = model.fit(
        X_train_scaled, y_train_scaled,
        validation_data=(X_val_scaled, y_val_scaled),
        epochs=50,
        batch_size=128,
        callbacks=[checkpoint],
        verbose=1
    )
    training_time = time.time() - start_time
    print(f"Training time for {model_name}: {training_time:.3f} seconds")

    # Save the model (final model)
    model.save(f'W187{model_name}.keras')
    print(f"Model {model_name} saved.")

    # Optionally return the model and scalers for further evaluation or prediction
    return model, scaler_X, scaler_y, X_test_scaled, y_test_scaled, dates_test


def main():
    """
    Main function to train models with and without precipitation data.
    """
    # these files are in the same directory as this script
    parking_file_path = 'W187.csv'
    precipitation_file_path = 'data.csv'

    # Check if files exist
    if not os.path.exists(parking_file_path):
        print(f"File {parking_file_path} does not exist. Please ensure the file is in the current directory.")
        return
    if not os.path.exists(precipitation_file_path):
        print(f"File {precipitation_file_path} does not exist. Please ensure the file is in the current directory.")
        return

    # ============================
    # Model 1: Only consider time-related features
    # ============================

    print("\n===== Training Model 1: Only Time-Related Features =====")
    df_features_time_only, df_full_time_only = load_and_preprocess_data(
        parking_file_path,
        use_precipitation=False
    )

    # Train Model 1
    model_name_time_only = 'model_time_only'
    model_time_only, scaler_X_time_only, scaler_y_time_only, X_test_scaled_time_only, y_test_scaled_time_only, dates_test_time_only = train_model(
        model_name=model_name_time_only,
        df_features=df_features_time_only,
        df_full=df_full_time_only,
        use_precipitation=False,
        forecast_horizon=8  # Multi-step prediction
    )

    # ============================
    # Model 2: Consider time features and precipitation
    # ============================

    print("\n===== Training Model 2: Time Features and Precipitation =====")
    df_features_with_precip, df_full_with_precip = load_and_preprocess_data(
        parking_file_path,
        precipitation_file_path=precipitation_file_path,
        use_precipitation=True
    )

    # Train Model 2
    model_name_with_precip = 'model_with_precipitation'
    model_with_precip, scaler_X_with_precip, scaler_y_with_precip, X_test_scaled_with_precip, y_test_scaled_with_precip, dates_test_with_precip = train_model(
        model_name=model_name_with_precip,
        df_features=df_features_with_precip,
        df_full=df_full_with_precip,
        use_precipitation=True,
        forecast_horizon=8  # Multi-step prediction
    )

    print("\nAll models have been trained and saved.")


if __name__ == "__main__":
    main()