# Visual Step-by-Step Guide

## Adding Jenkinsfile to Gitea (Web UI)

### Step 1: Open Repository
```
Browser → http://localhost:3000/admin/zcu102-bsp
```

### Step 2: Click "New File"
```
[New File] button (top right area)
```

### Step 3: Enter Filename
```
Filename box: Jenkinsfile
```

### Step 4: Copy Content
```
On your computer:
1. Open: QA-lab/embedded-ci-lab-simulator-manual/project_repo/Jenkinsfile
2. Select All (Ctrl+A)
3. Copy (Ctrl+C)
```

### Step 5: Paste in Gitea
```
In Gitea editor:
1. Click in the text area
2. Paste (Ctrl+V)
```

### Step 6: Commit
```
Scroll down:
1. Commit message: "Add Jenkinsfile"
2. Click [Commit Changes] button
```

✅ Done! File is now in Gitea.

## Creating Jenkins Pipeline (Web UI)

### Step 1: Create Job
```
Jenkins → [New Item]
Name: ZCU102-BSP-Pipeline
Type: Pipeline
Click [OK]
```

### Step 2: Configure Source
```
Scroll to "Pipeline" section:
1. Definition: "Pipeline script from SCM"
2. SCM: "Git"
3. Repository URL: http://gitea:3000/admin/zcu102-bsp.git
```

### Step 3: Add Credentials
```
Click [Add] next to Credentials:
1. Kind: "Username with password"
2. Username: admin
3. Password: password
4. ID: gitea-creds
5. Click [Add]
6. Select "admin/***" from dropdown
```

### Step 4: Set Branch and Script
```
1. Branch Specifier: */main
2. Script Path: Jenkinsfile
3. Click [Save]
```

✅ Done! Pipeline is configured.

## Running the Pipeline

### Manual Trigger
```
Jenkins → ZCU102-BSP-Pipeline → [Build Now]
```

### View Results
```
Click on build number (e.g., #1)
Click [Console Output]
Watch the pipeline run!
```

## Adding Second Jenkinsfile

### In Gitea
```
1. Go to: http://localhost:3000/admin/zcu102-bsp
2. Click [New File]
3. Filename: Jenkinsfile-complete
4. Copy content from project_repo/Jenkinsfile-complete
5. Paste and commit
```

### In Jenkins
```
1. [New Item]
2. Name: ZCU102-Complete-Pipeline
3. Type: Pipeline
4. Configure same as before BUT:
   - Script Path: Jenkinsfile-complete
5. Save
```

Now you have TWO pipelines using TWO different Jenkinsfiles!

## Viewing Results

### MinIO Console
```
Browser → http://localhost:9001
Login: admin/password
Navigate to buckets:
- artifacts → BSP files
- test-results → Test logs
```

### Download Test Results
```
MinIO → test-results bucket
Click on file → Download
Or click "Preview" to view in browser
```

## Common Tasks

### Update Jenkinsfile
```
Gitea → zcu102-bsp → Jenkinsfile → [Edit] → Modify → Commit
Jenkins → Pipeline → [Build Now]
```

### View Pipeline History
```
Jenkins → Pipeline → Left sidebar shows build history
Click any build number to see details
```

### Check Logs
```
Jenkins → Build → [Console Output]
Scroll through to see each stage
```

## No Terminal Commands!

Everything through web browsers:
- Gitea: File management
- Jenkins: Pipeline management  
- MinIO: Result viewing

Simple, visual, and easy!
