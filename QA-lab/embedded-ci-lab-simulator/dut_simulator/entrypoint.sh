#!/bin/bash
set -e

# Generate SSH host keys if they don't exist
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

echo "============================================="
echo "ZCU102 Board Simulator - Boot Sequence"
echo "============================================="
echo ""

# Simulate FSBL stage
echo "[FSBL] Xilinx First Stage Boot Loader"
echo "[FSBL] Release 2024.1"
sleep 1
echo "[FSBL] Processor frequency: 1333 MHz"
echo "[FSBL] Board: ZCU102 Rev 1.0"
sleep 0.5
echo "[FSBL] Initializing PS..."
echo "[FSBL] DDR init successful"
echo "[FSBL] Loading U-Boot from QSPI..."
echo ""

# Simulate U-Boot stage
sleep 1
echo "U-Boot 2024.01 (Xilinx ZCU102 Board)"
echo "DRAM:  4 GiB"
echo "Flash: 128 MiB"
echo "MMC:   mmc@ff170000: 0"
sleep 0.5
echo "Loading Environment from SPI Flash..."
echo "SF: Detected n25q512a with page size 256 Bytes"
echo "Net:   ethernet@ff0e0000"
sleep 0.5
echo "Hit any key to stop autoboot:  0"
echo "Loading kernel from QSPI..."
echo ""

# Simulate Linux Kernel boot
sleep 1
echo "Starting kernel ..."
echo "[    0.000000] Linux version 6.1.0-xilinx (oe-user@oe-host)"
echo "[    0.000000] Machine: ZynqMP ZCU102 Rev1.0"
sleep 0.5
echo "[    0.234567] Memory: 4194304K available"
echo "[    0.456789] CPU: Cortex-A53 r0p4"
echo "[    0.678901] Zynq UltraScale+ MPSoC"
sleep 0.5
echo "[    1.234567] EXT4-fs (mmcblk0p2): mounted filesystem"
echo "[    1.456789] VFS: Mounted root (ext4 filesystem)"
sleep 0.5
echo "[    1.890123] Run /sbin/init as init process"
echo ""

# Simulate init system
sleep 1
echo "INIT: version 2.88 booting"
echo "Starting udev..."
sleep 0.5
echo "Configuring network interfaces... done."
echo "Starting OpenSSH server... sshd."
echo ""

# Display login prompt
sleep 0.5
echo "============================================="
echo "PetaLinux 2024.1 zcu102-zynqmp"
echo "============================================="
echo ""
echo "zcu102-zynqmp login: root"
echo ""
echo "Login prompt ready - SSH server starting..."
echo ""

# Start SSH daemon in background
/usr/sbin/sshd -D &

# Start UART-like TCP console on port 23
# This provides an interactive shell for serial console simulation
exec socat TCP-LISTEN:23,fork,reuseaddr EXEC:'/bin/bash -i'
