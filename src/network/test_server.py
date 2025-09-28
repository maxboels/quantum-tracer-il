#!/usr/bin/env python3
"""
Simple Test Server (For Your Laptop)
====================================

This is a minimal test server to verify network communication works
before testing the full inference system.

Usage:
    python3 test_server.py --port 8889
"""

import argparse
import socket
import json
import threading
import time
import struct
import cv2
import numpy as np

class TestServer:
    def __init__(self, port=8889):
        self.port = port
        self.running = False
        
    def start_server(self):
        """Start the test server"""
        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('0.0.0.0', self.port))
            server_socket.listen(5)
            
            print(f"🚀 Test server started on port {self.port}")
            print(f"💻 Laptop IP: {self.get_local_ip()}")
            print("Waiting for connections from Raspberry Pi...")
            print("=" * 50)
            
            self.running = True
            
            while self.running:
                try:
                    client_socket, client_address = server_socket.accept()
                    print(f"🔗 New connection from {client_address}")
                    
                    # Handle client in separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        print(f"Socket error: {e}")
                        
        except KeyboardInterrupt:
            print("\n👋 Server shutdown requested")
        finally:
            self.running = False
            server_socket.close()
            print("🛑 Server stopped")
    
    def handle_client(self, client_socket, client_address):
        """Handle individual client connections"""
        try:
            message_count = 0
            
            while self.running:
                # Receive message length
                length_data = self.recv_exact(client_socket, 4)
                if not length_data:
                    break
                    
                message_length = int.from_bytes(length_data, byteorder='big')
                
                # Receive message data
                message_data = self.recv_exact(client_socket, message_length)
                if not message_data:
                    break
                
                # Try to determine if it's JSON or binary data
                try:
                    # First, try to decode as UTF-8 to see if it's text/JSON
                    decoded_text = message_data.decode('utf-8')
                    # If successful, try to parse as JSON
                    message = json.loads(decoded_text)
                    message_count += 1
                    
                    print(f"📥 Message {message_count} from {client_address}:")
                    print(f"   Type: JSON message")
                    print(f"   Content: {message.get('message', message.get('test', 'No message'))}")
                    
                    # Send response
                    response = {
                        'status': 'received',
                        'message_id': message_count,
                        'timestamp': time.time(),
                        'message': f'Hello back from laptop! (Response {message_count})'
                    }
                    
                    response_data = json.dumps(response).encode('utf-8')
                    client_socket.send(len(response_data).to_bytes(4, byteorder='big'))
                    client_socket.send(response_data)
                    
                except (UnicodeDecodeError, json.JSONDecodeError):
                    # This is binary data (likely an image)
                    message_count += 1
                    print(f"📸 Frame {message_count} from {client_address}:")
                    print(f"   Size: {len(message_data)} bytes")
                    
                    # Try to decode as image
                    try:
                        # Assume it's JPEG data
                        frame_array = np.frombuffer(message_data, dtype=np.uint8)
                        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
                        
                        if frame is not None:
                            print(f"   ✅ Frame decoded successfully: {frame.shape}")
                            # Save frame for debugging
                            filename = f"received_frame_{message_count:03d}.jpg"
                            cv2.imwrite(filename, frame)
                            print(f"   💾 Saved as {filename}")
                        else:
                            print(f"   ❌ Could not decode as image")
                            
                    except Exception as e:
                        print(f"   ❌ Frame processing error: {e}")
                    
                    # Send simple response
                    response = f"Frame {message_count} received successfully"
                    response_bytes = response.encode('utf-8')
                    client_socket.send(len(response_bytes).to_bytes(4, byteorder='big'))
                    client_socket.send(response_bytes)
                
        except Exception as e:
            print(f"❌ Client handling error: {e}")
        finally:
            client_socket.close()
            print(f"🔌 Client {client_address} disconnected")
    
    def recv_exact(self, sock, length):
        """Receive exactly 'length' bytes"""
        data = b''
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                return None
            data += chunk
        return data
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to a dummy address to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "Unknown"

def main():
    parser = argparse.ArgumentParser(description='Simple Test Server (Laptop)')
    parser.add_argument('--port', type=int, default=8889, help='Server port (default: 8889)')
    
    args = parser.parse_args()
    
    print("💻 Simple Test Server - Laptop Side")
    print("=" * 40)
    print("This server will receive test messages from your Raspberry Pi")
    print(f"Port: {args.port}")
    print()
    
    server = TestServer(args.port)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == '__main__':
    main()