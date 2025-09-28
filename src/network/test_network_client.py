#!/usr/bin/env python3
"""
Simple Network Test Client (Raspberry Pi Side)
==============================================

This script tests basic network communication by sending simple messages
to your laptop to verify the connection works before testing the full system.

Usage:
    python3 test_network_client.py --server-ip 192.168.1.XXX
"""

import argparse
import socket
import time
import json
import sys

def test_connection(server_ip, server_port=8889):
    """Test basic network connection"""
    print(f"🔌 Testing connection to {server_ip}:{server_port}")
    
    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10.0)  # 10 second timeout
        
        # Try to connect
        print("⏳ Attempting to connect...")
        client_socket.connect((server_ip, server_port))
        print("✅ Connected successfully!")
        
        # Send test messages
        for i in range(5):
            message = {
                'test_id': i + 1,
                'timestamp': time.time(),
                'message': f'Hello from Raspberry Pi! Test {i + 1}',
                'pi_info': {
                    'hostname': socket.gethostname(),
                    'local_ip': socket.gethostbyname(socket.gethostname())
                }
            }
            
            # Send message
            message_data = json.dumps(message).encode('utf-8')
            message_length = len(message_data)
            
            # Send length first, then message
            client_socket.send(message_length.to_bytes(4, byteorder='big'))
            client_socket.send(message_data)
            
            print(f"📤 Sent test message {i + 1}")
            
            # Wait for response
            try:
                response_length = int.from_bytes(client_socket.recv(4), byteorder='big')
                response_data = client_socket.recv(response_length)
                response = json.loads(response_data.decode('utf-8'))
                
                print(f"📥 Received response: {response['message']}")
                
            except socket.timeout:
                print(f"⏰ Timeout waiting for response to message {i + 1}")
            
            time.sleep(1)  # Wait 1 second between messages
        
        client_socket.close()
        print("🎉 Network test completed successfully!")
        return True
        
    except ConnectionRefusedError:
        print(f"❌ Connection refused. Make sure the server is running on {server_ip}:{server_port}")
        return False
    except socket.timeout:
        print(f"❌ Connection timeout. Check if {server_ip} is reachable")
        return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Network Test Client (Raspberry Pi)')
    parser.add_argument('--server-ip', type=str, required=True, 
                       help='IP address of your laptop (e.g., 192.168.1.100)')
    parser.add_argument('--server-port', type=int, default=8889, 
                       help='Server port (default: 8889)')
    
    args = parser.parse_args()
    
    print("🍓 Raspberry Pi Network Test Client")
    print("=" * 40)
    print(f"Target: {args.server_ip}:{args.server_port}")
    print()
    
    # Get Pi's IP address
    try:
        pi_ip = socket.gethostbyname(socket.gethostname())
        print(f"📍 Raspberry Pi IP: {pi_ip}")
    except:
        print("📍 Could not determine Pi IP address")
    
    print()
    
    # Test connection
    success = test_connection(args.server_ip, args.server_port)
    
    if success:
        print("\n✅ Network communication test PASSED!")
        print("🚀 You can now test the full remote inference system")
    else:
        print("\n❌ Network communication test FAILED!")
        print("🔧 Check your network setup and try again")
        sys.exit(1)

if __name__ == '__main__':
    main()