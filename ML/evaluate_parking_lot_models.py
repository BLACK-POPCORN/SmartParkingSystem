import os
import random
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import Huber

from sklearn.preprocessing import MinMaxScaler
from scipy.stats import ttest_rel


def load_and_preprocess_data(parking_file_path, precipitation_file_path=None, use_precipitation=False):
    """
    Load and preprocess parking lot Data, and optionally precipitation Data.

    Parameters:
    - parking_file_path (str): Path to the parking lot CSV file.
    - precipitation_file_path (str, optional): Path to the precipitation Data CSV file.
    - use_precipitation (bool, optional): Whether to include precipitation Data as a feature.

    Returns:
    - df_features (pd.DataFrame): Processed features for modeling.
    - df_merged (pd.DataFrame): The full merged DataFrame after preprocessing.
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
        # If not using precipitation, still ensure timestamps are consistent with when precipitation is used
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
    ).dt.total_seconds() / 60  # In minutes

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
    Create sequences of Data for training/testing the model.

    Parameters:
    - Data (np.array): Input Data array.
    - window_size (int): Size of the input window (number of past time steps).
    - forecast_horizon (int): Number of future steps to predict.

    Returns:
    - X (np.array): Array of input sequences.
    - y (np.array): Array of target sequences.
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


def evaluate_parking_lot(parking_lot_id, models_base_dir, parking_lot_dir, precipitation_file_path, forecast_horizon=8):
    """
    Evaluate models for a given parking lot.

    Parameters:
    - parking_lot_id (str): ID of the parking lot.
    - models_base_dir (str): Base directory where models are saved.
    - parking_lot_dir (str): Directory containing parking lot Data files.
    - precipitation_file_path (str): Path to the precipitation Data CSV file.
    - forecast_horizon (int): Number of future steps to predict.

    Returns:
    - results (dict): Dictionary containing evaluation metrics and results.
    """
    results = {}

    try:
        print(f"\nEvaluating models for parking lot {parking_lot_id}")

        parking_file_path = os.path.join(parking_lot_dir, f'{parking_lot_id}.csv')

        # Check if parking lot file exists
        if not os.path.exists(parking_file_path):
            print(f"File {parking_file_path} does not exist. Skipping this parking lot.")
            return None

        # Load the model save directory
        parking_model_dir = os.path.join(models_base_dir, parking_lot_id)

        # Load and preprocess Data (with precipitation feature)
        df_features_with_precip, _ = load_and_preprocess_data(
            parking_file_path,
            precipitation_file_path=precipitation_file_path,
            use_precipitation=True
        )

        # Load and preprocess Data (without precipitation feature but ensure consistent timestamps)
        df_features_time_only, _ = load_and_preprocess_data(
            parking_file_path,
            precipitation_file_path=precipitation_file_path,
            use_precipitation=False
        )

        # Create sequence Data
        window_size = 20
        X_with_precip, y_with_precip = create_sequences(df_features_with_precip.values, window_size, forecast_horizon)
        X_time_only, y_time_only = create_sequences(df_features_time_only.values, window_size, forecast_horizon)

        # Create corresponding datetime labels
        dates = df_features_with_precip.index[window_size + forecast_horizon - 1:]

        # Load Data split indices
        split_indices_time_only_path = os.path.join(parking_model_dir, f'split_indices_model_time_only.npz')
        split_indices_with_precip_path = os.path.join(parking_model_dir, f'split_indices_model_with_precipitation.npz')

        if not os.path.exists(split_indices_time_only_path) or not os.path.exists(split_indices_with_precip_path):
            print(f"Data split indices missing, skipping parking lot {parking_lot_id}")
            return None

        split_indices_time_only = np.load(split_indices_time_only_path, allow_pickle=True)
        split_indices_with_precip = np.load(split_indices_with_precip_path, allow_pickle=True)

        # Use the same test set indices
        dates_test = split_indices_time_only['dates_test']

        # Create test set mask
        test_mask = np.isin(dates, dates_test)

        X_test_with_precip = X_with_precip[test_mask]
        y_test_with_precip = y_with_precip[test_mask]
        X_test_time_only = X_time_only[test_mask]
        y_test_time_only = y_time_only[test_mask]

        # Load scalers
        scaler_X_time_only_path = os.path.join(parking_model_dir, f'scaler_X_model_time_only.pkl')
        scaler_y_time_only_path = os.path.join(parking_model_dir, f'scaler_y_model_time_only.pkl')

        scaler_X_with_precip_path = os.path.join(parking_model_dir, f'scaler_X_model_with_precipitation.pkl')
        scaler_y_with_precip_path = os.path.join(parking_model_dir, f'scaler_y_model_with_precipitation.pkl')

        with open(scaler_X_time_only_path, 'rb') as f:
            scaler_X_time_only = pickle.load(f)
        with open(scaler_y_time_only_path, 'rb') as f:
            scaler_y_time_only = pickle.load(f)

        with open(scaler_X_with_precip_path, 'rb') as f:
            scaler_X_with_precip = pickle.load(f)
        with open(scaler_y_with_precip_path, 'rb') as f:
            scaler_y_with_precip = pickle.load(f)

        # Scale test set
        X_test_scaled_time_only = scaler_X_time_only.transform(
            X_test_time_only.reshape(-1, X_test_time_only.shape[-1])
        ).reshape(X_test_time_only.shape)
        y_test_scaled_time_only = scaler_y_time_only.transform(
            y_test_time_only.reshape(-1, y_test_time_only.shape[-1])
        ).reshape(y_test_time_only.shape)

        X_test_scaled_with_precip = scaler_X_with_precip.transform(
            X_test_with_precip.reshape(-1, X_test_with_precip.shape[-1])
        ).reshape(X_test_with_precip.shape)
        y_test_scaled_with_precip = scaler_y_with_precip.transform(
            y_test_with_precip.reshape(-1, y_test_with_precip.shape[-1])
        ).reshape(y_test_with_precip.shape)

        # Load models
        model_time_only_path = os.path.join(parking_model_dir, 'model_time_only.keras')
        model_with_precip_path = os.path.join(parking_model_dir, 'model_with_precipitation.keras')

        if not os.path.exists(model_time_only_path) or not os.path.exists(model_with_precip_path):
            print(f"Model files missing, skipping parking lot {parking_lot_id}")
            return None

        model_time_only = load_model(model_time_only_path, custom_objects={'Huber': Huber()})
        model_with_precip = load_model(model_with_precip_path, custom_objects={'Huber': Huber()})

        # Predict on test set
        y_pred_scaled_time_only = model_time_only.predict(X_test_scaled_time_only)
        y_pred_scaled_with_precip = model_with_precip.predict(X_test_scaled_with_precip)

        # Inverse scale predictions and actual values
        y_pred_time_only = scaler_y_time_only.inverse_transform(y_pred_scaled_time_only)
        y_pred_with_precip = scaler_y_with_precip.inverse_transform(y_pred_scaled_with_precip)

        y_test_actual_time_only = scaler_y_time_only.inverse_transform(
            y_test_scaled_time_only.reshape(-1, y_test_scaled_time_only.shape[-1])
        )
        y_test_actual_with_precip = scaler_y_with_precip.inverse_transform(
            y_test_scaled_with_precip.reshape(-1, y_test_scaled_with_precip.shape[-1])
        )

        # Define a function to calculate evaluation metrics
        def calculate_metrics(y_true, y_pred):
            # Calculate SMAPE for each forecast step
            denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
            # Avoid division by zero
            denominator = np.where(denominator == 0, 1e-10, denominator)
            smape_per_step = np.mean(np.abs(y_true - y_pred) / denominator, axis=0) * 100  # Percentage

            # Calculate Percentage RMSE for each forecast step
            rmse_per_step = np.sqrt(np.mean((y_true - y_pred) ** 2, axis=0))
            mean_y_per_step = np.mean(y_true, axis=0)
            percentage_rmse_per_step = (rmse_per_step / mean_y_per_step) * 100

            # Calculate MAPE for each forecast step
            mape_per_step = []
            for i in range(y_true.shape[1]):
                y_true_i = y_true[:, i]
                y_pred_i = y_pred[:, i]
                non_zero_mask = y_true_i != 0
                if np.any(non_zero_mask):
                    mape = np.mean(
                        np.abs((y_true_i[non_zero_mask] - y_pred_i[non_zero_mask]) / y_true_i[non_zero_mask])
                    ) * 100
                else:
                    mape = np.nan  # Or set to 0
                mape_per_step.append(mape)
            mape_per_step = np.array(mape_per_step)

            # Calculate overall SMAPE
            denominator_overall = (np.abs(y_true) + np.abs(y_pred)) / 2
            denominator_overall = np.where(denominator_overall == 0, 1e-10, denominator_overall)
            smape_overall = np.mean(np.abs(y_true - y_pred) / denominator_overall) * 100

            # Calculate overall Percentage RMSE
            rmse_overall = np.sqrt(np.mean((y_true - y_pred) ** 2))
            mean_y_overall = np.mean(y_true)
            percentage_rmse_overall = (rmse_overall / mean_y_overall) * 100

            # Calculate overall MAPE
            y_true_flat = y_true.flatten()
            y_pred_flat = y_pred.flatten()
            non_zero_mask = y_true_flat != 0
            if np.any(non_zero_mask):
                mape_overall = np.mean(
                    np.abs((y_true_flat[non_zero_mask] - y_pred_flat[non_zero_mask]) / y_true_flat[non_zero_mask])
                ) * 100
            else:
                mape_overall = np.nan  # Or set to 0

            return smape_per_step, percentage_rmse_per_step, mape_per_step, smape_overall, percentage_rmse_overall, mape_overall

        # Calculate metrics (without precipitation feature)
        smape_per_step_time_only, perc_rmse_per_step_time_only, mape_per_step_time_only, smape_overall_time_only, perc_rmse_overall_time_only, mape_overall_time_only = calculate_metrics(
            y_test_actual_time_only, y_pred_time_only)

        # Calculate metrics (with precipitation feature)
        smape_per_step_with_precip, perc_rmse_per_step_with_precip, mape_per_step_with_precip, smape_overall_with_precip, perc_rmse_overall_with_precip, mape_overall_with_precip = calculate_metrics(
            y_test_actual_with_precip, y_pred_with_precip)

        # Store results
        results['parking_lot_id'] = parking_lot_id
        results['smape_overall_time_only'] = smape_overall_time_only
        results['smape_overall_with_precip'] = smape_overall_with_precip
        results['perc_rmse_overall_time_only'] = perc_rmse_overall_time_only
        results['perc_rmse_overall_with_precip'] = perc_rmse_overall_with_precip
        results['mape_overall_time_only'] = mape_overall_time_only
        results['mape_overall_with_precip'] = mape_overall_with_precip

        results['smape_per_step_time_only'] = smape_per_step_time_only
        results['smape_per_step_with_precip'] = smape_per_step_with_precip
        results['perc_rmse_per_step_time_only'] = perc_rmse_per_step_time_only
        results['perc_rmse_per_step_with_precip'] = perc_rmse_per_step_with_precip
        results['mape_per_step_time_only'] = mape_per_step_time_only
        results['mape_per_step_with_precip'] = mape_per_step_with_precip

        # Calculate improvements
        results['smape_improvement_overall'] = smape_overall_time_only - smape_overall_with_precip
        results['perc_rmse_improvement_overall'] = perc_rmse_overall_time_only - perc_rmse_overall_with_precip
        results['mape_improvement_overall'] = mape_overall_time_only - mape_overall_with_precip

        results['smape_improvement_per_step'] = smape_per_step_time_only - smape_per_step_with_precip
        results['perc_rmse_improvement_per_step'] = perc_rmse_per_step_time_only - perc_rmse_per_step_with_precip
        results['mape_improvement_per_step'] = mape_per_step_time_only - mape_per_step_with_precip

        # Calculate percentage improvements
        results['smape_percentage_improvement_overall'] = (results['smape_improvement_overall'] / smape_overall_time_only) * 100
        results['perc_rmse_percentage_improvement_overall'] = (results['perc_rmse_improvement_overall'] / perc_rmse_overall_time_only) * 100
        results['mape_percentage_improvement_overall'] = (results['mape_improvement_overall'] / mape_overall_time_only) * 100

        results['smape_percentage_improvement_per_step'] = (results['smape_improvement_per_step'] / smape_per_step_time_only) * 100
        results['perc_rmse_percentage_improvement_per_step'] = (results['perc_rmse_improvement_per_step'] / perc_rmse_per_step_time_only) * 100
        results['mape_percentage_improvement_per_step'] = (results['mape_improvement_per_step'] / mape_per_step_time_only) * 100

        return results

    except Exception as e:
        print(f"An error occurred while evaluating parking lot {parking_lot_id}: {e}")
        return None


def main():
    """
    Main function to evaluate models for selected parking lots.
    """
    # Set random seed for reproducibility
    random.seed(42)

    # Parking lot Data directory
    parking_lot_dir = 'Data/ParkingAvailability'

    # Base directory where models are saved
    models_base_dir = 'trained_models'

    # Set forecast horizon (in the application, we choose 8-step)
    forecast_horizon = 8

    # Get all trained parking lot IDs
    trained_parking_lots = [d for d in os.listdir(models_base_dir) if os.path.isdir(os.path.join(models_base_dir, d))]
    trained_parking_lots.sort()
    print(f"Found {len(trained_parking_lots)} trained parking lots.")

    # Select the number of parking lots to evaluate
    n = len(trained_parking_lots)

    # Randomly select n parking lots for evaluation
    selected_parking_lots = random.sample(trained_parking_lots, n)
    print(f"Randomly selected {n} parking lots for evaluation: {selected_parking_lots}")

    # Precipitation file path
    precipitation_file_path = 'Data/Precipitation/data.csv'

    # Check if precipitation file exists
    if not os.path.exists(precipitation_file_path):
        print(f"File {precipitation_file_path} does not exist. Please ensure the file is in the directory.")
        return

    # List to store evaluation results for all parking lots
    all_results = []

    # Evaluate each selected parking lot
    for parking_lot_id in selected_parking_lots:
        result = evaluate_parking_lot(
            parking_lot_id,
            models_base_dir,
            parking_lot_dir,
            precipitation_file_path,
            forecast_horizon=forecast_horizon
        )
        if result:
            all_results.append(result)

    # If there are evaluation results, aggregate and plot
    if all_results:
        # Convert results to DataFrame
        df_results = pd.DataFrame(all_results)

        # Calculate average metrics (overall and per forecast step)
        avg_smape_overall_time_only = df_results['smape_overall_time_only'].mean()
        avg_smape_overall_with_precip = df_results['smape_overall_with_precip'].mean()
        avg_perc_rmse_overall_time_only = df_results['perc_rmse_overall_time_only'].mean()
        avg_perc_rmse_overall_with_precip = df_results['perc_rmse_overall_with_precip'].mean()
        avg_mape_overall_time_only = df_results['mape_overall_time_only'].mean()
        avg_mape_overall_with_precip = df_results['mape_overall_with_precip'].mean()

        avg_smape_per_step_time_only = np.mean(np.vstack(df_results['smape_per_step_time_only']), axis=0)
        avg_smape_per_step_with_precip = np.mean(np.vstack(df_results['smape_per_step_with_precip']), axis=0)
        avg_perc_rmse_per_step_time_only = np.mean(np.vstack(df_results['perc_rmse_per_step_time_only']), axis=0)
        avg_perc_rmse_per_step_with_precip = np.mean(np.vstack(df_results['perc_rmse_per_step_with_precip']), axis=0)
        avg_mape_per_step_time_only = np.nanmean(np.vstack(df_results['mape_per_step_time_only']), axis=0)
        avg_mape_per_step_with_precip = np.nanmean(np.vstack(df_results['mape_per_step_with_precip']), axis=0)

        # Calculate average improvements
        avg_smape_improvement_overall = avg_smape_overall_time_only - avg_smape_overall_with_precip
        avg_perc_rmse_improvement_overall = avg_perc_rmse_overall_time_only - avg_perc_rmse_overall_with_precip
        avg_mape_improvement_overall = avg_mape_overall_time_only - avg_mape_overall_with_precip

        avg_smape_improvement_per_step = avg_smape_per_step_time_only - avg_smape_per_step_with_precip
        avg_perc_rmse_improvement_per_step = avg_perc_rmse_per_step_time_only - avg_perc_rmse_per_step_with_precip
        avg_mape_improvement_per_step = avg_mape_per_step_time_only - avg_mape_per_step_with_precip

        # Print overall metrics
        print("\nAverage Metrics (Without Precipitation Feature):")
        print(f"Average Overall SMAPE: {avg_smape_overall_time_only:.2f}%")
        print(f"Average Overall Percentage RMSE: {avg_perc_rmse_overall_time_only:.2f}%")
        print(f"Average Overall MAPE: {avg_mape_overall_time_only:.2f}%")

        print("\nAverage Metrics (With Precipitation Feature):")
        print(f"Average Overall SMAPE: {avg_smape_overall_with_precip:.2f}%")
        print(f"Average Overall Percentage RMSE: {avg_perc_rmse_overall_with_precip:.2f}%")
        print(f"Average Overall MAPE: {avg_mape_overall_with_precip:.2f}%")

        # Print average improvements
        print("\nAverage Performance Improvement:")
        print(f"Average SMAPE Improvement: {avg_smape_improvement_overall:.2f}%")
        print(f"Average Percentage RMSE Improvement: {avg_perc_rmse_improvement_overall:.2f}%")
        print(f"Average MAPE Improvement: {avg_mape_improvement_overall:.2f}%")

        # Perform statistical significance tests (paired t-test)
        from scipy.stats import ttest_rel

        # Paired t-test for overall SMAPE
        t_stat_smape, p_value_smape = ttest_rel(
            df_results['smape_overall_time_only'], df_results['smape_overall_with_precip']
        )
        print(f"\nSMAPE Overall Paired t-test: t-statistic = {t_stat_smape:.4f}, p-value = {p_value_smape:.4f}")

        # Paired t-test for overall Percentage RMSE
        t_stat_perc_rmse, p_value_perc_rmse = ttest_rel(
            df_results['perc_rmse_overall_time_only'], df_results['perc_rmse_overall_with_precip']
        )
        print(f"Percentage RMSE Overall Paired t-test: t-statistic = {t_stat_perc_rmse:.4f}, p-value = {p_value_perc_rmse:.4f}")

        # Paired t-test for overall MAPE
        t_stat_mape, p_value_mape = ttest_rel(
            df_results['mape_overall_time_only'], df_results['mape_overall_with_precip'], nan_policy='omit'
        )
        print(f"MAPE Overall Paired t-test: t-statistic = {t_stat_mape:.4f}, p-value = {p_value_mape:.4f}")

        # Plot average metrics bar charts
        steps = np.arange(1, forecast_horizon + 1)
        bar_width = 0.35
        index = np.arange(len(steps))

        # Plot average SMAPE bar chart
        plt.figure(figsize=(12, 6))
        plt.bar(index, avg_smape_per_step_time_only, bar_width, label='Without Precipitation')
        plt.bar(index + bar_width, avg_smape_per_step_with_precip, bar_width, label='With Precipitation')
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average SMAPE (%)')
        plt.title('Average SMAPE per Forecast Step')
        plt.xticks(index + bar_width / 2, steps)
        plt.legend()
        plt.show()

        # Plot average Percentage RMSE bar chart
        plt.figure(figsize=(12, 6))
        plt.bar(index, avg_perc_rmse_per_step_time_only, bar_width, label='Without Precipitation')
        plt.bar(index + bar_width, avg_perc_rmse_per_step_with_precip, bar_width, label='With Precipitation')
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average Percentage RMSE (%)')
        plt.title('Average Percentage RMSE per Forecast Step')
        plt.xticks(index + bar_width / 2, steps)
        plt.legend()
        plt.show()

        # Plot average MAPE bar chart
        plt.figure(figsize=(12, 6))
        plt.bar(index, avg_mape_per_step_time_only, bar_width, label='Without Precipitation')
        plt.bar(index + bar_width, avg_mape_per_step_with_precip, bar_width, label='With Precipitation')
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average MAPE (%)')
        plt.title('Average MAPE per Forecast Step')
        plt.xticks(index + bar_width / 2, steps)
        plt.legend()
        plt.show()

        # Plot average SMAPE improvement per step
        plt.figure(figsize=(12, 6))
        plt.bar(steps, avg_smape_improvement_per_step)
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average SMAPE Improvement (%)')
        plt.title('Average SMAPE Improvement per Forecast Step')
        plt.grid(True)
        plt.show()

        # Plot average Percentage RMSE improvement per step
        plt.figure(figsize=(12, 6))
        plt.bar(steps, avg_perc_rmse_improvement_per_step)
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average Percentage RMSE Improvement (%)')
        plt.title('Average Percentage RMSE Improvement per Forecast Step')
        plt.grid(True)
        plt.show()

        # Plot average MAPE improvement per step
        plt.figure(figsize=(12, 6))
        plt.bar(steps, avg_mape_improvement_per_step)
        plt.xlabel('Forecast Horizon')
        plt.ylabel('Average MAPE Improvement (%)')
        plt.title('Average MAPE Improvement per Forecast Step')
        plt.grid(True)
        plt.show()

        # Print average metrics per forecast step (without precipitation)
        print("\nAverage Metrics per Forecast Step (Without Precipitation Feature):")
        for i in range(len(steps)):
            print(f"Step {i + 1}: "
                  f"Average SMAPE = {avg_smape_per_step_time_only[i]:.2f}%, "
                  f"Average Percentage RMSE = {avg_perc_rmse_per_step_time_only[i]:.2f}%, "
                  f"Average MAPE = {avg_mape_per_step_time_only[i]:.2f}%")

        # Print average metrics per forecast step (with precipitation)
        print("\nAverage Metrics per Forecast Step (With Precipitation Feature):")
        for i in range(len(steps)):
            print(f"Step {i + 1}: "
                  f"Average SMAPE = {avg_smape_per_step_with_precip[i]:.2f}%, "
                  f"Average Percentage RMSE = {avg_perc_rmse_per_step_with_precip[i]:.2f}%, "
                  f"Average MAPE = {avg_mape_per_step_with_precip[i]:.2f}%")

        # Output average performance improvement per forecast step
        print("\nAverage Performance Improvement per Forecast Step:")
        for i in range(len(steps)):
            print(f"Step {i + 1}: "
                  f"Average SMAPE Improvement = {avg_smape_improvement_per_step[i]:.2f}%, "
                  f"Average Percentage RMSE Improvement = {avg_perc_rmse_improvement_per_step[i]:.2f}%, "
                  f"Average MAPE Improvement = {avg_mape_improvement_per_step[i]:.2f}%")

    else:
        print("No evaluation results were obtained.")


if __name__ == "__main__":
    main()