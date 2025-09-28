#!/usr/bin/env python3
"""
Fixed Network Test Client (Raspberry Pi)
========================================
Tests basic network communication with improved reliability for large data transfers.
"""

import socket
import json
import time
import cv2
import numpy as np
import struct

def send_all(sock, data):
    """Send all data reliably"""
    bytes_sent = 0
    total_bytes = len(data)
    
    while bytes_sent < total_bytes:
        try:
            sent = sock.send(data[bytes_sent:])
            if sent == 0:
                raise RuntimeError("Socket connection broken")
            bytes_sent += sent
            
            # Show progress for large transfers
            if total_bytes > 10000 and bytes_sent % 50000 == 0:
                progress = (bytes_sent / total_bytes) * 100
                print(f"   📤 Sent: {bytes_sent}/{total_bytes} bytes ({progress:.1f}%)")
                
        except Exception as e:
            print(f"❌ Error sending data: {e}")
            return False
    
    return True

def test_connection(server_ip, server_port=8889):
    """Test basic socket connection"""
    print(f"🔗 Testing connection to {server_ip}:{server_port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)  # Longer timeout
        
        # Increase socket buffer sizes
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
        
        sock.connect((server_ip, server_port))
        
        # Send a simple test message
        test_msg = {"test": "hello from raspberry pi", "timestamp": time.time()}
        msg_data = json.dumps(test_msg).encode()
        
        # Send length as big-endian 4-byte integer (to match server)
        length_bytes = len(msg_data).to_bytes(4, byteorder='big')
        
        if not send_all(sock, length_bytes):
            print("❌ Failed to send message length")
            return False
            
        if not send_all(sock, msg_data):
            print("❌ Failed to send message data")
            return False
        
        print("✅ Message sent successfully")
        
        # Wait for response
        try:
            response_length_data = sock.recv(4)
            if len(response_length_data) != 4:
                print("❌ Invalid response length data")
                return False
                
            response_length = int.from_bytes(response_length_data, byteorder='big')
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode())
            print(f"✅ Server response: {response.get('message', 'No message')}")
            sock.close()
            return True
        except socket.timeout:
            print("⏰ Timeout waiting for response")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_camera():
    """Test camera capture"""
    print("📷 Testing camera...")
    
    try:
        cap = cv2.VideoCapture(0)
        
        # Set camera properties for smaller image
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            print(f"✅ Camera working: {frame.shape}")
            return frame
        else:
            print("❌ Camera failed to capture")
            return None
            
    except Exception as e:
        print(f"❌ Camera error: {e}")
        return None

def test_frame_sending(server_ip, frame, server_port=8889):
    """Test sending a camera frame"""
    print(f"📸 Testing frame sending to {server_ip}:{server_port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30.0)  # Longer timeout for large data
        
        # Increase socket buffer sizes
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
        
        sock.connect((server_ip, server_port))
        print("✅ Connected to server")
        
        # Resize frame to standard resolution
        resized_frame = cv2.resize(frame, (640, 480))  # Standard VGA resolution
        
        # Encode frame as JPEG with high compression
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 60]  # Lower quality = smaller size
        success, encoded_frame = cv2.imencode('.jpg', resized_frame, encode_params)
        
        if not success:
            print("❌ Failed to encode frame")
            return False
            
        frame_data = encoded_frame.tobytes()
        print(f"   Frame size: {len(frame_data)} bytes (resized to {resized_frame.shape})")
        
        # Send frame length
        length_bytes = len(frame_data).to_bytes(4, byteorder='big')
        if not send_all(sock, length_bytes):
            print("❌ Failed to send frame length")
            return False
        
        print("✅ Frame length sent")
        
        # Send frame data
        if not send_all(sock, frame_data):
            print("❌ Failed to send frame data")
            return False
        
        print("✅ Frame data sent successfully")
        
        # Wait for response
        try:
            response_length_data = sock.recv(4)
            if len(response_length_data) != 4:
                print("❌ Invalid response length")
                return False
                
            response_length = int.from_bytes(response_length_data, byteorder='big')
            print(f"📥 Response length: {response_length}")
            
            response_data = sock.recv(response_length)
            response_text = response_data.decode()
            print(f"✅ Server response: {response_text}")
            sock.close()
            return True
            
        except socket.timeout:
            print("⏰ Timeout waiting for frame response")
            return False
        
    except Exception as e:
        print(f"❌ Frame sending failed: {e}")
        return False

def main():
    print("🧪 Fixed Network Communication Test - Raspberry Pi Client")
    print("=" * 55)
    
    # Get server IP from user
    server_ip = input("Enter your laptop's IP address (192.168.1.33): ").strip()
    if not server_ip:
        server_ip = "192.168.1.33"  # Default to your laptop's IP
    
    print(f"🎯 Target server: {server_ip}:8889")
    print("📍 Pi IP address:", socket.gethostbyname(socket.gethostname()))
    print()
    
    # Test 1: Basic connection
    print("TEST 1: Basic Connection")
    print("-" * 25)
    if not test_connection(server_ip):
        print("❌ Basic connection failed - check server is running")
        return
    print("✅ Basic connection test PASSED")
    print()
    
    # Test 2: Camera
    print("TEST 2: Camera")
    print("-" * 15)
    test_frame = test_camera()
    if test_frame is None:
        print("❌ Camera test failed")
        return
    print("✅ Camera test PASSED")
    print()
    
    # Test 3: Frame sending
    print("TEST 3: Frame Sending")
    print("-" * 20)
    if test_frame_sending(server_ip, test_frame):
        print("✅ Frame sending test PASSED")
        print()
        print("🎉 ALL TESTS PASSED! Network communication is working.")
        print("🚀 You can now run the full remote inference system.")
    else:
        print("❌ Frame sending test FAILED")

if __name__ == '__main__':
    main()