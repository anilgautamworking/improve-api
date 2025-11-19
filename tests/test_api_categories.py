"""
Tests for category filtering by exam
"""
import pytest
import json


class TestCategoryFiltering:
    """Test category filtering by exam_id"""

    def test_get_categories_requires_auth(self, client):
        """Test GET /api/categories requires authentication"""
        response = client.get('/api/categories')
        assert response.status_code == 401

    def test_get_categories_with_exam_id(self, client, user_token):
        """Test getting categories filtered by exam_id"""
        headers = {'Authorization': f'Bearer {user_token}'}
        
        # Get an exam ID
        exams_response = client.get('/api/exams')
        exams = json.loads(exams_response.data)['exams']
        
        if len(exams) > 0:
            exam_id = exams[0]['id']
            response = client.get(
                f'/api/categories?exam_id={exam_id}',
                headers=headers
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'categories' in data

    def test_get_categories_from_token(self, client, user_token):
        """Test categories filtered by exam_id from JWT token"""
        headers = {'Authorization': f'Bearer {user_token}'}
        response = client.get('/api/categories', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'categories' in data


class TestAdminCategoryEndpoints:
    """Test admin category management"""

    def test_get_categories_admin(self, client, admin_token):
        """Test admin GET /api/admin/categories"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        response = client.get('/api/admin/categories', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'categories' in data

    def test_create_category_admin(self, client, admin_token):
        """Test creating a category as admin"""
        import time
        headers = {'Authorization': f'Bearer {admin_token}'}
        data = {
            'name': f'Test Category {int(time.time())}',
            'description': 'Test Description'
        }
        response = client.post(
            '/api/admin/categories',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code in [201, 400]  # 400 if duplicate

    def test_create_category_validation(self, client, admin_token):
        """Test category creation validation"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Missing required fields
        data = {'name': 'Test'}
        response = client.post(
            '/api/admin/categories',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400

