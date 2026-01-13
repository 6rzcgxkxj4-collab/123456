"""
Check-in API routes for facial recognition attendance.
"""
import os
import base64
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from src.models import db, User, CheckIn, SystemLog
from src.utils import (
    FaceDetector, 
    FaceEncoder, 
    FaceRecognizer,
    deserialize_encoding
)

checkin_bp = Blueprint('checkin', __name__)


def admin_required(f):
    """Decorator to require admin privileges."""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function


def log_system_event(level: str, message: str, module: str = 'checkin', user_id: int = None):
    """Log a system event to the database."""
    log = SystemLog(
        level=level,
        message=message,
        module=module,
        user_id=user_id
    )
    db.session.add(log)
    db.session.commit()


@checkin_bp.route('/face', methods=['POST'])
def face_checkin():
    """
    Process face check-in.
    
    Accepts either:
    - 'image' file upload
    - 'image_base64' in JSON body
    """
    try:
        import face_recognition
        import numpy as np
    except ImportError:
        return jsonify({'error': 'Face recognition library not available'}), 500
    
    image_data = None
    
    # Get image from file upload
    if 'image' in request.files:
        file = request.files['image']
        if file.filename != '':
            image_data = face_recognition.load_image_file(file)
    
    # Get image from base64
    if image_data is None and request.is_json:
        data = request.get_json()
        if data and 'image_base64' in data:
            try:
                image_bytes = base64.b64decode(data['image_base64'])
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes))
                image_data = np.array(img)
            except Exception as e:
                return jsonify({'error': f'Invalid base64 image: {str(e)}'}), 400
    
    if image_data is None:
        return jsonify({'error': 'No image provided'}), 400
    
    try:
        # Detect faces
        detector = FaceDetector(model=current_app.config.get('FACE_DETECTION_MODEL', 'hog'))
        face_locations = detector.detect_faces(image_data)
        
        if len(face_locations) == 0:
            log_system_event('WARNING', 'Check-in attempt with no face detected')
            return jsonify({'error': 'No face detected in the image'}), 400
        
        # Encode the first detected face
        encoder = FaceEncoder(model=current_app.config.get('FACE_ENCODING_MODEL', 'large'))
        encodings = encoder.encode_face(image_data, face_locations)
        
        if not encodings:
            log_system_event('ERROR', 'Failed to encode face during check-in')
            return jsonify({'error': 'Failed to encode face'}), 500
        
        # Load known faces from database
        users_with_faces = User.query.filter(
            User.face_encoding.isnot(None),
            User.is_active == True
        ).all()
        
        if not users_with_faces:
            return jsonify({'error': 'No registered faces in the system'}), 400
        
        # Initialize recognizer with known faces
        tolerance = current_app.config.get('FACE_RECOGNITION_TOLERANCE', 0.6)
        recognizer = FaceRecognizer(tolerance=tolerance)
        recognizer.load_known_faces_from_db(users_with_faces)
        
        # Recognize the face
        user_id, confidence = recognizer.recognize(encodings[0])
        
        if user_id is None:
            log_system_event('WARNING', 'Check-in attempt with unknown face')
            return jsonify({
                'success': False,
                'message': 'Face not recognized'
            }), 401
        
        # Get the user
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check cooldown
        cooldown = current_app.config.get('CHECK_IN_COOLDOWN', 60)
        last_checkin = CheckIn.query.filter_by(user_id=user_id).order_by(
            CheckIn.check_in_time.desc()
        ).first()
        
        if last_checkin:
            time_diff = datetime.utcnow() - last_checkin.check_in_time
            if time_diff.total_seconds() < cooldown:
                remaining = int(cooldown - time_diff.total_seconds())
                return jsonify({
                    'success': False,
                    'message': f'Please wait {remaining} seconds before checking in again',
                    'user': user.to_dict(),
                    'last_checkin': last_checkin.to_dict()
                }), 429
        
        # Get additional info from request
        location = None
        device_id = None
        if request.is_json:
            data = request.get_json() or {}
            location = data.get('location')
            device_id = data.get('device_id')
        
        # Create check-in record
        checkin = CheckIn(
            user_id=user_id,
            check_in_type='face',
            confidence=confidence,
            location=location,
            device_id=device_id
        )
        
        db.session.add(checkin)
        db.session.commit()
        
        log_system_event(
            'INFO', 
            f'User {user.name} ({user.employee_id}) checked in via face recognition',
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'message': f'Welcome, {user.name}!',
            'user': user.to_dict(),
            'checkin': checkin.to_dict(),
            'confidence': confidence
        })
        
    except Exception as e:
        log_system_event('ERROR', f'Check-in error: {str(e)}')
        return jsonify({'error': f'Check-in failed: {str(e)}'}), 500


@checkin_bp.route('/manual', methods=['POST'])
@login_required
@admin_required
def manual_checkin():
    """Manual check-in by admin."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    
    user = User.query.get_or_404(user_id)
    
    checkin = CheckIn(
        user_id=user_id,
        check_in_type='manual',
        location=data.get('location'),
        device_id=data.get('device_id')
    )
    
    db.session.add(checkin)
    db.session.commit()
    
    log_system_event(
        'INFO',
        f'Manual check-in for {user.name} ({user.employee_id}) by admin {current_user.name}',
        user_id=user_id
    )
    
    return jsonify({
        'success': True,
        'message': f'Manual check-in recorded for {user.name}',
        'checkin': checkin.to_dict()
    })


@checkin_bp.route('/records', methods=['GET'])
@login_required
def get_checkin_records():
    """Get check-in records."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_id = request.args.get('user_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    query = CheckIn.query
    
    # Non-admins can only view their own records
    if not current_user.is_admin:
        query = query.filter(CheckIn.user_id == current_user.id)
    elif user_id:
        query = query.filter(CheckIn.user_id == user_id)
    
    # Date filters
    if date_from:
        try:
            date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(CheckIn.check_in_time >= date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(CheckIn.check_in_time <= date_to)
        except ValueError:
            pass
    
    pagination = query.order_by(CheckIn.check_in_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'records': [record.to_dict() for record in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@checkin_bp.route('/statistics', methods=['GET'])
@login_required
@admin_required
def get_statistics():
    """Get check-in statistics."""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Default to today
    if not date_from:
        date_from = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        except ValueError:
            date_from = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if not date_to:
        date_to = datetime.utcnow()
    else:
        try:
            date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        except ValueError:
            date_to = datetime.utcnow()
    
    # Total check-ins in period
    total_checkins = CheckIn.query.filter(
        CheckIn.check_in_time >= date_from,
        CheckIn.check_in_time <= date_to
    ).count()
    
    # Unique users who checked in
    unique_users = db.session.query(CheckIn.user_id).filter(
        CheckIn.check_in_time >= date_from,
        CheckIn.check_in_time <= date_to
    ).distinct().count()
    
    # Total registered users
    total_users = User.query.filter(User.is_active == True).count()
    
    # Users with registered faces
    users_with_faces = User.query.filter(
        User.face_encoding.isnot(None),
        User.is_active == True
    ).count()
    
    # Check-in types breakdown
    face_checkins = CheckIn.query.filter(
        CheckIn.check_in_time >= date_from,
        CheckIn.check_in_time <= date_to,
        CheckIn.check_in_type == 'face'
    ).count()
    
    manual_checkins = CheckIn.query.filter(
        CheckIn.check_in_time >= date_from,
        CheckIn.check_in_time <= date_to,
        CheckIn.check_in_type == 'manual'
    ).count()
    
    return jsonify({
        'period': {
            'from': date_from.isoformat(),
            'to': date_to.isoformat()
        },
        'total_checkins': total_checkins,
        'unique_users_checked_in': unique_users,
        'total_active_users': total_users,
        'users_with_faces': users_with_faces,
        'attendance_rate': round(unique_users / total_users * 100, 2) if total_users > 0 else 0,
        'checkin_types': {
            'face': face_checkins,
            'manual': manual_checkins
        }
    })


@checkin_bp.route('/today', methods=['GET'])
@login_required
def get_today_checkins():
    """Get today's check-ins for the current user."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = CheckIn.query.filter(
        CheckIn.check_in_time >= today_start
    )
    
    if not current_user.is_admin:
        query = query.filter(CheckIn.user_id == current_user.id)
    
    checkins = query.order_by(CheckIn.check_in_time.desc()).all()
    
    return jsonify({
        'date': today_start.date().isoformat(),
        'records': [checkin.to_dict() for checkin in checkins],
        'count': len(checkins)
    })
