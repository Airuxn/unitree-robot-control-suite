#!/usr/bin/env python3
"""Capture GTK menu screenshots for docs (no robot required)."""
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk

import unitree_robot_control_suite as app


class FakeParent:
    def show_all(self):
        pass

    def hide(self):
        pass


def screenshot_widget(widget, path: str) -> None:
    widget.show_all()
    widget.realize()
    for _ in range(50):
        Gtk.main_iteration()
    GLib.usleep(200000)
    window = widget.get_window()
    if window is None:
        raise RuntimeError(f"No Gdk window for {path}")
    width = max(widget.get_allocated_width(), 400)
    height = max(widget.get_allocated_height(), 300)
    pixbuf = Gdk.pixbuf_get_from_window(window, 0, 0, width, height)
    if pixbuf is None:
        raise RuntimeError(f"Failed to grab pixels for {path}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        pixbuf.save_to_callback(fh.write, "png")


def main() -> int:
    app.apply_css()
    out_dir = os.path.join(APP_DIR, "docs", "images")
    parent = FakeParent()

    targets = [
        ("main-menu.png", lambda: app.MainMenu()),
        ("g1-menu.png", lambda: app.G1MenuWindow(parent)),
        ("go2w-menu.png", lambda: app.GO2WMenuWindow(parent)),
        ("g1-slam-menu.png", lambda: app.G1SlamMenu(parent)),
    ]

    for filename, factory in targets:
        widget = factory()
        path = os.path.join(out_dir, filename)
        try:
            screenshot_widget(widget, path)
            print(f"Wrote {path}")
        finally:
            widget.destroy()
            for _ in range(10):
                Gtk.main_iteration()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
