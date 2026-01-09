"""
TensorFlow Serving模型导出模块
将训练好的人脸识别模型导出为TensorFlow Serving格式
"""

import tensorflow as tf
import numpy as np
import os
from datetime import datetime


class ModelExporter:
    """模型导出器类"""
    
    def __init__(self, export_path: str = './tf_serving/models/face_recognition'):
        """
        初始化模型导出器
        
        Args:
            export_path: 模型导出路径
        """
        self.export_path = export_path
    
    def create_simple_model(self):
        """
        创建一个简单的人脸特征比对模型
        这是一个示例模型，实际使用中应该使用训练好的模型
        """
        # 输入层：两个128维的人脸特征向量
        input_encoding1 = tf.keras.Input(shape=(128,), name='encoding1')
        input_encoding2 = tf.keras.Input(shape=(128,), name='encoding2')
        
        # 计算欧氏距离
        def euclidean_distance(inputs):
            encoding1, encoding2 = inputs
            return tf.sqrt(tf.reduce_sum(tf.square(encoding1 - encoding2), axis=1, keepdims=True))
        
        distance = tf.keras.layers.Lambda(euclidean_distance)([input_encoding1, input_encoding2])
        
        # 输出层：距离值
        output = tf.keras.layers.Dense(1, activation='linear', name='distance')(distance)
        
        model = tf.keras.Model(inputs=[input_encoding1, input_encoding2], outputs=output)
        
        return model
    
    def export_model(self, model=None, version: int = None):
        """
        导出模型为TensorFlow Serving格式
        
        Args:
            model: Keras模型，如果为None则创建示例模型
            version: 模型版本号，如果为None则使用时间戳
        """
        if model is None:
            model = self.create_simple_model()
        
        if version is None:
            version = int(datetime.now().timestamp())
        
        # 构建导出路径
        export_dir = os.path.join(self.export_path, str(version))
        
        # 确保目录存在
        os.makedirs(export_dir, exist_ok=True)
        
        # 保存模型
        tf.saved_model.save(model, export_dir)
        
        print(f"模型已导出到: {export_dir}")
        return export_dir
    
    def export_face_encoder_model(self):
        """
        导出人脸编码模型
        这个模型接收图像并输出人脸特征向量
        """
        # 创建一个简单的编码模型示例
        # 实际应用中应该使用预训练的模型如FaceNet或者ArcFace
        
        input_image = tf.keras.Input(shape=(160, 160, 3), name='input_image')
        
        # 使用MobileNetV2作为骨干网络的示例
        base_model = tf.keras.applications.MobileNetV2(
            input_shape=(160, 160, 3),
            include_top=False,
            weights='imagenet'
        )
        
        x = base_model(input_image, training=False)
        x = tf.keras.layers.GlobalAveragePooling2D()(x)
        x = tf.keras.layers.Dense(256, activation='relu')(x)
        output = tf.keras.layers.Dense(128, activation=None, name='embedding')(x)
        
        # L2归一化
        output = tf.keras.layers.Lambda(lambda x: tf.nn.l2_normalize(x, axis=1))(output)
        
        model = tf.keras.Model(inputs=input_image, outputs=output)
        
        return model


def export_models():
    """导出所有模型"""
    exporter = ModelExporter()
    
    # 导出比对模型
    print("导出人脸比对模型...")
    comparison_model = exporter.create_simple_model()
    exporter.export_model(comparison_model, version=1)
    
    # 导出编码模型
    print("导出人脸编码模型...")
    encoder_model = exporter.export_face_encoder_model()
    exporter.export_path = './tf_serving/models/face_encoder'
    exporter.export_model(encoder_model, version=1)
    
    print("所有模型导出完成！")


if __name__ == '__main__':
    export_models()
