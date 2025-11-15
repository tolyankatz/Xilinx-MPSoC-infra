# BSP Validation Framework – Developer Briefing

_Audience: BSP / Embedded Linux developers_
_Speaker: Senior Validation Engineer – BSP_

---

## 1. Purpose of This Session

- **Set expectations** for how we validate the ZCU102 BSP
- **Explain the architecture** of the new "glass box" validation framework
- **Show how NFS-based artifacts + CI/CD + lab automation** fit together
- **Clarify what developers need to do** to get value from the system

---

## 2. Problem Statement & Goals

- **Problem**
  - BSP quality and regressions are hard to track across images and branches
  - Manual lab testing does not scale and is hard to reproduce
  - Artifacts, logs, and test results are scattered and hard to correlate

- **Goals**
  - Every BSP build is **automatically validated on real ZCU102 hardware**
  - We have **end-to-end traceability** from Git commit → BSP image → test results
  - Tests are **repeatable, scriptable, and observable**
  - Developers can **run the same tests locally** that CI runs in the lab

---

## 3. High-Level Architecture

- **Components** (see `docs/architecture.md`)
  - Git repository: **ZCU102 BSP Validation Monorepo**
  - Jenkins CI/CD: builds BSP, publishes artifacts, triggers hardware tests
  - NFS artifact store: single source of truth for images & manifests
  - Test host: Python-based framework running on a lab controller
  - DUT: ZCU102 board(s) with power control & JTAG recovery
  - Observability: ELK / Prometheus for logs and metrics

- **Key principle**: _"Filesystem as the artifact database"_
  - Versioned directories per BSP build
  - Manifests describe **what to deploy** and **what to test**

---

## 4. Test Strategy Overview

Aligned with the requirements in `docs/requirements.md`.

- **Test categories**
  - **Unit**: module-level behavior (e.g., UART helper logic, parsing)
  - **Integration**: interaction between framework components, DUT, and lab hardware
  - **System**: full end-to-end runs from power-on → boot → network → sanity tests
  - **Regression**: curated suites (smoke, regression, full) defined in `test_host/config.yaml`

- **Key focus areas**
  - **Boot sequence validation** (boot time, stages, error detection)
  - **UART communication** (console, configuration, data integrity, performance)
  - **Ethernet connectivity & performance** (link, ping, throughput)

- **Acceptance criteria**
  - Defined centrally in `test_host/config.yaml` under `acceptance_criteria`
  - Examples:
    - Max boot time: `boot.max_boot_time_seconds`
    - Min Ethernet throughput: `performance.min_ethernet_throughput_mbps`
    - Max ping latency: `performance.max_ping_latency_ms`

---

## 5. Boot Sequence Validation (boot_validator.py)

- **Objective**: Ensure the BSP boots reliably and within time budgets.

- **Implementation** (`test_host/framework/boot_validator.py`)
  - Reads boot logs from the **serial console** (via UART)
  - Detects boot stages using regex patterns:
    - FSBL → U-Boot → Kernel → Userspace → Login prompt
  - Tracks **per-stage durations** and total boot time
  - Flags **critical errors** (e.g., `kernel panic`, OOM, stack traces)

- **Metrics** (`BootMetrics`)
  - `total_boot_time_seconds`
  - `stage_durations[BootStage]`
  - `error_messages`, `warning_messages`
  - `boot_successful` flag and final stage reached

- **Acceptance**
  - Boot time must be below threshold (configurable, default 45s)
  - Required messages present, forbidden messages absent

---

## 6. UART Communication Tests (uart_test.py)

- **Objective**: Validate console access, configuration, and robustness.

- **Implementation** (`test_host/framework/uart_test.py`)
  - Uses `pyserial` to connect to `/dev/ttyUSBx`
  - `UartTester` class implements multiple test families:
    - **Console interaction**: run standard Linux commands over serial
    - **Data integrity**: send random data, verify checksums on DUT
    - **Performance**: measure throughput and latency

- **Metrics** (`UartTestMetrics`)
  - Command success rate, response times, throughput
  - Bytes transmitted/received, checksum matches/failures
  - Transmission/timeout errors and error messages

- **Why developers care**
  - UART is the primary **debug lifeline** for BSP issues
  - Regressions in console behavior are caught before you see them manually

---

## 7. Ethernet Tests (ethernet_test.py)

- **Objective**: Ensure network connectivity and basic performance on the BSP.

- **Implementation** (`test_host/framework/ethernet_test.py`)
  - `EthernetTester` uses `paramiko`/SSH and system tools on the DUT
  - Test categories:
    - **Connectivity**: link up/down, ping to/from DUT
    - **Performance**: TCP/UDP throughput measurement (simulated load)
    - **Stability**: basic drop/error tracking

- **Metrics** (`EthernetTestMetrics`)
  - Ping success rate, average latency, packet loss
  - TCP/UDP throughput and bandwidth utilization
  - Link speed, duplex mode, MTU

- **Acceptance**
  - Thresholds defined in `config.yaml` → e.g., min throughput 900 Mbps

---

## 8. Test Orchestration & Configuration

- **Orchestrator** (`test_host/run_tests.py`)
  - Loads `test_host/config.yaml`
  - Selects test suite: `smoke`, `regression`, or `full`
  - Powers DUT, performs boot validation, UART/Ethernet tests, plus other fixtures
  - Collects metrics and pushes reports/logs to observability backends

- **Configuration** (`test_host/config.yaml`)
  - **hardware.serial**: UART device, baud, timeouts
  - **hardware.network**: DUT IP, test host IP, interface
  - **hardware.power**: smart plug/relay settings for power cycling
  - **hardware.jtag**: cable and Vivado path for recovery
  - **test_suites**: mapping of suite names to test lists and timeouts
  - **acceptance_criteria**: central thresholds
  - **reporting**: Prometheus, Elasticsearch, S3, local logs

- **Key idea**: **No test code changes** are needed to tune behavior → adjust YAML.

---

## 9. NFS-Based Artifact Management

- **Motivation**
  - Replace JFrog Artifactory with a **simple, transparent, self-hosted** solution
  - NFS fits well with BSP images and large binary artifacts

- **Directory structure** (`/mnt/nfs_artifacts/bsp`)
  - One directory per build:
    - `bsp-main-137/`, `bsp-dev-2025.11-rc1/`, `bsp-hotfix-2025.11.1/`, ...
  - Each directory contains:
    - `BOOT.BIN`, `image.ub`, `system.dtb`, `rootfs.tar.gz`
    - `*.md5` checksum files
    - `deployment_manifest.yaml`
    - `build_metadata.json`

- **Publishing** (`scripts/publish_artifacts_to_nfs.sh`)
  - Called from Jenkins after build
  - Copies artifacts into a new build directory
  - Generates MD5 checksums and manifest/metadata
  - Applies retention policy (e.g., keep last N days/builds)

- **Management** (`scripts/manage_nfs_artifacts.sh`)
  - `list`, `info`, `verify`, `cleanup` commands
  - Lets us inspect and clean NFS artifacts safely

- **Monitoring & triggers** (`scripts/nfs_artifact_monitor.sh`)
  - Watches NFS for new manifests
  - Triggers Jenkins validation jobs with proper parameters

---

## 10. CI/CD and Lab Automation

- **Jenkins Pipeline** (see `Jenkinsfile`)
  - Stages:
    - Build BSP
    - Publish artifacts to NFS
    - Trigger hardware validation on test host
  - Uses parameters for `BUILD_ID`, `MANIFEST_PATH`, `TEST_SCOPE`

- **Test Host Automation**
  - Power cycling via `test_host/hardware_control/power_controller.py`
  - JTAG recovery via `test_host/hardware_control/jtag_controller.py`
  - Test execution and reporting via `run_tests.py`

- **Observability**
  - Prometheus/Grafana: metrics for test runs and lab health
  - ELK stack: central logs for test runs and DUT behavior

---

## 11. How Developers Use This System

- **Typical workflow**
  1. Implement BSP change and push to Git
  2. Jenkins builds the BSP and publishes artifacts to NFS
  3. NFS monitor triggers hardware validation
  4. Test host runs boot + UART + Ethernet + other tests
  5. Results are available via Jenkins, dashboards, and logs

- **Running locally** (developer workstation or lab host)
  - Use BSP manifest:
    ```bash
    python test_host/run_tests.py \
        --config test_host/config.yaml \
        --manifest artifacts/bsp-main-137.yaml \
        --test-suite smoke \
        --verbose
    ```
  - Or use helper scripts (`run_tests_with_bsp_manifest.sh` / `.bat`)

- **Adding a new test**
  1. Implement Python test in `test_host/tests/` or extend framework modules
  2. Wire it into the orchestrator or test suite mapping
  3. Update `config.yaml` if new parameters or criteria are needed

---

## 12. Expectations from the BSP Team

- **Keep manifests honest**
  - Ensure `artifacts/*.yaml` accurately describes the image and test plan
  - Include new artifacts and configuration when features are added

- **Respect acceptance criteria**
  - When a change violates boot time, throughput, or stability thresholds, treat it as a regression signal, not a test bug

- **Treat tests as first-class citizens**
  - When adding a feature, also consider:
    - How do we validate it on real hardware?
    - What metrics indicate success or regression?

- **Collaborate on coverage**
  - Identify gaps (e.g., additional peripherals, stress scenarios)
  - Propose tests and acceptance criteria for new areas

---

## 13. Current Status vs Requirements

- **Requirements tracking** (`docs/requirements.md`)
  - ~97% overall compliance with assignment-level requirements
  - 100% on critical items (test strategy, boot/UART/Ethernet modules, config, README)
  - "Partial" items are primarily where we chose **real hardware over pure mocks**, which is better for BSP validation

- **Bottom line**
  - The framework is **production-ready for ZCU102 BSP validation**
  - We can iteratively extend coverage as the BSP and hardware evolve

---

## 14. Roadmap & Next Steps

- **Short-term**
  - Refine acceptance thresholds based on real data from early runs
  - Harden recovery flows for more complex failure modes
  - Add more board-level tests (e.g., storage, GPIO, I2C/SPI when fixtures are ready)

- **Medium-term**
  - Expand to additional boards and BSP variants
  - Add more stress, soak, and longevity tests
  - Tighten integration with release processes and sign-off checklists

- **Long-term vision**
  - Make this framework the **single source of truth for BSP health** across all platforms
  - Provide self-service dashboards so developers can quickly answer: _"Is my BSP healthy on real hardware right now?"_

---

## 15. Q&A

- What tests matter most for your current BSP work?
- Which failure modes do you want to see detected automatically?
- What would make this framework easier for you to adopt in day-to-day development?
