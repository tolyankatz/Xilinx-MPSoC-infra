#!/bin/bash

# Initialize Gitea with default settings
curl -X POST http://localhost:3000/install \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "db_type=sqlite3" \
  -d "db_host=localhost:3306" \
  -d "db_user=root" \
  -d "db_passwd=" \
  -d "db_name=gitea" \
  -d "ssl_mode=disable" \
  -d "db_schema=" \
  -d "charset=utf8" \
  -d "db_path=/data/gitea/gitea.db" \
  -d "app_name=Gitea: Git with a cup of tea" \
  -d "repo_root_path=/data/git/repositories/" \
  -d "lfs_root_path=/data/git/lfs" \
  -d "run_user=git" \
  -d "domain=localhost" \
  -d "ssh_port=2222" \
  -d "http_port=3000" \
  -d "app_url=http://localhost:3000/" \
  -d "log_root_path=/data/gitea/log" \
  -d "admin_name=admin" \
  -d "admin_passwd=password" \
  -d "admin_confirm_passwd=password" \
  -d "admin_email=admin@example.com"

echo "Gitea initialization complete"
