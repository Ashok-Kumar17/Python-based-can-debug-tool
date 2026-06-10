# Infinity — Python CAN Debug Tool

A desktop GUI application for monitoring, debugging, and sending CAN bus messages. Built with PySide6 and python-can, developed during an internship at **Ather Energy**.

---

## Features

- **Multi-interface support** — PCAN (USB), ACAN (custom serial @ 1Mbps), and UDP socket server
- **Live message table** — real-time CAN frame display with ID, DLC, data bytes, direction, and timestamp
- **Overwrite mode** — shows only the latest frame per CAN ID (like a live signal monitor)
- **DBC decoding** — load a `.dbc` file to decode signal values inline in the message table
- **Send frames** — manually send CAN frames with configurable ID, DLC, and data bytes (keyboard shortcuts Ctrl+1 to Ctrl+0)
- **FPS counter** — live frames-per-second display
- **Autoscroll** — optionally follow the latest incoming message

---

## Requirements

- Python 3.10+
- PySide6
- python-can
- cantools
- pyserial

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Setup

1. Clone the repo:
```bash
git clone https://github.com/Ashok-Kumar17/Python-based-can-debug-tool.git
cd Python-based-can-debug-tool
```

2. Copy the example config and edit it for your machine:
```bash
cp can_config.example.json can_config.json
```

Edit `can_config.json` to match your CAN interface. For example, on Linux with a SocketCAN interface:
```json
{
    "linux": { "channel": "can0", "bus_type": "socketcan" },
    "bus_config": { "bitrate": 500000 }
}
```

3. Run the application:
```bash
python infinity.py
```

---

## Connection Modes

| Mode | Description |
|------|-------------|
| **PCAN** | PEAK USB CAN adapter via `python-can`. Uses `can_config.json` for channel and bitrate. |
| **ACAN** | Custom serial-over-USB protocol at 1Mbps. Select your COM/tty port from the dropdown. Frame format: `0xAA [4B timestamp] [1B DLC] [4B CAN ID] [8B data] 0xBB` |
| **UDP Server** | Listens for CAN frames sent over UDP. Configure IP and port in the Connections tab. |

---

## File Structure

```
├── infinity.py              # Entry point
├── main_window.py           # Top-level QMainWindow
├── can_message_ui.py        # Main widget — tabs, controls, message processing
├── can_message_table.py     # CAN message table model and view
├── connection_manager.py    # Handles PCAN / ACAN / UDP connections
├── connection_window.py     # Connection dialog
├── dbc_manager.py           # DBC file loading and signal decoding
├── send_frame_manager.py    # CAN frame transmission logic
├── can_enums.py             # Enums for connection type, capture state, etc.
├── can_config.example.json  # Template config — copy to can_config.json
├── styles.qss               # Qt stylesheet
└── requirements.txt
```

---

## Author

**Ashok Kumar Meena**  
Electrical Engineering, IIT Madras  
Intern — Embedded Software, Ather Energy (Summer 2025)
