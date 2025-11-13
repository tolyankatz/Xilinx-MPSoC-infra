#!/bin/bash
# ===================================================================
# NFS Mount Helper Script for Docker Containers
# ===================================================================
# Handles NFS mounting inside containers with proper error handling
# -------------------------------------------------------------------

set -euo pipefail

# Configuration
NFS_SERVER="${NFS_SERVER:-}"
NFS_EXPORT="${NFS_EXPORT:-/exports/bsp}"
NFS_MOUNT_POINT="${NFS_MOUNT_POINT:-/mnt/nfs_artifacts}"
NFS_OPTIONS="${NFS_OPTIONS:-rw,sync,hard,intr}"

# Logging
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] NFS-MOUNT INFO: $*"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] NFS-MOUNT ERROR: $*" >&2
}

# Validate parameters
if [[ -z "${NFS_SERVER}" ]]; then
    log_error "NFS_SERVER environment variable is required"
    exit 1
fi

# Check if already mounted
if mountpoint -q "${NFS_MOUNT_POINT}" 2>/dev/null; then
    log_info "NFS already mounted at ${NFS_MOUNT_POINT}"
    exit 0
fi

# Create mount point if it doesn't exist
if [[ ! -d "${NFS_MOUNT_POINT}" ]]; then
    log_info "Creating NFS mount point: ${NFS_MOUNT_POINT}"
    mkdir -p "${NFS_MOUNT_POINT}"
fi

# Attempt to mount NFS
log_info "Mounting NFS: ${NFS_SERVER}:${NFS_EXPORT} -> ${NFS_MOUNT_POINT}"
log_info "Options: ${NFS_OPTIONS}"

if mount -t nfs -o "${NFS_OPTIONS}" "${NFS_SERVER}:${NFS_EXPORT}" "${NFS_MOUNT_POINT}"; then
    log_info "NFS mounted successfully"
    
    # Create BSP directory structure if it doesn't exist
    if [[ ! -d "${NFS_MOUNT_POINT}/bsp" ]]; then
        log_info "Creating BSP directory structure"
        mkdir -p "${NFS_MOUNT_POINT}/bsp"
    fi
    
    # Test write access
    if touch "${NFS_MOUNT_POINT}/.mount_test" 2>/dev/null; then
        rm -f "${NFS_MOUNT_POINT}/.mount_test"
        log_info "NFS mount has write access"
    else
        log_info "NFS mount is read-only"
    fi
    
else
    log_error "Failed to mount NFS: ${NFS_SERVER}:${NFS_EXPORT}"
    exit 1
fi
