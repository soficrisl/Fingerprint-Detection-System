# socket_fingerprint_client_with_status.py
import socket
import json
import struct
import base64
import io
import time
import threading
from PIL import Image
import serial
import adafruit_fingerprint
from gpiozero import Button, LED 
from rpi_lcd import LCD

class FingerprintSocketClient:
    def __init__(self, server_host, server_port=5555):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.last_activity = time.time()
        self.keepalive_thread = None
        self.running = True
        self.transaction_in_progress = False
        self.lock = threading.Lock()
        # Uncomment for real hardware:
        # self.uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
        # self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)
        
    def connect(self):
        if self.connected and self.socket:
            if self.is_connection_alive():
                print("Already connected and alive")
                return True
            else:
                print("Connection dead, reconnecting...")
                self.disconnect()
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.settimeout(10.0)
            
            print(f"Connecting to {self.server_host}:{self.server_port}")
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            print("Connected successfully!")
            
            self.socket.settimeout(120.0)
            
            self.running = True
            self.transaction_in_progress = False
            if self.keepalive_thread is None or not self.keepalive_thread.is_alive():
                self.keepalive_thread = threading.Thread(target=self._keepalive_loop, daemon=True)
                self.keepalive_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            return False
    
    def _keepalive_loop(self):
        while self.running and self.connected:
            try:
                time.sleep(20)
                if self.transaction_in_progress:
                    continue
                if (time.time() - self.last_activity) <= 20:
                    continue
                with self.lock:
                    if not self.transaction_in_progress and self.connected:
                        try:
                            json_message = json.dumps({'action': 'keepalive'})
                            message_bytes = json_message.encode('utf-8')
                            length = len(message_bytes)
                            self.socket.sendall(struct.pack('!I', length))
                            self.socket.sendall(message_bytes)
                            length_data = self.receive_all(4)
                            if length_data:
                                length = struct.unpack('!I', length_data)[0]
                                message_data = self.receive_all(length)
                                if message_data:
                                    response = json.loads(message_data.decode('utf-8'))
                                    if response.get('status') == 'alive':
                                        print(f"Keepalive OK at {time.strftime('%H:%M:%S')}")
                                        self.last_activity = time.time()
                                    else:
                                        print("Keepalive failed - unexpected response")
                                        self.connected = False
                                        break
                        except Exception as e:
                            print(f"Keepalive error: {e}")
                            
            except Exception as e:
                print(f"Keepalive loop error: {e}")
    
    def is_connection_alive(self): 
        """Check if connection is still alive"""
        if not self.connected or not self.socket: 
            return False
        
        with self.lock:
            try:
                was_in_transaction = self.transaction_in_progress
                self.transaction_in_progress = True
                
                original_timeout = self.socket.gettimeout()
                self.socket.settimeout(5.0)
                
                json_message = json.dumps({'action': 'health'})
                message_bytes = json_message.encode('utf-8')
                length = len(message_bytes)
                self.socket.sendall(struct.pack('!I', length))
                self.socket.sendall(message_bytes)
                
                length_data = self.receive_all(4)
                if not length_data:
                    self.connected = False
                    return False
                    
                length = struct.unpack('!I', length_data)[0]
                message_data = self.receive_all(length)
                if not message_data:
                    self.connected = False
                    return False
                    
                response = json.loads(message_data.decode('utf-8'))
                
                self.socket.settimeout(original_timeout)
                self.transaction_in_progress = was_in_transaction
                
                return response.get('status') == 'healthy'
            except Exception as e:
                print(f"Health check failed: {e}")
                self.connected = False
                self.transaction_in_progress = was_in_transaction
                return False

    def disconnect(self):
        self.running = False
        self.transaction_in_progress = False
        
        if self.socket:
            try:
                if self.connected:
                    with self.lock:
                        json_message = json.dumps({'action': 'disconnect'})
                        message_bytes = json_message.encode('utf-8')
                        length = len(message_bytes)
                        self.socket.sendall(struct.pack('!I', length))
                        self.socket.sendall(message_bytes)
                        time.sleep(0.1)
            except:
                pass
            
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.connected = False
        print("Disconnected")
    
    def send_message(self, message):
        if not self.connected:
            raise Exception("Not connected to server")
        
        with self.lock:
            try:
                json_message = json.dumps(message)
                message_bytes = json_message.encode('utf-8')
                length = len(message_bytes)
                self.socket.sendall(struct.pack('!I', length))
                self.socket.sendall(message_bytes)
                self.last_activity = time.time()
            except Exception as e: 
                self.connected = False 
                raise Exception(f"Send failed: {e}")
        
    def receive_message(self):
        """Receive message from server"""
        if not self.connected:
            raise Exception("Not connected to server")
        
        try:
            length_data = self.receive_all(4)
            if not length_data:
                raise Exception("Connection lost")
            length = struct.unpack('!I', length_data)[0]
            
            message_data = self.receive_all(length)
            if not message_data:
                raise Exception("Connection lost")
            
            self.last_activity = time.time()
            return json.loads(message_data.decode('utf-8'))
        except Exception as e:
            self.connected = False 
            raise Exception(f"Receive failed: {e}")

    def receive_all(self, length):
        """Receive exactly 'length' bytes"""
        data = b''
        while len(data) < length:
            packet = self.socket.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return data
    
    def send_fingerprint_with_status(self, state, lcd, action='receive_fingerprint'):
        """Send fingerprint request and handle status updates"""
        start_time = time.time()
        
        # Block keepalive during transaction
        self.transaction_in_progress = True
        
        message = {
            'action': action,
            'state': state,
        }
        
        try:
            with self.lock:
                print(f"Sending {action} request...")
                send_start = time.time()
                
                # Send initial request
                json_message = json.dumps(message)
                message_bytes = json_message.encode('utf-8')
                length = len(message_bytes)
                self.socket.sendall(struct.pack('!I', length))
                self.socket.sendall(message_bytes)
                
                print("Waiting for responses...")
                
                # Keep receiving messages until we get final response
                while True:
                    length_data = self.receive_all(4)
                    if not length_data:
                        raise Exception("Connection lost while waiting for response")
                    
                    length = struct.unpack('!I', length_data)[0]
                    message_data = self.receive_all(length)
                    if not message_data:
                        raise Exception("Connection lost while receiving response")
                    
                    response = json.loads(message_data.decode('utf-8'))
                    
                    msg_type = response.get('type', 'final')
                    
                    if msg_type == 'status':
                        status_text = response.get('message', '')
                        line1 = response.get('line1', status_text[:16] if status_text else '')
                        line2 = response.get('line2', status_text[16:32] if len(status_text) > 16 else '')
                        
                        lcd.clear()
                        if line1:
                            lcd.text(line1, 1)
                        if line2:
                            lcd.text(line2, 2)
                    
                        print(f"Status: {status_text}")
                        continue
                        
                    elif msg_type == 'final':
                        network_time = time.time() - send_start
                        self.last_activity = time.time()
                        response['network_time'] = network_time
                        response['total_time'] = time.time() - start_time
                        print(f"Final response received in {network_time:.2f}s")
                        return response
                    
                    else:
                        # Unknown message type, treat as final
                        print(f"Unknown message type: {msg_type}")
                        response['network_time'] = time.time() - send_start
                        response['total_time'] = time.time() - start_time
                        return response
            
        except Exception as e:
            print(f"Error during fingerprint operation: {e}")
            return {
                'success': False, 
                'error': str(e),
                'total_time': time.time() - start_time
            }
        finally:
            # Re-enable keepalive
            self.transaction_in_progress = False
    
    def send_with_smart_reconnect(self, state, lcd, action='receive_fingerprint', max_retries=2):
        for attempt in range(max_retries):
            # Check and reconnect if needed
            if not self.connected or not self.is_connection_alive():
                print(f"Connection lost, reconnecting (attempt {attempt + 1}/{max_retries})...")
                lcd.clear()
                lcd.text("Reconectando...", 1)
                lcd.text(f"Intento {attempt + 1}/{max_retries}", 2)
                
                if not self.connect():
                    time.sleep(0.5)
                    continue
            
            try:
                result = self.send_fingerprint_with_status(state, lcd, action)
                return result
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                self.connected = False
                if attempt < max_retries - 1:
                    time.sleep(0.5)
        
        return {
            'success': False,
            'error': 'Failed to complete operation after retries'
        }

def main():
    client = FingerprintSocketClient(server_host='10.251.111.252')
    lcd = LCD()
    
    # Buttons
    match_button = Button(6, pull_up=True)
    register_button = Button(5, pull_up=True)  
    
    # LEDs
    red = LED(17)
    green = LED(27)
    
    # Initial connection
    print("Estableciendo conexion inicial...")
    lcd.clear()
    lcd.text("Conectando...", 1)
    lcd.text("Por favor espere", 2)
    
    connection_attempts = 0
    max_connection_attempts = 3
    
    while connection_attempts < max_connection_attempts:
        if client.connect():
            lcd.clear()
            lcd.text("Sistema listo", 1)
            time.sleep(1)
            break
        connection_attempts += 1
        if connection_attempts < max_connection_attempts:
            lcd.clear()
            lcd.text(f"Reintento {connection_attempts}/{max_connection_attempts}", 1)
            time.sleep(2)
    else:
        lcd.clear()
        lcd.text("Error conexion", 1)
        lcd.text("Reinicie sistema", 2)
        return
    
    try:
        msg_index = 0
        start_time = time.time()
        transaction_count = 0
        
        while True:
            # Ensure connection is alive before showing menu
            if not client.connected:
                lcd.clear()
                lcd.text("Reconectando...", 1)
                if not client.connect():
                    lcd.text("Fallo reconexion", 2)
                    time.sleep(2)
                    continue
            
            lcd.clear()
            messages = [
                ("Metro de Caracas", "Presione boton"),
                ("Paga con LP ->", "<- Registrate :)")
            ]
            
            state = None
            
            # Wait for button press
            while state is None:
                if time.time() - start_time >= 2:
                    msg_index = (msg_index + 1) % 2
                    lcd.clear()
                    lcd.text(messages[msg_index][0], 1)
                    lcd.text(messages[msg_index][1], 2)
                    start_time = time.time()
                
                if match_button.is_pressed:
                    state = False  # Match mode
                    lcd.clear()
                    lcd.text("Modo: Pagar", 1)
                    time.sleep(0.5)
                elif register_button.is_pressed:  
                    state = True  # Register mode
                    lcd.clear()
                    lcd.text("Modo: Registrar", 1)
                    time.sleep(0.5)
                
                time.sleep(0.05)
            
            # Process transaction
            transaction_count += 1
            print(f"\n--- Transaction #{transaction_count} ---")
            
            # Initial processing message
            lcd.clear()
            lcd.text("Iniciando...", 1)
            lcd.text("", 2)
            
            result = client.send_with_smart_reconnect(state, lcd, 'receive_fingerprint')
            
            print(f"Result: {result}")
            
            lcd.clear()
            if result.get('success'):
                green.on()
                if state:  # Register mode
                    lcd.text(result.get('message',"Registro Ok!"), 1)
                    lcd.text(f"ID: {result.get('pas_id', 'N/A')}", 2)
                else:  # Match mode
                    lcd.text(result.get('message',"Acceso Ok!"), 1)
                    lcd.text(f"ID: {result.get('pas_id', 'N/A')}", 2)
                
                print(f"Success! Time: {result.get('total_time', 0):.2f}s")
                print(f"Connection still alive: {client.connected}")
                time.sleep(3)
                green.off()
            else:
                red.on()
                if state:  # Register mode
                    lcd.text("Error registro", 1)
                else:  # Match mode
                    lcd.text("Acceso denegado", 1)
                
                error_msg = result.get('message', result.get('error', 'Error desconocido'))
                if len(error_msg) > 16:
                    error_msg = error_msg[:16]
                lcd.text(error_msg, 2)
                
                print(f"Failed: {error_msg}")
                time.sleep(3)
                red.off()
            
            # Reset for next iteration
            msg_index = 0
            start_time = time.time()
            lcd.clear()
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        client.disconnect()
        lcd.clear()
        lcd.text("Sistema", 1)
        lcd.text("Apagado", 2)
        green.off()
        red.off()

if __name__ == "__main__":
    main()