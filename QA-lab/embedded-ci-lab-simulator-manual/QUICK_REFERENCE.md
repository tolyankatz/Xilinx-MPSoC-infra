# Quick Reference

## Commands

```powershell
# Start Gitea and MinIO
docker-compose --profile git-commit up -d

# Start everything (after configuring Gitea/MinIO)
docker-compose --profile full up -d --build

# Check status
docker-compose ps

# Stop everything
docker-compose --profile full down

# View logs
docker-compose logs jenkins
docker-compose logs host_controller
```

## Configuration Order

### 1. Gitea (http://localhost:3000)
- Install with SQLite3
- Create admin user: admin/password
- Create repo: `zcu102-bsp`
- Add `Jenkinsfile` via web UI

### 2. MinIO (http://localhost:9001)
- Login: admin/password
- Create buckets: `artifacts`, `test-results`

### 3. Jenkins (http://localhost:8080)
- Get password: `docker-compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`
- Install plugins, create admin user
- Create pipeline pointing to Gitea repo

## URLs

- **Gitea**: http://localhost:3000 (admin/password)
- **Jenkins**: http://localhost:8080 (admin/password)
- **MinIO**: http://localhost:9001 (admin/password)

### Update etc Host file with Getea record
- C:\Windows\System32\drivers\etc\hosts
- Add: `127.0.0.1 gitea`

## Two Pipelines

### Simple Pipeline
- File: `Jenkinsfile`
- Stages: Build → Test → Publish → Deploy
- Duration: ~30 seconds
- repo:http://gitea:3000/admin/zcu102-bsp.git


### Complete Pipeline
- File: `Jenkinsfile-complete`
- Stages: Build → Unit Tests → Publish → Deploy → E2E Tests → Report
- Duration: ~2 minutes
- Results in MinIO `test-results` bucket
- repo:http://gitea:3000/admin/zcu102-bsp.git
