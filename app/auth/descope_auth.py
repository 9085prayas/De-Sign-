from functools import wraps
from flask import request, jsonify, g
import os
from descope import DescopeClient, AuthException
import jwt
import requests

class DescopeAuth:
    """Real Descope authentication handler"""
    
    def __init__(self):
        # Load from environment
        self.project_id = os.getenv('DESCOPE_PROJECT_ID')
        self.management_key = os.getenv('DESCOPE_MANAGEMENT_KEY')
        
        if not self.project_id:
            print("WARNING: DESCOPE_PROJECT_ID not found in environment")
            # Fallback to mock mode
            self.mock_mode = True
            self._init_mock_mode()
            return
        
        try:
            self.descope_client = DescopeClient(project_id=self.project_id)
            self.mock_mode = False
            print(f"Descope client initialized with project ID: {self.project_id[:10]}...")
        except Exception as e:
            print(f"Failed to initialize Descope client: {e}")
            print("Falling back to mock mode")
            self.mock_mode = True
            self._init_mock_mode()
        
        # Define permissions for different workflow stages
        self.permissions = {
            'upload_file': ['user', 'admin', 'processor'],
            'approve_processing': ['admin', 'approver'],
            'schedule_meeting': ['admin', 'scheduler', 'processor'],
            'view_status': ['user', 'admin', 'processor', 'approver', 'scheduler']
        }
    
    def _init_mock_mode(self):
        """Initialize mock mode for testing"""
        self.permissions = {
            'upload_file': ['user', 'admin', 'processor'],
            'approve_processing': ['admin', 'approver'],
            'schedule_meeting': ['admin', 'scheduler', 'processor'],
            'view_status': ['user', 'admin', 'processor', 'approver', 'scheduler']
        }
        print("Mock authentication mode enabled")
    
    def authenticate_token(self, token: str):
        """Validate JWT token with Descope or mock"""
        if self.mock_mode:
            return self._mock_authenticate_token(token)
        
        try:
            # For current Descope Python SDK
            jwt_response = self.descope_client.validate_session(token)
            print(f"Token validated successfully for user: {jwt_response.get('sub', 'unknown')}")
            return jwt_response
        except AuthException as e:
            print(f"Authentication failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected authentication error: {e}")
            return None

    
    def _mock_authenticate_token(self, token: str):
        """Mock token validation for testing"""
        # Accept specific test tokens
        valid_test_tokens = {
            'test-token': {
                'sub': 'test-user-123',
                'email': 'test@example.com',
                'roles': ['admin', 'user'],
                'permissions': ['all']
            },
            'user-token': {
                'sub': 'user-456',
                'email': 'user@example.com',
                'roles': ['user'],
                'permissions': ['limited']
            },
            'admin-token': {
                'sub': 'admin-789',
                'email': 'admin@example.com',
                'roles': ['admin', 'user', 'approver', 'scheduler'],
                'permissions': ['all']
            }
        }
        
        return valid_test_tokens.get(token)
    
    def check_permission(self, user_roles: list, required_permission: str) -> bool:
        """Check if user has required permission"""
        if not user_roles:
            return False
        
        # Admin can do everything
        if 'admin' in user_roles:
            return True
            
        allowed_roles = self.permissions.get(required_permission, [])
        return any(role in allowed_roles for role in user_roles)
    
    def get_user_info(self, token: str):
        """Get user information from token"""
        try:
            jwt_response = self.authenticate_token(token)
            if jwt_response:
                return {
                    'user_id': jwt_response.get('sub'),
                    'email': jwt_response.get('email'),
                    'roles': jwt_response.get('roles', []),
                    'permissions': jwt_response.get('permissions', []),
                    'tenant': jwt_response.get('tenant'),
                    'auth_mode': 'mock' if self.mock_mode else 'descope'
                }
            return None
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None

def require_auth(permission=None):
    """Decorator to require authentication and optional permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                return jsonify({'error': 'Missing authorization header'}), 401
            
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Invalid authorization header format. Use: Bearer <token>'}), 401
            
            token = auth_header.split(' ')[1]
            
            # Initialize auth handler
            auth_handler = DescopeAuth()
            
            # Validate token
            user_info = auth_handler.get_user_info(token)
            if not user_info:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Check permission if required
            if permission:
                user_roles = user_info.get('roles', [])
                if not auth_handler.check_permission(user_roles, permission):
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'required_permission': permission,
                        'user_roles': user_roles
                    }), 403
            
            # Store user info in g for access in route
            g.current_user = user_info
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
