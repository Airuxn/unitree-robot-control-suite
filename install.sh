#!/bin/bash

# Unitree Robot Control Suite - Complete Installation Script
# Created: October 24, 2025
# Author: Michael
# Description: Automated installation of all dependencies and SDKs

set -e  # Exit on any error

echo "🤖 Unitree Robot Control Suite - Installation Script"
echo "=================================================="
echo ""
echo "This script will install ALL required dependencies and SDKs"
echo "for the Unitree Robot Control Suite."
echo ""
echo "⚠️  IMPORTANT: This will take 30-60 minutes depending on your internet speed"
echo "⚠️  Make sure you have a stable internet connection"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root (sudo). Run as normal user."
    echo "   The script will ask for sudo when needed."
    exit 1
fi

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

# Function to wait for user confirmation
wait_for_confirmation() {
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."
    echo ""
}

echo "📋 Installation Checklist:"
echo "1. System Dependencies (apt packages)"
echo "2. ROS2 Humble Installation"
echo "3. Unitree SDK2 (C++ and Python)"
echo "4. CycloneDDS Installation"
echo "5. Python Dependencies"
echo "6. Inspire Hand Module"
echo "7. Environment Setup"
echo "8. Verification"
echo ""

wait_for_confirmation

# Step 1: System Dependencies
echo "🔧 Step 1: Installing System Dependencies..."
echo "============================================="

print_info "Updating package lists..."
sudo apt update

print_info "Installing essential packages..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-gi \
    python3-gi-cairo \
    libgtk-3-0 \
    gnome-terminal \
    nautilus \
    git \
    build-essential \
    cmake \
    curl \
    wget \
    software-properties-common \
    python3-colcon-common-extensions \
    python3-setuptools \
    python3-wheel

print_status "System dependencies installed successfully"

# Step 2: ROS2 Installation
echo ""
echo "🤖 Step 2: Installing ROS2 Humble..."
echo "===================================="

if command_exists ros2; then
    print_warning "ROS2 already installed, skipping..."
else
    print_info "Adding ROS2 repository..."
    sudo add-apt-repository universe
    sudo apt update && sudo apt install -y curl
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    print_info "Installing ROS2 Humble..."
    sudo apt update
    sudo apt install -y ros-humble-desktop-full
    
    print_status "ROS2 Humble installed successfully"
fi

# Step 3: Create Workspace Directory
echo ""
echo "📁 Step 3: Setting up Workspace..."
echo "=================================="

WORKSPACE_DIR="$HOME/unitree_ros2"
print_info "Creating workspace directory: $WORKSPACE_DIR"
mkdir -p "$WORKSPACE_DIR"
cd "$WORKSPACE_DIR"

print_status "Workspace directory created"

# Step 4: Install Required SDKs
echo ""
echo "📦 Step 4: Installing Required SDKs..."
echo "====================================="

print_info "Installing SDKs to exact paths your app expects..."

# Step 5: Install Unitree SDK2 (C++) (CRITICAL: App expects ~/unitree_sdk2/)
echo ""
echo "🔧 Step 5: Installing Unitree SDK2 (C++)..."
echo "=========================================="

print_info "CRITICAL: App expects C++ SDK at ~/unitree_sdk2/"

if [ -d "$HOME/unitree_sdk2" ]; then
    print_status "✓ Unitree SDK2 (C++) already exists at ~/unitree_sdk2"
else
    print_info "Installing Unitree SDK2 (C++) to ~/unitree_sdk2..."
    cd "$HOME"
    git clone https://github.com/unitreerobotics/unitree_sdk2.git
    cd unitree_sdk2
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    sudo make install
    print_status "✓ Unitree SDK2 (C++) installed to ~/unitree_sdk2"
fi

# Step 6: Install Unitree ROS2 (CRITICAL: App expects ~/unitree_ros2/)
echo ""
echo "🤖 Step 6: Installing Unitree ROS2..."
echo "===================================="

print_info "CRITICAL: App expects ROS2 workspace at ~/unitree_ros2/"

if [ -d "$WORKSPACE_DIR" ] && [ "$(ls -A $WORKSPACE_DIR)" ]; then
    print_status "✓ Unitree ROS2 workspace already exists at ~/unitree_ros2"
else
    print_info "Installing Unitree ROS2 workspace to ~/unitree_ros2..."
    cd "$WORKSPACE_DIR"
    git clone https://github.com/unitreerobotics/unitree_ros2.git .
    colcon build
    print_status "✓ Unitree ROS2 workspace installed to ~/unitree_ros2"
fi

# Step 7: Install Unitree SDK2 Python (CRITICAL: App expects ~/unitree_sdk2_python/)
echo ""
echo "🐍 Step 7: Installing Unitree SDK2 Python..."
echo "==========================================="

print_info "CRITICAL: App expects SDK2 Python at ~/unitree_sdk2_python/"

if [ -d "$HOME/unitree_sdk2_python" ]; then
    print_status "✓ Unitree SDK2 Python already exists at ~/unitree_sdk2_python"
else
    print_info "Installing Unitree SDK2 Python to ~/unitree_sdk2_python..."
    cd "$HOME"
    git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
    cd unitree_sdk2_python
    pip3 install -e .
    print_status "✓ Unitree SDK2 Python installed to ~/unitree_sdk2_python"
fi

# Step 8: Install Unitree MuJoCo (CRITICAL: App expects ~/unitree_mujoco/)
echo ""
echo "🎮 Step 8: Installing Unitree MuJoCo..."
echo "======================================"

print_info "CRITICAL: App expects MuJoCo at ~/unitree_mujoco/"

if [ -d "$HOME/unitree_mujoco" ]; then
    print_status "✓ Unitree MuJoCo already exists at ~/unitree_mujoco"
else
    print_info "Installing Unitree MuJoCo to ~/unitree_mujoco..."
    cd "$HOME"
    git clone https://github.com/unitreerobotics/unitree_mujoco.git
    cd unitree_mujoco
    
    print_info "Installing MuJoCo dependencies..."
    sudo apt install -y libgl1-mesa-glx libglfw3 libglfw3-dev libgles2-mesa-dev
    
    print_info "Building C++ simulator..."
    cd simulate
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    cd "$HOME/unitree_mujoco"
    
    print_info "Building Python simulator..."
    cd simulate_python
    pip3 install -e .
    print_status "✓ Unitree MuJoCo installed to ~/unitree_mujoco"
fi

# Step 9: Install CycloneDDS (CRITICAL: App expects cyclonedds_ws, not cyclonedx!)
echo ""
echo "🌐 Step 9: Installing CycloneDDS..."
echo "=================================="

print_info "CRITICAL: App expects CycloneDDS at ~/unitree_ros2/cyclonedds_ws/"

if [ -d "$WORKSPACE_DIR/cyclonedds_ws" ]; then
    print_status "✓ CycloneDDS already exists at ~/unitree_ros2/cyclonedds_ws"
else
    print_info "Installing CycloneDDS to ~/unitree_ros2/cyclonedds_ws..."
    cd "$WORKSPACE_DIR"
    git clone https://github.com/eclipse-cyclonedx/cyclonedx.git cyclonedds_ws
    cd cyclonedds_ws
    colcon build
    print_status "✓ CycloneDDS installed to ~/unitree_ros2/cyclonedds_ws"
fi

# Step 10: Python Dependencies
echo ""
echo "🐍 Step 10: Installing Python Dependencies..."
echo "============================================"

print_info "Installing Python packages..."
pip3 install -r requirements.txt

print_info "Installing additional packages..."
pip3 install matplotlib scipy pillow requests

print_status "Python dependencies installed"

# Step 5: Unitree SDK2 Installation
echo ""
echo "🔧 Step 4: Installing Unitree SDK2..."
echo "====================================="

# Check if SDK2 already exists
if [ -d "$WORKSPACE_DIR/unitree_sdk2" ]; then
    print_warning "Unitree SDK2 already exists, skipping C++ installation..."
else
    print_info "Cloning Unitree SDK2 (C++)..."
    git clone https://github.com/unitreerobotics/unitree_sdk2.git
    cd unitree_sdk2
    
    print_info "Building Unitree SDK2..."
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    sudo make install
    
    print_status "Unitree SDK2 (C++) installed successfully"
fi

# Step 5: Unitree SDK2 Python Installation
echo ""
echo "🐍 Step 5: Installing Unitree SDK2 Python..."
echo "============================================"

cd "$WORKSPACE_DIR"

if [ -d "$WORKSPACE_DIR/unitree_sdk2_python" ]; then
    print_warning "Unitree SDK2 Python already exists, skipping..."
else
    print_info "Cloning Unitree SDK2 Python..."
    git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
    cd unitree_sdk2_python
    
    print_info "Installing Unitree SDK2 Python..."
    pip3 install -e .
    
    print_status "Unitree SDK2 Python installed successfully"
fi

# Step 6: MuJoCo Installation
echo ""
echo "🎮 Step 6: Installing MuJoCo Simulation..."
echo "=========================================="

if [ -d "unitree_mujoco" ]; then
    print_info "Installing MuJoCo dependencies..."
    sudo apt install -y libgl1-mesa-glx libglfw3 libglfw3-dev libgles2-mesa-dev
    
    print_info "Building C++ simulator (recommended)..."
    cd unitree_mujoco/simulate
    mkdir build && cd build
    cmake ..
    make -j$(nproc)
    cd "$WORKSPACE_DIR"
    
    print_info "Building Python simulator (optional)..."
    cd unitree_mujoco/simulate_python
    pip3 install -e .
    cd "$WORKSPACE_DIR"
    
    print_status "MuJoCo simulation installed successfully"
else
    print_error "Unitree MuJoCo submodule not found"
fi

cd "$WORKSPACE_DIR"

if [ -d "$WORKSPACE_DIR/cyclonedx_ws" ]; then
    print_warning "CycloneDDS already exists, skipping..."
else
    print_info "Cloning CycloneDDS..."
    git clone https://github.com/eclipse-cyclonedx/cyclonedx.git cyclonedx_ws
    cd cyclonedx_ws
    
    print_info "Building CycloneDDS..."
    colcon build
    
    print_status "CycloneDDS installed successfully"
fi

# Step 8: Python Dependencies
echo ""
echo "📦 Step 8: Installing Python Dependencies..."
echo "============================================"

# Install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    print_info "Installing dependencies from requirements.txt..."
    pip3 install -r requirements.txt
else
    print_info "Installing core Python dependencies..."
    pip3 install \
        PyGObject \
        opencv-python \
        numpy \
        netifaces \
        pyserial \
        packaging \
        matplotlib \
        scipy \
        pillow \
        requests
fi

print_status "Python dependencies installed successfully"

# Step 9: Inspire Hand Installation
echo ""
echo "🤖 Step 9: Installing Inspire Hand Module..."
echo "============================================"

# Check if inspire_hand directory exists in current project
if [ -d "inspire_hand" ]; then
    print_info "Installing Inspire Hand module..."
    cd inspire_hand
    sudo python3 setup.py install
    
    print_info "Adding user to dialout group..."
    sudo usermod -a -G dialout $USER
    
    print_status "Inspire Hand module installed successfully"
else
    print_warning "Inspire Hand module not found in current directory"
    print_info "You can install it manually later if needed"
fi

# Step 10: Environment Setup
echo ""
echo "🌍 Step 10: Setting up Environment..."
echo "===================================="

# Create environment setup script
ENV_SETUP_FILE="$HOME/.unitree_env"
print_info "Creating environment setup file: $ENV_SETUP_FILE"

cat > "$ENV_SETUP_FILE" << 'EOF'
#!/bin/bash
# Unitree Robot Control Suite Environment Setup
# Source this file: source ~/.unitree_env

# ROS2 Environment
if [ -f /opt/ros/humble/setup.bash ]; then
    source /opt/ros/humble/setup.bash
    echo "✅ ROS2 Humble sourced"
fi

# Unitree SDK2 Environment
if [ -d ~/unitree_sdk2 ]; then
    export UNITREE_SDK2_PATH=~/unitree_sdk2
    echo "✅ Unitree SDK2 path set"
fi

if [ -d ~/unitree_sdk2_python ]; then
    export UNITREE_SDK2_PYTHON_PATH=~/unitree_sdk2_python
    echo "✅ Unitree SDK2 Python path set"
fi

# CycloneDDS Environment
if [ -f ~/unitree_ros2/cyclonedds_ws/install/setup.bash ]; then
    source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
    echo "✅ CycloneDDS sourced"
fi

# DDS Configuration
export DDS_DOMAIN=0
export DDS_INTERFACE=enp3s0
export DDS_PARTICIPANT_INDEX=0

echo "🚀 Unitree environment ready!"
EOF

# Add to bashrc
print_info "Adding environment setup to ~/.bashrc..."
if ! grep -q "source ~/.unitree_env" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Unitree Robot Control Suite Environment" >> ~/.bashrc
    echo "source ~/.unitree_env" >> ~/.bashrc
fi

print_status "Environment setup completed"

# Step 11: Verification
echo ""
echo "🔍 Step 11: Verifying Installation..."
echo "====================================="

# Check Python packages
print_info "Checking Python packages..."
python3 -c "import gi; print('✅ PyGObject:', gi.version_info)"
python3 -c "import cv2; print('✅ OpenCV:', cv2.__version__)"
python3 -c "import numpy; print('✅ NumPy:', numpy.__version__)"
python3 -c "import netifaces; print('✅ Netifaces:', netifaces.__version__)"
python3 -c "import serial; print('✅ PySerial:', serial.__version__)"

# Check ROS2
if command_exists ros2; then
    print_status "ROS2 is installed and available"
else
    print_error "ROS2 not found in PATH"
fi

# Check Unitree SDK2
if [ -d "$WORKSPACE_DIR/unitree_sdk2" ]; then
    print_status "Unitree SDK2 directory exists"
else
    print_error "Unitree SDK2 directory not found"
fi

if [ -d "$WORKSPACE_DIR/unitree_sdk2_python" ]; then
    print_status "Unitree SDK2 Python directory exists"
else
    print_error "Unitree SDK2 Python directory not found"
fi

# Check CycloneDDS
if [ -d "$WORKSPACE_DIR/cyclonedx_ws" ]; then
    print_status "CycloneDDS workspace exists"
else
    print_error "CycloneDDS workspace not found"
fi

# Final Summary
echo ""
echo "🎉 Installation Complete!"
echo "========================"
echo ""
echo "📋 What was installed:"
echo "✅ System dependencies (apt packages)"
echo "✅ ROS2 Humble"
echo "✅ Unitree SDK2 (C++ and Python)"
echo "✅ CycloneDDS"
echo "✅ Python dependencies"
echo "✅ Inspire Hand module"
echo "✅ Environment configuration"
echo ""
echo "📁 Important Directories:"
echo "• Workspace: $WORKSPACE_DIR"
echo "• SDK2 C++: $WORKSPACE_DIR/unitree_sdk2"
echo "• SDK2 Python: $WORKSPACE_DIR/unitree_sdk2_python"
echo "• CycloneDDS: $WORKSPACE_DIR/cyclonedx_ws"
echo "• Environment: $ENV_SETUP_FILE"
echo ""
echo "🚀 Next Steps:"
echo "1. Logout and login again (for group changes)"
echo "2. Source environment: source ~/.unitree_env"
echo "3. Connect your robot via Ethernet"
echo "4. Run the application: python3 unitree_g1_full_menu.py"
echo ""
echo "📚 Documentation:"
echo "• README.md - Complete usage guide"
echo "• docs/ - Detailed documentation"
echo "• GitHub Issues - For support"
echo ""
echo "✨ Happy robot controlling! 🤖"

# Make environment file executable
chmod +x "$ENV_SETUP_FILE"

print_status "Installation script completed successfully!"
