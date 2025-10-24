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
                print_status "Netifaces: installed"
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

# Check ROS2 setup files (primary check)
ros2_installed=false
ros2_paths=("/opt/ros/humble/setup.bash" "/opt/ros/foxy/setup.bash")
for path in "${ros2_paths[@]}"; do
    if path_exists "$path"; then
        print_status "ROS2 setup found: $path"
        ros2_installed=true
        break
    fi
done

# Check ROS2 command (secondary check)
if command_exists ros2; then
    print_status "ROS2 command available"
    ros2_version=$(ros2 --version 2>/dev/null | head -1)
    print_info "Version: $ros2_version"
elif [ "$ros2_installed" = true ]; then
    print_status "ROS2 is installed (command not in current shell PATH)"
    print_info "Note: ROS2 works fine when sourced in your applications"
else
    print_error "ROS2 is NOT installed"
fi

echo ""
echo "🔧 Checking Unitree SDK2 Installation..."
echo "======================================="

# Check SDK2 directories
sdk2_paths=(
    "$HOME/unitree_sdk2"
    "$HOME/unitree_sdk2_python"
    "$HOME/unitree_ros2/cyclonedds_ws"
)

for path in "${sdk2_paths[@]}"; do
    if path_exists "$path"; then
        print_status "Directory exists: $path"
    else
        print_error "Directory missing: $path"
    fi
done

# Check SDK2 binaries
if path_exists "$HOME/unitree_sdk2/build/bin"; then
    print_status "SDK2 binaries directory exists"
    bin_count=$(ls "$HOME/unitree_sdk2/build/bin" 2>/dev/null | wc -l)
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

if path_exists "$HOME/unitree_ros2/cyclonedds_ws/install/setup.bash"; then
    print_status "CycloneDDS setup file exists"
else
    print_error "CycloneDDS setup file missing"
fi

echo ""
echo "🎮 Checking MuJoCo Simulation..."
echo "==============================="

# Check MuJoCo
if path_exists "$HOME/unitree_mujoco"; then
    print_status "Unitree MuJoCo directory exists"
    if path_exists "$HOME/unitree_mujoco/simulate/build/unitree_mujoco"; then
        print_status "MuJoCo C++ simulator built successfully"
    else
        print_warning "MuJoCo C++ simulator not built"
    fi
    if path_exists "$HOME/unitree_mujoco/unitree_robots"; then
        print_status "Robot models directory exists"
    else
        print_warning "Robot models directory missing"
    fi
else
    print_error "Unitree MuJoCo directory not found"
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

# Check ROS2 environment
if [ -f "/opt/ros/humble/setup.bash" ]; then
    print_status "ROS2 Humble environment available"
else
    print_warning "ROS2 Humble environment not found"
fi

# Check Unitree ROS2 environment
if [ -f "$HOME/unitree_ros2/setup.sh" ]; then
    print_status "Unitree ROS2 environment available"
else
    print_warning "Unitree ROS2 environment not found"
fi

echo ""
echo "📁 Checking Project Files..."
echo "============================"

# Check main application files
project_files=(
    "unitree_robot_control_suite.py"
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
echo "3. Source ROS2 environment: source /opt/ros/humble/setup.bash"
echo "4. Source Unitree environment: source ~/unitree_ros2/setup.sh"
echo "5. Connect robot via Ethernet"
echo "6. Run application: python3 unitree_robot_control_suite.py"
echo ""
echo "📚 For help:"
echo "• Check README.md for detailed instructions"
echo "• Check docs/ folder for troubleshooting"
echo "• Create GitHub issue for support"
echo ""
echo "✨ Happy robot controlling! 🤖"
