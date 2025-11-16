---
description: Run full regression test suite against the DUT simulator
---

# Run Regression Test Suite

This workflow executes the complete regression test suite, including all validation tests.

## Prerequisites

- Lab services must be running
- DUT simulator must be fully booted
- Optional: BSP artifacts published to Minio

## Steps

1. Navigate to the embedded-ci-lab-simulator directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator
```

2. Ensure DUT is ready
```bash
docker-compose logs --tail=20 dut_simulator
```

// turbo
3. Run the regression test suite
```bash
docker-compose exec host_controller python3 /app/test_host/run_tests.py --config /app/test_host/config.yaml --test-suite regression --skip-download
```

## Test Suite Contents

The regression test suite includes:
- Boot validation
- SSH connectivity  
- UART/console interaction
- Ethernet/network tests

## Expected Results

All tests should PASS:
- ✓ Boot validation: PASS
- ✓ SSH connectivity: PASS
- ✓ UART interaction: PASS
- ✓ Ethernet tests: PASS

## Test Logs

Test logs are saved to:
- Container: `/tmp/test_logs/`
- Minio: `test-logs` bucket (if upload enabled)

To view logs:
```bash
docker-compose exec host_controller ls -la /tmp/test_logs/
docker-compose exec host_controller cat /tmp/test_logs/test_run_*.log
```

## Running with Artifacts

If you have artifacts published to Minio:

```bash
docker-compose exec host_controller python3 /app/test_host/run_tests.py \
    --config /app/test_host/config.yaml \
    --manifest s3://bsp-artifacts/bsp-main-137/deployment_manifest.yaml \
    --test-suite regression
```

This will download artifacts before testing.
