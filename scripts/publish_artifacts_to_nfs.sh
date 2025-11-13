#!/bin/bash
# ===================================================================
# NFS Artifact Publishing Script
# ===================================================================
# This script publishes BSP build artifacts to the NFS share
# Implements versioning, checksums, and integrity validation
# Called by Jenkins build pipeline
# -------------------------------------------------------------------

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NFS_MOUNT_POINT="/mnt/nfs_artifacts"
NFS_ROOT="${NFS_MOUNT_POINT}/bsp"
CHECKSUM_ALGORITHM="md5"
RETENTION_DAYS=30

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
    log_info "Validating NFS mount availability..."
    
    if [[ ! -d "${NFS_MOUNT_POINT}" ]]; then
        log_error "NFS mount point directory not found: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    if ! mountpoint -q "${NFS_MOUNT_POINT}"; then
        log_error "NFS is not mounted at: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    if [[ ! -w "${NFS_MOUNT_POINT}" ]]; then
        log_error "NFS mount point is not writable: ${NFS_MOUNT_POINT}"
        exit 1
    fi
    
    log_info "NFS mount validation passed"
}

create_build_directory() {
    local build_id="$1"
    local build_path="${NFS_ROOT}/${build_id}"
    
    log_info "Creating build directory: ${build_path}"
    
    if [[ -d "${build_path}" ]]; then
        log_warning "Build directory already exists: ${build_path}"
        log_warning "Existing content will be overwritten"
        rm -rf "${build_path}"
    fi
    
    mkdir -p "${build_path}"
    
    # Set appropriate permissions
    chmod 755 "${build_path}"
    
    echo "${build_path}"
}

calculate_checksum() {
    local file_path="$1"
    local algorithm="$2"
    
    case "${algorithm}" in
        "md5")
            md5sum "${file_path}" | cut -d' ' -f1
            ;;
        "sha256")
            sha256sum "${file_path}" | cut -d' ' -f1
            ;;
        *)
            log_error "Unsupported checksum algorithm: ${algorithm}"
            exit 1
            ;;
    esac
}

publish_artifact() {
    local source_file="$1"
    local build_path="$2"
    local filename="$(basename "${source_file}")"
    local dest_file="${build_path}/${filename}"
    
    log_info "Publishing artifact: ${filename}"
    
    # Verify source file exists
    if [[ ! -f "${source_file}" ]]; then
        log_error "Source artifact not found: ${source_file}"
        exit 1
    fi
    
    # Copy artifact to NFS
    log_info "Copying ${filename} to NFS..."
    cp "${source_file}" "${dest_file}"
    
    # Calculate and save checksum
    log_info "Calculating checksum for ${filename}..."
    local checksum=$(calculate_checksum "${dest_file}" "${CHECKSUM_ALGORITHM}")
    echo "${checksum}  ${filename}" > "${dest_file}.${CHECKSUM_ALGORITHM}"
    
    # Set appropriate permissions
    chmod 644 "${dest_file}" "${dest_file}.${CHECKSUM_ALGORITHM}"
    
    log_info "Successfully published: ${filename} (checksum: ${checksum})"
    echo "${checksum}"
}

generate_manifest() {
    local build_id="$1"
    local build_path="$2"
    local commit_hash="${3:-unknown}"
    local build_type="${4:-stable}"
    
    local manifest_file="${build_path}/deployment_manifest.yaml"
    
    log_info "Generating deployment manifest: ${manifest_file}"
    
    # Create manifest header
    cat > "${manifest_file}" << EOF
# ===================================================================
# Deployment Manifest for ZCU102 BSP (${build_type} build)
# ===================================================================
# Generated automatically by NFS artifact publisher
# Build ID: ${build_id}
# Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')
# -------------------------------------------------------------------

manifest_version: 1.0

# --- Target and Build Information ---
target_board: "ZCU102"
build_info:
  build_id: "${build_id}"
  commit_hash: "${commit_hash}"
  build_timestamp: "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  build_type: "${build_type}"
  nfs_path: "${build_path}"

# --- Artifacts ---
artifacts:
  repository_url: "nfs://${build_path}"
  components:
EOF

    # Add artifacts found in build directory
    local artifact_count=0
    for artifact_file in "${build_path}"/*.{bin,BIN,ub,dtb,gz,elf}; do
        if [[ -f "${artifact_file}" ]]; then
            local filename="$(basename "${artifact_file}")"
            local checksum_file="${artifact_file}.${CHECKSUM_ALGORITHM}"
            
            if [[ -f "${checksum_file}" ]]; then
                local checksum=$(cut -d' ' -f1 "${checksum_file}")
                local artifact_name="${filename%.*}"  # Remove extension
                artifact_name="${artifact_name,,}"    # Convert to lowercase
                
                # Determine artifact type based on filename
                case "${filename}" in
                    BOOT*.BIN|BOOT*.bin)
                        artifact_name="boot_binary"
                        ;;
                    *image*.ub|vmlinux)
                        artifact_name="kernel_image"
                        ;;
                    *.dtb)
                        artifact_name="device_tree"
                        ;;
                    rootfs*.tar.gz|rootfs*.tgz)
                        artifact_name="root_filesystem"
                        ;;
                esac
                
                cat >> "${manifest_file}" << EOF
    - name: "${artifact_name}"
      file: "${filename}"
      version: "${build_id}"
      checksum_${CHECKSUM_ALGORITHM}: "${checksum}"
      nfs_path: "${artifact_file}"

EOF
                ((artifact_count++))
            fi
        fi
    done
    
    if [[ ${artifact_count} -eq 0 ]]; then
        log_warning "No artifacts with checksums found in build directory"
    fi
    
    # Add deployment and runtime configuration sections
    cat >> "${manifest_file}" << EOF
# --- Deployment Configuration ---
deployment_config:
  method: "sd_card"
  verify_checksums: true
  source_type: "nfs"

# --- Runtime Configuration ---
runtime_config:
  console:
    baud_rate: 115200
  network:
    interface: "eth0"
    config_method: "dhcp"
  credentials:
    username: "root"
    password: "\${SECURE_PASSWORD}"

# --- Test Plan ---
test_plan:
  - "boot_validation"
  - "hardware_self_test"
EOF

    # Set appropriate permissions
    chmod 644 "${manifest_file}"
    
    log_info "Generated manifest with ${artifact_count} artifacts"
    echo "${manifest_file}"
}

create_build_metadata() {
    local build_path="$1"
    local build_id="$2"
    local commit_hash="${3:-unknown}"
    
    local metadata_file="${build_path}/build_metadata.json"
    
    log_info "Creating build metadata: ${metadata_file}"
    
    cat > "${metadata_file}" << EOF
{
  "build_id": "${build_id}",
  "commit_hash": "${commit_hash}",
  "build_timestamp": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
  "publisher": "$(whoami)@$(hostname)",
  "nfs_path": "${build_path}",
  "artifacts": [
EOF

    # List all published artifacts
    local first=true
    for artifact_file in "${build_path}"/*; do
        if [[ -f "${artifact_file}" ]] && [[ ! "${artifact_file}" =~ \.(md5|sha256|json|yaml)$ ]]; then
            if [[ "${first}" == "true" ]]; then
                first=false
            else
                echo "," >> "${metadata_file}"
            fi
            
            local filename="$(basename "${artifact_file}")"
            local size=$(stat -f%z "${artifact_file}" 2>/dev/null || stat -c%s "${artifact_file}")
            
            cat >> "${metadata_file}" << EOF
    {
      "filename": "${filename}",
      "size_bytes": ${size},
      "checksum_file": "${filename}.${CHECKSUM_ALGORITHM}"
    }EOF
        fi
    done
    
    cat >> "${metadata_file}" << EOF

  ]
}
EOF

    chmod 644 "${metadata_file}"
    log_info "Build metadata created successfully"
}

cleanup_old_builds() {
    local retention_days="$1"
    
    log_info "Cleaning up builds older than ${retention_days} days..."
    
    if [[ ! -d "${NFS_ROOT}" ]]; then
        log_warning "NFS root directory not found, skipping cleanup"
        return 0
    fi
    
    local cleaned_count=0
    
    # Find directories older than retention period
    find "${NFS_ROOT}" -maxdepth 1 -type d -mtime +${retention_days} | while read -r old_build_dir; do
        if [[ "${old_build_dir}" != "${NFS_ROOT}" ]]; then
            local build_name="$(basename "${old_build_dir}")"
            log_info "Removing old build: ${build_name}"
            rm -rf "${old_build_dir}"
            ((cleaned_count++))
        fi
    done
    
    log_info "Cleanup completed. Removed ${cleaned_count} old builds."
}

# --- Argument Parsing ---
BUILD_ID=""
SOURCE_DIR=""
COMMIT_HASH=""
BUILD_TYPE="stable"
CLEANUP_ENABLED="true"

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-id)
            BUILD_ID="$2"
            shift 2
            ;;
        --source-dir)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --commit-hash)
            COMMIT_HASH="$2"
            shift 2
            ;;
        --build-type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP_ENABLED="false"
            shift
            ;;
        --retention-days)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --build-id ID --source-dir DIR [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --build-id ID         Unique build identifier (required)"
            echo "  --source-dir DIR      Directory containing artifacts to publish (required)"
            echo "  --commit-hash HASH    Git commit hash for traceability"
            echo "  --build-type TYPE     Build type: stable|development|hotfix (default: stable)"
            echo "  --no-cleanup         Skip cleanup of old builds"
            echo "  --retention-days N    Days to retain old builds (default: ${RETENTION_DAYS})"
            echo "  -h, --help           Show this help message"
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
log_info "NFS Artifact Publisher"
log_info "Build ID: ${BUILD_ID}"
log_info "=========================================="

# Validate required parameters
if [[ -z "${BUILD_ID}" ]]; then
    log_error "Build ID is required. Use --build-id parameter."
    exit 1
fi

if [[ -z "${SOURCE_DIR}" ]]; then
    log_error "Source directory is required. Use --source-dir parameter."
    exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
    log_error "Source directory not found: ${SOURCE_DIR}"
    exit 1
fi

# Validate NFS mount
validate_nfs_mount

# Create build directory
BUILD_PATH=$(create_build_directory "${BUILD_ID}")

# Publish artifacts
log_info "Publishing artifacts from: ${SOURCE_DIR}"
ARTIFACT_COUNT=0

for source_file in "${SOURCE_DIR}"/*; do
    if [[ -f "${source_file}" ]]; then
        filename="$(basename "${source_file}")"
        
        # Skip certain file types
        case "${filename}" in
            *.log|*.tmp|*.bak|*~)
                log_info "Skipping file: ${filename}"
                continue
                ;;
        esac
        
        publish_artifact "${source_file}" "${BUILD_PATH}"
        ((ARTIFACT_COUNT++))
    fi
done

if [[ ${ARTIFACT_COUNT} -eq 0 ]]; then
    log_error "No artifacts found to publish in: ${SOURCE_DIR}"
    exit 1
fi

# Generate deployment manifest
generate_manifest "${BUILD_ID}" "${BUILD_PATH}" "${COMMIT_HASH}" "${BUILD_TYPE}"

# Create build metadata
create_build_metadata "${BUILD_PATH}" "${BUILD_ID}" "${COMMIT_HASH}"

# Cleanup old builds if enabled
if [[ "${CLEANUP_ENABLED}" == "true" ]]; then
    cleanup_old_builds "${RETENTION_DAYS}"
fi

log_info "=========================================="
log_info "Artifact publishing completed successfully"
log_info "Published ${ARTIFACT_COUNT} artifacts to: ${BUILD_PATH}"
log_info "Build available at: nfs://${BUILD_PATH}"
log_info "=========================================="
