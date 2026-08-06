# Unitree Robot Control Suite

GTK3 control UI for **Unitree G1** and **GO2W** robots — camera streaming, Inspire Hand serial control, SLAM/navigation (Hesai XT16), and Unitree SDK2 integration.

**Status:** stable · **Requires:** Ubuntu 20.04/22.04, physical G1 or GO2W, SDK paths below · [MIT](LICENSE)

[![CI](https://github.com/Airuxn/unitree-robot-control-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/Airuxn/unitree-robot-control-suite/actions/workflows/ci.yml)

---

## Quick start

```bash
git clone https://github.com/Airuxn/unitree-robot-control-suite.git
cd unitree-robot-control-suite
chmod +x install.sh
./install.sh
python3 unitree_robot_control_suite.py
```

Verify paths after install: `./scripts/verify_installation.sh`

Full manual install (ROS2, SDK2, MuJoCo, CycloneDDS): [docs/INSTALL.md](docs/INSTALL.md)

---

## Features

- G1 and GO2W robot control from a single GTK3 GUI
- Real-time camera streaming (`go2w_camera_viewer.py`)
- Inspire Hand control via CH340 serial (`inspire_hand/`, based on [Sentdex/inspire_hands](https://github.com/Sentdex/inspire_hands))
- SLAM mapping and relocation with Hesai XT16 lidar (RViz configs included)
- PCD map listing and visualization
- MuJoCo simulation hooks
- WiFi / Ethernet network management for robot link

---

## Required SDK paths

The application expects **fixed install locations**. `install.sh` targets these paths — do not relocate without updating the app.

| Component | Path |
|-----------|------|
| Unitree SDK2 (C++) | `~/unitree_sdk2/` |
| Unitree SDK2 Python | `~/unitree_sdk2_python/` |
| Unitree ROS2 | `~/unitree_ros2/` |
| Unitree MuJoCo | `~/unitree_mujoco/` |
| CycloneDDS workspace | `~/unitree_ros2/cyclonedds_ws/` |
| Unitree G1 Autonomous | `~/unitree-g1-autonomous/` |
| ROS2 Humble | `/opt/ros/humble/setup.bash` |
| Inspire Hand module | `./inspire_hand/` (in repo) |

Official SDKs: [unitree_sdk2](https://github.com/unitreerobotics/unitree_sdk2) · [unitree_sdk2_python](https://github.com/unitreerobotics/unitree_sdk2_python) · [unitree_ros2](https://github.com/unitreerobotics/unitree_ros2) · [unitree_mujoco](https://github.com/unitreerobotics/unitree_mujoco)

---

## System requirements

| | |
|--|--|
| **Hardware** | Unitree G1 or GO2W; Ubuntu PC; Ethernet or WiFi to robot; USB for Inspire Hand (CH340) |
| **Software** | Python 3.10+, ROS2 Humble, GTK3, OpenCV, pcl-tools, full Unitree SDK2 stack |

Default robot IP: `192.168.123.164` (user `unitree`). Default Ethernet interface: `enp3s0`.

---

## Repository layout

| Path | Description |
|------|-------------|
| `unitree_robot_control_suite.py` | Main GTK3 application |
| `go2w_camera_viewer.py` | Standalone camera viewer |
| `connect_inspire_hand.sh` | Inspire Hand connection helper |
| `install.sh` | Automated SDK + dependency installer |
| `scripts/verify_installation.sh` | Post-install path checks |
| `inspire_hand/` | Inspire Hand Python module |
| `docs/INSTALL.md` | Step-by-step manual installation |

---

## Usage

```bash
# Main GUI
python3 unitree_robot_control_suite.py

# Camera only
python3 go2w_camera_viewer.py enp3s0

# Inspire Hand CLI
python3 -m inspire_hand.cli interactive
```

SLAM maps save to `/home/unitree/` on the robot as `.pcd` files. See [docs/INSTALL.md](docs/INSTALL.md) for SLAM workflow and troubleshooting.

---

## Security

Local desktop control for robots on your LAN. Default robot SSH credentials are for lab use — change them on production deployments. Never commit API keys or custom network configs.

See [SECURITY.md](SECURITY.md) for data handling and reporting.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Sentdex/inspire_hands](https://github.com/Sentdex/inspire_hands) — Inspire Hand Python library
- [Unitree Robotics](https://www.unitree.com/) — SDK and robot platforms
- [ROS 2](https://www.ros.org/) — robotics middleware

---

## 📞 Support

For support and questions:

- Create an issue on [GitHub](https://github.com/Airuxn/unitree-robot-control-suite/issues)
- Install & troubleshooting: [docs/INSTALL.md](docs/INSTALL.md)
- Security: see [SECURITY.md](SECURITY.md)

---

**⭐ If this project helped you, please give it a star!**
