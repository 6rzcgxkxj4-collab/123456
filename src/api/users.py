"""
User management API routes.
"""
import os
import pickle
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from src.models import db, User
from src.utils import FaceDetector, FaceEncoder, serialize_encoding

users_bp = Blueprint('users', __name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def admin_required(f):
    """Decorator to require admin privileges."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function


@users_bp.route('/', methods=['GET'])
@login_required
@admin_required
def list_users():
    """List all users."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '')
    department = request.args.get('department', '')
    
    query = User.query
    
    if search:
        query = query.filter(
            (User.name.ilike(f'%{search}%')) |
            (User.employee_id.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    if department:
        query = query.filter(User.department == department)
    
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'users': [user.to_dict() for user in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@users_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get user by ID."""
    # Users can only view their own profile unless admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    return jsonify({'user': user.to_dict()})


@users_bp.route('/', methods=['POST'])
@login_required
@admin_required
def create_user():
    """Create a new user."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['employee_id', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    # Check if employee_id already exists
    if User.query.filter_by(employee_id=data['employee_id']).first():
        return jsonify({'error': 'Employee ID already exists'}), 400
    
    # Check if email already exists
    if data.get('email') and User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        employee_id=data['employee_id'],
        name=data['name'],
        email=data.get('email'),
        department=data.get('department'),
        is_admin=data.get('is_admin', False)
    )
    
    # Set default password
    default_password = data.get('password', 'changeme123')
    user.set_password(default_password)
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'message': 'User created successfully',
        'user': user.to_dict()
    }), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user information."""
    # Users can only update their own profile unless admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Update allowed fields
    if current_user.is_admin:
        if 'name' in data:
            user.name = data['name']
        if 'department' in data:
            user.department = data['department']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'is_admin' in data:
            user.is_admin = data['is_admin']
    
    # Allow email update by user or admin
    if 'email' in data:
        if data['email'] and User.query.filter(
            User.email == data['email'],
            User.id != user_id
        ).first():
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': user.to_dict()
    })


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user."""
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    user = User.query.get_or_404(user_id)
    
    # Delete face image if exists
    if user.face_image_path and os.path.exists(user.face_image_path):
        os.remove(user.face_image_path)
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'message': 'User deleted successfully'})


@users_bp.route('/<int:user_id>/register-face', methods=['POST'])
@login_required
def register_face(user_id):
    """Register face for a user."""
    # Users can only register their own face unless admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Import face_recognition for image processing
        import face_recognition
        import numpy as np
        
        # Read and process image
        image = face_recognition.load_image_file(file)
        
        # Detect faces
        detector = FaceDetector(model=current_app.config.get('FACE_DETECTION_MODEL', 'hog'))
        face_locations = detector.detect_faces(image)
        
        if len(face_locations) == 0:
            return jsonify({'error': 'No face detected in the image'}), 400
        
        if len(face_locations) > 1:
            return jsonify({'error': 'Multiple faces detected. Please provide an image with a single face'}), 400
        
        # Encode face
        encoder = FaceEncoder(model=current_app.config.get('FACE_ENCODING_MODEL', 'large'))
        encodings = encoder.encode_face(image, face_locations)
        
        if not encodings:
            return jsonify({'error': 'Failed to encode face'}), 500
        
        # Save face encoding
        user.face_encoding = serialize_encoding(encodings[0])
        
        # Save face image
        filename = secure_filename(f"{user.employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'data/faces')
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        
        # Save the image
        from PIL import Image
        img = Image.fromarray(image)
        img.save(filepath)
        
        user.face_image_path = filepath
        db.session.commit()
        
        return jsonify({
            'message': 'Face registered successfully',
            'user': user.to_dict()
        })
        
    except ImportError:
        return jsonify({'error': 'Face recognition library not available'}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to register face: {str(e)}'}), 500


@users_bp.route('/<int:user_id>/remove-face', methods=['POST'])
@login_required
def remove_face(user_id):
    """Remove registered face for a user."""
    # Users can only remove their own face unless admin
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Delete face image if exists
    if user.face_image_path and os.path.exists(user.face_image_path):
        os.remove(user.face_image_path)
    
    user.face_encoding = None
    user.face_image_path = None
    db.session.commit()
    
    return jsonify({
        'message': 'Face removed successfully',
        'user': user.to_dict()
    })


@users_bp.route('/departments', methods=['GET'])
@login_required
def list_departments():
    """List all unique departments."""
    departments = db.session.query(User.department).distinct().filter(
        User.department.isnot(None)
    ).all()
    
    return jsonify({
        'departments': [d[0] for d in departments if d[0]]
    })
