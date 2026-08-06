# Contributing to Unitree Robot Control Suite

Thanks for your interest in this project.

## Before you start

- Read [README.md](README.md) and [docs/INSTALL.md](docs/INSTALL.md).
- Hardware testing requires a **Unitree G1 or GO2W** — note robot model in PRs when relevant.
- Search [existing issues](https://github.com/Airuxn/unitree-robot-control-suite/issues) first.
- Security: [SECURITY.md](SECURITY.md) — no public exploit reports.

## Development setup

**Requirements:** Ubuntu 20.04/22.04, Python 3.10+, ROS2 Humble, Unitree SDK2 at fixed paths (see README).

```bash
git clone https://github.com/Airuxn/unitree-robot-control-suite.git
cd unitree-robot-control-suite
./install.sh   # or follow docs/INSTALL.md
./scripts/verify_installation.sh
python3 -m py_compile unitree_robot_control_suite.py go2w_camera_viewer.py
```

## Pull requests

1. Fork and branch from `main`.
2. Keep GTK3 UI changes focused; test on target Ubuntu version when possible.
3. If you change expected SDK paths, update `install.sh`, `verify_installation.sh`, and docs together.
4. Run CI checks locally before opening.

## Commit messages

```
Fix camera viewer interface selection for wlan0
Document CycloneDDS path in INSTALL.md
```

## License

By contributing, you agree your contributions are licensed under the [MIT License](LICENSE).
