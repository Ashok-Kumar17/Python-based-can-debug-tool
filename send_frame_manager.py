import can
import time
import socket
import pickle
import struct
import serial
from can_enums import connect_enum

class SendFrameManager:
    def __init__(self, connection_manager, can_message_queue):
        """
        Initialize the SendFrameManager.
        :param can_bus: CAN bus object to send messages.
        :param can_message_queue: Queue to store CAN messages for processing.
        """
        self.connection_manager = connection_manager
        self.can_message_queue = can_message_queue

    def send_frame(self, can_id, is_extended, is_rtr, dlc, data):
        bus = self.connection_manager.get_active_bus()
        connection_type = self.connection_manager.get_connection_type()

        if not bus and connection_type != connect_enum.SOCKETSERVER:
            print("[ERROR] CAN bus is not initialized.")
            return False, "CAN bus is not initialized."

        try:
            if connection_type == connect_enum.ACAN:
                stx = 0xAA
                etx = 0xBB
                timestamp = int(time.time())
                frame = struct.pack(
                    "<BIBI8sB",
                    stx,
                    timestamp,
                    dlc,
                    can_id,
                    bytes(data).ljust(8, b'\x00'),
                    etx
                )
                bus.write(frame)
                message = can.Message(
                    timestamp=timestamp,
                    arbitration_id=can_id,
                    is_extended_id=is_extended,
                    is_remote_frame=is_rtr,
                    dlc=dlc,
                    data=bytearray(data),
                    is_rx = False
                )
                message.is_rx = False
                self.can_message_queue.put(message)
                return True, "Frame sent successfully (ACAN)."

            elif connection_type == connect_enum.PCAN:
                message = can.Message(
                    arbitration_id=can_id,
                    is_extended_id=is_extended,
                    is_remote_frame=is_rtr,
                    dlc=dlc,
                    data=data
                )
                bus.send(message)
                message.timestamp = time.time()
                message.is_rx = False
                self.can_message_queue.put(message)
                return True, "Frame sent successfully."

            elif connection_type == connect_enum.SOCKETSERVER:
                udp_socket = self.connection_manager.get_active_bus()
                client_address = getattr(self.connection_manager, "client_address", None)
                if not udp_socket:
                    print("[ERROR] UDP socket is not initialized.")
                    return False, "UDP socket is not initialized."
                if not client_address:
                    print("[ERROR] Client address is not set. Awaiting initial connection.")
                    return False, "Client address is not set."

                message = can.Message(
                    arbitration_id=can_id,
                    is_extended_id=is_extended,
                    is_remote_frame=is_rtr,
                    dlc=dlc,
                    data=bytearray(data),
                    is_rx=False,
                    timestamp=time.time()
                )
                frame_bytes = pickle.dumps(message)
                udp_socket.sendto(frame_bytes, client_address)
                self.can_message_queue.put(message)
                return True, "Frame sent successfully (UDP)."

            else:
                print("[ERROR] Unsupported bus type for sending.")
                return False, "Unsupported bus type."

        except can.CanError as e:
            print(f"[ERROR] Failed to send CAN frame to bus: {e}")
            return False, f"Failed to send frame to bus: {e}"
        except Exception as e:
            print(f"[ERROR] Failed to process CAN frame: {e}")
            return False, f"Failed to process frame: {e}"

    def set_connection_type(self, connection_type):
        if connection_type not in connect_enum:
            self.connection_type = connect_enum.NONE
            return False
        
        self.connection_type = connection_type
        return True