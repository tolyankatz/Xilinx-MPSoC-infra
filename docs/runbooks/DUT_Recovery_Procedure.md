# DUT Recovery Procedure

## Overview
This runbook provides step-by-step procedures for recovering a ZCU102 Development Unit Target (DUT) that has become unresponsive or "bricked" during testing operations.

## Symptoms
- **No Console Output**: Serial console shows no activity during power-on
- **Boot Failure**: System starts boot sequence but fails to complete
- **Network Inaccessible**: DUT fails to respond to ping or SSH after expected boot time
- **Flash Corruption**: Invalid or corrupted boot loader preventing system startup
- **Stuck in U-Boot**: System boots to U-Boot prompt but cannot load kernel

## Diagnosis Steps

### 1. Basic Connectivity Check
```bash
# Verify serial connection
sudo screen /dev/ttyUSB0 115200
# Or using minicom
sudo minicom -D /dev/ttyUSB0 -b 115200
```

### 2. Power Cycle Test
1. **Hard Power Off**: Disconnect power cable for 10 seconds
2. **Power On**: Reconnect power and observe boot sequence
3. **Check Boot Messages**: Look for error messages or hang points

### 3. SD Card Verification
```bash
# Check if SD card is detected by the system
lsblk
# Verify SD card filesystem integrity
sudo fsck /dev/mmcblk0p1
```

### 4. JTAG Connectivity Test
```bash
# Test JTAG connection using Vivado Hardware Manager
vivado -mode batch -source check_jtag.tcl
```

## Recovery Steps

### Method 1: SD Card Recovery (First Line of Defense)

1. **Prepare Recovery SD Card**
   ```bash
   # Format SD card (replace /dev/sdX with actual device)
   sudo fdisk /dev/sdX
   # Create boot partition (2GB, FAT32)
   sudo mkfs.fat -F32 -n BOOT /dev/sdX1
   # Create root partition (remaining space, ext4)
   sudo mkfs.ext4 -L rootfs /dev/sdX2
   ```

2. **Copy Known-Good Images**
   ```bash
   # Mount boot partition
   sudo mount /dev/sdX1 /mnt/boot
   # Copy boot files from last known good build
   sudo cp artifacts/BOOT.BIN /mnt/boot/
   sudo cp artifacts/image.ub /mnt/boot/
   sudo cp artifacts/system.dtb /mnt/boot/
   sudo umount /mnt/boot
   
   # Mount root partition and extract rootfs
   sudo mount /dev/sdX2 /mnt/root
   sudo tar -xzf artifacts/rootfs.tar.gz -C /mnt/root/
   sudo umount /mnt/root
   ```

3. **Insert SD Card and Power On**
   - Insert SD card into ZCU102
   - Set boot mode switches to SD card boot
   - Power on and monitor serial console

### Method 2: JTAG Recovery (Last Resort)

1. **Connect JTAG Debugger**
   - Ensure Xilinx Platform Cable USB or similar is connected
   - Verify JTAG chain detection

2. **Flash Boot Loader via JTAG**
   ```tcl
   # Vivado TCL script for JTAG flashing
   open_hw_manager
   connect_hw_server
   open_hw_target
   set_property PROGRAM.FILE {artifacts/BOOT.BIN} [get_hw_devices xc7z*]
   program_hw_devices [get_hw_devices xc7z*]
   ```

3. **Alternative: Use Xilinx SDK**
   ```bash
   # Using XSCT (Xilinx Software Command Line Tool)
   xsct recovery_script.tcl
   ```

### Method 3: Factory Reset Procedure

1. **Restore Factory Bootloader**
   - Use Xilinx-provided factory BOOT.BIN if available
   - Flash via JTAG using Vivado Hardware Manager

2. **Network Recovery Setup**
   ```bash
   # Set up TFTP server for network boot recovery
   sudo systemctl start tftp.service
   # Copy recovery images to TFTP directory
   sudo cp artifacts/*.* /var/lib/tftpboot/
   ```

## Prevention Measures

### Pre-Test Validation
- Always verify artifact checksums before deployment
- Test images on a separate development board first
- Maintain backup of last known good configuration

### Monitoring Setup
```python
# Add to test framework - heartbeat monitoring
def setup_heartbeat_monitor():
    """Set up watchdog timer for DUT responsiveness"""
    # Implementation for monitoring DUT health during tests
    pass
```

### Recovery Automation
```bash
#!/bin/bash
# Automated recovery script template
RECOVERY_LOG="/var/log/dut_recovery.log"
echo "$(date): Starting DUT recovery procedure..." >> $RECOVERY_LOG
# Add recovery automation logic here
```

## Emergency Contacts

- **Hardware Team Lead**: ext. 1234
- **BSP Engineering**: ext. 5678  
- **Test Infrastructure**: ext. 9012

## Related Documentation

- [ZCU102 User Guide](https://www.xilinx.com/support/documentation/boards_and_kits/zcu102/ug1182-zcu102-eval-bd.pdf)
- [Debugging Test Failures](./Debugging_Test_Failures.md)
- [JTAG Programming Reference](../architecture.md#jtag-programming)

---
**Last Updated**: November 2024  
**Document Owner**: Test Infrastructure Team  
**Review Cycle**: Quarterly
