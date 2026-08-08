"""Minimal tests for unitree_robot_control_suite.py.

These tests import the main module with heavy GUI/ROS dependencies mocked,
so they can run in CI without a display or robot hardware.
"""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Mock heavy GUI / ROS dependencies before importing the module.
mock_gi = MagicMock()
mock_gi.require_version = MagicMock()
sys.modules["gi"] = mock_gi
sys.modules["gi.repository"] = MagicMock()
sys.modules["gi.repository.Gtk"] = MagicMock()
sys.modules["gi.repository.Gdk"] = MagicMock()
sys.modules["gi.repository.GLib"] = MagicMock()
sys.modules["netifaces"] = MagicMock()

_spec = importlib.util.spec_from_file_location(
    "unitree_robot_control_suite",
    Path(__file__).parent.parent / "unitree_robot_control_suite.py",
)
unitree_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unitree_mod)


class TestConstants(unittest.TestCase):
    def test_default_ethernet_ip(self):
        self.assertEqual(unitree_mod.ETHERNET_IP, "192.168.123.18")

    def test_config_file_path(self):
        self.assertTrue(unitree_mod.CONFIG_FILE.endswith(".unitree_go2w_config.json"))

    def test_apply_css_exists(self):
        self.assertTrue(callable(unitree_mod.apply_css))


class TestConfigHelpers(unittest.TestCase):
    def test_load_and_save_config_roundtrip(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            f.write(json.dumps({"interface": "eth0"}))
            path = f.name

        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            loaded = unitree_mod.load_go2w_config()
            self.assertEqual(loaded["interface"], "eth0")
            self.assertEqual(loaded["connection_method"], "ethernet")
            unitree_mod.save_go2w_config({"interface": "wlan0", "connection_method": "wifi", "wifi_ip": "192.168.1.100"})
            reloaded = unitree_mod.load_go2w_config()
            self.assertEqual(reloaded["interface"], "wlan0")
            self.assertEqual(reloaded["connection_method"], "wifi")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)


class TestGo2WRobotIP(unittest.TestCase):
    def test_ethernet_returns_default_ip(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "ethernet"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            self.assertEqual(unitree_mod.get_go2w_robot_ip(), unitree_mod.ETHERNET_IP)
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_with_ip_returns_wifi_ip(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi", "wifi_ip": "192.168.1.50"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            self.assertEqual(unitree_mod.get_go2w_robot_ip(), "192.168.1.50")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_without_ip_falls_back_to_ethernet(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            self.assertEqual(unitree_mod.get_go2w_robot_ip(), unitree_mod.ETHERNET_IP)
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)


class TestGo2WNetworkInterface(unittest.TestCase):
    def _make_pinging_subprocess(self, reachable_iface):
        fake = MagicMock()

        def run(cmd, **kwargs):
            result = MagicMock()
            result.returncode = 0 if reachable_iface and cmd[2] == reachable_iface else 1
            return result

        fake.run = MagicMock(side_effect=run)
        return fake

    def test_wifi_finds_reachable_interface(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi", "wifi_ip": "192.168.1.50"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "wlan0", "eth0"]
            fake_subprocess = self._make_pinging_subprocess("wlan0")

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "wlan0")
                    fake_subprocess.run.assert_called()
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_falls_back_to_wlan_named_interface(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi", "wifi_ip": "192.168.1.50"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "wlp2s0", "eth0"]
            fake_subprocess = self._make_pinging_subprocess(None)

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "wlp2s0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_falls_back_to_wlan0(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi", "wifi_ip": "192.168.1.50"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "docker0", "eth0"]
            fake_subprocess = self._make_pinging_subprocess(None)

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "wlan0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_without_ip_falls_back_to_wlan_named_interface(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "wlp2s0", "eth0"]
            fake_subprocess = self._make_pinging_subprocess(None)

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "wlp2s0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_ethernet_finds_reachable_interface(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "ethernet"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "enp3s0", "wlan0"]
            fake_subprocess = self._make_pinging_subprocess("enp3s0")

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "enp3s0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_ethernet_falls_back_to_eth_named_interface(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "ethernet"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "eth0", "wlan0"]
            fake_subprocess = self._make_pinging_subprocess(None)

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "eth0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_ethernet_falls_back_to_eth0(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "ethernet"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "docker0", "wlan0"]
            fake_subprocess = self._make_pinging_subprocess(None)

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "eth0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_wifi_handles_ping_exception(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "wifi", "wifi_ip": "192.168.1.50"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "wlan0"]
            fake_subprocess = MagicMock()
            fake_subprocess.run.side_effect = OSError("ping failed")

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "wlan0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_ethernet_handles_ping_exception(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"connection_method": "ethernet"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path

            fake_netifaces = MagicMock()
            fake_netifaces.interfaces.return_value = ["lo", "enp3s0"]
            fake_subprocess = MagicMock()
            fake_subprocess.run.side_effect = OSError("ping failed")

            with unittest.mock.patch.object(unitree_mod, "netifaces", fake_netifaces):
                with unittest.mock.patch.object(unitree_mod, "subprocess", fake_subprocess):
                    self.assertEqual(unitree_mod.get_go2w_network_interface(), "enp3s0")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)


class TestConfigEdgeCases(unittest.TestCase):
    def test_save_config_error_is_swallowed(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            os.chmod(path, 0o444)
            # Should not raise even though writing is not allowed.
            unitree_mod.save_go2w_config({"interface": "eth0"})
            self.assertEqual(os.path.getsize(path), 0)
        finally:
            unitree_mod.CONFIG_FILE = original
            os.chmod(path, 0o644)
            os.remove(path)

    def test_load_missing_file_returns_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "missing.json")
            original = unitree_mod.CONFIG_FILE
            try:
                unitree_mod.CONFIG_FILE = missing
                config = unitree_mod.load_go2w_config()
                self.assertEqual(config["connection_method"], "ethernet")
                self.assertEqual(config["wifi_ip"], "")
            finally:
                unitree_mod.CONFIG_FILE = original

    def test_load_invalid_json_returns_default(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            f.write("not json")
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            config = unitree_mod.load_go2w_config()
            self.assertEqual(config["connection_method"], "ethernet")
            self.assertEqual(config["wifi_ip"], "")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)

    def test_load_partial_config_merges_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as f:
            json.dump({"wifi_ip": "10.0.0.5"}, f)
            path = f.name
        try:
            original = unitree_mod.CONFIG_FILE
            unitree_mod.CONFIG_FILE = path
            config = unitree_mod.load_go2w_config()
            self.assertEqual(config["connection_method"], "ethernet")
            self.assertEqual(config["wifi_ip"], "10.0.0.5")
        finally:
            unitree_mod.CONFIG_FILE = original
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
