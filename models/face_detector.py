"""
面部检测模块
使用face_recognition库进行人脸检测和特征提取
"""

import face_recognition
import numpy as np
import cv2
from typing import List, Tuple, Optional


class FaceDetector:
    """人脸检测器类"""
    
    def __init__(self, model='hog'):
        """
        初始化人脸检测器
        
        Args:
            model: 检测模型类型，'hog'(快速) 或 'cnn'(精确但慢)
        """
        self.model = model
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        检测图像中的人脸位置
        
        Args:
            image: 输入图像(numpy数组，BGR格式)
            
        Returns:
            人脸位置列表，每个位置为(top, right, bottom, left)
        """
        # 将BGR转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 检测人脸
        face_locations = face_recognition.face_locations(rgb_image, model=self.model)
        
        return face_locations
    
    def get_face_encodings(self, image: np.ndarray, face_locations: Optional[List] = None) -> List[np.ndarray]:
        """
        获取人脸特征编码
        
        Args:
            image: 输入图像(numpy数组，BGR格式)
            face_locations: 人脸位置列表，如果为None则自动检测
            
        Returns:
            人脸特征向量列表，每个向量为128维
        """
        # 将BGR转换为RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 如果没有提供人脸位置，先检测
        if face_locations is None:
            face_locations = self.detect_faces(image)
        
        # 获取人脸编码
        encodings = face_recognition.face_encodings(rgb_image, face_locations)
        
        return encodings
    
    def compare_faces(self, known_encodings: List[np.ndarray], face_encoding: np.ndarray, 
                     tolerance: float = 0.6) -> Tuple[List[bool], List[float]]:
        """
        比较人脸编码
        
        Args:
            known_encodings: 已知的人脸编码列表
            face_encoding: 待比较的人脸编码
            tolerance: 匹配阈值，越小越严格
            
        Returns:
            (匹配结果列表, 距离列表)
        """
        # 计算距离
        distances = face_recognition.face_distance(known_encodings, face_encoding)
        
        # 判断是否匹配
        matches = list(distances <= tolerance)
        
        return matches, distances.tolist()
    
    def find_best_match(self, known_encodings: List[np.ndarray], face_encoding: np.ndarray,
                       tolerance: float = 0.6) -> Tuple[Optional[int], Optional[float]]:
        """
        找到最佳匹配
        
        Args:
            known_encodings: 已知的人脸编码列表
            face_encoding: 待比较的人脸编码
            tolerance: 匹配阈值
            
        Returns:
            (最佳匹配索引, 距离)，如果没有匹配则返回(None, None)
        """
        if len(known_encodings) == 0:
            return None, None
        
        matches, distances = self.compare_faces(known_encodings, face_encoding, tolerance)
        
        if not any(matches):
            return None, None
        
        # 找到最小距离的索引
        best_match_index = np.argmin(distances)
        
        return best_match_index, distances[best_match_index]
    
    def draw_face_box(self, image: np.ndarray, face_location: Tuple[int, int, int, int],
                     label: str = "", color: Tuple[int, int, int] = (0, 255, 0)) -> np.ndarray:
        """
        在图像上绘制人脸框
        
        Args:
            image: 输入图像
            face_location: 人脸位置(top, right, bottom, left)
            label: 标签文本
            color: 框的颜色(BGR)
            
        Returns:
            绘制后的图像
        """
        top, right, bottom, left = face_location
        
        # 绘制矩形框
        cv2.rectangle(image, (left, top), (right, bottom), color, 2)
        
        # 绘制标签
        if label:
            cv2.rectangle(image, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(image, label, (left + 6, bottom - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        
        return image
