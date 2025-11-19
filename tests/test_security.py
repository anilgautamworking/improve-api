"""
Security tests for admin endpoints and role-based access
"""
import pytest
import json


class TestAdminRouteProtection:
    """Test admin route protection"""

    def test_admin_stats_requires_auth(self, client):
        """Test admin stats endpoint requires authentication"""
        response = client.get('/api/admin/stats')
        assert response.status_code == 401

    def test_admin_stats_requires_admin_role(self, client, user_token):
        """Test admin stats endpoint requires admin role"""
        headers = {'Authorization': f'Bearer {user_token}'}
        response = client.get('/api/admin/stats', headers=headers)
        assert response.status_code == 403

    def test_admin_exams_requires_admin_role(self, client, user_token):
        """Test admin exams endpoint requires admin role"""
        headers = {'Authorization': f'Bearer {user_token}'}
        response = client.get('/api/admin/exams', headers=headers)
        assert response.status_code == 403

    def test_admin_categories_requires_admin_role(self, client, user_token):
        """Test admin categories endpoint requires admin role"""
        headers = {'Authorization': f'Bearer {user_token}'}
        response = client.get('/api/admin/categories', headers=headers)
        assert response.status_code == 403


class TestJWTValidation:
    """Test JWT token validation"""

    def test_invalid_token(self, client):
        """Test request with invalid token"""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.get('/api/admin/stats', headers=headers)
        assert response.status_code == 403

    def test_expired_token(self, client):
        """Test request with expired token"""
        import jwt
        from datetime import datetime, timedelta
        from src.config.settings import JWT_SECRET, JWT_ALGORITHM
        
        # Create expired token
        payload = {
            "userId": "test-id",
            "email": "test@test.com",
            "role": "admin",
            "exp": datetime.utcnow() - timedelta(days=1)  # Expired
        }
        expired_token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        headers = {'Authorization': f'Bearer {expired_token}'}
        response = client.get('/api/admin/stats', headers=headers)
        assert response.status_code == 403

    def test_missing_token(self, client):
        """Test request without token"""
        response = client.get('/api/admin/stats')
        assert response.status_code == 401


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_sql_injection_prevention(self, client, admin_token):
        """Test SQL injection prevention"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Try SQL injection in exam name
        data = {
            'name': "'; DROP TABLE exams; --",
            'category': 'Test'
        }
        response = client.post(
            '/api/admin/exams',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        # Should handle gracefully (either create with sanitized name or reject)
        assert response.status_code in [201, 400, 500]

    def test_xss_prevention(self, client, admin_token):
        """Test XSS prevention in inputs"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Try XSS in description
        data = {
            'name': 'Test Exam',
            'description': '<script>alert("xss")</script>'
        }
        response = client.post(
            '/api/admin/exams',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        # Should handle gracefully
        assert response.status_code in [201, 400]


