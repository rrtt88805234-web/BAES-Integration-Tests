@echo off
REM Local CI/CD Pipeline Verification Script (Windows)
REM Run this before pushing to verify all CI checks will pass

setlocal enabledelayedexpansion

echo ================================================
echo M1 -^> M2a Integration Tests - Local CI Pipeline
echo ================================================
echo.

REM Step 1: Check Python version
echo [1/6] Checking Python version...
python --version
echo.

REM Step 2: Install dependencies
echo [2/6] Installing test dependencies...
pip install -q -r requirements-test.txt
if errorlevel 1 (
    echo Failed to install dependencies
    exit /b 1
)
echo Dependencies installed
echo.

REM Step 3: Run verification tests
echo [3/6] Running framework verification tests...
python verify_integration_tests.py
if errorlevel 1 (
    echo Framework verification failed
    exit /b 1
)
echo Framework verification passed
echo.

REM Step 4: Run integration tests with coverage
echo [4/6] Running integration tests with coverage...
pytest tests/integration/ ^
    --cov=runtime ^
    --cov=tests ^
    --cov-report=term-missing:skip-covered ^
    --cov-report=html ^
    --cov-branch ^
    -v
if errorlevel 1 (
    echo Integration tests failed
    exit /b 1
)
echo Integration tests passed
echo.

REM Step 5: Coverage report
echo [5/6] Generating coverage report...
coverage report --skip-covered
echo Coverage report generated in htmlcov/index.html
echo.

REM Step 6: Display summary
echo [6/6] CI Pipeline Summary
echo ================================================
echo ✓ All CI checks passed successfully!
echo ================================================
echo.
echo You can now push your changes with confidence.
echo.
echo Generated artifacts:
echo - htmlcov/index.html (Coverage report)
echo - .coverage (Coverage data)
echo.

endlocal
