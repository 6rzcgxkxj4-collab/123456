"""
Unit tests for the Face Recognition Attendance System.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import json

# Test configuration
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFaceUtils:
    """Tests for face processing utilities."""
    
    def test_calculate_distance(self):
        """Test Euclidean distance calculation."""
        from src.utils.face_utils import calculate_distance
        
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        distance = calculate_distance(embedding1, embedding2)
        assert abs(distance - np.sqrt(2)) < 1e-6
    
    def test_calculate_distance_same_embedding(self):
        """Test distance between identical embeddings."""
        from src.utils.face_utils import calculate_distance
        
        embedding = np.array([0.5, 0.5, 0.5])
        distance = calculate_distance(embedding, embedding)
        assert distance == 0.0
    
    def test_calculate_cosine_similarity(self):
        """Test cosine similarity calculation."""
        from src.utils.face_utils import calculate_cosine_similarity
        
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([1.0, 0.0, 0.0])
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        assert abs(similarity - 1.0) < 1e-6
    
    def test_calculate_cosine_similarity_orthogonal(self):
        """Test cosine similarity for orthogonal vectors."""
        from src.utils.face_utils import calculate_cosine_similarity
        
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        similarity = calculate_cosine_similarity(embedding1, embedding2)
        assert abs(similarity) < 1e-6
    
    def test_is_same_person(self):
        """Test same person detection."""
        from src.utils.face_utils import is_same_person
        
        # Similar embeddings (small distance)
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.99, 0.01, 0.0])
        
        is_same, confidence = is_same_person(embedding1, embedding2, threshold=0.5)
        assert is_same is True
        assert confidence > 0.5
    
    def test_is_different_person(self):
        """Test different person detection."""
        from src.utils.face_utils import is_same_person
        
        # Different embeddings (large distance)
        embedding1 = np.array([1.0, 0.0, 0.0])
        embedding2 = np.array([0.0, 1.0, 0.0])
        
        is_same, confidence = is_same_person(embedding1, embedding2, threshold=0.5)
        assert is_same is False


class TestFaceProcessor:
    """Tests for FaceProcessor class."""
    
    def test_preprocess_image(self):
        """Test image preprocessing."""
        from src.utils.face_utils import FaceProcessor
        
        processor = FaceProcessor()
        
        # Create a dummy BGR image
        image = np.random.randint(0, 256, (200, 200, 3), dtype=np.uint8)
        
        processed = processor.preprocess_image(image)
        
        # Check output shape
        assert processed.shape == (160, 160, 3)
        
        # Check value range [-1, 1]
        assert processed.min() >= -1.0
        assert processed.max() <= 1.0
    
    def test_detect_faces_returns_list(self):
        """Test that detect_faces returns a list."""
        from src.utils.face_utils import FaceProcessor
        
        processor = FaceProcessor()
        
        # Create a dummy image (unlikely to contain a face)
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        
        faces = processor.detect_faces(image)
        
        assert isinstance(faces, list)


class TestConfig:
    """Tests for configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        from config.config import Config
        
        cfg = Config()
        
        assert cfg.TF_SERVING_HOST == "localhost"
        assert cfg.TF_SERVING_PORT == 8501
        assert cfg.FACE_ENCODING_SIZE == 128
        assert cfg.IMAGE_SIZE == (160, 160)


class TestDatabaseModels:
    """Tests for database models."""
    
    def test_user_model_creation(self):
        """Test User model creation."""
        from src.models.database import User
        
        user = User(
            employee_id="EMP001",
            name="Test User",
            email="test@example.com",
            department="Engineering"
        )
        
        assert user.employee_id == "EMP001"
        assert user.name == "Test User"
        assert user.email == "test@example.com"
        assert user.department == "Engineering"
    
    def test_user_to_dict(self):
        """Test User to_dict method."""
        from src.models.database import User
        
        user = User(
            id=1,
            employee_id="EMP001",
            name="Test User",
            email="test@example.com",
            department="Engineering",
            is_active=True
        )
        
        user_dict = user.to_dict()
        
        assert user_dict["id"] == 1
        assert user_dict["employee_id"] == "EMP001"
        assert user_dict["name"] == "Test User"
        assert user_dict["is_active"] is True


class TestTFServingClient:
    """Tests for TensorFlow Serving client."""
    
    @patch('src.backend.tf_serving_client.requests.get')
    def test_get_model_status(self, mock_get):
        """Test getting model status."""
        from src.backend.tf_serving_client import TFServingClient
        
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"model_version_status": [{"state": "AVAILABLE"}]}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        client = TFServingClient()
        status = client.get_model_status()
        
        assert "model_version_status" in status
    
    @patch('src.backend.tf_serving_client.requests.post')
    def test_predict(self, mock_post):
        """Test prediction."""
        from src.backend.tf_serving_client import TFServingClient
        
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {"predictions": [[0.1] * 128]}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        client = TFServingClient()
        image = np.random.rand(160, 160, 3).astype(np.float32)
        embedding = client.predict(image)
        
        assert embedding is not None
        assert len(embedding) == 128
    
    @patch('src.backend.tf_serving_client.requests.post')
    def test_predict_failure(self, mock_post):
        """Test prediction failure handling."""
        from src.backend.tf_serving_client import TFServingClient
        import requests
        
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        
        client = TFServingClient()
        image = np.random.rand(160, 160, 3).astype(np.float32)
        embedding = client.predict(image)
        
        assert embedding is None


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.backend.app import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/api/health')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['status'] == 'healthy'
    
    def test_get_users_empty(self, client):
        """Test getting users when database is empty."""
        response = client.get('/api/users')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['success'] is True
        assert isinstance(data['data'], list)
    
    def test_create_user_missing_fields(self, client):
        """Test creating user with missing required fields."""
        response = client.post('/api/users', 
                              data=json.dumps({}),
                              content_type='application/json')
        data = json.loads(response.data)
        
        assert response.status_code == 400
        assert data['success'] is False
    
    def test_get_attendance_empty(self, client):
        """Test getting attendance when no records exist."""
        response = client.get('/api/attendance')
        data = json.loads(response.data)
        
        assert response.status_code == 200
        assert data['success'] is True
        assert isinstance(data['data'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
