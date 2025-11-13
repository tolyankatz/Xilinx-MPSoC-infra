# NFS-Based BSP Validation Deployment Guide

## Overview
This guide provides step-by-step instructions for deploying the complete NFS-based BSP validation infrastructure, replacing Artifactory with a self-hosted filesystem solution.

## Prerequisites

### System Requirements
- **NFS Server**: Ubuntu 20.04+ with at least 500GB storage
- **Jenkins Controller**: 4+ CPU cores, 8GB RAM, 100GB storage
- **Test Hosts**: 2+ CPU cores, 4GB RAM, hardware access (USB/JTAG)
- **Network**: Gigabit Ethernet for NFS performance

### Software Dependencies
- Docker and Docker Compose
- Python 3.8+
- Jenkins 2.400+
- NFS utilities
- Git

### Network Configuration
```bash
# Example network layout
NFS Server:     192.168.1.10
Jenkins:        192.168.1.20
Test Host 1:    192.168.1.30
Test Host 2:    192.168.1.31
```

## Step 1: NFS Server Setup

### 1.1 Install NFS Server
```bash
# On NFS server (192.168.1.10)
sudo apt update
sudo apt install -y nfs-kernel-server

# Create NFS export directory
sudo mkdir -p /exports/bsp
sudo chown nobody:nogroup /exports/bsp
sudo chmod 755 /exports/bsp
```

### 1.2 Configure NFS Exports
```bash
# Edit /etc/exports
sudo tee -a /etc/exports << EOF
/exports/bsp 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash,insecure)
EOF

# Apply configuration
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

### 1.3 Configure Firewall
```bash
# Allow NFS traffic
sudo ufw allow from 192.168.1.0/24 to any port nfs
sudo ufw allow from 192.168.1.0/24 to any port 2049
sudo ufw allow from 192.168.1.0/24 to any port 111

# Enable firewall if not already enabled
sudo ufw --force enable
```

### 1.4 Test NFS Server
```bash
# Verify exports
sudo exportfs -v

# Test local mount
sudo mkdir -p /tmp/test_mount
sudo mount -t nfs localhost:/exports/bsp /tmp/test_mount
sudo touch /tmp/test_mount/test_file
sudo umount /tmp/test_mount
```

## Step 2: Jenkins Controller Setup

### 2.1 Install Docker and Dependencies
```bash
# On Jenkins server (192.168.1.20)
sudo apt update
sudo apt install -y docker.io docker-compose git python3 python3-pip nfs-common

# Add user to docker group
sudo usermod -a -G docker $USER
newgrp docker
```

### 2.2 Deploy Infrastructure Stack
```bash
# Clone repository
git clone https://github.com/company/xilinx-mpsoc-infra.git
cd xilinx-mpsoc-infra

# Create environment file
cat > .env << EOF
# Jenkins Configuration
JENKINS_AGENT_SECRET=your-jenkins-agent-secret
JENKINS_USER=admin
JENKINS_TOKEN=your-jenkins-api-token

# NFS Configuration
NFS_SERVER=192.168.1.10
NFS_EXPORT=/exports/bsp

# Monitoring Configuration
GRAFANA_PASSWORD=secure-password

# Network Configuration
DOCKER_NETWORK_SUBNET=172.20.0.0/16
EOF

# Deploy complete stack
docker-compose -f docker/docker-compose.yml up -d
```

### 2.3 Verify Docker Deployment
```bash
# Check all services are running
docker-compose -f docker/docker-compose.yml ps

# Check NFS mount in containers
docker exec bsp-jenkins ls -la /mnt/nfs_artifacts
docker exec bsp-test-host mountpoint /mnt/nfs_artifacts
```

### 2.4 Configure Jenkins
```bash
# Get Jenkins initial password
docker exec bsp-jenkins cat /var/jenkins_home/secrets/initialAdminPassword

# Access Jenkins UI at http://192.168.1.20:8080
# Complete initial setup and install recommended plugins

# Install additional required plugins via UI:
# - Pipeline
# - SSH Agent
# - Email Extension
# - Build Timeout
```

## Step 3: Test Host Configuration

### 3.1 Physical Test Host Setup
```bash
# On test host (192.168.1.30)
sudo apt update
sudo apt install -y nfs-common python3 python3-pip python3-venv git

# Create test user
sudo useradd -m -s /bin/bash testuser
sudo usermod -a -G dialout,tty,plugdev testuser

# Install framework
sudo mkdir -p /opt/zcu102-bsp-validation
sudo chown -R testuser:testuser /opt/zcu102-bsp-validation

# Switch to test user
sudo su - testuser
cd /opt/zcu102-bsp-validation

# Clone and setup framework
git clone https://github.com/company/xilinx-mpsoc-infra.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/*.sh
```

### 3.2 Configure NFS Mount
```bash
# Create NFS mount point
sudo mkdir -p /mnt/nfs_artifacts

# Add to /etc/fstab for automatic mounting
sudo tee -a /etc/fstab << EOF
192.168.1.10:/exports/bsp /mnt/nfs_artifacts nfs defaults,_netdev 0 0
EOF

# Mount NFS share
sudo mount /mnt/nfs_artifacts

# Verify mount
mountpoint /mnt/nfs_artifacts
ls -la /mnt/nfs_artifacts
```

### 3.3 Configure Hardware Access
```bash
# Add udev rules for ZCU102
sudo tee /etc/udev/rules.d/99-zcu102.rules << EOF
# ZCU102 JTAG/UART access
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6010", GROUP="dialout", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6010", GROUP="plugdev", MODE="0666"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Step 4: Jenkins Pipeline Configuration

### 4.1 Create Jenkins Credentials
Via Jenkins UI (Manage Jenkins > Manage Credentials):

1. **SSH Key for Test Host**:
   - Kind: SSH Username with private key
   - ID: `jenkins-test-host-key`
   - Username: `testuser`
   - Private Key: Upload private key file

2. **NFS Server Address**:
   - Kind: Secret text
   - ID: `nfs-server-address`
   - Secret: `192.168.1.10`

3. **Test Host Endpoint**:
   - Kind: Secret text
   - ID: `test-host-endpoint`
   - Secret: `192.168.1.30`

### 4.2 Create Pipeline Job
```bash
# Create new Pipeline job in Jenkins UI
# Name: ZCU102-BSP-Hardware-Validation
# Type: Pipeline
# Pipeline Definition: Pipeline script from SCM
# Repository URL: https://github.com/company/xilinx-mpsoc-infra.git
# Script Path: Jenkinsfile
```

### 4.3 Test Pipeline Execution
```bash
# Trigger manual build with parameters:
# MANIFEST_PATH: bsp-main-137.yaml
# BUILD_ID: bsp-main-137
# TEST_SCOPE: smoke
# FORCE_DEPLOYMENT: false
```

## Step 5: Artifact Monitor Setup

### 5.1 Configure Monitoring Service
```bash
# On test host or dedicated monitoring server
sudo su - testuser
cd /opt/zcu102-bsp-validation

# Create systemd service
sudo tee /etc/systemd/system/nfs-artifact-monitor.service << EOF
[Unit]
Description=NFS Artifact Monitor Service
After=network.target nfs-client.target

[Service]
Type=simple
User=testuser
Group=testuser
WorkingDirectory=/opt/zcu102-bsp-validation
Environment="PATH=/opt/zcu102-bsp-validation/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="JENKINS_URL=http://192.168.1.20:8080"
Environment="JENKINS_JOB=ZCU102-BSP-Hardware-Validation"
Environment="JENKINS_TOKEN=your-api-token"
ExecStart=/opt/zcu102-bsp-validation/scripts/nfs_artifact_monitor.sh --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable nfs-artifact-monitor
sudo systemctl start nfs-artifact-monitor

# Check service status
sudo systemctl status nfs-artifact-monitor
```

### 5.2 Verify Monitor Operation
```bash
# Check monitor logs
sudo journalctl -u nfs-artifact-monitor -f

# Test with sample artifact
cd /mnt/nfs_artifacts/bsp
sudo mkdir -p test-build-$(date +%s)
sudo cp /path/to/sample/manifest.yaml test-build-*/

# Monitor should detect and trigger pipeline
```

## Step 6: Initial Artifact Publishing

### 6.1 Publish Sample Artifacts
```bash
# Create sample build artifacts
mkdir -p /tmp/sample_artifacts
cd /tmp/sample_artifacts

# Copy sample files (these would come from actual build)
cp /opt/zcu102-bsp-validation/artifacts/bsp-main-137.yaml ./deployment_manifest.yaml

# Create dummy artifacts for testing
dd if=/dev/urandom of=BOOT.BIN bs=1M count=1
dd if=/dev/urandom of=image.ub bs=1M count=10
dd if=/dev/urandom of=system.dtb bs=1K count=50
dd if=/dev/urandom of=rootfs.tar.gz bs=1M count=50

# Publish to NFS
cd /opt/zcu102-bsp-validation
./scripts/publish_artifacts_to_nfs.sh \
    --build-id "test-build-$(date +%Y%m%d)" \
    --source-dir /tmp/sample_artifacts \
    --build-type development \
    --commit-hash "test123456789"
```

### 6.2 Verify Publication
```bash
# List published artifacts
./scripts/manage_nfs_artifacts.sh list --details

# Verify specific build
./scripts/manage_nfs_artifacts.sh verify test-build-$(date +%Y%m%d)

# Check NFS structure
ls -la /mnt/nfs_artifacts/bsp/
```

## Step 7: End-to-End Testing

### 7.1 Manual Pipeline Test
```bash
# Trigger Jenkins build manually
curl -X POST \
  "http://192.168.1.20:8080/job/ZCU102-BSP-Hardware-Validation/buildWithParameters" \
  -u admin:your-token \
  -d "MANIFEST_PATH=test-build-$(date +%Y%m%d)/deployment_manifest.yaml" \
  -d "BUILD_ID=test-build-$(date +%Y%m%d)" \
  -d "TEST_SCOPE=smoke"
```

### 7.2 Test Artifact Fetching
```bash
# On test host, manually test artifact fetching
cd /opt/zcu102-bsp-validation
./scripts/run_hw_tests.sh \
    --manifest-path "test-build-$(date +%Y%m%d)/deployment_manifest.yaml" \
    --build-id "test-build-$(date +%Y%m%d)" \
    --test-scope smoke \
    --force-deployment
```

### 7.3 Validate Complete Flow
1. **Publish new artifact** → Monitor detects → Pipeline triggers
2. **Pipeline executes** → Artifacts downloaded → Tests run
3. **Results collected** → Notifications sent → Reports generated

## Step 8: Monitoring and Observability

### 8.1 Access Monitoring Dashboards
- **Jenkins**: http://192.168.1.20:8080
- **Grafana**: http://192.168.1.20:3000 (admin/secure-password)
- **Kibana**: http://192.168.1.20:5601
- **Prometheus**: http://192.168.1.20:9090

### 8.2 Configure Alerting
```bash
# Example Grafana alert for NFS availability
# Create dashboard panel monitoring NFS mount status
# Set alert condition: mountpoint check fails
# Configure notification channels (Slack, email)
```

## Step 9: Production Hardening

### 9.1 Security Configuration
```bash
# Enable SSL/TLS for Jenkins
# Configure proper authentication
# Restrict network access
# Regular security updates

# Example Jenkins security config
# Manage Jenkins > Configure Global Security
# - Enable security
# - Set security realm (LDAP/AD if available)
# - Configure authorization strategy
# - Enable CSRF protection
```

### 9.2 Backup Strategy
```bash
# NFS data backup
sudo crontab -e
# Add: 0 2 * * * rsync -av /exports/bsp/ /backup/nfs/

# Jenkins configuration backup
# Use Configuration as Code plugin
# Regular backup of JENKINS_HOME

# Database backups (if using external DBs)
```

### 9.3 Performance Tuning
```bash
# NFS server tuning
echo 'net.core.rmem_default = 262144' >> /etc/sysctl.conf
echo 'net.core.rmem_max = 16777216' >> /etc/sysctl.conf
sudo sysctl -p

# Jenkins JVM tuning
# Update JAVA_OPTS in docker-compose.yml
JAVA_OPTS: "-Xmx4g -XX:+UseG1GC -XX:MaxGCPauseMillis=100"
```

## Troubleshooting

### Common Issues and Solutions

#### NFS Mount Failures
```bash
# Check NFS server status
sudo systemctl status nfs-kernel-server

# Verify exports
sudo exportfs -v

# Test network connectivity
ping 192.168.1.10
telnet 192.168.1.10 2049
```

#### Pipeline Failures
```bash
# Check Jenkins logs
docker logs bsp-jenkins

# Verify SSH connectivity
ssh testuser@192.168.1.30 'echo "SSH working"'

# Test NFS from Jenkins
docker exec bsp-jenkins ls -la /mnt/nfs_artifacts
```

#### Monitoring Issues
```bash
# Check monitor service
sudo systemctl status nfs-artifact-monitor
sudo journalctl -u nfs-artifact-monitor -f

# Verify Jenkins API access
curl -u admin:token http://192.168.1.20:8080/api/json
```

## Maintenance Procedures

### Regular Maintenance Tasks
```bash
# Weekly: Clean old artifacts
./scripts/manage_nfs_artifacts.sh cleanup --days 30

# Monthly: Verify all builds
for build in $(ls /mnt/nfs_artifacts/bsp/); do
    ./scripts/manage_nfs_artifacts.sh verify "$build"
done

# Quarterly: Update system packages
sudo apt update && sudo apt upgrade

# As needed: Docker image updates
docker-compose pull && docker-compose up -d
```

### Scaling Considerations
- **Multiple Test Hosts**: Add additional test hosts as needed
- **NFS Performance**: Consider NFS clustering for high load
- **Jenkins Agents**: Add more Docker agents for parallel builds
- **Storage Expansion**: Monitor disk usage and expand as needed

This deployment guide provides a complete, production-ready NFS-based artifact management system that replaces Artifactory while maintaining enterprise-grade functionality and reliability.
