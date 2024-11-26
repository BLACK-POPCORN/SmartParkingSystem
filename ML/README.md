# Machine Learning Models for Smart Parking System

This directory contains machine learning scripts for predicting parking availability in Singapore’s public parking lots. The models utilize historical parking availability data and, optionally, precipitation data to forecast future parking availability.

**Important:** The code assumes that the `Data` directory is located inside the `ML` directory. Please ensure you move or copy the `Data` directory into the `ML` directory before running any scripts.

## Prerequisites

- Python 3.7 or higher
- Required Python packages (listed in `requirements.txt`)

## Scripts and Usage

### 1. Training Models

#### `train_parking_lot_models.py`

This script trains two LSTM models for selected parking lots:

- **Model 1:** Uses only time-related features.
- **Model 2:** Uses time-related features and precipitation data.

**Usage:**

```bash
python train_parking_lot_models.py
```

**Features:**

- Randomly selects a subset of parking lots for training.
- Saves trained models and scalers in the `trained_models/` directory.

#### `train_and_export_parking_lot_models.py`

This script trains LSTM models for all parking lots and exports them for deployment.

**Usage:**

```bash
python train_and_export_parking_lot_models.py
```

**Features:**

- Iterates over all parking lot CSV files in `Data/ParkingAvailability/`.
- Trains a multi-step prediction LSTM model for each parking lot.
- Exports the trained models for deployment and compresses them into `.tar.gz` files in the `deploy_lstm/` directory.

#### `train_single_model.py`

This script trains LSTM models for a single parking lot. Ensure that train_single_model.py, the parking lot CSV file (e.g., W187.csv), and the weather data CSV file (e.g., data.csv) are in the same directory. Modify the script to specify the parking lot you want to train the model for by changing the parking_file_path variable.

**Usage:**

```bash
python train_single_model.py
```

**Features:**

Trains two models for the specified parking lot:

- **Model 1:** Uses only time-related features.
- **Model 2:** Uses time-related features and precipitation data.

Saves the trained models in the current directory.

### 2. Evaluating Models

#### `evaluate_parking_lot_models.py`

This script evaluates the performance of the trained models, comparing models with and without precipitation data.

**Usage:**

```bash
python evaluate_parking_lot_models.py
```

**Features:**

- Evaluates models for all trained parking lots.
- Calculates evaluation metrics: SMAPE, MAPE, and Percentage RMSE.
- Performs statistical significance tests (paired t-tests).
- Generates plots to visualize the results.

#### `evaluate_single_model.py`

This script evaluates the performance of models for a single parking lot. Ensure that evaluate_single_model.py, the parking lot CSV file (e.g., W187.csv), and the weather data CSV file (e.g., data.csv) are in the same directory. Modify the script to specify the parking lot you want to evaluate the model for by changing the parking_file_path variable.

**Usage:**

```bash
python evaluate_single_model.py
```

**Features:**

- Evaluates the performance of the two models trained for the specified parking lot.
- Calculates evaluation metrics: RMSE, MAE, MSE, SMAPE, and Percentage RMSE.
- Performs statistical significance tests (paired t-tests).
- Generates plots to visualize the results and compare the models


### 3. Utility Scripts

#### `find_missing_models.py`

This script identifies parking lots for which models were not successfully generated.

**Usage:**

```bash
python find_missing_models.py`
```

**Features:**

- Compares parking lot IDs from the data directory and the deployment directory.
- Lists parking lots missing models.

## Requirements

The required Python packages are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```
