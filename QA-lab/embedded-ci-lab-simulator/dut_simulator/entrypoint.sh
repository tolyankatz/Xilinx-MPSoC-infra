#!/bin/bash
set -e

# Simple simulated boot log
echo "Simulated DUT Boot Log..."
echo "Board: ZCU102 (Simulated)"
echo "Login:"

# Start UART-like TCP console on port 23
# Each connection gets an interactive bash shell, similar to a serial console.
exec socat TCP-LISTEN:23,fork,reuseaddr EXEC:'/bin/bash -i'
