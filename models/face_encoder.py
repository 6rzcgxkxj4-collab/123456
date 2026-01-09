"""
人脸编码模块
使用深度学习模型提取人脸特征向量
"""

import numpy as np
import face_recognition
import cv2
from typing import Optional


class FaceEncoder:
    """人脸编码器类"""
    
    def __init__(self):
        """初始化人脸编码器"""
        pass
    
    def encode_face(self, image: np.ndarray, face_location: Optional[tuple] = None) -> Optional[np.ndarray]:
        """
        对单个人脸进行编码
        
        Args:
            image: 输入图像(BGR格式)
            face_location: 人脸位置，如果为None则自动检测
            
        Returns:
            128维人脸特征向量，如果失败返回None
        """
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 如果没有提供位置，检测人脸
        if face_location is None:
            face_locations = face_recognition.face_locations(rgb_image)
            if len(face_locations) == 0:
                return None
            face_location = face_locations[0]
        
        # 获取编码
        encodings = face_recognition.face_encodings(rgb_image, [face_location])
        
        if len(encodings) == 0:
            return None
        
        return encodings[0]
    
    def encode_multiple_faces(self, image: np.ndarray) -> list:
        """
        对图像中的多个人脸进行编码
        
        Args:
            image: 输入图像(BGR格式)
            
        Returns:
            人脸编码列表
        """
        # 转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 检测所有人脸
        face_locations = face_recognition.face_locations(rgb_image)
        
        # 获取所有编码
        encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        return list(encodings)
    
    @staticmethod
    def calculate_distance(encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """
        计算两个人脸编码之间的欧氏距离
        
        Args:
            encoding1: 第一个编码
            encoding2: 第二个编码
            
        Returns:
            欧氏距离
        """
        return np.linalg.norm(encoding1 - encoding2)
    
    @staticmethod
    def is_match(encoding1: np.ndarray, encoding2: np.ndarray, threshold: float = 0.6) -> bool:
        """
        判断两个人脸编码是否匹配
        
        Args:
            encoding1: 第一个编码
            encoding2: 第二个编码
            threshold: 匹配阈值，默认0.6
            
        Returns:
            是否匹配
        """
        distance = FaceEncoder.calculate_distance(encoding1, encoding2)
        return distance <= threshold
    
    @staticmethod
    def encoding_to_list(encoding: np.ndarray) -> list:
        """
        将numpy数组编码转换为列表
        
        Args:
            encoding: numpy数组编码
            
        Returns:
            列表形式的编码
        """
        return encoding.tolist()
    
    @staticmethod
    def list_to_encoding(encoding_list: list) -> np.ndarray:
        """
        将列表转换为numpy数组编码
        
        Args:
            encoding_list: 列表形式的编码
            
        Returns:
            numpy数组编码
        """
        return np.array(encoding_list)
