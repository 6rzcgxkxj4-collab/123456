"""
Authentication API routes.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from src.models import db, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    employee_id = data.get('employee_id')
    password = data.get('password')
    
    if not employee_id or not password:
        return jsonify({'error': 'Employee ID and password are required'}), 400
    
    user = User.query.filter_by(employee_id=employee_id).first()
    
    if user is None or not user.check_password(password):
        return jsonify({'error': 'Invalid employee ID or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 403
    
    login_user(user)
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """User logout endpoint."""
    logout_user()
    return jsonify({'message': 'Logout successful'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user information."""
    return jsonify({
        'user': current_user.to_dict()
    })


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'Old and new passwords are required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    if not current_user.check_password(old_password):
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'})
