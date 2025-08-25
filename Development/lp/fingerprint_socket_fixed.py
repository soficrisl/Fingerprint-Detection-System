# fingerprint_socket_server_fixed.py
# Server with persistent connections

import socket 
import threading
import json 
import struct
import time
from datetime import datetime
from app import App

# Create directory for received images
import os
SAVE_DIR = "received_fingerprints"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

class FingerprintSocketServer: 
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host 
        self.port = port
        self.server_socket = None 
        self.running = False 
        self.clients = {}
        self.client_threads = []

    def start(self): 
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True

        print(f"Socket server started on {self.host}:{self.port}")
        print("Waiting for connections...")
        print("-" * 60)

        while self.running: 
            try: 
                client_socket, client_address = self.server_socket.accept()
                print(f"\n[NEW] Client connected: {client_address}")
                print(f"[INFO] Connection will remain open for multiple transactions")
                
                client_id = f"{client_address[0]}:{client_address[1]}"
                self.clients[client_id] = {
                    'socket': client_socket,
                    'address': client_address,
                    'connected_at': datetime.now(),
                    'transactions': 0
                }
                
                client_thread = threading.Thread(
                    target=self.handle_client_persistent,
                    args=(client_socket, client_address, client_id),
                    daemon=True
                )
                client_thread.start()
                self.client_threads.append(client_thread)
                
                self.client_threads = [t for t in self.client_threads if t.is_alive()]
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running: 
                    print(f"[ERROR] Error accepting connection: {e}")

    def receive_all(self, sock, length): 
        """Receive exactly 'length' bytes"""
        data = b''
        while len(data) < length: 
            try:
                packet = sock.recv(length - len(data))
                if not packet: 
                    return None 
                data += packet
            except socket.timeout:
                if not self.running:
                    return None
                continue
            except Exception:
                return None
        return data 
    
    def send_status_message(self, client_socket, message, line1=None, line2=None):
        status_msg = {
            'type': 'status',
            'message': message,
            'line1': line1 or message[:16],
            'line2': line2 or (message[16:32] if len(message) > 16 else '')
        }
        
        try:
            json_response = json.dumps(status_msg)
            response_bytes = json_response.encode('utf-8')
            length = len(response_bytes)
            client_socket.sendall(struct.pack("!I", length))
            client_socket.sendall(response_bytes)
            print(f"[STATUS] Sent to LCD: {line1} | {line2}")
        except Exception as e:
            print(f"[ERROR] Failed to send status: {e}")

    def handle_client_persistent(self, client_socket, client_address, client_id): 
        """Handle client with persistent connection"""
        # Set longer timeout for persistent connections
        client_socket.settimeout(90.0)
        
        # Create app instance for this client
        client_app = App(False)
        
        try: 
            while self.running:
                try:
                    length_data = self.receive_all(client_socket, 4)
                    if not length_data:
                        print(f"[DISCONNECT] Client {client_address} disconnected (no data)")
                        break 
                    
                    message_length = struct.unpack('!I', length_data)[0]
                    
                    # Sanity check
                    if message_length > 10 * 1024 * 1024:  
                        print(f"[ERROR] Message too large from {client_address}: {message_length} bytes")
                        break
                    
                    # Receive message
                    message_data = self.receive_all(client_socket, message_length)
                    if not message_data: 
                        print(f"[DISCONNECT] Client {client_address} disconnected (incomplete message)")
                        break 

                    message = json.loads(message_data.decode('utf-8'))
                    action = message.get('action')
                    
                    # Update client activity
                    if client_id in self.clients:
                        self.clients[client_id]['transactions'] += 1
                        trans_count = self.clients[client_id]['transactions']
                    
                    # Log actions (except keepalive)
                    if action not in ['keepalive']:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {client_address} -> {action}")



                    # Process actions
                    if action == 'health': 
                        response = self.health_check()
                    elif action == 'keepalive':
                        response = {'status': 'alive', 'message': 'Connection maintained'}
                    elif action == 'disconnect':
                        print(f"[INFO] Client {client_address} requested disconnect")
                        response = {'status': 'goodbye', 'message': 'Disconnected'}
                        self.send_response(client_socket, response)
                        break
                    elif action == 'receive_fingerprint':
                        print(f"[PROCESS] Processing fingerprint for {client_address}...")
                        state = message.get('state', False)

                        def status_callback(msg, line1=None, line2=None):
                            self.send_status_message(client_socket, msg, line1, line2)
                        
                        client_app.set_state_callback (status_callback)

                        start_time = time.time()
                        client_app.set_state(state)
                        result = client_app.initiate()
                        process_time = time.time() - start_time

                        # Format response
                        if result["success"]:
                            response = {
                                "success": True,
                                "message": result["message"],
                                "pas_id": result.get('pas_id', 0)
                            }
                            print(f"[SUCCESS] Fingerprint processed in {process_time:.2f}s")
                        else:
                            response = {
                                "success": False,
                                "message": result.get("error", "Unknown error")
                            }
                            print(f"[FAILED] Fingerprint processing failed: {result.get('error')}")
                        
                        if client_id in self.clients:
                            print(f"[INFO] Transaction #{trans_count} completed for {client_address}")
                    elif action == 'test':
                        response = self.test()
                    elif action == 'ping':
                        response = {'success': True, 'message': 'pong'}
                    else: 
                        response = { 
                            'success': False, 
                            'error': f"Unknown action: {action}"
                        }
                        print(f"[WARNING] Unknown action from {client_address}: {action}")

                    # Send response
                    self.send_response(client_socket, response)
                    
                    
                except socket.timeout:
                    # Timeout is normal for idle connections - continue
                    continue
                except json.JSONDecodeError as e:
                    print(f"[ERROR] Invalid JSON from {client_address}: {e}")
                    error_response = {
                        "success": False, 
                        "error": "Invalid JSON format"
                    }
                    try:
                        self.send_response(client_socket, error_response)
                    except:
                        break
                except Exception as e:
                    print(f"[ERROR] Error handling request from {client_address}: {e}")
                    # Try to send error response
                    try:
                        error_response = {
                            "success": False,
                            "error": str(e)
                        }
                        self.send_response(client_socket, error_response)
                    except:
                        pass
                    # Don't break - try to keep connection alive if possible
                    
        except Exception as e:
            print(f"[CRITICAL] Critical error with client {client_address}: {e}")
        finally:
            if client_id in self.clients:
                info = self.clients[client_id]
                duration = (datetime.now() - info['connected_at']).total_seconds()
                print(f"[STATS] Client {client_address} disconnected:")
                print(f"        Duration: {duration:.1f}s, Transactions: {info['transactions']}")
                del self.clients[client_id]
            else:
                print(f"[DISCONNECT] Client {client_address} disconnected")
            
            client_socket.close()

    def send_response(self, client_socket, response):
        """Send response to client"""
        json_response = json.dumps(response)
        response_bytes = json_response.encode('utf-8')
        length = len(response_bytes)
        client_socket.sendall(struct.pack("!I", length))
        client_socket.sendall(response_bytes)

    def health_check(self):
        """Health check endpoint"""
        return {
            "status": "healthy",
            "message": "Fingerprint socket server is running",
            "active_clients": len(self.clients)
        }    

    def test(self):
        """Test endpoint"""
        return {
            "success": True,
            "message": "Server is working!",
            "actions": [
                "health - Check server health",
                "receive_fingerprint - Process fingerprint",
                "test - This action",
                "ping - Connection test",
                "keepalive - Keep connection alive"
            ],
            "connected_clients": len(self.clients)
        }
    
    def stop(self):
        """Stop the server gracefully"""
        print("\n[SHUTDOWN] Stopping server...")
        self.running = False
        
        # Close all client connections
        for client_id, client_info in self.clients.items():
            try:
                client_info['socket'].close()
            except:
                pass
        
        # Wait for client threads
        for thread in self.client_threads:
            thread.join(timeout=1.0)
        
        if self.server_socket:
            self.server_socket.close()
        
        print("[SHUTDOWN] Server stopped")
    
    def status(self):
        """Print server status"""
        print("\n" + "="*60)
        print(f"SERVER STATUS at {datetime.now().strftime('%H:%M:%S')}")
        print(f"Active clients: {len(self.clients)}")
        for client_id, info in self.clients.items():
            idle = (datetime.now() - info.get('last_activity', info['connected_at'])).total_seconds()
            print(f"  - {info['address']} | Transactions: {info['transactions']} | Connected: {idle:.1f}s ago")
        print("="*60)

if __name__ == '__main__':
    print("=" * 60)
    print("Fingerprint Socket Server with Persistent Connections")
    print(f"Server listening on: 0.0.0.0:5555")
    print("\nFeatures:")
    print("\nAvailable actions:")
    print("  - health: Check server health")
    print("  - receive_fingerprint: Process fingerprint")
    print("  - keepalive: Keep connection alive")
    print("  - disconnect: Graceful disconnect")
    print("  - test: Test server")
    print("\nPress Ctrl+C to stop | Press 's' + Enter for status")
    print("=" * 60)
    
    server = FingerprintSocketServer()
    
    # Start server in a thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    try:
        while True:
            # Allow user to check status
            user_input = input()
            if user_input.lower() == 's':
                server.status()
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Received interrupt signal")
        server.stop()
        print("[SHUTDOWN] Complete")