FROM tensorflow/serving:latest

# 复制模型文件
COPY models /models

# 暴露端口
EXPOSE 8500 8501

# 设置模型名称
ENV MODEL_NAME=face_recognition

# 启动TensorFlow Serving
CMD ["tensorflow_model_server", "--rest_api_port=8501", "--model_config_file=/models/model_config.config"]
