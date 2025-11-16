# ZCU102 BSP Validation – Executive Overview

_Audience: Engineering leadership, tech leads_
_Speaker: Senior Validation Engineer – BSP_

---

## 1. Why We Built This Framework

- **Problem**
  - BSP quality and regressions are difficult to track across builds and branches.
  - Manual lab testing is slow, non-repeatable, and doesn’t scale.
  - Artifacts, logs, and test results are scattered; root-cause analysis is costly.

- **Objective**
  - Make BSP health **visible, measurable, and repeatable** on real ZCU102 hardware.
  - Provide **end-to-end traceability** from Git commit → BSP image → test results.
  - Enable developers to **self-serve validation** locally and in CI.

- **Key Principle**
  - Treat the validation system as a **first-class product**, not a side script.

---

## 2. Architecture in One Slide

- **Core Components**
  - **Git monorepo** – BSP + test framework + infrastructure in one place.
  - **Jenkins CI/CD** – builds BSP images and triggers hardware validation.
  - **NFS artifact store** – versioned directories per BSP build (filesystem as DB).
  - **Test host** – Python-based framework controlling DUT, power, and JTAG.
  - **DUT (ZCU102 board)** – real hardware under automated control.
  - **Observability stack** – ELK + Prometheus/Grafana for logs and metrics.

- **Flow (high level)**
  1. Developer pushes code → Jenkins builds BSP.
  2. Artifacts + manifest are published to NFS.
  3. Filesystem monitor detects new build → triggers validation job.
  4. Test host runs automated boot, UART, Ethernet, and system tests.
  5. Results and metrics are stored and visualized for decision making.

---

## 3. What We Actually Test

- **Boot Sequence** (`boot_validator.py`)
  - Tracks FSBL → U-Boot → Kernel → Userspace → Login.
  - Measures per-stage and total boot time; flags kernel panics and critical errors.
  - Acceptance criteria (e.g., max 45s boot) configured in `test_host/config.yaml`.

- **UART Communication** (`uart_test.py`)
  - Validates console access, baud configuration, data integrity, and latency.
  - Measures command success rate, throughput, and timeouts over the real serial link.

- **Ethernet Connectivity & Performance** (`ethernet_test.py`)
  - Verifies link up/down, ping success, and basic throughput (TCP/UDP).
  - Enforces thresholds such as minimum Mb/s and maximum ping latency.

- **Test Suites**
  - `smoke`, `regression`, `full` – curated combinations of the above, plus fixtures.

---

## 4. NFS-Based Artifact Lifecycle (Replacing Artifactory)

- **Why NFS?**
  - Simple, transparent, self-hosted; ideal for large BSP images and manifests.
  - Aligns with our "glass box" philosophy – no hidden state in external services.

- **Structure** (`/mnt/nfs_artifacts/bsp`)
  - One directory per build (e.g., `bsp-main-137/`, `bsp-dev-2025.11-rc1/`).
  - Each contains images (`BOOT.BIN`, `image.ub`, `system.dtb`, `rootfs.tar.gz`),
    MD5 checksums, `deployment_manifest.yaml`, and `build_metadata.json`.

- **Automation**
  - `publish_artifacts_to_nfs.sh`: publishes and versions artifacts, generates checksums and manifests, applies retention.
  - `nfs_artifact_monitor.sh`: watches for new manifests and triggers Jenkins validation.
  - `manage_nfs_artifacts.sh`: list, inspect, verify, and clean up builds.

- **Outcome**
  - NFS is now the **single source of truth** for BSP artifacts and their tests.

---

## 5. Impact on Developers & Releases

- **For Developers**
  - Same tests run in CI can be run locally using the BSP manifest:
    ```bash
    python test_host/run_tests.py \
        --config test_host/config.yaml \
        --manifest artifacts/bsp-main-137.yaml \
        --test-suite smoke \
        --verbose
    ```
  - Clear criteria for success/failure (boot time, throughput, stability) are defined in config, not buried in code.
  - Faster feedback on regressions in critical areas (boot, console, network).

- **For Release/Leadership**
  - A BSP build is "green" only if it passes **hardware-based** acceptance criteria.
  - `docs/requirements.md` shows ~**97% compliance** with the original project spec,
    including 100% on critical test/architecture/CI requirements.
  - Dashboards and logs give a **defensible basis** for release decisions.

---

## 6. Where We’re Going Next

- **Short Term**
  - Tune thresholds based on real data; harden recovery flows.
  - Add more board-level tests (storage, GPIO, I2C/SPI as fixtures mature).

- **Medium Term**
  - Extend framework to additional boards and BSP variants.
  - Add stress/soak/longevity runs for robustness over time.

- **Long Term Vision**
  - Make this framework the **authoritative source** for BSP health across platforms.
  - Ensure any stakeholder can quickly answer: _"Is this BSP build healthy on real hardware right now?"_.
