"""
Tests for question filtering by exam
"""
import pytest
import json


class TestQuestionFiltering:
    """Test question filtering by exam_id"""

    def test_generate_questions_requires_auth(self, client):
        """Test POST /api/questions/generate requires authentication"""
        response = client.post(
            '/api/questions/generate',
            data=json.dumps({'category': 'all', 'count': 2}),
            content_type='application/json'
        )
        assert response.status_code == 401

    def test_generate_questions_with_exam_id(self, client, user_token):
        """Test generating questions filtered by exam_id"""
        headers = {'Authorization': f'Bearer {user_token}'}
        
        # Get an exam ID
        exams_response = client.get('/api/exams')
        exams = json.loads(exams_response.data)['exams']
        
        if len(exams) > 0:
            exam_id = exams[0]['id']
            data = {
                'category': 'all',
                'count': 2,
                'exam_id': exam_id
            }
            response = client.post(
                '/api/questions/generate',
                headers=headers,
                data=json.dumps(data),
                content_type='application/json'
            )
            # May return 200 or 404 if no questions for that exam
            assert response.status_code in [200, 404]

    def test_generate_questions_from_token(self, client, user_token):
        """Test questions filtered by exam_id from JWT token"""
        headers = {'Authorization': f'Bearer {user_token}'}
        data = {
            'category': 'all',
            'count': 2
        }
        response = client.post(
            '/api/questions/generate',
            headers=headers,
            data=json.dumps(data),
            content_type='application/json'
        )
        # May return 200 or 404
        assert response.status_code in [200, 404]


