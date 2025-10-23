#!/bin/bash

# Check if the device is physically connected via lsusb
if ! lsusb | grep -q '1a86:7523'; then
    echo "Qinheng CH340 device not connected."
    read -p "Press Enter to exit..."
    exit 1
fi

# Try /dev/serial/by-id first (more stable)
PORT=$(readlink -f /dev/serial/by-id/*USB_Serial-if00-port0 2>/dev/null | head -1)

# If not found, try /dev/ttyUSB*
if [ -z "$PORT" ]; then
    for dev in /dev/ttyUSB*; do
        if udevadm info --query=all --name="$dev" 2>/dev/null | grep -q 'ID_VENDOR_ID=1a86'; then
            if udevadm info --query=all --name="$dev" 2>/dev/null | grep -q 'ID_MODEL_ID=7523'; then
                PORT="$dev"
                break
            fi
        fi
    done
fi

if [ -z "$PORT" ]; then
    echo "Qinheng CH340 device not found!"
    echo "- Detected via lsusb but no serial node yet. Try: sudo modprobe ch341; replug USB; or check dmesg."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "Connecting to Inspire Hand on $PORT..."
python3 -m inspire_hand.cli --port "$PORT" interactive
read -p "Press Enter to exit..."
