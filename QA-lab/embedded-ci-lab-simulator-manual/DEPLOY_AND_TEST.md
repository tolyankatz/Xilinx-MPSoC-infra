# Deploy and Test - Staged Manual Setup

## Overview

**Two-step deployment** - Configure Gitea/MinIO first, then add Jenkins.
**All Git operations via Gitea Web UI** - No command line needed!

## Deployment Process

### Step 1: Gitea and MinIO (5 min)

#### 1.1 Start Gitea and MinIO

```powershell
cd QA-lab/embedded-ci-lab-simulator-manual
docker-compose --profile git-commit up -d
```

This starts only Gitea and MinIO.

#### 1.2 Configure Gitea

1. Open browser: http://localhost:3000
2. You'll see Gitea install page
3. Settings:
   - Database Type: **SQLite3** (default)
   - Scroll down to "Administrator Account Settings"
   - Username: `admin`
   - Password: `password`
   - Email: `admin@example.com`
4. Click **"Install Gitea"**
5. Login with `admin` / `password`

#### 1.3 Create Repository in Gitea

1. Click **"+"** icon (top right)
2. Select **"New Repository"**
3. Repository Name: `zcu102-bsp`
4. Make it **Public**
5. Click **"Create Repository"**

#### 1.4 Add Jenkinsfile via Web UI

1. You're now in the empty `zcu102-bsp` repository
2. Click **"New File"** button
3. Filename: `Jenkinsfile`
4. Open `project_repo/Jenkinsfile` on your computer
5. Copy ALL content (Ctrl+A, Ctrl+C)
6. Paste into Gitea editor (Ctrl+V)
7. Commit message: `Add Jenkinsfile`
8. Click **"Commit Changes"**

✅ Jenkinsfile is now in Gitea!

#### 1.5 (Optional) Add Jenkinsfile-complete

1. In `zcu102-bsp` repository, click **"New File"**
2. Filename: `Jenkinsfile-complete`
3. Open `project_repo/Jenkinsfile-complete` on your computer
4. Copy and paste content
5. Commit message: `Add complete pipeline`
6. Click **"Commit Changes"**

✅ Now you have TWO Jenkinsfiles in the repo!

#### 1.6 Configure MinIO

1. Open browser: http://localhost:9001
2. Login: `admin` / `password`
3. Click **"Buckets"** (left sidebar)
4. Click **"Create Bucket"**
5. Bucket Name: `artifacts`
6. Click **"Create Bucket"**
7. Repeat for bucket: `test-results`

✅ MinIO buckets created!

---

### Step 2: Jenkins and Host Controller (5 min)

#### 2.1 Start All Services

```powershell
docker-compose --profile full up -d --build
```

This builds and starts Jenkins, Host Controller, and DUT Simulator.

#### 2.2 Get Jenkins Password

```powershell
docker-compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Copy the password.

#### 2.3 Setup Jenkins

1. Open browser: http://localhost:8080
2. Paste the password
3. Click **"Install suggested plugins"**
4. Wait 2-3 minutes for plugins to install
5. Create admin user:
   - Username: `admin`
   - Password: `password`
   - Full name: `Admin`
   - Email: `admin@example.com`
6. Click **"Save and Continue"**
7. Click **"Save and Finish"**
8. Click **"Start using Jenkins"**

✅ Jenkins is ready!

#### 2.4 Create Pipeline Job

1. Click **"New Item"** (left sidebar)
2. Name: `ZCU102-BSP-Pipeline`
3. Select **"Pipeline"**
4. Click **"OK"**

#### 2.5 Configure Pipeline

1. Scroll to **"Pipeline"** section
2. Definition: **"Pipeline script from SCM"**
3. SCM: **"Git"**
4. Repository URL: `http://gitea:3000/admin/zcu102-bsp.git`

#### 2.6 Add Git Credentials

1. Click **"Add"** next to Credentials → **"Jenkins"**
2. Kind: **"Username with password"**
3. Username: `admin`
4. Password: `password`
5. ID: `gitea-creds`
6. Description: `Gitea Admin`
7. Click **"Add"**
8. Select `admin/***` from Credentials dropdown

#### 2.7 Finish Configuration

1. Branch Specifier: `*/main` (or `*/master`)
2. Script Path: `Jenkinsfile`
3. Click **"Save"**

✅ Pipeline configured!

---

## Run the Pipeline

### First Run

1. Go to http://localhost:8080/job/ZCU102-BSP-Pipeline/
2. Click **"Build Now"** (left sidebar)
3. Watch build appear in Build History
4. Click on build number (e.g., #1)
5. Click **"Console Output"**
6. Watch the pipeline execute!

Expected stages:
- ✅ Checkout
- ✅ Build
- ✅ Test
- ✅ Publish
- ✅ Deploy to Test

### View Results

**MinIO Console**: http://localhost:9001
- Bucket: `artifacts`
- File: `zcu102-bsp-1.tar.gz`

## Using Jenkinsfile-complete

If you added `Jenkinsfile-complete` to Gitea:

### Create Second Pipeline

1. Jenkins → **"New Item"**
2. Name: `ZCU102-Complete-Pipeline`
3. Type: **"Pipeline"**
4. Configure same as before BUT:
   - Script Path: `Jenkinsfile-complete`
5. Save and Build Now

This pipeline includes:
- Build BSP
- Unit Tests
- Publish Artifact
- Deploy to Host Controller
- **Execute End-to-End Tests** ← NEW
- **Collect Test Results** ← NEW
- **Generate Report** ← NEW

Results in MinIO `test-results` bucket!

## Installing test_host Framework (Optional)

For real test execution in Jenkinsfile-complete:

```powershell
# Copy test_host to host_controller
docker cp ../../test_host embedded-ci-lab-simulator-manual-host_controller-1:/home/jenkins/

# Install Python
docker-compose exec host_controller bash -c "
    apt-get update && apt-get install -y python3 python3-pip python3-venv
    cd /home/jenkins
    python3 -m venv venv
    . venv/bin/activate
    pip install -r test_host/requirements.txt
"
```

Now Jenkinsfile-complete will use the actual test framework!

## Useful Commands

### Check Status
```powershell
docker-compose ps
```

### Stop All Services
```powershell
docker-compose --profile full down
```

### Stop Only Gitea/MinIO
```powershell
docker-compose --profile git-commit down
```

### View Logs
```powershell
docker-compose logs jenkins
docker-compose logs host_controller
```

### Test SSH
```powershell
ssh -i ssh_keys/jenkins_id_rsa jenkins@localhost -p 2223
```

## Summary

✅ **git-commit profile**: Gitea + MinIO → Configure manually
✅ **full profile**: All services → Configure Jenkins
✅ **Two Jenkinsfiles**: Simple and Complete
✅ **All via Web UI**: No command line Git needed
✅ **Test Results**: Stored in MinIO

See **VISUAL_GUIDE.md** for step-by-step screenshots guide.
