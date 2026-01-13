"""
Face detection and recognition utility functions.
"""
import os
import pickle
import numpy as np
from typing import List, Tuple, Optional, Any

# Try to import face_recognition, fall back to mock for testing
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    face_recognition = None

# Try to import cv2
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None


class FaceDetector:
    """Face detection class using face_recognition library."""
    
    def __init__(self, model: str = 'hog'):
        """
        Initialize face detector.
        
        Args:
            model: Detection model to use ('hog' or 'cnn')
        """
        self.model = model
        
    def detect_faces(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image.
        
        Args:
            image: Image as numpy array (RGB format)
            
        Returns:
            List of face locations as (top, right, bottom, left) tuples
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("face_recognition library is not available")
        
        face_locations = face_recognition.face_locations(image, model=self.model)
        return face_locations
    
    def detect_faces_from_file(self, image_path: str) -> List[Tuple[int, int, int, int]]:
        """
        Detect faces in an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of face locations as (top, right, bottom, left) tuples
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("face_recognition library is not available")
        
        image = face_recognition.load_image_file(image_path)
        return self.detect_faces(image)
    
    def extract_face(
        self, 
        image: np.ndarray, 
        face_location: Tuple[int, int, int, int],
        margin: int = 20
    ) -> np.ndarray:
        """
        Extract a face region from an image.
        
        Args:
            image: Image as numpy array
            face_location: Face location as (top, right, bottom, left)
            margin: Extra margin around the face
            
        Returns:
            Cropped face image
        """
        top, right, bottom, left = face_location
        
        # Add margin
        height, width = image.shape[:2]
        top = max(0, top - margin)
        right = min(width, right + margin)
        bottom = min(height, bottom + margin)
        left = max(0, left - margin)
        
        return image[top:bottom, left:right]


class FaceEncoder:
    """Face encoding class for generating face feature vectors."""
    
    def __init__(self, model: str = 'large', num_jitters: int = 1):
        """
        Initialize face encoder.
        
        Args:
            model: Encoding model ('small' or 'large')
            num_jitters: Number of times to re-sample the face
        """
        self.model = model
        self.num_jitters = num_jitters
        
    def encode_face(
        self, 
        image: np.ndarray, 
        face_locations: Optional[List[Tuple[int, int, int, int]]] = None
    ) -> List[np.ndarray]:
        """
        Generate face encodings for an image.
        
        Args:
            image: Image as numpy array (RGB format)
            face_locations: Optional list of face locations
            
        Returns:
            List of face encodings (128-dimensional vectors)
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("face_recognition library is not available")
        
        if face_locations is None:
            face_locations = face_recognition.face_locations(image)
        
        encodings = face_recognition.face_encodings(
            image, 
            known_face_locations=face_locations,
            num_jitters=self.num_jitters,
            model=self.model
        )
        
        return encodings
    
    def encode_face_from_file(self, image_path: str) -> List[np.ndarray]:
        """
        Generate face encodings from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            List of face encodings
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("face_recognition library is not available")
        
        image = face_recognition.load_image_file(image_path)
        return self.encode_face(image)


class FaceRecognizer:
    """Face recognition class for identifying known faces."""
    
    def __init__(self, tolerance: float = 0.6):
        """
        Initialize face recognizer.
        
        Args:
            tolerance: How much distance between faces to consider it a match
        """
        self.tolerance = tolerance
        self.known_encodings: List[np.ndarray] = []
        self.known_ids: List[Any] = []
        
    def add_known_face(self, encoding: np.ndarray, user_id: Any):
        """
        Add a known face encoding.
        
        Args:
            encoding: Face encoding (128-dimensional vector)
            user_id: User identifier
        """
        self.known_encodings.append(encoding)
        self.known_ids.append(user_id)
        
    def remove_known_face(self, user_id: Any) -> bool:
        """
        Remove a known face by user ID.
        
        Args:
            user_id: User identifier to remove
            
        Returns:
            True if face was removed, False otherwise
        """
        indices_to_remove = [
            i for i, uid in enumerate(self.known_ids) if uid == user_id
        ]
        
        for i in reversed(indices_to_remove):
            del self.known_encodings[i]
            del self.known_ids[i]
            
        return len(indices_to_remove) > 0
    
    def load_known_faces_from_db(self, users):
        """
        Load known face encodings from database users.
        
        Args:
            users: List of User objects with face_encoding attribute
        """
        self.known_encodings = []
        self.known_ids = []
        
        for user in users:
            if user.face_encoding:
                try:
                    encoding = pickle.loads(user.face_encoding)
                    self.known_encodings.append(encoding)
                    self.known_ids.append(user.id)
                except Exception:
                    continue
    
    def recognize(
        self, 
        face_encoding: np.ndarray
    ) -> Tuple[Optional[Any], float]:
        """
        Recognize a face encoding against known faces.
        
        Args:
            face_encoding: Face encoding to recognize
            
        Returns:
            Tuple of (user_id, confidence) or (None, 0.0) if no match
        """
        if not FACE_RECOGNITION_AVAILABLE:
            raise RuntimeError("face_recognition library is not available")
        
        if not self.known_encodings:
            return None, 0.0
        
        # Calculate distances to all known faces
        distances = face_recognition.face_distance(
            self.known_encodings, 
            face_encoding
        )
        
        # Find the best match
        min_distance_idx = np.argmin(distances)
        min_distance = distances[min_distance_idx]
        
        if min_distance <= self.tolerance:
            confidence = 1.0 - min_distance
            return self.known_ids[min_distance_idx], confidence
        
        return None, 0.0
    
    def recognize_multiple(
        self, 
        face_encodings: List[np.ndarray]
    ) -> List[Tuple[Optional[Any], float]]:
        """
        Recognize multiple face encodings.
        
        Args:
            face_encodings: List of face encodings
            
        Returns:
            List of (user_id, confidence) tuples
        """
        return [self.recognize(enc) for enc in face_encodings]


def serialize_encoding(encoding: np.ndarray) -> bytes:
    """Serialize a face encoding to bytes."""
    return pickle.dumps(encoding)


def deserialize_encoding(data: bytes) -> np.ndarray:
    """Deserialize a face encoding from bytes."""
    return pickle.loads(data)


def preprocess_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocess an image for face recognition.
    
    Args:
        image: Image as numpy array
        
    Returns:
        Preprocessed image in RGB format
    """
    if not CV2_AVAILABLE:
        # If cv2 not available, assume image is already RGB
        return image
    
    # Convert BGR to RGB if needed (OpenCV loads as BGR)
    if len(image.shape) == 3 and image.shape[2] == 3:
        # Check if it appears to be BGR by checking red/blue channel distribution
        # For simplicity, we'll assume it might be BGR and convert
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    return image


def resize_image(image: np.ndarray, max_size: int = 1024) -> np.ndarray:
    """
    Resize image if it's too large.
    
    Args:
        image: Image as numpy array
        max_size: Maximum dimension size
        
    Returns:
        Resized image
    """
    if not CV2_AVAILABLE:
        return image
    
    height, width = image.shape[:2]
    
    if max(height, width) <= max_size:
        return image
    
    scale = max_size / max(height, width)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return cv2.resize(image, (new_width, new_height))
