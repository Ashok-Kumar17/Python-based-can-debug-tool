from enum import IntEnum


class capture_state(IntEnum):
    """
    Enum for capture states.
    """
    CAPTURE = 0
    PAUSE   = 1
    STOP    = 2

class con_button(IntEnum):
    """
    Enum for connection button states.
    """
    CONNECT     = 0
    DISCONNECT  = 1

class can_msg_table_header(IntEnum):
    """
    Enum for CAN message table headers.
    """
    TIME_STAMP_HEADER   = 0
    TIME_DELTA_HEADER   = 1

class connect_enum(IntEnum):
    """
    Enum class to define connection types.
    """
    NONE = 0,
    PCAN = 1,
    ACAN = 2,
    SOCKETSERVER = 3
