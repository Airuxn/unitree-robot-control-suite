#!/usr/bin/env python3
"""
Unitree Camera Viewer using SDK2
Based on official Unitree example
"""

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.video.video_client import VideoClient
import cv2
import numpy as np
import sys


def main():
    print("=" * 50)
    print("🎥 Unitree Camera Viewer")
    print("=" * 50)
    print("Press ESC to quit")
    print()
    
    # Initialize the channel with network interface if provided
    if len(sys.argv) > 1:
        network_interface = sys.argv[1]
        print(f"Using network interface: {network_interface}")
        ChannelFactoryInitialize(0, network_interface)
    else:
        print("Using default network interface")
        ChannelFactoryInitialize(0)

    # Create and initialize video client
    client = VideoClient()
    client.SetTimeout(3.0)
    client.Init()
    
    print("Connecting to camera...")
    code, data = client.GetImageSample()

    if code != 0:
        print(f"❌ Failed to connect to camera. Error code: {code}")
        print("Make sure you are connected to the robot!")
        return

    print("✅ Camera connected! Displaying video stream...")
    print()
    
    # Create resizable window once outside the loop
    cv2.namedWindow("Unitree Front Camera", cv2.WINDOW_NORMAL)

    # Request normal when code==0
    while code == 0:
        # Check if window is still open first
        try:
            prop = cv2.getWindowProperty("Unitree Front Camera", 1)
            if prop < 0:
                print("\nWindow closed by user")
                break
        except:
            print("\nWindow closed")
            break
        
        # Get Image data from robot
        code, data = client.GetImageSample()

        if code == 0:
            # Convert to numpy image
            image_data = np.frombuffer(bytes(data), dtype=np.uint8)
            image = cv2.imdecode(image_data, cv2.IMREAD_COLOR)

            if image is not None:
                # Display image in the window
                cv2.imshow("Unitree Front Camera", image)
                
                # Press ESC to stop
                key = cv2.waitKey(20) & 0xFF
                if key == 27:
                    print("\nClosing camera viewer...")
                    break
            else:
                print("Warning: Failed to decode image")

    if code != 0:
        print(f"\n❌ Error getting image sample. Code: {code}")

    cv2.destroyAllWindows()
    print("Camera viewer closed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        cv2.destroyAllWindows()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        cv2.destroyAllWindows()

