# Test Suite

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_api_exams.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v
```

### Test Structure

- `test_api_exams.py` - Exam endpoint tests
- `test_api_auth.py` - Authentication tests
- `test_api_categories.py` - Category filtering tests
- `test_api_questions.py` - Question filtering tests
- `test_security.py` - Security and RBAC tests

### Test Categories

Tests are marked with pytest markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.security` - Security tests

Run specific category:
```bash
pytest -m security
```

## Frontend Tests

Frontend tests use Vitest and React Testing Library.

```bash
cd ../Dailyquestionbank-frontend
npm install  # Install test dependencies
npm test     # Run tests
npm run test:ui  # Run with UI
npm run test:coverage  # Run with coverage
```

## Integration Tests

Full stack integration tests are in `scripts/test_full_stack.py`:

```bash
python scripts/test_full_stack.py
```


