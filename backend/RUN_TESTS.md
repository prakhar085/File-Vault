# Running Tests

This document provides instructions for running the test suite for the File Vault application.

## Prerequisites

- Docker and Docker Compose (for Option 1)
- Python 3.9+ and virtual environment (for Option 2)

---

## Option 1: Docker (Recommended)

### Quick Start

**Start Docker containers:**
```bash
docker-compose up -d
```

**Run all tests:**
```bash
docker-compose exec backend python manage.py test --verbosity=2
```

**View test summary:**
The test output will show:
```
----------------------------------------------------------------------
Ran 44 tests in 2.960s

OK
```

You'll see:
- **Test count**: Number of tests executed (e.g., "44 tests")
- **Execution time**: How long tests took (e.g., "2.960s")
- **Status**: "OK" (all passed) or "FAILED (failures=X, errors=Y)"

**Run specific test class:**
```bash
docker-compose exec backend python manage.py test files.tests.APIViewTestCase
```

**Run specific test:**
```bash
docker-compose exec backend python manage.py test files.tests.APIViewTestCase.test_upload_file_success
```

### Expected Output

When all tests pass, you should see:
```
----------------------------------------------------------------------
Ran 44 tests in 2.8s

OK
```

**Test Summary Format:**
- `Ran X tests in Y.Ys` - Total number of tests executed and execution time
- `OK` - All tests passed
- If tests fail: `FAILED (failures=X, errors=Y)` - Number of failures and errors

---

## Option 2: Virtual Environment

### Setup

**Create and activate virtual environment:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Install dependencies:**
```bash
pip install -r requirements.txt
```

### Quick Start (Using Script)

The script automatically displays test statistics:
```bash
cd backend
./run_tests.sh 2
```

**Output includes:**
- Test execution details
- **TEST SUMMARY** section with:
  - Number of tests executed
  - Execution time
  - Pass/Fail status
  - Failures and errors count (if any)
  - **List of failed test names** (if any tests fail)

### Manual Steps

```bash
cd backend
source venv/bin/activate  # PYTHONPATH is automatically set
python3 manage.py test --verbosity=2
deactivate
```

**Run specific test class:**
```bash
python3 manage.py test files.tests.APIViewTestCase
```

**Run specific test:**
```bash
python3 manage.py test files.tests.APIViewTestCase.test_upload_file_success
```

### Expected Output

When all tests pass:
```
----------------------------------------------------------------------
Ran 44 tests in 2.6s

OK
```

**Test Summary:**
- Successful: `Ran 44 tests in X.Xs` followed by `OK`
- Failed: `FAILED (failures=N, errors=M)` with details of failed tests

---

## Test Coverage

The test suite includes:

- **Model Tests**: File and UserStats models
- **Service Tests**: Upload, Delete, Search, Stats services
- **API Tests**: All REST API endpoints
- **Middleware Tests**: UserId header validation
- **Rate Limiting Tests**: Throttling functionality
- **Edge Cases**: Quota limits, file sizes, deduplication

**Total Tests**: 44

---

## Troubleshooting

### Error: "service 'backend' is not running"
**Solution:**
- Start Docker first: `docker-compose up -d`
- Verify container is running: `docker-compose ps`

### Error: "index idx_user_filename_search already exists"
**Solution:**
- Remove duplicate migration: 
  ```bash
  docker-compose exec backend rm -f /app/files/migrations/0002_optimize_indexes.py
  ```
- Reset database: 
  ```bash
  docker-compose exec backend rm -f /app/data/db.sqlite3
  docker-compose exec backend python manage.py migrate
  ```

### Error: "ModuleNotFoundError: No module named 'django'"
**Solution:**
- Make sure you're in the `backend` directory
- Activate the virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`

### Tests are slow or timing out
**Solution:**
- Use `--verbosity=1` for faster output
- Check if rate limiting is affecting test execution
- Ensure database is properly configured

---

## Test Output Examples

### Successful Test Run
```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
test_upload_file_success (files.tests.APIViewTestCase) ... ok
test_delete_file_success (files.tests.APIViewTestCase) ... ok
...
----------------------------------------------------------------------
Ran 44 tests in 2.882s

OK
Destroying test database for alias 'default'...
```

### Failed Test Run
```
test_upload_file_success (files.tests.APIViewTestCase) ... FAIL
test_delete_file_success (files.tests.APIViewTestCase) ... ok
...
======================================================================
FAIL: test_upload_file_success (files.tests.APIViewTestCase)
----------------------------------------------------------------------
Traceback (most recent call last):
  ...
AssertionError: ...

----------------------------------------------------------------------
Ran 44 tests in 2.900s

FAILED (failures=1, errors=0)

==========================================
TEST SUMMARY
==========================================
✗ Tests failed!
  Tests executed: 44
  Execution time: 2.900s
  Failures: 1
  Errors: 0
  Status: FAILED

Failed Tests:
----------------------------------------
  - files.tests.APIViewTestCase.test_upload_file_success
----------------------------------------
```

---

## Notes

- Test database is created automatically and destroyed after tests complete
- Tests run in isolation - each test starts with a clean database state
- Rate limiting tests may need delays between requests
- All tests should pass before deploying to production
