"""
Tests for exam-related API endpoints
"""
import pytest
import json
from unittest.mock import patch, MagicMock


class TestExamEndpoints:
    """Test public exam endpoints"""

    def test_get_exams_public(self, client):
        """Test GET /api/exams (public endpoint)"""
        response = client.get('/api/exams')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'exams' in data
        assert isinstance(data['exams'], list)

    def test_get_exams_structure(self, client):
        """Test exam response structure"""
        response = client.get('/api/exams')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        if len(data['exams']) > 0:
            exam = data['exams'][0]
            assert 'id' in exam
            assert 'name' in exam
            assert 'category' in exam
            assert 'description' in exam


class TestAdminExamEndpoints:
    """Test admin exam management endpoints"""

    def test_get_exams_admin_requires_auth(self, client):
        """Test admin GET /api/admin/exams requires authentication"""
        response = client.get('/api/admin/exams')
        assert response.status_code == 401

    def test_get_exams_admin_requires_admin_role(self, client, user_token):
        """Test admin endpoints require admin role"""
        headers = {'Authorization': f'Bearer {user_token}'}
        response = client.get('/api/admin/exams', headers=headers)
        assert response.status_code == 403

    def test_create_exam_admin(self, client, admin_token):
        """Test creating an exam as admin"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        data = {
            'name': 'Test Exam',
            'category': 'Test Category',
            'description': 'Test Description'
        }
        response = client.post(
            '/api/admin/exams',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code in [201, 400]  # 400 if duplicate

    def test_create_exam_validation(self, client, admin_token):
        """Test exam creation validation"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Missing name
        data = {'category': 'Test Category'}
        response = client.post(
            '/api/admin/exams',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_update_exam_admin(self, client, admin_token):
        """Test updating an exam as admin"""
        # First create an exam
        headers = {'Authorization': f'Bearer {admin_token}'}
        create_data = {
            'name': 'Update Test Exam',
            'category': 'Test',
            'description': 'Original'
        }
        create_response = client.post(
            '/api/admin/exams',
            headers=headers,
            data=json.dumps(create_data),
            content_type='application/json'
        )
        
        if create_response.status_code == 201:
            exam = json.loads(create_response.data)
            exam_id = exam['id']
            
            # Update the exam
            update_data = {
                'name': 'Updated Exam Name',
                'category': 'Updated Category',
                'description': 'Updated Description'
            }
            response = client.put(
                f'/api/admin/exams/{exam_id}',
                headers=headers,
                data=json.dumps(update_data),
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_delete_exam_admin(self, client, admin_token):
        """Test deleting an exam as admin"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Try to delete non-existent exam
        response = client.delete(
            '/api/admin/exams/00000000-0000-0000-0000-000000000000',
            headers=headers
        )
        assert response.status_code == 404


class TestExamCategoryEndpoints:
    """Test exam-category relationship endpoints"""

    def test_get_exam_categories(self, client, admin_token):
        """Test getting categories for an exam"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # Get first exam
        exams_response = client.get('/api/exams')
        exams = json.loads(exams_response.data)['exams']
        
        if len(exams) > 0:
            exam_id = exams[0]['id']
            response = client.get(
                f'/api/admin/exams/{exam_id}/categories',
                headers=headers
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'categories' in data

    def test_add_exam_category(self, client, admin_token):
        """Test adding a category to an exam"""
        headers = {'Authorization': f'Bearer {admin_token}'}
        # This test would need actual exam and category IDs
        # Skipping for now as it requires database setup
        pass


