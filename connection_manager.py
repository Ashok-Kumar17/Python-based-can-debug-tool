import can
import json
import pickle
import serial
import struct
import socket
import sys
from can_enums import connect_enum
from PySide6.QtCore import QThread, Signal

class SerialReaderThread(QThread):
    frame_received = Signal(bytes)

    def __init__(self, serial_port, frame_size=19):
        super().__init__()
        self.serial_port = serial_port
        self._running = True
        self.frame_size = frame_size
        self.buffer = bytearray()

    def run(self):
        while self._running and self.serial_port and self.serial_port.is_open:
            try:
                available = self.serial_port.in_waiting
                to_read = (available // self.frame_size) * self.frame_size
                if to_read > 0:
                    data = self.serial_port.read(to_read)
                    self.buffer.extend(data)
                    self._extract_frames()
            except Exception as e:
                print(f"[ERROR] Serial read error: {e}")
                break

    def _extract_frames(self):
        idx = 0
        while idx < len(self.buffer):
            if self.buffer[idx] == 0xAA:
                if idx + self.frame_size <= len(self.buffer):
                    frame = self.buffer[idx:idx+self.frame_size]
                    self.frame_received.emit(bytes(frame))
                    idx += self.frame_size
                else:
                    break
            else:
                idx += 1
        self.buffer = self.buffer[idx:]

    def stop(self):
        self._running = False
        self.wait()

class UDPReaderThread(QThread):
    frame_received = Signal(bytes, object)

    def __init__(self, udp_socket, frame_size=19):
        super().__init__()
        self.udp_socket = udp_socket
        self._running = True
        self.frame_size = frame_size

    def run(self):
        while self._running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                if data:
                    self.frame_received.emit(data, addr)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ERROR] UDP read error: {e}")
                break

    def stop(self):
        self._running = False
        self.wait()

class ConnectionManager:
    def __init__(self):
        self.active_bus = None
        self.can_bus = None
        self.connection_type = connect_enum.NONE
        self.can_msg_notifier = None
        self.config_path = "can_config.json"
        self.serial_thread = None
        self.udp_socket = None
        self.msg_callback = None
        self.client_address = None

    def connect(self, on_message_received_callback, connection_type, params=None):
        self.connection_type = connection_type
        if connection_type == connect_enum.PCAN:
            try:
                with open(self.config_path, "r") as config_file:
                    can_config = json.load(config_file)
                    platform = sys.platform
                    connection_config = can_config[platform]
                    bus_config = can_config["bus_config"]
                    bitrate = bus_config["bitrate"]

                    self.can_bus = can.ThreadSafeBus(
                        channel=connection_config["channel"],
                        bustype=connection_config["bus_type"],
                        bitrate=bitrate
                    )
                    self.can_msg_notifier = can.Notifier(self.can_bus, [on_message_received_callback])
                    self.active_bus = self.can_bus
                    return True
            except Exception as e:
                print(f"[ERROR] Failed to connect: {e}")
                return False
        elif connection_type == connect_enum.ACAN:
            try:
                port = params.get('port')
                if not port:
                    print("[ERROR] No serial port specified.")
                    return False
                self.serial_port = serial.Serial(port=port, baudrate=1000000, timeout=0.1)
                self.serial_thread = SerialReaderThread(self.serial_port, frame_size=19)
                self.msg_callback = on_message_received_callback
                self.serial_thread.frame_received.connect(self.handle_frame)
                self.serial_thread.start()
                self.active_bus = self.serial_port
                print(f"[DEBUG] Connected to serial port {port} (QThread, 1Mbps, 19 bytes/frame)")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to connect (ACAN): {e}")
                return False
        elif connection_type == connect_enum.SOCKETSERVER:
            try:
                ip = params.get('ip', '0.0.0.0')
                port = int(params.get('port', 5000))
                self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_socket.bind((ip, port))
                self.udp_socket.settimeout(0.5)
                self.udp_thread = UDPReaderThread(self.udp_socket, frame_size=19)
                self.msg_callback = on_message_received_callback
                self.udp_thread.frame_received.connect(self.handle_udp_frame)
                self.udp_thread.start()
                self.active_bus = self.udp_socket
                print(f"[DEBUG] UDP server started on {ip}:{port}")
                return True
            except Exception as e:
                print(f"[ERROR] Failed to start UDP server: {e}")
                return False

        else:
            print("[ERROR] Unknown connection type.")
            return False

    def disconnect(self):
        try:
            if self.connection_type == connect_enum.PCAN:
                if self.can_msg_notifier:
                    self.can_msg_notifier.stop()
                    self.can_msg_notifier = None
                if self.active_bus:
                    try:
                        self.active_bus.shutdown()
                    except Exception as e:
                        print(f"[WARNING] Error shutting down CAN bus: {e}")
                    self.active_bus = None
                self.can_bus = None

            elif self.connection_type == connect_enum.ACAN:
                if self.serial_thread:
                    self.serial_thread.stop()
                    self.serial_thread = None
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except Exception as e:
                        print(f"[WARNING] Error closing serial port: {e}")
                    self.serial_port = None
                self.active_bus = None

            elif self.connection_type == connect_enum.SOCKETSERVER:
                if hasattr(self, 'udp_thread') and self.udp_thread:
                    self.udp_thread.stop()
                    self.udp_thread = None
                if self.udp_socket:
                    try:
                        self.udp_socket.close()
                    except Exception as e:
                        print(f"[WARNING] Error closing UDP socket: {e}")
                    self.udp_socket = None
                self.active_bus = None

            self.connection_type = connect_enum.NONE
            return True
        except Exception as e:
            print(f"[ERROR] Failed to disconnect: {e}")
            return False

    def suspend(self):
        """
        Suspend the CAN message notifier or equivalent for other connections.
        """
        try:
            if self.connection_type == connect_enum.PCAN:
                if self.can_msg_notifier:
                    self.can_msg_notifier.stop()
                    self.can_msg_notifier = None
                    print("[DEBUG] CAN message notifier suspended.")
                    return True

            elif self.connection_type == connect_enum.ACAN:
                if self.serial_thread:
                    self.serial_thread.stop()
                    self.serial_thread = None
                    print("[DEBUG] ACAN serial reader thread suspended.")
                    return True

            elif self.connection_type == connect_enum.SOCKETSERVER:
                if hasattr(self, 'udp_thread') and self.udp_thread:
                    self.udp_thread.stop()
                    self.udp_thread = None
                    print("[DEBUG] UDP reader thread suspended.")
                    return True

            print("[WARNING] No active connection to suspend.")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to suspend: {e}")
            return False

    def resume(self, on_message_received_callback):
        """
        Resume the CAN message notifier or equivalent for other connections.
        """
        try:
            if self.connection_type == connect_enum.PCAN:
                if self.active_bus and not self.can_msg_notifier:
                    self.can_msg_notifier = can.Notifier(self.active_bus, [on_message_received_callback])
                    print("[DEBUG] CAN message notifier resumed.")
                    return True

            elif self.connection_type == connect_enum.ACAN:
                if self.serial_port and not self.serial_thread:
                    self.serial_thread = SerialReaderThread(self.serial_port, frame_size=19)
                    self.msg_callback = on_message_received_callback
                    self.serial_thread.frame_received.connect(self.handle_frame)
                    self.serial_thread.start()
                    print("[DEBUG] ACAN serial reader thread resumed.")
                    return True

            elif self.connection_type == connect_enum.SOCKETSERVER:
                if self.udp_socket and (not hasattr(self, 'udp_thread') or self.udp_thread is None):
                    self.udp_thread = UDPReaderThread(self.udp_socket, frame_size=19)
                    self.msg_callback = on_message_received_callback
                    self.udp_thread.frame_received.connect(self.handle_frame)
                    self.udp_thread.start()
                    print("[DEBUG] UDP reader thread resumed.")
                    return True

            print("[WARNING] No connection to resume.")
            return False
        except Exception as e:
            print(f"[ERROR] Failed to resume: {e}")
            return False
            
    def handle_frame(self, frame_bytes):
        if len(frame_bytes) != 19 or frame_bytes[0] != 0xAA or frame_bytes[-1] != 0xBB:
            return

        stx, ts, dlc, can_id, data, etx = struct.unpack("<B I B I 8s B", frame_bytes)

        msg = can.Message(
            timestamp=ts,
            arbitration_id =can_id,
            is_extended_id = lambda can_id: True if can_id > 0x7FF else False,
            is_rx =True,
            is_remote_frame = False,
            dlc = dlc,
            data = bytearray(data)
        )
        if self.msg_callback:
            self.msg_callback(msg)

    def handle_udp_frame(self, frame_bytes, addr):
        if self.is_initial_connection(frame_bytes):
            self.client_address = addr 
            print(f"[INFO] Registered client address: {addr}")
            return
        try:
            msg = pickle.loads(frame_bytes)
            if hasattr(msg, "arbitration_id") and hasattr(msg, "data"):
                if self.msg_callback:
                    self.msg_callback(msg)
                return
        except Exception as e:
            print(f"[WARNING] UDP frame is neither raw nor pickled can.Message: {e}")

        print("[WARNING] Received unknown UDP frame format.")

    def is_initial_connection(self, frame_bytes):
        # Implement your logic to detect initial connection message
        # For example, check for a specific string or message type
        return frame_bytes == b"HELLO"

    def get_active_bus(self):
        return self.active_bus

    def get_connection_type(self):
        return self.connection_type

    def is_connected(self):
        return self.active_bus is not None