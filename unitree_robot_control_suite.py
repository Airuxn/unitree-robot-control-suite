import gi
import subprocess
import os
import threading
import time
import netifaces
import tempfile
import json
# GTK3
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

# Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
MUJOCO_BUILD_DIR = os.path.expanduser('~/unitree_mujoco/simulate/build')
DESKTOP = os.path.expanduser('~/Desktop')
SDK_ARM_DEMO = 'cd ~/unitree_sdk2_python/example/g1/high_level && DDS_DOMAIN=0 DDS_INTERFACE=enp3s0 DDS_PARTICIPANT_INDEX=0 python3 g1_arm7_sdk_dds_example.py; exec bash'
CAMERA_VIEW = 'source /opt/ros/humble/setup.bash; source ~/unitree_ros2/cyclonedds_ws/install/setup.bash; source ~/unitree_ros2/setup.sh; ros2 run rqt_image_view rqt_image_view /camera/image_raw; exec bash'
INSPIRE_HAND_CMD = ["gnome-terminal", "--", os.path.join(os.path.dirname(__file__), "connect_inspire_hand.sh")]

# CSS for modern look
CSS = b'''
window {
    background: #171C21;
}
button {
    font-size: 18px;
    font-weight: bold;
    border-radius: 12px;
    background: linear-gradient(90deg, #00FFD0 0%, #00BFFF 100%);
    color: #171C21;
    margin: 8px 0;
}
button.suggested-action {
    background: linear-gradient(90deg, #00FFD0 0%, #00BFFF 100%);
    color: #171C21;
}
button.destructive-action {
    background: linear-gradient(90deg, #00BFFF 0%, #00FFD0 100%);
    color: #171C21;
}
button:disabled, button:insensitive {
    background: #888888;
    color: #444444;
}
'''

def apply_css():
    style_provider = Gtk.CssProvider()
    style_provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

# Configuration management for GO2W connection settings
CONFIG_FILE = os.path.expanduser("~/.unitree_go2w_config.json")
ETHERNET_IP = "192.168.123.18"

def load_go2w_config():
    """Load GO2W connection configuration from file"""
    default_config = {
        "connection_method": "ethernet",  # "ethernet" or "wifi"
        "wifi_ip": ""
    }
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Ensure all keys exist
                for key in default_config:
                    if key not in config:
                        config[key] = default_config[key]
                return config
    except Exception as e:
        print(f"Error loading config: {e}")
    return default_config

def save_go2w_config(config):
    """Save GO2W connection configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")

def get_go2w_robot_ip():
    """Get the current robot IP based on connection method"""
    config = load_go2w_config()
    if config["connection_method"] == "wifi" and config["wifi_ip"]:
        return config["wifi_ip"]
    return ETHERNET_IP

def get_go2w_network_interface():
    """Get the appropriate network interface for GO2W connection"""
    config = load_go2w_config()
    
    if config["connection_method"] == "wifi":
        wifi_ip = config.get("wifi_ip", "")
        if wifi_ip:
            # Try to find the interface that can reach the WiFi IP
            for iface in netifaces.interfaces():
                if iface.startswith(('lo', 'docker', 'br-')):
                    continue
                try:
                    result = subprocess.run(["ping", "-I", iface, "-c", "1", "-W", "1", wifi_ip], 
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if result.returncode == 0:
                        return iface
                except:
                    continue
            # If ping doesn't work, find WiFi interface by name
            for iface in netifaces.interfaces():
                if iface.startswith(('wl', 'wlan')):
                    return iface
        # Fallback to first WiFi interface
        for iface in netifaces.interfaces():
            if iface.startswith(('wl', 'wlan')):
                return iface
        return "wlan0"
    else:
        # For Ethernet, find the interface that can reach the robot
        for iface in netifaces.interfaces():
            if iface.startswith(('lo', 'wl', 'wlan', 'docker', 'br-')):
                continue
            try:
                result = subprocess.run(["ping", "-I", iface, "-c", "1", "-W", "1", ETHERNET_IP], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return iface
            except:
                continue
        # Fallback to common Ethernet interface names
        for iface in netifaces.interfaces():
            if iface.startswith(('enp', 'eth')):
                return iface
        return "eth0"

class ProgressDialog(Gtk.Dialog):
    def __init__(self, parent, title, message):
        Gtk.Dialog.__init__(self, title, parent, 0, buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.set_default_size(400, 120)
        self.set_border_width(16)
        self.set_modal(True)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        box = self.get_content_area()
        self.label = Gtk.Label(label=message)
        self.progress = Gtk.ProgressBar()
        box.add(self.label)
        box.add(self.progress)
        self.show_all()
        self.connect("delete-event", self.on_delete_event)
    def set_fraction(self, frac):
        self.progress.set_fraction(frac)
    def set_text(self, text):
        self.label.set_text(text)
    def on_delete_event(self, widget, event):
        self.present()
        return True  # Prevent closing

class MainMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Unitree Robot Control Suite")
        self.set_border_width(24)
        self.set_default_size(400, 350)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        vbox.set_homogeneous(False)
        self.add(vbox)
        # Branding
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00BFFF">Unitree Robot Control Suite</span>')
        vbox.pack_start(title_label, False, False, 0)
        creator_label = Gtk.Label()
        creator_label.set_markup('<span size="medium" foreground="#AAAAAA">by Michael</span>')
        vbox.pack_start(creator_label, False, False, 0)
        vbox.pack_start(Gtk.Label(), True, True, 0)
        # Buttons
        btn1 = Gtk.Button(label="Connect to Unitree G1 (Ethernet)")
        btn1.get_style_context().add_class("suggested-action")
        btn1.set_size_request(0, 48)
        btn1.connect("clicked", self.on_connect_g1)
        vbox.pack_start(btn1, False, False, 0)
        btn2 = Gtk.Button(label="Connect to GO2W-U5 (Ethernet)")
        btn2.get_style_context().add_class("suggested-action")
        btn2.set_size_request(0, 48)
        btn2.connect("clicked", self.on_connect_go2w)
        vbox.pack_start(btn2, False, False, 0)
        btn3 = Gtk.Button(label="Connect to Inspire Hands (USB)")
        btn3.get_style_context().add_class("destructive-action")
        btn3.set_size_request(0, 48)
        btn3.connect("clicked", self.on_connect_inspire_hand)
        vbox.pack_start(btn3, False, False, 0)
        vbox.pack_start(Gtk.Label(), True, True, 0)
    def on_connect_g1(self, widget):
        self.hide()
        menu = G1MenuWindow(self)
        menu.show_all()
    def on_connect_go2w(self, widget):
        self.hide()
        menu = GO2WMenuWindow(self)
        menu.show_all()
    def on_connect_inspire_hand(self, widget):
        subprocess.Popen(INSPIRE_HAND_CMD)

class G1MenuWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Unitree G1 Launcher")
        self.set_border_width(24)
        self.set_default_size(400, 450)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.connected = False
        self.status_label = Gtk.Label()
        self.update_status_label()
        self.parent = parent
        self.network_check_in_progress = False
        self.api_key_file = os.path.expanduser('~/.unitree_g1_api_key')
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        # Add network check/setup button
        self.net_btn = Gtk.Button(label="Check/Setup Network Connection")
        self.net_btn.set_size_request(0, 40)
        self.net_btn.connect("clicked", self.on_check_network)
        vbox.pack_start(self.net_btn, False, False, 0)
        vbox.pack_start(self.status_label, False, False, 0)
        label = Gtk.Label()
        label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">Unitree G1 Menu</span>')
        vbox.pack_start(label, False, False, 0)
        # Create menu options
        self.menu_options = ["Connect to EDU",
            "ROS 2 Terminal",
            "G1 Autonomous Navigation",
            "G1 SLAM & Navigation",
            "MuJoCo Simulation",
            "C++ SDK Examples",
            "Python SDK Examples"
        ]
        for text in self.menu_options:
            btn = Gtk.Button(label=text)
            btn.set_size_request(0, 40)
            btn.connect("clicked", self.on_menu_option)
            vbox.pack_start(btn, False, False, 0)
        # Add Return button at the bottom
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
        # Start live status update
        self.keep_updating = True
        self.status_thread = threading.Thread(target=self.status_updater, daemon=True)
        self.status_thread.start()
        self.connect("destroy", self.on_destroy)
        
        # Load API key after initialization
        self.load_api_key()
    
    def load_api_key(self):
        """Load API key from file"""
        try:
            if os.path.exists(self.api_key_file):
                with open(self.api_key_file, 'r') as f:
                    api_key = f.read().strip()
                    if api_key:
                        os.environ['GEMINI_API_KEY'] = api_key
                        return True
        except Exception as e:
            print(f"Error loading API key: {e}")
        return False
    
    def save_api_key(self, api_key):
        """Save API key to file"""
        try:
            with open(self.api_key_file, 'w') as f:
                f.write(api_key)
            os.environ['GEMINI_API_KEY'] = api_key
            return True
        except Exception as e:
            print(f"Error saving API key: {e}")
            return False
    
    def update_api_status_label(self):
        """Update the API key status label"""
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            self.api_status_label.set_markup('<span size="small" foreground="#00FF00">🔑 API Key: Set</span>')
        else:
            self.api_status_label.set_markup('<span size="small" foreground="#FF5555">❌ No API Key Set</span>')
    
    def on_set_api_key(self, widget):
        """Handle Set API Key button click"""
        self.show_api_key_dialog("set_only")
    
    def on_reset_api_key(self, widget, parent_dialog=None):
        """Handle Reset API Key button click"""
        parent = parent_dialog if parent_dialog else self
        # Show confirmation dialog
        dialog = Gtk.MessageDialog(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Reset API Key?\n\nThis will remove the saved API key and you'll need to enter it again."
        )
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            # Remove the API key file and environment variable
            try:
                if os.path.exists(self.api_key_file):
                    os.remove(self.api_key_file)
                if 'GEMINI_API_KEY' in os.environ:
                    del os.environ['GEMINI_API_KEY']
                self.update_api_status_label()
            except Exception as e:
                print(f"Error resetting API key: {e}")
    
    def update_status_label(self):
        if self.connected:
            self.status_label.set_markup('<span size="large" weight="bold" foreground="#00FF00">Connected to Unitree G1</span>')
        else:
            self.status_label.set_markup('<span size="large" weight="bold" foreground="#FF5555">Not connected to Unitree G1</span>')
    def status_updater(self):
        while self.keep_updating:
            try:
                result = subprocess.run(["ping", "-c", "1", "-W", "1", "192.168.123.164"], stdout=subprocess.DEVNULL)
                connected = (result.returncode == 0)
            except Exception:
                connected = False
            if connected != self.connected:
                self.connected = connected
                GLib.idle_add(self.update_status_label)
            time.sleep(1)
    def on_destroy(self, *args):
        self.keep_updating = False
    def on_check_network(self, widget):
        if getattr(self, 'network_check_in_progress', False):
            return  # Prevent multiple checks
        self.network_check_in_progress = True
        self.net_btn.set_sensitive(False)
        progress = ProgressDialog(self, "Connecting to Unitree G1", "Checking connection...")
        cancel_requested = {'value': False}
        def on_cancel(*args):
            cancel_requested['value'] = True
            progress.destroy()
            self.network_check_in_progress = False
            self.net_btn.set_sensitive(True)
        progress.connect("delete-event", on_cancel)
        progress.connect("response", on_cancel)
        
        def network_thread():
            try:
                # First check if we're already connected
                GLib.idle_add(progress.set_text, "Checking current connection...")
                
                # Try to find an interface that can reach the robot
                for iface in netifaces.interfaces():
                    # Skip loopback and wireless interfaces
                    if iface.startswith(('lo', 'wl', 'wlan')):
                        continue
                    try:
                        result = subprocess.run(["ping", "-I", iface, "-c", "1", "-W", "1", "192.168.123.164"], 
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if result.returncode == 0:
                            # We found a working interface
                            self.connected = True
                            self.selected_iface = iface
                            GLib.idle_add(self.update_status_label)
                            GLib.idle_add(progress.set_text, f"✅ Already connected to Unitree G1 on {iface}!")
                            time.sleep(2)
                            GLib.idle_add(progress.destroy)
                            GLib.idle_add(lambda: setattr(self, 'network_check_in_progress', False))
                            GLib.idle_add(lambda: self.net_btn.set_sensitive(True))
                            return
                    except Exception:
                        continue
                
                # If we get here, we need to set up the network
                GLib.idle_add(progress.set_text, "Setting up network connection...")
                
                # Create a script to handle all network setup in one go
                with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                    tmp_script.write("""#!/bin/bash
set -e  # Exit on any error

# Function to check command success
check_success() {
    if [ $? -ne 0 ]; then
        echo "Failed: $1" >&2
        exit 1
    fi
    echo "Success: $1"
}

# Find the interface that can reach the robot
echo "Step 1: Finding suitable network interface..."
ROBOT_IFACE=""
for iface in $(ip -o link show | awk -F': ' '{print $2}'); do
    # Skip loopback and wireless interfaces
    if [[ $iface == lo* ]] || [[ $iface == wl* ]] || [[ $iface == wlan* ]]; then
        continue
    fi
    
    # Try to ping the robot through this interface
    if ping -I $iface -c 1 -W 1 192.168.123.164 > /dev/null 2>&1; then
        ROBOT_IFACE=$iface
        echo "Found working interface: $ROBOT_IFACE"
        break
    fi
done

# If no interface found, default to enp3s0
if [ -z "$ROBOT_IFACE" ]; then
    ROBOT_IFACE="enp3s0"
    echo "No working interface found, using default: $ROBOT_IFACE"
fi

# Save the interface for later use
echo $ROBOT_IFACE > /tmp/robot_interface

# Bring interface up
echo "Step 2: Bringing up interface $ROBOT_IFACE..."
ip link set $ROBOT_IFACE up
check_success "Interface brought up"

# Remove any existing IPs
echo "Step 3: Removing existing IP addresses..."
for ip in $(ip addr show $ROBOT_IFACE | grep -oP '192.168.123.\\d+'); do
    echo "Removing IP: $ip"
    ip addr del $ip/24 dev $ROBOT_IFACE 2>/dev/null
done

# Add our static IP
echo "Step 4: Setting static IP..."
ip addr add 192.168.123.99/24 dev $ROBOT_IFACE
check_success "Static IP set"

# Wait for network to stabilize
echo "Step 5: Waiting for network to stabilize..."
sleep 3

# Test connection to robot
echo "Step 6: Testing connection to robot..."
    if ! ping -I $ROBOT_IFACE -c 1 -W 2 192.168.123.164 > /dev/null 2>&1; then
        echo "Failed: Could not reach robot at 192.168.123.164" >&2
    exit 1
fi
echo "Success: Robot is reachable"

# All steps completed successfully
echo "Network setup completed successfully"
echo "1" > /tmp/network_setup_status
""")
                    script_path = tmp_script.name
                
                subprocess.run(["chmod", "+x", script_path])
                
                # Run the script and capture output in real-time
                proc = subprocess.Popen(["pkexec", "bash", script_path], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True,
                                      bufsize=1)
                
                # Read output in real-time
                last_step_time = time.time()
                while True:
                    output = proc.stdout.readline()
                    if output == '' and proc.poll() is not None:
                        break
                    if output:
                        # If this is a new step (starts with "Step"), wait to ensure previous step was visible
                        if output.strip().startswith("Step"):
                            # Calculate time since last step
                            time_since_last = time.time() - last_step_time
                            if time_since_last < 1.0:  # If less than 1 second has passed
                                time.sleep(1.0 - time_since_last)  # Wait the remaining time
                            last_step_time = time.time()
                        
                        GLib.idle_add(progress.set_text, output.strip())
                        # Force update the GUI
                        while Gtk.events_pending():
                            Gtk.main_iteration()
                
                # Get any remaining output
                stdout, stderr = proc.communicate()
                if stdout:
                    print(f"Network setup output: {stdout}")
                if stderr:
                    print(f"Network setup errors: {stderr}")
                
                # Ensure the last step is visible for at least 1 second
                time_since_last = time.time() - last_step_time
                if time_since_last < 1.0:
                    time.sleep(1.0 - time_since_last)
                
                # Check if network setup was successful
                try:
                    with open('/tmp/network_setup_status', 'r') as f:
                        setup_success = int(f.read().strip()) == 1
                    with open('/tmp/robot_interface', 'r') as f:
                        self.selected_iface = f.read().strip()
                except:
                    setup_success = False
                
                # Wait for network to stabilize before final check
                time.sleep(2)
                
                # Do a final connection check
                try:
                    result = subprocess.run(["ping", "-c", "1", "-W", "1", "192.168.123.164"], stdout=subprocess.DEVNULL)
                    if result.returncode == 0:
                        setup_success = True
                except Exception:
                    setup_success = False
                
                if setup_success:
                    self.connected = True
                    GLib.idle_add(self.update_status_label)
                    GLib.idle_add(progress.set_text, f"✅ Connected to Unitree G1 on {self.selected_iface}!")
                else:
                    # Try for up to 10 seconds to establish connection
                    connection_succeeded = False
                    for _ in range(10):
                        try:
                            result = subprocess.run(["ping", "-c", "1", "-W", "1", "192.168.123.164"], stdout=subprocess.DEVNULL)
                            if result.returncode == 0:
                                self.connected = True
                                GLib.idle_add(self.update_status_label)
                                GLib.idle_add(progress.set_text, f"✅ Connected to Unitree G1 on {self.selected_iface}!")
                                connection_succeeded = True
                                break
                        except Exception:
                            pass
                        time.sleep(1)
                    
                    if not connection_succeeded:
                        GLib.idle_add(progress.set_text, "❌ Failed to configure network settings.\nPlease check your network settings.")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Exception in network thread: {e}")
                GLib.idle_add(progress.set_text, f"❌ Error: {str(e)}")
                time.sleep(2)
            
            finally:
                try:
                    GLib.idle_add(progress.destroy)
                    GLib.idle_add(lambda: setattr(self, 'network_check_in_progress', False))
                    GLib.idle_add(lambda: self.net_btn.set_sensitive(True))
                except Exception as e:
                    print(f"Error in cleanup: {e}")
        
        threading.Thread(target=network_thread, daemon=True).start()
        progress.show_all()
        while progress.get_visible():
            while Gtk.events_pending():
                Gtk.main_iteration()

    def on_menu_option(self, widget):
        text = widget.get_label()
        if text == "Connect to EDU":
            self.connect_pc2(widget)
        elif text == "ROS 2 Terminal":
            self.ros2_terminal(widget)
        elif text == "C++ SDK Examples":
            self.show_sdk_examples(widget)
        elif text == "Python SDK Examples":
            self.show_python_examples(widget)
        elif text == "MuJoCo Simulation":
            self.launch_mujoco_simulation(widget)
        elif text == "G1 Autonomous Navigation":
            self.show_autonomous_dialog(widget)
        elif text == "G1 SLAM & Navigation":
            self.show_g1_slam_menu(widget)

    def show_g1_slam_menu(self, widget):
        """Show the G1 SLAM & Navigation menu"""
        slam_menu = G1SlamMenu(self)
        slam_menu.show_all()

    def show_sdk_examples(self, widget):
        """Show the SDK examples menu"""
        examples_menu = SDKExamplesMenu(self, "192.168.123.164")
        examples_menu.show_all()

    def show_python_examples(self, widget):
        """Show the Python SDK examples menu"""
        examples_menu = PythonExamplesMenu(self)
        examples_menu.show_all()
    
    def launch_mujoco_simulation(self, widget):
        """Launch MuJoCo simulation for G1"""
        command = f"cd {MUJOCO_BUILD_DIR} && ./unitree_mujoco -r g1 ../../unitree_robots/g1/scene_29dof_with_hand.xml"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=MuJoCo G1", 
                "--", 
                "bash", 
                "-c", 
                f"echo 'Running: {command}'; echo '=========================================='; {command}; echo Press Enter to close...; read"
            ])
        except Exception as e:
            print(f"Error launching MuJoCo: {e}")
    
    def show_autonomous_dialog(self, widget):
        """Show autonomous navigation mode selection dialog"""
        dialog = Gtk.Dialog("G1 Autonomous Navigation", self, 0)
        dialog.set_default_size(450, 400)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.set_border_width(20)
        
        # Get content area
        content_area = dialog.get_content_area()
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">G1 Autonomous Navigation</span>')
        content_area.pack_start(title_label, False, False, 10)
        
        # API Key Status Section
        api_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        api_section.set_margin_bottom(15)
        
        # API Status
        self.api_status_label = Gtk.Label()
        self.api_status_label.set_halign(Gtk.Align.CENTER)
        self.update_api_status_label()
        api_section.pack_start(self.api_status_label, False, False, 0)
        
        # API Management buttons
        api_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        api_btn_box.set_homogeneous(True)  # Make buttons equal width
        
        self.api_btn = Gtk.Button(label="Set API Key")
        self.api_btn.set_size_request(0, 35)
        self.api_btn.connect("clicked", lambda w: self.show_api_key_dialog("set_only", dialog))
        api_btn_box.pack_start(self.api_btn, True, True, 0)
        
        self.reset_api_btn = Gtk.Button(label="Reset")
        self.reset_api_btn.set_size_request(0, 35)
        self.reset_api_btn.connect("clicked", lambda w: self.on_reset_api_key(dialog))
        api_btn_box.pack_start(self.reset_api_btn, True, True, 0)
        
        api_section.pack_start(api_btn_box, False, False, 0)
        content_area.pack_start(api_section, False, False, 0)
        
        # Separator
        separator = Gtk.Separator()
        content_area.pack_start(separator, False, False, 10)
        
        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup('<span size="medium" foreground="#AAAAAA">Choose how to run the autonomous navigation system:</span>')
        desc_label.set_line_wrap(True)
        content_area.pack_start(desc_label, False, False, 10)
        
        # Add some spacing
        content_area.pack_start(Gtk.Label(), False, False, 10)
        
        # Simulation button
        sim_btn = Gtk.Button(label="🤖 Simulation Mode")
        sim_btn.set_size_request(0, 50)
        sim_btn.get_style_context().add_class("suggested-action")
        sim_btn.connect("clicked", lambda w: self.launch_autonomous_simulation(dialog))
        content_area.pack_start(sim_btn, False, False, 5)
        
        # Hardware button
        hw_btn = Gtk.Button(label="🔧 Hardware Mode (Real Robot)")
        hw_btn.set_size_request(0, 50)
        hw_btn.get_style_context().add_class("destructive-action")
        hw_btn.connect("clicked", lambda w: self.launch_autonomous_hardware(dialog))
        content_area.pack_start(hw_btn, False, False, 5)
        
        # Add some spacing
        content_area.pack_start(Gtk.Label(), False, False, 10)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup('<span size="small" foreground="#888888">• Simulation: Safe testing with camera feed\n• Hardware: Real robot control (requires connection)</span>')
        info_label.set_line_wrap(True)
        content_area.pack_start(info_label, False, False, 5)
        
        # Cancel button
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.set_size_request(0, 40)
        cancel_btn.connect("clicked", lambda w: dialog.destroy())
        content_area.pack_start(cancel_btn, False, False, 10)
        
        dialog.show_all()
    
    def launch_autonomous_simulation(self, dialog):
        """Launch autonomous navigation in simulation mode"""
        if dialog:
            dialog.destroy()
        
        # Check if API key is set
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            # Try to load from file
            if not self.load_api_key():
                # Show API key dialog
                self.show_api_key_dialog("simulation")
                return
            api_key = os.getenv('GEMINI_API_KEY')
        
        # Launch simulation
        command = "cd ~/unitree-g1-autonomous && export GEMINI_API_KEY=\"$GEMINI_API_KEY\" && python3 autonomous_mode.py --sim"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=G1 Autonomous - Simulation", 
                "--", 
                "bash", 
                "-c", 
                f"echo '🤖 G1 Autonomous Navigation - Simulation Mode'; echo '=========================================='; echo 'API Key: configured'; echo ''; {command}; echo ''; echo 'Press Enter to close...'; read"
            ])
        except Exception as e:
            print(f"Error launching autonomous simulation: {e}")
    
    def launch_autonomous_hardware(self, dialog):
        """Launch autonomous navigation on real hardware"""
        if dialog:
            dialog.destroy()
        
        # Check if connected to robot
        if not self.connected:
            error_dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="❌ Not connected to Unitree G1!\n\nPlease connect to the robot first using the 'Check/Setup Network Connection' button."
            )
            error_dialog.run()
            error_dialog.destroy()
            return
        
        # Check if API key is set
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            # Try to load from file
            if not self.load_api_key():
                # Show API key dialog
                self.show_api_key_dialog("hardware")
                return
            api_key = os.getenv('GEMINI_API_KEY')
        
        # Show warning dialog
        warning_dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="⚠️ WARNING: Hardware Mode\n\nThis will control the REAL robot!\n\nPlease ensure:\n• Robot is on a stable surface\n• No obstacles around the robot\n• You are ready to stop the robot if needed\n• Camera is working properly\n\nContinue?"
        )
        response = warning_dialog.run()
        warning_dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            # Launch hardware mode
            command = "cd ~/unitree-g1-autonomous && export GEMINI_API_KEY=\"$GEMINI_API_KEY\" && python3 autonomous_mode.py"
            try:
                subprocess.Popen([
                    "gnome-terminal", 
                    "--title=G1 Autonomous - Hardware", 
                    "--", 
                    "bash", 
                    "-c", 
                    f"echo '🔧 G1 Autonomous Navigation - Hardware Mode'; echo '=========================================='; echo 'API Key: configured'; echo 'Robot IP: 192.168.123.164'; echo ''; {command}; echo ''; echo 'Press Enter to close...'; read"
                ])
            except Exception as e:
                print(f"Error launching autonomous hardware: {e}")
    
    def show_api_key_dialog(self, mode, parent_dialog=None):
        """Show dialog to set API key"""
        parent = parent_dialog if parent_dialog else self
        dialog = Gtk.Dialog("Set Gemini API Key", parent, 0)
        dialog.set_default_size(400, 200)
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.set_modal(True)
        
        content_area = dialog.get_content_area()
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="large" weight="bold" foreground="#00FFD0">Gemini API Key Required</span>')
        content_area.pack_start(title_label, False, False, 10)
        
        # Description
        desc_label = Gtk.Label()
        desc_label.set_markup('<span size="medium">Enter your Google Gemini API key to enable AI vision:</span>')
        desc_label.set_line_wrap(True)
        content_area.pack_start(desc_label, False, False, 10)
        
        # API key entry
        entry = Gtk.Entry()
        entry.set_placeholder_text("AIzaSy...")
        entry.set_visibility(False)  # Hide the key
        entry.set_activates_default(True)  # Enter key activates default button
        content_area.pack_start(entry, False, False, 10)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        ok_btn = Gtk.Button(label="Launch")
        ok_btn.set_can_default(True)
        ok_btn.grab_default()  # Make this the default button
        ok_btn.connect("clicked", lambda w: self.set_api_key_and_launch(entry.get_text(), mode, dialog))
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda w: dialog.destroy())
        
        button_box.pack_start(ok_btn, True, True, 0)
        button_box.pack_start(cancel_btn, True, True, 0)
        content_area.pack_start(button_box, False, False, 10)
        
        # Focus on entry field
        entry.grab_focus()
        
        dialog.show_all()
    
    def set_api_key_and_launch(self, api_key, mode, dialog):
        """Set API key and launch autonomous mode"""
        if not api_key or not api_key.startswith('AIzaSy'):
            error_dialog = Gtk.MessageDialog(
                parent=dialog,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="❌ Invalid API Key!\n\nPlease enter a valid Google Gemini API key starting with 'AIzaSy'"
            )
            error_dialog.run()
            error_dialog.destroy()
            return
        
        # Save API key to file
        if not self.save_api_key(api_key):
            error_dialog = Gtk.MessageDialog(
                parent=dialog,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="❌ Error saving API key!\n\nPlease try again."
            )
            error_dialog.run()
            error_dialog.destroy()
            return
        
        # Update status label
        self.update_api_status_label()
        
        # If mode is "set_only", just close dialog
        if mode == "set_only":
            dialog.destroy()
            return
        
        # Show launching message
        launching_dialog = Gtk.MessageDialog(
            parent=dialog,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.NONE,
            text=f"🚀 Launching G1 Autonomous Navigation - {mode.title()} Mode...\n\nPlease wait..."
        )
        launching_dialog.set_modal(True)
        launching_dialog.show_all()
        
        # Close both dialogs and launch
        dialog.destroy()
        GLib.timeout_add(500, self._delayed_launch, mode, launching_dialog)
    
    def _delayed_launch(self, mode, launching_dialog):
        """Delayed launch to ensure dialog is closed"""
        # Close the launching dialog
        launching_dialog.destroy()
        
        # Launch the appropriate mode
        if mode == "simulation":
            self.launch_autonomous_simulation(None)
        else:
            self.launch_autonomous_hardware(None)
        return False  # Don't repeat
    
    def connect_pc2(self, widget):
        subprocess.Popen(["nautilus", "sftp://unitree@192.168.123.164/home/unitree"])
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", "ssh unitree@192.168.123.164; exec bash"])
    def ros2_terminal(self, widget):
        # Create a ROS2 launcher script with help menu
        ros2_script = '''#!/bin/bash
echo "=========================================="
echo "🤖 ROS2 Environment Launcher"
echo "=========================================="

# Detect ROS2 version
if [ -f /opt/ros/humble/setup.bash ]; then
    ROS_VERSION_NAME="Humble"
    source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/foxy/setup.bash ]; then
    ROS_VERSION_NAME="Foxy"
    source /opt/ros/foxy/setup.bash
else
    echo "❌ No ROS2 installation found!"
    exit 1
fi

# Source additional setup files if they exist
if [ -f ~/unitree_ros2/cyclonedds_ws/install/setup.bash ]; then
    source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
fi

if [ -f ~/unitree_ros2/setup.sh ]; then
    source ~/unitree_ros2/setup.sh
fi

echo "✅ ROS2 $ROS_VERSION_NAME sourced successfully"
echo "📍 Current directory: $(pwd)"
echo ""

# Show ROS2 help menu
echo "🚀 ROS2 COMMAND REFERENCE"
echo "=========================================="
echo ""
echo "📋 BASIC COMMANDS:"
echo "  ros2 --help                    # Show all ROS2 commands"
echo "  ros2 node list                 # List active nodes"
echo "  ros2 topic list                # List available topics"
echo "  ros2 service list              # List available services"
echo "  ros2 action list               # List available actions"
echo ""
echo "🔍 MONITORING:"
echo "  ros2 topic echo /topic_name    # Monitor a topic"
echo "  ros2 topic info /topic_name    # Get topic info"
echo "  ros2 node info /node_name      # Get node info"
echo "  ros2 service type /service_name # Get service type"
echo ""
echo "🏃 RUNNING NODES:"
echo "  ros2 run package_name node_name # Run a specific node"
echo "  ros2 launch package_name launch_file.launch.py # Launch a launch file"
echo ""
echo "📦 PACKAGE MANAGEMENT:"
echo "  ros2 pkg list                  # List all packages"
echo "  ros2 pkg list | grep unitree   # Find Unitree packages"
echo "  ros2 pkg executables package_name # List executables in package"
echo ""
echo "🔧 WORKSPACE:"
echo "  colcon build                   # Build workspace"
echo "  colcon build --packages-select package_name # Build specific package"
echo "  source install/setup.bash      # Source workspace"
echo ""
echo "🤖 UNITREE SPECIFIC:"
echo "  ros2 run unitree_go2_bringup go2_bringup_node # Run GO2 node"
echo "  ros2 run unitree_g1_bringup g1_bringup_node   # Run G1 node"
echo "  ros2 topic list | grep unitree # List Unitree topics"
echo ""
echo "❓ GET HELP:"
echo "  ros2 <command> --help          # Get help for specific command"
echo "  ros2 <command> -h              # Short help"
echo ""

# Show current ROS2 status
echo "📊 CURRENT ROS2 STATUS:"
echo "=========================================="
echo "ROS_DISTRO: $ROS_DISTRO"
echo "ROS_VERSION: $ROS_VERSION"
echo ""

# Show available topics
echo "📡 ACTIVE TOPICS:"
echo "=========================================="
ros2 topic list
echo ""

# Show available nodes
echo "🔗 ACTIVE NODES:"
echo "=========================================="
ros2 node list
echo ""

echo "💡 TIP: Type 'ros2 --help' for complete command reference"
echo "💡 TIP: Use 'ros2 <command> --help' for specific command help"
echo ""

# Keep terminal open
echo "=========================================="

# Start interactive bash with ROS2 environment
exec bash'''
        
        # Write script to temporary file
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
            tmp_script.write(ros2_script)
            script_path = tmp_script.name
        
        # Make executable and run
        subprocess.run(["chmod", "+x", script_path])
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    def exit_app(self, widget):
        Gtk.main_quit()
    def on_return(self, widget):
        self.keep_updating = False
        self.destroy()
        self.parent.show_all()

class SDKExamplesMenu(Gtk.Window):
    def __init__(self, parent, robot_ip="192.168.123.164"):
        Gtk.Window.__init__(self, title="Unitree SDK Examples")
        self.robot_ip = robot_ip
        self.set_border_width(24)
        self.set_default_size(400, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">C++ SDK Examples</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Example buttons
        examples = [
            ("Locomotion Client", self.run_locomotion),
            ("Audio Example", self.run_audio),
            ("Arm7 Example (Sport Mode)", self.run_arm7),
            ("Arm Action Example", self.run_arm_action),
            ("Hello World Example", self.run_hello_world),
            ("Wireless Controller", self.run_gamepad),
            ("State Machine", self.run_state_machine)
        ]
        
        for label, callback in examples:
            btn = Gtk.Button(label=label)
            btn.set_size_request(0, 40)
            btn.connect("clicked", callback)
            vbox.pack_start(btn, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
    
    def run_locomotion(self, widget):
        cmd = "cd ~/unitree_sdk2/build/bin && ./g1_loco_client --network_interface=enp3s0 --start"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_audio(self, widget):
        cmd = "cd ~/unitree_sdk2/build/bin && ./g1_audio_client_example enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_arm7(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
            "⚠️ WARNING: The Arm7 example will move the robot's arm.\n\nPlease ensure:\n1. There are no obstacles around the robot\n2. The robot is on a stable surface\n3. You are ready to stop the robot if needed\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            cmd = "cd ~/unitree_sdk2/build/bin && ./g1_arm7_sdk_dds_example enp3s0"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_arm_action(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
            "⚠️ WARNING: The Arm Action example will move the robot's arm.\n\nPlease ensure:\n1. There are no obstacles around the robot\n2. The robot is on a stable surface\n3. You are ready to stop the robot if needed\n\nThis example allows you to:\n- List available arm actions (enter 0)\n- Execute specific arm actions by ID\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            cmd = "cd ~/unitree_sdk2/build/bin && ./g1_arm_action_example enp3s0"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_hello_world(self, widget):
        # Create a dialog to choose which part to run
        dialog = Gtk.Dialog("Hello World Example", self, 0)
        dialog.set_default_size(300, 150)
        box = dialog.get_content_area()
        label = Gtk.Label(label="Choose which part to run:")
        box.add(label)
        
        # Add buttons for each part
        laptop_btn = Gtk.Button(label="Run on Laptop (Subscriber)")
        robot_btn = Gtk.Button(label="Run on Robot (Publisher)")
        
        def on_laptop(*args):
            cmd = "cd ~/unitree_sdk2/build/bin && ./test_subscriber"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
            dialog.destroy()
        
        def on_robot(*args):
            # Create a script that will handle the SSH session and process termination
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Function to handle cleanup
cleanup() {{
    echo "Cleaning up..."
    ssh unitree@{robot_ip} 'pkill -f test_publisher' 2>/dev/null || true
    exit 0
}}

# Set up trap to catch terminal close
trap cleanup EXIT

# Run the publisher on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_publisher'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_publisher'

# If we get here, the SSH session ended
# Cleanup happens automatically via trap
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
            dialog.destroy()
        
        laptop_btn.connect("clicked", on_laptop)
        robot_btn.connect("clicked", on_robot)
        
        box.add(laptop_btn)
        box.add(robot_btn)
        dialog.show_all()
    
    def run_gamepad(self, widget):
        cmd = "cd ~/unitree_sdk2/build/bin && ./advanced_gamepad enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_state_machine(self, widget):
        cmd = "cd ~/unitree_sdk2/build/bin && ./state_machine_example --param ../../example/state_machine/params -i enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()
    
    def exit_app(self, widget):
        Gtk.main_quit()

class PythonExamplesMenu(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Python SDK Examples")
        self.set_border_width(24)
        self.set_default_size(400, 400)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        # Add title
        label = Gtk.Label()
        label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">Python SDK Examples</span>')
        vbox.pack_start(label, False, False, 0)
        # Add buttons
        # Start Lease Server button removed
        btn2 = Gtk.Button(label="Wireless Controller")
        btn2.set_size_request(0, 40)
        btn2.connect("clicked", self.run_wireless_controller)
        vbox.pack_start(btn2, False, False, 0)
        btn3 = Gtk.Button(label="G1 Loco Client")
        btn3.set_size_request(0, 40)
        btn3.connect("clicked", self.run_g1_loco_client)
        vbox.pack_start(btn3, False, False, 0)
        btn4 = Gtk.Button(label="G1 Audio Client")
        btn4.set_size_request(0, 40)
        btn4.connect("clicked", self.run_g1_audio_client)
        vbox.pack_start(btn4, False, False, 0)
        # Add Return button at the bottom
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
        self.parent = parent
        self.connect("destroy", lambda *a: self.parent.show_all())

    
    def run_wireless_controller(self, widget):
        cmd = "cd ~/unitree_sdk2_python/example/wireless_controller && python3 wireless_controller.py enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_g1_loco_client(self, widget):
        cmd = "cd ~/unitree_sdk2_python/example/g1/high_level && python3 g1_loco_client_example.py enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_g1_audio_client(self, widget):
        cmd = "cd ~/unitree_sdk2_python/example/g1/audio && python3 g1_audio_client_example.py enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()

    def exit_app(self, widget):
        Gtk.main_quit()

class GO2WSDKExamplesMenu(Gtk.Window):
    def __init__(self, parent, robot_ip="192.168.123.18"):
        Gtk.Window.__init__(self, title="Unitree GO2W C++ SDK Examples")
        self.robot_ip = robot_ip
        self.set_border_width(24)
        self.set_default_size(400, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">GO2W C++ SDK Examples</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Example buttons
        examples = [
            ("GO2W Sport Client (High-Level)", self.run_go2w_sport_client),
            ("GO2W Stand Example (Low-Level)", self.run_go2w_stand_example),
            ("Hello World Example", self.run_hello_world_example)
        ]
        
        for label, callback in examples:
            btn = Gtk.Button(label=label)
            btn.set_size_request(0, 40)
            btn.connect("clicked", callback)
            vbox.pack_start(btn, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
    
    def run_go2w_sport_client(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL,
            "🤖 GO2W Sport Client\n\nThis example provides high-level control:\n• Damp mode\n• Stand up/Stand down\n• Movement control\n• Speed levels\n• Gait switching\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the sport client on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=eth0 DDS_PARTICIPANT_INDEX=0 ./go2w_sport_client eth0'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=eth0 DDS_PARTICIPANT_INDEX=0 ./go2w_sport_client eth0'

# If we get here, the SSH session ended
# Cleanup happens automatically via trap
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    
    def run_go2w_stand_example(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
            "⚠️ WARNING: GO2W Stand Example\n\nThis example will control the robot's joints directly:\n• Low-level joint control\n• Custom PID parameters\n• Real-time state monitoring\n\nPlease ensure:\n1. Robot is on stable surface\n2. No obstacles around\n3. Ready to stop if needed\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the stand example on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=eth0 DDS_PARTICIPANT_INDEX=0 ./go2w_stand_example eth0'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=eth0 DDS_PARTICIPANT_INDEX=0 ./go2w_stand_example eth0'

# If we get here, the SSH session ended
# Cleanup happens automatically via trap
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    
    def run_hello_world_example(self, widget):
        # Create a dialog to choose which part to run
        dialog = Gtk.Dialog("Hello World Example", self, 0)
        dialog.set_default_size(300, 200)
        box = dialog.get_content_area()
        label = Gtk.Label(label="Choose which part to run:")
        box.add(label)
        
        # Add buttons for each part
        laptop_pub_btn = Gtk.Button(label="Run Publisher on Laptop")
        laptop_sub_btn = Gtk.Button(label="Run Subscriber on Laptop")
        robot_pub_btn = Gtk.Button(label="Run Publisher on Robot")
        robot_sub_btn = Gtk.Button(label="Run Subscriber on Robot")
        
        def on_laptop_publisher(*args):
            cmd = "cd ~/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=enp3s0 DDS_PARTICIPANT_INDEX=0 ./test_publisher"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
            dialog.destroy()
        
        def on_laptop_subscriber(*args):
            cmd = "cd ~/unitree_sdk2/build/bin && DDS_DOMAIN=0 DDS_INTERFACE=enp3s0 DDS_PARTICIPANT_INDEX=0 ./test_subscriber"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
            dialog.destroy()
        
        def on_robot_publisher(*args):
            # Create a script that will handle the SSH session and process termination
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the publisher on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_publisher'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_publisher'
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
            dialog.destroy()
        
        def on_robot_subscriber(*args):
            # Create a script that will handle the SSH session and process termination
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the subscriber on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_subscriber'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2/build/bin && ./test_subscriber'
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
            dialog.destroy()
        
        laptop_pub_btn.connect("clicked", on_laptop_publisher)
        laptop_sub_btn.connect("clicked", on_laptop_subscriber)
        robot_pub_btn.connect("clicked", on_robot_publisher)
        robot_sub_btn.connect("clicked", on_robot_subscriber)
        
        box.add(laptop_pub_btn)
        box.add(laptop_sub_btn)
        box.add(robot_pub_btn)
        box.add(robot_sub_btn)
        dialog.show_all()
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()
    
    def exit_app(self, widget):
        Gtk.main_quit()

class GO2WPythonExamplesMenu(Gtk.Window):
    def __init__(self, parent, robot_ip="192.168.123.18"):
        Gtk.Window.__init__(self, title="Unitree GO2W Python SDK Examples")
        self.robot_ip = robot_ip
        self.set_border_width(24)
        self.set_default_size(400, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">GO2W Python SDK Examples</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Example buttons
        examples = [
            ("GO2W Sport Client (High-Level)", self.run_go2w_sport_client),
            ("GO2W Stand Example (Low-Level)", self.run_go2w_stand_example),
            ("Hello World Example", self.run_hello_world_example)
        ]
        
        for label, callback in examples:
            btn = Gtk.Button(label=label)
            btn.set_size_request(0, 40)
            btn.connect("clicked", callback)
            vbox.pack_start(btn, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
    
    def run_go2w_sport_client(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL,
            "🤖 GO2W Sport Client (Python)\n\nHigh-level control features:\n• Damp mode\n• Stand up/Stand down\n• Movement control\n• Speed levels\n• Gait switching\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the sport client on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/go2w/high_level && python3 go2w_sport_client.py eth0'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/go2w/high_level && python3 go2w_sport_client.py eth0'

# If we get here, the SSH session ended
# Cleanup happens automatically via trap
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    
    def run_go2w_stand_example(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.WARNING, Gtk.ButtonsType.OK_CANCEL,
            "⚠️ WARNING: GO2W Stand Example (Python)\n\nLow-level joint control:\n• Custom PID parameters\n• Direct motor control\n• Real-time state monitoring\n• Motion switching\n\nPlease ensure robot is safe!\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                robot_ip = self.robot_ip
                tmp_script.write(f"""#!/bin/bash
# Run the stand example on the robot
echo "Running: ssh unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/go2w/low_level && python3 go2w_stand_example.py eth0'"
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/go2w/low_level && python3 go2w_stand_example.py eth0'

# If we get here, the SSH session ended
# Cleanup happens automatically via trap
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    
    def run_hello_world_example(self, widget):
        # Create a dialog to choose which part to run
        dialog = Gtk.Dialog("Hello World Example", self, 0)
        dialog.set_default_size(300, 200)
        box = dialog.get_content_area()
        label = Gtk.Label(label="Choose which part to run:")
        box.add(label)
        
        # Add buttons for each part
        laptop_pub_btn = Gtk.Button(label="Run Publisher on Laptop")
        laptop_sub_btn = Gtk.Button(label="Run Subscriber on Laptop")
        robot_pub_btn = Gtk.Button(label="Run Publisher on Robot")
        robot_sub_btn = Gtk.Button(label="Run Subscriber on Robot")
        
        def on_laptop_publisher(*args):
            cmd = "cd ~/unitree_sdk2_python/example/helloworld && python3 publisher.py"
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                tmp_script.write(f"""#!/bin/bash
echo 'Running: {cmd}'
cd ~/unitree_sdk2_python/example/helloworld && python3 publisher.py
""")
                script_path = tmp_script.name
                subprocess.run(["chmod", "+x", script_path])
                subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
                dialog.destroy()
        
        def on_laptop_subscriber(*args):
            cmd = "cd ~/unitree_sdk2_python/example/helloworld && python3 subscriber.py"
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                tmp_script.write(f"""#!/bin/bash
echo 'Running: {cmd}'
cd ~/unitree_sdk2_python/example/helloworld && python3 subscriber.py
""")
                script_path = tmp_script.name
                subprocess.run(["chmod", "+x", script_path])
                subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
                dialog.destroy()
        
        def on_robot_publisher(*args):
            # Create a script that will handle the SSH session and process termination
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                tmp_script.write(f"""#!/bin/bash
# Run the publisher on the robot
echo "Running: ssh unitree@{self.robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/helloworld && python3 publisher.py'"
ssh -t unitree@{self.robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/helloworld && python3 publisher.py'
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
            dialog.destroy()
        
        def on_robot_subscriber(*args):
            # Create a script that will handle the SSH session and process termination
            with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                tmp_script.write(f"""#!/bin/bash
# Run the subscriber on the robot
echo "Running: ssh unitree@{self.robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/helloworld && python3 subscriber.py'"
ssh -t unitree@{self.robot_ip} 'cd /home/unitree/unitree_sdk2_python/example/helloworld && python3 subscriber.py'
""")
                script_path = tmp_script.name
            
            # Make the script executable
            subprocess.run(["chmod", "+x", script_path])
            
            # Run the script in a new terminal
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
            dialog.destroy()
        
        laptop_pub_btn.connect("clicked", on_laptop_publisher)
        laptop_sub_btn.connect("clicked", on_laptop_subscriber)
        robot_pub_btn.connect("clicked", on_robot_publisher)
        robot_sub_btn.connect("clicked", on_robot_subscriber)
        
        box.add(laptop_pub_btn)
        box.add(laptop_sub_btn)
        box.add(robot_pub_btn)
        box.add(robot_sub_btn)
        dialog.show_all()
    
    def run_obstacle_avoidance_move(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL,
            "🚧 Obstacle Avoidance Move\n\nPerfect for cemetery mapping:\n• LiDAR-based detection\n• Autonomous navigation\n• Path planning\n• Collision avoidance\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            cmd = "cd ~/unitree_sdk2_python/example/obstacles_avoid && python3 obstacles_avoid_move.py enp3s0"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_obstacle_avoidance_switch(self, widget):
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, Gtk.ButtonsType.OK_CANCEL,
            "🚧 Obstacle Avoidance Switch\n\nAdvanced obstacle avoidance:\n• Mode switching\n• Dynamic behavior changes\n• Enhanced navigation\n• Cemetery environment ready\n\nContinue?")
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            cmd = "cd ~/unitree_sdk2_python/example/obstacles_avoid && python3 obstacles_avoid_switch.py enp3s0"
            subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def run_wireless_controller(self, widget):
        cmd = "cd ~/unitree_sdk2_python/example/wireless_controller && python3 wireless_controller.py enp3s0"
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"echo 'Running: {cmd}'; {cmd}; exec bash"])
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()
    
    def exit_app(self, widget):
        Gtk.main_quit()

class GO2WMenuWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Unitree GO2W-U5 Launcher")
        self.set_border_width(24)
        self.set_default_size(400, 500)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.connected = False
        self.status_label = Gtk.Label()
        self.update_status_label()
        self.parent = parent
        self.network_check_in_progress = False
        
        # Load configuration
        self.config = load_go2w_config()
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Connection method selection
        conn_frame = Gtk.Frame(label="Connection Method")
        conn_frame.set_label_align(0.5, 0.5)
        conn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        conn_frame.add(conn_box)
        conn_frame.set_border_width(8)
        
        # Radio buttons for connection method
        self.ethernet_radio = Gtk.RadioButton(label=f"Ethernet ({ETHERNET_IP})")
        self.wifi_radio = Gtk.RadioButton.new_with_label_from_widget(self.ethernet_radio, "WiFi")
        conn_box.pack_start(self.ethernet_radio, False, False, 0)
        conn_box.pack_start(self.wifi_radio, False, False, 0)
        
        # Set current selection
        if self.config["connection_method"] == "wifi":
            self.wifi_radio.set_active(True)
        else:
            self.ethernet_radio.set_active(True)
        
        # Connect radio buttons to handler
        self.ethernet_radio.connect("toggled", self.on_connection_method_changed)
        self.wifi_radio.connect("toggled", self.on_connection_method_changed)
        
        # WiFi IP display and configuration
        wifi_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wifi_label = Gtk.Label(label="WiFi IP:")
        wifi_ip = self.config.get("wifi_ip", "")
        self.wifi_ip_label = Gtk.Label()
        if wifi_ip:
            self.wifi_ip_label.set_markup(f'<span foreground="#00FF00">{wifi_ip}</span>')
        else:
            self.wifi_ip_label.set_markup('<span foreground="#FF5555">Not set</span>')
        wifi_set_btn = Gtk.Button(label="Set WiFi IP")
        wifi_set_btn.set_size_request(100, 30)
        wifi_set_btn.connect("clicked", self.on_set_wifi_ip)
        wifi_box.pack_start(wifi_label, False, False, 0)
        wifi_box.pack_start(self.wifi_ip_label, True, True, 0)
        wifi_box.pack_start(wifi_set_btn, False, False, 0)
        conn_box.pack_start(wifi_box, False, False, 0)
        
        vbox.pack_start(conn_frame, False, False, 0)
        
        # Add network check/setup button
        self.net_btn = Gtk.Button(label="Check/Setup Network Connection")
        self.net_btn.set_size_request(0, 40)
        self.net_btn.connect("clicked", self.on_check_network)
        vbox.pack_start(self.net_btn, False, False, 0)
        vbox.pack_start(self.status_label, False, False, 0)
        label = Gtk.Label()
        label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">Unitree GO2W-U5 Menu</span>')
        vbox.pack_start(label, False, False, 0)
        # Create menu options
        self.menu_options = ["Connect to EDU",
            "ROS 2 Terminal",
            "Streaming",
            "Hesai XT16 Mapping + SLAM",
            "MuJoCo Simulation",
            "C++ SDK Examples",
            "Python SDK Examples"
        ]
        for text in self.menu_options:
            btn = Gtk.Button(label=text)
            btn.set_size_request(0, 40)
            btn.connect("clicked", self.on_menu_option)
            vbox.pack_start(btn, False, False, 0)
        # Add Return button at the bottom
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
        # Start live status update
        self.keep_updating = True
        self.status_thread = threading.Thread(target=self.status_updater, daemon=True)
        self.status_thread.start()
        self.connect("destroy", self.on_destroy)
    
    def update_status_label(self):
        robot_ip = get_go2w_robot_ip()
        if self.connected:
            self.status_label.set_markup(f'<span size="large" weight="bold" foreground="#00FF00">Connected to Unitree GO2W-U5 ({robot_ip})</span>')
        else:
            self.status_label.set_markup(f'<span size="large" weight="bold" foreground="#FF5555">Not connected to Unitree GO2W-U5 ({robot_ip})</span>')
    
    def status_updater(self):
        while self.keep_updating:
            try:
                robot_ip = get_go2w_robot_ip()
                result = subprocess.run(["ping", "-c", "1", "-W", "1", robot_ip], stdout=subprocess.DEVNULL)
                connected = (result.returncode == 0)
            except Exception:
                connected = False
            if connected != self.connected:
                self.connected = connected
                GLib.idle_add(self.update_status_label)
            time.sleep(1)
    
    def on_connection_method_changed(self, widget):
        """Handle connection method radio button changes"""
        if self.ethernet_radio.get_active():
            self.config["connection_method"] = "ethernet"
        else:
            self.config["connection_method"] = "wifi"
        save_go2w_config(self.config)
        # Update WiFi IP label display
        wifi_ip = self.config.get("wifi_ip", "")
        if wifi_ip:
            self.wifi_ip_label.set_markup(f'<span foreground="#00FF00">{wifi_ip}</span>')
        else:
            self.wifi_ip_label.set_markup('<span foreground="#FF5555">Not set</span>')
        # Update status immediately
        self.connected = False
        GLib.idle_add(self.update_status_label)
    
    def on_set_wifi_ip(self, widget):
        """Open dialog to set WiFi IP address"""
        dialog = Gtk.Dialog(title="Set WiFi IP Address", parent=self, flags=0)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                          Gtk.STOCK_OK, Gtk.ResponseType.OK)
        dialog.set_default_size(400, 150)
        dialog.set_border_width(16)
        
        box = dialog.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.add(vbox)
        
        label = Gtk.Label(label="Enter WiFi IP address:")
        label.set_halign(Gtk.Align.START)
        vbox.pack_start(label, False, False, 0)
        
        entry = Gtk.Entry()
        entry.set_text(self.config.get("wifi_ip", ""))
        entry.set_placeholder_text("e.g., 192.168.1.100")
        vbox.pack_start(entry, False, False, 0)
        
        info_label = Gtk.Label()
        info_label.set_markup('<span size="small" foreground="#AAAAAA">The app will remember this IP address</span>')
        info_label.set_halign(Gtk.Align.START)
        vbox.pack_start(info_label, False, False, 0)
        
        dialog.show_all()
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            wifi_ip = entry.get_text().strip()
            if wifi_ip:
                # Validate IP format (basic check)
                parts = wifi_ip.split('.')
                if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                    self.config["wifi_ip"] = wifi_ip
                    save_go2w_config(self.config)
                    self.wifi_ip_label.set_text(wifi_ip)
                    self.wifi_ip_label.set_markup(f'<span foreground="#00FF00">{wifi_ip}</span>')
                    
                    # If WiFi is selected, test connection
                    if self.wifi_radio.get_active():
                        self.test_wifi_connection(wifi_ip)
                else:
                    error_dialog = Gtk.MessageDialog(
                        parent=self,
                        flags=0,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Invalid IP Address"
                    )
                    error_dialog.format_secondary_text("Please enter a valid IP address (e.g., 192.168.1.100)")
                    error_dialog.run()
                    error_dialog.destroy()
        
        dialog.destroy()
    
    def test_wifi_connection(self, wifi_ip):
        """Test WiFi connection and update status"""
        def test_thread():
            try:
                result = subprocess.run(["ping", "-c", "1", "-W", "2", wifi_ip], 
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                connected = (result.returncode == 0)
                GLib.idle_add(lambda: setattr(self, 'connected', connected))
                GLib.idle_add(self.update_status_label)
            except Exception:
                GLib.idle_add(lambda: setattr(self, 'connected', False))
                GLib.idle_add(self.update_status_label)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def on_destroy(self, *args):
        self.keep_updating = False
    
    def on_check_network(self, widget):
        # Get the current robot IP based on connection method
        robot_ip = get_go2w_robot_ip()
        connection_method = self.config.get("connection_method", "ethernet")
        
        # For WiFi, just test the connection
        if connection_method == "wifi":
            if not self.config.get("wifi_ip"):
                error_dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.WARNING,
                    buttons=Gtk.ButtonsType.OK,
                    text="WiFi IP Not Set"
                )
                error_dialog.format_secondary_text("Please set the WiFi IP address first.")
                error_dialog.run()
                error_dialog.destroy()
                return
            
            # Test WiFi connection
            self.net_btn.set_sensitive(False)
            progress = ProgressDialog(self, "Testing WiFi Connection", f"Pinging {robot_ip}...")
            
            def wifi_test_thread():
                try:
                    result = subprocess.run(["ping", "-c", "3", "-W", "2", robot_ip], 
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    connected = (result.returncode == 0)
                    self.connected = connected
                    GLib.idle_add(self.update_status_label)
                    if connected:
                        GLib.idle_add(progress.set_text, f"✅ Successfully connected to {robot_ip} via WiFi!")
                    else:
                        GLib.idle_add(progress.set_text, f"❌ Could not reach {robot_ip} via WiFi.\nPlease check your WiFi connection and IP address.")
                    time.sleep(2)
                except Exception as e:
                    GLib.idle_add(progress.set_text, f"❌ Error: {str(e)}")
                    time.sleep(2)
                finally:
                    GLib.idle_add(progress.destroy)
                    GLib.idle_add(lambda: self.net_btn.set_sensitive(True))
            
            threading.Thread(target=wifi_test_thread, daemon=True).start()
            progress.show_all()
            while progress.get_visible():
                while Gtk.events_pending():
                    Gtk.main_iteration()
                time.sleep(0.05)
            return
        
        # For Ethernet, use the existing network setup logic
        if getattr(self, 'network_check_in_progress', False):
            return
        self.network_check_in_progress = True
        self.net_btn.set_sensitive(False)
        progress = ProgressDialog(self, "Connecting to Unitree GO2W-U5", "Checking connection...")
        cancel_requested = {'value': False}
        def on_cancel(*args):
            cancel_requested['value'] = True
            progress.destroy()
            self.network_check_in_progress = False
            self.net_btn.set_sensitive(True)
        progress.connect("delete-event", on_cancel)
        progress.connect("response", on_cancel)
        
        def network_thread():
            try:
                # First check if we're already connected
                GLib.idle_add(progress.set_text, "Checking current connection...")
                
                # Try to find an interface that can reach the robot
                for iface in netifaces.interfaces():
                    # Skip loopback and wireless interfaces for Ethernet
                    if iface.startswith(('lo', 'wl', 'wlan')):
                        continue
                    try:
                        result = subprocess.run(["ping", "-I", iface, "-c", "1", "-W", "1", robot_ip], 
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if result.returncode == 0:
                            # We found a working interface
                            self.connected = True
                            self.selected_iface = iface
                            GLib.idle_add(self.update_status_label)
                            GLib.idle_add(progress.set_text, f"✅ Already connected to Unitree GO2W-U5 on {iface}!")
                            time.sleep(2)
                            GLib.idle_add(progress.destroy)
                            GLib.idle_add(lambda: setattr(self, 'network_check_in_progress', False))
                            GLib.idle_add(lambda: self.net_btn.set_sensitive(True))
                            return
                    except Exception:
                        continue
                
                # If we get here, we need to set up the network
                GLib.idle_add(progress.set_text, "Setting up network connection...")
                
                # Create a script to handle all network setup in one go
                with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
                    tmp_script.write("""#!/bin/bash
set -e  # Exit on any error

# Function to check command success
check_success() {
    if [ $? -ne 0 ]; then
        echo "Failed: $1" >&2
        exit 1
    fi
    echo "Success: $1"
}

# Find the interface that can reach the robot
echo "Step 1: Finding suitable network interface..."
ROBOT_IFACE=""
for iface in $(ip -o link show | awk -F': ' '{print $2}'); do
    # Skip loopback and wireless interfaces
    if [[ $iface == lo* ]] || [[ $iface == wl* ]] || [[ $iface == wlan* ]]; then
        continue
    fi
    
    # Try to ping the robot through this interface
    if ping -I $iface -c 1 -W 1 192.168.123.18 > /dev/null 2>&1; then
        ROBOT_IFACE=$iface
        echo "Found working interface: $iface"
        break
    fi
done

if [ -z "$ROBOT_IFACE" ]; then
    echo "Step 2: Bringing up interface $ROBOT_IFACE..."
    
    # Find the first non-loopback, non-wireless interface
    for iface in $(ip -o link show | awk -F': ' '{print $2}'); do
        if [[ $iface == lo* ]] || [[ $iface == wl* ]] || [[ $iface == wlan* ]]; then
            continue
        fi
        ROBOT_IFACE=$iface
        echo "Using interface: $iface"
        break
    done
    
    if [ -z "$ROBOT_IFACE" ]; then
        echo "No suitable network interface found"
        exit 1
    fi
    
    # Remove existing IP addresses
    echo "Step 3: Removing existing IP addresses..."
    for ip in $(ip addr show $ROBOT_IFACE | grep -oP '192.168.123.\\d+'); do
        ip addr del $ip/24 dev $ROBOT_IFACE 2>/dev/null || true
    done
    
    # Set static IP
    echo "Step 4: Setting static IP..."
    ip addr add 192.168.123.99/24 dev $ROBOT_IFACE
    check_success "Added IP address to $ROBOT_IFACE"
    
    # Bring up the interface
    ip link set $ROBOT_IFACE up
    check_success "Brought up $ROBOT_IFACE"
    
    # Wait for network to stabilize
    echo "Step 5: Waiting for network to stabilize..."
    sleep 3
    
    # Test connection to robot
    echo "Step 6: Testing connection to robot..."
    if ! ping -I $ROBOT_IFACE -c 1 -W 2 192.168.123.18 > /dev/null 2>&1; then
        echo "Failed: Could not reach robot at 192.168.123.18" >&2
        exit 1
    fi
    echo "Success: Robot is reachable"
    
    # All steps completed successfully
    echo "Network setup completed successfully"
    echo "1" > /tmp/network_setup_status
    echo "$ROBOT_IFACE" > /tmp/robot_interface
else
    echo "Success: Already connected to robot via $ROBOT_IFACE"
    echo "1" > /tmp/network_setup_status
    echo "$ROBOT_IFACE" > /tmp/robot_interface
fi
""")
                    script_path = tmp_script.name
                
                subprocess.run(["chmod", "+x", script_path])
                
                # Run the script and capture output in real-time
                proc = subprocess.Popen(["pkexec", "bash", script_path], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      universal_newlines=True,
                                      bufsize=1)
                
                # Read output in real-time
                last_step_time = time.time()
                while True:
                    output = proc.stdout.readline()
                    if output == '' and proc.poll() is not None:
                        break
                    if output:
                        # If this is a new step (starts with "Step"), wait to ensure previous step was visible
                        if output.strip().startswith("Step"):
                            # Calculate time since last step
                            time_since_last = time.time() - last_step_time
                            if time_since_last < 1.0:  # If less than 1 second has passed
                                time.sleep(1.0 - time_since_last)  # Wait the remaining time
                            last_step_time = time.time()
                        
                        GLib.idle_add(progress.set_text, output.strip())
                        # Force update the GUI
                        while Gtk.events_pending():
                            Gtk.main_iteration()
                
                # Get any remaining output
                stdout, stderr = proc.communicate()
                if stdout:
                    print(f"Network setup output: {stdout}")
                if stderr:
                    print(f"Network setup errors: {stderr}")
                
                # Ensure the last step is visible for at least 1 second
                time_since_last = time.time() - last_step_time
                if time_since_last < 1.0:
                    time.sleep(1.0 - time_since_last)
                
                # Check if network setup was successful
                try:
                    with open('/tmp/network_setup_status', 'r') as f:
                        setup_success = int(f.read().strip()) == 1
                    with open('/tmp/robot_interface', 'r') as f:
                        self.selected_iface = f.read().strip()
                except:
                    setup_success = False
                
                # Wait for network to stabilize before final check
                time.sleep(2)
                
                # Do a final connection check
                try:
                    result = subprocess.run(["ping", "-c", "1", "-W", "1", robot_ip], stdout=subprocess.DEVNULL)
                    if result.returncode == 0:
                        setup_success = True
                except Exception:
                    setup_success = False
                
                if setup_success:
                    self.connected = True
                    GLib.idle_add(self.update_status_label)
                    GLib.idle_add(progress.set_text, f"✅ Connected to Unitree GO2W-U5 on {self.selected_iface}!")
                else:
                    # Try for up to 10 seconds to establish connection
                    connection_succeeded = False
                    for _ in range(10):
                        try:
                            result = subprocess.run(["ping", "-c", "1", "-W", "1", robot_ip], stdout=subprocess.DEVNULL)
                            if result.returncode == 0:
                                self.connected = True
                                GLib.idle_add(self.update_status_label)
                                GLib.idle_add(progress.set_text, f"✅ Connected to Unitree GO2W-U5 on {self.selected_iface}!")
                                connection_succeeded = True
                                break
                        except Exception:
                            pass
                        time.sleep(1)
                    
                    if not connection_succeeded:
                        GLib.idle_add(progress.set_text, "❌ Failed to configure network settings.\nPlease check your network settings.")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Exception in network thread: {e}")
                GLib.idle_add(progress.set_text, f"❌ Error: {str(e)}")
                time.sleep(2)
            
            finally:
                try:
                    GLib.idle_add(progress.destroy)
                    GLib.idle_add(lambda: setattr(self, 'network_check_in_progress', False))
                    GLib.idle_add(lambda: self.net_btn.set_sensitive(True))
                except Exception as e:
                    print(f"Error in cleanup: {e}")
        
        threading.Thread(target=network_thread, daemon=True).start()
        progress.show_all()
        while progress.get_visible():
            while Gtk.events_pending():
                Gtk.main_iteration()
            time.sleep(0.05)

    def on_menu_option(self, widget):
        text = widget.get_label()
        if text == "Connect to EDU":
            self.connect_pc2(widget)
        elif text == "ROS 2 Terminal":
            self.ros2_terminal(widget)
        elif text == "Streaming":
            self.show_streams_menu(widget)
        elif text == "Hesai XT16 Mapping + SLAM":
            self.show_xt16_slam_menu(widget)
        elif text == "C++ SDK Examples":
            self.show_sdk_examples(widget)
        elif text == "Python SDK Examples":
            self.show_python_examples(widget)
        elif text == "MuJoCo Simulation":
            self.launch_mujoco_simulation(widget)

    def show_streams_menu(self, widget):
        """Show the Streams submenu"""
        streams_menu = GO2WStreamsMenu(self)
        streams_menu.show_all()

    def show_xt16_slam_menu(self, widget):
        """Show the XT16 Mapping + SLAM menu"""
        slam_menu = GO2WXT16SlamMenu(self)
        slam_menu.show_all()

    def show_sdk_examples(self, widget):
        """Show the GO2W C++ SDK examples menu"""
        robot_ip = get_go2w_robot_ip()
        examples_menu = GO2WSDKExamplesMenu(self, robot_ip)
        examples_menu.show_all()

    def show_python_examples(self, widget):
        """Show the GO2W Python SDK examples menu"""
        robot_ip = get_go2w_robot_ip()
        examples_menu = GO2WPythonExamplesMenu(self, robot_ip)
        examples_menu.show_all()
    
    def launch_mujoco_simulation(self, widget):
        """Launch MuJoCo simulation for GO2W"""
        command = f"cd {MUJOCO_BUILD_DIR} && ./unitree_mujoco -r go2w -s scene_terrain.xml"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=MuJoCo GO2-W", 
                "--", 
                "bash", 
                "-c", 
                f"echo 'Running: {command}'; echo '=========================================='; {command}; echo Press Enter to close...; read"
            ])
        except Exception as e:
            print(f"Error launching MuJoCo: {e}")
    
    def view_camera(self, widget):
        """Launch camera viewer for GO2W"""
        script_path = os.path.join(APP_DIR, "go2w_camera_viewer.py")
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=GO2W Front Camera", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🎥 GO2W Front Camera Stream"; echo "=========================================="; echo "Running: python3 {script_path} enp3s0"; echo "=========================================="; echo "Press ESC to close the camera window"; echo ""; python3 "{script_path}" enp3s0'
            ])
        except Exception as e:
            print(f"Error launching camera viewer: {e}")
    
    def visualize_lidar(self, widget):
        """Launch RViz2 with L1 lidar visualization"""
        config_path = os.path.join(APP_DIR, "unitree_l1_lidar.rviz")
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=GO2W L1 Lidar Visualization", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🗺️  GO2W L1 Lidar Visualization (RViz2)"; echo "=========================================="; echo "Running: source /opt/ros/humble/setup.bash && source ~/unitree_ros2/... && rviz2 -d {config_path}"; echo "=========================================="; echo "Lidar: L1 (Unitree)"; echo "Fixed Frame: utlidar_lidar"; echo "Topic: /utlidar/cloud"; echo ""; source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && rviz2 -d "{config_path}"'
            ])
        except Exception as e:
            print(f"Error launching RViz2: {e}")
    
    def view_camera(self, widget):
        """Launch camera viewer for GO2W"""
        script_path = os.path.join(APP_DIR, "go2w_camera_viewer.py")
        network_interface = get_go2w_network_interface()
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=GO2W Front Camera", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🎥 GO2W Front Camera Stream"; echo "=========================================="; echo "Running: python3 {script_path} {network_interface}"; echo "=========================================="; echo "Press ESC to close the camera window"; echo ""; python3 "{script_path}" {network_interface}'
            ])
        except Exception as e:
            print(f"Error launching camera viewer: {e}")
    
    def connect_pc2(self, widget):
        robot_ip = get_go2w_robot_ip()
        subprocess.Popen(["nautilus", f"sftp://unitree@{robot_ip}/home/unitree"])
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", f"ssh unitree@{robot_ip}; exec bash"])
    
    def ros2_terminal(self, widget):
        # Get the appropriate network interface
        network_interface = get_go2w_network_interface()
        robot_ip = get_go2w_robot_ip()
        config = load_go2w_config()
        connection_method = config.get("connection_method", "ethernet")
        
        # Create a ROS2 launcher script with help menu
        ros2_script = f'''#!/bin/bash
echo "=========================================="
echo "🤖 ROS2 Environment Launcher"
echo "=========================================="
echo "Connection: {connection_method.upper()}"
echo "Robot IP: {robot_ip}"
echo "Network Interface: {network_interface}"
echo "=========================================="
echo ""

# Set DDS environment variables for Unitree robot communication
export DDS_DOMAIN=0
export DDS_INTERFACE={network_interface}
export DDS_PARTICIPANT_INDEX=0

echo "📡 DDS Configuration:"
echo "  DDS_DOMAIN=$DDS_DOMAIN"
echo "  DDS_INTERFACE=$DDS_INTERFACE"
echo "  DDS_PARTICIPANT_INDEX=$DDS_PARTICIPANT_INDEX"
echo ""

# Detect ROS2 version
if [ -f /opt/ros/humble/setup.bash ]; then
    ROS_VERSION_NAME="Humble"
    source /opt/ros/humble/setup.bash
elif [ -f /opt/ros/foxy/setup.bash ]; then
    ROS_VERSION_NAME="Foxy"
    source /opt/ros/foxy/setup.bash
else
    echo "❌ No ROS2 installation found!"
    exit 1
fi

# Source additional setup files if they exist
if [ -f ~/unitree_ros2/cyclonedds_ws/install/setup.bash ]; then
    source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
fi

if [ -f ~/unitree_ros2/setup.sh ]; then
    source ~/unitree_ros2/setup.sh
fi

# Override CYCLONEDDS_URI with the correct interface (setup.sh hardcodes enp3s0)
# CYCLONEDDS_URI takes precedence over DDS_INTERFACE, so we must set it correctly
export CYCLONEDDS_URI="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\\"{network_interface}\\" priority=\\"default\\" multicast=\\"default\\" /></Interfaces></General></Domain></CycloneDDS>"

# Also set DDS variables for consistency
export DDS_DOMAIN=0
export DDS_INTERFACE={network_interface}
export DDS_PARTICIPANT_INDEX=0

echo "✅ ROS2 $ROS_VERSION_NAME sourced successfully"
echo "📍 Current directory: $(pwd)"
echo ""
echo "📡 DDS Configuration (after overriding setup.sh):"
echo "  DDS_DOMAIN=$DDS_DOMAIN"
echo "  DDS_INTERFACE=$DDS_INTERFACE"
echo "  DDS_PARTICIPANT_INDEX=$DDS_PARTICIPANT_INDEX"
echo "  CYCLONEDDS_URI configured for interface: {network_interface}"
echo ""

# Show ROS2 help menu
echo "🚀 ROS2 COMMAND REFERENCE"
echo "=========================================="
echo ""
echo "📋 BASIC COMMANDS:"
echo "  ros2 --help                    # Show all ROS2 commands"
echo "  ros2 node list                 # List active nodes"
echo "  ros2 topic list                # List available topics"
echo "  ros2 service list              # List available services"
echo "  ros2 action list               # List available actions"
echo ""
echo "🔍 MONITORING:"
echo "  ros2 topic echo /topic_name    # Monitor a topic"
echo "  ros2 topic info /topic_name    # Get topic info"
echo "  ros2 node info /node_name      # Get node info"
echo "  ros2 service type /service_name # Get service type"
echo ""
echo "🏃 RUNNING NODES:"
echo "  ros2 run package_name node_name # Run a specific node"
echo "  ros2 launch package_name launch_file.launch.py # Launch a launch file"
echo ""
echo "📦 PACKAGE MANAGEMENT:"
echo "  ros2 pkg list                  # List all packages"
echo "  ros2 pkg list | grep unitree   # Find Unitree packages"
echo "  ros2 pkg executables package_name # List executables in package"
echo ""
echo "🔧 WORKSPACE:"
echo "  colcon build                   # Build workspace"
echo "  colcon build --packages-select package_name # Build specific package"
echo "  source install/setup.bash      # Source workspace"
echo ""
echo "🤖 UNITREE SPECIFIC:"
echo "  ros2 run unitree_go2_bringup go2_bringup_node # Run GO2 node"
echo "  ros2 run unitree_g1_bringup g1_bringup_node   # Run G1 node"
echo "  ros2 topic list | grep unitree # List Unitree topics"
echo ""
echo "❓ GET HELP:"
echo "  ros2 <command> --help          # Get help for specific command"
echo "  ros2 <command> -h              # Short help"
echo ""

# Show current ROS2 status
echo "📊 CURRENT ROS2 STATUS:"
echo "=========================================="
echo "ROS_DISTRO: $ROS_DISTRO"
echo "ROS_VERSION: $ROS_VERSION"
echo ""

# Show available topics
echo "📡 ACTIVE TOPICS:"
echo "=========================================="
ros2 topic list
echo ""

# Show available nodes
echo "🔗 ACTIVE NODES:"
echo "=========================================="
ros2 node list
echo ""

echo "💡 TIP: Type 'ros2 --help' for complete command reference"
echo "💡 TIP: Use 'ros2 <command> --help' for specific command help"
echo ""

# Keep terminal open
echo "=========================================="

# Start interactive bash with ROS2 environment
exec bash'''
        
        # Write script to temporary file
        with tempfile.NamedTemporaryFile('w', delete=False, suffix='.sh') as tmp_script:
            tmp_script.write(ros2_script)
            script_path = tmp_script.name
        
        # Make executable and run
        subprocess.run(["chmod", "+x", script_path])
        subprocess.Popen(["gnome-terminal", "--", "bash", "-c", script_path])
    
    def exit_app(self, widget):
        Gtk.main_quit()
    
    def on_return(self, widget):
        self.keep_updating = False
        self.destroy()
        self.parent.show_all()

    def on_l1_lidar(self, widget):
        """Open L1 LIDAR mapping interface"""
        self.hide()
        lidar_window = L1LidarWindow(self)
        lidar_window.show_all()

class L1LidarWindow(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="L1 LIDAR Mapping & SLAM")
        self.set_border_width(24)
        self.set_default_size(500, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">L1 LIDAR Mapping & SLAM</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Step 1: Start L1 LiDAR Driver
        step1_frame = self.create_step_frame(
            "Step 1: Start L1 LiDAR Driver",
            "cd ~/unilidar_sdk/unitree_lidar_ros && source devel/setup.bash && roslaunch unitree_lidar_ros run_without_rviz.launch",
            self.run_lidar_driver
        )
        vbox.pack_start(step1_frame, False, False, 0)
        
        # Step 2: Start L1 SLAM Mapping
        step2_frame = self.create_step_frame(
            "Step 2: Start L1 SLAM Mapping",
            "cd ~/catkin_point_lio_unilidar && source devel/setup.bash && roslaunch point_lio_unilidar mapping_unilidar_l1.launch",
            self.run_slam_mapping
        )
        vbox.pack_start(step2_frame, False, False, 0)
        
        # Step 3: Open Saved Files Folder
        step3_frame = self.create_step_frame(
            "Step 3: Open Saved Files Folder",
            "nautilus ~/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/",
            self.open_maps_folder
        )
        vbox.pack_start(step3_frame, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return to GO2W Menu")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
    
    def create_step_frame(self, title, command, callback):
        """Create a frame with title and run button"""
        frame = Gtk.Frame()
        frame.set_border_width(8)
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup(f'<span size="large" weight="bold" foreground="#00BFFF">{title}</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Run button
        run_btn = Gtk.Button(label="▶ Run Command")
        run_btn.set_size_request(0, 40)
        run_btn.get_style_context().add_class("suggested-action")
        run_btn.connect("clicked", callback)
        vbox.pack_start(run_btn, False, False, 0)
        
        return frame
    
    def run_lidar_driver(self, widget):
        """Run L1 LiDAR driver command"""
        command = "cd ~/unilidar_sdk/unitree_lidar_ros && source devel/setup.bash && roslaunch unitree_lidar_ros run_without_rviz.launch"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=L1 LiDAR Driver", 
                "--", 
                "bash", 
                "-c", 
                f"echo 'Running: {command}'; echo '=========================================='; {command}; echo Press Enter to close...; read"
            ])
        except Exception as e:
            print(f"Error launching L1 LiDAR driver: {e}")
    
    def run_slam_mapping(self, widget):
        """Run L1 SLAM mapping command"""
        command = "cd ~/catkin_point_lio_unilidar && source devel/setup.bash && roslaunch point_lio_unilidar mapping_unilidar_l1.launch"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=L1 SLAM Mapping", 
                "--", 
                "bash", 
                "-c", 
                f"echo 'Running: {command}'; echo '=========================================='; {command}; echo Press Enter to close...; read"
            ])
        except Exception as e:
            print(f"Error launching L1 SLAM mapping: {e}")
    
    def open_maps_folder(self, widget):
        """Open the maps folder in file manager"""
        maps_folder = os.path.expanduser("~/catkin_point_lio_unilidar/src/point_lio_unilidar/PCD/")
        try:
            subprocess.Popen(["nautilus", maps_folder])
        except Exception as e:
            print(f"Error opening maps folder: {e}")
    
    def on_return(self, widget):
        self.hide()
        self.parent.show_all()

class GO2WStreamsMenu(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="GO2W Streams")
        self.set_border_width(24)
        self.set_default_size(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">GO2W Streams</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Camera button
        camera_btn = Gtk.Button(label="Front Camera Stream")
        camera_btn.set_size_request(0, 50)
        camera_btn.connect("clicked", self.view_camera)
        vbox.pack_start(camera_btn, False, False, 0)
        
        # Lidar button
        lidar_btn = Gtk.Button(label="L1 LIDAR Stream")
        lidar_btn.set_size_request(0, 50)
        lidar_btn.connect("clicked", self.visualize_lidar)
        vbox.pack_start(lidar_btn, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 0)
    
    def view_camera(self, widget):
        """Launch camera viewer for GO2W"""
        script_path = os.path.join(APP_DIR, "go2w_camera_viewer.py")
        network_interface = get_go2w_network_interface()
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=GO2W Front Camera", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🎥 GO2W Front Camera Stream"; echo "=========================================="; echo "Running: python3 {script_path} {network_interface}"; echo "=========================================="; echo "Press ESC to close the camera window"; echo ""; python3 "{script_path}" {network_interface}'
            ])
        except Exception as e:
            print(f"Error launching camera viewer: {e}")
    
    def visualize_lidar(self, widget):
        """Launch RViz2 with L1 lidar visualization"""
        config_path = os.path.join(APP_DIR, "unitree_l1_lidar.rviz")
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=GO2W L1 Lidar Visualization", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🗺️  GO2W L1 Lidar Visualization (RViz2)"; echo "=========================================="; echo "Running: source /opt/ros/humble/setup.bash && source ~/unitree_ros2/... && rviz2 -d {config_path}"; echo "=========================================="; echo "Lidar: L1 (Unitree)"; echo "Fixed Frame: utlidar_lidar"; echo "Topic: /utlidar/cloud"; echo ""; source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && rviz2 -d "{config_path}"'
            ])
        except Exception as e:
            print(f"Error launching RViz2: {e}")
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()

class GO2WXT16SlamMenu(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="Hesai XT16 Mapping + SLAM")
        self.set_border_width(24)
        self.set_default_size(500, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        self.robot_ip = get_go2w_robot_ip()
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">🗺️ Hesai XT16 Mapping + SLAM</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup('<span size="small" foreground="#888888">Complete SLAM workflow for autonomous navigation</span>')
        info_label.set_line_wrap(True)
        vbox.pack_start(info_label, False, False, 0)
        
        # Section 1: Initial Setup
        section1_label = Gtk.Label()
        section1_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">📡 Step 1: Start XT16 Driver</span>')
        section1_label.set_xalign(0)
        vbox.pack_start(section1_label, False, False, 10)
        
        driver_btn = Gtk.Button(label="Start XT16 Lidar Driver")
        driver_btn.set_size_request(0, 50)
        driver_btn.connect("clicked", self.start_xt16_driver)
        vbox.pack_start(driver_btn, False, False, 0)
        
        driver_info = Gtk.Label()
        driver_info.set_markup('<span size="small" foreground="#666666">Keep this terminal running during mapping</span>')
        driver_info.set_xalign(0)
        vbox.pack_start(driver_info, False, False, 0)
        
        # Section 2: SLAM Service
        section2_label = Gtk.Label()
        section2_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">🤖 Step 2: Start SLAM Service</span>')
        section2_label.set_xalign(0)
        vbox.pack_start(section2_label, False, False, 10)
        
        slam_btn = Gtk.Button(label="Start SLAM Service")
        slam_btn.set_size_request(0, 50)
        slam_btn.connect("clicked", self.start_slam_service)
        vbox.pack_start(slam_btn, False, False, 0)
        
        slam_info = Gtk.Label()
        slam_info.set_markup('<span size="small" foreground="#666666">SLAM service processes lidar data</span>')
        slam_info.set_xalign(0)
        vbox.pack_start(slam_info, False, False, 0)
        
        # Section 3: Mapping Control
        section3_label = Gtk.Label()
        section3_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">🕹️ Step 3: Start Mapping Control</span>')
        section3_label.set_xalign(0)
        vbox.pack_start(section3_label, False, False, 10)
        
        keydemo_btn = Gtk.Button(label="Start KeyDemo (Mapping Control)")
        keydemo_btn.set_size_request(0, 50)
        keydemo_btn.connect("clicked", self.start_keydemo)
        vbox.pack_start(keydemo_btn, False, False, 0)
        
        keydemo_info = Gtk.Label()
        keydemo_info.set_markup('<span size="small" foreground="#666666">Press \'q\' to start mapping, \'w\' to save map</span>')
        keydemo_info.set_xalign(0)
        vbox.pack_start(keydemo_info, False, False, 0)
        
        # Section 4: Navigation
        section4_label = Gtk.Label()
        section4_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">🚀 Navigation Tools</span>')
        section4_label.set_xalign(0)
        vbox.pack_start(section4_label, False, False, 10)
        
        # Grid for navigation buttons
        nav_grid = Gtk.Grid()
        nav_grid.set_row_spacing(8)
        nav_grid.set_column_spacing(8)
        nav_grid.set_column_homogeneous(True)
        
        # Visualize Mapping button
        viz_map_btn = Gtk.Button(label="📊 Visualize Mapping")
        viz_map_btn.set_size_request(0, 45)
        viz_map_btn.connect("clicked", lambda w: self.visualize_slam(w, "mapping"))
        nav_grid.attach(viz_map_btn, 0, 0, 1, 1)
        
        # Visualize Relocation button
        viz_reloc_btn = Gtk.Button(label="📍 Visualize Navigation")
        viz_reloc_btn.set_size_request(0, 45)
        viz_reloc_btn.connect("clicked", lambda w: self.visualize_slam(w, "relocation"))
        nav_grid.attach(viz_reloc_btn, 1, 0, 1, 1)
        
        # View maps button
        view_maps_btn = Gtk.Button(label="View Saved Maps")
        view_maps_btn.set_size_request(0, 45)
        view_maps_btn.connect("clicked", self.view_saved_maps)
        nav_grid.attach(view_maps_btn, 0, 1, 1, 1)
        
        # Visualize maps button
        viz_maps_btn = Gtk.Button(label="🔍 Visualize Saved Maps")
        viz_maps_btn.set_size_request(0, 45)
        viz_maps_btn.connect("clicked", self.visualize_saved_maps)
        nav_grid.attach(viz_maps_btn, 1, 1, 1, 1)
        
        # Manual button
        manual_btn = Gtk.Button(label="Open Manual")
        manual_btn.set_size_request(0, 45)
        manual_btn.connect("clicked", self.open_manual)
        nav_grid.attach(manual_btn, 0, 2, 2, 1)
        
        vbox.pack_start(nav_grid, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 10)
    
    def start_xt16_driver(self, widget):
        """Start XT16 Lidar Driver"""
        try:
            # Create a wrapper that sources ROS and runs the command
            cmd = f'echo "Command: ssh -t unitree@{self.robot_ip} \'cd /unitree/module/unitree_slam/bin && ./xt16_driver eth0\'"; echo ""; echo "📡 Starting XT16 Lidar Driver"; echo "=========================================="; echo "Robot: {self.robot_ip}"; echo "Lidar: 192.168.123.20"; echo "Topic: rt/unitree/slam_lidar/points"; echo "=========================================="; echo ""; echo "Connecting and starting driver..."; echo ""; ssh -t unitree@{self.robot_ip} \'/bin/bash -c "source /opt/ros/foxy/setup.bash && export LD_LIBRARY_PATH=/usr/local/lib:/opt/ros/foxy/lib:$LD_LIBRARY_PATH && cd /unitree/module/unitree_slam/bin && ./xt16_driver eth0"\'; exec bash'
            subprocess.Popen([
                "gnome-terminal", 
                "--title=XT16 Lidar Driver", 
                "--", 
                "bash", 
                "-c", 
                cmd
            ])
        except Exception as e:
            print(f"Error launching XT16 driver: {e}")
    
    def start_slam_service(self, widget):
        """Start SLAM Service"""
        try:
            cmd = f'echo "Command: ssh -t unitree@{self.robot_ip} \'cd /unitree/module/unitree_slam/bin && ./unitree_slam\'"; echo ""; echo "🤖 Starting SLAM Service"; echo "=========================================="; echo "Robot: {self.robot_ip}"; echo "Service: unitree_slam"; echo "=========================================="; echo ""; echo "Connecting and starting SLAM service..."; echo ""; ssh -t unitree@{self.robot_ip} \'/bin/bash -c "source /opt/ros/foxy/setup.bash && export LD_LIBRARY_PATH=/usr/local/lib:/opt/ros/foxy/lib:$LD_LIBRARY_PATH && cd /unitree/module/unitree_slam/bin && ./unitree_slam"\'; exec bash'
            subprocess.Popen([
                "gnome-terminal", 
                "--title=SLAM Service", 
                "--", 
                "bash", 
                "-c", 
                cmd
            ])
        except Exception as e:
            print(f"Error launching SLAM service: {e}")
    
    def start_keydemo(self, widget):
        """Start KeyDemo for mapping control"""
        try:
            cmd = f'echo "Command: ssh -t unitree@{self.robot_ip} \'cd /unitree/module/unitree_slam/bin && ./keyDemo eth0\'"; echo ""; echo "🕹️ SLAM KeyDemo - Mapping Control"; echo "=========================================="; echo "Controls:"; echo "  q - Start mapping"; echo "  w - End mapping and save"; echo "  a - Start relocation"; echo "  s - Add pose to task list"; echo "  d - Execute task list"; echo "  f - Clear task list"; echo "  z - Pause navigation"; echo "  x - Resume navigation"; echo "=========================================="; echo ""; echo "Connecting and starting KeyDemo..."; echo ""; ssh -t unitree@{self.robot_ip} \'/bin/bash -c "source /opt/ros/foxy/setup.bash && export LD_LIBRARY_PATH=/usr/local/lib:/opt/ros/foxy/lib:$LD_LIBRARY_PATH && cd /unitree/module/unitree_slam/bin && ./keyDemo eth0"\'; exec bash'
            subprocess.Popen([
                "gnome-terminal", 
                "--title=SLAM KeyDemo - Mapping Control", 
                "--", 
                "bash", 
                "-c", 
                cmd
            ])
        except Exception as e:
            print(f"Error launching KeyDemo: {e}")
    
    def visualize_slam(self, widget, mode="mapping"):
        """Launch RViz2 to visualize XT16 SLAM data on laptop"""
        config_path = os.path.join(APP_DIR, f"hesai_xt16_{mode}.rviz")
        title = "Mapping" if mode == "mapping" else "Navigation/Relocation"
        window_title = f"XT16 SLAM {title} Visualization"
        try:
            subprocess.Popen([
                "gnome-terminal", 
                f"--title={window_title}", 
                "--", 
                "bash", 
                "-c", 
                f'echo "📊 XT16 SLAM {title} Visualization (RViz2)"; echo "=========================================="; echo "Config: Official Unitree {mode}.rviz"; echo "Lidar: XT16 (Hesai)"; echo "Robot: {self.robot_ip}"; echo "=========================================="; echo ""; echo "Starting RViz2..."; echo ""; source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && rviz2 -d "{config_path}"'
            ])
        except Exception as e:
            print(f"Error launching RViz2: {e}")
    
    def view_saved_maps(self, widget):
        """View saved maps on the robot"""
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=Saved SLAM Maps", 
                "--", 
                "bash", 
                "-c", 
                f'echo "🗺️ Saved SLAM Maps"; echo "=========================================="; echo "Location: /home/unitree/"; echo "=========================================="; echo ""; ssh unitree@{self.robot_ip} "cd /home/unitree && ls -lh *.pcd 2>/dev/null || echo \'No maps found. Create a map first!\'; echo \'\'; echo \'Press Enter to close...\'; read"'
            ])
        except Exception as e:
            print(f"Error viewing maps: {e}")
    
    def visualize_saved_maps(self, widget):
        """Visualize a saved PCD map"""
        try:
            subprocess.Popen([
                "gnome-terminal", 
                "--title=Visualize Saved Map", 
                "--", 
                "bash", 
                "-c", 
                f'''echo "🔍 Visualizing Saved SLAM Map"; echo "=========================================="; echo "Available maps:"; ssh unitree@{self.robot_ip} "cd /home/unitree && ls -lh *.pcd 2>/dev/null || echo 'No maps found!'"; echo ""; echo "Enter map filename (e.g., test.pcd) or press Enter for test.pcd:"; read MAP_NAME; if [ -z "$MAP_NAME" ]; then MAP_NAME="test.pcd"; fi; echo ""; echo "Downloading $MAP_NAME..."; scp unitree@{self.robot_ip}:/home/unitree/$MAP_NAME /tmp/saved_map.pcd && echo "Map downloaded to /tmp/saved_map.pcd"; echo ""; echo "Opening pcl_viewer..."; pcl_viewer /tmp/saved_map.pcd'''
            ])
        except Exception as e:
            print(f"Error visualizing saved map: {e}")
    
    def open_manual(self, widget):
        """Open the autonomous navigation manual"""
        manual_path = os.path.join(DESKTOP, "GO2W_Autonomous_Navigation_Manual.html")
        try:
            subprocess.Popen(["xdg-open", manual_path])
        except Exception as e:
            print(f"Error opening manual: {e}")
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()

class G1SlamMenu(Gtk.Window):
    def __init__(self, parent):
        Gtk.Window.__init__(self, title="G1 SLAM & Navigation")
        self.set_border_width(24)
        self.set_default_size(500, 650)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.override_background_color(Gtk.StateFlags.NORMAL, Gdk.RGBA(0.09, 0.11, 0.13, 1))
        self.parent = parent
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        vbox.set_homogeneous(False)
        self.add(vbox)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large" weight="bold" foreground="#00FFD0">🗺️ G1 SLAM & Navigation</span>')
        vbox.pack_start(title_label, False, False, 0)
        
        # Info label
        info_label = Gtk.Label()
        info_label.set_markup('<span size="small" foreground="#888888">Complete SLAM workflow for G1 autonomous navigation</span>')
        info_label.set_line_wrap(True)
        vbox.pack_start(info_label, False, False, 0)
        
        # Section 1: SLAM Mapping Control
        section1_label = Gtk.Label()
        section1_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">📡 SLAM Mapping</span>')
        section1_label.set_xalign(0)
        vbox.pack_start(section1_label, False, False, 10)
        
        # Grid for mapping buttons
        map_grid = Gtk.Grid()
        map_grid.set_row_spacing(8)
        map_grid.set_column_spacing(8)
        map_grid.set_column_homogeneous(True)
        
        start_map_btn = Gtk.Button(label="▶ Start Mapping")
        start_map_btn.set_size_request(0, 45)
        start_map_btn.get_style_context().add_class("suggested-action")
        start_map_btn.connect("clicked", self.start_mapping)
        map_grid.attach(start_map_btn, 0, 0, 1, 1)
        
        stop_map_btn = Gtk.Button(label="⏹ Stop Mapping")
        stop_map_btn.set_size_request(0, 45)
        stop_map_btn.get_style_context().add_class("destructive-action")
        stop_map_btn.connect("clicked", self.stop_mapping)
        map_grid.attach(stop_map_btn, 1, 0, 1, 1)
        
        save_map_btn = Gtk.Button(label="💾 Save Map")
        save_map_btn.set_size_request(0, 45)
        save_map_btn.connect("clicked", self.save_map)
        map_grid.attach(save_map_btn, 0, 1, 2, 1)
        
        vbox.pack_start(map_grid, False, False, 0)
        
        map_info = Gtk.Label()
        map_info.set_markup('<span size="small" foreground="#666666">Create and save SLAM maps for navigation</span>')
        map_info.set_xalign(0)
        vbox.pack_start(map_info, False, False, 0)
        
        # Remote keyDemo button (runs on robot)
        keydemo_btn = Gtk.Button(label="🎮 Run keyDemo on Robot")
        keydemo_btn.set_size_request(0, 45)
        keydemo_btn.connect("clicked", self.run_keydemo_on_robot)
        vbox.pack_start(keydemo_btn, False, False, 8)
        
        keydemo_info = Gtk.Label()
        keydemo_info.set_markup('<span size="small" foreground="#666666">Interactive SLAM control from robot terminal</span>')
        keydemo_info.set_xalign(0)
        vbox.pack_start(keydemo_info, False, False, 0)
        
        # Section 2: Relocation
        section2_label = Gtk.Label()
        section2_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">📍 Relocation</span>')
        section2_label.set_xalign(0)
        vbox.pack_start(section2_label, False, False, 10)
        
        reloc_btn = Gtk.Button(label="Start Relocation")
        reloc_btn.set_size_request(0, 50)
        reloc_btn.connect("clicked", self.start_relocation)
        vbox.pack_start(reloc_btn, False, False, 0)
        
        reloc_info = Gtk.Label()
        reloc_info.set_markup('<span size="small" foreground="#666666">Relocate robot in saved map</span>')
        reloc_info.set_xalign(0)
        vbox.pack_start(reloc_info, False, False, 0)
        
        # Section 3: Visualization
        section3_label = Gtk.Label()
        section3_label.set_markup('<span size="large" weight="bold" foreground="#00BFFF">🚀 Visualization Tools</span>')
        section3_label.set_xalign(0)
        vbox.pack_start(section3_label, False, False, 10)
        
        # Grid for visualization buttons
        viz_grid = Gtk.Grid()
        viz_grid.set_row_spacing(8)
        viz_grid.set_column_spacing(8)
        viz_grid.set_column_homogeneous(True)
        
        # Visualize Mapping button
        viz_map_btn = Gtk.Button(label="📊 Visualize Mapping")
        viz_map_btn.set_size_request(0, 45)
        viz_map_btn.connect("clicked", lambda w: self.visualize_slam(w, "mapping"))
        viz_grid.attach(viz_map_btn, 0, 0, 1, 1)
        
        # Visualize Relocation button
        viz_reloc_btn = Gtk.Button(label="📍 Visualize Relocation")
        viz_reloc_btn.set_size_request(0, 45)
        viz_reloc_btn.connect("clicked", lambda w: self.visualize_slam(w, "relocation"))
        viz_grid.attach(viz_reloc_btn, 1, 0, 1, 1)
        
        # Visualize Lidar button
        viz_lidar_btn = Gtk.Button(label="🔍 Visualize Lidar Stream")
        viz_lidar_btn.set_size_request(0, 45)
        viz_lidar_btn.connect("clicked", self.visualize_lidar)
        viz_grid.attach(viz_lidar_btn, 0, 1, 2, 1)
        
        vbox.pack_start(viz_grid, False, False, 0)
        
        # Return button
        return_btn = Gtk.Button(label="Return")
        return_btn.set_size_request(0, 40)
        return_btn.connect("clicked", self.on_return)
        vbox.pack_start(return_btn, False, False, 10)
    
    def send_slam_command(self, command_type, action):
        """Send SLAM command via ROS2 topic API"""
        print(f"DEBUG: send_slam_command called with command_type={command_type}, action={action}")
        import json
        robot_ip = "192.168.123.164"
        
        # Build JSON command based on official Unitree API format
        # According to documentation: api-id 1801=start mapping, 1802=end mapping, 1804=initialize pose
        if command_type == "mapping":
            if action == "start":
                # API ID 1801: Start mapping with slam_type="indoor"
                cmd_json = json.dumps({"data": {"slam_type": "indoor"}})
                api_id = 1801
            elif action == "stop":
                # API ID 1802: End mapping (save map)
                # Default save address, user can modify if needed
                cmd_json = json.dumps({"data": {"address": "/home/unitree/test.pcd"}})
                api_id = 1802
            elif action == "save":
                # Same as stop mapping - saves the map
                cmd_json = json.dumps({"data": {"address": "/home/unitree/test.pcd"}})
                api_id = 1802
        elif command_type == "relocation":
            # For relocation, we need initialize pose (api_id 1804)
            # But this requires loading a map first, so we'll use a default
            cmd_json = json.dumps({"data": {
                "x": 0.0, "y": 0.0, "z": 0.0,
                "q_x": 0.0, "q_y": 0.0, "q_z": 0.0, "q_w": 1.0,
                "address": "/home/unitree/test.pcd"
            }})
            api_id = 1804
        else:
            return
        
        # Create Python script to publish command
        script = f'''#!/usr/bin/env python3
# API ID: {api_id}
import rclpy
from rclpy.node import Node
from unitree_api.msg import Request
from unitree_api.msg import Response
import json
import sys

class SlamCommandPublisher(Node):
    def __init__(self):
        super().__init__('g1_slam_command_publisher')
        self.publisher = self.create_publisher(Request, '/api/slam_operate/request', 10)
        self.subscription = self.create_subscription(Response, '/api/slam_operate/response', self.response_callback, 10)
        self.response_received = False
        self.response_data = None
        self.expected_request_id = None
        
        # Give subscription time to connect
        import time
        time.sleep(0.5)
        for _ in range(5):
            rclpy.spin_once(self, timeout_sec=0.1)
        
    def response_callback(self, msg):
        # Check if this response matches our request
        if self.expected_request_id is None or msg.header.identity.id == self.expected_request_id:
            self.response_data = msg
            self.response_received = True
        
    def send_command(self, cmd_json):
        import random
        import time as time_module
        
        # Generate unique request ID
        self.expected_request_id = int(time_module.time() * 1000) + random.randint(1000, 9999)
        
        msg = Request()
        msg.header.identity.id = self.expected_request_id
        msg.header.identity.api_id = {api_id}  # Use correct API ID ({api_id})
        msg.header.lease.id = 1
        msg.header.policy.priority = 0
        msg.header.policy.noreply = False
        msg.parameter = cmd_json
        
        print(f"Sending command: {{cmd_json}}")
        
        # Reset response flag
        self.response_received = False
        self.response_data = None
        
        self.publisher.publish(msg)
        print("Command sent. Waiting for response...")
        
        # Wait for response (timeout after 10 seconds)
        import time
        start_time = time.time()
        timeout = 10.0
        while not self.response_received and (time.time() - start_time) < timeout:
            rclpy.spin_once(self, timeout_sec=0.1)
        
        if self.response_received and self.response_data:
            response_data = self.response_data.data
            response_code = self.response_data.header.status.code
            
            # Try to parse as JSON first
            try:
                response_json = json.loads(response_data)
                print("Response: " + json.dumps(response_json, indent=2))
                if response_json.get('succeed'):
                    print("✅ Command succeeded!")
                elif 'errorCode' in response_json:
                    if response_json.get('errorCode') == 0:
                        print("✅ Command succeeded!")
                    else:
                        error_msg = response_json.get('info', 'Unknown error')
                        print(f"❌ Command failed: {{error_msg}}")
                else:
                    print("✅ Command accepted")
            except json.JSONDecodeError:
                # Not JSON - check response code instead
                if response_code == 0:
                    print("✅ Command succeeded!")
                else:
                    print(f"⚠️ Response code: {{response_code}}")
        else:
            print("⚠️ No response received (timeout or error)")
            print("This might mean:")
            print("  1. The robot is not running SLAM services")
            print("  2. DDS domain/network configuration issue")
            print("  3. The command format might be incorrect")
            print("  4. Check /slam_info topic for status")

def main():
    rclpy.init()
    node = SlamCommandPublisher()
    node.send_command({repr(cmd_json)})
    rclpy.shutdown()

if __name__ == '__main__':
    main()
'''
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as tmp_script:
                tmp_script.write(script)
                script_path = tmp_script.name
            
            subprocess.run(["chmod", "+x", script_path])
            
            cmd = f'echo "Command: python3 {script_path}"; echo ""; echo "🤖 G1 SLAM Command ({action.title()} {command_type})"; echo "=========================================="; echo "Robot: {robot_ip}"; echo "API: /api/slam_operate"; echo "=========================================="; echo ""; source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && python3 "{script_path}"; echo ""; echo "Press Enter to close..."; read'
            
            print(f"DEBUG: About to launch terminal with command: {cmd[:100]}...")
            print(f"DEBUG: Script path: {script_path}")
            
            try:
                result = subprocess.Popen([
                    "gnome-terminal",
                    f"--title=G1 SLAM {action.title()} {command_type.title()}",
                    "--",
                    "bash",
                    "-c",
                    cmd
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"DEBUG: Terminal launch attempted, PID: {result.pid}")
            except FileNotFoundError:
                error_dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="gnome-terminal not found"
                )
                error_dialog.format_secondary_text("Please install gnome-terminal or use a different terminal emulator")
                error_dialog.run()
                error_dialog.destroy()
                return
            
            # Give it a moment and check if it started
            import time
            time.sleep(0.5)
            if result.poll() is not None and result.returncode != 0:
                error_dialog = Gtk.MessageDialog(
                    parent=self,
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text=f"Error launching SLAM command terminal"
                )
                error_dialog.format_secondary_text(f"Failed to open terminal. Return code: {result.returncode}")
                error_dialog.run()
                error_dialog.destroy()
            
        except Exception as e:
            import traceback
            error_msg = f"Error sending SLAM command: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            error_dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error sending SLAM command"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def start_mapping(self, widget):
        """Start SLAM mapping"""
        try:
            self.send_slam_command("mapping", "start")
        except Exception as e:
            print(f"DEBUG: Exception in start_mapping: {e}")
            import traceback
            traceback.print_exc()
            error_dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error starting mapping"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def stop_mapping(self, widget):
        """Stop SLAM mapping"""
        print("DEBUG: stop_mapping called")
        try:
            self.send_slam_command("mapping", "stop")
        except Exception as e:
            print(f"DEBUG: Exception in stop_mapping: {e}")
            import traceback
            traceback.print_exc()
    
    def save_map(self, widget):
        """Save current map"""
        print("DEBUG: save_map called")
        try:
            self.send_slam_command("mapping", "save")
        except Exception as e:
            print(f"DEBUG: Exception in save_map: {e}")
            import traceback
            traceback.print_exc()
    
    def start_relocation(self, widget):
        """Start relocation in saved map"""
        try:
            self.send_slam_command("relocation", "start")
        except Exception as e:
            print(f"DEBUG: Exception in start_relocation: {e}")
            import traceback
            traceback.print_exc()
    
    def visualize_slam(self, widget, mode="mapping"):
        """Launch RViz2 to visualize G1 SLAM data"""
        config_path = os.path.join(APP_DIR, f"g1_slam_{mode}.rviz")
        title = "Mapping" if mode == "mapping" else "Relocation"
        window_title = f"G1 SLAM {title} Visualization"
        try:
            # Publish a static transform to correct for inverted lidar mounting per Unitree documentation
            # Documentation states: lidar is inverted, position relative to robot: (-0.0, 0.0, -0.47618), pitch: -2.3°
            # 180° rotation around X axis (quaternion: 1,0,0,0) corrects for inverted mounting
            # Z translation: -1.25m (translate down from lidar at 125cm to ground level at 0cm)
            # From map (lidar frame, inverted) to map_corrected (corrected orientation at ground level)
            transform_cmd = 'source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && ros2 run tf2_ros static_transform_publisher 0 0 -1.25 1 0 0 0 map map_corrected > /dev/null 2>&1 &'
            
            cmd = f'''{transform_cmd}
sleep 0.5
echo "📊 G1 SLAM {title} Visualization (RViz2)"
echo "=========================================="
echo "Lidar: Livox MID360 (inverted mount)"
echo "Robot: 192.168.123.164"
echo "Topic: /unitree/slam_{mode}/points"
echo "Transform: map -> map_corrected (fixing inverted coordinates)"
echo "=========================================="
echo ""
echo "Starting RViz2..."
echo ""
source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && rviz2 -d "{config_path}"
exec bash'''
            
            subprocess.Popen([
                "gnome-terminal",
                f"--title={window_title}",
                "--",
                "bash",
                "-c",
                cmd
            ])
        except Exception as e:
            print(f"Error launching RViz2: {e}")
    
    def run_keydemo_on_robot(self, widget):
        """SSH to robot and run keyDemo for interactive SLAM control"""
        robot_ip = "192.168.123.164"
        # keyDemo typically runs with eth0 as network interface (network segment 123)
        # The user can change this if needed, but eth0 is standard for robot's wired connection
        network_interface = "eth0"
        
        try:
            cmd = f'''echo "🎮 G1 SLAM keyDemo (Robot Terminal)"
echo "=========================================="
echo "Robot: {robot_ip}"
echo "Program: keyDemo"
echo "Interface: {network_interface}"
echo "=========================================="
echo ""
echo "SSH connection..."
echo ""
echo "Command: ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_slam_example/build && ./keyDemo {network_interface}'"
echo ""
ssh -t unitree@{robot_ip} 'cd /home/unitree/unitree_slam_example/build && ./keyDemo {network_interface}'
exec bash'''
            
            subprocess.Popen([
                "gnome-terminal",
                "--title=G1 keyDemo (Robot)",
                "--",
                "bash",
                "-c",
                cmd
            ])
        except Exception as e:
            print(f"Error launching keyDemo on robot: {e}")
            error_dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.OK,
                text="Error launching keyDemo"
            )
            error_dialog.format_secondary_text(str(e))
            error_dialog.run()
            error_dialog.destroy()
    
    def visualize_lidar(self, widget):
        """Launch RViz2 with G1 lidar visualization"""
        config_path = os.path.join(APP_DIR, "g1_lidar.rviz")
        try:
            # Publish a static transform to correct for inverted lidar mounting
            # 180° rotation around X axis (quaternion: 1,0,0,0) corrects for inverted mounting
            # Z translation: +1.25m (raw lidar frame needs positive translation to reach ground level)
            # From livox_frame (raw lidar frame, inverted) to livox_frame_corrected (corrected orientation)
            transform_cmd = 'source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && ros2 run tf2_ros static_transform_publisher 0 0 1.25 1 0 0 0 livox_frame livox_frame_corrected > /dev/null 2>&1 &'
            
            cmd = f'''{transform_cmd}
sleep 0.5
echo "🔍 G1 Lidar Visualization (RViz2)"
echo "=========================================="
echo "Lidar: Livox MID360 (inverted mount)"
echo "Robot: 192.168.123.164"
echo "Topic: /utlidar/cloud_livox_mid360"
echo "Transform: livox_frame -> livox_frame_corrected (fixing inverted coordinates)"
echo "=========================================="
echo ""
echo "Starting RViz2..."
echo ""
source /opt/ros/humble/setup.bash && source ~/unitree_ros2/cyclonedds_ws/install/setup.bash && source ~/unitree_ros2/setup.sh && rviz2 -d "{config_path}"
exec bash'''
            
            subprocess.Popen([
                "gnome-terminal",
                "--title=G1 Lidar Visualization",
                "--",
                "bash",
                "-c",
                cmd
            ])
        except Exception as e:
            print(f"Error launching RViz2: {e}")
    
    def on_return(self, widget):
        self.destroy()
        self.parent.show_all()

def main():
    apply_css()
    win = MainMenu()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main() 
