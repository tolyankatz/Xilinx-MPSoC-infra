#!/bin/bash
set -e

# Wait for Gitea to be ready
echo "Waiting for Gitea to become available..."
until curl -s -f http://gitea:3000 > /dev/null 2>&1; do
  echo "  Still waiting..."
  sleep 5
done
echo "Gitea is responding."

# Additional wait to ensure Gitea is fully initialized
echo "Waiting for Gitea to fully initialize..."
sleep 10

# Complete Gitea installation via web form
echo "Completing Gitea installation..."
curl -X POST "http://gitea:3000/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "db_type=SQLite3" \
  --data-urlencode "db_host=localhost:3306" \
  --data-urlencode "db_user=root" \
  --data-urlencode "db_passwd=" \
  --data-urlencode "db_name=gitea" \
  --data-urlencode "ssl_mode=disable" \
  --data-urlencode "db_path=/data/gitea/gitea.db" \
  --data-urlencode "app_name=Gitea: Git with a cup of tea" \
  --data-urlencode "repo_root_path=/data/git/repositories" \
  --data-urlencode "lfs_root_path=/data/git/lfs" \
  --data-urlencode "run_user=git" \
  --data-urlencode "domain=localhost" \
  --data-urlencode "ssh_port=22" \
  --data-urlencode "http_port=3000" \
  --data-urlencode "app_url=http://localhost:3000/" \
  --data-urlencode "log_root_path=/data/gitea/log" \
  --data-urlencode "smtp_host=" \
  --data-urlencode "smtp_from=" \
  --data-urlencode "smtp_user=" \
  --data-urlencode "smtp_passwd=" \
  --data-urlencode "enable_federated_avatar=on" \
  --data-urlencode "enable_open_id_sign_in=on" \
  --data-urlencode "enable_open_id_sign_up=on" \
  --data-urlencode "default_allow_create_organization=on" \
  --data-urlencode "default_enable_timetracking=on" \
  --data-urlencode "no_reply_address=noreply.localhost" \
  --data-urlencode "password_algorithm=pbkdf2" \
  --data-urlencode "admin_name=admin" \
  --data-urlencode "admin_passwd=password" \
  --data-urlencode "admin_confirm_passwd=password" \
  --data-urlencode "admin_email=admin@example.com" \
  2>&1 | head -20

echo "Waiting for installation to complete..."
sleep 10

# Create the repository via API
echo "Creating repository zcu102-bsp..."
for i in {1..5}; do
  RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "http://gitea:3000/api/v1/user/repos" \
    -H "Content-Type: application/json" \
    -u "admin:password" \
    -d '{ "name": "zcu102-bsp", "private": false, "auto_init": false, "default_branch": "main" }')
  
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  echo "Repository creation response code: $HTTP_CODE"
  
  if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
    echo "Repository created or already exists."
    break
  else
    echo "Attempt $i failed, retrying..."
    sleep 5
  fi
done

# Clone, add file, and push
echo "Pushing initial Jenkinsfile to the repo..."
git config --global user.email "provisioner@lab.com"
git config --global user.name "Provisioner"

git clone http://admin:password@gitea:3000/admin/zcu102-bsp.git /repo 2>/dev/null || {
  echo "Clone failed, trying to initialize repo..."
  mkdir -p /repo
  cd /repo
  git init
  git remote add origin http://admin:password@gitea:3000/admin/zcu102-bsp.git
}

cd /repo
cp /jenkinsfile/Jenkinsfile .
git add Jenkinsfile
git commit -m "Initial commit: Add Jenkinsfile" || echo "Nothing to commit"
git push -u origin main 2>/dev/null || git push -u origin master 2>/dev/null || {
  echo "Push failed, repository may not be ready"
}

echo "Provisioning complete."
