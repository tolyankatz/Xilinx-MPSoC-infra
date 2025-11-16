# CI/CD Lab - Manual Setup

Simple CI/CD lab for ZCU102 BSP testing with manual Gitea/Jenkins configuration.

## Quick Start

```powershell
# Step 1: Start Gitea and MinIO
docker-compose --profile git-commit up -d

# Configure Gitea and MinIO via web UI (see DEPLOY_AND_TEST.md)

# Step 2: Start everything
docker-compose --profile full up -d --build
```

Then follow **DEPLOY_AND_TEST.md** for complete setup.

## Services

- **Gitea**: http://localhost:3000 (Git server)
- **Jenkins**: http://localhost:8080 (CI/CD)
- **MinIO**: http://localhost:9001 (Artifact storage)
- **Host Controller**: SSH on port 2223 (Test execution)

## Credentials

All services: `admin` / `password`

## Pipelines

### Jenkinsfile (Simple)
Basic CI/CD: Build → Test → Publish → Deploy

### Jenkinsfile-complete (Full)
Complete E2E: Build → Unit Tests → Publish → Deploy → E2E Tests → Report

## Documentation

1. **DEPLOY_AND_TEST.md** - Complete setup and usage guide
2. **VISUAL_GUIDE.md** - Step-by-step visual instructions
3. **MANUAL_SETUP_SUMMARY.md** - Quick reference

## Key Feature

✅ **All Git operations via Gitea Web UI** - No command line needed!
✅ **Two Jenkinsfiles** - Simple and Complete pipelines
✅ **Manual configuration** - Full control via web interfaces

## Architecture

```
Gitea (zcu102-bsp repo)
    ↓
Jenkins (Pipeline)
    ↓
Build BSP → Test → Publish to MinIO
    ↓
Deploy to Host Controller → Run Tests
    ↓
Results in MinIO (test-results bucket)
```

## Manual Configuration

This setup requires manual configuration of:
1. Gitea (web setup, create repo)
2. Jenkins (install plugins, create pipeline)
3. Pipeline job (configure Git source)

See **DEPLOY_AND_TEST.md** for step-by-step instructions.
