"""
Full stack integration test

Tests the complete flow from Flask API to database
"""

import sys
import os
import requests
import json

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.logger import setup_logging
import logging

setup_logging()
logger = logging.getLogger('test_full_stack')

API_URL = 'http://localhost:3001/api'

def test_health_check():
    """Test API health check"""
    logger.info("Testing health check...")
    try:
        response = requests.get('http://localhost:3001/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        logger.info("✓ Health check passed")
        return True
    except Exception as e:
        logger.error(f"✗ Health check failed: {str(e)}")
        return False

def test_signup():
    """Test user signup"""
    logger.info("\nTesting signup...")
    try:
        # Generate unique email
        email = f"test_{int(os.urandom(4).hex(), 16)}@example.com"
        password = "testpass123"
        
        response = requests.post(f'{API_URL}/auth/signup', json={
            'email': email,
            'password': password
        })
        
        assert response.status_code == 201
        data = response.json()
        assert 'user' in data
        assert 'token' in data
        assert data['user']['email'] == email
        
        logger.info(f"✓ Signup successful: {email}")
        return data['token'], data['user']['id']
    except Exception as e:
        logger.error(f"✗ Signup failed: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response: {e.response.text}")
        return None, None

def test_login(email, password):
    """Test user login"""
    logger.info("\nTesting login...")
    try:
        response = requests.post(f'{API_URL}/auth/login', json={
            'email': email,
            'password': password
        })
        
        assert response.status_code == 200
        data = response.json()
        assert 'token' in data
        
        logger.info(f"✓ Login successful")
        return data['token']
    except Exception as e:
        logger.error(f"✗ Login failed: {str(e)}")
        return None

def test_categories(token):
    """Test categories endpoint"""
    logger.info("\nTesting categories...")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{API_URL}/categories', headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'categories' in data
        categories = data['categories']
        
        logger.info(f"✓ Categories fetched: {len(categories)} categories")
        for cat in categories:
            logger.info(f"  - {cat['name']}: {cat['question_count']} questions")
        
        return True
    except Exception as e:
        logger.error(f"✗ Categories test failed: {str(e)}")
        return False

def test_questions(token, category='Economy'):
    """Test question generation"""
    logger.info(f"\nTesting question generation (category: {category})...")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{API_URL}/questions/generate', 
                                headers=headers,
                                json={'category': category, 'count': 2})
        
        assert response.status_code == 200
        data = response.json()
        assert 'questions' in data
        questions = data['questions']
        
        logger.info(f"✓ Questions fetched: {len(questions)} questions")
        
        if questions:
            q = questions[0]
            logger.info("\n  Sample question:")
            logger.info(f"    Q: {q['question_text'][:80]}...")
            logger.info(f"    A: {q['option_a'][:40]}...")
            logger.info(f"    B: {q['option_b'][:40]}...")
            logger.info(f"    C: {q['option_c'][:40]}...")
            logger.info(f"    D: {q['option_d'][:40]}...")
            logger.info(f"    Correct: {q['correct_answer'].upper()}")
            logger.info(f"    Difficulty: {q['difficulty']}")
            logger.info(f"    Points: {q['points']}")
            
            return questions
        
        return []
    except Exception as e:
        logger.error(f"✗ Questions test failed: {str(e)}")
        if hasattr(e, 'response'):
            logger.error(f"Response: {e.response.text}")
        return []

def test_save_answer(token, question_id):
    """Test saving answer"""
    logger.info(f"\nTesting save answer...")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{API_URL}/answers',
                                headers=headers,
                                json={
                                    'question_id': question_id,
                                    'selected_answer': 'a',
                                    'is_correct': True
                                })
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        
        logger.info(f"✓ Answer saved successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Save answer failed: {str(e)}")
        return False

def test_correct_answers(token):
    """Test get correct answers"""
    logger.info("\nTesting get correct answers...")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{API_URL}/answers/correct', headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'correctAnswers' in data
        
        logger.info(f"✓ Correct answers fetched: {len(data['correctAnswers'])} questions")
        return True
    except Exception as e:
        logger.error(f"✗ Correct answers test failed: {str(e)}")
        return False

def test_stats(token):
    """Test user statistics"""
    logger.info("\nTesting user statistics...")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(f'{API_URL}/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert 'totalAnswered' in data
        assert 'correctAnswers' in data
        assert 'wrongAnswers' in data
        
        logger.info(f"✓ Stats fetched:")
        logger.info(f"    Total: {data['totalAnswered']}")
        logger.info(f"    Correct: {data['correctAnswers']}")
        logger.info(f"    Wrong: {data['wrongAnswers']}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Stats test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    logger.info("=" * 80)
    logger.info("Full Stack Integration Test")
    logger.info("=" * 80)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Health check
    tests_total += 1
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Signup
    tests_total += 1
    token, user_id = test_signup()
    if token:
        tests_passed += 1
    else:
        logger.error("Cannot continue without token")
        return 1
    
    # Test 3: Categories
    tests_total += 1
    if test_categories(token):
        tests_passed += 1
    
    # Test 4: Questions
    tests_total += 1
    questions = test_questions(token, category='Economy')
    if questions:
        tests_passed += 1
    
    # Test 5: Save answer
    if questions:
        tests_total += 1
        if test_save_answer(token, questions[0]['id']):
            tests_passed += 1
    
    # Test 6: Correct answers
    tests_total += 1
    if test_correct_answers(token):
        tests_passed += 1
    
    # Test 7: Stats
    tests_total += 1
    if test_stats(token):
        tests_passed += 1
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("Test Summary")
    logger.info("=" * 80)
    logger.info(f"Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        logger.info("\n✓ All tests passed! Full stack is working correctly.")
        logger.info("\nFrontend should be ready at: http://localhost:5173")
        logger.info("Admin dashboard at: http://localhost:3001")
        return 0
    else:
        logger.error(f"\n✗ {tests_total - tests_passed} test(s) failed")
        return 1

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)

