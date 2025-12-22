# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security issue, please **do not** open a public GitHub issue.

Contact the maintainer privately via GitHub Security Advisories or direct message.

## Security Model

This is a **local desktop application** for controlling Unitree robots on your LAN.

- Gemini API keys are stored locally in `~/.unitree_g1_api_key` (never commit this file).
- GO2W WiFi settings are stored in `~/.unitree_go2w_config.json`.
- Default robot IPs (`192.168.123.x`) are Unitree factory defaults, not secrets.
- SSH access uses the default `unitree` user on the robot — change robot credentials in production.

## Before Sharing or Deploying

1. Never commit API keys, robot passwords, or custom network configs.
2. Keep `.unitree_g1_api_key` and `.unitree_go2w_config.json` on your machine only.
3. Run `scripts/install-desktop.sh` after cloning to generate a local desktop launcher.
