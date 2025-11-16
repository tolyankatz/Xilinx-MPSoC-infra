---
description: Run smoke tests locally against the DUT simulator
---

# Run Smoke Test Locally

This workflow executes the smoke test suite from the host_controller.

## Prerequisites

- Lab services must be running (use start-lab workflow)
- DUT simulator must have completed boot sequence

## Steps

1. Navigate to the embedded-ci-lab-simulator directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator
```

2. Wait for DUT boot to complete (check logs)
```bash
docker-compose logs dut_simulator
```

Look for "Login prompt ready" message.

// turbo
3. Run the smoke test suite
```bash
docker-compose exec host_controller python3 /app/test_host/run_tests.py --config /app/test_host/config.yaml --test-suite smoke --skip-download
```

## Test Suite Contents

The smoke test suite includes:
- Boot validation (verify all boot stages complete)
- SSH connectivity (ensure DUT is accessible)

## Expected Results

- Boot validation: PASS (boot time < 120 seconds)
- SSH connectivity: PASS (can connect and execute commands)

## Troubleshooting

### Test fails with "Connection refused"
- DUT may not be fully booted yet
- Wait 10 more seconds and retry
- Check DUT status: `docker-compose ps dut_simulator`

### Test fails with "Boot stages missing"
- Check DUT logs: `docker-compose logs dut_simulator`
- Restart DUT: `docker-compose restart dut_simulator`

### Test hangs or times out
- Increase timeout in `config.yaml`
- Check Docker resources (CPU, memory)
