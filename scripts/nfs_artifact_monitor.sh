#!/bin/bash
# ===================================================================
# NFS Artifact Monitor Script
# ===================================================================
# Monitors NFS share for new BSP artifacts and triggers Jenkins pipeline
# Replaces Artifactory webhook functionality with filesystem watching
# -------------------------------------------------------------------

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NFS_MOUNT_POINT="/mnt/nfs_artifacts"
NFS_ROOT="${NFS_MOUNT_POINT}/bsp"
WATCH_PATTERN="*.yaml"
JENKINS_URL="${JENKINS_URL:-http://localhost:8080}"
JENKINS_JOB="ZCU102-BSP-Hardware-Validation"
JENKINS_USER="${JENKINS_USER:-jenkins}"
JENKINS_TOKEN="${JENKINS_TOKEN:-}"
POLL_INTERVAL=30
STATE_FILE="/var/lib/nfs-artifact-monitor/last_check"

# --- Logging Functions ---
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $*"
}

log_debug() {
    if [[ "${DEBUG:-false}" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] DEBUG: $*"
    fi
}

# --- Helper Functions ---
validate_environment() {
    log_info "Validating monitoring environment..."
    
    # Check NFS mount
    if [[ ! -d "${NFS_MOUNT_POINT}" ]]; then
        log_error "NFS mount point not found: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    if ! mountpoint -q "${NFS_MOUNT_POINT}"; then
        log_error "NFS is not mounted at: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    # Check required tools
    for tool in curl jq; do
        if ! command -v "$tool" >/dev/null 2>&1; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Create state directory
    mkdir -p "$(dirname "${STATE_FILE}")"
    
    log_info "Environment validation passed"
}

get_last_check_time() {
    if [[ -f "${STATE_FILE}" ]]; then
        cat "${STATE_FILE}"
    else
        echo "0"
    fi
}

update_last_check_time() {
    echo "$(date +%s)" > "${STATE_FILE}"
}

find_new_artifacts() {
    local last_check=$(get_last_check_time)
    local new_artifacts=()
    
    log_debug "Searching for artifacts newer than timestamp: ${last_check}"
    
    # Find manifest files created/modified since last check
    while IFS= read -r -d '' file; do
        local file_mtime=$(stat -c %Y "${file}" 2>/dev/null || stat -f %m "${file}")
        
        if [[ ${file_mtime} -gt ${last_check} ]]; then
            log_debug "Found new artifact: ${file}"
            new_artifacts+=("${file}")
        fi
    done < <(find "${NFS_ROOT}" -name "${WATCH_PATTERN}" -type f -print0 2>/dev/null)
    
    # Return array of new artifacts
    printf '%s\n' "${new_artifacts[@]}"
}

extract_build_info() {
    local manifest_file="$1"
    
    log_debug "Extracting build info from: ${manifest_file}"
    
    # Use Python to parse YAML and extract build information
    python3 << EOF
import yaml
import sys
import os

try:
    with open("${manifest_file}", 'r') as f:
        manifest = yaml.safe_load(f)
    
    build_info = manifest.get('build_info', {})
    build_id = build_info.get('build_id', os.path.basename("${manifest_file}").replace('.yaml', ''))
    nfs_path = build_info.get('nfs_path', os.path.dirname("${manifest_file}"))
    build_type = build_info.get('build_type', 'unknown')
    
    print(f"BUILD_ID:{build_id}")
    print(f"NFS_PATH:{nfs_path}")
    print(f"BUILD_TYPE:{build_type}")
    print(f"MANIFEST_PATH:{os.path.relpath('${manifest_file}', '${NFS_ROOT}')}")
    
except Exception as e:
    print(f"ERROR: Failed to parse manifest: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

trigger_jenkins_build() {
    local build_id="$1"
    local manifest_path="$2"
    local nfs_path="$3"
    local build_type="$4"
    
    log_info "Triggering Jenkins build for: ${build_id}"
    
    # Prepare Jenkins API request
    local jenkins_url="${JENKINS_URL}/job/${JENKINS_JOB}/buildWithParameters"
    local auth_header=""
    
    if [[ -n "${JENKINS_TOKEN}" ]]; then
        auth_header="Authorization: Bearer ${JENKINS_TOKEN}"
    fi
    
    # Build parameter payload
    local params="MANIFEST_PATH=${manifest_path}&BUILD_ID=${build_id}&NFS_BUILD_PATH=${nfs_path}&TEST_SCOPE=full"
    
    # Add build type specific parameters
    case "${build_type}" in
        "development")
            params="${params}&TEST_SCOPE=smoke"
            ;;
        "hotfix")
            params="${params}&FORCE_DEPLOYMENT=true"
            ;;
    esac
    
    log_debug "Jenkins URL: ${jenkins_url}"
    log_debug "Parameters: ${params}"
    
    # Trigger Jenkins build
    local response
    if [[ -n "${auth_header}" ]]; then
        response=$(curl -s -w "%{http_code}" \
            -H "${auth_header}" \
            -X POST \
            "${jenkins_url}?${params}" \
            2>/dev/null)
    else
        response=$(curl -s -w "%{http_code}" \
            -X POST \
            "${jenkins_url}?${params}" \
            2>/dev/null)
    fi
    
    local http_code="${response: -3}"
    local response_body="${response%???}"
    
    case "${http_code}" in
        "201")
            log_info "Successfully triggered Jenkins build for ${build_id}"
            return 0
            ;;
        "401")
            log_error "Jenkins authentication failed. Check JENKINS_TOKEN."
            return 1
            ;;
        "404")
            log_error "Jenkins job not found: ${JENKINS_JOB}"
            return 1
            ;;
        *)
            log_error "Jenkins API request failed with HTTP ${http_code}"
            log_error "Response: ${response_body}"
            return 1
            ;;
    esac
}

process_new_artifact() {
    local manifest_file="$1"
    
    log_info "Processing new artifact: $(basename "${manifest_file}")"
    
    # Extract build information
    local build_info
    if ! build_info=$(extract_build_info "${manifest_file}"); then
        log_error "Failed to extract build info from: ${manifest_file}"
        return 1
    fi
    
    # Parse build info
    local build_id nfs_path build_type manifest_path
    while IFS=':' read -r key value; do
        case "${key}" in
            "BUILD_ID") build_id="${value}" ;;
            "NFS_PATH") nfs_path="${value}" ;;
            "BUILD_TYPE") build_type="${value}" ;;
            "MANIFEST_PATH") manifest_path="${value}" ;;
        esac
    done <<< "${build_info}"
    
    log_info "Extracted build info:"
    log_info "  Build ID: ${build_id}"
    log_info "  Build Type: ${build_type}"
    log_info "  NFS Path: ${nfs_path}"
    log_info "  Manifest Path: ${manifest_path}"
    
    # Trigger Jenkins build
    if trigger_jenkins_build "${build_id}" "${manifest_path}" "${nfs_path}" "${build_type}"; then
        log_info "Successfully processed artifact: ${build_id}"
        return 0
    else
        log_error "Failed to process artifact: ${build_id}"
        return 1
    fi
}

monitor_loop() {
    log_info "Starting artifact monitoring loop..."
    log_info "NFS Root: ${NFS_ROOT}"
    log_info "Watch Pattern: ${WATCH_PATTERN}"
    log_info "Poll Interval: ${POLL_INTERVAL}s"
    log_info "Jenkins URL: ${JENKINS_URL}"
    log_info "Jenkins Job: ${JENKINS_JOB}"
    
    while true; do
        log_debug "Checking for new artifacts..."
        
        # Find new artifacts since last check
        local new_artifacts
        new_artifacts=$(find_new_artifacts)
        
        if [[ -n "${new_artifacts}" ]]; then
            log_info "Found new artifacts to process"
            
            # Process each new artifact
            while IFS= read -r artifact; do
                if [[ -n "${artifact}" ]]; then
                    process_new_artifact "${artifact}"
                fi
            done <<< "${new_artifacts}"
        else
            log_debug "No new artifacts found"
        fi
        
        # Update last check time
        update_last_check_time
        
        # Wait for next poll interval
        log_debug "Waiting ${POLL_INTERVAL} seconds until next check..."
        sleep "${POLL_INTERVAL}"
    done
}

daemon_mode() {
    log_info "Starting in daemon mode..."
    
    # Redirect output to log file
    local log_file="/var/log/nfs-artifact-monitor.log"
    mkdir -p "$(dirname "${log_file}")"
    
    exec > >(tee -a "${log_file}")
    exec 2>&1
    
    # Set up signal handlers for graceful shutdown
    trap 'log_info "Received shutdown signal, exiting..."; exit 0' TERM INT
    
    monitor_loop
}

# --- Argument Parsing ---
MODE="monitor"
DAEMON=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --daemon)
            DAEMON=true
            shift
            ;;
        --poll-interval)
            POLL_INTERVAL="$2"
            shift 2
            ;;
        --jenkins-url)
            JENKINS_URL="$2"
            shift 2
            ;;
        --jenkins-job)
            JENKINS_JOB="$2"
            shift 2
            ;;
        --jenkins-token)
            JENKINS_TOKEN="$2"
            shift 2
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        --test)
            MODE="test"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --daemon                Run as daemon process"
            echo "  --poll-interval N       Poll interval in seconds (default: ${POLL_INTERVAL})"
            echo "  --jenkins-url URL       Jenkins base URL (default: ${JENKINS_URL})"
            echo "  --jenkins-job JOB       Jenkins job name (default: ${JENKINS_JOB})"
            echo "  --jenkins-token TOKEN   Jenkins API token for authentication"
            echo "  --debug                 Enable debug logging"
            echo "  --test                  Test mode - check configuration and exit"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  JENKINS_URL            Jenkins base URL"
            echo "  JENKINS_USER           Jenkins username"
            echo "  JENKINS_TOKEN          Jenkins API token"
            exit 0
            ;;
        *)
            log_error "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

# --- Main Execution ---
log_info "=========================================="
log_info "NFS Artifact Monitor"
log_info "Mode: ${MODE}"
log_info "=========================================="

# Validate environment
validate_environment

if [[ "${MODE}" == "test" ]]; then
    log_info "Test mode - configuration validated successfully"
    log_info "NFS Root: ${NFS_ROOT}"
    log_info "Jenkins URL: ${JENKINS_URL}"
    log_info "Jenkins Job: ${JENKINS_JOB}"
    log_info "State File: ${STATE_FILE}"
    exit 0
fi

# Run monitoring
if [[ "${DAEMON}" == "true" ]]; then
    daemon_mode
else
    monitor_loop
fi
