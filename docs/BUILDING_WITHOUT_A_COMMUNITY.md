# Building a Unitree G1 control suite when nothing existed yet

When the **Unitree G1** shipped, early adopters did not get a turnkey desktop app, a Belgian user group, or Stack Overflow threads. This repo is the control suite **Michael VH built from scratch** for lab use: one GTK3 entry point for **G1** and **GO2W-U5**, network bring-up, SDK2/ROS2 terminals, MuJoCo simulation, SLAM workflows, camera streaming, and Inspire Hand control — integrated before Unitree’s ecosystem had caught up.

> **Context:** Among the first G1 units in Belgium. No community, no vendor hand-holding — reverse-engineering from SDK fragments, trial and error on real hardware, and encoding what worked into repeatable menus and install scripts.

---

## The problem

Early G1 ownership looked like this:

| What you had | What you did *not* have |
|--------------|-------------------------|
| Official SDK2 repos (C++, Python, ROS2) | A single “open app and drive robot” product |
| Example binaries scattered by platform | Documented end-to-end lab workflow |
| Ethernet to `192.168.123.164` (G1) | Reliable “which interface / which IP” tooling |
| Separate GO2W stack and IPs | Unified desktop for two robot families |

Every session started the same way: **find the right network interface**, **source the right ROS/DDS environment**, **remember which example binary maps to which task**, **don't launch low-level joint control on an unstable surface**.

The suite exists so that work happens **once**, in code, instead of every lab day in bash history.

---

## Design: one launcher, two robot worlds

```
                    ┌─────────────────────────┐
                    │       MainMenu          │
                    │  G1 · GO2W · Inspire    │
                    └───────────┬─────────────┘
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │ G1MenuWindow │  │GO2WMenuWindow│  │ inspire_hand │
      │  .164 ping   │  │ eth / WiFi   │  │  USB serial  │
      └──────┬───────┘  └──────┬───────┘  └──────────────┘
             │                 │
    ROS2 · MuJoCo · SLAM   Streams · XT16 SLAM
    SDK C++/Python         SDK via SSH on robot
    Autonomous nav         MuJoCo · examples
```

**MainMenu** (`unitree_robot_control_suite.py`) is deliberately small: three buttons, dark theme, no robot logic yet.

**G1MenuWindow** and **GO2WMenuWindow** are separate trees because the platforms are not interchangeable:

- **G1** default robot IP: `192.168.123.164`, Ethernet-first network setup, SLAM via `G1SlamMenu`, autonomous navigation with optional API key storage in `~/.unitree_g1_api_key`.
- **GO2W-U5** default Ethernet IP: `192.168.123.18`, optional WiFi IP in `~/.unitree_go2w_config.json`, Hesai XT16 mapping via `GO2WXT16SlamMenu`, high-level sport clients often executed **on the robot over SSH** with explicit `DDS_DOMAIN` / `DDS_INTERFACE` flags.

That split is intentional: sharing one menu would hide foot-guns (wrong IP, wrong DDS interface, wrong example class).

---

## Network layer: the unglamorous core

Most “robot doesn’t connect” issues are networking, not SDK bugs. The suite treats connectivity as a **first-class wizard**, not an README step.

### G1

- Background **status thread** pings `192.168.123.164` every second; label flips green/red live.
- **Check/Setup Network Connection** scans interfaces with `ping -I <iface>`, skips WiFi interfaces for the initial Ethernet path, and can run a bundled shell script to configure static addressing when nothing responds.
- Selected interface is stored (`self.selected_iface`) for later SDK launches that need `DDS_INTERFACE=enp3s0` (or whatever the lab PC uses).

### GO2W

- Persists **Ethernet vs WiFi** in JSON config.
- **`get_go2w_network_interface()`** probes which local interface can reach the robot IP (ping per iface; WiFi name heuristics for `wl*` / `wlan*`).
- SDK examples that run on the robot build temp shell scripts with `ssh unitree@<ip> '… DDS_INTERFACE=eth0 …'` so DDS matches the robot-side network stack.

This is the kind of code you only write after watching `test_publisher` work on a laptop but not on the robot — because nobody told you the interface name on either side.

---

## When to use SDK2 directly vs ROS2

The menus mirror how Unitree split their own stack:

| Task | Path in the suite |
|------|-------------------|
| Low/high-level motion examples | C++ or Python SDK2 binaries (`SDKExamplesMenu`, `GO2WSDKExamplesMenu`) |
| Camera stream | `go2w_camera_viewer.py` — SDK2 `VideoClient` + OpenCV |
| ROS2 introspection | Pre-sourced `gnome-terminal` with Humble + CycloneDDS workspace |
| RViz / image topics | Wrapped `ros2 run rqt_image_view … /camera/image_raw` |
| MuJoCo sim | `./unitree_mujoco -r g1 …scene_29dof_with_hand.xml` in dedicated terminal |
| SLAM map / relocate | `G1SlamMenu` + bundled `.rviz` configs; PCD maps on robot under `/home/unitree/` |

The suite does not reimplement Unitree’s drivers. It **orchestrates** them with guard rails: confirmation dialogs before low-level GO2W stand examples, connection checks before autonomous hardware mode, separate simulation vs hardware launch paths.

---

## SLAM and lidar workflows

### G1 — `G1SlamMenu`

End-to-end buttons for mapping lifecycle:

- Start / stop mapping, save map
- Relocation against saved maps
- RViz presets: `g1_slam_mapping.rviz`, `g1_slam_relocation.rviz`, `g1_lidar.rviz`
- Optional **keyDemo on robot** for interactive SLAM from the robot terminal

### GO2W — Hesai XT16

`GO2WXT16SlamMenu` and configs `hesai_xt16_mapping.rviz`, `hesai_xt16_relocation.rviz` cover the GO2W + XT16 lidar path separately from G1 SLAM — different hardware, same “operator should not memorize ros2 launch strings” philosophy.

---

## Fixed SDK paths: reproducibility over portability

`install.sh` and the GUI assume **canonical paths** under `$HOME`:

| Component | Path |
|-----------|------|
| Unitree SDK2 (C++) | `~/unitree_sdk2/` |
| Unitree SDK2 Python | `~/unitree_sdk2_python/` |
| Unitree ROS2 | `~/unitree_ros2/` |
| CycloneDDS workspace | `~/unitree_ros2/cyclonedds_ws/` |
| MuJoCo sim | `~/unitree_mujoco/simulate/build` |

That looks rigid on GitHub. In an early-G1 lab it was the **only way** to stop every script from breaking when someone cloned SDKs to a different folder. `scripts/verify_installation.sh` exists to fail fast when a path is missing.

The 30–60 minute `install.sh` is part of the product: when vendor docs were fragmented, **one script** that installs ROS2 Humble, SDK2, CycloneDDS, Python deps, and Inspire Hand module was the onboarding doc.

---

## Inspire Hand as a parallel subsystem

Inspire Hands are not on the robot DDS bus. **Connect to Inspire Hands (USB)** launches `connect_inspire_hand.sh` → `inspire_hand/` Python module (based on [Sentdex/inspire_hands](https://github.com/Sentdex/inspire_hands)) over CH340 serial.

Keeping hands on a separate button avoids coupling hand failures to robot motion sessions.

---

## What this repo proves

Not “I copied Unitree examples” — but:

1. **Integration under uncertainty** when vendor UX and community support lag hardware.
2. **Safety-minded orchestration** (confirmations, connection gates, sim vs hardware).
3. **Dual-platform thinking** (G1 humanoid vs GO2W wheeled) without pretending one size fits all.
4. **Operational reproducibility** (install script, path verification, persisted network config).

For reviewers who cannot access a G1: the screenshots below match the **production GTK3 menus** (labels, layout, and theme from `unitree_robot_control_suite.py`). They are headless UI renders — replace or supplement with lab photos of the robot when you have them.

Regenerate: `python3 scripts/generate_doc_screenshots.py` (or `scripts/capture_screenshots.py` on a machine where GTK window capture works).

---

## Screenshots

### Main entry — G1, GO2W, Inspire Hand

![Main menu](../images/main-menu.png)

### G1 launcher — network check, SDK, SLAM, MuJoCo

![G1 menu](../images/g1-menu.png)

### GO2W launcher — Ethernet/WiFi config and XT16 SLAM entry

![GO2W menu](../images/go2w-menu.png)

### G1 SLAM & navigation workflow

![G1 SLAM menu](../images/g1-slam-menu.png)

> **Add your own lab photos:** robot beside the laptop, RViz mapping, or hardware in the loop — drop them in `docs/images/` and link from your README for maximum credibility.

---

## Related files

| File | Role |
|------|------|
| `unitree_robot_control_suite.py` | Main GTK3 application (~3200 lines) |
| `go2w_camera_viewer.py` | SDK2 camera stream viewer |
| `install.sh` | Full lab stack installer |
| `scripts/verify_installation.sh` | Path / dependency verification |
| `scripts/capture_screenshots.py` | Regenerate doc screenshots from GTK |
| `docs/INSTALL.md` | Manual install when `install.sh` is not enough |
| `*.rviz` | SLAM / lidar visualization presets |

See [INSTALL.md](INSTALL.md) for hardware requirements and step-by-step setup.
