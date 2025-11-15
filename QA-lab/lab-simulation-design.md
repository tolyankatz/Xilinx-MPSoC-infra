# Design Document: A Docker-Based Simulated CI/CD Lab for Embedded Systems

## 1. Vision & Objective

The objective is to create a fully simulated, stand-alone lab environment that mirrors a professional CI/CD pipeline for embedded systems development. This entire lab will run within Docker containers, requiring no physical hardware. It will serve as the foundational infrastructure upon which the BSP validation framework will be built and tested.

The core philosophy is to create a "digital twin" of the real-world lab, allowing for rapid development, testing, and iteration of the automation framework itself without consuming physical hardware resources.

## 2. Simulated Lab Architecture

The lab consists of five core, interconnected services managed by `docker-compose`. They communicate over a shared virtual network (`lab_network`).

**Architectural Diagram:**

```
+-------------------------------------------------------------------------+
| Docker Host                                                             |
|                                                                         |
|  +-----------------------+      +-----------------------+               |
|  | Gitea (Git Server)    |<---->| Jenkins (CI/CD)       |<--+           |
|  | - Stores source code  |      | - Polls Gitea         |   |           |
|  +-----------------------+      | - Orchestrates jobs   |   | (SSH)     |
|                                 +-----------------------+   |           |
|                                                             v           |
|  +-----------------------+      +-----------------------+   +-----------+
|  | MinIO (Artifacts/Logs)|<---->| Host Controller       |<->| DUT       |
|  | - S3-compatible store |      | - Receives SSH commands |   | Simulator |
|  +-----------------------+      | - Controls DUT        |   +-----------+
|                                 | - Manages artifacts   |               |
|                                 +-----------------------+               |
|                                                                         |
+-------------------------------------------------------------------------+
```

## 3. Component Roles & Interactions

*   **Gitea (The "GitHub"):** A lightweight, self-hosted Git server. It acts as the central source code repository for the project. Jenkins will poll this service for changes.
*   **Jenkins (The "Orchestrator"):** The heart of the CI/CD pipeline. It will be configured to automatically detect commits in Gitea, trigger "build" jobs (which will be simulated), and then execute "test" jobs by sending SSH commands to the Host Controller.
*   **MinIO (The "Artifact Store"):** An S3-compatible object storage server. It will function as our universal repository for build artifacts (simulated firmware), test logs, and reports. The Host Controller will be the primary client for this service.
*   **Host Controller (The "Lab PC"):** This container simulates the physical machine in the lab. Its primary role is to be a remote execution target for Jenkins. It will have an SSH server running and will contain the necessary client tools (`mc` for MinIO, `netcat` for UART simulation) to interact with the other services.
*   **DUT Simulator (The "Hardware"):** This container simulates the ZCU102 board. It does not run a real BSP. Instead, it provides endpoints that mimic the board's interfaces:
    *   **Simulated UART:** A TCP socket managed by `socat` that behaves like a serial console. The Host Controller will connect to this socket to send "commands" and receive "log" output.
    *   **Simulated Ethernet:** Standard container networking. The Host Controller can `ping` and run `iperf3` against it to test basic network functionality.

This design creates a closed-loop system perfect for developing and validating the automation scripts and Jenkins pipelines before they are deployed to a real hardware lab.

