import os
import random
import time
import pickle
import pandas as pd
import numpy as np

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.losses import Huber
from tensorflow.keras.metrics import RootMeanSquaredError
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.regularizers import l2

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler


def load_and_preprocess_data(parking_file_path, precipitation_file_path=None, use_precipitation=False):
    """
    Load and preprocess parking lot Data and optionally precipitation Data.

    Parameters:
    - parking_file_path (str): Path to the parking lot Data CSV file.
    - precipitation_file_path (str, optional): Path to the precipitation Data CSV file.
    - use_precipitation (bool, optional): Whether to include precipitation Data as a feature.

    Returns:
    - df_features (pd.DataFrame): DataFrame containing the processed features for modeling.
    - df_merged (pd.DataFrame): The full merged DataFrame with all preprocessing applied.
    """
    # Load parking lot Data
    df_parking = pd.read_csv(parking_file_path)
    df_parking = df_parking[['update_datetime', 'lots_available']]
    df_parking['update_datetime'] = pd.to_datetime(df_parking['update_datetime'])
    df_parking = df_parking.sort_values('update_datetime')
    df_parking.set_index('update_datetime', inplace=True)
    df_parking['lots_available'] = df_parking['lots_available'].ffill()

    # Resample parking Data to 15-minute intervals
    df_parking_resampled = df_parking.resample('15min').mean()
    df_parking_resampled['lots_available'] = df_parking_resampled['lots_available'].ffill()

    if use_precipitation and precipitation_file_path:
        # Load precipitation Data
        df_precipitation = pd.read_csv(precipitation_file_path)
        df_precipitation = df_precipitation[['timestamp', 'precipitation']]
        df_precipitation['timestamp'] = pd.to_datetime(df_precipitation['timestamp'])
        df_precipitation = df_precipitation.sort_values('timestamp')
        df_precipitation.set_index('timestamp', inplace=True)
        df_precipitation['precipitation'] = df_precipitation['precipitation'].ffill()

        # Resample precipitation Data to 15-minute intervals
        df_precipitation_resampled = df_precipitation.resample('15min').mean()
        df_precipitation_resampled['precipitation'] = df_precipitation_resampled['precipitation'].interpolate()

        # Merge Data using inner join to ensure consistent timestamps
        df_merged = pd.merge(
            df_parking_resampled,
            df_precipitation_resampled,
            left_index=True,
            right_index=True,
            how='inner'
        )

        # Handle any missing values after merging
        df_merged['precipitation'] = df_merged['precipitation'].interpolate().ffill().bfill()
    else:
        # If not using precipitation, ensure timestamps are consistent with when precipitation is used
        if precipitation_file_path:
            # Load precipitation Data to get common timestamps
            df_precipitation = pd.read_csv(precipitation_file_path)
            df_precipitation = df_precipitation[['timestamp', 'precipitation']]
            df_precipitation['timestamp'] = pd.to_datetime(df_precipitation['timestamp'])
            df_precipitation = df_precipitation.sort_values('timestamp')
            df_precipitation.set_index('timestamp', inplace=True)
            df_precipitation['precipitation'] = df_precipitation['precipitation'].ffill()

            df_precipitation_resampled = df_precipitation.resample('15min').mean()
            df_precipitation_resampled['precipitation'] = df_precipitation_resampled['precipitation'].interpolate()

            # Merge Data using inner join
            df_merged = pd.merge(
                df_parking_resampled,
                df_precipitation_resampled,
                left_index=True,
                right_index=True,
                how='inner'
            )
        else:
            df_merged = df_parking_resampled.copy()

        # Create a placeholder precipitation feature
        df_merged['precipitation'] = 0

    # Add time features
    df_merged.reset_index(inplace=True)
    df_merged['hour'] = df_merged['update_datetime'].dt.hour
    df_merged['minute'] = df_merged['update_datetime'].dt.minute
    df_merged['day_of_week'] = df_merged['update_datetime'].dt.dayofweek
    df_merged['day_of_month'] = df_merged['update_datetime'].dt.day
    df_merged['month'] = df_merged['update_datetime'].dt.month
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

    df_merged['time_index'] = (
        df_merged['update_datetime'] - df_merged['update_datetime'].iloc[0]
    ).dt.total_seconds() / 60  # in minutes

    # Define the list of features
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

    df_merged.set_index('update_datetime', inplace=True)

    return df_merged[features], df_merged  # Return the processed Data


def create_sequences(data, window_size, forecast_horizon=1):
    """
    Create sequences of Data for training the model.

    Parameters:
    - Data (np.array): The input Data array.
    - window_size (int): The size of the input window (number of past time steps).
    - forecast_horizon (int): The number of future steps to forecast.

    Returns:
    - X (np.array): Array of input sequences.
    - y (np.array): Array of target values.
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


def train_model(model_name, df_features, df_full, use_precipitation=False, forecast_horizon=1, save_dir='.'):
    """
    Train the LSTM model and save it.

    Parameters:
    - model_name (str): Name of the model for saving files.
    - df_features (pd.DataFrame): DataFrame containing the features.
    - df_full (pd.DataFrame): Full DataFrame (not used but kept for potential future use).
    - use_precipitation (bool): Whether to include precipitation Data.
    - forecast_horizon (int): Forecast horizon; 1 for single-step prediction, >1 for multi-step prediction.
    - save_dir (str): Directory to save the model and related files.

    Returns:
    - model: The trained Keras model.
    """
    window_size = 20  # Window size

    # Create time series sequences
    X, y = create_sequences(df_features.values, window_size, forecast_horizon=forecast_horizon)

    # Create corresponding datetime labels
    if forecast_horizon == 1:
        dates = df_features.index[window_size:]
    else:
        dates = df_features.index[window_size + forecast_horizon - 1:]

    # Check if there is enough Data
    if len(X) == 0 or len(y) == 0:
        print(f"Not enough Data to train model {model_name}.")
        return

    # Split Data into training, validation, and test sets
    X_train, X_temp, y_train, y_temp, dates_train, dates_temp = train_test_split(
        X, y, dates, test_size=0.3, shuffle=False)
    X_val, X_test, y_val, y_test, dates_val, dates_test = train_test_split(
        X_temp, y_temp, dates_temp, test_size=0.5, shuffle=False)

    # Save the indices of Data splits
    split_indices = {
        'dates_train': dates_train,
        'dates_val': dates_val,
        'dates_test': dates_test
    }
    split_indices_path = os.path.join(save_dir, f'split_indices_{model_name}.npz')
    np.savez(split_indices_path, **split_indices)
    print(f"Data split indices saved to {split_indices_path}")

    # Normalize features (fit only on training Data)
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

    # Save the scalers
    scaler_X_path = os.path.join(save_dir, f'scaler_X_{model_name}.pkl')
    scaler_y_path = os.path.join(save_dir, f'scaler_y_{model_name}.pkl')
    with open(scaler_X_path, 'wb') as f:
        pickle.dump(scaler_X, f)
    with open(scaler_y_path, 'wb') as f:
        pickle.dump(scaler_y, f)
    print(f"Scalers saved to {scaler_X_path} and {scaler_y_path}")

    # Define the model
    model = Sequential()
    model.add(LSTM(64, kernel_regularizer=l2(0.0005), input_shape=(window_size, X_train_scaled.shape[2])))
    model.add(Dense(8, activation='relu'))
    if forecast_horizon == 1:
        model.add(Dense(1, activation='linear'))
    else:
        model.add(Dense(forecast_horizon))  # Output forecast_horizon predictions

    # Set up model checkpoint with .keras extension
    checkpoint_path = os.path.join(save_dir, f'best_model_{model_name}.keras')
    checkpoint = ModelCheckpoint(checkpoint_path, monitor='val_loss', save_best_only=True, verbose=1)

    # Compile the model
    model.compile(loss=Huber(),
                  optimizer=Adam(learning_rate=0.001),
                  metrics=[RootMeanSquaredError()])

    # Train the model
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

    # Save the final model
    final_model_path = os.path.join(save_dir, f'{model_name}.keras')
    model.save(final_model_path)
    print(f"Model {model_name} saved at {final_model_path}.")

    # Optionally return the model for further evaluation or prediction
    return model


def main():
    """
    Main function to train models for selected parking lots.
    """
    # Set random seed for reproducibility
    random.seed(42)

    # Parking lot Data directory
    parking_lot_dir = 'Data/ParkingAvailability'

    # Get all parking lot IDs
    all_parking_lots = [f.split('.')[0] for f in os.listdir(parking_lot_dir) if f.endswith('.csv')]
    all_parking_lots.sort()
    print(f"Found {len(all_parking_lots)} parking lots.")

    # Select the number of parking lots to process
    n = 100  # Modify n as needed

    # Randomly select n parking lots
    selected_parking_lots = random.sample(all_parking_lots, n)
    print(f"Randomly selected {n} parking lots: {selected_parking_lots}")

    # Create base directory to save models
    models_base_dir = 'trained_models'
    if not os.path.exists(models_base_dir):
        os.makedirs(models_base_dir)

    # Precipitation file path
    precipitation_file_path = 'Data/Precipitation/data.csv'  # Precipitation Data file

    # Check if precipitation file exists
    if not os.path.exists(precipitation_file_path):
        print(f"File {precipitation_file_path} does not exist. Please ensure the file is in the directory.")
        return

    # For each selected parking lot, train two models
    for parking_lot_id in selected_parking_lots:
        try:
            print(f"\nProcessing parking lot {parking_lot_id}")

            parking_file_path = os.path.join(parking_lot_dir, f'{parking_lot_id}.csv')

            # Check if parking lot file exists
            if not os.path.exists(parking_file_path):
                print(f"File {parking_file_path} does not exist. Skipping this parking lot.")
                continue

            # Create directory to save models for this parking lot
            parking_model_dir = os.path.join(models_base_dir, parking_lot_id)
            if not os.path.exists(parking_model_dir):
                os.makedirs(parking_model_dir)

            # ============================
            # Model 1: Only consider time-related features
            # ============================

            print(f"\n===== Training Model 1 ({parking_lot_id}): Only Time-related Features =====")
            df_features_time_only, df_full_time_only = load_and_preprocess_data(
                parking_file_path,
                precipitation_file_path=precipitation_file_path,
                use_precipitation=False
            )

            # Train Model 1
            model_name_time_only = 'model_time_only'
            train_model(
                model_name=model_name_time_only,
                df_features=df_features_time_only,
                df_full=df_full_time_only,
                use_precipitation=False,
                forecast_horizon=8,  # 8-step prediction
                save_dir=parking_model_dir
            )

            # ============================
            # Model 2: Consider time features and precipitation
            # ============================

            print(f"\n===== Training Model 2 ({parking_lot_id}): Time Features and Precipitation =====")
            df_features_with_precip, df_full_with_precip = load_and_preprocess_data(
                parking_file_path,
                precipitation_file_path=precipitation_file_path,
                use_precipitation=True
            )

            # Train Model 2
            model_name_with_precip = 'model_with_precipitation'
            train_model(
                model_name=model_name_with_precip,
                df_features=df_features_with_precip,
                df_full=df_full_with_precip,
                use_precipitation=True,
                forecast_horizon=8,  # 8-step prediction
                save_dir=parking_model_dir
            )

            print(f"\nCompleted training models for parking lot {parking_lot_id}.\nModels saved in {parking_model_dir}")

        except Exception as e:
            print(f"An error occurred while processing parking lot {parking_lot_id}: {e}")

    print("\nAll models have been trained and saved.")


if __name__ == "__main__":
    main()
