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

# NFS Configuration
NFS_MOUNT_POINT="/mnt/nfs_artifacts"
NFS_ROOT="${NFS_MOUNT_POINT}/bsp"
LOCAL_ARTIFACTS_DIR="${FRAMEWORK_ROOT}/artifacts"

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
    
    # Check if NFS mount point is available
    if [[ ! -d "${NFS_MOUNT_POINT}" ]]; then
        log_error "NFS mount point not found: ${NFS_MOUNT_POINT}"
        exit 2
    fi
    
    # Verify NFS mount is active
    if ! mountpoint -q "${NFS_MOUNT_POINT}"; then
        log_error "NFS mount point is not mounted: ${NFS_MOUNT_POINT}"
        exit 2
    fi
    
    # Check if we have necessary hardware access
    if ! groups | grep -q "dialout\|tty"; then
        log_warning "User not in dialout/tty groups - serial access may fail"
    fi
    
    log_info "Environment validation completed"
}

verify_checksum() {
    local file_path="$1"
    local expected_checksum="$2"
    local algorithm="${3:-md5}"
    
    log_info "Verifying checksum for $(basename "${file_path}")"
    
    if [[ ! -f "${file_path}" ]]; then
        log_error "File not found for checksum verification: ${file_path}"
        return 1
    fi
    
    local calculated_checksum
    case "${algorithm}" in
        "md5")
            calculated_checksum=$(md5sum "${file_path}" | cut -d' ' -f1)
            ;;
        "sha256")
            calculated_checksum=$(sha256sum "${file_path}" | cut -d' ' -f1)
            ;;
        *)
            log_error "Unsupported checksum algorithm: ${algorithm}"
            return 1
            ;;
    esac
    
    if [[ "${calculated_checksum}" != "${expected_checksum}" ]]; then
        log_error "Checksum mismatch for $(basename "${file_path}")"
        log_error "Expected: ${expected_checksum}"
        log_error "Calculated: ${calculated_checksum}"
        return 1
    fi
    
    log_info "Checksum verification passed for $(basename "${file_path}")"
    return 0
}

fetch_and_verify_artifacts() {
    local manifest_file="$1"
    local nfs_build_path="$2"
    
    log_info "Fetching and verifying artifacts from NFS"
    log_info "Manifest: ${manifest_file}"
    log_info "NFS Build Path: ${nfs_build_path}"
    
    # Create local artifacts directory
    mkdir -p "${LOCAL_ARTIFACTS_DIR}"
    
    # Verify NFS build directory exists
    if [[ ! -d "${nfs_build_path}" ]]; then
        log_error "NFS build directory not found: ${nfs_build_path}"
        exit 2
    fi
    
    # Parse manifest and extract artifacts
    log_info "Parsing manifest for artifact list..."
    
    # Check if manifest is YAML format
    if ! python3 -c "import yaml; yaml.safe_load(open('${manifest_file}'))" 2>/dev/null; then
        log_error "Invalid YAML manifest file: ${manifest_file}"
        exit 2
    fi
    
    # Use Python to extract artifact information from YAML manifest
    python3 << EOF
import yaml
import sys
import os

manifest_file = "${manifest_file}"
nfs_build_path = "${nfs_build_path}"
local_artifacts_dir = "${LOCAL_ARTIFACTS_DIR}"

try:
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    
    artifacts = manifest.get('artifacts', {}).get('components', [])
    
    for artifact in artifacts:
        name = artifact.get('name', '')
        filename = artifact.get('file', '')
        checksum = artifact.get('checksum_md5', '')
        
        if not all([name, filename, checksum]):
            print(f"ERROR: Incomplete artifact definition for {name}")
            sys.exit(1)
        
        nfs_source = os.path.join(nfs_build_path, filename)
        local_dest = os.path.join(local_artifacts_dir, filename)
        
        print(f"ARTIFACT:{name}:{filename}:{checksum}:{nfs_source}:{local_dest}")

except Exception as e:
    print(f"ERROR: Failed to parse manifest: {e}")
    sys.exit(1)
EOF
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to parse manifest file"
        exit 2
    fi
    
    # Process each artifact
    while IFS=':' read -r artifact_name filename checksum nfs_source local_dest; do
        if [[ "${artifact_name}" == "ARTIFACT" ]]; then
            log_info "Processing artifact: ${filename}"
            
            # Check if source file exists on NFS
            if [[ ! -f "${nfs_source}" ]]; then
                log_error "Source artifact not found on NFS: ${nfs_source}"
                exit 2
            fi
            
            # Copy artifact from NFS to local directory
            log_info "Copying ${filename} from NFS to local workspace"
            if ! cp "${nfs_source}" "${local_dest}"; then
                log_error "Failed to copy artifact: ${nfs_source} -> ${local_dest}"
                exit 2
            fi
            
            # Verify checksum
            if ! verify_checksum "${local_dest}" "${checksum}" "md5"; then
                log_error "Checksum verification failed for ${filename}"
                exit 2
            fi
            
            log_info "Successfully fetched and verified: ${filename}"
        fi
    done < <(python3 << 'EOF'
import yaml
import sys
import os

manifest_file = sys.argv[1] if len(sys.argv) > 1 else "${manifest_file}"
nfs_build_path = sys.argv[2] if len(sys.argv) > 2 else "${nfs_build_path}"
local_artifacts_dir = sys.argv[3] if len(sys.argv) > 3 else "${LOCAL_ARTIFACTS_DIR}"

try:
    with open(manifest_file, 'r') as f:
        manifest = yaml.safe_load(f)
    
    artifacts = manifest.get('artifacts', {}).get('components', [])
    
    for artifact in artifacts:
        name = artifact.get('name', '')
        filename = artifact.get('file', '')
        checksum = artifact.get('checksum_md5', '')
        
        if not all([name, filename, checksum]):
            continue
        
        nfs_source = os.path.join(nfs_build_path, filename)
        local_dest = os.path.join(local_artifacts_dir, filename)
        
        print(f"ARTIFACT:{name}:{filename}:{checksum}:{nfs_source}:{local_dest}")

except Exception as e:
    print(f"ERROR: Failed to parse manifest: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)
    
    log_info "All artifacts fetched and verified successfully"
    return 0
}

download_manifest() {
    local manifest_path="$1"
    local nfs_build_path="$2"
    local local_manifest="${MANIFESTS_DIR}/current_manifest.yaml"
    
    log_info "Fetching BSP manifest from NFS: ${manifest_path}"
    
    # Create manifests directory if it doesn't exist
    mkdir -p "${MANIFESTS_DIR}"
    
    # Determine manifest source location
    local manifest_source=""
    
    if [[ "${manifest_path}" =~ ^/ ]]; then
        # Absolute path - use as-is
        manifest_source="${manifest_path}"
    elif [[ -n "${nfs_build_path}" ]] && [[ -f "${nfs_build_path}/${manifest_path}" ]]; then
        # Relative path - look in NFS build directory first
        manifest_source="${nfs_build_path}/${manifest_path}"
    elif [[ -f "${NFS_ROOT}/${manifest_path}" ]]; then
        # Look in NFS root directory
        manifest_source="${NFS_ROOT}/${manifest_path}"
    elif [[ -f "${FRAMEWORK_ROOT}/../Xilinx-MPSoC-infra/artifacts/${manifest_path}" ]]; then
        # Fallback to local artifacts directory
        manifest_source="${FRAMEWORK_ROOT}/../Xilinx-MPSoC-infra/artifacts/${manifest_path}"
    else
        log_error "Manifest file not found in any expected location: ${manifest_path}"
        log_error "Checked locations:"
        log_error "  - ${nfs_build_path}/${manifest_path}"
        log_error "  - ${NFS_ROOT}/${manifest_path}" 
        log_error "  - ${FRAMEWORK_ROOT}/../Xilinx-MPSoC-infra/artifacts/${manifest_path}"
        exit 2
    fi
    
    log_info "Found manifest at: ${manifest_source}"
    
    # Copy manifest to local directory
    if ! cp "${manifest_source}" "${local_manifest}"; then
        log_error "Failed to copy manifest: ${manifest_source} -> ${local_manifest}"
        exit 2
    fi
    
    # Validate manifest file
    if [[ ! -s "${local_manifest}" ]]; then
        log_error "Copied manifest is empty or invalid"
        exit 2
    fi
    
    # Verify it's valid YAML
    if ! python3 -c "import yaml; yaml.safe_load(open('${local_manifest}'))" 2>/dev/null; then
        log_error "Manifest is not valid YAML: ${local_manifest}"
        exit 2
    fi
    
    log_info "Manifest fetched successfully: ${local_manifest}"
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
NFS_BUILD_PATH=""
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
        --nfs-build-path)
            NFS_BUILD_PATH="$2"
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
            echo "  --manifest-path PATH     Path to BSP manifest file (required)"
            echo "  --build-id ID           Build identifier"
            echo "  --nfs-build-path PATH   Full NFS path to build directory"
            echo "  --test-scope SCOPE      Test scope: smoke|full|regression|security (default: full)"
            echo "  --jenkins-build NUM     Jenkins build number"
            echo "  --force-deployment      Continue even if validation fails"
            echo "  -h, --help             Show this help message"
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

# Auto-generate NFS build path if not provided
if [[ -z "${NFS_BUILD_PATH}" ]] && [[ -n "${BUILD_ID}" ]]; then
    NFS_BUILD_PATH="${NFS_ROOT}/${BUILD_ID}"
    log_info "Auto-generated NFS Build Path: ${NFS_BUILD_PATH}"
fi

# Validate environment
validate_environment

# Download and validate manifest
MANIFEST_FILE=$(download_manifest "${MANIFEST_PATH}" "${NFS_BUILD_PATH}")

# Fetch and verify artifacts from NFS
if [[ -n "${NFS_BUILD_PATH}" ]]; then
    fetch_and_verify_artifacts "${MANIFEST_FILE}" "${NFS_BUILD_PATH}"
    
    # Update manifest to point to local artifacts
    log_info "Updating manifest to use local artifact paths"
    python3 << EOF
import yaml
import os

manifest_file = "${MANIFEST_FILE}"
local_artifacts_dir = "${LOCAL_ARTIFACTS_DIR}"

with open(manifest_file, 'r') as f:
    manifest = yaml.safe_load(f)

# Update artifact paths to point to local copies
if 'artifacts' in manifest and 'components' in manifest['artifacts']:
    for artifact in manifest['artifacts']['components']:
        if 'file' in artifact:
            artifact['local_path'] = os.path.join(local_artifacts_dir, artifact['file'])

# Update repository URL to point to local directory
manifest['artifacts']['repository_url'] = f"file://{local_artifacts_dir}"

with open(manifest_file, 'w') as f:
    yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)

print(f"Updated manifest with local artifact paths")
EOF
fi

# Execute tests
if execute_tests "${MANIFEST_FILE}" "${TEST_SCOPE}" "${FORCE_DEPLOYMENT}"; then
    log_info "Hardware validation completed successfully"
    exit 0
else
    log_error "Hardware validation failed"
    exit 1
fi
