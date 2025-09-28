#!/usr/bin/env python3
"""
Network Setup and Testing Script
================================

Sets up and tests the networked remote inference system.

Usage:
    # On Raspberry Pi (test client functionality)
    python3 network_setup.py --mode client --server-ip 192.168.1.100

    # On Laptop (test server functionality)  
    python3 network_setup.py --mode server --port 8888

    # Network connectivity test
    python3 network_setup.py --mode test --target-ip 192.168.1.100
"""

import argparse
import socket
import time
import threading
import json
import struct
import numpy as np
import cv2
import subprocess
import sys
from typing import Optional

def get_local_ip() -> str:
    """Get local IP address"""
    try:
        # Connect to a remote server to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def test_network_connectivity(target_ip: str, port: int = 8888) -> bool:
    """Test network connectivity to target"""
    print(f"🔍 Testing connectivity to {target_ip}:{port}...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            result = s.connect_ex((target_ip, port))
            if result == 0:
                print(f"✅ Connection successful!")
                return True
            else:
                print(f"❌ Connection failed (error code: {result})")
                return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_bandwidth(target_ip: str, port: int = 8889, duration: int = 10) -> dict:
    """Test network bandwidth with dummy data"""
    print(f"📊 Testing bandwidth to {target_ip}:{port} for {duration}s...")
    
    # Simple bandwidth test
    try:
        # Create test data (simulating camera frame)
        test_frame = np.random.randint(0, 255, (240, 320, 3), dtype=np.uint8)
        _, encoded = cv2.imencode('.jpg', test_frame)
        frame_data = encoded.tobytes()
        
        bytes_sent = 0
        frames_sent = 0
        start_time = time.time()
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5.0)
            s.connect((target_ip, port))
            
            while time.time() - start_time < duration:
                try:
                    s.send(frame_data)
                    bytes_sent += len(frame_data)
                    frames_sent += 1
                    time.sleep(0.033)  # ~30 FPS
                except Exception:
                    break
        
        elapsed = time.time() - start_time
        bandwidth_mbps = (bytes_sent * 8) / (elapsed * 1000000)  # Mbps
        fps = frames_sent / elapsed
        
        results = {
            'bytes_sent': bytes_sent,
            'frames_sent': frames_sent,
            'elapsed_time': elapsed,
            'bandwidth_mbps': bandwidth_mbps,
            'fps': fps
        }
        
        print(f"📈 Bandwidth Test Results:")
        print(f"   Data sent: {bytes_sent / 1024 / 1024:.1f} MB")
        print(f"   Frames sent: {frames_sent}")
        print(f"   Bandwidth: {bandwidth_mbps:.2f} Mbps")
        print(f"   Frame rate: {fps:.1f} FPS")
        
        return results
        
    except Exception as e:
        print(f"❌ Bandwidth test failed: {e}")
        return {}

def setup_wifi_raspberry_pi():
    """Help setup WiFi on Raspberry Pi"""
    print("🔧 WiFi Setup for Raspberry Pi")
    print("=" * 40)
    
    try:
        # Get current IP
        local_ip = get_local_ip()
        print(f"Current IP: {local_ip}")
        
        # Show network interfaces
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\nNetwork Interfaces:")
            print(result.stdout)
        
        # Show WiFi status
        result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        if result.returncode == 0:
            print("\nWiFi Status:")
            print(result.stdout)
            
    except Exception as e:
        print(f"Error checking network status: {e}")

def test_camera():
    """Test camera functionality"""
    print("📹 Testing Camera...")
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Camera not available")
            return False
        
        # Test capture
        ret, frame = cap.read()
        if ret:
            print(f"✅ Camera OK: {frame.shape}")
            
            # Test encoding (for network transmission)
            _, encoded = cv2.imencode('.jpg', frame)
            compressed_size = len(encoded)
            compression_ratio = compressed_size / (frame.shape[0] * frame.shape[1] * frame.shape[2])
            
            print(f"   Original size: {frame.nbytes} bytes")
            print(f"   Compressed size: {compressed_size} bytes")
            print(f"   Compression ratio: {compression_ratio:.3f}")
            
            cap.release()
            return True
        else:
            print("❌ Camera capture failed")
            cap.release()
            return False
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_arduino_connection(port: str = '/dev/ttyACM0'):
    """Test Arduino connection"""
    print(f"🤖 Testing Arduino connection on {port}...")
    
    try:
        import serial
        
        with serial.Serial(port, 115200, timeout=2) as ser:
            time.sleep(2)  # Arduino reset
            
            # Look for Arduino ready signal
            ready_received = False
            for _ in range(10):
                line = ser.readline().decode('utf-8').strip()
                if line == "ARDUINO_READY":
                    ready_received = True
                    break
                elif line.startswith("DATA,"):
                    print(f"   Data sample: {line}")
            
            if ready_received:
                print("✅ Arduino communication OK")
                
                # Test control command
                ser.write(b"STATUS\n")
                response = ser.readline().decode('utf-8').strip()
                print(f"   Status response: {response}")
                
                return True
            else:
                print("❌ Arduino ready signal not received")
                return False
                
    except ImportError:
        print("❌ pyserial not installed: pip install pyserial")
        return False
    except Exception as e:
        print(f"❌ Arduino test failed: {e}")
        return False

def run_client_tests(server_ip: str, port: int = 8888):
    """Run client-side tests"""
    print("🖥️  Running Client-Side Tests (Raspberry Pi)")
    print("=" * 50)
    
    # 1. Network setup
    setup_wifi_raspberry_pi()
    print()
    
    # 2. Hardware tests
    camera_ok = test_camera()
    arduino_ok = test_arduino_connection()
    print()
    
    # 3. Network connectivity
    network_ok = test_network_connectivity(server_ip, port)
    print()
    
    # 4. Summary
    print("📋 Test Summary:")
    print(f"   Camera: {'✅' if camera_ok else '❌'}")
    print(f"   Arduino: {'✅' if arduino_ok else '❌'}")
    print(f"   Network: {'✅' if network_ok else '❌'}")
    
    if camera_ok and arduino_ok and network_ok:
        print("\n🎉 Client setup complete! Ready for remote inference.")
        print(f"\n🚀 To start autonomous driving:")
        print(f"   python3 src/network/remote_inference_client.py --server-ip {server_ip}")
    else:
        print("\n⚠️  Some tests failed. Please fix issues before proceeding.")

def run_server_tests(port: int = 8888):
    """Run server-side tests"""
    print("💻 Running Server-Side Tests (Laptop)")
    print("=" * 40)
    
    local_ip = get_local_ip()
    print(f"Server will run on: {local_ip}:{port}")
    
    # Test PyTorch availability
    try:
        import torch
        print(f"✅ PyTorch available: {torch.__version__}")
        if torch.cuda.is_available():
            print(f"✅ CUDA available: {torch.cuda.get_device_name()}")
        else:
            print("⚠️  CUDA not available - will use CPU")
    except ImportError:
        print("❌ PyTorch not installed")
        print("   Install with: pip install torch torchvision")
    
    # Test OpenCV
    try:
        print(f"✅ OpenCV available: {cv2.__version__}")
    except:
        print("❌ OpenCV not available")
        print("   Install with: pip install opencv-python")
    
    print(f"\n🚀 To start inference server:")
    print(f"   python3 src/network/remote_inference_server.py --port {port}")
    print(f"\n📱 Clients should connect to: {local_ip}:{port}")

def main():
    parser = argparse.ArgumentParser(description='Network Setup and Testing')
    parser.add_argument('--mode', choices=['client', 'server', 'test'], required=True,
                        help='Test mode: client (Pi), server (laptop), or test (connectivity)')
    parser.add_argument('--server-ip', type=str, help='Server IP address (for client mode)')
    parser.add_argument('--target-ip', type=str, help='Target IP for connectivity test')
    parser.add_argument('--port', type=int, default=8888, help='Server port')
    
    args = parser.parse_args()
    
    print("🌐 RC Car Remote Inference - Network Setup")
    print("=" * 50)
    
    if args.mode == 'client':
        if not args.server_ip:
            print("Error: --server-ip required for client mode")
            sys.exit(1)
        run_client_tests(args.server_ip, args.port)
        
    elif args.mode == 'server':
        run_server_tests(args.port)
        
    elif args.mode == 'test':
        target_ip = args.target_ip or args.server_ip
        if not target_ip:
            print("Error: --target-ip or --server-ip required for test mode")
            sys.exit(1)
        test_network_connectivity(target_ip, args.port)

if __name__ == '__main__':
    main()