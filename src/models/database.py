"""
Database models for the Facial Recognition Check-in System.
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for storing user information and face encodings."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    department = db.Column(db.String(100), nullable=True)
    face_encoding = db.Column(db.LargeBinary, nullable=True)  # Serialized numpy array
    face_image_path = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    password_hash = db.Column(db.String(256), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    check_ins = db.relationship('CheckIn', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'name': self.name,
            'email': self.email,
            'department': self.department,
            'is_admin': self.is_admin,
            'is_active': self.is_active,
            'has_face_registered': self.face_encoding is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<User {self.employee_id}: {self.name}>'


class CheckIn(db.Model):
    """Check-in record model."""
    
    __tablename__ = 'check_ins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    check_in_type = db.Column(db.String(20), default='face')  # 'face', 'manual'
    confidence = db.Column(db.Float, nullable=True)  # Recognition confidence score
    location = db.Column(db.String(100), nullable=True)
    device_id = db.Column(db.String(50), nullable=True)
    snapshot_path = db.Column(db.String(255), nullable=True)  # Path to check-in photo
    
    def to_dict(self):
        """Convert check-in to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'employee_id': self.user.employee_id if self.user else None,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'check_in_type': self.check_in_type,
            'confidence': self.confidence,
            'location': self.location,
            'device_id': self.device_id
        }
    
    def __repr__(self):
        return f'<CheckIn {self.user_id} at {self.check_in_time}>'


class SystemLog(db.Model):
    """System log for tracking operations and errors."""
    
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    level = db.Column(db.String(20), nullable=False)  # 'INFO', 'WARNING', 'ERROR'
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(100), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    def to_dict(self):
        """Convert log to dictionary."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'message': self.message,
            'module': self.module,
            'user_id': self.user_id
        }
    
    def __repr__(self):
        return f'<SystemLog {self.level}: {self.message[:50]}>'
