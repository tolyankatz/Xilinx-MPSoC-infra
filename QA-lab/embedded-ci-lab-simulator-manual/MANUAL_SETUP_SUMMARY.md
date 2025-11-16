# Manual Setup Summary

## Key Point: All Git Operations via Web UI

**No command line Git needed!** Everything is done through Gitea's web interface.

## Adding Files to Gitea

### Method 1: Create New File
1. Go to your repository in Gitea
2. Click **"New File"**
3. Enter filename (e.g., `Jenkinsfile`)
4. Paste content
5. Click **"Commit Changes"**

### Method 2: Edit Existing File
1. Go to your repository in Gitea
2. Click on the file
3. Click **"Edit"** (pencil icon)
4. Modify content
5. Click **"Commit Changes"**

### Method 3: Upload File
1. Go to your repository in Gitea
2. Click **"Upload File"**
3. Drag and drop or browse
4. Click **"Commit Changes"**

## Two Jenkinsfiles in Same Repo

You can have both files in the `zcu102-bsp` repository:

```
zcu102-bsp/
├── Jenkinsfile          ← Simple pipeline
└── Jenkinsfile-complete ← Full E2E pipeline
```

Then create two Jenkins jobs:
- Job 1: Script Path = `Jenkinsfile`
- Job 2: Script Path = `Jenkinsfile-complete`

## Quick Reference

### Gitea
- URL: http://localhost:3000
- Login: admin/password
- Create repo → Add files via web UI

### Jenkins
- URL: http://localhost:8080
- Login: admin/password
- Create pipeline → Point to Gitea repo

### MinIO
- URL: http://localhost:9001
- Login: admin/password
- View artifacts and test results

## File Locations

### On Your Computer
- `project_repo/Jenkinsfile` - Simple pipeline
- `project_repo/Jenkinsfile-complete` - Full pipeline

### In Gitea (after manual upload)
- http://localhost:3000/admin/zcu102-bsp
- Files: `Jenkinsfile` and/or `Jenkinsfile-complete`

### In Jenkins
- Workspace: `/var/jenkins_home/workspace/ZCU102-BSP-Pipeline/`
- Jenkins clones from Gitea automatically

## Workflow

```
1. Edit file on your computer
   ↓
2. Copy content
   ↓
3. Paste in Gitea web UI
   ↓
4. Commit via web UI
   ↓
5. Jenkins detects change (if polling enabled)
   ↓
6. Or manually click "Build Now" in Jenkins
   ↓
7. Pipeline runs
```

## No Command Line Needed!

All operations through web browsers:
- ✅ Gitea web UI for Git operations
- ✅ Jenkins web UI for pipeline management
- ✅ MinIO web UI for viewing results

Simple and visual!
