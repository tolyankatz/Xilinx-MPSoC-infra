#!/bin/bash

# ZCU102 BSP Build Log Parser
#
# This script analyzes PetaLinux build logs to extract key metrics and quality indicators.
# It supports the "glass box" philosophy by surfacing build-time insights that inform
# engineering decisions and identify potential issues before they reach hardware testing.
#
# Usage: parse_build_log.sh <build_log_file>
# Output: JSON formatted metrics suitable for ingestion by monitoring systems

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
BUILD_LOG="${1:-build/build.log}"

# Validate input file exists
if [[ ! -f "$BUILD_LOG" ]]; then
    echo "Error: Build log file '$BUILD_LOG' not found" >&2
    exit 1
fi

# Initialize metrics collection
declare -A METRICS
METRICS[warnings]=0
METRICS[errors]=0  
METRICS[build_time_seconds]=0
METRICS[kernel_modules]=0
METRICS[rootfs_size_mb]=0
METRICS[boot_partition_size_mb]=0

# Extract build duration from log timestamps
parse_build_duration() {
    local start_time=$(grep -m1 "Starting bitbake" "$BUILD_LOG" | cut -d'[' -f2 | cut -d']' -f1 2>/dev/null || echo "")
    local end_time=$(grep "Build Configuration:" "$BUILD_LOG" | tail -1 | cut -d'[' -f2 | cut -d']' -f1 2>/dev/null || echo "")
    
    if [[ -n "$start_time" && -n "$end_time" ]]; then
        local start_epoch=$(date -d "$start_time" +%s 2>/dev/null || echo 0)
        local end_epoch=$(date -d "$end_time" +%s 2>/dev/null || echo 0)
        METRICS[build_time_seconds]=$((end_epoch - start_epoch))
    fi
}

# Count warnings and errors with categorization
parse_issues() {
    # Count compiler warnings
    METRICS[warnings]=$(grep -c "warning:" "$BUILD_LOG" 2>/dev/null || echo 0)
    
    # Count build errors  
    METRICS[errors]=$(grep -c -E "(error:|Error:|ERROR:)" "$BUILD_LOG" 2>/dev/null || echo 0)
    
    # Extract specific warning categories for trending analysis
    METRICS[deprecated_warnings]=$(grep -c "deprecated" "$BUILD_LOG" 2>/dev/null || echo 0)
    METRICS[unused_variable_warnings]=$(grep -c "unused variable" "$BUILD_LOG" 2>/dev/null || echo 0)
}

# Extract artifact size information
parse_artifact_sizes() {
    # Parse rootfs size if available in log
    local rootfs_line=$(grep "rootfs.tar.gz" "$BUILD_LOG" | grep -o "[0-9.]\+[MG]" | head -1 || echo "0M")
    if [[ "$rootfs_line" =~ ([0-9.]+)([MG]) ]]; then
        local size=${BASH_REMATCH[1]}
        local unit=${BASH_REMATCH[2]}
        if [[ "$unit" == "G" ]]; then
            METRICS[rootfs_size_mb]=$(echo "$size * 1024" | bc -l 2>/dev/null | cut -d. -f1)
        else
            METRICS[rootfs_size_mb]=$(echo "$size" | cut -d. -f1)
        fi
    fi
    
    # Count kernel modules built
    METRICS[kernel_modules]=$(grep -c "\.ko" "$BUILD_LOG" 2>/dev/null || echo 0)
}

# Extract quality indicators
parse_quality_metrics() {
    # Check for successful recipe completions
    METRICS[recipes_completed]=$(grep -c "Completed" "$BUILD_LOG" 2>/dev/null || echo 0)
    
    # Check for failed tasks
    METRICS[failed_tasks]=$(grep -c "FAILED" "$BUILD_LOG" 2>/dev/null || echo 0)
    
    # Detect memory pressure during build
    local oom_kills=$(grep -c "Out of memory" "$BUILD_LOG" 2>/dev/null || echo 0)
    METRICS[oom_events]=$oom_kills
    
    # Check for disk space warnings
    local disk_warnings=$(grep -c -i "no space left" "$BUILD_LOG" 2>/dev/null || echo 0)
    METRICS[disk_space_warnings]=$disk_warnings
}

# Extract compiler and toolchain information
parse_toolchain_info() {
    # Extract GCC version if mentioned
    local gcc_version=$(grep -o "gcc version [0-9.]\+" "$BUILD_LOG" | head -1 | cut -d' ' -f3 || echo "unknown")
    METRICS[gcc_version]="\"$gcc_version\""
    
    # Check for cross-compilation target
    local target_arch=$(grep -o "aarch64-xilinx-linux" "$BUILD_LOG" | head -1 || echo "unknown")
    METRICS[target_architecture]="\"$target_arch\""
}

# Main parsing execution
main() {
    echo "Parsing build log: $BUILD_LOG" >&2
    
    parse_build_duration
    parse_issues
    parse_artifact_sizes
    parse_quality_metrics
    parse_toolchain_info
    
    # Add metadata
    METRICS[log_file]="\"$BUILD_LOG\""
    METRICS[parsed_at]="\"$(date -Iseconds)\""
    METRICS[log_size_bytes]=$(stat -c%s "$BUILD_LOG" 2>/dev/null || echo 0)
    
    # Output JSON formatted metrics
    echo "{"
    local first=true
    for key in "${!METRICS[@]}"; do
        if [[ "$first" == true ]]; then
            first=false
        else
            echo ","
        fi
        
        # Handle string vs numeric values
        if [[ "${METRICS[$key]}" =~ ^\".*\"$ ]]; then
            printf "  \"%s\": %s" "$key" "${METRICS[$key]}"
        else
            printf "  \"%s\": %s" "$key" "${METRICS[$key]}"
        fi
    done
    echo ""
    echo "}"
}

# Execute main function
main "$@"
