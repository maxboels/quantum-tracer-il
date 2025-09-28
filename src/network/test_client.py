#!/usr/bin/envdef test_connection(server_ip, server_port=8889):
    """Test basic socket connection"""
    print(f"🔗 Testing connection to {server_ip}:{server_port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((server_ip, server_port))
        
        # Send a simple test message
        test_msg = {"test": "hello from raspberry pi", "timestamp": time.time()}
        msg_data = json.dumps(test_msg).encode()
        
        # Send length as big-endian 4-byte integer (to match server)
        sock.send(len(msg_data).to_bytes(4, byteorder='big'))
        sock.send(msg_data)mple Network Test Client (Raspberry Pi)
=========================================
Tests basic network communication before running the full inference system.
"""

import socket
import json
import time
import cv2
import numpy as np
import struct

def test_connection(server_ip, server_port=8889):
    """Test basic socket connection"""
    print(f"🔗 Testing connection to {server_ip}:{server_port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((server_ip, server_port))
        
        # Send a simple test message
        test_msg = {"test": "hello from raspberry pi", "timestamp": time.time()}
        msg_data = json.dumps(test_msg).encode()
        
        sock.send(struct.pack('I', len(msg_data)))
        sock.send(msg_data)
        
        # Wait for response
        response_size = struct.unpack('I', sock.recv(4))[0]
        response_data = sock.recv(response_size)
        response = json.loads(response_data.decode())
        
        print(f"✅ Connection successful!")
        print(f"📨 Server response: {response}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_camera():
    """Test camera capture"""
    print("📷 Testing camera...")
    
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        
        if ret:
            print(f"✅ Camera OK: {frame.shape}")
            cap.release()
            return True
        else:
            print("❌ Camera capture failed")
            cap.release()
            return False
            
    except Exception as e:
        print(f"❌ Camera error: {e}")
        return False

def test_frame_sending(server_ip, server_port=8889):
    """Test sending a camera frame"""
    print(f"📸 Testing frame sending to {server_ip}:{server_port}...")
    
    # Capture a test frame
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        print("❌ Could not capture test frame")
        return False
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((server_ip, server_port))
        
        # Encode frame as JPEG
        _, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_data = encoded_frame.tobytes()
        
        # Create test message
        message = {
            'test_frame': True,
            'timestamp': time.time(),
            'frame_size': len(frame_data),
            'sensor_data': {
                'steering_current': 0.0,
                'throttle_current': 0.0,
                'arduino_timestamp': int(time.time() * 1000)
            }
        }
        
        # Send header
        header = json.dumps(message).encode()
        sock.send(struct.pack('I', len(header)))
        sock.send(header)
        sock.send(frame_data)
        
        print(f"📤 Sent frame: {frame.shape}, {len(frame_data)} bytes")
        
        # Wait for response
        response_size = struct.unpack('I', sock.recv(4))[0]
        response_data = sock.recv(response_size)
        response = json.loads(response_data.decode())
        
        print(f"📥 Server response: {response}")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Frame sending failed: {e}")
        return False

def main():
    import sys
    
    print("🧪 Network Communication Test - Raspberry Pi Client")
    print("=" * 50)
    
    # Get server IP from command line or user input
    if len(sys.argv) > 1:
        server_ip = sys.argv[1].strip()
        print(f"Using IP from command line: {server_ip}")
    else:
        server_ip = input("Enter your laptop's IP address: ").strip()
        if not server_ip:
            print("❌ No IP address provided")
            return
    
    print(f"🎯 Target server: {server_ip}:8889")
    print("📍 Pi IP address:", socket.gethostbyname(socket.gethostname()))
    print()
    
    # Test 1: Basic connection
    print("TEST 1: Basic Connection")
    if not test_connection(server_ip):
        print("❌ Basic connection failed. Make sure server is running!")
        return
    print()
    
    # Test 2: Camera
    print("TEST 2: Camera")
    if not test_camera():
        print("❌ Camera test failed. Check camera connection!")
        return
    print()
    
    # Test 3: Frame sending
    print("TEST 3: Frame Sending")
    if test_frame_sending(server_ip):
        print("✅ All tests passed! Ready for remote inference.")
    else:
        print("❌ Frame sending failed.")

if __name__ == '__main__':
    main()