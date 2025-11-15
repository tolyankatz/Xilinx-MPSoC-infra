# Seed Data and Initial Configuration Instructions

## Jenkins Configuration as Code (CasC)
- **Instruction:** Generate a `jenkins/casc.yaml` file.
- **Content:**
  - Pre-configure the connection to the Gitea server.
  - Create a seed job named "bsp-pipeline-main" that is configured to scan the Gitea server for any repository containing a `Jenkinsfile`.
  - Disable unneeded security warnings to provide a cleaner initial UI.

## MinIO Bucket Initialization
- **Instruction:** Add a command to the `host_controller/entrypoint.sh` script.
- **Content:**
  - The script should use the `mc` client to check if the MinIO buckets exist upon startup, and if not, create them.
  - **Required Buckets:**
    - `mc mb minio/bsp-firmware`
    - `mc mb minio/test-logs`

## Gitea Repository Initialization
- **Instruction:** Add instructions to the root `README.md`.
- **Content:**
  - Provide a `curl` command that uses the Gitea API to create an initial user and a sample repository named "zcu102-bsp". This shows the user how to get started immediately.