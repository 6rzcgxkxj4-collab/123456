"""
Facial Recognition Check-in System - Flask Application Factory.
"""
import os
from flask import Flask, render_template, jsonify
from flask_login import LoginManager
from flask_cors import CORS

from config import config
from src.models import db, User


login_manager = LoginManager()


def create_app(config_name=None):
    """
    Create and configure the Flask application.
    
    Args:
        config_name: Configuration name ('development', 'production', 'testing')
        
    Returns:
        Configured Flask application
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    CORS(app)
    
    # Configure login manager
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'error': 'Authentication required'}), 401
    
    # Register blueprints
    from src.api import auth_bp, users_bp, checkin_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(checkin_bp, url_prefix='/api/checkin')
    
    # Register main routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/admin')
    def admin():
        return render_template('admin.html')
    
    @app.route('/checkin')
    def checkin_page():
        return render_template('checkin.html')
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'facial-recognition-checkin'
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500
    
    # Create database tables
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        if not User.query.filter_by(employee_id='admin').first():
            admin_user = User(
                employee_id='admin',
                name='Administrator',
                email='admin@example.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
    
    return app
