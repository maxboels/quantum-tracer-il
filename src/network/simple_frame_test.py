#!/usr/bin/env python3
"""
Simple Camera Frame Test Client (Raspberry Pi)
==============================================
Tests sending camera frames to laptop test server.
"""

import socket
import time
import json
import struct
import cv2
import numpy as np

def test_basic_connection(server_ip, server_port=8889):
    """Test basic socket connection with simple message"""
    print(f"🔗 Testing basic connection to {server_ip}:{server_port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((server_ip, server_port))
        
        # Send a simple test message
        test_msg = {
            "test": "hello from raspberry pi", 
            "timestamp": time.time(),
            "pi_ip": "192.168.1.111"
        }
        msg_data = json.dumps(test_msg).encode()
        
        # Send length as big-endian 4-byte integer (to match server)
        sock.send(len(msg_data).to_bytes(4, byteorder='big'))
        sock.send(msg_data)
        
        # Wait for response
        response_length_bytes = sock.recv(4)
        if response_length_bytes:
            response_length = int.from_bytes(response_length_bytes, byteorder='big')
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode())
            print(f"✅ Received response: {response}")
            sock.close()
            return True
        else:
            print("❌ No response received")
            sock.close()
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_camera():
    """Test camera capture"""
    print("📷 Testing camera...")
    
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return False
            
        ret, frame = cap.read()
        if ret:
            print(f"✅ Camera OK: {frame.shape}")
            cap.release()
            return True
        else:
            print("❌ Cannot read from camera")
            cap.release()
            return False
            
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_frame_sending(server_ip, server_port=8889):
    """Test sending camera frames to server"""
    print(f"📸 Testing frame sending to {server_ip}:{server_port}...")
    
    # Capture a test frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Could not capture frame")
        return False
    
    try:
        # Resize frame to reduce bandwidth
        small_frame = cv2.resize(frame, (320, 240))
        
        # Encode frame as JPEG
        _, encoded_frame = cv2.imencode('.jpg', small_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_data = encoded_frame.tobytes()
        
        print(f"   Frame size: {len(frame_data)} bytes")
        
        # Connect and send frame
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15.0)  # Longer timeout for frame transfer
        sock.connect((server_ip, server_port))
        
        # Send frame data (server expects raw bytes for frames)
        sock.send(len(frame_data).to_bytes(4, byteorder='big'))
        sock.send(frame_data)
        
        # Wait for response with longer timeout
        sock.settimeout(10.0)
        try:
            response_length_bytes = sock.recv(4)
            if response_length_bytes and len(response_length_bytes) == 4:
                response_length = int.from_bytes(response_length_bytes, byteorder='big')
                response_data = sock.recv(response_length)
                if response_data:
                    response = response_data.decode('utf-8')
                    print(f"✅ Server response: {response}")
                    sock.close()
                    return True
                else:
                    print("❌ Empty response from server")
            else:
                print("❌ Invalid response length from server")
        except socket.timeout:
            print("❌ Timeout waiting for response")
        except Exception as e:
            print(f"❌ Error receiving response: {e}")
        
        sock.close()
        return False
            
    except Exception as e:
        print(f"❌ Frame sending failed: {e}")
        return False

def main():
    print("🧪 Camera Frame Test - Raspberry Pi Client")
    print("=" * 50)
    
    # Get server IP
    server_ip = input("Enter your laptop's IP address (192.168.1.33): ").strip()
    if not server_ip:
        server_ip = "192.168.1.33"
    
    print(f"🎯 Target server: {server_ip}:8889")
    print()
    
    # Test 1: Basic connection
    print("TEST 1: Basic Connection")
    if not test_basic_connection(server_ip):
        print("❌ Basic connection failed!")
        return
    print("✅ Basic connection OK\n")
    
    # Test 2: Camera
    print("TEST 2: Camera")
    if not test_camera():
        print("❌ Camera test failed!")
        return
    print("✅ Camera test OK\n")
    
    # Test 3: Frame sending
    print("TEST 3: Frame Sending")
    if test_frame_sending(server_ip):
        print("✅ Frame sending OK")
        print("\n🎉 All tests passed! Your network setup is working!")
    else:
        print("❌ Frame sending failed")

if __name__ == '__main__':
    main()