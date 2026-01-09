"""
Face processing utilities for detection, preprocessing, and encoding.
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

from config.config import config

logger = logging.getLogger(__name__)


class FaceProcessor:
    """Face detection and preprocessing class."""
    
    def __init__(self):
        """Initialize face processor with Haar cascade detector."""
        # Use OpenCV's pre-trained Haar cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.image_size = config.IMAGE_SIZE
    
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image.
        
        Args:
            image: Input image as numpy array (BGR format).
        
        Returns:
            List of face bounding boxes as (x, y, width, height) tuples.
        """
        # Convert to grayscale for detection
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        return [(x, y, w, h) for (x, y, w, h) in faces]
    
    def extract_face(
        self,
        image: np.ndarray,
        face_box: Tuple[int, int, int, int],
        margin: float = 0.2
    ) -> np.ndarray:
        """
        Extract and preprocess a face region from an image.
        
        Args:
            image: Input image as numpy array (BGR format).
            face_box: Face bounding box as (x, y, width, height).
            margin: Margin to add around the face (as fraction of face size).
        
        Returns:
            Preprocessed face image ready for embedding extraction.
        """
        x, y, w, h = face_box
        img_h, img_w = image.shape[:2]
        
        # Add margin
        margin_w = int(w * margin)
        margin_h = int(h * margin)
        
        x1 = max(0, x - margin_w)
        y1 = max(0, y - margin_h)
        x2 = min(img_w, x + w + margin_w)
        y2 = min(img_h, y + h + margin_h)
        
        # Extract face region
        face = image[y1:y2, x1:x2]
        
        # Resize to model input size
        face = cv2.resize(face, self.image_size)
        
        # Convert BGR to RGB
        face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        
        # Normalize pixel values to [-1, 1] (FaceNet preprocessing)
        face = (face.astype(np.float32) - 127.5) / 128.0
        
        return face
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for face recognition.
        
        Args:
            image: Input image as numpy array.
        
        Returns:
            Preprocessed image ready for model input.
        """
        # Resize to model input size
        if image.shape[:2] != self.image_size:
            image = cv2.resize(image, self.image_size)
        
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Normalize pixel values to [-1, 1]
        image = (image.astype(np.float32) - 127.5) / 128.0
        
        return image
    
    def detect_and_extract_faces(
        self,
        image: np.ndarray
    ) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        Detect and extract all faces from an image.
        
        Args:
            image: Input image as numpy array (BGR format).
        
        Returns:
            List of tuples containing (preprocessed_face, bounding_box).
        """
        faces = []
        face_boxes = self.detect_faces(image)
        
        for box in face_boxes:
            try:
                face = self.extract_face(image, box)
                faces.append((face, box))
            except Exception as e:
                logger.warning(f"Failed to extract face: {e}")
                continue
        
        return faces


def calculate_distance(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two face embeddings.
    
    Args:
        embedding1: First face embedding vector.
        embedding2: Second face embedding vector.
    
    Returns:
        Euclidean distance between embeddings.
    """
    return float(np.linalg.norm(embedding1 - embedding2))


def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two face embeddings.
    
    Args:
        embedding1: First face embedding vector.
        embedding2: Second face embedding vector.
    
    Returns:
        Cosine similarity score (0 to 1, higher is more similar).
    """
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def is_same_person(
    embedding1: np.ndarray,
    embedding2: np.ndarray,
    threshold: float = None
) -> Tuple[bool, float]:
    """
    Determine if two face embeddings belong to the same person.
    
    Args:
        embedding1: First face embedding vector.
        embedding2: Second face embedding vector.
        threshold: Distance threshold for same person (lower = stricter).
    
    Returns:
        Tuple of (is_same_person, confidence_score).
    """
    if threshold is None:
        threshold = config.FACE_RECOGNITION_THRESHOLD
    
    distance = calculate_distance(embedding1, embedding2)
    # Convert distance to confidence (inverse relationship)
    confidence = 1.0 / (1.0 + distance)
    
    return distance < threshold, confidence


# Create default face processor instance
face_processor = FaceProcessor()
