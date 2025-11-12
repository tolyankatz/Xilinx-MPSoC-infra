---
projectName: "zcu102-bsp-validation-monorepo"
projectType: "Monorepo"
description: "A complete, end-to-end validation framework for the ZCU102 embedded Linux BSP, including CI/CD, test automation, infrastructure, and documentation."
primaryLanguage: "Python"
pythonVersion: "3.10"
ciSystem: "Jenkins"
artifactRepo: "JFrog Artifactory"
observabilityStack: "Prometheus, Grafana, ELK Stack"
---

# Windmill Project Generation Blueprint: ZCU102 BSP Validation

This document serves as the master blueprint for Windmill to generate the complete project monorepo. The AI should parse each section and generate the corresponding files and boilerplate code according to the specified structure and requirements.

## 1. Project Scaffolding

**Instruction:** Generate the top-level monorepo directory structure. Create a root `README.md` with the project name and description, and a comprehensive `.gitignore` file suitable for a Python project that also includes build artifacts and temporary files.

**Directory Structure:**
```
zcu102-bsp-validation-monorepo/
├── .gitignore
├── README.md
├── jenkins/
├── test_host/
├── infra/
└── docs/
```

---

## 2. Jenkins CI/CD Configuration (`jenkins/`)

**Instruction:** Generate a multi-stage, declarative `Jenkinsfile` for the main build-and-test pipeline. Also, create a subdirectory for any helper scripts the pipeline might need.

**File Generation:**
- **`jenkins/Jenkinsfile`**:
  - Define pipeline `agent` to use a Docker container (specified in `infra/Dockerfile.petalinux-builder`).
  - Define pipeline parameters (e.g., `TARGET_BOARD`, `TEST_SUITE`).
  - **Stage 1: Checkout:** Check out the SCM.
  - **Stage 2: Build BSP:** Execute the PetaLinux build commands inside the container. Add comments on error handling.
  - **Stage 3: Publish to Artifactory:** On success, use the Artifactory plugin (`rtUpload`) to push the generated `BOOT.BIN`, `image.ub`, and `rootfs.tar.gz` to the repository. Ensure artifacts are versioned with the build number and commit hash.
  - **Stage 4: Generate Deployment Manifest:** Create a `deployment_manifest.yaml` by dynamically populating artifact details (checksums, version) from the build stage. Archive this manifest.
  - **Stage 5: Trigger Hardware Test:** Trigger a downstream Jenkins job (e.g., "Hardware-Test-ZCU102"), passing the generated manifest as a parameter.
  - **Stage 6: Report Results:** Use a `post` block to report success or failure to Bitbucket/GitHub and Slack/Teams.

- **`jenkins/scripts/`**:
  - Create a placeholder script `jenkins/scripts/parse_build_log.sh` to demonstrate how the pipeline could call external scripts for complex logic.

---

## 3. Test Host Controller (`test_host/`)

**Instruction:** Generate a complete Python test framework using `pytest`. This is the core test automation code. The structure should be modular and easily extensible.

**File Generation:**
- **`test_host/requirements.txt`**: Include `pytest`, `pyserial`, `pyyaml`, `paramiko`, `prometheus-client`, `python-json-logger`.
- **`test_host/config.yaml`**: Create a base config file with placeholders for `serial_port`, `baud_rate`, `target_ip`, and `acceptance_criteria` (e.g., `boot_time_threshold_sec`).
- **`test_host/framework/`**: Generate the core library modules.
  - `boot_validator.py`, `uart_test.py`, `ethernet_test.py` (based on our previous implementation, including mock classes and their unit tests).
- **`test_host/hardware_control/`**: Create modules to abstract hardware interactions.
  - `power_controller.py`: A class `PowerController` with methods `on()`, `off()`, `cycle()`. Include comments on how to implement this for a specific smart plug or relay.
  - `jtag_controller.py`: A class `JTAGController` with a method `flash_image(image_path)`. Comment on using Xilinx tools via `subprocess`.
- **`test_host/reporters/`**: Create modules for pushing results.
  - `prometheus_reporter.py`: A function `push_metrics(metrics_dict)` that pushes key-value pairs to a Prometheus Pushgateway.
  - `elk_reporter.py`: A function `log_test_result(result_json)` that logs a JSON object to a file or a TCP socket for Logstash to ingest.
- **`test_host/tests/`**: Generate the system test suite.
  - `conftest.py`: Create pytest fixtures for managing hardware resources (e.g., a fixture that initializes the serial port and automatically closes it after a test).
  - `test_system_validation.py`: Create test cases that use the framework modules to test the boot sequence, UART, and Ethernet based on the test plan.
- **`test_host/run_tests.py`**: The main entry point script that Jenkins will call on the Test Host. This script will:
  1. Parse the `deployment_manifest.yaml` passed from Jenkins.
  2. Call the `hardware_control` modules to provision the DUT.
  3. Invoke `pytest` with appropriate parameters using `subprocess`.
  4. Call the `reporters` to push the final results.

---

## 4. Infrastructure & OS Configuration (`infra/`)

**Instruction:** Generate Infrastructure-as-Code (IaC) and service configuration files to ensure the build and test environments are reproducible.

**File Generation:**
- **`infra/docker/Dockerfile.petalinux-builder`**: A Dockerfile to create the Jenkins build agent. It should be based on a supported OS (e.g., Ubuntu 20.04) and include all dependencies required to run the Xilinx PetaLinux SDK.
- **`infra/docker/Dockerfile.test-host`**: A Dockerfile to set up the Test Host environment. It should start from a base Python image, copy the `test_host/` directory, and run `pip install -r requirements.txt`.
- **`infra/elk/docker-compose.yml`**: A `docker-compose` file to quickly spin up a local ELK stack (Elasticsearch, Logstash, Kibana) for development and debugging of the reporting pipeline. Include a basic Logstash config to receive JSON over TCP.
- **`infra/prometheus/prometheus.yml`**: A basic Prometheus configuration file, including a job to scrape the Pushgateway where test metrics are sent.

---

## 5. Documentation & Runbooks (`docs/`)

**Instruction:** Generate markdown templates for critical documentation, including architecture overviews and operational runbooks.

**File Generation:**
- **`docs/architecture.md`**: An architecture overview document. Embed the system diagram we designed and provide a brief description of each component's role.
- **`docs/runbooks/`**: A directory for operational guides.
  - **`docs/runbooks/DUT_Recovery_Procedure.md`**: A template runbook with sections for "Symptoms," "Diagnosis," and "Recovery Steps" (e.g., "How to re-flash a bricked board using JTAG").
  - **`docs/runbooks/Debugging_Test_Failures.md`**: A template with sections for "Analyzing S3 Logs," "Querying Kibana," and "Interpreting Grafana Dashboards."
  - **`docs/runbooks/Onboarding_New_Test_Case.md`**: A guide explaining how a developer can add a new test case to the Python framework.