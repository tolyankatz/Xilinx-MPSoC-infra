#!/bin/bash
# ===================================================================
# NFS Artifact Management Script
# ===================================================================
# Comprehensive management tool for NFS-based BSP artifact storage
# Supports listing, cleanup, verification, and maintenance operations
# -------------------------------------------------------------------

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NFS_MOUNT_POINT="/mnt/nfs_artifacts"
NFS_ROOT="${NFS_MOUNT_POINT}/bsp"
DEFAULT_RETENTION_DAYS=30

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

# --- Helper Functions ---
validate_nfs_mount() {
    if [[ ! -d "${NFS_MOUNT_POINT}" ]]; then
        log_error "NFS mount point not found: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    if ! mountpoint -q "${NFS_MOUNT_POINT}"; then
        log_error "NFS is not mounted at: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    if [[ ! -d "${NFS_ROOT}" ]]; then
        log_error "NFS artifact root not found: ${NFS_ROOT}"
        exit 1
    fi
}

human_readable_size() {
    local bytes=$1
    local units=("B" "KB" "MB" "GB" "TB")
    local unit=0
    
    while (( bytes >= 1024 && unit < 4 )); do
        bytes=$((bytes / 1024))
        ((unit++))
    done
    
    echo "${bytes}${units[$unit]}"
}

# --- Command Functions ---
cmd_list() {
    local show_details=false
    local sort_by="name"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --details|-d)
                show_details=true
                shift
                ;;
            --sort)
                sort_by="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option for list command: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Listing artifacts in NFS root: ${NFS_ROOT}"
    
    if [[ ! -d "${NFS_ROOT}" ]] || [[ -z "$(ls -A "${NFS_ROOT}" 2>/dev/null)" ]]; then
        echo "No artifacts found."
        return 0
    fi
    
    if [[ "${show_details}" == "true" ]]; then
        printf "%-20s %-12s %-15s %-10s %s\n" "BUILD_ID" "BUILD_TYPE" "SIZE" "ARTIFACTS" "CREATED"
        printf "%-20s %-12s %-15s %-10s %s\n" "--------------------" "------------" "---------------" "----------" "-------------------"
    else
        printf "%-20s %-12s %s\n" "BUILD_ID" "BUILD_TYPE" "CREATED"
        printf "%-20s %-12s %s\n" "--------------------" "------------" "-------------------"
    fi
    
    # Process each build directory
    local build_dirs=()
    for build_dir in "${NFS_ROOT}"/*; do
        if [[ -d "${build_dir}" ]]; then
            build_dirs+=("${build_dir}")
        fi
    done
    
    # Sort build directories
    case "${sort_by}" in
        "name")
            IFS=$'\n' build_dirs=($(sort <<< "${build_dirs[*]}"))
            ;;
        "date")
            IFS=$'\n' build_dirs=($(ls -1dt "${build_dirs[@]}"))
            ;;
    esac
    
    for build_dir in "${build_dirs[@]}"; do
        local build_id="$(basename "${build_dir}")"
        local created=$(stat -c %y "${build_dir}" 2>/dev/null | cut -d' ' -f1 || echo "unknown")
        local build_type="unknown"
        local total_size=0
        local artifact_count=0
        
        # Try to get build type from metadata
        if [[ -f "${build_dir}/build_metadata.json" ]]; then
            build_type=$(python3 -c "
import json, sys
try:
    with open('${build_dir}/build_metadata.json') as f:
        data = json.load(f)
    print(data.get('build_type', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
        elif [[ -f "${build_dir}/deployment_manifest.yaml" ]]; then
            build_type=$(python3 -c "
import yaml, sys
try:
    with open('${build_dir}/deployment_manifest.yaml') as f:
        data = yaml.safe_load(f)
    print(data.get('build_info', {}).get('build_type', 'unknown'))
except:
    print('unknown')
" 2>/dev/null)
        fi
        
        # Determine build type from build_id if still unknown
        if [[ "${build_type}" == "unknown" ]]; then
            case "${build_id}" in
                *-dev-*|*-rc*)
                    build_type="development"
                    ;;
                *-hotfix-*)
                    build_type="hotfix"
                    ;;
                *-stable*)
                    build_type="stable"
                    ;;
            esac
        fi
        
        if [[ "${show_details}" == "true" ]]; then
            # Calculate total size and artifact count
            for file in "${build_dir}"/*; do
                if [[ -f "${file}" ]] && [[ ! "${file}" =~ \.(md5|sha256|json|yaml)$ ]]; then
                    local size=$(stat -c %s "${file}" 2>/dev/null || echo 0)
                    total_size=$((total_size + size))
                    ((artifact_count++))
                fi
            done
            
            local size_str=$(human_readable_size ${total_size})
            printf "%-20s %-12s %-15s %-10d %s\n" "${build_id}" "${build_type}" "${size_str}" "${artifact_count}" "${created}"
        else
            printf "%-20s %-12s %s\n" "${build_id}" "${build_type}" "${created}"
        fi
    done
}

cmd_cleanup() {
    local retention_days="${DEFAULT_RETENTION_DAYS}"
    local dry_run=false
    local force=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --days)
                retention_days="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            *)
                log_error "Unknown option for cleanup command: $1"
                exit 1
                ;;
        esac
    done
    
    log_info "Starting cleanup of artifacts older than ${retention_days} days"
    
    if [[ "${dry_run}" == "true" ]]; then
        log_info "DRY RUN MODE - No files will be deleted"
    fi
    
    if [[ ! -d "${NFS_ROOT}" ]]; then
        log_warning "NFS root directory not found, nothing to clean"
        return 0
    fi
    
    local cleaned_count=0
    local total_size_cleaned=0
    
    # Find directories older than retention period
    while IFS= read -r -d '' old_build_dir; do
        if [[ "${old_build_dir}" != "${NFS_ROOT}" ]]; then
            local build_name="$(basename "${old_build_dir}")"
            local dir_size=$(du -sb "${old_build_dir}" 2>/dev/null | cut -f1 || echo 0)
            
            if [[ "${dry_run}" == "true" ]]; then
                echo "Would remove: ${build_name} ($(human_readable_size ${dir_size}))"
            else
                if [[ "${force}" == "true" ]] || read -p "Remove build ${build_name}? (y/N): " -r && [[ $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Removing old build: ${build_name}"
                    rm -rf "${old_build_dir}"
                    ((cleaned_count++))
                    total_size_cleaned=$((total_size_cleaned + dir_size))
                fi
            fi
        fi
    done < <(find "${NFS_ROOT}" -maxdepth 1 -type d -mtime +${retention_days} -print0 2>/dev/null)
    
    if [[ "${dry_run}" == "true" ]]; then
        log_info "DRY RUN: Would clean ${cleaned_count} builds"
    else
        log_info "Cleanup completed: Removed ${cleaned_count} builds ($(human_readable_size ${total_size_cleaned}) freed)"
    fi
}

cmd_verify() {
    local build_id="$1"
    local build_dir="${NFS_ROOT}/${build_id}"
    
    log_info "Verifying build: ${build_id}"
    
    if [[ ! -d "${build_dir}" ]]; then
        log_error "Build directory not found: ${build_dir}"
        exit 1
    fi
    
    local verification_errors=0
    local artifacts_verified=0
    
    # Check for required files
    local manifest_file="${build_dir}/deployment_manifest.yaml"
    if [[ ! -f "${manifest_file}" ]]; then
        log_error "Missing deployment manifest: ${manifest_file}"
        ((verification_errors++))
    fi
    
    # Verify checksums for all artifacts
    for artifact_file in "${build_dir}"/*; do
        if [[ -f "${artifact_file}" ]] && [[ ! "${artifact_file}" =~ \.(md5|sha256|json|yaml)$ ]]; then
            local filename="$(basename "${artifact_file}")"
            local checksum_file="${artifact_file}.md5"
            
            if [[ -f "${checksum_file}" ]]; then
                local expected_checksum=$(cut -d' ' -f1 "${checksum_file}")
                local calculated_checksum=$(md5sum "${artifact_file}" | cut -d' ' -f1)
                
                if [[ "${expected_checksum}" == "${calculated_checksum}" ]]; then
                    log_info "✓ Checksum verified: ${filename}"
                    ((artifacts_verified++))
                else
                    log_error "✗ Checksum mismatch: ${filename}"
                    log_error "  Expected: ${expected_checksum}"
                    log_error "  Calculated: ${calculated_checksum}"
                    ((verification_errors++))
                fi
            else
                log_warning "Missing checksum file: ${filename}.md5"
                ((verification_errors++))
            fi
        fi
    done
    
    if [[ ${verification_errors} -eq 0 ]]; then
        log_info "✓ Verification completed successfully: ${artifacts_verified} artifacts verified"
        return 0
    else
        log_error "✗ Verification failed: ${verification_errors} errors found"
        return 1
    fi
}

cmd_info() {
    local build_id="$1"
    local build_dir="${NFS_ROOT}/${build_id}"
    
    if [[ ! -d "${build_dir}" ]]; then
        log_error "Build directory not found: ${build_dir}"
        exit 1
    fi
    
    echo "Build Information: ${build_id}"
    echo "=================="
    echo "Path: ${build_dir}"
    echo "Created: $(stat -c %y "${build_dir}" 2>/dev/null || echo "unknown")"
    echo ""
    
    # Show metadata if available
    local metadata_file="${build_dir}/build_metadata.json"
    if [[ -f "${metadata_file}" ]]; then
        echo "Metadata:"
        python3 -c "
import json
try:
    with open('${metadata_file}') as f:
        data = json.load(f)
    
    for key, value in data.items():
        if key != 'artifacts':
            print(f'  {key}: {value}')
except Exception as e:
    print(f'  Error reading metadata: {e}')
"
        echo ""
    fi
    
    # List artifacts
    echo "Artifacts:"
    local total_size=0
    local artifact_count=0
    
    for artifact_file in "${build_dir}"/*; do
        if [[ -f "${artifact_file}" ]] && [[ ! "${artifact_file}" =~ \.(md5|sha256|json|yaml)$ ]]; then
            local filename="$(basename "${artifact_file}")"
            local size=$(stat -c %s "${artifact_file}" 2>/dev/null || echo 0)
            local size_str=$(human_readable_size ${size})
            
            echo "  ${filename} (${size_str})"
            total_size=$((total_size + size))
            ((artifact_count++))
        fi
    done
    
    echo ""
    echo "Summary: ${artifact_count} artifacts, $(human_readable_size ${total_size}) total"
}

cmd_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list [--details] [--sort name|date]  List all artifacts"
    echo "  cleanup [--days N] [--dry-run] [--force]  Clean old artifacts"
    echo "  verify <build_id>                    Verify artifact checksums"
    echo "  info <build_id>                      Show detailed build information"
    echo ""
    echo "Examples:"
    echo "  $0 list --details --sort date        List with details, sorted by date"
    echo "  $0 cleanup --days 30 --dry-run     Show what would be cleaned"
    echo "  $0 verify bsp-main-137              Verify specific build"
    echo "  $0 info bsp-dev-2025.11-rc1        Show build information"
    echo ""
    echo "Environment:"
    echo "  NFS mount point: ${NFS_MOUNT_POINT}"
    echo "  Artifact root: ${NFS_ROOT}"
}

# --- Argument Parsing ---
if [[ $# -lt 1 ]]; then
    cmd_usage
    exit 1
fi

COMMAND="$1"
shift

# Validate environment first
validate_nfs_mount

# Execute command
case "${COMMAND}" in
    "list")
        cmd_list "$@"
        ;;
    "cleanup")
        cmd_cleanup "$@"
        ;;
    "verify")
        if [[ $# -lt 1 ]]; then
            log_error "Build ID required for verify command"
            exit 1
        fi
        cmd_verify "$1"
        ;;
    "info")
        if [[ $# -lt 1 ]]; then
            log_error "Build ID required for info command"
            exit 1
        fi
        cmd_info "$1"
        ;;
    "help"|"-h"|"--help")
        cmd_usage
        ;;
    *)
        log_error "Unknown command: ${COMMAND}"
        cmd_usage
        exit 1
        ;;
esac
