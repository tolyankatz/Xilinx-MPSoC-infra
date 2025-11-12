#!/bin/bash
# BSP Manifest Test Execution Script
# This script demonstrates how to run the ZCU102 test framework with the BSP manifest

echo "============================================"
echo "ZCU102 BSP Validation with Manifest"
echo "============================================"

# Set up Python environment
echo "Setting up Python environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r test_host/requirements.txt

# Run the BSP manifest integration demonstration
echo ""
echo "Running BSP manifest integration demonstration..."
python test_bsp_manifest.py

# Run actual tests with BSP manifest (using mock hardware)
echo ""
echo "Running test suite with BSP manifest..."
python test_host/run_tests.py \
    --config test_host/config.yaml \
    --manifest artifacts/bsp-main-137.yaml \
    --test-suite smoke \
    --mock-hardware \
    --verbose \
    --pytest-args -v --tb=short

echo ""
echo "============================================"
echo "Test execution completed!"
echo "Check the logs for detailed results."
echo "============================================"
