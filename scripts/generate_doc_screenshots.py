#!/usr/bin/env python3
"""Generate doc screenshots matching GTK menu labels and theme (headless fallback)."""
from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(APP_DIR, "docs", "images")

BG = (23, 28, 33)
TITLE_CYAN = (0, 191, 255)
ACCENT = (0, 255, 208)
BTN_TOP = (0, 255, 208)
BTN_BOTTOM = (0, 191, 255)
BTN_TEXT = (23, 28, 33)
MUTED = (170, 170, 170)
DIM = (136, 136, 136)
RED = (255, 85, 85)
GREEN = (0, 255, 0)
FRAME = (60, 70, 80)


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def gradient_button(draw: ImageDraw.ImageDraw, xy, text: str, fnt):
    x0, y0, x1, y1 = xy
    for y in range(y0, y1):
        t = (y - y0) / max(y1 - y0 - 1, 1)
        r = int(BTN_TOP[0] + (BTN_BOTTOM[0] - BTN_TOP[0]) * t)
        g = int(BTN_TOP[1] + (BTN_BOTTOM[1] - BTN_TOP[1]) * t)
        b = int(BTN_TOP[2] + (BTN_BOTTOM[2] - BTN_TOP[2]) * t)
        draw.line([(x0, y), (x1, y)], fill=(r, g, b))
    draw.rounded_rectangle(xy, radius=12, outline=(0, 140, 180), width=1)
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = x0 + (x1 - x0 - tw) // 2
    ty = y0 + (y1 - y0 - th) // 2 - 2
    draw.text((tx, ty), text, fill=BTN_TEXT, font=fnt)


def new_canvas(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (w, h), BG)
    return img, ImageDraw.Draw(img)


def save(img: Image.Image, name: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    img.save(path, "PNG")
    print(f"Wrote {path}")


def render_main_menu() -> None:
    img, draw = new_canvas(480, 420)
    title_f = font(22, True)
    sub_f = font(13)
    btn_f = font(16, True)
    draw.text((240, 48), "Unitree Robot Control Suite", fill=TITLE_CYAN, font=title_f, anchor="mm")
    draw.text((240, 78), "by Michael", fill=MUTED, font=sub_f, anchor="mm")
    y = 130
    for label in (
        "Connect to Unitree G1 (Ethernet)",
        "Connect to GO2W-U5 (Ethernet)",
        "Connect to Inspire Hands (USB)",
    ):
        gradient_button(draw, (40, y, 440, y + 48), label, btn_f)
        y += 58
    save(img, "main-menu.png")


def render_g1_menu() -> None:
    img, draw = new_canvas(480, 560)
    title_f = font(20, True)
    btn_f = font(14, True)
    status_f = font(15, True)
    gradient_button(draw, (40, 24, 440, 64), "Check/Setup Network Connection", btn_f)
    draw.text((240, 88), "Not connected to Unitree G1", fill=RED, font=status_f, anchor="mm")
    draw.text((240, 118), "Unitree G1 Menu", fill=ACCENT, font=title_f, anchor="mm")
    y = 150
    for label in (
        "Connect to EDU",
        "ROS 2 Terminal",
        "G1 Autonomous Navigation",
        "G1 SLAM & Navigation",
        "MuJoCo Simulation",
        "C++ SDK Examples",
        "Python SDK Examples",
        "Return",
    ):
        gradient_button(draw, (40, y, 440, y + 40), label, btn_f)
        y += 46
    save(img, "g1-menu.png")


def render_go2w_menu() -> None:
    img, draw = new_canvas(480, 620)
    title_f = font(20, True)
    btn_f = font(14, True)
    status_f = font(14, True)
    small_f = font(12)
    draw.rounded_rectangle((32, 20, 448, 150), radius=8, outline=FRAME, width=2)
    draw.text((240, 34), "Connection Method", fill=MUTED, font=small_f, anchor="mm")
    draw.text((52, 58), "● Ethernet (192.168.123.18)", fill=GREEN, font=small_f)
    draw.text((52, 82), "○ WiFi", fill=MUTED, font=small_f)
    draw.text((52, 110), "WiFi IP: Not set", fill=RED, font=small_f)
    gradient_button(draw, (40, 162, 440, 202), "Check/Setup Network Connection", btn_f)
    draw.text((240, 226), "Not connected to Unitree GO2W-U5 (192.168.123.18)", fill=RED, font=status_f, anchor="mm")
    draw.text((240, 256), "Unitree GO2W-U5 Menu", fill=ACCENT, font=title_f, anchor="mm")
    y = 288
    for label in (
        "Connect to EDU",
        "ROS 2 Terminal",
        "Streaming",
        "Hesai XT16 Mapping + SLAM",
        "MuJoCo Simulation",
        "C++ SDK Examples",
        "Python SDK Examples",
        "Return",
    ):
        gradient_button(draw, (40, y, 440, y + 40), label, btn_f)
        y += 46
    save(img, "go2w-menu.png")


def render_g1_slam_menu() -> None:
    img, draw = new_canvas(520, 680)
    title_f = font(20, True)
    section_f = font(16, True)
    btn_f = font(13, True)
    small_f = font(11)
    draw.text((260, 36), "🗺️ G1 SLAM & Navigation", fill=ACCENT, font=title_f, anchor="mm")
    draw.text((260, 62), "Complete SLAM workflow for G1 autonomous navigation", fill=DIM, font=small_f, anchor="mm")
    draw.text((40, 92), "📡 SLAM Mapping", fill=TITLE_CYAN, font=section_f)
    gradient_button(draw, (40, 110, 250, 155), "▶ Start Mapping", btn_f)
    gradient_button(draw, (270, 110, 480, 155), "⏹ Stop Mapping", btn_f)
    gradient_button(draw, (40, 165, 480, 210), "💾 Save Map", btn_f)
    gradient_button(draw, (40, 230, 480, 275), "🎮 Run keyDemo on Robot", btn_f)
    draw.text((40, 300), "📍 Relocation", fill=TITLE_CYAN, font=section_f)
    gradient_button(draw, (40, 318, 480, 368), "Start Relocation", btn_f)
    draw.text((40, 392), "🚀 Visualization Tools", fill=TITLE_CYAN, font=section_f)
    gradient_button(draw, (40, 410, 250, 455), "📊 Visualize Mapping", btn_f)
    gradient_button(draw, (270, 410, 480, 455), "📍 Visualize Relocation", btn_f)
    gradient_button(draw, (40, 465, 480, 510), "🔍 Visualize Lidar Stream", btn_f)
    gradient_button(draw, (40, 540, 480, 585), "Return", btn_f)
    save(img, "g1-slam-menu.png")


def main() -> int:
    render_main_menu()
    render_g1_menu()
    render_go2w_menu()
    render_g1_slam_menu()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
