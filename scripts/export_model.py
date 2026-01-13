"""
TensorFlow Model Export Script for Face Recognition.

This script demonstrates how to create and export a face recognition model
for deployment with TensorFlow Serving.
"""
import os
import sys
import argparse
import numpy as np

def create_face_embedding_model(input_shape=(160, 160, 3), embedding_size=128):
    """
    Create a simple face embedding model for demonstration.
    
    In production, you would use a pre-trained model like:
    - FaceNet
    - ArcFace
    - VGGFace2
    
    Args:
        input_shape: Input image shape (height, width, channels)
        embedding_size: Size of the output embedding vector
        
    Returns:
        TensorFlow Keras model
    """
    try:
        import tensorflow as tf
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError:
        print("Error: TensorFlow is not installed.")
        print("Install it with: pip install tensorflow")
        sys.exit(1)
    
    # Simple CNN model for face embedding
    # In production, use a proper face recognition architecture
    model = keras.Sequential([
        # Input layer
        layers.Input(shape=input_shape, name='input_image'),
        
        # Convolutional blocks
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(256, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(512, (3, 3), activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.GlobalAveragePooling2D(),
        
        # Dense layers
        layers.Dense(256, activation='relu'),
        layers.Dropout(0.5),
        
        # Embedding layer
        layers.Dense(embedding_size, name='embedding'),
        
        # L2 normalization for face embeddings
        layers.Lambda(lambda x: tf.math.l2_normalize(x, axis=1), name='l2_normalize')
    ])
    
    return model


def export_model_for_serving(model, export_path, version=1):
    """
    Export model for TensorFlow Serving.
    
    Args:
        model: TensorFlow Keras model
        export_path: Base path for export
        version: Model version number
    """
    try:
        import tensorflow as tf
    except ImportError:
        print("Error: TensorFlow is not installed.")
        sys.exit(1)
    
    version_path = os.path.join(export_path, str(version))
    
    # Create export directory
    os.makedirs(version_path, exist_ok=True)
    
    # Save model in SavedModel format
    tf.saved_model.save(model, version_path)
    
    print(f"Model exported to: {version_path}")
    print("\nTo serve this model with TensorFlow Serving, run:")
    print(f"  docker run -p 8501:8501 -p 8500:8500 \\")
    print(f"    --mount type=bind,source={os.path.abspath(export_path)},target=/models/face_recognition \\")
    print(f"    -e MODEL_NAME=face_recognition \\")
    print(f"    tensorflow/serving")


def create_serving_config(model_base_path, model_name='face_recognition'):
    """
    Create a TensorFlow Serving model configuration file.
    
    Args:
        model_base_path: Base path where model versions are stored
        model_name: Name of the model
        
    Returns:
        Configuration string
    """
    config = f"""
model_config_list {{
  config {{
    name: "{model_name}"
    base_path: "{model_base_path}"
    model_platform: "tensorflow"
    model_version_policy {{
      latest {{
        num_versions: 2
      }}
    }}
  }}
}}
"""
    return config


def main():
    """Main entry point for model export."""
    parser = argparse.ArgumentParser(
        description='Export face recognition model for TensorFlow Serving'
    )
    parser.add_argument(
        '--output', '-o',
        default='./models/face_recognition',
        help='Output directory for exported model'
    )
    parser.add_argument(
        '--version', '-v',
        type=int,
        default=1,
        help='Model version number'
    )
    parser.add_argument(
        '--input-size',
        type=int,
        default=160,
        help='Input image size (height=width)'
    )
    parser.add_argument(
        '--embedding-size',
        type=int,
        default=128,
        help='Face embedding vector size'
    )
    
    args = parser.parse_args()
    
    print("Creating face embedding model...")
    model = create_face_embedding_model(
        input_shape=(args.input_size, args.input_size, 3),
        embedding_size=args.embedding_size
    )
    
    print("\nModel summary:")
    model.summary()
    
    print("\nExporting model for TensorFlow Serving...")
    export_model_for_serving(model, args.output, args.version)
    
    # Create serving config
    config = create_serving_config(
        '/models/face_recognition',  # Container path
        'face_recognition'
    )
    
    config_path = os.path.join(args.output, 'models.config')
    with open(config_path, 'w') as f:
        f.write(config)
    
    print(f"\nServing config saved to: {config_path}")
    print("\nDone!")


if __name__ == '__main__':
    main()
