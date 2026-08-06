# Installation guide

Manual installation for **Unitree Robot Control Suite**. Prefer `./install.sh` when possible — it targets the hardcoded paths the GUI expects.

## System requirements

### Hardware

- Unitree G1 or GO2W robot
- Ubuntu 20.04 LTS (recommended) or 22.04 LTS
- Ethernet or WiFi to robot
- USB CH340 adapter for Inspire Hand

### Software

- Python 3.10.12 or compatible
- ROS2 Humble (recommended) or Foxy
- GTK3, OpenCV, pcl-tools
- Full Unitree SDK2 stack (see paths in [README.md](../README.md))

---

## Step 1: System dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y \
    python3 python3-pip python3-gi python3-gi-cairo \
    libgtk-3-0 gnome-terminal nautilus git build-essential \
    cmake curl wget pcl-tools
```

---

## Step 2: ROS2 Humble

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install -y ros-humble-desktop-full python3-colcon-common-extensions
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## Step 3: Unitree SDK2 (C++)

**Path:** `~/unitree_sdk2/`

```bash
cd ~
git clone https://github.com/unitreerobotics/unitree_sdk2.git
cd unitree_sdk2
mkdir build && cd build
cmake ..
make -j$(nproc)
sudo make install
```

---

## Step 4: Unitree ROS2

**Path:** `~/unitree_ros2/`

```bash
mkdir -p ~/unitree_ros2 && cd ~/unitree_ros2
git clone https://github.com/unitreerobotics/unitree_ros2.git .
colcon build
```

---

## Step 5: Unitree SDK2 Python

**Path:** `~/unitree_sdk2_python/`

```bash
cd ~
git clone https://github.com/unitreerobotics/unitree_sdk2_python.git
cd unitree_sdk2_python
pip3 install -e .
```

---

## Step 6: Unitree MuJoCo

**Path:** `~/unitree_mujoco/`

```bash
cd ~
git clone https://github.com/unitreerobotics/unitree_mujoco.git
cd unitree_mujoco
sudo apt install -y libgl1-mesa-glx libglfw3 libglfw3-dev libgles2-mesa-dev
cd simulate && mkdir build && cd build
cmake .. && make -j$(nproc)
cd ~/unitree_mujoco/simulate_python && pip3 install -e .
```

---

## Step 7: CycloneDDS

**Path:** `~/unitree_ros2/cyclonedds_ws/`

```bash
mkdir -p ~/unitree_ros2 && cd ~/unitree_ros2
git clone https://github.com/eclipse-cyclonedx/cyclonedx.git cyclonedds_ws
cd cyclonedds_ws && colcon build
```

---

## Step 8: Python dependencies

```bash
cd ~/unitree-robot-control-suite
pip3 install -r requirements.txt
pip3 install matplotlib scipy pillow requests
```

---

## Step 9: Inspire Hand

Based on [Sentdex/inspire_hands](https://github.com/Sentdex/inspire_hands). Module must live in the repo at `inspire_hand/`.

```bash
cd ~/unitree-robot-control-suite/inspire_hand/
sudo python3 setup.py install
sudo usermod -a -G dialout $USER
# Log out and back in for dialout group
```

---

## Environment variables

Add to `~/.bashrc`:

```bash
source /opt/ros/humble/setup.bash
source ~/unitree_ros2/cyclonedx_ws/install/setup.bash
source ~/unitree_ros2/setup.sh
export UNITREE_SDK2_PATH=~/unitree_sdk2
export UNITREE_SDK2_PYTHON_PATH=~/unitree_sdk2_python
export DDS_DOMAIN=0
export DDS_INTERFACE=enp3s0
export DDS_PARTICIPANT_INDEX=0
```

---

## Network defaults

| Setting | Default |
|---------|---------|
| Ethernet interface | `enp3s0` |
| WiFi interface | `wlan0` |
| Robot IP | `192.168.123.164` |
| SSH user / password | `unitree` / `unitree` |

Change these for your lab network.

---

## SLAM workflow (Hesai XT16)

1. Start XT16 lidar driver
2. Start SLAM service
3. Start KeyDemo — `q` to map, `w` to save
4. Visualize in RViz (configs in repo root: `hesai_xt16_*.rviz`, `g1_slam_*.rviz`)
5. Maps stored on robot at `/home/unitree/*.pcd`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No module named 'unitree_sdk2py'` | Reinstall SDK2 Python at `~/unitree_sdk2_python/` |
| Camera connection failed | `ping 192.168.123.164`, check `enp3s0` |
| Inspire Hand not found | USB cable, `lsusb \| grep CH340`, dialout group |
| ROS2 not found | `source /opt/ros/humble/setup.bash` |

Run `./scripts/verify_installation.sh` for automated checks.
