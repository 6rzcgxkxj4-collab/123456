"""
Database models for the Face Recognition Attendance System.
Uses SQLAlchemy for ORM.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, LargeBinary, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model for storing registered users."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    department = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship with face encodings
    face_encodings = relationship("FaceEncoding", back_populates="user", cascade="all, delete-orphan")
    
    # Relationship with attendance records
    attendance_records = relationship("AttendanceRecord", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, employee_id={self.employee_id}, name={self.name})>"
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            "name": self.name,
            "email": self.email,
            "department": self.department,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_active": self.is_active
        }


class FaceEncoding(Base):
    """Face encoding model for storing face embeddings."""
    
    __tablename__ = "face_encodings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    encoding = Column(LargeBinary, nullable=False)  # Store numpy array as bytes
    image_path = Column(String(255), nullable=True)  # Path to the face image
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="face_encodings")
    
    def __repr__(self):
        return f"<FaceEncoding(id={self.id}, user_id={self.user_id})>"


class AttendanceRecord(Base):
    """Attendance record model for storing check-in/check-out records."""
    
    __tablename__ = "attendance_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    check_in_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    check_out_time = Column(DateTime, nullable=True)
    confidence = Column(Float, nullable=True)  # Recognition confidence score
    location = Column(String(100), nullable=True)  # Optional location info
    device_id = Column(String(50), nullable=True)  # Device identifier
    
    # Relationship with user
    user = relationship("User", back_populates="attendance_records")
    
    def __repr__(self):
        return f"<AttendanceRecord(id={self.id}, user_id={self.user_id}, check_in={self.check_in_time})>"
    
    def to_dict(self):
        """Convert attendance record to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "employee_id": self.user.employee_id if self.user else None,
            "check_in_time": self.check_in_time.isoformat() if self.check_in_time else None,
            "check_out_time": self.check_out_time.isoformat() if self.check_out_time else None,
            "confidence": self.confidence,
            "location": self.location,
            "device_id": self.device_id
        }
