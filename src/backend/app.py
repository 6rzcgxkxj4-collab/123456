"""
Flask application with RESTful API endpoints for the Face Recognition Attendance System.
"""

import base64
import io
import logging
import os
from datetime import datetime, date, timezone

import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config.config import config
from src.backend.db_service import db_service
from src.backend.user_service import user_service
from src.backend.attendance_service import attendance_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, static_folder='../../src/frontend/static', template_folder='../../src/frontend/templates')
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH  # Configurable, default 5MB

# Enable CORS
CORS(app)

# Initialize database
db_service.create_tables()

# Create upload directories
os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.FACE_IMAGES_FOLDER, exist_ok=True)


def decode_image(image_data: str) -> np.ndarray:
    """
    Decode base64 image data to numpy array.
    
    Args:
        image_data: Base64-encoded image string, optionally with data URL prefix.
    
    Returns:
        Decoded image as numpy array, or None if decoding fails.
    
    Raises:
        ValueError: If the base64 data is invalid.
    """
    try:
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            logger.error("Failed to decode image: cv2.imdecode returned None")
            return None
        
        return image
    except (base64.binascii.Error, ValueError) as e:
        logger.error(f"Failed to decode base64 image data: {e}")
        raise ValueError(f"Invalid base64 image data: {e}")


def save_face_image(image: np.ndarray, user_id: int, filename: str = None) -> str:
    """Save face image and return the file path."""
    if filename is None:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        filename = f"user_{user_id}_{timestamp}.jpg"
    
    filepath = os.path.join(config.FACE_IMAGES_FOLDER, filename)
    cv2.imwrite(filepath, image)
    return filepath


# =============================================================================
# Frontend Routes
# =============================================================================

@app.route('/')
def index():
    """Serve the main frontend page."""
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files."""
    return send_from_directory(app.static_folder, filename)


# =============================================================================
# Health Check Endpoints
# =============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


# =============================================================================
# User Management Endpoints
# =============================================================================

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users."""
    try:
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        users = user_service.get_all_users(active_only=active_only)
        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users]
        })
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user by ID."""
    try:
        user = user_service.get_user_by_id(user_id)
        if user:
            return jsonify({
                'success': True,
                'data': user.to_dict()
            })
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user."""
    try:
        data = request.get_json()
        
        if not data.get('employee_id') or not data.get('name'):
            return jsonify({
                'success': False,
                'error': 'employee_id and name are required'
            }), 400
        
        user = user_service.create_user(
            employee_id=data['employee_id'],
            name=data['name'],
            email=data.get('email'),
            department=data.get('department')
        )
        
        return jsonify({
            'success': True,
            'data': user.to_dict(),
            'message': 'User created successfully'
        }), 201
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update a user."""
    try:
        data = request.get_json()
        
        user = user_service.update_user(
            user_id=user_id,
            name=data.get('name'),
            email=data.get('email'),
            department=data.get('department'),
            is_active=data.get('is_active')
        )
        
        if user:
            return jsonify({
                'success': True,
                'data': user.to_dict(),
                'message': 'User updated successfully'
            })
        return jsonify({'success': False, 'error': 'User not found'}), 404
        
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user."""
    try:
        success = user_service.delete_user(user_id)
        if success:
            return jsonify({
                'success': True,
                'message': 'User deleted successfully'
            })
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# Face Registration Endpoints
# =============================================================================

@app.route('/api/users/<int:user_id>/face', methods=['POST'])
def register_face(user_id):
    """Register a face for a user."""
    try:
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({
                'success': False,
                'error': 'image data is required'
            }), 400
        
        # Decode image
        image = decode_image(data['image'])
        if image is None:
            return jsonify({
                'success': False,
                'error': 'Invalid image data'
            }), 400
        
        # Save face image
        image_path = save_face_image(image, user_id)
        
        # Register face
        face_encoding = user_service.register_face(
            user_id=user_id,
            face_image=image,
            image_path=image_path
        )
        
        if face_encoding:
            return jsonify({
                'success': True,
                'message': 'Face registered successfully',
                'data': {
                    'encoding_id': face_encoding.id,
                    'image_path': image_path
                }
            }), 201
        
        return jsonify({
            'success': False,
            'error': 'Failed to register face. No face detected or user not found.'
        }), 400
        
    except Exception as e:
        logger.error(f"Error registering face: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/face/recognize', methods=['POST'])
def recognize_face():
    """Recognize a face and return the matching user."""
    try:
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({
                'success': False,
                'error': 'image data is required'
            }), 400
        
        # Decode image
        image = decode_image(data['image'])
        if image is None:
            return jsonify({
                'success': False,
                'error': 'Invalid image data'
            }), 400
        
        # Recognize face
        result = user_service.recognize_face(image)
        
        if result:
            user, confidence = result
            return jsonify({
                'success': True,
                'data': {
                    'user': user.to_dict(),
                    'confidence': confidence
                }
            })
        
        return jsonify({
            'success': False,
            'error': 'Face not recognized'
        }), 404
        
    except Exception as e:
        logger.error(f"Error recognizing face: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# Attendance Endpoints
# =============================================================================

@app.route('/api/attendance/check-in', methods=['POST'])
def check_in():
    """Process check-in using face recognition."""
    try:
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({
                'success': False,
                'error': 'image data is required'
            }), 400
        
        # Decode image
        image = decode_image(data['image'])
        if image is None:
            return jsonify({
                'success': False,
                'error': 'Invalid image data'
            }), 400
        
        # Process check-in
        result = attendance_service.check_in(
            face_image=image,
            location=data.get('location'),
            device_id=data.get('device_id')
        )
        
        if result:
            record, user, confidence = result
            return jsonify({
                'success': True,
                'message': f'Check-in successful for {user.name}',
                'data': {
                    'attendance': record.to_dict(),
                    'user': user.to_dict(),
                    'confidence': confidence
                }
            })
        
        return jsonify({
            'success': False,
            'error': 'Face not recognized. Please register first.'
        }), 404
        
    except Exception as e:
        logger.error(f"Error during check-in: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/check-out', methods=['POST'])
def check_out():
    """Process check-out using face recognition."""
    try:
        data = request.get_json()
        
        if not data.get('image'):
            return jsonify({
                'success': False,
                'error': 'image data is required'
            }), 400
        
        # Decode image
        image = decode_image(data['image'])
        if image is None:
            return jsonify({
                'success': False,
                'error': 'Invalid image data'
            }), 400
        
        # Process check-out
        result = attendance_service.check_out(
            face_image=image,
            location=data.get('location'),
            device_id=data.get('device_id')
        )
        
        if result:
            record, user, confidence = result
            return jsonify({
                'success': True,
                'message': f'Check-out successful for {user.name}',
                'data': {
                    'attendance': record.to_dict(),
                    'user': user.to_dict(),
                    'confidence': confidence
                }
            })
        
        return jsonify({
            'success': False,
            'error': 'No check-in record found or face not recognized.'
        }), 404
        
    except Exception as e:
        logger.error(f"Error during check-out: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance', methods=['GET'])
def get_attendance():
    """Get attendance records."""
    try:
        # Parse query parameters
        user_id = request.args.get('user_id', type=int)
        date_str = request.args.get('date')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if user_id:
            # Get attendance for specific user
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
            
            records = attendance_service.get_attendance_by_user(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
        elif date_str:
            # Get attendance for specific date
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            records = attendance_service.get_attendance_by_date(target_date)
        else:
            # Get today's attendance
            records = attendance_service.get_attendance_by_date()
        
        return jsonify({
            'success': True,
            'data': [record.to_dict() for record in records]
        })
        
    except Exception as e:
        logger.error(f"Error getting attendance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/statistics', methods=['GET'])
def get_attendance_statistics():
    """Get attendance statistics for a date range."""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({
                'success': False,
                'error': 'start_date and end_date are required'
            }), 400
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        statistics = attendance_service.get_attendance_statistics(start_date, end_date)
        
        return jsonify({
            'success': True,
            'data': statistics
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/manual/check-in', methods=['POST'])
def manual_check_in():
    """Manually create a check-in record."""
    try:
        data = request.get_json()
        
        if not data.get('user_id'):
            return jsonify({
                'success': False,
                'error': 'user_id is required'
            }), 400
        
        check_in_time = None
        if data.get('check_in_time'):
            check_in_time = datetime.fromisoformat(data['check_in_time'])
        
        record = attendance_service.manual_check_in(
            user_id=data['user_id'],
            check_in_time=check_in_time,
            location=data.get('location'),
            device_id=data.get('device_id')
        )
        
        return jsonify({
            'success': True,
            'message': 'Manual check-in created successfully',
            'data': record.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating manual check-in: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/attendance/manual/check-out/<int:record_id>', methods=['PUT'])
def manual_check_out(record_id):
    """Manually update a check-out time."""
    try:
        data = request.get_json() or {}
        
        check_out_time = None
        if data.get('check_out_time'):
            check_out_time = datetime.fromisoformat(data['check_out_time'])
        
        record = attendance_service.manual_check_out(
            record_id=record_id,
            check_out_time=check_out_time
        )
        
        if record:
            return jsonify({
                'success': True,
                'message': 'Manual check-out updated successfully',
                'data': record.to_dict()
            })
        
        return jsonify({
            'success': False,
            'error': 'Attendance record not found'
        }), 404
        
    except Exception as e:
        logger.error(f"Error updating manual check-out: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# TensorFlow Serving Status Endpoint
# =============================================================================

@app.route('/api/model/status', methods=['GET'])
def get_model_status():
    """Get TensorFlow Serving model status."""
    try:
        from src.backend.tf_serving_client import tf_serving_client
        status = tf_serving_client.get_model_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    app.run(
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        debug=config.DEBUG
    )
