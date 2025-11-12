#!/bin/bash
# ===================================================================
# ZCU102 BSP Hardware Validation Controller Script
# ===================================================================
# This script is the entry point for hardware validation execution
# Called by Jenkins pipeline via SSH
# -------------------------------------------------------------------

set -euo pipefail  # Exit on error, undefined variables, pipe failures

# --- Script Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="/opt/zcu102-bsp-validation"
PYTHON_VENV="${FRAMEWORK_ROOT}/venv/bin/activate"
TEST_RUNNER="${FRAMEWORK_ROOT}/test_host/run_tests.py"
LOG_DIR="${FRAMEWORK_ROOT}/logs"
RESULTS_DIR="${FRAMEWORK_ROOT}/test-results"
MANIFESTS_DIR="${FRAMEWORK_ROOT}/manifests"
SCREENSHOTS_DIR="${FRAMEWORK_ROOT}/screenshots"

# Create timestamp for this run
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
RUN_ID="hw-test-${TIMESTAMP}"

# --- Logging Setup ---
mkdir -p "${LOG_DIR}/latest" "${RESULTS_DIR}" "${SCREENSHOTS_DIR}"
EXECUTION_LOG="${LOG_DIR}/latest/execution.log"
SUMMARY_LOG="${LOG_DIR}/latest/summary.log"

# Redirect all output to log file while also showing on console
exec > >(tee -a "${EXECUTION_LOG}")
exec 2>&1

# --- Helper Functions ---
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $*"
}

cleanup() {
    local exit_code=$?
    log_info "Cleanup initiated with exit code: ${exit_code}"
    
    # Deactivate virtual environment if active
    if [[ "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    # Generate summary report
    generate_summary_report "${exit_code}"
    
    # Copy logs to timestamped directory
    cp -r "${LOG_DIR}/latest" "${LOG_DIR}/${RUN_ID}" 2>/dev/null || true
    
    log_info "Cleanup completed"
    exit ${exit_code}
}

generate_summary_report() {
    local exit_code=$1
    local status="UNKNOWN"
    
    case ${exit_code} in
        0) status="SUCCESS" ;;
        1) status="FAILURE" ;;
        2) status="VALIDATION_ERROR" ;;
        3) status="DEPLOYMENT_ERROR" ;;
        *) status="UNKNOWN_ERROR" ;;
    esac
    
    cat > "${SUMMARY_LOG}" << EOF
ZCU102 Hardware Validation Summary
=================================
Run ID: ${RUN_ID}
Timestamp: $(date)
Status: ${status}
Exit Code: ${exit_code}

Parameters:
- Manifest Path: ${MANIFEST_PATH:-"not specified"}
- Build ID: ${BUILD_ID:-"not specified"}
- Test Scope: ${TEST_SCOPE:-"not specified"}
- Jenkins Build: ${JENKINS_BUILD:-"not specified"}
- Force Deployment: ${FORCE_DEPLOYMENT:-"false"}

Logs:
- Execution Log: ${EXECUTION_LOG}
- Framework Log: ${LOG_DIR}/latest/framework.log
- Test Results: ${RESULTS_DIR}/

EOF

    if [[ -f "${RESULTS_DIR}/junit.xml" ]]; then
        echo "JUnit Report: Available" >> "${SUMMARY_LOG}"
    fi
    
    if [[ -d "${SCREENSHOTS_DIR}" ]] && [[ $(ls -A "${SCREENSHOTS_DIR}" 2>/dev/null | wc -l) -gt 0 ]]; then
        echo "Screenshots: $(ls -1 "${SCREENSHOTS_DIR}" | wc -l) files captured" >> "${SUMMARY_LOG}"
    fi
}

validate_environment() {
    log_info "Validating execution environment..."
    
    # Check if framework directory exists
    if [[ ! -d "${FRAMEWORK_ROOT}" ]]; then
        log_error "Framework directory not found: ${FRAMEWORK_ROOT}"
        exit 2
    fi
    
    # Check if Python virtual environment exists
    if [[ ! -f "${PYTHON_VENV}" ]]; then
        log_error "Python virtual environment not found: ${PYTHON_VENV}"
        exit 2
    fi
    
    # Check if test runner exists
    if [[ ! -f "${TEST_RUNNER}" ]]; then
        log_error "Test runner not found: ${TEST_RUNNER}"
        exit 2
    fi
    
    # Check if we have necessary hardware access
    if ! groups | grep -q "dialout\|tty"; then
        log_warning "User not in dialout/tty groups - serial access may fail"
    fi
    
    log_info "Environment validation completed"
}

download_manifest() {
    local manifest_path="$1"
    local local_manifest="${MANIFESTS_DIR}/current_manifest.yaml"
    
    log_info "Downloading BSP manifest from: ${manifest_path}"
    
    # Create manifests directory if it doesn't exist
    mkdir -p "${MANIFESTS_DIR}"
    
    # Download manifest from Artifactory
    # In a real implementation, this would use proper Artifactory API/credentials
    if [[ "${manifest_path}" =~ ^https?:// ]]; then
        # HTTP(S) URL - download directly
        if command -v curl >/dev/null; then
            curl -sf -o "${local_manifest}" "${manifest_path}"
        elif command -v wget >/dev/null; then
            wget -q -O "${local_manifest}" "${manifest_path}"
        else
            log_error "Neither curl nor wget available for downloading manifest"
            exit 2
        fi
    else
        # Assume it's a file path in the artifacts directory
        local artifacts_base="${FRAMEWORK_ROOT}/../Xilinx-MPSoC-infra/artifacts"
        if [[ -f "${artifacts_base}/${manifest_path}" ]]; then
            cp "${artifacts_base}/${manifest_path}" "${local_manifest}"
        else
            log_error "Manifest file not found: ${artifacts_base}/${manifest_path}"
            exit 2
        fi
    fi
    
    # Validate manifest file
    if [[ ! -s "${local_manifest}" ]]; then
        log_error "Downloaded manifest is empty or invalid"
        exit 2
    fi
    
    log_info "Manifest downloaded successfully: ${local_manifest}"
    echo "${local_manifest}"
}

execute_tests() {
    local manifest_file="$1"
    local test_scope="$2"
    local force_deployment="$3"
    
    log_info "Starting test execution with manifest: ${manifest_file}"
    log_info "Test scope: ${test_scope}"
    log_info "Force deployment: ${force_deployment}"
    
    # Activate Python virtual environment
    log_info "Activating Python virtual environment..."
    source "${PYTHON_VENV}"
    
    # Change to framework directory
    cd "${FRAMEWORK_ROOT}"
    
    # Prepare test runner arguments
    local test_args=()
    test_args+=("--manifest" "${manifest_file}")
    test_args+=("--log-level" "INFO")
    test_args+=("--output-dir" "${RESULTS_DIR}")
    test_args+=("--run-id" "${RUN_ID}")
    
    # Add test scope
    case "${test_scope}" in
        "smoke")
            test_args+=("--test-suite" "smoke_tests")
            ;;
        "full")
            test_args+=("--test-suite" "full_validation")
            ;;
        "regression")
            test_args+=("--test-suite" "regression")
            ;;
        "security")
            test_args+=("--test-suite" "security_tests")
            ;;
        *)
            log_warning "Unknown test scope '${test_scope}', using default"
            ;;
    esac
    
    # Add force deployment flag
    if [[ "${force_deployment}" == "true" ]]; then
        test_args+=("--force-deployment")
    fi
    
    # Add Jenkins build info if available
    if [[ -n "${JENKINS_BUILD:-}" ]]; then
        test_args+=("--jenkins-build" "${JENKINS_BUILD}")
    fi
    
    log_info "Executing: python3 ${TEST_RUNNER} ${test_args[*]}"
    
    # Execute the test framework
    if python3 "${TEST_RUNNER}" "${test_args[@]}"; then
        log_info "Test execution completed successfully"
        return 0
    else
        local exit_code=$?
        log_error "Test execution failed with exit code: ${exit_code}"
        return ${exit_code}
    fi
}

# --- Argument Parsing ---
MANIFEST_PATH=""
BUILD_ID=""
TEST_SCOPE="full"
JENKINS_BUILD=""
FORCE_DEPLOYMENT="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --manifest-path)
            MANIFEST_PATH="$2"
            shift 2
            ;;
        --build-id)
            BUILD_ID="$2"
            shift 2
            ;;
        --test-scope)
            TEST_SCOPE="$2"
            shift 2
            ;;
        --jenkins-build)
            JENKINS_BUILD="$2"
            shift 2
            ;;
        --force-deployment)
            FORCE_DEPLOYMENT="true"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 --manifest-path PATH [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --manifest-path PATH    Path to BSP manifest file (required)"
            echo "  --build-id ID          Build identifier"
            echo "  --test-scope SCOPE     Test scope: smoke|full|regression|security (default: full)"
            echo "  --jenkins-build NUM    Jenkins build number"
            echo "  --force-deployment     Continue even if validation fails"
            echo "  -h, --help            Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# --- Main Execution ---
trap cleanup EXIT

log_info "=========================================="
log_info "ZCU102 Hardware Validation Controller"
log_info "Run ID: ${RUN_ID}"
log_info "=========================================="

# Validate required parameters
if [[ -z "${MANIFEST_PATH}" ]]; then
    log_error "Manifest path is required. Use --manifest-path parameter."
    exit 1
fi

# Validate environment
validate_environment

# Download and validate manifest
MANIFEST_FILE=$(download_manifest "${MANIFEST_PATH}")

# Execute tests
if execute_tests "${MANIFEST_FILE}" "${TEST_SCOPE}" "${FORCE_DEPLOYMENT}"; then
    log_info "Hardware validation completed successfully"
    exit 0
else
    log_error "Hardware validation failed"
    exit 1
fi
