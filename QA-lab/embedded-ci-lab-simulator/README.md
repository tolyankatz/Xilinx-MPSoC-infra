# Embedded CI Lab Simulator

This project provides a Docker-Compose-based simulation of an embedded CI/CD lab with Gitea, Jenkins, MinIO, a Host Controller, and a DUT Simulator. It is infrastructure-only and expects your own BSP code, Jenkinsfiles, and test scripts.

## Architecture Overview

- **Gitea**: Git server for BSP and test repositories.
- **Jenkins**: CI/CD orchestrator polling Gitea and running pipelines.
- **MinIO**: S3-compatible artifact and log store.
- **Host Controller**: Lab PC with SSH access and MinIO client; manages artifacts and talks to the DUT.
- **DUT Simulator**: Simulated ZCU102 board exposing a UART-like TCP shell and basic network services.

All services run on a shared Docker network `lab_network` and can be started together with a single command.

## Prerequisites

- Docker
- Docker Compose v2 or compatible

## Getting Started

From the `embedded-ci-lab-simulator` directory:

```bash
docker-compose up -d --build
```

This will build custom images and start all containers in the background.

To stop and remove containers:

```bash
docker-compose down
```

Named volumes `gitea_data`, `jenkins_home`, and `minio_data` persist service data across restarts.

## Service Endpoints

- **Gitea Web UI**: http://localhost:3000
- **Gitea SSH**: `ssh://git@localhost:2222` (once configured in Gitea)
- **Jenkins Web UI**: http://localhost:8080
- **MinIO S3 API**: http://localhost:9000
- **MinIO Console UI**: http://localhost:9001
- **Host Controller SSH** (from your machine):

  ```bash
  ssh jenkins@localhost -p 2223
  ```

  Default password: `jenkins`.

The DUT simulator is reachable from the Host Controller on the internal Docker network as `dut_simulator` (for example on TCP port 23 for the simulated UART).

## Initial Credentials

These are lab defaults intended for a local, isolated environment:

- **MinIO**:
  - Access key: `admin`
  - Secret key: `password`
- **Jenkins** (preconfigured via CasC):
  - User: `admin`
  - Password: `admin`
- **Host Controller**:
  - SSH user: `jenkins`
  - SSH password: `jenkins`

You should change these if you expose the lab beyond your local machine.

## Gitea: Creating a User and Repository via API

After Gitea is running and you have completed its initial web-based setup and created an admin account, you can use the Gitea API to create a lab user and a sample repository `zcu102-bsp`.

Replace `ADMIN_USER` and `ADMIN_PASSWORD` with your actual Gitea admin credentials.

Create a new user `bsp-dev`:

```bash
curl -X POST "http://localhost:3000/api/v1/admin/users" \
  -u "ADMIN_USER:ADMIN_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bsp-dev@example.com",
    "full_name": "BSP Developer",
    "login_name": "bsp-dev",
    "username": "bsp-dev",
    "must_change_password": false,
    "password": "bsp-dev-pass"
  }'
```

Create the `zcu102-bsp` repository for that user:

```bash
curl -X POST "http://localhost:3000/api/v1/admin/users/bsp-dev/repos" \
  -u "ADMIN_USER:ADMIN_PASSWORD" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "zcu102-bsp",
    "private": false
  }'
```

You can now clone the repository locally using either HTTP or SSH (after you configure SSH in Gitea):

```bash
git clone http://localhost:3000/bsp-dev/zcu102-bsp.git
```

## Jenkins: Preconfigured Seed Job

Jenkins is preconfigured via Configuration as Code (CasC) with:

- A connection to the local Gitea server at `http://gitea:3000` using admin credentials.
- A multibranch pipeline job named `bsp-pipeline-main` that points at the `zcu102-bsp` repository inside Gitea and looks for a `Jenkinsfile` in each branch.
- Selected security warnings disabled for a cleaner UI.

After starting the lab:

1. Open Jenkins at http://localhost:8080.
2. Log in with `admin` / `admin`.
3. You should see the `bsp-pipeline-main` job already present.
4. Once you push a branch with a `Jenkinsfile` to `zcu102-bsp`, trigger **Scan Multibranch Pipeline Now** on `bsp-pipeline-main`. Jenkins will discover branches with a `Jenkinsfile` and run pipelines for them.

This fulfills the requirement that a BSP developer sees their pipeline start soon after pushing changes, as long as the repository contains a valid `Jenkinsfile`.

## MinIO: Buckets and Logs

On startup, the Host Controller uses the MinIO client `mc` to ensure that the following buckets exist:

- `bsp-firmware`
- `test-logs`

You can browse these from the MinIO Console at http://localhost:9001 using the MinIO credentials above.

As a QA Automation Engineer, you can upload or download artifacts and test logs via the S3 API or via the web console, making it easy to inspect logs from failed runs.

## Host Controller: Lab PC Simulation

The Host Controller container simulates the lab PC that Jenkins talks to over SSH.

- From Jenkins pipelines, you can connect to the `host_controller` container using its service name `host_controller` on port 22.
- From your local machine, you can SSH to it using:

  ```bash
  ssh jenkins@localhost -p 2223
  ```

Once connected, you will find tools such as `netcat`, `iperf3`, `python3`, and the MinIO client `mc` installed.

The Host Controller is also configured to talk to MinIO using the alias `minio` and to manage the `bsp-firmware` and `test-logs` buckets automatically on startup.

## DUT Simulator: UART and Network

The DUT Simulator exposes a simple TCP-based shell on port 23 inside the Docker network to emulate a UART console.

From the Host Controller, you can connect to it using tools like `nc` or `telnet` (if installed) to simulate serial interaction, and use `ping` or `iperf3` to exercise network behavior between the Host Controller and DUT.

## Typical Workflows

### BSP Developer Workflow

1. Create a lab user and `zcu102-bsp` repository in Gitea (using the API commands above or the web UI).
2. Clone the repository locally and add your BSP code and a `Jenkinsfile` describing your build and test pipeline.
3. Push your changes to Gitea.
4. In Jenkins, open `bsp-pipeline-main` and run **Scan Multibranch Pipeline Now** if the scan has not already occurred.
5. Observe pipeline runs, console output, and build status. Jenkins links back to your commits in Gitea through the Git plugin.

### QA Automation Engineer Workflow

1. SSH into the Host Controller using `ssh jenkins@localhost -p 2223` to debug test scripts or investigate failures.
2. Use `mc` on the Host Controller or the MinIO Console UI to retrieve artifacts and logs from the `test-logs` bucket.
3. In Jenkins, manually trigger `bsp-pipeline-main` runs against specific branches to validate particular builds or test suites.

This lab is intended as a safe digital twin of a hardware lab, letting you iterate on Jenkins pipelines and automation scripts before deploying them to real boards.
