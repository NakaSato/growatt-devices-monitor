import tensorflow as tf
from tensorflow import keras
from keras.models import Sequential, load_model
from keras.layers import LSTM, Dense, Dropout, Bidirectional, BatchNormalization, Conv1D
from keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint, TensorBoard
from keras.optimizers import Adam
import numpy as np
import os
from datetime import datetime

def create_lstm_model(input_shape, output_size=1, lstm_units=64, architecture='bidirectional', 
                      dropout_rate=0.2, learning_rate=0.001, use_batch_norm=True,
                      use_conv_layer=False):
    """
    Create an enhanced LSTM model for time series forecasting.
    
    Args:
        input_shape: Shape of input data (sequence_length, n_features)
        output_size: Number of output features
        lstm_units: Number of LSTM units
        architecture: Type of LSTM architecture ('bidirectional', 'stacked', 'simple')
        dropout_rate: Dropout rate for regularization
        learning_rate: Learning rate for the optimizer
        use_batch_norm: Whether to use batch normalization
        use_conv_layer: Whether to add a convolutional layer for feature extraction
        
    Returns:
        Compiled LSTM model
    """
    model = Sequential()
    
    # Optional Conv1D layer for feature extraction
    if use_conv_layer:
        model.add(Conv1D(filters=32, kernel_size=3, padding='same', 
                         activation='relu', input_shape=input_shape))
        if use_batch_norm:
            model.add(BatchNormalization())
    
    # LSTM layers based on architecture choice
    if architecture == 'bidirectional':
        # Bidirectional LSTM architecture
        model.add(Bidirectional(LSTM(lstm_units, return_sequences=True), 
                              input_shape=None if use_conv_layer else input_shape))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        
        model.add(Bidirectional(LSTM(lstm_units//2)))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        
    elif architecture == 'stacked':
        # Stacked LSTM architecture
        model.add(LSTM(lstm_units, return_sequences=True, 
                     input_shape=None if use_conv_layer else input_shape))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        
        model.add(LSTM(lstm_units, return_sequences=True))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        
        model.add(LSTM(lstm_units//2))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        
    else:
        # Simple LSTM architecture
        model.add(LSTM(lstm_units, input_shape=None if use_conv_layer else input_shape))
        if use_batch_norm:
            model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
    
    # Dense hidden layer for additional pattern recognition
    model.add(Dense(lstm_units//2, activation='relu'))
    if use_batch_norm:
        model.add(BatchNormalization())
    model.add(Dropout(dropout_rate/2))
    
    # Output layer
    model.add(Dense(output_size))
    
    # Compile the model with customizable learning rate
    optimizer = Adam(learning_rate=learning_rate)
    model.compile(optimizer=optimizer, loss='mse', metrics=['mae', 'mape'])
    
    return model

def train_lstm_model(model, X_train, y_train, X_val, y_val, epochs=100, batch_size=32,
                    patience=10, min_delta=0.001, save_dir=None, model_name=None):
    """
    Train the LSTM model with advanced callbacks for better performance.
    
    Args:
        model: LSTM model to train
        X_train, y_train: Training data
        X_val, y_val: Validation data
        epochs: Maximum number of epochs
        batch_size: Batch size for training
        patience: Patience for early stopping
        min_delta: Minimum change to qualify as improvement
        save_dir: Directory to save model checkpoints
        model_name: Name for the saved model
        
    Returns:
        Trained model and training history
    """
    callbacks = []
    
    # Early stopping to prevent overfitting
    early_stopping = EarlyStopping(
        monitor='val_loss',
        patience=patience,
        min_delta=min_delta,
        restore_best_weights=True,
        verbose=1
    )
    callbacks.append(early_stopping)
    
    # Learning rate reduction when plateauing
    lr_reduction = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=patience//2,
        min_delta=min_delta,
        min_lr=1e-6,
        verbose=1
    )
    callbacks.append(lr_reduction)
    
    # Model checkpointing
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)
        
        if model_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = f"lstm_model_{timestamp}"
        
        checkpoint_path = os.path.join(save_dir, f"{model_name}.h5")
        checkpoint = ModelCheckpoint(
            filepath=checkpoint_path,
            save_best_only=True,
            monitor='val_loss',
            mode='min',
            verbose=1
        )
        callbacks.append(checkpoint)
        
        # TensorBoard logging
        log_dir = os.path.join(save_dir, 'logs', model_name)
        tensorboard = TensorBoard(
            log_dir=log_dir,
            histogram_freq=1,
            write_graph=True
        )
        callbacks.append(tensorboard)
    
    # Train the model
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_val, y_val),
        callbacks=callbacks,
        verbose=1
    )
    
    return model, history

def save_lstm_model(model, model_path):
    """
    Save the LSTM model to disk.
    
    Args:
        model: Trained LSTM model
        model_path: Path to save the model
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    model.save(model_path)
    print(f"Model saved to {model_path}")

def load_lstm_model(model_path):
    """
    Load an LSTM model from disk.
    
    Args:
        model_path: Path to the saved model
        
    Returns:
        Loaded LSTM model
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"No model found at {model_path}")
    
    return load_model(model_path)

def predict_sequence(model, input_sequence, steps_ahead=24):
    """
    Generate a sequence of predictions stepping forward in time.
    
    Args:
        model: Trained LSTM model
        input_sequence: Initial input sequence
        steps_ahead: Number of steps to predict ahead
        
    Returns:
        Array of predictions
    """
    predictions = []
    current_sequence = input_sequence.copy()
    
    for _ in range(steps_ahead):
        # Predict the next step
        next_pred = model.predict(current_sequence, verbose=0)
        predictions.append(next_pred[0])
        
        # Update the sequence for the next prediction
        # Remove the first time step and add the new prediction
        new_sequence = np.append(current_sequence[:, 1:, :], 
                                [[next_pred]], 
                                axis=1)
        current_sequence = new_sequence
    
    return np.array(predictions)
