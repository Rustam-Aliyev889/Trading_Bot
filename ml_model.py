import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import xgboost as xgb
import optuna
from optuna.samplers import TPESampler
import joblib

# List of symbols
symbols = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'META', 'TSLA', 'NFLX', 'NVDA', 'V', 'PYPL']

# Load and concatenate data for all symbols
data_list = []
for symbol in symbols:
    file_path = f'tests/historic_data/{symbol}_historical_data.csv'
    symbol_data = pd.read_csv(file_path)
    symbol_data['symbol'] = symbol  # Add a column for the symbol
    data_list.append(symbol_data)

# Concatenate all data into a single DataFrame
data = pd.concat(data_list)

# Ensure the 'timestamp' or 'time' column exists and is in datetime format
if 'timestamp' in data.columns:
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data = data.sort_values(by=['symbol', 'timestamp'])
elif 'time' in data.columns:
    data['time'] = pd.to_datetime(data['time'])
    data = data.sort_values(by=['symbol', 'time'])
else:
    raise KeyError("The 'timestamp' or 'time' column is missing from the data.")

# Initialize an empty DataFrame to hold features
features_list = []

# Compute features for each symbol separately
for symbol in symbols:
    symbol_data = data[data['symbol'] == symbol].copy()
    
    # Feature Engineering
    symbol_data['SMA_10'] = symbol_data['close'].rolling(window=10).mean()
    symbol_data['EMA_12'] = symbol_data['close'].ewm(span=12, adjust=False).mean()
    symbol_data['EMA_26'] = symbol_data['close'].ewm(span=26, adjust=False).mean()
    symbol_data['Bollinger_High'] = symbol_data['close'].rolling(window=20).mean() + (symbol_data['close'].rolling(window=20).std() * 2)
    symbol_data['Bollinger_Low'] = symbol_data['close'].rolling(window=20).mean() - (symbol_data['close'].rolling(window=20).std() * 2)

    # Calculate ATR
    symbol_data['prev_close'] = symbol_data['close'].shift(1)
    symbol_data['TR1'] = symbol_data['high'] - symbol_data['low']
    symbol_data['TR2'] = abs(symbol_data['high'] - symbol_data['prev_close'])
    symbol_data['TR3'] = abs(symbol_data['low'] - symbol_data['prev_close'])
    symbol_data['TR'] = symbol_data[['TR1', 'TR2', 'TR3']].max(axis=1)
    symbol_data['ATR'] = symbol_data['TR'].rolling(window=14).mean()

    # Calculate OBV and Stochastic Oscillator
    symbol_data['OBV'] = (np.sign(symbol_data['close'].diff()) * symbol_data['volume']).fillna(0).cumsum()
    symbol_data['Stochastic_Oscillator'] = ((symbol_data['close'] - symbol_data['low'].rolling(window=14).min()) / (symbol_data['high'].rolling(window=14).max() - symbol_data['low'].rolling(window=14).min())) * 100

    # Existing Features
    delta = symbol_data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    symbol_data['RSI_14'] = 100 - (100 / (1 + rs))
    exp1 = symbol_data['close'].ewm(span=12, adjust=False).mean()
    exp2 = symbol_data['close'].ewm(span=26, adjust=False).mean()
    symbol_data['MACD'] = exp1 - exp2
    symbol_data['MACD_signal'] = symbol_data['MACD'].ewm(span=9, adjust=False).mean()

    # Additional features
    symbol_data['lagged_return'] = symbol_data['close'].pct_change().shift(1)
    symbol_data['volatility'] = symbol_data['close'].pct_change().rolling(window=10).std()

    # Drop NaNs
    symbol_data = symbol_data.dropna()

    # Define target
    symbol_data['target'] = (symbol_data['close'].shift(-1) > symbol_data['close']).astype(int)
    symbol_data = symbol_data.dropna(subset=['target'])

    # Append to features list
    features_list.append(symbol_data)

# Concatenate all features into a single DataFrame
features = pd.concat(features_list)

# Define features and target
X = features[['SMA_10', 'EMA_12', 'EMA_26', 'Bollinger_High', 'Bollinger_Low', 'RSI_14', 'MACD', 'MACD_signal', 'lagged_return', 'volatility', 'ATR', 'OBV', 'Stochastic_Oscillator']]
y = features['target']

# Ensure X and y have consistent lengths
assert len(X) == len(y), "X and y lengths are inconsistent"

# Scale features
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Apply SMOTE to balance the classes
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

# Define the objective function for Optuna
def objective(trial):
    param = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 20),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.5, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 1.0),
        'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0.0, 0.5)
    }
    model = xgb.XGBClassifier(objective='binary:logistic', eval_metric='logloss', random_state=42, **param)
    
    # Using cross-validation
    cv_scores = cross_val_score(model, X_train_resampled, y_train_resampled, cv=5, scoring='f1', n_jobs=-1)
    
    # Return the mean of the cross-validation scores
    return cv_scores.mean()

# Create the study for Optuna
study = optuna.create_study(direction='maximize', sampler=TPESampler())
study.optimize(objective, n_trials=100)

# Print the best parameters found by Optuna
print(f"Best Parameters: {study.best_params}")

# Train the best model with the entire training set
best_model_optuna = xgb.XGBClassifier(objective='binary:logistic', eval_metric='logloss', random_state=42, **study.best_params)
best_model_optuna.fit(X_train_resampled, y_train_resampled)

# Validate the model on the test set
y_pred_optuna = best_model_optuna.predict(X_test)
accuracy_optuna = accuracy_score(y_test, y_pred_optuna)
precision_optuna = precision_score(y_test, y_pred_optuna)
recall_optuna = recall_score(y_test, y_pred_optuna)
f1_optuna = f1_score(y_test, y_pred_optuna)

# Final metrics
print(f"Model Accuracy (Optuna): {accuracy_optuna:.2f}")
print(f"Model Precision (Optuna): {precision_optuna:.2f}")
print(f"Model Recall (Optuna): {recall_optuna:.2f}")
print(f"Model F1 Score (Optuna): {f1_optuna:.2f}")

# Save the model
joblib.dump(best_model_optuna, 'xgboost_model_optuna.pkl')