"""
Tests for the Facial Recognition Check-in System.
"""
import pytest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.models import db, User, CheckIn


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create test admin user
        admin = User(
            employee_id='test_admin',
            name='Test Admin',
            email='admin@test.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create test regular user
        user = User(
            employee_id='test_user',
            name='Test User',
            email='user@test.com',
            department='Engineering',
            is_admin=False
        )
        user.set_password('user123')
        db.session.add(user)
        
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def auth_admin(client):
    """Authenticate as admin and return client."""
    response = client.post('/api/auth/login', 
        data=json.dumps({
            'employee_id': 'test_admin',
            'password': 'admin123'
        }),
        content_type='application/json'
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def auth_user(client):
    """Authenticate as regular user and return client."""
    response = client.post('/api/auth/login',
        data=json.dumps({
            'employee_id': 'test_user',
            'password': 'user123'
        }),
        content_type='application/json'
    )
    assert response.status_code == 200
    return client


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'facial-recognition-checkin'


class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_login_success(self, client):
        """Test successful login."""
        response = client.post('/api/auth/login',
            data=json.dumps({
                'employee_id': 'test_admin',
                'password': 'admin123'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
        assert data['user']['employee_id'] == 'test_admin'
    
    def test_login_invalid_password(self, client):
        """Test login with invalid password."""
        response = client.post('/api/auth/login',
            data=json.dumps({
                'employee_id': 'test_admin',
                'password': 'wrong_password'
            }),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_login_invalid_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/api/auth/login',
            data=json.dumps({
                'employee_id': 'nonexistent',
                'password': 'password'
            }),
            content_type='application/json'
        )
        assert response.status_code == 401
    
    def test_get_current_user(self, auth_admin):
        """Test getting current user info."""
        response = auth_admin.get('/api/auth/me')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['employee_id'] == 'test_admin'
    
    def test_logout(self, auth_admin):
        """Test logout."""
        response = auth_admin.post('/api/auth/logout')
        assert response.status_code == 200
        
        # After logout, should not be able to access protected route
        response = auth_admin.get('/api/auth/me')
        assert response.status_code == 401


class TestUserManagement:
    """Test user management endpoints."""
    
    def test_list_users_as_admin(self, auth_admin):
        """Test listing users as admin."""
        response = auth_admin.get('/api/users/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'users' in data
        assert len(data['users']) >= 2  # Admin + regular user
    
    def test_list_users_as_regular_user(self, auth_user):
        """Test that regular users cannot list all users."""
        response = auth_user.get('/api/users/')
        assert response.status_code == 403
    
    def test_create_user(self, auth_admin):
        """Test creating a new user."""
        response = auth_admin.post('/api/users/',
            data=json.dumps({
                'employee_id': 'new_user',
                'name': 'New User',
                'email': 'new@test.com',
                'department': 'HR'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['user']['employee_id'] == 'new_user'
        assert data['user']['name'] == 'New User'
    
    def test_create_duplicate_user(self, auth_admin):
        """Test creating a user with duplicate employee_id."""
        response = auth_admin.post('/api/users/',
            data=json.dumps({
                'employee_id': 'test_user',
                'name': 'Duplicate User'
            }),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_get_user(self, auth_admin, app):
        """Test getting a specific user."""
        with app.app_context():
            user = User.query.filter_by(employee_id='test_user').first()
            user_id = user.id
        
        response = auth_admin.get(f'/api/users/{user_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['employee_id'] == 'test_user'
    
    def test_update_user(self, auth_admin, app):
        """Test updating a user."""
        with app.app_context():
            user = User.query.filter_by(employee_id='test_user').first()
            user_id = user.id
        
        response = auth_admin.put(f'/api/users/{user_id}',
            data=json.dumps({
                'name': 'Updated Name',
                'department': 'Marketing'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user']['name'] == 'Updated Name'
        assert data['user']['department'] == 'Marketing'


class TestCheckIn:
    """Test check-in endpoints."""
    
    def test_get_statistics(self, auth_admin):
        """Test getting check-in statistics."""
        response = auth_admin.get('/api/checkin/statistics')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'total_checkins' in data
        assert 'unique_users_checked_in' in data
        assert 'total_active_users' in data
    
    def test_get_today_checkins(self, auth_admin):
        """Test getting today's check-ins."""
        response = auth_admin.get('/api/checkin/today')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'records' in data
        assert 'date' in data
    
    def test_get_checkin_records(self, auth_admin):
        """Test getting check-in records."""
        response = auth_admin.get('/api/checkin/records')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'records' in data
        assert 'total' in data
    
    def test_manual_checkin(self, auth_admin, app):
        """Test manual check-in by admin."""
        with app.app_context():
            user = User.query.filter_by(employee_id='test_user').first()
            user_id = user.id
        
        response = auth_admin.post('/api/checkin/manual',
            data=json.dumps({
                'user_id': user_id,
                'location': 'Office'
            }),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['checkin']['check_in_type'] == 'manual'
    
    def test_face_checkin_no_image(self, client):
        """Test face check-in without image."""
        response = client.post('/api/checkin/face',
            content_type='application/json'
        )
        # Either 400 (no image) or 500 (face_recognition not available) is valid
        assert response.status_code in [400, 500]


class TestPages:
    """Test web pages."""
    
    def test_index_page(self, client):
        """Test index page loads."""
        response = client.get('/')
        assert response.status_code == 200
        assert '面部识别自动签到系统' in response.data.decode('utf-8')
    
    def test_checkin_page(self, client):
        """Test check-in page loads."""
        response = client.get('/checkin')
        assert response.status_code == 200
        assert '面部识别签到' in response.data.decode('utf-8')
    
    def test_admin_page(self, client):
        """Test admin page loads."""
        response = client.get('/admin')
        assert response.status_code == 200
        assert '管理后台' in response.data.decode('utf-8')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
