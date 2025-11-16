# End-to-End Command List
**Location**: C:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator  
**Purpose**: Manual execution commands for complete system validation (PowerShell)

---

## 🚀 Quick Start - Full End-to-End Execution

### Option 1: Complete System Reset & Validation
```powershell
# 1. Clean shutdown and remove all volumes
docker-compose down -v

# 2. Rebuild and start all services
docker-compose up -d --build

# 3. Wait for Jenkins to initialize (2-3 minutes)
docker-compose logs -f jenkins

# 4. Run smoke tests
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite smoke --skip-download

# 5. Run full regression tests
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download
```

### Option 2: Quick Validation (No Reset)
```powershell
# 1. Check all services are running
docker-compose ps

# 2. Run regression test suite
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download

# 3. Verify test logs in Minio
docker-compose exec host_controller mc ls minio/test-logs
```

---

## 📋 Detailed Command List

### 1. System Management Commands

#### Start All Services
```powershell
docker-compose up -d --build
```

#### Stop All Services
```powershell
docker-compose down
```

#### Clean Reset (Remove All Data)
```powershell
docker-compose down -v
```

#### Check Service Status
```powershell
docker-compose ps
```

#### View Service Logs
```powershell
# All services
docker-compose logs

# Specific service
docker-compose logs jenkins
docker-compose logs gitea
docker-compose logs minio
docker-compose logs host_controller
docker-compose logs dut_simulator

# Follow logs in real-time
docker-compose logs -f jenkins
```

### 2. Jenkins Commands

#### Wait for Jenkins Initialization
```powershell
docker-compose logs -f jenkins
# Wait for "Jenkins is fully up and running" message
```

#### Check Jenkins Jobs
```powershell
docker-compose exec jenkins ls -la /var/jenkins_home/jobs/
```

#### View Jenkins Job Configuration
```powershell
docker-compose exec jenkins cat /var/jenkins_home/jobs/bsp-build-pipeline/config.xml
docker-compose exec jenkins cat /var/jenkins_home/jobs/zcu102-bsp-validation-pipeline/config.xml
```

#### Trigger Jenkins Build (Manual via Web UI)
1. Open http://localhost:8080
2. Login: admin / admin
3. Click job name
4. Click "Build Now"

#### Check Jenkins Build History
```powershell
docker-compose exec jenkins ls -la /var/jenkins_home/jobs/bsp-build-pipeline/builds/
```

#### View Build Logs
```powershell
docker-compose exec jenkins cat /var/jenkins_home/jobs/bsp-build-pipeline/builds/1/log
```

### 3. Gitea Commands

#### Initialize Gitea (First Time)
```powershell
docker-compose exec host_controller sh -c "curl -X POST http://gitea:3000/install -H 'Content-Type: application/x-www-form-urlencoded' -d 'db_type=SQLite3&db_host=localhost&db_path=/data/gitea/gitea.db&db_user=&db_passwd=&db_name=&app_name=Gitea+Git+with+a+cup+of+tea&repo_root_path=/data/git/repositories&lfs_root_path=/data/git/lfs&run_user=git&domain=localhost&ssh_port=2222&http_port=3000&app_url=http://localhost:3000/&log_root_path=/data/gitea/log&disable_registration=true&require_signin_view=true&default_keep_email_private=false&default_allow_create_organization=true&default_enable_timetracking=true&no_reply_address=noreply.localhost&password_algorithm=pbkdf2&admin_name=admin&admin_password=password&admin_confirm_password=password&admin_email=admin@example.com'"
```

#### Create Repository via API
```powershell
# Create JSON file
@'
{
  "name": "test-repo",
  "description": "Test repository",
  "private": false
}
'@ | Out-File -FilePath "create-repo.json" -Encoding UTF8

# Copy to container
docker cp create-repo.json embedded-ci-lab-simulator-host_controller-1:/tmp/create-repo.json

# Create repository
docker-compose exec host_controller sh -c "curl -X POST http://gitea:3000/api/v1/user/repos -H 'Content-Type: application/json' -d @/tmp/create-repo.json -u admin:password"

# Clean up local file
Remove-Item create-repo.json
```

#### List Repositories
```powershell
docker-compose exec host_controller curl -u admin:password http://gitea:3000/api/v1/user/repos
```

### 4. Test Framework Commands

#### Run Smoke Tests
```powershell
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite smoke --skip-download
```

#### Run Regression Tests
```powershell
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download
```

#### Run Individual Tests
```powershell
# Boot validation only
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite smoke --skip-download `
  --tests boot_validation

# SSH connectivity only
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite smoke --skip-download `
  --tests ssh_connectivity
```

#### View Test Configuration
```powershell
docker-compose exec host_controller cat /app/test_host/config.yaml
```

#### View Test Framework Structure
```powershell
docker-compose exec host_controller ls -la /app/test_host/
docker-compose exec host_controller ls -la /app/test_host/framework/
docker-compose exec host_controller ls -la /app/test_host/hardware_control/
```

### 5. Hardware Control Commands

#### Power Cycle DUT
```powershell
docker-compose exec host_controller python3 -c @"
import sys
sys.path.append('/app/test_host')
from hardware_control.power_controller import PowerController
pc = PowerController()
pc.power_cycle()
"@
```

#### Power ON DUT
```powershell
docker-compose exec host_controller python3 -c @"
import sys
sys.path.append('/app/test_host')
from hardware_control.power_controller import PowerController
pc = PowerController()
pc.power_on()
"@
```

#### Power OFF DUT
```powershell
docker-compose exec host_controller python3 -c @"
import sys
sys.path.append('/app/test_host')
from hardware_control.power_controller import PowerController
pc = PowerController()
pc.power_off()
"@
```

#### View DUT Boot Logs
```powershell
docker-compose logs dut_simulator
```

#### SSH to DUT
```powershell
docker-compose exec host_controller ssh root@dut_simulator "uname -a"
```

### 6. Minio Commands

#### List Buckets
```powershell
docker-compose exec host_controller mc ls minio
```

#### List Test Logs
```powershell
docker-compose exec host_controller mc ls minio/test-logs
```

#### Download Test Log
```powershell
docker-compose exec host_controller mc cp minio/test-logs/test_run_20251115_234945.log /tmp/
docker-compose exec host_controller cat /tmp/test_run_20251115_234945.log
```

#### Upload Test Artifact
```powershell
docker-compose exec host_controller mc cp /app/test_host/config.yaml minio/test-logs/
```

#### View Minio Configuration
```powershell
docker-compose exec host_controller mc config host ls
```

### 7. Git Repository Commands

#### Clone Repository from Gitea
```powershell
Set-Location /tmp
git clone http://admin:password@localhost:3000/admin/zcu102-bsp-validation-monorepo.git
Set-Location zcu102-bsp-validation-monorepo
Get-ChildItem -Force
```

#### Push to Repository
```powershell
Set-Location /tmp/zcu102-bsp-validation-monorepo
git config user.email "admin@example.com"
git config user.name "admin"
git add .
git commit -m "Test commit"
git push origin master:main
```

#### Check Repository Status
```powershell
Set-Location /tmp/zcu102-bsp-validation-monorepo
git status
git log --oneline
```

### 8. Network and Connectivity Tests

#### Test Network Connectivity
```powershell
# Test Gitea from host_controller
docker-compose exec host_controller curl http://gitea:3000/api/v1/version

# Test Jenkins from host_controller  
docker-compose exec host_controller curl http://jenkins:8080/

# Test Minio from host_controller
docker-compose exec host_controller curl http://minio:9000/minio/health/live

# Test DUT connectivity
docker-compose exec host_controller ping -c 3 dut_simulator
```

#### Test SSH Connections
```powershell
# SSH to DUT
docker-compose exec host_controller ssh root@dut_simulator "echo 'SSH test successful'"

# SSH to host_controller from Jenkins container
docker-compose exec jenkins ssh jenkins@host_controller "echo 'Jenkins SSH test successful'"
```

### 9. System Validation Commands

#### Complete Health Check
```powershell
# Check all containers
docker-compose ps

# Check service endpoints
docker-compose exec host_controller curl -s http://gitea:3000/api/v1/version | Select-Object -First 1
docker-compose exec host_controller curl -s http://jenkins:8080/login | Select-Object -First 1
docker-compose exec host_controller curl -s http://minio:9000/minio/health/live

# Run test suite
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download

# Verify artifacts
docker-compose exec host_controller mc ls minio/test-logs | Select-Object -Last 5
```

#### Performance Metrics
```powershell
# System resource usage
docker stats --no-stream

# Network latency test
docker-compose exec host_controller ping -c 10 dut_simulator

# Disk usage
docker-compose exec host_controller df -h
```

### 10. Troubleshooting Commands

#### Check Service Logs for Errors
```powershell
docker-compose logs jenkins | Select-String -Pattern "error" -CaseSensitive
docker-compose logs gitea | Select-String -Pattern "error" -CaseSensitive
docker-compose logs minio | Select-String -Pattern "error" -CaseSensitive
docker-compose logs host_controller | Select-String -Pattern "error" -CaseSensitive
docker-compose logs dut_simulator | Select-String -Pattern "error" -CaseSensitive
```

#### Restart Individual Services
```powershell
docker-compose restart jenkins
docker-compose restart gitea
docker-compose restart minio
docker-compose restart host_controller
docker-compose restart dut_simulator
```

#### Clean Docker System
```powershell
# Remove unused containers and networks
docker system prune -f

# Remove unused images
docker image prune -f

# Remove unused volumes (BE CAREFUL - may delete data)
docker volume prune -f
```

#### Reset Specific Service
```powershell
# Reset Jenkins (remove job configurations)
docker-compose stop jenkins
docker-compose rm -f jenkins
docker-compose up -d jenkins

# Reset Gitea (remove repositories)
docker-compose stop gitea
docker-compose rm -f gitea
docker-compose up -d gitea
```

---

## 🎯 Common Workflows

### Workflow 1: Daily Validation
```powershell
# 1. Check system status
docker-compose ps

# 2. Run regression tests
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download

# 3. Verify test results
docker-compose exec host_controller mc ls minio/test-logs | Select-Object -Last 1
```

### Workflow 2: After Code Changes
```powershell
# 1. Push changes to Gitea
Set-Location zcu102-bsp-validation-monorepo
git add .
git commit -m "Update test framework"
git push gitea master:main

# 2. Trigger Jenkins build manually (via UI)
# Open http://localhost:8080 and build zcu102-bsp-validation-pipeline

# 3. Monitor build results
docker-compose logs -f jenkins
```

### Workflow 3: Full System Reset
```powershell
# 1. Complete shutdown
docker-compose down -v

# 2. Rebuild everything
docker-compose up -d --build

# 3. Wait for services
Start-Sleep -Seconds 60

# 4. Initialize Gitea
docker-compose exec host_controller sh -c "curl -X POST http://gitea:3000/install -H 'Content-Type: application/x-www-form-urlencoded' -d 'db_type=SQLite3&db_host=localhost&db_path=/data/gitea/gitea.db&db_user=&db_passwd=&db_name=&app_name=Gitea+Git+with+a+cup+of+tea&repo_root_path=/data/git/repositories&lfs_root_path=/data/git/lfs&run_user=git&domain=localhost&ssh_port=2222&http_port=3000&app_url=http://localhost:3000/&log_root_path=/data/gitea/log&disable_registration=true&require_signin_view=true&default_keep_email_private=false&default_allow_create_organization=true&default_enable_timetracking=true&no_reply_address=noreply.localhost&password_algorithm=pbkdf2&admin_name=admin&admin_password=password&admin_confirm_password=password&admin_email=admin@example.com'"

# 5. Run validation
docker-compose exec host_controller python3 /app/test_host/run_tests.py `
  --config /app/test_host/config.yaml --test-suite regression --skip-download
```

---

## 📊 Quick Reference

### Service URLs
- Gitea: http://localhost:3000
- Jenkins: http://localhost:8080
- Minio Console: http://localhost:9001

### Credentials
- Gitea: admin / password
- Jenkins: admin / admin
- Minio: admin / password
- Host Controller SSH: jenkins / jenkins
- DUT SSH: root / root

### Key Files
- Test Config: `/app/test_host/config.yaml`
- Test Runner: `/app/test_host/run_tests.py`
- Jenkins Jobs: `/var/jenkins_home/jobs/`
- Gitea Repos: `/data/git/repositories/`
- Minio Buckets: `minio/test-logs/`

---

**Last Updated**: November 16, 2025  
**Validated**: All PowerShell commands tested and functional
