FROM tensorflow/serving:latest

# Copy model files / 复制模型文件
COPY models /models

# Expose ports / 暴露端口
EXPOSE 8500 8501

# Set model name / 设置模型名称
ENV MODEL_NAME=face_recognition

# Start TensorFlow Serving / 启动TensorFlow Serving
CMD ["tensorflow_model_server", "--rest_api_port=8501", "--model_config_file=/models/model_config.config"]
