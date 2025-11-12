# Jenkins CI/CD Configuration Guide

## Overview
This guide provides step-by-step instructions to configure Jenkins for automated ZCU102 BSP hardware validation triggered by Artifactory artifact deployment.

## Prerequisites

### Required Jenkins Plugins

Install the following plugins through **Manage Jenkins > Manage Plugins**:

#### Core Pipeline Plugins
- **Pipeline: Groovy** - Core pipeline functionality
- **Pipeline: Stage View** - Visual pipeline representation
- **Pipeline: Job** - Pipeline job type support
- **Workflow: Aggregator** - Complete pipeline plugin set

#### Integration Plugins
- **Artifactory Plugin** - JFrog Artifactory integration and triggers
- **SSH Agent Plugin** - Secure SSH credential management
- **SSH Pipeline Steps** - SSH execution within pipelines

#### Notification Plugins
- **Slack Notification Plugin** - Slack integration for notifications
- **Email Extension Plugin** - Enhanced email notifications
- **Build Timeout Plugin** - Pipeline timeout management

#### Testing & Reporting Plugins
- **JUnit Plugin** - Test result publishing
- **HTML Publisher Plugin** - HTML report publishing
- **Build Timestamp Plugin** - Adds timestamp to builds

### System Requirements
- Jenkins version 2.400+ (LTS recommended)
- Java 11 or 17
- Network access to:
  - JFrog Artifactory server
  - Test Host machine(s)
  - Slack workspace (if using notifications)
  - Email server (if using email notifications)

## Step-by-Step Configuration

### Step 1: Configure Artifactory Integration

1. Navigate to **Manage Jenkins > Configure System**
2. Scroll to **JFrog** section
3. Click **Add JFrog Platform Instance**
4. Configure the following:
   ```
   Instance ID: primary-artifactory
   JFrog Platform URL: https://artifactory.company.com
   Username: jenkins-service-account
   Password: [Use secure credentials]
   ```
5. Click **Test Connection** to verify
6. Save configuration

### Step 2: Setup SSH Credentials

#### Create SSH Key Pair
On your Jenkins controller or a secure machine:
```bash
# Generate SSH key pair for Jenkins
ssh-keygen -t rsa -b 4096 -C "jenkins@company.com" -f jenkins_test_host_key

# Copy public key to test host
ssh-copy-id -i jenkins_test_host_key.pub testuser@test-host-01.lab
```

#### Add SSH Credentials to Jenkins
1. Navigate to **Manage Jenkins > Manage Credentials**
2. Select appropriate domain (usually "Global")
3. Click **Add Credentials**
4. Configure SSH credential:
   ```
   Kind: SSH Username with private key
   Scope: Global
   ID: jenkins-test-host-key
   Username: testuser
   Private Key: [Paste contents of jenkins_test_host_key]
   Passphrase: [If key is encrypted]
   ```

#### Add Test Host Endpoint Credentials
1. Add another credential for the test host endpoint:
   ```
   Kind: Secret text
   Scope: Global  
   Secret: test-host-01.lab
   ID: test-host-endpoint
   ```

2. Add test host username:
   ```
   Kind: Secret text
   Scope: Global
   Secret: testuser  
   ID: test-host-user
   ```

### Step 3: Configure Notification Systems

#### Slack Integration (Optional)
1. In Slack, create an incoming webhook for your channel
2. In Jenkins, navigate to **Manage Jenkins > Configure System**
3. Find **Slack** section and configure:
   ```
   Workspace: your-workspace
   Credential: [Add webhook URL as secret text]
   Default Channel: #bsp-validation
   ```

#### Email Configuration (Optional)
1. Navigate to **Manage Jenkins > Configure System**
2. Configure **Extended E-mail Notification**:
   ```
   SMTP Server: smtp.company.com
   SMTP Port: 587
   Username: jenkins@company.com
   Password: [Email account password]
   Use SSL/TLS: Yes
   Default Recipients: bsp-team@company.com
   ```

### Step 4: Create Pipeline Job

1. Click **New Item** in Jenkins
2. Enter job name: `ZCU102-BSP-Hardware-Validation`
3. Select **Pipeline** job type
4. Click **OK**

#### Configure Pipeline Job
1. **General Configuration**:
   - Description: `Automated hardware validation for ZCU102 BSP artifacts`
   - Check **Discard old builds**: Keep 30 builds
   - Check **This project is parameterized** (parameters defined in Jenkinsfile)

2. **Build Triggers**:
   - The Artifactory trigger is defined in the Jenkinsfile
   - Optionally enable **Build periodically** for maintenance: `H 2 * * 0` (weekly)

3. **Pipeline Configuration**:
   ```
   Definition: Pipeline script from SCM
   SCM: Git
   Repository URL: https://git.company.com/bsp/xilinx-mpsoc-infra.git
   Credentials: [Your Git credentials]
   Branch: main
   Script Path: Jenkinsfile
   ```

4. **Advanced Options**:
   - Lightweight checkout: Enabled
   - Shallow clone: Enabled (if repository is large)

### Step 5: Test Host Setup

#### Install Framework Dependencies
On the test host (`test-host-01.lab`):

```bash
# Create framework user (if not exists)
sudo useradd -m -s /bin/bash testuser
sudo usermod -a -G dialout,tty testuser

# Switch to framework user
sudo su - testuser

# Create directory structure
sudo mkdir -p /opt/zcu102-bsp-validation
sudo chown -R testuser:testuser /opt/zcu102-bsp-validation

# Clone repository
cd /opt/zcu102-bsp-validation
git clone https://git.company.com/bsp/xilinx-mpsoc-infra.git .

# Setup Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Make controller script executable
chmod +x scripts/run_hw_tests.sh

# Create log directories
mkdir -p logs test-results screenshots manifests
```

#### Configure Hardware Access
```bash
# Add user to hardware access groups
sudo usermod -a -G dialout,tty,plugdev testuser

# Configure udev rules for ZCU102 (if needed)
sudo tee /etc/udev/rules.d/99-zcu102.rules << EOF
# ZCU102 JTAG/UART access
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6010", GROUP="dialout", MODE="0666"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6010", GROUP="plugdev", MODE="0666"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### Verify SSH Access
From Jenkins controller, test SSH access:
```bash
ssh -i jenkins_test_host_key testuser@test-host-01.lab 'hostname && date'
```

### Step 6: Configure Artifactory Triggers

1. In Artifactory, navigate to your BSP repository
2. Configure webhooks for artifact deployment:
   ```
   URL: https://jenkins.company.com/job/ZCU102-BSP-Hardware-Validation/build
   Events: Artifact Deployed
   Repository: bsp-builds, bsp-dev-builds, bsp-security
   Path Pattern: **/*.yaml
   ```

### Step 7: Testing the Pipeline

#### Manual Test Execution
1. Navigate to the pipeline job in Jenkins
2. Click **Build with Parameters**
3. Enter test parameters:
   ```
   MANIFEST_PATH: bsp-main-137.yaml
   BUILD_ID: bsp-main-137
   TEST_SCOPE: smoke
   FORCE_DEPLOYMENT: false
   ```
4. Click **Build**

#### Verify Artifactory Trigger
1. Upload a new BSP manifest to Artifactory
2. Verify the pipeline is triggered automatically
3. Check build logs for proper execution

## Monitoring and Maintenance

### Log Management
- Jenkins build logs: Automatic cleanup after 30 builds
- Test host logs: Located in `/opt/zcu102-bsp-validation/logs/`
- Log rotation: Configure with `logrotate`

### Health Checks
Create a simple monitoring script:
```bash
#!/bin/bash
# /opt/zcu102-bsp-validation/scripts/health_check.sh

# Check framework availability
test -x /opt/zcu102-bsp-validation/scripts/run_hw_tests.sh || exit 1

# Check hardware connectivity
test -c /dev/ttyUSB0 || exit 1  # Adjust for your setup

# Check Python environment
source /opt/zcu102-bsp-validation/venv/bin/activate
python3 -c "import pytest, yaml, requests" || exit 1

echo "Health check passed"
```

### Backup and Recovery
1. **Jenkins Configuration**: Use Configuration as Code (JCasC) plugin
2. **Test Host**: Regular backup of `/opt/zcu102-bsp-validation/`
3. **Credentials**: Store in secure credential management system

## Troubleshooting

### Common Issues

#### Pipeline Not Triggered
- Verify Artifactory webhook configuration
- Check Jenkins webhook URL accessibility
- Review Artifactory plugin logs

#### SSH Connection Failures
- Verify SSH key permissions (600)
- Check firewall rules between Jenkins and test host
- Validate SSH agent plugin configuration

#### Test Execution Failures
- Check test host hardware connections
- Verify Python virtual environment
- Review framework logs on test host

#### Missing Test Results
- Verify `test-results/` directory permissions
- Check JUnit XML format validity
- Review artifact archiving patterns

### Debug Commands
```bash
# Test SSH connectivity
ssh -vvv testuser@test-host-01.lab

# Check Jenkins agent logs
tail -f /var/log/jenkins/jenkins.log

# Verify Artifactory connectivity
curl -u username:password https://artifactory.company.com/artifactory/api/system/ping

# Test framework directly
sudo su - testuser
cd /opt/zcu102-bsp-validation
./scripts/run_hw_tests.sh --help
```

## Security Best Practices

1. **Credentials Management**:
   - Never store passwords in plain text
   - Use Jenkins credential store
   - Rotate SSH keys regularly

2. **Network Security**:
   - Restrict Jenkins webhook access
   - Use VPN for test host access
   - Enable SSH key-only authentication

3. **Access Control**:
   - Implement role-based access in Jenkins
   - Limit test host user privileges
   - Regular security audits

## Performance Optimization

1. **Pipeline Optimization**:
   - Use parallel stages where possible
   - Implement pipeline restart from failed stage
   - Cache dependencies in virtual environment

2. **Resource Management**:
   - Limit concurrent pipeline executions
   - Monitor test host resource usage
   - Implement queue management for hardware access

3. **Artifact Management**:
   - Implement artifact cleanup policies
   - Use artifact checksums for integrity
   - Compress logs and results

This configuration provides a robust, automated pipeline for ZCU102 BSP hardware validation with proper error handling, notifications, and monitoring capabilities.
