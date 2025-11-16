# Git and Jenkins Setup Guide

## Git Repository Setup

### 1. Gitea Configuration
- **URL**: http://localhost:3000
- **Admin Credentials**: admin / password
- **Status**: ✅ Initialized and ready

### 2. Repository Creation
The BSP Validation Framework monorepo is ready to be pushed:

```bash
cd zcu102-bsp-validation-monorepo
git remote add origin http://localhost:3000/admin/zcu102-bsp-validation-monorepo.git
git push -u origin master
```

### 3. Repository Structure
```
zcu102-bsp-validation-monorepo/
├── README.md                    # Main documentation
├── DEVELOPER_GUIDE.md           # Development workflow
├── Jenkinsfile                  # CI/CD pipeline definition
├── docs/
│   ├── architecture.md          # System architecture
│   └── requirements.md          # System requirements
├── scripts/
│   ├── publish_artifacts_to_minio.sh
│   ├── download_artifacts_from_minio.sh
│   └── list_artifacts.sh
└── test_host/
    ├── config.yaml              # Test configuration
    ├── run_tests.py             # Main test orchestrator
    ├── framework/               # Test modules
    │   ├── boot_validator.py
    │   ├── uart_test.py
    │   └── ethernet_test.py
    └── hardware_control/        # Hardware control modules
        ├── power_controller.py
        └── jtag_controller.py
```

## Jenkins Configuration

### 1. Current Status
- **URL**: http://localhost:8080
- **Status**: ✅ Fully operational
- **Admin Credentials**: admin / password (configured via security.groovy)
- **Plugins Installed**: git, ssh-agent, workflow-aggregator, job-dsl, configuration-as-code, gitea, docker-workflow, credentials

### 2. Issues Fixed

The following issues were resolved during deployment:

#### Issue 1: BlueOcean Plugin Dependency
- **Problem**: BlueOcean plugin caused sse-gateway plugin conflicts leading to Jenkins startup failure
- **Solution**: Removed blueocean from plugins.txt, replaced with workflow-aggregator for pipeline support
- **Files Modified**: `jenkins/plugins.txt`

#### Issue 2: Job-DSL CasC Configuration Error
- **Problem**: Configuration-as-Code (CasC) failed during boot when attempting to create jobs via job-dsl scripts
- **Solution**: Removed automatic job creation from casc.yaml - jobs now created manually via UI
- **Files Modified**: `jenkins/casc.yaml`

### 3. Current Configuration

Jenkins is now successfully running with:
- Security configured via groovy init script (admin/password)
- Gitea server integration configured
- Credentials pre-configured (gitea-admin-creds, minio-credentials)
- Ready for manual job creation

### 4. Manual Setup Steps

#### Step 1: Access Jenkins
1. Open http://localhost:8080 in browser
2. Login with credentials: admin / password
3. No initial setup wizard required (handled by CasC)

#### Step 2: Install Required Plugins
Install these plugins via Manage Jenkins → Manage Plugins:
- `gitea` - For Gitea integration
- `workflow-multibranch` - For multibranch pipelines
- `docker-workflow` - For Docker pipeline support
- `credentials` - For credential management

#### Step 3: Configure Gitea Integration
1. Go to Manage Jenkins → Configure System
2. Add Gitea server:
   - Name: `gitea`
   - Server URL: `http://gitea:3000`
   - Credentials: Add username/password (admin/password)

#### Step 4: Create Multibranch Pipeline
1. New Item → Multibranch Pipeline
2. Name: `bsp-validation-pipeline`
3. Branch Sources → Add Source → Gitea
4. Select the `zcu102-bsp-validation-monorepo` repository
5. Save and Jenkins will scan the repository

### 3. Pipeline Configuration
The `Jenkinsfile` in the repository defines:
- **Stages**:
  - Checkout: Clone repository
  - Simulated BSP Build: Mock build process
  - Publish Artifacts: Upload to Minio
  - Hardware Validation: Run test framework
  - Publish Results: Upload test results

### 4. Credentials Configuration
Add these credentials in Jenkins → Manage Jenkins → Manage Credentials:
- **Minio Credentials**:
  - Username: `admin`
  - Password: `password`
  - ID: `minio-credentials`

### 5. Environment Variables
The pipeline uses these environment variables:
- `MINIO_ENDPOINT`: `http://minio:9000`
- `MINIO_ACCESS_KEY`: `admin`
- `MINIO_SECRET_KEY`: `password`

## Integration Workflow

### 1. Development Workflow
1. Make changes to BSP Validation Framework
2. Commit and push to Gitea
3. Jenkins automatically triggers pipeline
4. Tests run in Docker environment
5. Results published to Minio

### 2. Test Execution
Tests can be run locally:
```bash
# From host_controller container
python3 /app/test_host/run_tests.py --config /app/test_host/config.yaml --test-suite smoke --skip-download
```

### 3. Artifact Management
- **Source Artifacts**: Stored in `minio/bsp-firmware/`
- **Test Logs**: Stored in `minio/test-logs/`
- **Build Metadata**: `deployment_manifest.yaml`

## Troubleshooting

### Jenkins Issues
- **Plugin Conflicts**: Remove problematic plugins via CLI
- **Memory Issues**: Increase JVM memory in docker-compose.yml
- **Permission Issues**: Ensure Jenkins user has Docker access

### Git Issues
- **Authentication**: Use username/password for HTTP access
- **Repository Creation**: Create via web UI if API fails
- **SSH Keys**: Configure SSH keys for passwordless access

### Network Issues
- **Service Discovery**: Use container names (gitea, minio, jenkins)
- **Port Conflicts**: Check port mappings in docker-compose.yml
- **Firewall**: Ensure ports 3000, 8080, 9000 are accessible

## Next Steps

1. **Complete Jenkins Setup**: Follow manual steps above
2. **Push Repository**: Upload monorepo to Gitea
3. **Configure Pipeline**: Set up multibranch pipeline
4. **Test Integration**: Verify CI/CD workflow
5. **Monitor Results**: Check Minio for artifacts and logs

## Service URLs Summary

- **Gitea**: http://localhost:3000 (admin/password)
- **Jenkins**: http://localhost:8080 (setup required)
- **Minio**: http://localhost:9000 (admin/password)
- **Minio Console**: http://localhost:9001
- **Host Controller SSH**: ssh://localhost:2223 (jenkins/jenkins)
