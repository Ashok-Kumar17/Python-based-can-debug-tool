from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtWidgets import QTableView, QHeaderView
from can_enums import can_msg_table_header


class CANMessageTableModel(QAbstractTableModel):
    def __init__(self, headers, parent=None):
        """
        Initialize the CANMessageTableModel.
        """
        super().__init__(parent)
        self.headers = headers
        self.data_rows = []


    def rowCount(self, parent=QModelIndex()):
        """
        Return the number of rows in the table.
        """
        return len(self.data_rows)

    def columnCount(self, parent=QModelIndex()):
        """
        Return the number of columns in the table.
        """
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        """
        Return the data for a given cell.
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return str(index.row() + 1)
            return self.data_rows[index.row()][index.column() - 1]

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Return the header data for the table.
        """
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]

        return None

    def clear_table(self):
        """
        Clear all rows in the table.
        """
        self.beginResetModel()
        self.data_rows = []
        self.endResetModel()

    def update_table(self, timestamp, can_id, extended, rtr, direction, dlc, data, overwrite=False, interpret=False):
        """
        Update the table with a new CAN message.
        - In overwrite or interpret mode, update the row with the same CAN ID or insert in ascending order.
        - In normal mode, append the row sequentially.
        """
        column_data = [
            timestamp,
            can_id,
            extended,
            rtr,
            direction,
            str(dlc),
            data
        ]

        if overwrite or interpret:
            for row_index, row in enumerate(self.data_rows):
                if row[1] == can_id:
                    self.data_rows[row_index] = column_data
                    self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, len(column_data) - 1))
                    return row_index

            insert_index = 0
            for row_index, row in enumerate(self.data_rows):
                if can_id < row[1]:
                    insert_index = row_index
                    break
            else:
                insert_index = len(self.data_rows)

            self.beginInsertRows(QModelIndex(), insert_index, insert_index)
            self.data_rows.insert(insert_index, column_data)
            self.endInsertRows()
            return insert_index

        else:
            self.beginInsertRows(QModelIndex(), len(self.data_rows), len(self.data_rows))
            self.data_rows.append(column_data)
            self.endInsertRows()
            return len(self.data_rows) - 1

class CANMessageTable(QTableView):
    def __init__(self, parent=None):
        """
        Initialize the CANMessageTable as a QTableView with a custom model.
        """
        super().__init__(parent)

        self.headers = ["", "Timestamp", "ID", "Ext", "RTR", "Dir", "Len", "Data"]
        self.timestamp_index = self.headers.index("Timestamp")

        self.model = CANMessageTableModel(self.headers)
        self.setModel(self.model)

        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QTableView {
                background-color: #1F1F1F;
                alternate-background-color: #2E2E2E;
                gridline-color: #707070;
                color: white;
                border: 1px solid #4F4F4F;
            }
        """)

        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(len(self.headers) - 1, QHeaderView.Stretch)

        self.autoscroll_enabled = False

    def clear_table(self):
        """
        Clear all rows in the table.
        """
        self.model.clear_table()

    def update_table(self, timestamp, can_id, extended, rtr, direction, dlc, data, overwrite=False, interpret=False):
        """
        Update the table with a new CAN message.
        """
        row_index = self.model.update_table(timestamp, can_id, extended, rtr, direction, dlc, data, overwrite, interpret)

        if overwrite:
            self.resizeRowToContents(row_index)

        if self.autoscroll_enabled:
            self.scrollToBottom()

        self.viewport().update()

    def can_msg_table_set_header(self, header):
        """
        Set the header for the CAN message table.
        """
        if header == can_msg_table_header.TIME_STAMP_HEADER:
            self.model.headers[self.timestamp_index] = "Timestamp"
            print("[DEBUG] Timestamp set")
        elif header == can_msg_table_header.TIME_DELTA_HEADER:
            self.model.headers[self.timestamp_index] = "Time Delta"
            print("[DEBUG] Time Delta header set")
        else:
            return False

    def toggle_autoscroll(self, enabled):
        """
        Enable or disable autoscrolling.
        """
        self.autoscroll_enabled = enabled