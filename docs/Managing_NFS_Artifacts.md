# Managing NFS Artifacts

## Overview
This document provides comprehensive guidance for managing BSP artifacts using the NFS (Network File System) storage infrastructure. The NFS-based approach replaces Artifactory with a self-hosted filesystem solution that provides versioning, integrity checking, and automated pipeline integration.

## Architecture

### NFS Directory Structure
```
/mnt/nfs_artifacts/bsp/
├── bsp-main-137/
│   ├── BOOT.BIN
│   ├── BOOT.BIN.md5
│   ├── image.ub
│   ├── image.ub.md5
│   ├── system.dtb
│   ├── system.dtb.md5
│   ├── rootfs.tar.gz
│   ├── rootfs.tar.gz.md5
│   ├── deployment_manifest.yaml
│   └── build_metadata.json
├── bsp-dev-2025.11-rc1/
└── bsp-hotfix-2025.11.1/
```

### File Types and Purpose
- **Binary Artifacts**: Core BSP files (BOOT.BIN, image.ub, system.dtb, rootfs.tar.gz)
- **Checksums**: `.md5` files for integrity verification
- **Manifests**: `deployment_manifest.yaml` - Complete deployment specification
- **Metadata**: `build_metadata.json` - Build information and artifact catalog

## Publishing Artifacts

### Automated Publishing (CI/CD Pipeline)
The Jenkins build pipeline automatically publishes artifacts using the `publish_artifacts_to_nfs.sh` script:

```bash
# Example Jenkins pipeline execution
./scripts/publish_artifacts_to_nfs.sh \
    --build-id "bsp-main-138" \
    --source-dir "./build_output" \
    --commit-hash "a1b2c3d4e5f6" \
    --build-type "stable"
```

### Manual Publishing
For development or testing purposes:

```bash
# Publish development build
cd /path/to/xilinx-mpsoc-infra
./scripts/publish_artifacts_to_nfs.sh \
    --build-id "bsp-dev-$(date +%Y%m%d)-test" \
    --source-dir "./my_artifacts" \
    --build-type "development" \
    --no-cleanup
```

### Publishing Parameters
- `--build-id`: Unique identifier for the build
- `--source-dir`: Directory containing artifacts to publish
- `--commit-hash`: Git commit hash for traceability
- `--build-type`: One of `stable`, `development`, `hotfix`
- `--no-cleanup`: Skip automatic cleanup of old builds
- `--retention-days`: Override default retention policy

## Artifact Management

### Listing Artifacts
```bash
# Basic list
./scripts/manage_nfs_artifacts.sh list

# Detailed list with sizes and artifact counts
./scripts/manage_nfs_artifacts.sh list --details

# Sort by creation date (newest first)
./scripts/manage_nfs_artifacts.sh list --details --sort date
```

### Viewing Build Information
```bash
# Show detailed information about a specific build
./scripts/manage_nfs_artifacts.sh info bsp-main-137

# Output includes:
# - Build metadata
# - Artifact list with sizes
# - Creation timestamp
# - Total size
```

### Verifying Integrity
```bash
# Verify all checksums for a build
./scripts/manage_nfs_artifacts.sh verify bsp-main-137

# The script will:
# - Check for presence of all .md5 files
# - Calculate checksums for all artifacts
# - Report any mismatches
# - Return non-zero exit code on failure
```

## Cleanup and Maintenance

### Automatic Cleanup
Cleanup is performed automatically during artifact publishing:
- Default retention: 30 days
- Configurable via `--retention-days` parameter
- Only affects builds older than retention period

### Manual Cleanup
```bash
# Preview what would be cleaned (dry run)
./scripts/manage_nfs_artifacts.sh cleanup --days 30 --dry-run

# Clean artifacts older than 30 days with confirmation
./scripts/manage_nfs_artifacts.sh cleanup --days 30

# Force cleanup without confirmation prompts
./scripts/manage_nfs_artifacts.sh cleanup --days 7 --force
```

### Space Management
Monitor NFS storage usage:
```bash
# Check overall NFS usage
df -h /mnt/nfs_artifacts

# Check per-build usage
./scripts/manage_nfs_artifacts.sh list --details | grep -v "^BUILD_ID"
```

## Filesystem Monitoring and Triggers

### Monitoring Service
The `nfs_artifact_monitor.sh` script provides filesystem-based triggering:

```bash
# Start monitoring in foreground (for debugging)
./scripts/nfs_artifact_monitor.sh --debug

# Start as daemon
./scripts/nfs_artifact_monitor.sh --daemon

# Test configuration
./scripts/nfs_artifact_monitor.sh --test
```

### Configuration
Environment variables for monitoring:
```bash
export JENKINS_URL="http://localhost:8080"
export JENKINS_JOB="ZCU102-BSP-Hardware-Validation"
export JENKINS_TOKEN="your-api-token"
export POLL_INTERVAL=30  # seconds
```

### Trigger Behavior
- Monitors for new `.yaml` manifest files
- Tracks modification timestamps
- Triggers Jenkins builds automatically
- Handles different build types (stable, dev, hotfix) appropriately

## Integration with Test Framework

### Artifact Fetching
The test host controller (`run_hw_tests.sh`) automatically:
1. Validates NFS mount availability
2. Downloads manifest from NFS path
3. Fetches all artifacts listed in manifest
4. Verifies checksums for integrity
5. Creates local workspace with verified artifacts
6. Updates manifest to point to local copies

### Error Handling
Common issues and resolutions:

#### NFS Mount Issues
```bash
# Check if NFS is mounted
mountpoint -q /mnt/nfs_artifacts

# Manual mount (if needed)
sudo mount -t nfs nfs-server:/exports/bsp /mnt/nfs_artifacts
```

#### Permission Issues
```bash
# Check NFS permissions
ls -la /mnt/nfs_artifacts

# Fix ownership (if necessary)
sudo chown -R testuser:testuser /mnt/nfs_artifacts/bsp
```

#### Checksum Failures
```bash
# Investigate checksum mismatch
./scripts/manage_nfs_artifacts.sh verify bsp-main-137

# Re-publish if corruption detected
./scripts/publish_artifacts_to_nfs.sh --build-id bsp-main-137-fixed \
    --source-dir ./corrected_artifacts
```

## Security Considerations

### Access Control
- NFS exports should be restricted to trusted networks
- Use proper firewall rules to limit NFS access
- Consider NFSv4 with Kerberos for authentication
- Regular audit of NFS access logs

### File Integrity
- All artifacts include MD5 checksums
- Checksums are verified before deployment
- Tampered files are automatically rejected
- Consider upgrading to SHA-256 for enhanced security

### Network Security
```bash
# Example NFS export configuration (/etc/exports)
/exports/bsp 192.168.1.0/24(rw,sync,no_subtree_check,root_squash)

# Firewall rules (iptables example)
iptables -A INPUT -p tcp --dport 2049 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p udp --dport 2049 -s 192.168.1.0/24 -j ACCEPT
```

## Troubleshooting

### Common Issues

#### Build Publishing Failures
```bash
# Check NFS mount status
./scripts/publish_artifacts_to_nfs.sh --help

# Verify source directory contents
ls -la /path/to/source/directory

# Check NFS write permissions
touch /mnt/nfs_artifacts/test_write && rm /mnt/nfs_artifacts/test_write
```

#### Pipeline Trigger Issues
```bash
# Test Jenkins connectivity
curl -u user:token http://jenkins:8080/api/json

# Check monitor logs
tail -f /var/log/nfs-artifact-monitor.log

# Verify polling interval
./scripts/nfs_artifact_monitor.sh --test
```

#### Artifact Corruption
```bash
# Check filesystem errors
dmesg | grep -i nfs

# Verify network connectivity
ping nfs-server

# Re-verify all builds
for build in $(ls /mnt/nfs_artifacts/bsp/); do
    ./scripts/manage_nfs_artifacts.sh verify "$build"
done
```

### Debug Mode
Enable verbose logging:
```bash
# Enable debug for all scripts
export DEBUG=true

# Run with detailed output
./scripts/nfs_artifact_monitor.sh --debug
```

### Log Locations
- Artifact Monitor: `/var/log/nfs-artifact-monitor.log`
- NFS Mount: `/var/log/syslog` or `/var/log/messages`
- Jenkins Pipeline: Jenkins build console output
- Test Execution: `/opt/zcu102-bsp-validation/logs/`

## Migration from Artifactory

### Migration Steps
1. **Export existing artifacts** from Artifactory
2. **Organize by build ID** in temporary directory
3. **Bulk publish** using management scripts:
   ```bash
   for build_dir in /tmp/artifactory_export/*; do
       build_id=$(basename "$build_dir")
       ./scripts/publish_artifacts_to_nfs.sh \
           --build-id "$build_id" \
           --source-dir "$build_dir" \
           --no-cleanup
   done
   ```
4. **Update Jenkins configuration** to use NFS paths
5. **Test pipeline execution** with migrated artifacts
6. **Decommission Artifactory** after validation

### Validation Checklist
- [ ] All builds migrated successfully
- [ ] Checksums verified for all artifacts
- [ ] Jenkins pipeline triggers working
- [ ] Test host can fetch artifacts
- [ ] Monitoring service operational
- [ ] Cleanup policies configured

## Performance Optimization

### NFS Tuning
```bash
# Mount options for performance
mount -t nfs -o rsize=8192,wsize=8192,timeo=14,intr \
    nfs-server:/exports/bsp /mnt/nfs_artifacts
```

### Caching Strategy
- Local artifact caching on test hosts
- Parallel artifact downloads when possible
- Cleanup of local cache based on usage

### Monitoring Metrics
Track these metrics for performance:
- Artifact publish time
- Download/verify time
- NFS response time
- Storage utilization
- Pipeline trigger latency

This NFS-based artifact management system provides enterprise-grade reliability while maintaining simplicity and cost-effectiveness compared to commercial solutions like Artifactory.
