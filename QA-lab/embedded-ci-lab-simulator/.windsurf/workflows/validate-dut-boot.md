---
description: Validate that the DUT simulator boots correctly and shows all boot stages
---

# Validate DUT Boot Sequence

This workflow helps you verify the DUT simulator is booting correctly with all expected stages.

## Steps

1. Navigate to the embedded-ci-lab-simulator directory
```bash
cd c:\source\Xilinx\Xilinx-MPSoC-infra\QA-lab\embedded-ci-lab-simulator
```

// turbo
2. Restart the DUT to see a fresh boot sequence
```bash
docker-compose restart dut_simulator
```

// turbo
3. Follow the boot logs in real-time
```bash
docker-compose logs -f dut_simulator
```

## Expected Boot Stages

You should see the following stages in order:

1. **FSBL (First Stage Boot Loader)**
   ```
   [FSBL] Xilinx First Stage Boot Loader
   [FSBL] Release 2024.1
   ```

2. **U-Boot**
   ```
   U-Boot 2024.01 (Xilinx ZCU102 Board)
   DRAM:  4 GiB
   ```

3. **Linux Kernel**
   ```
   Starting kernel ...
   Linux version 6.1.0-xilinx
   ```

4. **Login Prompt**
   ```
   zcu102-zynqmp login: root
   Login prompt ready - SSH server starting...
   ```

## Validation

✅ **Boot is successful if:**
- All four stages appear in logs
- Total boot time is under 10 seconds (simulated)
- SSH server starts without errors
- "Login prompt ready" message appears

❌ **Boot has issues if:**
- Any stage is missing
- Container restarts unexpectedly
- SSH server fails to start
- Errors in boot logs

## Troubleshooting

### Container keeps restarting
```bash
docker-compose logs dut_simulator
```
Look for error messages before restart.

### SSH not starting
Check if openssh-server is installed in the Dockerfile.

### Boot sequence incomplete
Verify entrypoint.sh has all echo statements and proper sleep delays.

## Advanced: Interactive Console

To connect to the simulated UART console:

```bash
docker-compose exec host_controller nc dut_simulator 23
```

Type commands and press Enter to interact with the bash shell.
Press Ctrl+C to disconnect.
