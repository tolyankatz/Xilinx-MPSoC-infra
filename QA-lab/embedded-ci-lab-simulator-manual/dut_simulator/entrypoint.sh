#!/bin/bash
set -e

# Start SSH daemon for Ethernet tests (Paramiko)
/usr/sbin/sshd || true

# Create boot script that will run for each TCP connection
cat > /boot_script.sh << 'EOF'
#!/bin/bash
sleep 0.5
echo "U-Boot 2020.01 (Simulated)"
sleep 1
echo "Starting kernel..."
sleep 1
echo "Linux version 5.10.0-xilinx" 
sleep 1
echo "Reached target Multi-User System"
sleep 1
echo "login:"
exec /bin/bash -i
EOF
chmod +x /boot_script.sh

# Start UART-like TCP console on port 23
exec socat TCP-LISTEN:23,fork,reuseaddr EXEC:/boot_script.sh
