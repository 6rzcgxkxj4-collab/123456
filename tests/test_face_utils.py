"""
Tests for face recognition utilities.
"""
import pytest
import numpy as np
import pickle
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.face_recognition_utils import (
    FaceRecognizer,
    serialize_encoding,
    deserialize_encoding,
    resize_image
)


class TestFaceRecognizer:
    """Test FaceRecognizer class."""
    
    def test_add_known_face(self):
        """Test adding a known face."""
        recognizer = FaceRecognizer(tolerance=0.6)
        encoding = np.random.rand(128)
        
        recognizer.add_known_face(encoding, user_id=1)
        
        assert len(recognizer.known_encodings) == 1
        assert len(recognizer.known_ids) == 1
        assert recognizer.known_ids[0] == 1
    
    def test_add_multiple_faces(self):
        """Test adding multiple faces."""
        recognizer = FaceRecognizer(tolerance=0.6)
        
        for i in range(5):
            encoding = np.random.rand(128)
            recognizer.add_known_face(encoding, user_id=i)
        
        assert len(recognizer.known_encodings) == 5
        assert len(recognizer.known_ids) == 5
    
    def test_remove_known_face(self):
        """Test removing a known face."""
        recognizer = FaceRecognizer(tolerance=0.6)
        
        # Add faces
        for i in range(3):
            encoding = np.random.rand(128)
            recognizer.add_known_face(encoding, user_id=i)
        
        # Remove middle face
        result = recognizer.remove_known_face(user_id=1)
        
        assert result is True
        assert len(recognizer.known_encodings) == 2
        assert 1 not in recognizer.known_ids
    
    def test_remove_nonexistent_face(self):
        """Test removing a face that doesn't exist."""
        recognizer = FaceRecognizer(tolerance=0.6)
        
        result = recognizer.remove_known_face(user_id=999)
        
        assert result is False
    
    def test_recognize_empty_database(self):
        """Test recognition with no known faces."""
        recognizer = FaceRecognizer(tolerance=0.6)
        test_encoding = np.random.rand(128)
        
        # If face_recognition library is not available, this will raise
        # Otherwise it should return None, 0.0 for empty database
        try:
            user_id, confidence = recognizer.recognize(test_encoding)
            assert user_id is None
            assert confidence == 0.0
        except RuntimeError as e:
            if "face_recognition library is not available" in str(e):
                pytest.skip("face_recognition library not available")


class TestEncodingSerialization:
    """Test encoding serialization functions."""
    
    def test_serialize_deserialize(self):
        """Test serialization and deserialization of encoding."""
        original = np.random.rand(128)
        
        serialized = serialize_encoding(original)
        deserialized = deserialize_encoding(serialized)
        
        assert isinstance(serialized, bytes)
        assert isinstance(deserialized, np.ndarray)
        np.testing.assert_array_almost_equal(original, deserialized)
    
    def test_serialize_different_sizes(self):
        """Test serialization with different array sizes."""
        for size in [64, 128, 256, 512]:
            original = np.random.rand(size)
            serialized = serialize_encoding(original)
            deserialized = deserialize_encoding(serialized)
            
            np.testing.assert_array_almost_equal(original, deserialized)


class TestImageProcessing:
    """Test image processing utilities."""
    
    def test_resize_image_smaller(self):
        """Test resizing a large image."""
        # Create a test image (RGB)
        image = np.random.randint(0, 255, (2048, 2048, 3), dtype=np.uint8)
        
        try:
            import cv2
            resized = resize_image(image, max_size=1024)
            
            assert max(resized.shape[:2]) <= 1024
        except ImportError:
            # cv2 not available, function should return original image
            resized = resize_image(image, max_size=1024)
            assert resized is image
    
    def test_resize_image_already_small(self):
        """Test that small images are not resized."""
        image = np.random.randint(0, 255, (500, 500, 3), dtype=np.uint8)
        
        try:
            import cv2
            resized = resize_image(image, max_size=1024)
            
            assert resized.shape == image.shape
        except ImportError:
            resized = resize_image(image, max_size=1024)
            assert resized is image


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
