"""
User service for managing user-related operations.
"""

import io
import logging
import os
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np

from config.config import config
from src.backend.db_service import db_service
from src.backend.tf_serving_client import tf_serving_client
from src.models.database import User, FaceEncoding
from src.utils.face_utils import face_processor, calculate_distance

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user management operations."""
    
    def __init__(self):
        """Initialize user service."""
        self.db = db_service
        self.tf_client = tf_serving_client
        self.face_processor = face_processor
    
    def create_user(
        self,
        employee_id: str,
        name: str,
        email: str = None,
        department: str = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            employee_id: Unique employee identifier.
            name: User's full name.
            email: User's email address.
            department: User's department.
        
        Returns:
            Created User object.
        
        Raises:
            ValueError: If employee_id already exists.
        """
        session = self.db.get_session()
        try:
            # Check if employee_id already exists
            existing = session.query(User).filter_by(employee_id=employee_id).first()
            if existing:
                raise ValueError(f"User with employee_id {employee_id} already exists")
            
            # Create new user
            user = User(
                employee_id=employee_id,
                name=name,
                email=email,
                department=department
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            
            logger.info(f"Created user: {user}")
            return user
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        session = self.db.get_session()
        try:
            return session.query(User).filter_by(id=user_id).first()
        finally:
            session.close()
    
    def get_user_by_employee_id(self, employee_id: str) -> Optional[User]:
        """Get user by employee ID."""
        session = self.db.get_session()
        try:
            return session.query(User).filter_by(employee_id=employee_id).first()
        finally:
            session.close()
    
    def get_all_users(self, active_only: bool = True) -> List[User]:
        """Get all users."""
        session = self.db.get_session()
        try:
            query = session.query(User)
            if active_only:
                query = query.filter_by(is_active=True)
            return query.all()
        finally:
            session.close()
    
    def update_user(
        self,
        user_id: int,
        name: str = None,
        email: str = None,
        department: str = None,
        is_active: bool = None
    ) -> Optional[User]:
        """Update user information."""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return None
            
            if name is not None:
                user.name = name
            if email is not None:
                user.email = email
            if department is not None:
                user.department = department
            if is_active is not None:
                user.is_active = is_active
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            
            return user
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user and their face encodings."""
        session = self.db.get_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            
            session.delete(user)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def register_face(
        self,
        user_id: int,
        face_image: np.ndarray,
        image_path: str = None
    ) -> Optional[FaceEncoding]:
        """
        Register a face for a user.
        
        Args:
            user_id: User's ID.
            face_image: Face image as numpy array (BGR format).
            image_path: Optional path where face image is saved.
        
        Returns:
            Created FaceEncoding object, or None if registration fails.
        """
        session = self.db.get_session()
        try:
            # Check if user exists
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                logger.error(f"User with id {user_id} not found")
                return None
            
            # Detect and extract face
            faces = self.face_processor.detect_and_extract_faces(face_image)
            if not faces:
                logger.error("No face detected in image")
                return None
            
            if len(faces) > 1:
                logger.warning("Multiple faces detected, using the first one")
            
            preprocessed_face, _ = faces[0]
            
            # Get face embedding from TensorFlow Serving
            embedding = self.tf_client.predict(preprocessed_face)
            if embedding is None:
                logger.error("Failed to get face embedding")
                return None
            
            # Store encoding as bytes
            encoding_bytes = embedding.tobytes()
            
            # Create face encoding record
            face_encoding = FaceEncoding(
                user_id=user_id,
                encoding=encoding_bytes,
                image_path=image_path
            )
            session.add(face_encoding)
            session.commit()
            session.refresh(face_encoding)
            
            logger.info(f"Registered face for user {user_id}")
            return face_encoding
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to register face: {e}")
            raise e
        finally:
            session.close()
    
    def get_user_face_encodings(self, user_id: int) -> List[np.ndarray]:
        """Get all face encodings for a user."""
        session = self.db.get_session()
        try:
            face_encodings = session.query(FaceEncoding).filter_by(user_id=user_id).all()
            return [
                np.frombuffer(fe.encoding, dtype=np.float32)
                for fe in face_encodings
            ]
        finally:
            session.close()
    
    def recognize_face(
        self,
        face_image: np.ndarray,
        threshold: float = None
    ) -> Optional[Tuple[User, float]]:
        """
        Recognize a face and return the matching user.
        
        Args:
            face_image: Face image as numpy array (BGR format).
            threshold: Distance threshold for recognition.
        
        Returns:
            Tuple of (User, confidence) if recognized, None otherwise.
        """
        if threshold is None:
            threshold = config.FACE_RECOGNITION_THRESHOLD
        
        # Detect and extract face
        faces = self.face_processor.detect_and_extract_faces(face_image)
        if not faces:
            logger.warning("No face detected in image")
            return None
        
        preprocessed_face, _ = faces[0]
        
        # Get face embedding
        query_embedding = self.tf_client.predict(preprocessed_face)
        if query_embedding is None:
            logger.error("Failed to get face embedding")
            return None
        
        # Find matching user
        session = self.db.get_session()
        try:
            # Get all active users with face encodings
            users = session.query(User).filter_by(is_active=True).all()
            
            best_match = None
            best_distance = float('inf')
            
            for user in users:
                face_encodings = session.query(FaceEncoding).filter_by(user_id=user.id).all()
                
                for fe in face_encodings:
                    stored_embedding = np.frombuffer(fe.encoding, dtype=np.float32)
                    distance = calculate_distance(query_embedding, stored_embedding)
                    
                    if distance < best_distance:
                        best_distance = distance
                        best_match = user
            
            if best_match and best_distance < threshold:
                confidence = 1.0 / (1.0 + best_distance)
                return best_match, confidence
            
            return None
            
        finally:
            session.close()


# Create default user service instance
user_service = UserService()
