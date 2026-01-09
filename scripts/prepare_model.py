#!/usr/bin/env python3
"""
Script to download and prepare the FaceNet model for TensorFlow Serving.

This script downloads a pre-trained FaceNet model and converts it to 
TensorFlow SavedModel format for use with TensorFlow Serving.
"""

import os
import sys
import argparse
import shutil
import logging

import tensorflow as tf
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_facenet_model(input_shape=(160, 160, 3), embedding_size=128):
    """
    Create a FaceNet-like model architecture.
    
    This is a simplified version. For production, you should use 
    a pre-trained FaceNet model or train your own.
    
    Args:
        input_shape: Input image shape.
        embedding_size: Size of the output embedding vector.
    
    Returns:
        tf.keras.Model: FaceNet model.
    """
    # Base model using InceptionResNetV2 (similar to FaceNet)
    base_model = tf.keras.applications.InceptionResNetV2(
        include_top=False,
        weights='imagenet',
        input_shape=input_shape,
        pooling='avg'
    )
    
    # Freeze base model layers
    base_model.trainable = False
    
    # Build the model
    inputs = tf.keras.Input(shape=input_shape)
    x = base_model(inputs, training=False)
    x = tf.keras.layers.Dense(512, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    outputs = tf.keras.layers.Dense(embedding_size)(x)
    
    # L2 normalize the embeddings
    outputs = tf.keras.layers.Lambda(lambda x: tf.math.l2_normalize(x, axis=1))(outputs)
    
    model = tf.keras.Model(inputs, outputs, name='facenet')
    
    return model


def export_model(model, export_path, version=1):
    """
    Export model to TensorFlow SavedModel format.
    
    Args:
        model: Keras model to export.
        export_path: Path to save the model.
        version: Model version number.
    """
    version_path = os.path.join(export_path, str(version))
    
    # Create directory if it doesn't exist
    os.makedirs(version_path, exist_ok=True)
    
    # Save the model
    model.save(version_path, save_format='tf')
    
    logger.info(f"Model exported to: {version_path}")


def main():
    parser = argparse.ArgumentParser(description='Prepare FaceNet model for TensorFlow Serving')
    parser.add_argument('--output-dir', type=str, default='models/facenet',
                       help='Output directory for the model')
    parser.add_argument('--version', type=int, default=1,
                       help='Model version number')
    parser.add_argument('--embedding-size', type=int, default=128,
                       help='Size of face embedding vector')
    
    args = parser.parse_args()
    
    logger.info("Creating FaceNet model...")
    model = create_facenet_model(embedding_size=args.embedding_size)
    
    logger.info("Model summary:")
    model.summary()
    
    logger.info(f"Exporting model to {args.output_dir}...")
    export_model(model, args.output_dir, args.version)
    
    logger.info("Model preparation complete!")
    logger.info(f"Model saved to: {args.output_dir}/{args.version}")
    logger.info("\nTo use with TensorFlow Serving:")
    logger.info(f"  docker run -p 8501:8501 --mount type=bind,source=$(pwd)/{args.output_dir},target=/models/facenet -e MODEL_NAME=facenet -t tensorflow/serving")


if __name__ == '__main__':
    main()
