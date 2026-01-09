"""
应用配置文件
"""

import os

class Config:
    """应用配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = True
    
    # 数据库配置
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    
    # 上传文件配置
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    # 人脸识别配置
    FACE_DETECTION_MODEL = 'hog'  # 'hog' 或 'cnn'
    FACE_RECOGNITION_TOLERANCE = 0.6  # 匹配阈值，越小越严格
    
    # TensorFlow Serving配置
    TF_SERVING_URL = os.environ.get('TF_SERVING_URL') or 'http://localhost:8501'
    USE_TF_SERVING = os.environ.get('USE_TF_SERVING', 'False').lower() == 'true'
    
    # 应用配置
    HOST = '0.0.0.0'
    PORT = 5000
