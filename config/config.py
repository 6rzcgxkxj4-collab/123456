"""
Configuration settings for the Face Recognition Attendance System.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration class."""
    
    # TensorFlow Serving configuration
    TF_SERVING_HOST: str = os.getenv("TF_SERVING_HOST", "localhost")
    TF_SERVING_PORT: int = int(os.getenv("TF_SERVING_PORT", "8501"))
    TF_SERVING_MODEL_NAME: str = os.getenv("TF_SERVING_MODEL_NAME", "face_recognition")
    
    # Database configuration
    DATABASE_URI: str = os.getenv("DATABASE_URI", "sqlite:///attendance.db")
    
    # Face recognition parameters
    FACE_DETECTION_CONFIDENCE: float = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
    FACE_RECOGNITION_THRESHOLD: float = float(os.getenv("FACE_RECOGNITION_THRESHOLD", "0.6"))
    FACE_ENCODING_SIZE: int = 128  # FaceNet embedding size
    
    # Image processing
    IMAGE_SIZE: tuple = (160, 160)  # Input size for FaceNet
    
    # Server configuration
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "5000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # File storage
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    FACE_IMAGES_FOLDER: str = os.getenv("FACE_IMAGES_FOLDER", "face_images")
    
    # Secret key for session
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")


# Create a default config instance
config = Config()
