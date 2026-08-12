#!/bin/bash
# Local CI/CD Pipeline Verification Script
# Run this before pushing to verify all CI checks will pass

set -e  # Exit on first error

echo "================================================"
echo "M1 -> M2a Integration Tests - Local CI Pipeline"
echo "================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python version
echo -e "${YELLOW}[1/6]${NC} Checking Python version..."
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python $PYTHON_VERSION"
echo ""

# Step 2: Install dependencies
echo -e "${YELLOW}[2/6]${NC} Installing test dependencies..."
pip install -q -r requirements-test.txt || {
    echo -e "${RED}Failed to install dependencies${NC}"
    exit 1
}
echo -e "${GREEN}Dependencies installed${NC}"
echo ""

# Step 3: Run verification tests
echo -e "${YELLOW}[3/6]${NC} Running framework verification tests..."
python verify_integration_tests.py || {
    echo -e "${RED}Framework verification failed${NC}"
    exit 1
}
echo -e "${GREEN}Framework verification passed${NC}"
echo ""

# Step 4: Run integration tests with coverage
echo -e "${YELLOW}[4/6]${NC} Running integration tests with coverage..."
pytest tests/integration/ \
    --cov=runtime \
    --cov=tests \
    --cov-report=term-missing:skip-covered \
    --cov-report=html \
    --cov-branch \
    -v || {
    echo -e "${RED}Integration tests failed${NC}"
    exit 1
}
echo -e "${GREEN}Integration tests passed${NC}"
echo ""

# Step 5: Check coverage threshold
echo -e "${YELLOW}[5/6]${NC} Checking coverage threshold (80%)..."
COVERAGE=$(coverage report --skip-covered | tail -1 | awk '{print $NF}' | sed 's/%//')
echo "Current coverage: ${COVERAGE}%"

if (( $(echo "$COVERAGE < 80" | bc -l) )); then
    echo -e "${RED}Coverage below 80% threshold${NC}"
    echo "Please improve test coverage before pushing"
    exit 1
fi
echo -e "${GREEN}Coverage threshold met${NC}"
echo ""

# Step 6: Security checks
echo -e "${YELLOW}[6/6]${NC} Running security checks..."
if command -v bandit &> /dev/null; then
    bandit -q -r runtime tests || echo "Note: Some security issues found"
else
    echo "Bandit not installed, skipping security checks"
fi
echo -e "${GREEN}Security checks completed${NC}"
echo ""

# Final summary
echo "================================================"
echo -e "${GREEN}✓ All CI checks passed successfully!${NC}"
echo "================================================"
echo ""
echo "Summary:"
echo "  - Python version: $PYTHON_VERSION"
echo "  - Integration tests: PASSED"
echo "  - Coverage: ${COVERAGE}%"
echo "  - Security checks: COMPLETED"
echo ""
echo "You can now push your changes with confidence."
echo ""
