import sys
import time
import math
import random
from dataclasses import dataclass
from typing import Optional, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QMessageBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
)

# Optional CAN support. The app still works in mock mode without python-can.
try:
    import can  # type: ignore
except Exception:
    can = None


# -------------------------------
# CAN frame helpers
# -------------------------------
@dataclass
class CanFrame:
    arbitration_id: int
    data: List[int]
    direction: str  # "TX" or "RX"
    name: str
    timestamp: float


class VcuProtocol:
    SET_PARAM_ID = 0xAAA
    GET_PARAM_ID = 0xBBB
    PARAM_RESPONSE_ID = 0xCCC
    TOGGLE_STATE_ID = 0xABA
    STATE_1_ID = 0x12A
    STATE_2_ID = 0x12B
    STATE_3_ID = 0x12C

    @staticmethod
    def checksum_simple(data_without_checksum: List[int]) -> int:
        return sum(data_without_checksum) & 0xFF

    @staticmethod
    def split_u16(value: int) -> List[int]:
        return [(value >> 8) & 0xFF, value & 0xFF]

    @staticmethod
    def split_u40(value: int) -> List[int]:
        return [
            (value >> 32) & 0xFF,
            (value >> 24) & 0xFF,
            (value >> 16) & 0xFF,
            (value >> 8) & 0xFF,
            value & 0xFF,
        ]

    @staticmethod
    def join_u40(bytes_5: List[int]) -> int:
        value = 0
        for b in bytes_5:
            value = (value << 8) | (b & 0xFF)
        return value

    @classmethod
    def build_set_param(cls, param_id: int, value: int) -> CanFrame:
        pid = cls.split_u16(param_id)
        val = cls.split_u40(value)
        payload = pid + val
        checksum = cls.checksum_simple(payload)
        payload.append(checksum)
        return CanFrame(cls.SET_PARAM_ID, payload, "TX", "Set VCU Parameter", time.time())

    @classmethod
    def build_get_param(cls, param_id_low_byte: int) -> CanFrame:
        payload = [param_id_low_byte & 0xFF]
        return CanFrame(cls.GET_PARAM_ID, payload, "TX", "Get VCU Parameter", time.time())

    @classmethod
    def build_toggle_state(cls, value: int) -> CanFrame:
        payload = [value & 0xFF]
        return CanFrame(cls.TOGGLE_STATE_ID, payload, "TX", "Toggle VCU State", time.time())

    @classmethod
    def decode_param_response(cls, data: List[int]) -> dict:
        if len(data) != 8:
            return {"valid": False, "error": "Expected 8 bytes"}
        pid = (data[0] << 8) | data[1]
        value = cls.join_u40(data[2:7])
        checksum = data[7]
        calc = cls.checksum_simple(data[:7])
        return {
            "valid": checksum == calc,
            "param_id": pid,
            "value": value,
            "checksum": checksum,
            "expected_checksum": calc,
        }


# -------------------------------
# Transport layer
# -------------------------------
class MockCanBackend:
    def __init__(self):
        self.rx_queue: List[CanFrame] = []
        self.requested_torque = 0
        self.actual_torque = 0
        self.speed_kph = 0
        self.mode = 1
        self.fault = False
        self.last_param_id = 0
        self.last_param_value = 0

    def send(self, frame: CanFrame):
        if frame.arbitration_id == VcuProtocol.SET_PARAM_ID and len(frame.data) == 8:
            self.last_param_id = (frame.data[0] << 8) | frame.data[1]
            self.last_param_value = VcuProtocol.join_u40(frame.data[2:7])

            # Demo assumption: param 0x0001 = requested torque in Nm
            if self.last_param_id == 0x0001:
                self.requested_torque = min(self.last_param_value, 1000)

            response = CanFrame(
                VcuProtocol.PARAM_RESPONSE_ID,
                frame.data.copy(),
                "RX",
                "VCU Parameter Response",
                time.time(),
            )
            self.rx_queue.append(response)

        elif frame.arbitration_id == VcuProtocol.GET_PARAM_ID and len(frame.data) == 1:
            requested_low = frame.data[0]
            if requested_low == 0x01:
                pid = [0x00, 0x01]
                val = VcuProtocol.split_u40(int(self.requested_torque))
            else:
                pid = [0x00, requested_low]
                val = VcuProtocol.split_u40(self.last_param_value)
            data7 = pid + val
            checksum = VcuProtocol.checksum_simple(data7)
            response = CanFrame(
                VcuProtocol.PARAM_RESPONSE_ID,
                data7 + [checksum],
                "RX",
                "VCU Parameter Response",
                time.time(),
            )
            self.rx_queue.append(response)

        elif frame.arbitration_id == VcuProtocol.TOGGLE_STATE_ID and len(frame.data) == 1:
            self.mode = frame.data[0]

    def tick(self):
        # Simulate actual torque following requested torque
        delta = self.requested_torque - self.actual_torque
        self.actual_torque += delta * 0.2
        self.actual_torque += random.uniform(-3, 3)
        self.actual_torque = max(0, min(1000, self.actual_torque))

        self.speed_kph += random.uniform(-1.5, 2.0)
        self.speed_kph = max(0, min(160, self.speed_kph))

        if random.random() < 0.02:
            self.fault = not self.fault

        # Broadcast 1: requested torque, actual torque, speed, fault, mode
        req = int(self.requested_torque)
        act = int(self.actual_torque)
        spd = int(self.speed_kph)
        data_12a = [
            (req >> 8) & 0xFF,
            req & 0xFF,
            (act >> 8) & 0xFF,
            act & 0xFF,
            (spd >> 8) & 0xFF,
            spd & 0xFF,
            1 if self.fault else 0,
            self.mode & 0xFF,
        ]
        self.rx_queue.append(
            CanFrame(VcuProtocol.STATE_1_ID, data_12a, "RX", "VCU State Broadcast 1", time.time())
        )

        # Broadcast 2: spare demo bytes
        data_12b = [random.randint(0, 255) for _ in range(8)]
        self.rx_queue.append(
            CanFrame(VcuProtocol.STATE_2_ID, data_12b, "RX", "VCU State Broadcast 2", time.time())
        )

        # Broadcast 3: fault summary byte
        data_12c = [1 if self.fault else 0]
        self.rx_queue.append(
            CanFrame(VcuProtocol.STATE_3_ID, data_12c, "RX", "VCU State Broadcast 3", time.time())
        )

    def receive_all(self) -> List[CanFrame]:
        frames = self.rx_queue[:]
        self.rx_queue.clear()
        return frames


class PythonCanBackend:
    def __init__(self, channel: str = "can0", bustype: str = "socketcan"):
        if can is None:
            raise RuntimeError("python-can is not installed")
        self.bus = can.interface.Bus(channel=channel, bustype=bustype)

    def send(self, frame: CanFrame):
        msg = can.Message(
            arbitration_id=frame.arbitration_id,
            data=bytearray(frame.data),
            is_extended_id=False,
        )
        self.bus.send(msg)

    def tick(self):
        pass

    def receive_all(self) -> List[CanFrame]:
        frames = []
        while True:
            msg = self.bus.recv(timeout=0.0)
            if msg is None:
                break
            name = {
                VcuProtocol.PARAM_RESPONSE_ID: "VCU Parameter Response",
                VcuProtocol.STATE_1_ID: "VCU State Broadcast 1",
                VcuProtocol.STATE_2_ID: "VCU State Broadcast 2",
                VcuProtocol.STATE_3_ID: "VCU State Broadcast 3",
            }.get(msg.arbitration_id, "RX Frame")
            frames.append(
                CanFrame(
                    arbitration_id=msg.arbitration_id,
                    data=list(msg.data),
                    direction="RX",
                    name=name,
                    timestamp=time.time(),
                )
            )
        return frames


# -------------------------------
# GUI
# -------------------------------
class ValueCard(QGroupBox):
    def __init__(self, title: str, default_text: str = "--"):
        super().__init__(title)
        layout = QVBoxLayout()
        self.value_label = QLabel(default_text)
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        layout.addWidget(self.value_label)
        self.setLayout(layout)

    def set_value(self, text: str, color: Optional[str] = None):
        css = "font-size: 24px; font-weight: bold; padding: 10px;"
        if color:
            css += f" color: {color};"
        self.value_label.setStyleSheet(css)
        self.value_label.setText(text)


class SimpleGraph(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFixedHeight(170)
        self.values_req: List[int] = []
        self.values_act: List[int] = []

    def push(self, requested: int, actual: int):
        self.values_req.append(requested)
        self.values_act.append(actual)
        max_points = 40
        self.values_req = self.values_req[-max_points:]
        self.values_act = self.values_act[-max_points:]
        self.redraw()

    def redraw(self):
        if not self.values_req:
            self.setPlainText("No graph data yet")
            return

        width = len(self.values_req)
        height = 12
        grid = [[" " for _ in range(width)] for _ in range(height)]
        max_val = max(max(self.values_req), max(self.values_act), 1)

        for x in range(width):
            rq = self.values_req[x]
            ac = self.values_act[x]
            y_rq = height - 1 - int((rq / max_val) * (height - 1))
            y_ac = height - 1 - int((ac / max_val) * (height - 1))
            grid[y_rq][x] = "R"
            if grid[y_ac][x] == "R":
                grid[y_ac][x] = "*"
            else:
                grid[y_ac][x] = "A"

        text = "Requested=R  Actual=A  Both=*\n\n"
        for row in grid:
            text += "".join(row) + "\n"
        self.setPlainText(text)


class VcuDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VCU Torque Dashboard")
        self.resize(1300, 820)

        self.backend_mode = "Mock"
        self.backend = MockCanBackend()

        self.requested_torque = 0
        self.actual_torque = 0
        self.speed_kph = 0
        self.fault_active = False
        self.mode_value = 1

        self.build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_backend)
        self.timer.start(200)

    def build_ui(self):
        root = QVBoxLayout()

        top_row = QHBoxLayout()
        self.connection_box = QGroupBox("Connection")
        conn_layout = QGridLayout()

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Mock", "python-can"])

        self.channel_input = QLineEdit("can0")
        self.bustype_input = QLineEdit("socketcan")
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_backend)

        conn_layout.addWidget(QLabel("Mode:"), 0, 0)
        conn_layout.addWidget(self.backend_combo, 0, 1)
        conn_layout.addWidget(QLabel("Channel:"), 1, 0)
        conn_layout.addWidget(self.channel_input, 1, 1)
        conn_layout.addWidget(QLabel("Bus Type:"), 2, 0)
        conn_layout.addWidget(self.bustype_input, 2, 1)
        conn_layout.addWidget(self.connect_button, 3, 0, 1, 2)
        self.connection_box.setLayout(conn_layout)
        top_row.addWidget(self.connection_box, 1)

        cards_box = QGroupBox("Live Status")
        cards_layout = QGridLayout()
        self.request_card = ValueCard("Requested Torque")
        self.actual_card = ValueCard("Actual Torque")
        self.speed_card = ValueCard("Speed")
        self.mode_card = ValueCard("VCU Mode")
        self.fault_card = ValueCard("Fault")
        cards_layout.addWidget(self.request_card, 0, 0)
        cards_layout.addWidget(self.actual_card, 0, 1)
        cards_layout.addWidget(self.speed_card, 0, 2)
        cards_layout.addWidget(self.mode_card, 1, 0)
        cards_layout.addWidget(self.fault_card, 1, 1)
        cards_box.setLayout(cards_layout)
        top_row.addWidget(cards_box, 3)
        root.addLayout(top_row)

        middle_row = QHBoxLayout()

        send_box = QGroupBox("Send Commands")
        send_layout = QGridLayout()

        self.param_id_input = QLineEdit("0x0001")
        self.param_value_input = QLineEdit("250")
        self.get_param_input = QLineEdit("0x01")
        self.toggle_state_input = QLineEdit("1")
        self.auto_send_checkbox = QCheckBox("Auto-send torque every second")

        self.send_param_button = QPushButton("Send Set Param")
        self.send_param_button.clicked.connect(self.send_set_param)
        self.get_param_button = QPushButton("Send Get Param")
        self.get_param_button.clicked.connect(self.send_get_param)
        self.toggle_button = QPushButton("Send Toggle State")
        self.toggle_button.clicked.connect(self.send_toggle_state)

        send_layout.addWidget(QLabel("Param ID (hex):"), 0, 0)
        send_layout.addWidget(self.param_id_input, 0, 1)
        send_layout.addWidget(QLabel("Value:"), 1, 0)
        send_layout.addWidget(self.param_value_input, 1, 1)
        send_layout.addWidget(self.send_param_button, 2, 0, 1, 2)
        send_layout.addWidget(QLabel("Get Param Low Byte (hex):"), 3, 0)
        send_layout.addWidget(self.get_param_input, 3, 1)
        send_layout.addWidget(self.get_param_button, 4, 0, 1, 2)
        send_layout.addWidget(QLabel("Toggle State Value:"), 5, 0)
        send_layout.addWidget(self.toggle_state_input, 5, 1)
        send_layout.addWidget(self.toggle_button, 6, 0, 1, 2)
        send_layout.addWidget(self.auto_send_checkbox, 7, 0, 1, 2)
        send_box.setLayout(send_layout)
        middle_row.addWidget(send_box, 1)

        graph_box = QGroupBox("Live Torque Graph")
        graph_layout = QVBoxLayout()
        self.graph_widget = SimpleGraph()
        graph_layout.addWidget(self.graph_widget)
        graph_box.setLayout(graph_layout)
        middle_row.addWidget(graph_box, 2)

        raw_box = QGroupBox("Decoded Frame Details")
        raw_layout = QVBoxLayout()
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        raw_layout.addWidget(self.details_text)
        raw_box.setLayout(raw_layout)
        middle_row.addWidget(raw_box, 2)

        root.addLayout(middle_row)

        log_box = QGroupBox("CAN Log")
        log_layout = QVBoxLayout()
        self.log_table = QTableWidget(0, 5)
        self.log_table.setHorizontalHeaderLabels(["Time", "Dir", "ID", "Name", "Data"])
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        log_layout.addWidget(self.log_table)
        log_box.setLayout(log_layout)
        root.addWidget(log_box)

        self.setLayout(root)

        self.auto_send_timer = QTimer(self)
        self.auto_send_timer.timeout.connect(self.send_auto_torque)
        self.auto_send_checkbox.toggled.connect(self.toggle_auto_send)

        self.refresh_cards()

    def connect_backend(self):
        mode = self.backend_combo.currentText()
        try:
            if mode == "Mock":
                self.backend = MockCanBackend()
                self.backend_mode = "Mock"
            else:
                self.backend = PythonCanBackend(
                    channel=self.channel_input.text().strip(),
                    bustype=self.bustype_input.text().strip(),
                )
                self.backend_mode = "python-can"
            QMessageBox.information(self, "Connected", f"Connected using {self.backend_mode} mode.")
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.backend = MockCanBackend()
            self.backend_mode = "Mock"

    def parse_int(self, text: str) -> int:
        text = text.strip().lower()
        if text.startswith("0x"):
            return int(text, 16)
        return int(text)

    def send_frame(self, frame: CanFrame):
        try:
            self.backend.send(frame)
            self.add_log(frame)
        except Exception as e:
            QMessageBox.critical(self, "Send Error", str(e))

    def send_set_param(self):
        try:
            param_id = self.parse_int(self.param_id_input.text())
            value = self.parse_int(self.param_value_input.text())
            frame = VcuProtocol.build_set_param(param_id, value)
            self.send_frame(frame)
        except Exception as e:
            QMessageBox.warning(self, "Bad Input", f"Could not build set param frame:\n{e}")

    def send_get_param(self):
        try:
            param_low = self.parse_int(self.get_param_input.text())
            frame = VcuProtocol.build_get_param(param_low)
            self.send_frame(frame)
        except Exception as e:
            QMessageBox.warning(self, "Bad Input", f"Could not build get param frame:\n{e}")

    def send_toggle_state(self):
        try:
            value = self.parse_int(self.toggle_state_input.text())
            frame = VcuProtocol.build_toggle_state(value)
            self.send_frame(frame)
        except Exception as e:
            QMessageBox.warning(self, "Bad Input", f"Could not build toggle frame:\n{e}")

    def toggle_auto_send(self, checked: bool):
        if checked:
            self.auto_send_timer.start(1000)
        else:
            self.auto_send_timer.stop()

    def send_auto_torque(self):
        try:
            frame = VcuProtocol.build_set_param(0x0001, self.parse_int(self.param_value_input.text()))
            self.send_frame(frame)
        except Exception:
            self.auto_send_checkbox.setChecked(False)

    def poll_backend(self):
        try:
            self.backend.tick()
            frames = self.backend.receive_all()
            for frame in frames:
                self.add_log(frame)
                self.handle_rx_frame(frame)
        except Exception as e:
            self.details_text.append(f"Backend poll error: {e}")

    def handle_rx_frame(self, frame: CanFrame):
        if frame.arbitration_id == VcuProtocol.PARAM_RESPONSE_ID:
            decoded = VcuProtocol.decode_param_response(frame.data)
            self.details_text.append(
                f"Param Response -> param_id=0x{decoded.get('param_id', 0):04X}, "
                f"value={decoded.get('value', 0)}, valid_checksum={decoded.get('valid', False)}"
            )

        elif frame.arbitration_id == VcuProtocol.STATE_1_ID and len(frame.data) == 8:
            self.requested_torque = (frame.data[0] << 8) | frame.data[1]
            self.actual_torque = (frame.data[2] << 8) | frame.data[3]
            self.speed_kph = (frame.data[4] << 8) | frame.data[5]
            self.fault_active = bool(frame.data[6])
            self.mode_value = frame.data[7]
            self.graph_widget.push(self.requested_torque, self.actual_torque)
            self.refresh_cards()
            self.details_text.append(
                f"State 1 -> requested={self.requested_torque} Nm, actual={self.actual_torque} Nm, "
                f"speed={self.speed_kph} kph, fault={self.fault_active}, mode={self.mode_value}"
            )

        elif frame.arbitration_id == VcuProtocol.STATE_2_ID:
            self.details_text.append(
                "State 2 -> raw bytes: " + " ".join(f"{b:02X}" for b in frame.data)
            )

        elif frame.arbitration_id == VcuProtocol.STATE_3_ID and len(frame.data) >= 1:
            self.fault_active = bool(frame.data[0])
            self.refresh_cards()
            self.details_text.append(f"State 3 -> fault summary byte={frame.data[0]}")

        self.trim_details()

    def trim_details(self):
        text = self.details_text.toPlainText().splitlines()
        if len(text) > 120:
            self.details_text.setPlainText("\n".join(text[-120:]))
            cursor = self.details_text.textCursor()
            cursor.movePosition(cursor.End)
            self.details_text.setTextCursor(cursor)

    def refresh_cards(self):
        self.request_card.set_value(f"{self.requested_torque} Nm")
        self.actual_card.set_value(f"{self.actual_torque} Nm")
        self.speed_card.set_value(f"{self.speed_kph} kph")
        self.mode_card.set_value(str(self.mode_value))
        if self.fault_active:
            self.fault_card.set_value("FAULT", "red")
        else:
            self.fault_card.set_value("OK", "green")

    def add_log(self, frame: CanFrame):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        timestamp_text = time.strftime("%H:%M:%S", time.localtime(frame.timestamp))
        data_text = " ".join(f"{b:02X}" for b in frame.data)
        id_text = f"0x{frame.arbitration_id:03X}"

        values = [timestamp_text, frame.direction, id_text, frame.name, data_text]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if frame.direction == "TX":
                item.setBackground(QColor(230, 240, 255))
            elif frame.arbitration_id in (VcuProtocol.STATE_3_ID,) and frame.data and frame.data[0] != 0:
                item.setBackground(QColor(255, 230, 230))
            self.log_table.setItem(row, col, item)

        if row > 300:
            self.log_table.removeRow(0)
        self.log_table.scrollToBottom()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VcuDashboard()
    window.show()
    sys.exit(app.exec())
