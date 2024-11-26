import os
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import Huber
from tensorflow.keras.metrics import RootMeanSquaredError

from sklearn.metrics import mean_squared_error, mean_absolute_error
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


def evaluate_models():
    """
    Load models and evaluate their performance with and without precipitation data.
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

    window_size = 20  # Window size
    forecast_horizon = 8  # Multi-step prediction

    # Load and preprocess data (without precipitation feature)
    df_features_time_only, _ = load_and_preprocess_data(
        parking_file_path,
        use_precipitation=False
    )

    # Load and preprocess data (with precipitation feature)
    df_features_with_precip, _ = load_and_preprocess_data(
        parking_file_path,
        precipitation_file_path=precipitation_file_path,
        use_precipitation=True
    )

    # Create sequence data (without precipitation feature)
    X_time_only, y_time_only = create_sequences(df_features_time_only.values, window_size, forecast_horizon=forecast_horizon)

    # Create sequence data (with precipitation feature)
    X_with_precip, y_with_precip = create_sequences(df_features_with_precip.values, window_size, forecast_horizon=forecast_horizon)

    # Create corresponding datetime labels
    dates_time_only = df_features_time_only.index[window_size + forecast_horizon - 1:]
    dates_with_precip = df_features_with_precip.index[window_size + forecast_horizon - 1:]

    # Split datasets into training, validation, and test sets
    def split_data(X, y, dates):
        X_train, X_temp, y_train, y_temp, dates_train, dates_temp = train_test_split(
            X, y, dates, test_size=0.3, shuffle=False)
        X_val, X_test, y_val, y_test, dates_val, dates_test = train_test_split(
            X_temp, y_temp, dates_temp, test_size=0.5, shuffle=False)
        return X_train, X_val, X_test, y_train, y_val, y_test, dates_train, dates_val, dates_test

    # Split data (without precipitation feature)
    X_train_time_only, X_val_time_only, X_test_time_only, y_train_time_only, y_val_time_only, y_test_time_only, dates_train_time_only, dates_val_time_only, dates_test_time_only = split_data(
        X_time_only, y_time_only, dates_time_only)

    # Split data (with precipitation feature)
    X_train_with_precip, X_val_with_precip, X_test_with_precip, y_train_with_precip, y_val_with_precip, y_test_with_precip, dates_train_with_precip, dates_val_with_precip, dates_test_with_precip = split_data(
        X_with_precip, y_with_precip, dates_with_precip)

    # Normalize features (fit only on training data)
    def scale_data(X_train, X_val, X_test, y_train, y_val, y_test):
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()

        # Reshape to 2D for scaler, then reshape back to 3D
        X_train_reshaped = X_train.reshape(-1, X_train.shape[-1])
        X_val_reshaped = X_val.reshape(-1, X_val.shape[-1])
        X_test_reshaped = X_test.reshape(-1, X_test.shape[-1])

        X_train_scaled = scaler_X.fit_transform(X_train_reshaped).reshape(X_train.shape)
        X_val_scaled = scaler_X.transform(X_val_reshaped).reshape(X_val.shape)
        X_test_scaled = scaler_X.transform(X_test_reshaped).reshape(X_test.shape)

        # Normalize target variable
        y_train_scaled = scaler_y.fit_transform(y_train)
        y_val_scaled = scaler_y.transform(y_val)
        y_test_scaled = scaler_y.transform(y_test)

        return X_train_scaled, X_val_scaled, X_test_scaled, y_train_scaled, y_val_scaled, y_test_scaled, scaler_X, scaler_y

    # Scale data (without precipitation feature)
    X_train_scaled_time_only, X_val_scaled_time_only, X_test_scaled_time_only, y_train_scaled_time_only, y_val_scaled_time_only, y_test_scaled_time_only, scaler_X_time_only, scaler_y_time_only = scale_data(
        X_train_time_only, X_val_time_only, X_test_time_only, y_train_time_only, y_val_time_only, y_test_time_only)

    # Scale data (with precipitation feature)
    X_train_scaled_with_precip, X_val_scaled_with_precip, X_test_scaled_with_precip, y_train_scaled_with_precip, y_val_scaled_with_precip, y_test_scaled_with_precip, scaler_X_with_precip, scaler_y_with_precip = scale_data(
        X_train_with_precip, X_val_with_precip, X_test_with_precip, y_train_with_precip, y_val_with_precip, y_test_with_precip)

    # Load models
    model_time_only = load_model('best_model_model_time_only.keras', custom_objects={'Huber': Huber()})
    model_with_precip = load_model('best_model_model_with_precipitation.keras', custom_objects={'Huber': Huber()})

    # Predict on test sets
    y_pred_scaled_time_only = model_time_only.predict(X_test_scaled_time_only)
    y_pred_scaled_with_precip = model_with_precip.predict(X_test_scaled_with_precip)

    # Inverse transform predictions and actual values
    y_pred_time_only = scaler_y_time_only.inverse_transform(y_pred_scaled_time_only)
    y_pred_with_precip = scaler_y_with_precip.inverse_transform(y_pred_scaled_with_precip)

    y_test_actual_time_only = scaler_y_time_only.inverse_transform(y_test_scaled_time_only)
    y_test_actual_with_precip = scaler_y_with_precip.inverse_transform(y_test_scaled_with_precip)

    # Calculate evaluation metrics
    def calculate_metrics(y_true, y_pred):
        # Calculate RMSE, MAE, MSE per prediction step
        rmse_per_step = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=0))
        mae_per_step = np.mean(np.abs(y_true - y_pred), axis=0)
        mse_per_step = np.mean((y_true - y_pred) ** 2, axis=0)

        # Calculate SMAPE per prediction step
        denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
        denominator = np.where(denominator == 0, 1e-10, denominator)  # Avoid division by zero
        smape_per_step = np.mean(np.abs(y_true - y_pred) / denominator, axis=0) * 100  # Percentage

        # Calculate Percentage RMSE per prediction step
        mean_y_per_step = np.mean(y_true, axis=0)
        percentage_rmse_per_step = (rmse_per_step / mean_y_per_step) * 100

        # Calculate overall RMSE, MAE, MSE
        rmse_overall = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae_overall = np.mean(np.abs(y_true - y_pred))
        mse_overall = np.mean((y_true - y_pred) ** 2)

        # Calculate overall SMAPE
        denominator_overall = (np.abs(y_true) + np.abs(y_pred)) / 2
        denominator_overall = np.where(denominator_overall == 0, 1e-10, denominator_overall)
        smape_overall = np.mean(np.abs(y_true - y_pred) / denominator_overall) * 100  # Percentage

        # Calculate overall Percentage RMSE
        mean_y_overall = np.mean(y_true)
        percentage_rmse_overall = (rmse_overall / mean_y_overall) * 100

        return rmse_per_step, mae_per_step, mse_per_step, smape_per_step, percentage_rmse_per_step, rmse_overall, mae_overall, mse_overall, smape_overall, percentage_rmse_overall

    # Calculate metrics (without precipitation feature)
    rmse_per_step_time_only, mae_per_step_time_only, mse_per_step_time_only, smape_per_step_time_only, perc_rmse_per_step_time_only, rmse_overall_time_only, mae_overall_time_only, mse_overall_time_only, smape_overall_time_only, perc_rmse_overall_time_only = calculate_metrics(
        y_test_actual_time_only, y_pred_time_only)

    # Calculate metrics (with precipitation feature)
    rmse_per_step_with_precip, mae_per_step_with_precip, mse_per_step_with_precip, smape_per_step_with_precip, perc_rmse_per_step_with_precip, rmse_overall_with_precip, mae_overall_with_precip, mse_overall_with_precip, smape_overall_with_precip, perc_rmse_overall_with_precip = calculate_metrics(
        y_test_actual_with_precip, y_pred_with_precip)

    # Print overall metrics
    print("\nModel 1 (Without Precipitation Feature):")
    print(f"Overall RMSE: {rmse_overall_time_only:.4f}")
    print(f"Overall MAE: {mae_overall_time_only:.4f}")
    print(f"Overall MSE: {mse_overall_time_only:.4f}")
    print(f"Overall SMAPE: {smape_overall_time_only:.2f}%")
    print(f"Overall Percentage RMSE: {perc_rmse_overall_time_only:.2f}%")

    print("\nModel 2 (With Precipitation Feature):")
    print(f"Overall RMSE: {rmse_overall_with_precip:.4f}")
    print(f"Overall MAE: {mae_overall_with_precip:.4f}")
    print(f"Overall MSE: {mse_overall_with_precip:.4f}")
    print(f"Overall SMAPE: {smape_overall_with_precip:.2f}%")
    print(f"Overall Percentage RMSE: {perc_rmse_overall_with_precip:.2f}%")

    # Compare metrics per prediction step
    steps = np.arange(1, forecast_horizon + 1)

    # Plot RMSE per forecast step
    plt.figure(figsize=(12, 6))
    plt.plot(steps, rmse_per_step_time_only, label='Without Precipitation')
    plt.plot(steps, rmse_per_step_with_precip, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('RMSE')
    plt.title('RMSE per Forecast Step')
    plt.legend()
    plt.show()

    # Plot MAE per forecast step
    plt.figure(figsize=(12, 6))
    plt.plot(steps, mae_per_step_time_only, label='Without Precipitation')
    plt.plot(steps, mae_per_step_with_precip, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MAE')
    plt.title('MAE per Forecast Step')
    plt.legend()
    plt.show()

    # Plot MSE per forecast step
    plt.figure(figsize=(12, 6))
    plt.plot(steps, mse_per_step_time_only, label='Without Precipitation')
    plt.plot(steps, mse_per_step_with_precip, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MSE')
    plt.title('MSE per Forecast Step')
    plt.legend()
    plt.show()

    # Plot SMAPE per forecast step
    plt.figure(figsize=(12, 6))
    plt.plot(steps, smape_per_step_time_only, label='Without Precipitation')
    plt.plot(steps, smape_per_step_with_precip, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('SMAPE (%)')
    plt.title('SMAPE per Forecast Step')
    plt.legend()
    plt.show()

    # Plot Percentage RMSE per forecast step
    plt.figure(figsize=(12, 6))
    plt.plot(steps, perc_rmse_per_step_time_only, label='Without Precipitation')
    plt.plot(steps, perc_rmse_per_step_with_precip, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('Percentage RMSE (%)')
    plt.title('Percentage RMSE per Forecast Step')
    plt.legend()
    plt.show()

    # Plot bar chart of Percentage RMSE per forecast step
    bar_width = 0.35
    index = np.arange(len(steps))
    plt.figure(figsize=(12, 6))
    plt.bar(index, perc_rmse_per_step_time_only, bar_width, label='Without Precipitation')
    plt.bar(index + bar_width, perc_rmse_per_step_with_precip, bar_width, label='With Precipitation')
    plt.xlabel('Forecast Horizon')
    plt.ylabel('Percentage RMSE (%)')
    plt.title('Percentage RMSE per Forecast Step')
    plt.xticks(index + bar_width / 2, steps)
    plt.legend()
    plt.show()

    # Plot predictions vs. actual values
    def plot_predictions(dates, y_true, y_pred, title):
        # Calculate the number of data points for one month (15-minute intervals)
        samples_per_day = 96  # 24 hours * 4 intervals per hour
        num_samples = min(samples_per_day * 30, len(y_true))  # Data points for one month

        # Create 8 subplots
        fig, axs = plt.subplots(4, 2, figsize=(15, 20))
        axs = axs.flatten()

        for i in range(forecast_horizon):
            axs[i].plot(dates[:num_samples], y_true[:num_samples, i], label=f'Actual t+{i+1}', linestyle='-')
            axs[i].plot(dates[:num_samples], y_pred[:num_samples, i], label=f'Predicted t+{i+1}', linestyle='--')
            axs[i].set_xlabel('Date Time')
            axs[i].set_ylabel('Lots Available')
            axs[i].set_title(f'Forecast t+{i+1}')
            axs[i].legend()
            axs[i].tick_params(axis='x', rotation=45)
            axs[i].xaxis.set_major_locator(plt.MaxNLocator(6))  # Control number of x-axis ticks

        plt.suptitle(title)
        plt.tight_layout(rect=[0, 0.03, 1, 0.97])
        plt.show()

    # Plot predictions for Model 1 (only one month's data)
    plot_predictions(dates_test_time_only, y_test_actual_time_only, y_pred_time_only, 'Model 1 Predictions vs Actual (Without Precipitation)')

    # Plot predictions for Model 2 (only one month's data)
    plot_predictions(dates_test_with_precip, y_test_actual_with_precip, y_pred_with_precip, 'Model 2 Predictions vs Actual (With Precipitation)')

    # Calculate performance improvements
    rmse_improvement_overall = rmse_overall_time_only - rmse_overall_with_precip
    mae_improvement_overall = mae_overall_time_only - mae_overall_with_precip
    mse_improvement_overall = mse_overall_time_only - mse_overall_with_precip
    smape_improvement_overall = smape_overall_time_only - smape_overall_with_precip
    perc_rmse_improvement_overall = perc_rmse_overall_time_only - perc_rmse_overall_with_precip

    # Performance improvement per prediction step
    rmse_improvement_per_step = rmse_per_step_time_only - rmse_per_step_with_precip
    mae_improvement_per_step = mae_per_step_time_only - mae_per_step_with_precip
    mse_improvement_per_step = mse_per_step_time_only - mse_per_step_with_precip
    smape_improvement_per_step = smape_per_step_time_only - smape_per_step_with_precip
    perc_rmse_improvement_per_step = perc_rmse_per_step_time_only - perc_rmse_per_step_with_precip

    # Print overall performance improvements
    print("\nPerformance Comparison:")
    print(f"RMSE Improvement (With Precipitation vs Without): {rmse_improvement_overall:.4f}")
    print(f"MAE Improvement (With Precipitation vs Without): {mae_improvement_overall:.4f}")
    print(f"MSE Improvement (With Precipitation vs Without): {mse_improvement_overall:.4f}")
    print(f"SMAPE Improvement (With Precipitation vs Without): {smape_improvement_overall:.2f}%")
    print(f"Percentage RMSE Improvement (With Precipitation vs Without): {perc_rmse_improvement_overall:.2f}%")

    # Plot RMSE improvement per forecast step
    plt.figure(figsize=(12, 6))
    plt.bar(steps, rmse_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('RMSE Improvement')
    plt.title('RMSE Improvement per Forecast Step (Positive Value Indicates Improvement)')
    plt.grid(True)
    plt.show()

    # Plot MAE improvement per forecast step
    plt.figure(figsize=(12, 6))
    plt.bar(steps, mae_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MAE Improvement')
    plt.title('MAE Improvement per Forecast Step (Positive Value Indicates Improvement)')
    plt.grid(True)
    plt.show()

    # Plot MSE improvement per forecast step
    plt.figure(figsize=(12, 6))
    plt.bar(steps, mse_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MSE Improvement')
    plt.title('MSE Improvement per Forecast Step (Positive Value Indicates Improvement)')
    plt.grid(True)
    plt.show()

    # Plot SMAPE improvement per forecast step
    plt.figure(figsize=(12, 6))
    plt.bar(steps, smape_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('SMAPE Improvement (%)')
    plt.title('SMAPE Improvement per Forecast Step (Positive Value Indicates Improvement)')
    plt.grid(True)
    plt.show()

    # Plot Percentage RMSE improvement per forecast step
    plt.figure(figsize=(12, 6))
    plt.bar(steps, perc_rmse_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('Percentage RMSE Improvement (%)')
    plt.title('Percentage RMSE Improvement per Forecast Step (Positive Value Indicates Improvement)')
    plt.grid(True)
    plt.show()

    # Print metrics per prediction step (without precipitation feature)
    print("\nMetrics per Prediction Step (Without Precipitation Feature):")
    for i in range(forecast_horizon):
        print(f"Step {i+1}: RMSE = {rmse_per_step_time_only[i]:.4f}, MAE = {mae_per_step_time_only[i]:.4f}, MSE = {mse_per_step_time_only[i]:.4f}, SMAPE = {smape_per_step_time_only[i]:.2f}%, Percentage RMSE = {perc_rmse_per_step_time_only[i]:.2f}%")

    # Print metrics per prediction step (with precipitation feature)
    print("\nMetrics per Prediction Step (With Precipitation Feature):")
    for i in range(forecast_horizon):
        print(f"Step {i+1}: RMSE = {rmse_per_step_with_precip[i]:.4f}, MAE = {mae_per_step_with_precip[i]:.4f}, MSE = {mse_per_step_with_precip[i]:.4f}, SMAPE = {smape_per_step_with_precip[i]:.2f}%, Percentage RMSE = {perc_rmse_per_step_with_precip[i]:.2f}%")

    # Print performance improvement per prediction step
    print("\nPerformance Improvement per Prediction Step (With Precipitation Feature):")
    for i in range(forecast_horizon):
        print(f"Step {i+1}: RMSE Improvement = {rmse_improvement_per_step[i]:.4f}, MAE Improvement = {mae_improvement_per_step[i]:.4f}, MSE Improvement = {mse_improvement_per_step[i]:.4f}, SMAPE Improvement = {smape_improvement_per_step[i]:.2f}%, Percentage RMSE Improvement = {perc_rmse_improvement_per_step[i]:.2f}%")

    # Calculate overall percentage improvements
    rmse_percentage_improvement_overall = (rmse_improvement_overall / rmse_overall_time_only) * 100
    mae_percentage_improvement_overall = (mae_improvement_overall / mae_overall_time_only) * 100
    mse_percentage_improvement_overall = (mse_improvement_overall / mse_overall_time_only) * 100
    smape_percentage_improvement_overall = (smape_improvement_overall / smape_overall_time_only) * 100
    perc_rmse_percentage_improvement_overall = (perc_rmse_improvement_overall / perc_rmse_overall_time_only) * 100

    # Print overall percentage improvements
    print("\nOverall Percentage Improvements (With Precipitation Feature):")
    print(f"RMSE Percentage Improvement: {rmse_percentage_improvement_overall:.2f}%")
    print(f"MAE Percentage Improvement: {mae_percentage_improvement_overall:.2f}%")
    print(f"MSE Percentage Improvement: {mse_percentage_improvement_overall:.2f}%")
    print(f"SMAPE Percentage Improvement: {smape_percentage_improvement_overall:.2f}%")
    print(f"Percentage RMSE Improvement: {perc_rmse_percentage_improvement_overall:.2f}%")

    # Calculate percentage improvements per prediction step
    rmse_percentage_improvement_per_step = rmse_improvement_per_step / rmse_per_step_time_only * 100
    mae_percentage_improvement_per_step = mae_improvement_per_step / mae_per_step_time_only * 100
    mse_percentage_improvement_per_step = mse_improvement_per_step / mse_per_step_time_only * 100
    smape_percentage_improvement_per_step = smape_improvement_per_step / smape_per_step_time_only * 100
    perc_rmse_percentage_improvement_per_step = perc_rmse_improvement_per_step / perc_rmse_per_step_time_only * 100

    # Print percentage improvements per prediction step
    print("\nPercentage Improvements per Prediction Step (With Precipitation Feature):")
    for i in range(forecast_horizon):
        print(f"Step {i + 1}: RMSE Percentage Improvement = {rmse_percentage_improvement_per_step[i]:.2f}%, "
              f"MAE Percentage Improvement = {mae_percentage_improvement_per_step[i]:.2f}%, "
              f"MSE Percentage Improvement = {mse_percentage_improvement_per_step[i]:.2f}%, "
              f"SMAPE Percentage Improvement = {smape_percentage_improvement_per_step[i]:.2f}%, "
              f"Percentage RMSE Improvement = {perc_rmse_percentage_improvement_per_step[i]:.2f}%")

    # Plot bar charts for percentage improvements
    # RMSE
    plt.figure(figsize=(12, 6))
    plt.bar(steps, rmse_percentage_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('RMSE Percentage Improvement (%)')
    plt.title('RMSE Percentage Improvement per Forecast Step')
    plt.grid(True)
    plt.show()

    # MAE
    plt.figure(figsize=(12, 6))
    plt.bar(steps, mae_percentage_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MAE Percentage Improvement (%)')
    plt.title('MAE Percentage Improvement per Forecast Step')
    plt.grid(True)
    plt.show()

    # MSE
    plt.figure(figsize=(12, 6))
    plt.bar(steps, mse_percentage_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('MSE Percentage Improvement (%)')
    plt.title('MSE Percentage Improvement per Forecast Step')
    plt.grid(True)
    plt.show()

    # SMAPE
    plt.figure(figsize=(12, 6))
    plt.bar(steps, smape_percentage_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('SMAPE Percentage Improvement (%)')
    plt.title('SMAPE Percentage Improvement per Forecast Step')
    plt.grid(True)
    plt.show()

    # Percentage RMSE
    plt.figure(figsize=(12, 6))
    plt.bar(steps, perc_rmse_percentage_improvement_per_step)
    plt.xlabel('Forecast Horizon')
    plt.ylabel('Percentage RMSE Improvement (%)')
    plt.title('Percentage RMSE Improvement per Forecast Step')
    plt.grid(True)
    plt.show()

    # ============ Additional Plots ============
    # Plot comparison for prediction step 1 (without precipitation feature)
    samples_per_day = 96  # 15-minute intervals, 96 data points per day
    num_samples = min(samples_per_day * 30, len(y_test_actual_time_only))  # Data points for one month

    plt.figure(figsize=(15, 6))
    plt.plot(dates_test_time_only[:num_samples], y_test_actual_time_only[:num_samples, 0], label='Actual (Without Precipitation)', linestyle='-')
    plt.plot(dates_test_time_only[:num_samples], y_pred_time_only[:num_samples, 0], label='Predicted (Without Precipitation)', linestyle='--')
    plt.xlabel('Date Time')
    plt.ylabel('Lots Available')
    plt.title('Predicted vs Actual Values for Prediction Step 1 (Without Precipitation)')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    # Plot comparison for prediction step 1 (with precipitation feature)
    num_samples = min(samples_per_day * 30, len(y_test_actual_with_precip))

    plt.figure(figsize=(16, 9))  # Adjust aspect ratio
    plt.plot(dates_test_with_precip[:num_samples], y_test_actual_with_precip[:num_samples, 0], label='Actual', linestyle='-', linewidth=2)
    plt.plot(dates_test_with_precip[:num_samples], y_pred_with_precip[:num_samples, 0], label='Predicted', linestyle='-', linewidth=2)
    plt.xlabel('Date Time', fontsize=14)
    plt.ylabel('Lots Available', fontsize=14)
    plt.title('Predicted vs Actual Values for Prediction Step 1 (With Precipitation)', fontsize=16)
    plt.legend(fontsize=12)
    plt.xticks(rotation=45, fontsize=12)
    plt.yticks(fontsize=12)
    plt.tight_layout()
    plt.show()
    # ============ End of Additional Plots ============


if __name__ == "__main__":
    evaluate_models()