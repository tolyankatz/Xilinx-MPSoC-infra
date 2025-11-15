---
projectName: "embedded-ci-lab-simulator"
projectType: "Infrastructure"
description: "A Docker-Compose based simulation of a CI/CD lab for embedded systems development, including a Git server, CI orchestrator, artifact store, and simulated hardware."
primaryTool: "Docker-Compose"
---

# Windmill Blueprint: CI/CD Lab Simulator Generation

This document instructs Windmill to generate the complete Docker-based infrastructure for a simulated embedded systems lab. Generate only the infrastructure files; no application or test code.

## 1. Project Scaffolding

**Instruction:** Generate the root project directory and the central `docker-compose.yml` file. Create subdirectories for each service's configuration and build contexts.

**Directory Structure:**
```
embedded-ci-lab-simulator/
├── docker-compose.yml
├── README.md
├── gitea_data/
├── jenkins_home/
├── minio_data/
├── jenkins/
│   ├── Dockerfile
│   └── plugins.txt
├── host_controller/
│   ├── Dockerfile
│   └── entrypoint.sh
└── dut_simulator/
    ├── Dockerfile
    └── entrypoint.sh
```

## 2. Root Files

**Instruction:** Generate the main `docker-compose.yml` and a `README.md`.

*   **`docker-compose.yml`**:
    - Define a top-level network: `lab_network`.
    - Define top-level volumes: `gitea_data`, `jenkins_home`, `minio_data`.
    - Create service definitions for `gitea`, `minio`, `jenkins`, `host_controller`, and `dut_simulator`. All services must be attached to `lab_network`.

*   **`README.md`**:
    - Provide instructions on how to start the lab (`docker-compose up -d --build`), access each service's web UI (Gitea, Jenkins, MinIO), and shut down the lab (`docker-compose down`).

## 3. Service Definitions

### Gitea Service (`gitea`)
- **Image:** `gitea/gitea:latest`
- **Volume:** Map the `gitea_data` volume to `/data`.
- **Ports:** Map `3000:3000` and `2222:22`.
- **Restart Policy:** `always`.

### MinIO Service (`minio`)
- **Image:** `minio/minio:latest`
- **Volumes:** Map `minio_data` to `/data`.
- **Ports:** Map `9000:9000` and `9001:9001`.
- **Environment:**
  - `MINIO_ROOT_USER`: `admin`
  - `MINIO_ROOT_PASSWORD`: `password`
- **Command:** `server /data --console-address ":9001"`

### Jenkins Service (`jenkins`)
- **Build Context:** `./jenkins`
- **Volume:** Map `jenkins_home` to `/var/jenkins_home`.
- **Ports:** Map `8080:8080` and `50000:50000`.
- **Dependencies:** `depends_on: [gitea]`
- **`jenkins/Dockerfile`**:
  - `FROM jenkins/jenkins:lts-jdk11`
  - Switch to `USER root`.
  - Install `docker.io`.
  - Add the `jenkins` user to the `docker` group.
  - Switch back to `USER jenkins`.
  - Copy `jenkins/plugins.txt` and install plugins using `jenkins-plugin-cli`.
- **`jenkins/plugins.txt`**: Generate with common plugins: `git`, `ssh-agent`, `blueocean`, `job-dsl`.

### Host Controller Service (`host_controller`)
- **Build Context:** `./host_controller`
- **Dependencies:** `depends_on: [jenkins]`
- **`host_controller/Dockerfile`**:
  - `FROM ubuntu:20.04`
  - Install `openssh-server`, `openssh-client`, `netcat`, `iperf3`, `python3`.
  - Download and install the MinIO client (`mc`).
  - Create an SSH user (e.g., `jenkins`).
  - Copy and set permissions for the `entrypoint.sh` script.
- **`host_controller/entrypoint.sh`**:
  - A shell script that generates SSH host keys on first run and starts the `sshd` daemon in the foreground.

### DUT Simulator Service (`dut_simulator`)
- **Build Context:** `./dut_simulator`
- **`dut_simulator/Dockerfile`**:
  - `FROM ubuntu:20.04`
  - Install `socat`, `iperf3`, and other basic networking tools.
  - Copy and set permissions for the `entrypoint.sh` script.
- **`dut_simulator/entrypoint.sh`**:
  - A shell script that starts the UART simulation using `socat`.
  - **Example `socat` command:**
    ```bash
    echo "Simulated DUT Boot Log..."
    echo "Login:"
    socat TCP-LISTEN:23,fork,reuseaddr EXEC:'/bin/bash -i'
    ```
    This command listens on TCP port 23 (like Telnet) and spawns an interactive bash shell for every connection, perfectly simulating a serial login prompt.
```

---

### **Deliverable 3: Windmill Conceptual Files & Execution Prompt**

#### Conceptual Files for AI Guidance

These files are not code, but structured data to help the AI understand the project's logic and relationships.

