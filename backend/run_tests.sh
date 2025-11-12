#!/bin/bash

# Script to run tests in virtual environment with enhanced stats display
# Usage: ./run_tests.sh [verbosity_level]

cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to include venv packages
export PYTHONPATH="$(pwd)/venv/lib/python3.14/site-packages:$PYTHONPATH"

# Set verbosity (default: 1)
VERBOSITY=${1:-1}

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Run tests and capture output
echo "=========================================="
echo "Running Tests (verbosity: $VERBOSITY)..."
echo "=========================================="
echo ""

TEST_OUTPUT=$(python3 manage.py test --verbosity=$VERBOSITY 2>&1)
TEST_EXIT_CODE=$?

# Display test output
echo "$TEST_OUTPUT"

# Extract and highlight test summary
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="

# Extract test count and time using sed (works on both macOS and Linux)
TEST_COUNT=$(echo "$TEST_OUTPUT" | grep "Ran .* test" | sed -E 's/.*Ran ([0-9]+) test.*/\1/' || echo "0")
TEST_TIME=$(echo "$TEST_OUTPUT" | grep "Ran .* test" | sed -E 's/.*Ran [0-9]+ test.*in ([0-9.]+)s.*/\1/' || echo "0")

# Check if tests passed or failed
if echo "$TEST_OUTPUT" | grep -q "^OK$"; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "  Tests executed: ${GREEN}$TEST_COUNT${NC}"
    echo -e "  Execution time: ${GREEN}${TEST_TIME}s${NC}"
    echo -e "  Status: ${GREEN}PASSED${NC}"
elif echo "$TEST_OUTPUT" | grep -q "FAILED"; then
    FAILURES=$(echo "$TEST_OUTPUT" | grep "FAILED" | sed -E 's/.*failures=([0-9]+).*/\1/' || echo "0")
    ERRORS=$(echo "$TEST_OUTPUT" | grep "FAILED" | sed -E 's/.*errors=([0-9]+).*/\1/' || echo "0")
    echo -e "${RED}✗ Tests failed!${NC}"
    echo -e "  Tests executed: $TEST_COUNT"
    echo -e "  Execution time: ${TEST_TIME}s"
    echo -e "  Failures: ${RED}$FAILURES${NC}"
    echo -e "  Errors: ${RED}$ERRORS${NC}"
    echo -e "  Status: ${RED}FAILED${NC}"
    
    # Extract failed test names
    echo ""
    echo "Failed Tests:"
    echo "----------------------------------------"
    
    # Method 1: Extract from lines like "test_name (TestClass) ... FAIL"
    # Format: "test_method_name (files.tests.TestCaseClass) ... FAIL"
    FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -E "\.\.\. (FAIL|ERROR)$" | sed -E 's/^test_([a-zA-Z_]+) \(([^)]+)\)\.\.\. (FAIL|ERROR)$/\2.test_\1/' | sort -u)
    
    # Method 2: If empty, try extracting just test method name
    if [ -z "$FAILED_TESTS" ]; then
        FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -E "\.\.\. (FAIL|ERROR)$" | sed -E 's/.*test_([a-zA-Z_]+).*\.\.\. (FAIL|ERROR)$/test_\1/' | sort -u)
    fi
    
    # Method 3: Extract from FAIL: or ERROR: header lines
    # Format: "FAIL: test_method_name (files.tests.TestCaseClass)"
    if [ -z "$FAILED_TESTS" ]; then
        FAILED_TESTS=$(echo "$TEST_OUTPUT" | grep -E "^(FAIL|ERROR):" | sed -E 's/^(FAIL|ERROR):\s+test_([a-zA-Z_]+)\s+\(([^)]+)\)/\3.test_\2/' | sort -u)
    fi
    
    # Method 4: Extract from traceback sections
    if [ -z "$FAILED_TESTS" ]; then
        FAILED_TESTS=$(echo "$TEST_OUTPUT" | awk '/^FAIL:/,/^---/ {print}' | grep -E "test_[a-zA-Z_]+" | sed -E 's/.*\.(test_[a-zA-Z_]+).*/\1/' | sort -u)
    fi
    
    # Display failed tests with full path
    if [ -n "$FAILED_TESTS" ] && [ "$FAILED_TESTS" != "" ]; then
        echo "$FAILED_TESTS" | while IFS= read -r test_name; do
            if [ -n "$test_name" ]; then
                echo -e "${RED}  - $test_name${NC}"
            fi
        done
    else
        echo -e "${YELLOW}  (Failed test names could not be automatically extracted)${NC}"
        echo -e "${YELLOW}  Check the test output above for details${NC}"
    fi
    echo "----------------------------------------"
else
    echo -e "${YELLOW}⚠ Test execution completed${NC}"
    echo -e "  Tests executed: $TEST_COUNT"
    echo -e "  Execution time: ${TEST_TIME}s"
fi

echo "=========================================="
echo ""

# Deactivate virtual environment
deactivate

exit $TEST_EXIT_CODE

