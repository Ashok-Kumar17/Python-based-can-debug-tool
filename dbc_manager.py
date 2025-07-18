import cantools
import json
import ctypes


class DBCManager:
    def __init__(self):
        """
        Initialize the DBCManager.
        """
        self.can_db = None
        self.preprocessed_data = {}

    def load_dbc_file(self, file_path):
        """
        Load a DBC file, preprocess its data, and return its status.
        """
        print("[DEBUG] Loading DBC file...")
        try:
            self.can_db = cantools.database.load_file(file_path)
            return True, f"Successfully loaded and preprocessed DBC file"
        except Exception as e:
            return False, f"Failed to load DBC file: {e}"

    def decode_message(self, can_id, data):
        """
        Decode a CAN message using cantools DBC.
        """
        if not self.can_db:
            return None, "DBC file not loaded."

        try:
            message = self.can_db.get_message_by_frame_id(can_id)
            decoded = message.decode(data)
            decoded_signals = {}
            for signal in message.signals:
                value = decoded.get(signal.name)
                unit = signal.unit if signal.unit else ""
                decoded_signals[signal.name] = f"{value} {unit}".strip() if unit else f"{value}"
            return decoded_signals, None
        except Exception as e:
            return None, f"Error decoding CAN message with ID 0x{can_id:X}: {e}"
