# ZCU102 BSP Validation Monorepo

## Project Vision: "Glass Box" Validation Framework

This monorepo implements a comprehensive, automated validation framework for the ZCU102 embedded Linux BSP. Our approach is not just to test features, but to build a "glass box" system that provides complete visibility into the behavior, performance, and robustness of our product at every stage of development.

## Architecture Overview

```
                  +--------------------------+
                  |  Developer Workstation   |
                  +-------------+------------+
                                | 1. Code Push
                                v
+----------------------+   +----+-----+   +---------------------------+
| Git (Bitbucket/etc.) |<--+ Webhook  +-->|   Jenkins CI/CD Server    |
| - Test Framework Code|   +----------+   | - Orchestrates Pipeline   |
| - BSP Source Code    |                  | - Manages Build/Test Jobs |
+----------+-----------+                  +----+------------------+---+
           |                                   | 2. Pull Code       | 3. Push Artifacts
           | 5a. Pull Test Code                v                    v
           |                          +--------+-------+   +-----------+-------------+
           |                          | Build Executor |-->| - NFS/JFrog Artifactory |
           |                          +----------------+   | - Firmware/Images       |
           |                                               | - Build Artifacts       |
           |                                               +------------+------------+
           |                                                        | 5b. Pull Firmware
           v                                                        v
+----------+--------------------------------------------------------+------------------+
|                                  Test Host / Lab Controller                           |
|---------------------------------------------------------------------------------------|
| - Python/Pytest Environment                                                           |
| - Hardware Control Scripts (Power, JTAG) & Test Fixtures                  |
| - Data Shipper (Filebeat)                                                             |
+----------+----------------------+--------------------------+-------------+-----------+
           | 6. Provision & Ctrl   | 7. Run Tests             | 8a. Push Logs| 8b. Push Metrics
           v                       v                          v             v
+----------+-----------+ +---------+----------+   +----------+-----+   +-----+------------+
| Controllable Power | |  ZCU102 Board (DUT) |   | S3 / Central |   | Prometheus/Grafana |
| + JTAG/Recovery    | | + Test Fixture     |   |   Storage    |   | + ELK Stack        |
+--------------------+ +----------------------+   +--------------+   | - Dashboards     |
                                                                     | - Analytics      |
```

## Key Principles

- **Quality by Design**: Every commit is automatically validated against real hardware
- **Full Traceability**: Every artifact is versioned and linked to its source commit
- **Data-Driven Decisions**: Rich metrics and logs enable informed release decisions
- **Developer Empowerment**: Fast feedback loops and clear debugging information

## BSP Manifest Integration

This framework includes comprehensive support for BSP (Board Support Package) deployment manifests that provide complete traceability from build artifacts to test execution. The manifest format (`bsp-main-137.yaml`) includes:

### Manifest Structure
- **Build Information**: Build ID, commit hash, and version tracking
- **Artifact Details**: Complete artifact inventory with checksums and download locations
- **Deployment Configuration**: Hardware provisioning and deployment methods
- **Runtime Configuration**: Network, console, and system settings
- **Test Plan**: Specific test suites to execute for this build

### Key Features
- **Automatic Artifact Management**: Downloads and validates build artifacts
- **Hardware Provisioning**: Configures DUT based on manifest specifications
- **Test Plan Execution**: Runs specific test suites defined in the manifest
- **Full Traceability**: Links test results back to exact build and commit

### Usage Example
```bash
# Run tests with BSP manifest
python test_host/run_tests.py \
    --config test_host/config.yaml \
    --manifest artifacts/bsp-main-137.yaml \
    --test-suite smoke \
    --verbose

# Or use the convenience scripts
./run_tests_with_bsp_manifest.sh  # Linux
run_tests_with_bsp_manifest.bat   # Windows
```
- **Automation First**: Manual intervention only where human judgment adds value

## Repository Structure

```
zcu102-bsp-validation-monorepo/
├── jenkins/                    # CI/CD pipeline configuration
│   ├── Jenkinsfile            # Main build-and-test pipeline
│   └── scripts/               # Helper scripts for pipeline stages
├── test_host/                 # Python test automation framework
│   ├── framework/             # Core test libraries
│   ├── hardware_control/      # DUT provisioning and control
│   ├── reporters/             # Results aggregation and reporting
│   ├── tests/                 # System validation test suite
│   └── run_tests.py          # Main test orchestrator
├── infra/                     # Infrastructure-as-Code
│   ├── docker/               # Container definitions
│   ├── elk/                  # Elasticsearch, Logstash, Kibana setup
│   └── prometheus/           # Metrics collection configuration  
└── docs/                      # Architecture and operational guides
    ├── architecture.md        # System design documentation
    └── runbooks/             # Operational procedures
```

## Getting Started

### Prerequisites
- Jenkins server with Docker support
- NFS/JFrog Artifactory instance
- Hardware test lab with ZCU102 boards
- ELK Stack and Prometheus/Grafana for observability

### Quick Start
1. Clone this repository
2. Configure Jenkins pipeline using `jenkins/Jenkinsfile`
3. Set up test host environment using `infra/docker/Dockerfile.test-host`
4. Deploy observability stack using `infra/elk/docker-compose.yml`
5. Configure hardware controllers in `test_host/config.yaml`

## Validation Coverage

Our framework validates:
- **Boot Sequence**: Integrity, performance, and reliability across power cycles
- **Protocol Testing**: UART, Ethernet, functional validation
- **Linux System**: Performance, real-time characteristics, stability testing  
- **Security Hardening**: Configuration verification and compliance checks

## Observability and Metrics

- **Real-time Dashboards**: Grafana dashboards for test execution monitoring
- **Historical Trending**: Track performance metrics and quality trends over time
- **Log Aggregation**: Centralized logging with powerful search and analysis
- **Alerting**: Proactive notifications for test failures and anomalies

## Contributing

This framework is designed to be extensible and team-friendly:
- Add new test cases following patterns in `test_host/tests/`
- Extend hardware support in `test_host/hardware_control/`  
- Enhance reporting in `test_host/reporters/`
- See `docs/runbooks/Onboarding_New_Test_Case.md` for detailed guidance

## Engineering Philosophy

As a BSP QA Engineer project, this framework embodies:
- **Technical Excellence**: Clean, maintainable, well-documented code
- **Operational Maturity**: Production-ready monitoring and debugging capabilities  
- **Team Enablement**: Tools and documentation that empower the entire engineering team
- **Continuous Improvement**: Architecture designed to evolve with our needs

---

*Built with the vision of creating not just tests, but a comprehensive validation ecosystem that gives us complete confidence in our embedded Linux products.*
