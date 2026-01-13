"""
Configuration settings for the Facial Recognition Check-in System.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'sqlite:///data/checkin.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # TensorFlow Serving settings
    TF_SERVING_HOST = os.environ.get('TF_SERVING_HOST', 'localhost')
    TF_SERVING_REST_PORT = int(os.environ.get('TF_SERVING_REST_PORT', 8501))
    TF_SERVING_GRPC_PORT = int(os.environ.get('TF_SERVING_GRPC_PORT', 8500))
    MODEL_NAME = os.environ.get('MODEL_NAME', 'face_recognition')
    
    # Face recognition settings
    FACE_DETECTION_MODEL = os.environ.get('FACE_DETECTION_MODEL', 'hog')  # 'hog' or 'cnn'
    FACE_RECOGNITION_TOLERANCE = float(os.environ.get('FACE_RECOGNITION_TOLERANCE', 0.6))
    FACE_ENCODING_MODEL = os.environ.get('FACE_ENCODING_MODEL', 'large')  # 'small' or 'large'
    
    # File storage settings
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'data/faces')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Check-in settings
    CHECK_IN_COOLDOWN = int(os.environ.get('CHECK_IN_COOLDOWN', 60))  # seconds between check-ins


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
