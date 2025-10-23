# Unitree Robot Control Suite

**Professional Robot Control Interface for Unitree G1 and GO2W Robots**

A comprehensive GUI application for controlling Unitree robots, featuring camera streaming, robotic hand control, autonomous navigation, and SDK integration.

---

## 🚀 Features

- **🎮 Complete Robot Control**: Full G1 and GO2W robot control interface
- **📹 Real-time Camera Streaming**: Live camera feed from robot cameras
- **🤖 Inspire Hand Integration**: Control robotic hands via serial communication
- **🧭 Autonomous Navigation**: AI-powered autonomous movement capabilities
- **🔧 SDK Integration**: Direct integration with Unitree SDK2
- **📊 Simulation Support**: MuJoCo simulation environment
- **🌐 Network Management**: WiFi and Ethernet connection management
- **📱 Modern GUI**: Professional GTK3 interface with custom styling

---

## 📋 System Requirements

### Hardware
- **Robot**: Unitree G1 or GO2W robot
- **Computer**: Ubuntu 20.04 LTS (recommended) or Ubuntu 22.04 LTS
- **Network**: Ethernet or WiFi connection to robot
- **USB**: For Inspire Hand connection (CH340 serial adapter)

### Software Dependencies
- **Python**: 3.10.12 or compatible
- **ROS2**: Humble (recommended) or Foxy
- **GTK3**: For GUI interface
- **OpenCV**: For camera streaming
- **Unitree SDK2**: Complete SDK installation required

---

## 🛠️ Complete Installation Guide

### Step 1: System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
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
    wget
```

### Step 2: ROS2 Installation

```bash
# Install ROS2 Humble (recommended)
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-humble-desktop-full
sudo apt install -y python3-colcon-common-extensions

# Source ROS2
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Unitree SDK2 Installation

**⚠️ CRITICAL: This is the most important step - ALL paths depend on this installation!**

```bash
# Create workspace directory
mkdir -p ~/unitree_ros2
cd ~/unitree_ros2

# Clone Unitree SDK2 (C++ version)
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cd unitree_sdk2
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install

# Clone Unitree SDK2 Python bindings
cd ~/unitree_ros2
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
cd unitree_sdk2_python
pip3 install -e .

# Install CycloneDDS (required for ROS2 communication)
cd ~/unitree_ros2
git clone https://github.com/eclipse-cyclonedx/cyclonedx.git cyclonedx_ws
cd cyclonedx_ws
colcon build
```

**Expected Directory Structure After Installation:**
```
~/unitree_ros2/
├── unitree_sdk2/           # C++ SDK
│   ├── build/bin/          # Executable binaries
│   └── example/            # C++ examples
├── unitree_sdk2_python/    # Python SDK
│   └── example/            # Python examples
└── cyclonedx_ws/           # CycloneDDS workspace
    └── install/            # Built packages
```

### Step 4: Additional Tools Installation

```bash
# Install Livox Viewer (for LiDAR visualization)
# Download from: https://www.livoxtech.com/downloads
# Install to: /opt/livoxviewer2/

# Install MuJoCo (for simulation)
mkdir -p ~/unitree_mujoco
cd ~/unitree_mujoco
# Download MuJoCo from: https://mujoco.org/download
# Extract and build according to MuJoCo documentation
```

### Step 5: Python Dependencies

```bash
# Install Python packages
pip3 install -r requirements.txt

# Additional packages for specific features
pip3 install \
    matplotlib \
    scipy \
    pillow \
    requests
```

### Step 6: Inspire Hand Setup

```bash
# Install Inspire Hand Python module
cd ~/Desktop/unitree-robot-control-suite/inspire_hand/
sudo python3 setup.py install

# Add user to dialout group for serial access
sudo usermod -a -G dialout $USER

# Logout and login again for group changes to take effect
```

---

## 🚀 Quick Start

### 1. Clone This Repository

```bash
git clone <your-github-repo-url>
cd unitree-robot-control-suite
```

### 2. Run Installation Script

```bash
chmod +x install.sh
./install.sh
```

### 3. Launch the Application

```bash
python3 unitree_g1_full_menu.py
```

---

## 📁 Project Structure

```
unitree-robot-control-suite/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── install.sh                   # Automated installation script
├── .gitignore                   # Git ignore rules
├── unitree_g1_full_menu.py     # Main GUI application
├── go2w_camera_viewer.py        # Camera streaming utility
├── connect_inspire_hand.sh      # Inspire Hand connection script
├── inspire_hand/               # Inspire Hand Python module
│   ├── __init__.py
│   ├── cli.py
│   ├── hand.py
│   ├── modbus.py
│   └── exceptions.py
├── docs/                       # Documentation
│   ├── installation.md
│   ├── usage.md
│   └── troubleshooting.md
├── scripts/                    # Utility scripts
│   ├── setup_network.sh
│   ├── install_sdks.sh
│   └── verify_installation.sh
└── examples/                   # Example configurations
    ├── camera_config.yaml
    └── robot_config.yaml
```

---

## 🔧 Configuration

### Network Configuration

The application expects specific network interfaces:

- **Ethernet**: `enp3s0` (default robot connection)
- **WiFi**: `wlan0` (if using WiFi adapter)

### Robot IP Addresses

- **Default Robot IP**: `192.168.123.164`
- **SSH User**: `unitree`
- **SSH Password**: `unitree`

### Environment Variables

Add to your `~/.bashrc`:

```bash
# ROS2 Environment
source /opt/ros/humble/setup.bash
source ~/unitree_ros2/cyclonedx_ws/install/setup.bash
source ~/unitree_ros2/setup.sh

# Unitree SDK Environment
export UNITREE_SDK2_PATH=~/unitree_sdk2
export UNITREE_SDK2_PYTHON_PATH=~/unitree_sdk2_python

# DDS Configuration
export DDS_DOMAIN=0
export DDS_INTERFACE=enp3s0
export DDS_PARTICIPANT_INDEX=0
```

---

## 🎮 Usage

### Main Interface

1. **Launch Application**: `python3 unitree_g1_full_menu.py`
2. **Select Robot Type**: Choose G1 or GO2W
3. **Connect to Robot**: Ensure network connection
4. **Use Control Features**: Camera, movement, hand control, etc.

### Camera Streaming

```bash
# Direct camera viewer
python3 go2w_camera_viewer.py

# With specific network interface
python3 go2w_camera_viewer.py enp3s0
```

### Inspire Hand Control

```bash
# Connect to Inspire Hand
./connect_inspire_hand.sh

# Direct Python control
python3 -m inspire_hand.cli interactive
```

---

## 🔍 Troubleshooting

### Common Issues

**1. "No module named 'unitree_sdk2py'"**
- **Solution**: Ensure Unitree SDK2 Python is properly installed
- **Check**: `ls ~/unitree_sdk2_python/`

**2. "Camera connection failed"**
- **Solution**: Verify robot network connection
- **Check**: `ping 192.168.123.164`

**3. "Inspire Hand not found"**
- **Solution**: Check USB connection and permissions
- **Check**: `lsusb | grep CH340`

**4. "ROS2 not found"**
- **Solution**: Source ROS2 environment
- **Fix**: `source /opt/ros/humble/setup.bash`

### Verification Script

Run the verification script to check your installation:

```bash
./scripts/verify_installation.sh
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Michael** - **
- Created: October 2025
- Experience: 3 months of robot development (started from 0% knowledge!)

---

## 🙏 Acknowledgments

- Unitree Robotics for the excellent SDK and documentation
- ROS2 community for the robust robotics framework
- Ubuntu community for the stable Linux platform
- OpenCV community for computer vision capabilities

---

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact: [Your contact information]
- Documentation: Check the `docs/` folder

---

**⭐ If this project helped you, please give it a star!**
