import os
import time
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import *
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.losses import Huber
from tensorflow.keras.metrics import RootMeanSquaredError
from tensorflow.keras.optimizers import Adam
from sklearn.model_selection import train_test_split
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.models import load_model
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras.losses import MeanSquaredError


def get_all_parking_lots():
    """
    Retrieve all parking lot IDs from the 'Data/ParkingAvailability' directory.

    Returns:
    - parking_lots (list): A sorted list of parking lot IDs.
    """
    # Iterate all files under 'Data/ParkingAvailability' directory
    parking_lots = []
    for filename in os.listdir('Data/ParkingAvailability'):
        if filename.endswith('.csv'):
            parking_lots.append(filename.split('.')[0])
    # Sort the parking lots
    parking_lots.sort()
    print(parking_lots)
    return parking_lots


def load_and_preprocess_data(file_path):
    """
    Load and preprocess parking lot data from a CSV file.

    Parameters:
    - file_path (str): Path to the parking lot CSV file.

    Returns:
    - df_resampled (pd.DataFrame): Resampled data at 15-minute intervals.
    """
    # Read the CSV file
    df = pd.read_csv(file_path)
    # Parse datetime
    df['update_datetime'] = pd.to_datetime(df['update_datetime'])
    # Sort by time
    df = df.sort_values('update_datetime')
    # Set datetime as the index
    df.set_index('update_datetime', inplace=True)
    # Handle missing values (if any)
    df['lots_available'] = df['lots_available'].ffill()
    # Select numerical columns needed
    numeric_cols = ['lots_available']
    df_numeric = df[numeric_cols]
    # Resample to 15-minute intervals
    df_resampled = df_numeric.resample('15min').mean()
    df_resampled['lots_available'] = df_resampled['lots_available'].ffill()
    # Reset index to ensure uniform time intervals
    df_resampled = df_resampled.reset_index().set_index('update_datetime')
    # Return the resampled data
    return df_resampled


def create_sequences(data, window_size, forecast_horizon):
    """
    Create sequences of data for time series prediction.

    Parameters:
    - data (np.array): Input data array.
    - window_size (int): Number of past time steps to use as input.
    - forecast_horizon (int): Number of future time steps to predict.

    Returns:
    - X (np.array): Array of input sequences.
    - y (np.array): Array of target sequences.
    """
    X = []
    y = []
    for i in range(len(data) - window_size - forecast_horizon + 1):
        X.append(data[i:i + window_size])
        y.append(data[i + window_size:i + window_size + forecast_horizon, 0])  # 'lots_available' is the first column
    X = np.array(X)
    y = np.array(y)
    return X, y


def train(parking_lot_id):
    """
    Train an LSTM model for a specific parking lot and save the trained model.

    Parameters:
    - parking_lot_id (str): The ID of the parking lot.
    """
    # File path
    file_path = f'Data/ParkingAvailability/{parking_lot_id}.csv'
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist. Please ensure the file is in the current directory.")
        return

    # Load and preprocess data
    df = load_and_preprocess_data(file_path)

    # Create time series features
    window_size = 20          # Window size of 20
    forecast_horizon = 8      # Predict the next 8 time steps

    X, y = create_sequences(df.values, window_size, forecast_horizon)

    # Split data into training, validation, and test sets
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, shuffle=False)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, shuffle=False)

    # Define the multi-step prediction LSTM model
    model = Sequential()
    model.add(LSTM(64, input_shape=(window_size, 1)))
    model.add(Dense(8, activation='relu'))
    model.add(Dense(forecast_horizon))  # Output forecast_horizon predictions

    model.summary()

    cp = ModelCheckpoint(f'models_to_deploy/{parking_lot_id}.keras', save_best_only=True)

    # Compile the model
    model.compile(loss=Huber(),
                  optimizer=Adam(learning_rate=0.001),
                  metrics=[RootMeanSquaredError()]
                  )

    # Train the model
    start_time = time.time()
    model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=128,
        verbose=1,
        callbacks=[cp]
    )
    training_time = time.time() - start_time
    print(f"Training time: {training_time:.3f} seconds")


def main():
    """
    Main function to train and export models for all parking lots.
    """
    ALL = get_all_parking_lots()
    # Get current working directory
    cwd = os.getcwd()
    # print(cwd)

    for parking_lot_id in ALL:
        try:
            train(parking_lot_id)
            model = tf.keras.models.load_model(f'models_to_deploy/{parking_lot_id}.keras')
            model.export(f'deploy_lstm/{parking_lot_id}/1')

            # Change directory to 'deploy_lstm/{parking_lot_id}/1'
            os.chdir(f"{cwd}/deploy_lstm/{parking_lot_id}")

            # Compress the folder into a tar.gz file
            os.system(f"tar -zcf ../{parking_lot_id}.tar.gz 1")

            # Change back to the original directory
            os.chdir(cwd)
        except Exception as e:
            # Append the error message to a file
            with open('error.log', 'a') as f:
                f.write(f"Error: {e}\n")


if __name__ == '__main__':
    main()