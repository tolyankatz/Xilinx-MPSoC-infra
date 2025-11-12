@echo off
REM BSP Manifest Test Execution Script
REM This script demonstrates how to run the ZCU102 test framework with the BSP manifest

echo ============================================
echo ZCU102 BSP Validation with Manifest
echo ============================================

REM Set up Python environment
echo Setting up Python environment...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

REM Install dependencies
echo Installing dependencies...
pip install -r test_host\requirements.txt

REM Run the BSP manifest integration demonstration
echo.
echo Running BSP manifest integration demonstration...
python test_bsp_manifest.py

REM Run actual tests with BSP manifest (using mock hardware)
echo.
echo Running test suite with BSP manifest...
python test_host\run_tests.py ^
    --config test_host\config.yaml ^
    --manifest artifacts\bsp-main-137.yaml ^
    --test-suite smoke ^
    --mock-hardware ^
    --verbose ^
    --pytest-args -v --tb=short

echo.
echo ============================================
echo Test execution completed!
echo Check the logs for detailed results.
echo ============================================

pause
