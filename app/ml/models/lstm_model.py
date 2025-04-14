import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
import numpy as np

def create_lstm_model(input_shape, output_size=1, lstm_units=64):
    """
    Create an LSTM model for time series forecasting.
    
    Args:
        input_shape: Shape of input data (sequence_length, n_features)
        output_size: Number of output features
        lstm_units: Number of LSTM units
        
    Returns:
        Compiled LSTM model
    """
    model = Sequential()
    
    # Bidirectional LSTM layers
    model.add(Bidirectional(LSTM(lstm_units, return_sequences=True), 
                           input_shape=input_shape))
    model.add(Dropout(0.2))
    
    model.add(Bidirectional(LSTM(lstm_units)))
    model.add(Dropout(0.2))
    
    # Output layer
    model.add(Dense(output_size))
    
    # Compile the model
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    
    return model

def train_lstm_model(model, X_train, y_train, X_val, y_val, epochs=100, batch_size=32):
    """
    Train the LSTM model with early stopping and learning rate reduction.
    
    Args:
        model: LSTM model to train
        X_train, y_train: Training data
        X_val, y_val: Validation data
        epochs: Maximum number of epochs
        batch_size: Batch size for training
        
    Returns:
        Trained model and training history
    """
    # Callbacks for better training
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=10,
        restore_best_weights=True
    )
    
    lr_reduction = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=5,
        min_lr=1e-6
    )
    
    # Train the model
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_val, y_val),
        callbacks=[early_stopping, lr_reduction],
        verbose=1
    )
    
    return model, history
