#!/bin/bash

# Unitree Robot Control Suite - Installation Verification Script
# Created: October 24, 2025
# Author: Michael

echo "🔍 Unitree Robot Control Suite - Verification Script"
echo "====================================================="
echo ""

# Function to print colored output
print_status() {
    echo -e "\033[1;32m✅ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m❌ $1\033[0m"
}

print_warning() {
    echo -e "\033[1;33m⚠️  $1\033[0m"
}

print_info() {
    echo -e "\033[1;34mℹ️  $1\033[0m"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if file/directory exists
path_exists() {
    [ -e "$1" ]
}

# Function to check Python package
check_python_package() {
    python3 -c "import $1" 2>/dev/null
}

echo "📋 System Information:"
echo "====================="
echo "OS: $(lsb_release -d | cut -f2)"
echo "Kernel: $(uname -r)"
echo "Architecture: $(uname -m)"
echo "Python: $(python3 --version)"
echo ""

echo "🔧 Checking System Dependencies..."
echo "=================================="

# Check essential commands
commands=("python3" "pip3" "git" "cmake" "make" "gcc" "gnome-terminal" "nautilus")
for cmd in "${commands[@]}"; do
    if command_exists "$cmd"; then
        print_status "$cmd is installed"
    else
        print_error "$cmd is NOT installed"
    fi
done

echo ""
echo "🐍 Checking Python Packages..."
echo "=============================="

# Check Python packages
packages=("gi" "cv2" "numpy" "netifaces" "serial")
for pkg in "${packages[@]}"; do
    if check_python_package "$pkg"; then
        case $pkg in
            "gi")
                version=$(python3 -c "import gi; print(gi.version_info)")
                print_status "PyGObject: $version"
                ;;
            "cv2")
                version=$(python3 -c "import cv2; print(cv2.__version__)")
                print_status "OpenCV: $version"
                ;;
            "numpy")
                version=$(python3 -c "import numpy; print(numpy.__version__)")
                print_status "NumPy: $version"
                ;;
            "netifaces")
                version=$(python3 -c "import netifaces; print(netifaces.__version__)")
                print_status "Netifaces: $version"
                ;;
            "serial")
                version=$(python3 -c "import serial; print(serial.__version__)")
                print_status "PySerial: $version"
                ;;
        esac
    else
        print_error "$pkg is NOT installed"
    fi
done

echo ""
echo "🤖 Checking ROS2 Installation..."
echo "==============================="

if command_exists ros2; then
    print_status "ROS2 is installed"
    ros2_version=$(ros2 --version 2>/dev/null | head -1)
    print_info "Version: $ros2_version"
else
    print_error "ROS2 is NOT installed"
fi

# Check ROS2 setup files
ros2_paths=("/opt/ros/humble/setup.bash" "/opt/ros/foxy/setup.bash")
for path in "${ros2_paths[@]}"; do
    if path_exists "$path"; then
        print_status "ROS2 setup found: $path"
    fi
done

echo ""
echo "🔧 Checking Unitree SDK2 Installation..."
echo "======================================="

# Check SDK2 directories
sdk2_paths=(
    "$HOME/unitree_ros2/unitree_sdk2"
    "$HOME/unitree_ros2/unitree_sdk2_python"
    "$HOME/unitree_ros2/cyclonedx_ws"
)

for path in "${sdk2_paths[@]}"; do
    if path_exists "$path"; then
        print_status "Directory exists: $path"
    else
        print_error "Directory missing: $path"
    fi
done

# Check SDK2 binaries
if path_exists "$HOME/unitree_ros2/unitree_sdk2/build/bin"; then
    print_status "SDK2 binaries directory exists"
    bin_count=$(ls "$HOME/unitree_ros2/unitree_sdk2/build/bin" 2>/dev/null | wc -l)
    print_info "Found $bin_count binary files"
else
    print_error "SDK2 binaries directory missing"
fi

# Check SDK2 Python module
if check_python_package "unitree_sdk2py"; then
    print_status "Unitree SDK2 Python module is installed"
else
    print_warning "Unitree SDK2 Python module not found (may need to source environment)"
fi

echo ""
echo "🌪️  Checking CycloneDDS Installation..."
echo "========================================"

if path_exists "$HOME/unitree_ros2/cyclonedx_ws/install/setup.bash"; then
    print_status "CycloneDDS setup file exists"
else
    print_error "CycloneDDS setup file missing"
fi

echo ""
echo "🤖 Checking Inspire Hand Module..."
echo "================================="

if check_python_package "inspire_hand"; then
    print_status "Inspire Hand module is installed"
else
    print_warning "Inspire Hand module not found"
fi

# Check serial port permissions
if groups | grep -q dialout; then
    print_status "User is in dialout group"
else
    print_warning "User is NOT in dialout group (needed for serial access)"
fi

echo ""
echo "🌍 Checking Environment Setup..."
echo "==============================="

# Check environment file
if path_exists "$HOME/.unitree_env"; then
    print_status "Environment setup file exists: ~/.unitree_env"
else
    print_warning "Environment setup file missing: ~/.unitree_env"
fi

# Check bashrc
if grep -q "source ~/.unitree_env" ~/.bashrc; then
    print_status "Environment sourcing added to ~/.bashrc"
else
    print_warning "Environment sourcing NOT added to ~/.bashrc"
fi

echo ""
echo "📁 Checking Project Files..."
echo "============================"

# Check main application files
project_files=(
    "unitree_g1_full_menu.py"
    "go2w_camera_viewer.py"
    "connect_inspire_hand.sh"
    "requirements.txt"
    "README.md"
    "install.sh"
    ".gitignore"
)

for file in "${project_files[@]}"; do
    if path_exists "$file"; then
        print_status "Project file exists: $file"
    else
        print_error "Project file missing: $file"
    fi
done

# Check Inspire Hand module
if path_exists "inspire_hand"; then
    print_status "Inspire Hand module directory exists"
else
    print_error "Inspire Hand module directory missing"
fi

echo ""
echo "🔌 Checking Network Configuration..."
echo "==================================="

# Check network interfaces
interfaces=("enp3s0" "wlan0")
for iface in "${interfaces[@]}"; do
    if ip link show "$iface" >/dev/null 2>&1; then
        print_status "Network interface exists: $iface"
    else
        print_warning "Network interface not found: $iface"
    fi
done

# Check robot IP connectivity
if ping -c 1 -W 1 192.168.123.164 >/dev/null 2>&1; then
    print_status "Robot IP (192.168.123.164) is reachable"
else
    print_warning "Robot IP (192.168.123.164) is NOT reachable"
fi

echo ""
echo "📊 Summary..."
echo "============="

# Count issues
error_count=0
warning_count=0

# This is a simplified count - in a real implementation, you'd track these during checks
print_info "Verification completed"
print_info "Check the output above for any ❌ errors or ⚠️ warnings"
print_info "All ✅ items are working correctly"

echo ""
echo "🚀 Next Steps:"
echo "=============="
echo "1. Fix any ❌ errors shown above"
echo "2. Address any ⚠️ warnings if needed"
echo "3. Source environment: source ~/.unitree_env"
echo "4. Connect robot via Ethernet"
echo "5. Run application: python3 unitree_g1_full_menu.py"
echo ""
echo "📚 For help:"
echo "• Check README.md for detailed instructions"
echo "• Check docs/ folder for troubleshooting"
echo "• Create GitHub issue for support"
echo ""
echo "✨ Happy robot controlling! 🤖"
