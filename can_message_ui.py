from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QGroupBox,
    QPushButton,
    QLabel,
    QCheckBox,
    QTabWidget,
    QSizePolicy,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QRadioButton,
    QButtonGroup,
    QStackedWidget
    )
from PySide6.QtGui import QKeySequence, QShortcut

from PySide6.QtCore import Qt, QTimer
import can
import cantools
import json
import os
import queue
import sys
import time
from functools import partial
from can_enums import can_msg_table_header, capture_state, con_button, connect_enum
from can_message_table import CANMessageTable
from connection_manager import ConnectionManager
from dbc_manager import DBCManager
from send_frame_manager import SendFrameManager
import serial.tools.list_ports

class CANMessageUI(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAN Bus Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.initialize_variables()

        self.setup_ui()

        self.initialize_timers()

    def initialize_variables(self):
        """
        Initialize all class variables.
        """
        self.can_bus = None
        self.can_msg_notifier = None
        self.last_timestamps = {}
        self.can_db = None
        self.can_msg_list = []

        self.first_timestamp = None
        self.total_frames_captured = 0
        self.frames_in_last_second = 0
        self.is_capturing_paused = False
        self.previous_checkbox_state = False

        self.can_intervals_counts = [
            1,          # 5ms
            2,          # 10ms
            4,          # 20ms
            10,         # 50ms
            20,         # 100ms
            100,        # 500ms
            200,        # 1s
            400,        # 2s
            1000,       # 5s
            2000,       # 10s
            6000,       # 30s
            12000,      # 1 min
            60000,      # 5 min
            120000,     # 10 min
            360000,     # 30 min
            720000      # 1 hr
        ]

        self.can_intervals_strings = [
            "5ms",
            "10ms",
            "20ms",
            "50ms",
            "100ms",
            "500ms",
            "1s",
            "2s",
            "5s",
            "10s",
            "30s",
            "1 min",
            "5 min",
            "10 min",
            "30 min",
            "1 hr"
        ]

        self.send_shortcut_keys = ['Ctrl+1', 'Ctrl+2', 'Ctrl+3', 'Ctrl+4', 'Ctrl+5', 'Ctrl+6', 'Ctrl+7', 'Ctrl+8', 'Ctrl+9', 'Ctrl+0']

        self.timestamp_offset = 0.0

        self.can_message_queue = queue.Queue()

        self.connection_radio_group = None

        self.current_sort_order = Qt.AscendingOrder
        self.control_layout_width = 200

        self.can_message_table = CANMessageTable()
        self.connection_manager = ConnectionManager()
        self.dbc_manager = DBCManager()

        self.send_frame_manager = SendFrameManager(self.connection_manager, self.can_message_queue)


    def setup_ui(self):
        """
        Set up the main UI components.
        """
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(1)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle
            {
                background-color: transparent;
                border: none;
            }
        """)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.main_splitter)

        self.setup_tabs()

        self.setup_right_layout()

    def setup_tabs(self):
        """
        Set up the tabs in the left layout.
        """
        self.tab_widget = QTabWidget()
        self.main_splitter.addWidget(self.tab_widget)

        self.can_messages_tab = QWidget()
        self.can_messages_layout = QVBoxLayout(self.can_messages_tab)
        self.can_messages_layout.addWidget(self.can_message_table)
        self.can_messages_tab.setLayout(self.can_messages_layout)
        self.tab_widget.addTab(self.can_messages_tab, "CAN Messages")

        self.send_frames_tab = QWidget()
        self.send_frames_layout = QVBoxLayout(self.send_frames_tab)

        self.send_frames_table = QTableWidget()
        self.send_frames_table.setColumnCount(13)
        self.send_frames_table.setHorizontalHeaderLabels(
            ["ID", "Ext", "RTR", "Len", "D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7", "Send"]
        )
        self.send_frames_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.send_frames_table.setRowCount(10)

        for row in range(10):
            id_input = QLineEdit()
            id_input.setText("0x150")
            id_input.setStyleSheet("color: white;")
            self.send_frames_table.setCellWidget(row, 0, id_input)

            ext_dropdown = QComboBox()
            ext_dropdown.addItems(["Standard", "Extended"])
            self.send_frames_table.setCellWidget(row, 1, ext_dropdown)

            rtr_checkbox = QCheckBox()
            self.send_frames_table.setCellWidget(row, 2, rtr_checkbox)

            dlc_spinbox = QSpinBox()
            dlc_spinbox.setRange(0, 8)
            dlc_spinbox.setValue(8)
            self.send_frames_table.setCellWidget(row, 3, dlc_spinbox)

            fixed_data = ["00", "00", "00", "00", "00", "00", "00", "00"]
            for col in range(4, 12):
                data_input = QLineEdit()
                if col - 4 < dlc_spinbox.value():
                    data_input.setText(fixed_data[col - 4])
                else:
                    data_input.setText("")
                data_input.setStyleSheet("color: white;")
                self.send_frames_table.setCellWidget(row, col, data_input)

            send_button = QPushButton("Send")
            send_button.clicked.connect(lambda _, r=row: self.handle_send_frame(r))
            self.send_frames_table.setCellWidget(row, 12, send_button)

            shortcut = QShortcut(QKeySequence(self.send_shortcut_keys[row]), self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(partial(self.handle_send_frame, row))

        self.send_frames_layout.addWidget(self.send_frames_table)
        self.send_frames_tab.setLayout(self.send_frames_layout)
        self.tab_widget.addTab(self.send_frames_tab, "Send Frames")

        self.connections_tab = QWidget()
        self.setup_connections_tab()
        self.tab_widget.addTab(self.connections_tab, "Connections")

    def setup_connections_tab(self):
        main_layout = QHBoxLayout(self.connections_tab)

        style_sheet = """
            QGroupBox {
                border: 1px solid #888;
                border-radius: 5px;
                margin-top: 1px;
            }
        """
        
        left_group = QGroupBox()
        left_group.setStyleSheet(style_sheet)
        left_layout = QVBoxLayout(left_group)
        self.connection_radio_group = QButtonGroup(self)
        self.radio_pcan = QRadioButton("PCAN")
        self.radio_acan = QRadioButton("ACAN")
        self.radio_udp = QRadioButton("UDP Server")
        self.connection_radio_group.addButton(self.radio_pcan, connect_enum.PCAN)
        self.connection_radio_group.addButton(self.radio_acan, connect_enum.ACAN)
        self.connection_radio_group.addButton(self.radio_udp, connect_enum.SOCKETSERVER)
        self.radio_pcan.setChecked(True)
        radio_style = "QRadioButton:focus { border: none; }"
        self.radio_pcan.setStyleSheet(radio_style)
        self.radio_acan.setStyleSheet(radio_style)
        self.radio_udp.setStyleSheet(radio_style)
        left_layout.addWidget(self.radio_pcan)
        left_layout.addWidget(self.radio_acan)
        left_layout.addWidget(self.radio_udp)
        left_layout.addSpacing(10)
        self.connect_button = self.create_button("Connect", self.toggle_connection)
        self.connect_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745; 
                color: white; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838; 
            }
            QPushButton:pressed {
                background-color: #1e7e34; 
            }
        """)
        left_layout.addWidget(self.connect_button)
        left_layout.addStretch()
        left_group.setFixedWidth(280)
        main_layout.addWidget(left_group, 1)

        right_group = QGroupBox()
        right_group.setStyleSheet(style_sheet)
        right_layout = QVBoxLayout(right_group)
        self.connection_settings_stack = QStackedWidget()

        self.pcan_settings_widget = QWidget()
        self.connection_settings_stack.addWidget(self.pcan_settings_widget)

        self.acan_settings_widget = QWidget()
        acan_layout = QVBoxLayout(self.acan_settings_widget)
        acan_layout.setAlignment(Qt.AlignLeft)
        acan_layout.addWidget(QLabel("Serial Device:"))

        serial_row = QHBoxLayout()
        serial_label = QLabel("Serial Device:")
        serial_row.addWidget(serial_label)
        self.acan_port_combo = QComboBox()
        self.acan_port_combo.setFixedHeight(30)
        serial_row.addWidget(self.acan_port_combo)
        self.acan_refresh_button = self.create_button("Refresh", self.refresh_serial_ports)
        self.acan_refresh_button.setFixedWidth(80)
        serial_row.addWidget(self.acan_refresh_button)
        serial_row.addStretch()

        acan_layout.addLayout(serial_row)
        acan_layout.addStretch()
        self.connection_settings_stack.addWidget(self.acan_settings_widget)

        self.udp_settings_widget = QWidget()
        udp_layout = QVBoxLayout(self.udp_settings_widget)
        udp_layout.setAlignment(Qt.AlignLeft)

        ip_label = QLabel("IP Address:")
        port_label = QLabel("Port:")
        label_width = max(ip_label.sizeHint().width(), port_label.sizeHint().width())
        ip_label.setFixedWidth(label_width)
        port_label.setFixedWidth(label_width)

        ip_row = QHBoxLayout()
        ip_row.addWidget(ip_label)
        self.udp_ip_edit = QLineEdit("127.0.0.1")
        self.udp_ip_edit.setFixedWidth(120)
        ip_row.addWidget(self.udp_ip_edit)
        ip_row.addStretch()
        udp_layout.addLayout(ip_row)

        port_row = QHBoxLayout()
        port_row.addWidget(port_label)
        self.udp_port_edit = QLineEdit("12345")
        self.udp_port_edit.setFixedWidth(120)
        port_row.addWidget(self.udp_port_edit)
        port_row.addStretch()
        udp_layout.addLayout(port_row)

        udp_layout.addStretch()
        self.connection_settings_stack.addWidget(self.udp_settings_widget)

        right_layout.addWidget(self.connection_settings_stack)
        main_layout.addWidget(right_group, 2)

        self.connection_radio_group.buttonClicked.connect(self.on_radio_changed)
        self.on_radio_changed()

    def on_radio_changed(self, button=None):
        idx = self.connection_radio_group.checkedId()
        if idx == connect_enum.PCAN:
            self.connection_settings_stack.setCurrentIndex(0)
        elif idx == connect_enum.ACAN:
            self.connection_settings_stack.setCurrentIndex(1)
            self.refresh_serial_ports()
        elif idx == connect_enum.SOCKETSERVER:
            self.connection_settings_stack.setCurrentIndex(2)
    
    
    def refresh_serial_ports(self):
        """Refresh the list of available serial ports for ACAN."""
        self.acan_port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.acan_port_combo.addItem(port.device)
    
    def setup_right_layout(self):
        """
        Set up the right layout for controls.
        """
        self.right_widget = QWidget()
        self.right_layout = QVBoxLayout(self.right_widget)

        self.capture_frame_button = self.create_button("Suspend Capturing", self.toggle_pause)
        self.clear_frame_button = self.create_button("Clear Frames", self.clear_frame_button_callback)

        self.control_layout = QVBoxLayout()

        self.total_frames_text_label = QLabel("Total Frames Captured")
        self.total_frames_text_label.setStyleSheet("color: white;")
        self.total_frames_text_label.setAlignment(Qt.AlignCenter)

        self.total_frames_value_label = QLabel("0")
        self.total_frames_value_label.setStyleSheet("color: white;")
        self.total_frames_value_label.setAlignment(Qt.AlignCenter)

        self.total_frames_layout = QVBoxLayout()
        self.total_frames_layout.addWidget(self.total_frames_text_label)
        self.total_frames_layout.addWidget(self.total_frames_value_label)
        self.total_frames_layout.setAlignment(Qt.AlignCenter)

        self.fps_text_label = QLabel("Frames Per Second")
        self.fps_text_label.setStyleSheet("color: white;")
        self.fps_text_label.setAlignment(Qt.AlignCenter)

        self.fps_value_label = QLabel("0")
        self.fps_value_label.setStyleSheet("color: white;")
        self.fps_value_label.setAlignment(Qt.AlignCenter)

        self.fps_layout = QVBoxLayout()
        self.fps_layout.addWidget(self.fps_text_label)
        self.fps_layout.addWidget(self.fps_value_label)
        self.fps_layout.setAlignment(Qt.AlignCenter)

        self.control_layout.addLayout(self.total_frames_layout)
        self.control_layout.addLayout(self.fps_layout)
        self.control_layout.addWidget(self.capture_frame_button)
        self.control_layout.addWidget(self.clear_frame_button)
        self.control_layout.setAlignment(Qt.AlignCenter)

        self.checkbox_and_buttons_layout = QVBoxLayout()

        self.overwrite_checkbox = self.create_checkbox("Overwrite Data", self.overwrite_callback)
        self.autoscroll_checkbox = self.create_checkbox("Autoscroll", self.autoscroll_callback)
        self.autoscroll_checkbox.setChecked(False)
        self.interpret_frames_checkbox = self.create_checkbox("Interpret Frames", self.interpret_frames_callback)
        self.interpret_frames_checkbox.setEnabled(False)

        self.checkbox_and_buttons_layout.addWidget(self.overwrite_checkbox)
        self.checkbox_and_buttons_layout.addWidget(self.autoscroll_checkbox)
        self.checkbox_and_buttons_layout.addWidget(self.interpret_frames_checkbox)
        
        self.control_layout.addLayout(self.checkbox_and_buttons_layout)

        self.dbc_status_label = QLabel("DBC File: None")
        self.dbc_status_label.setStyleSheet("""
            QLabel 
            {
                color: white;
                padding: 0px; 
            }
        """)
        self.load_dbc_button = self.create_button("Load DBC File", self.load_dbc_file)

        self.control_layout.addWidget(self.dbc_status_label)
        self.control_layout.addWidget(self.load_dbc_button)

        self.control_group = QGroupBox("")
        self.control_group.setLayout(self.control_layout)
        self.right_layout.addWidget(self.control_group)

        self.right_layout.addStretch()

        self.main_splitter.addWidget(self.right_widget)
        self.right_widget.setFixedWidth(self.control_layout_width)

        self.right_layout.setContentsMargins(0, 0, 0, 0)

    def initialize_timers(self):
        """
        Initialize timers for periodic tasks.
        """
        self.fps_timer = QTimer()
        self.fps_timer.timeout.connect(self.task_1s)
        self.fps_timer.start(1000)

        self.gui_update_timer = QTimer()
        self.gui_update_timer.timeout.connect(self.task_1ms)
        self.gui_update_timer.start(1)

    def create_can_messages_tab(self):
        """
        Create the CAN Messages tab and initialize the table.
        """
        self.can_messages_tab = QWidget()
        self.can_messages_layout = QVBoxLayout(self.can_messages_tab)

        self.can_messages_layout.addWidget(self.can_message_table)

        self.can_messages_tab.setLayout(self.can_messages_layout)
        self.tab_widget.addTab(self.can_messages_tab, "CAN Messages")

    def create_button(self, text, callback):
        """
        Create a button with the specified text and callback function.
        """
        button = QPushButton(text)
        button.setFixedHeight(20)
        button.setStyleSheet("""
            QPushButton
            { 
                background-color: #505050;
                color: white;
                border-radius: 3px;
                padding: 0px 0px;
            }
            QPushButton:hover 
            { 
                background-color: #606060;
            }
            QPushButton:pressed 
            { 
                background-color: #707070;
            }
        """)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button.clicked.connect(callback)
        return button

    def create_checkbox(self, text, callback = None):
        """
        Create a checkbox with the specified text and callback function.
        """
        checkbox = QCheckBox(text)
        checkbox.setStyleSheet("""
            QCheckBox 
            {
                color: white;
                padding: 5px; 
            }
        """)
        checkbox.setChecked(False)
        if callback:
            checkbox.stateChanged.connect(callback)

        return checkbox

    def connection_button_style(self, state):
        """
        Update the style of the connection button based on the connection state.
        """
        if state == con_button.CONNECT:
            print("[DEBUG] Device is connected")
            self.connect_button.setText("Connect")
            self.connect_button.setStyleSheet("""
                QPushButton { 
                    background-color: #28a745;
                }
                QPushButton:hover {
                    background-color: #218838; 
                }
                QPushButton:pressed {
                    background-color: #1e7e34; 
                }
            """)
        else:
            self.connect_button.setText("Disconnect")
            self.connect_button.setStyleSheet("""
                QPushButton { 
                    background-color: #dc3545;
                }
                QPushButton:hover {
                    background-color: #c82333; 
                }
                QPushButton:pressed {
                    background-color: #bd2130; 
                }
            """)
            print("[DEBUG] Device is disconnected")

    def clear_frame_button_callback(self):
        """
        Clear the CAN message table.
        """
        self.can_message_table.clear_table()
        self.total_frames_captured = 0
        self.frames_in_last_second = 0
        self.total_frames_value_label.setText("0")
        self.fps_value_label.setText("0")
        self.first_timestamp = None
        self.last_timestamps.clear()
        self.can_msg_list.clear()

    def load_dbc_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select DBC File", "", "DBC Files (*.dbc);;All Files (*)")

        ins = time.time()

        if file_path:
            keep_prefixes = (
                "VERSION", "NS_", "BS_", "BU_", "BO_", "SG_", "CM_", "VAL_", "BA_",
                "BA_DEF_", "BA_DEF_DEF_", "BA_DEF_DEF_REL_", "BA_REL_", "SGTYPE_", "SG_MUL_VAL_"
            )

            filtered_lines = []
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if any(line.strip().startswith(prefix) for prefix in keep_prefixes):
                        filtered_lines.append(line)

            import tempfile
            temp_path = os.path.join(tempfile.gettempdir(), "filtered_dbc.dbc")
            with open(temp_path, "w") as out:
                out.writelines(filtered_lines)

            success, message = self.dbc_manager.load_dbc_file(temp_path)
            if success:
                QMessageBox.information(self, "DBC File Loaded", message)
                print("[DEBUG] " + message)

                self.dbc_status_label.setText(f"DBC File: {os.path.basename(file_path)}")
                self.interpret_frames_checkbox.setEnabled(True)
            else:
                QMessageBox.critical(self, "Error", message)
                print(f"[ERROR] {message}")
                self.dbc_status_label.setText("DBC File: None")
                self.interpret_frames_checkbox.setEnabled(False)

            try:
                os.remove(temp_path)
            except:
                pass
        
            print(f"[DEBUG] DBC file loaded in {time.time() - ins:.2f} seconds")

        else:
            self.dbc_status_label.setText("DBC File: None")
            self.interpret_frames_checkbox.setEnabled(False)
            
    def toggle_pause(self):
        """
        Toggle the paused state of the CAN message reception.
        """
        if self.is_capturing_paused:
            success = self.connection_manager.resume(self.on_message_received)
            if success:
                self.can_message_table.clear_table()
                self.capture_button_set_state(capture_state.CAPTURE)
                self.total_frames_captured = 0
                print("[DEBUG] Resumed CAN message reception.")
        else:
            success = self.connection_manager.suspend()
            if success:
                self.capture_button_set_state(capture_state.PAUSE)
                print("[DEBUG] Suspended CAN message reception.")

    def create_non_editable_item(self, text):
        """
        Create a QTableWidgetItem that is not editable.
        """
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def overwrite_callback(self, state):
        """
        Handle the state change of the overwrite checkbox.
        Clear the raw CAN data table whenever the checkbox is toggled.
        """
        self.can_message_table.clear_table()

        if state == 2:
            self.can_message_table.can_msg_table_set_header(can_msg_table_header.TIME_DELTA_HEADER)
            self.last_timestamps.clear()
            self.first_timestamp = None
        else:
            if self.interpret_frames_checkbox.isChecked():
                self.interpret_frames_checkbox.setChecked(False)
            print("[DEBUG] Overwrite checkbox state changed:", state)
            self.can_message_table.can_msg_table_set_header(can_msg_table_header.TIME_STAMP_HEADER)
            self.first_timestamp = None

        self.previous_checkbox_state = (state == 2)

    def handle_send_frame(self, row):
        """
        Handle the Send button click to send a CAN frame for a specific row.
        """
        try:
            id_input = self.send_frames_table.cellWidget(row, 0)
            ext_dropdown = self.send_frames_table.cellWidget(row, 1)
            rtr_checkbox = self.send_frames_table.cellWidget(row, 2)
            dlc_spinbox = self.send_frames_table.cellWidget(row, 3)

            can_id = int(id_input.text(), 16)
            is_extended = ext_dropdown.currentText() == "Extended"
            is_rtr = rtr_checkbox.isChecked()
            dlc = dlc_spinbox.value()

            data = []
            for col in range(4, 4 + dlc):
                data_input = self.send_frames_table.cellWidget(row, col)
                byte_str = data_input.text()
                if byte_str:
                    data.append(int(byte_str, 16))
                else:
                    data.append(0)

            success, message = self.send_frame_manager.send_frame(can_id, is_extended, is_rtr, dlc, data)
            if success:
                print(f"[DEBUG] Row {row + 1}: {message}")
            else:
                print(f"[ERROR] Row {row + 1}: {message}")
        except ValueError:
            print(f"[ERROR] Row {row + 1}: Invalid input. Ensure all fields are in the correct format.")

    def autoscroll_callback(self, state):
        """
        Handle the state change of the autoscroll checkbox.
        """
        if state == 2:
            self.can_message_table.toggle_autoscroll(True)
        else:
            self.can_message_table.toggle_autoscroll(False)

    def interpret_frames_callback(self, state):
        """
        Handle the state change of the "Interpret Frames" checkbox.
        """
        print("[DEBUG] Interpret Frames checkbox state changed:", state)
        if state == 2:
            self.overwrite_checkbox.setChecked(True)
            self.can_message_table.model.overwrite_mode = True
            print("[DEBUG] Interpret Frames enabled. Table is in overwrite mode.")
        else:
            self.overwrite_checkbox.setChecked(False)
            self.can_message_table.model.overwrite_mode = False
            print("[DEBUG] Interpret Frames disabled.")

    def table_sort_callback(self, column_index):
        """
        Sort the table by the clicked column in ascending or descending order.
        """
        print("[DEBUG] Sorting column:", column_index)
        if not self.can_msg_notifier:
            if self.current_sort_order == Qt.AscendingOrder:
                self.current_sort_order = Qt.DescendingOrder
            else:
                self.current_sort_order = Qt.AscendingOrder

            print(f"[DEBUG] Sorting column {column_index} in {'ascending' if self.current_sort_order == Qt.AscendingOrder else 'descending'} order")

        self.can_msg_table.sortItems(column_index, self.current_sort_order)

    def capture_button_set_state(self, state):
        match state:
            case capture_state.CAPTURE:
                self.capture_frame_button.setText("Suspend Capturing")
                self.is_capturing_paused = False
            
            case capture_state.PAUSE:
                self.capture_frame_button.setText("Resume Capturing")
                self.is_capturing_paused = True

            case _:
                return False


    def create_non_editable_item(self, text):
        """
        Create a QTableWidgetItem that is not editable.
        """
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def toggle_connection(self):
        """
        Toggle the connection to the selected device type.
        """
        selected_id = self.connection_radio_group.checkedId()
        selected_type = connect_enum(selected_id)

        params = {}
        if selected_type == connect_enum.ACAN:
            params['port'] = self.acan_port_combo.currentText()
        elif selected_type == connect_enum.SOCKETSERVER:
            params['ip'] = self.udp_ip_edit.text()
            params['port'] = self.udp_port_edit.text()

        if not self.connection_manager.is_connected():
            success = self.connection_manager.connect(self.on_message_received, selected_type, params)
            if success:
                self.first_timestamp = None
                self.connection_button_style(con_button.DISCONNECT)
                self.clear_frame_button_callback()
                self.send_frame_manager.set_connection_type(selected_type)
                print(f"[DEBUG] Connected to {selected_type.name}.")
            else:
                QMessageBox.critical(self, "Error", f"Failed to connect to {selected_type.name}.")
        else:
            success = self.connection_manager.disconnect()
            if success:
                self.connection_button_style(con_button.CONNECT)
                print("[DEBUG] Disconnected.")
            else:
                QMessageBox.critical(self, "Error", "Failed to disconnect.")


    def on_message_received(self, msg):
        """
        Callback function that gets called whenever a CAN message is received.
        """
        if self.is_capturing_paused:
            return

        self.frames_in_last_second += 1
        self.can_message_queue.put(msg)

    def decode_data(self, can_id, data):
        """
        Decode the CAN message using the DBCManager and return the formatted data string.
        """
        decoded_signals, error = self.dbc_manager.decode_message(can_id, data)

        # Get CAN message name from DBC if available
        can_id_name = ""
        if self.dbc_manager.can_db:
            try:
                message = self.dbc_manager.can_db.get_message_by_frame_id(can_id)
                can_id_name = f"\t<{message.name}>"
            except Exception:
                can_id_name = ""

        raw_data_str = " ".join(f"0x{byte:02X}" for byte in data)
        raw_data_str += can_id_name + "\n"

        if error:
            decoded_data_str = f"Decoding Error: {error}"
        else:
            decoded_data_str = "\n".join([f"{signal}: {value}" for signal, value in decoded_signals.items()])

        return f"{raw_data_str}\n{decoded_data_str}"

    def task_1s(self):
        """
        Tasks runs for every second.
        """
        self.task_fps_update()

    def task_fps_update(self):
        """
        Update the FPS label every second.
        """
        self.fps_value_label.setText(f"{self.frames_in_last_second}")
        self.frames_in_last_second = 0

    def process_received_message(self, msg):
        """
        Process the received CAN message and enqueue it for batch GUI updates.
        """
        if self.is_capturing_paused:
            return
        
        self.can_message_queue.put(msg)

    def calculate_timestamp_diff(self, first_timestamp, current_timestamp):
        """
        Calculate the timestamp difference in microseconds.
        """
        self.timestamp_offset = current_timestamp - first_timestamp

    def task_1ms(self):
        """
        Dequeue messages from the thread-safe queue and update the GUI in batches.
        """
        while not self.can_message_queue.empty():
            try:
                msg = self.can_message_queue.get_nowait()

                self.can_msg_list.append(msg)

                self.total_frames_captured += 1
                self.total_frames_value_label.setText(f"{self.total_frames_captured}")

                if not self.overwrite_checkbox.isChecked() and self.first_timestamp is None:
                    self.first_timestamp = msg.timestamp
                    self.calculate_timestamp_diff(self.first_timestamp, time.time())
                    print(f"[DEBUG] TimeDiff: {self.timestamp_offset}")

                can_id = msg.arbitration_id
                if self.overwrite_checkbox.isChecked():
                    if can_id in self.last_timestamps:
                        timestamp_diff = msg.timestamp - self.last_timestamps[can_id]
                    else:
                        timestamp_diff = 0.0
                    self.last_timestamps[can_id] = msg.timestamp
                else:
                    if self.first_timestamp is not None:
                        timestamp_diff = msg.timestamp - self.first_timestamp
                    else:
                        timestamp_diff = 0.0

                if timestamp_diff < 0:
                    timestamp_diff = 0.0
                    self.first_timestamp = msg.timestamp
                    self.calculate_timestamp_diff(self.first_timestamp, time.time())

                if not msg.is_rx:
                    if (self.overwrite_checkbox.isChecked() or self.interpret_frames_checkbox.isChecked()):
                        continue
                    else:
                        if timestamp_diff != 0:
                            if self.first_timestamp < 0:
                                timestamp_diff += self.timestamp_offset
                            else:
                                timestamp_diff -= self.timestamp_offset

                if self.overwrite_checkbox.isChecked():
                    timestamp = int(timestamp_diff * 1000)
                else:
                    timestamp = int(timestamp_diff * 1000000)

                timestamp = f"{timestamp}"

                extended = "1" if msg.is_extended_id else "0"
                rtr = "1" if msg.is_remote_frame else "0"
                direction = "Rx" if msg.is_rx else "Tx"
                dlc = msg.dlc

                if self.interpret_frames_checkbox.isChecked():
                    data_column_content = self.decode_data(can_id, msg.data)
                else:
                    raw_data_str = " ".join(f"0x{byte:02X}" for byte in msg.data)
                    data_column_content = f"{raw_data_str}"

                over_write_mode = False
                if self.overwrite_checkbox.isChecked() or self.interpret_frames_checkbox.isChecked():
                    over_write_mode = True
                
                self.can_message_table.update_table(
                    timestamp=timestamp,
                    can_id=f"0x{can_id:X}",
                    extended=extended,
                    rtr=rtr,
                    direction=direction,
                    dlc=dlc,
                    data=data_column_content,
                    overwrite=over_write_mode
                )
            except queue.Empty:
                pass
    
    def task_msg_check(self):
        """
        Check if the CAN message is received and process it.
        """
        if self.can_message_queue.empty():
            return
        
        for loop_index in range(3):
            pass

    def closeEvent(self, event):
        """
        Handle the application close event.
        """
        if self.on_exit():
            event.accept()
        else:
            event.ignore()

    def on_exit(self):
        """
        Perform cleanup and confirm exit.
        """
        reply = QMessageBox.question(
            self,
            "Exit Confirmation",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.connection_manager.disconnect()

            print("[DEBUG] Exiting application...")
            return True
        else:
            print("[DEBUG] Exit canceled.")
            return False



