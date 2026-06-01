import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import QTimer, Slot, Signal, QFile
from PySide6.QtUiTools import QUiLoader
from peripherals.VCU import VCU
from functools import partial
import pyqtgraph as pg
import time, math
from collections import deque
from superqt import QLabeledDoubleRangeSlider
from PySide6.QtWidgets import QVBoxLayout
import ui.tritonRacingLogo_rc

class DraggablePoint(pg.TargetItem):
    def __init__(self, x, y, index, callback):
        super().__init__(
            pos=(x, y),
            movable=True,
            size=12,
            symbol='o'
        )
        self.index = index
        self.fixed_x = x
        self.callback = callback

        # Called continuously while dragging
        self.sigPositionChanged.connect(self.on_move)

    def on_move(self):
        pos = self.pos()

        # Lock X axis
        self.setPos(self.fixed_x, pos.y())
        if(self.index == 0):
            self.setPos(self.fixed_x, 0)
        if(self.index == 17):
            self.setPos(self.fixed_x, 1)
        if(pos.y() > 1):
            self.setPos(self.fixed_x, 1)
        elif(pos.y() < 0):
            self.setPos(self.fixed_x, 0)
        # Notify parent
        self.callback(self.index, pos.y())

class VCUWidget(QtWidgets.QMainWindow):
    window_closed = Signal()
    logger = Signal(str)
    def __init__(self, peripheral):
        
        super().__init__()
        #add ui file loading here
        self.vcu = peripheral
        
        loader = QUiLoader()
        ui_file = QFile("ui/VCU.ui")
        ui_file.open(QFile.ReadOnly)
        loader.registerCustomWidget(pg.PlotWidget)
        self.window = loader.load(ui_file,None)
        ui_file.close()
        
        central_layout = QVBoxLayout(self.window.centralwidget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(self.window.scrollArea)

        self.setupGraph()
        self.setupApps1RangeSlider()
        self.setupApps2RangeSlider()
        
        self.vcu.dataSignal.connect(self.updateUI)
        #self.apps1ReadTimer = QTimer(self)
        #.apps1ReadTimer.timeout.connect(self.updateApps1CurrentReadings)
        #self.apps1ReadTimer.start(100) 

        self.window.setPedalMapButton.clicked.connect(self.sendPedalMap)
        self.window.sendConfigButton.clicked.connect(self.vcu.writeConfiguration)
        self.window.syncButton.clicked.connect(self.vcu.requestSync)
        # BPS/APPS threshold buttons
        for btn_name, (msg_name) in self.vcu.const.button_map.items():
            getattr(self.window, btn_name).clicked.connect(
                lambda checked=False, msg_name=msg_name: self.vcu.set_param(msg_name))

        #self.window.exitConfig.clicked.connect(self.vcu.disable)
    def closeEvent(self, event):
        self.window_closed.emit()
        event.accept()
    
    def setupGraph(self):
        self.window.pedalGraph.getViewBox().disableAutoRange()
        self.start_time = time.perf_counter()
        self.sources = ["pedalMap"]
        self.buffers = {
            "pedalMap": [0, 0, 0, 0, 0, 0, 0, 0, 0,
                         0, 0, 0, 0, 0, 0, 0, 0, 1],
            "pedalMapVCU": [0, 0, 0, 0, 0, 0, 0, 0, 0,
                            0, 0, 0, 0, 0, 0, 0, 0, 1],
            "x": [x * 6.25 for x in range(18)]
        }
        self.window.pedalGraph.setXRange(0, 100)
        self.window.pedalGraph.setYRange(0, 1)
        self.window.pedalGraph.showGrid(x=True, y=True)
        self.window.pedalGraph.setLabel('bottom', 'Pedal Input %')
        self.window.pedalGraph.setLabel('left', 'Output %')
        self.window.pedalGraph.setMouseEnabled(x=False, y=False)
        # Main mapping curve
        self.curves = {
            "pedalMap": self.window.pedalGraph.plot(
                self.buffers["x"],
                self.buffers["pedalMap"],
                pen=pg.mkPen('r', width=1.5),
                name="Local"
            ),
            "pedalMapVCU": self.window.pedalGraph.plot(
                self.buffers["x"],
                self.buffers["pedalMapVCU"],
                pen=pg.mkPen('b', width=1.5),
                name="VCU"
            ),
        }

        # Draggable control points
        self.points = []
        for i, (x, y) in enumerate(zip(self.buffers["x"], self.buffers["pedalMap"])):
            point = DraggablePoint(
                x=x,
                y=y,
                index = i,
                callback=self.updateGraph
            )
            self.window.pedalGraph.addItem(point)
            self.points.append(point)

        # Collect spin box references in index order (pointInput1 = index 0, etc.)
        self.spinboxes = [
            getattr(self.window, f"pointInput{n}") for n in range(1, 19)
        ]

        # Configure and connect spin boxes for editable points (skip index 0 and 17)
        for i, sb in enumerate(self.spinboxes):
            sb.setRange(0.0, 1.0)
            sb.setDecimals(2)
            sb.setSingleStep(0.5)
            sb.setValue(self.buffers["pedalMap"][i])
            if i == 0 or i == 17:
                sb.setReadOnly(True)
            else:
                # Use a default-argument capture to bind the correct index
                sb.valueChanged.connect(lambda val, idx=i: self.onSpinBoxChanged(idx, val))

    def onSpinBoxChanged(self, index, value):
        # Update internal buffer and VCU state
        self.buffers["pedalMap"][index] = value
        self.vcu.state["pedalMap"] = self.buffers["pedalMap"]
        # Move the draggable point (block its position-change signal to avoid loops)
        self.points[index].sigPositionChanged.disconnect()
        self.points[index].setPos(self.buffers["x"][index], value)
        self.points[index].sigPositionChanged.connect(self.points[index].on_move)
        # Redraw curve
        self.curves["pedalMap"].setData(
            self.buffers["x"],
            self.buffers["pedalMap"] 
        )
    
    def updateGraph(self, index, value):
        if(index == 0):
            value = 0
        if(index == 17):
            value = 1
        value = max(0, min(value,1))
        # Update internal mapping
        self.buffers["pedalMap"][index] = value
        self.vcu.state["pedalMap"] = self.buffers["pedalMap"]
        # Sync the corresponding spin box without triggering valueChanged
        if index != 0 and index != 17:
            sb = self.spinboxes[index]
            sb.blockSignals(True)
            sb.setValue(value)
            sb.blockSignals(False)
        # Update curve
        self.curves["pedalMap"].setData(
            self.buffers["x"],
            self.buffers["pedalMap"]
        )
    
    @Slot()
    def updateUI(self, data, name):
        match name:
            case "DREW_CFG_APP1_THRESHOLD":
                self.window.appsLSignalCurrent.setValue(data[2])
                self.window.appsHSignalCurrent.setValue(data[3])
    
            case "DREW_CFG_APP2_THRESHOLD":
                self.window.appsHSignalCurrent_3.setValue(data[2])   # Current Low
                self.window.appsHSignalCurrent_2.setValue(data[3])   # Current High
    
            case "DREW_CFG_BSEF_THRESHOLD":
                self.window.bpsLFault.setValue(data[0])
                self.window.bpsHFault.setValue(data[1])
                # data[2] / data[3] = BSEF Signal Low/High — not used
    
            case "DREW_CFG_BSER_THRESHOLD":
                self.window.bpsLFault_2.setValue(data[0])
                self.window.bpsHFault_2.setValue(data[1])
                # data[2] / data[3] = BSER Signal Low/High — not used
    
            case "DREW_CFG_BSE_ENGAGE":
                self.window.bpsfEngaged.setValue(data[0])
                self.window.bpsrEngaged.setValue(data[1])
    
            case "DREW_CFG_MAX_TORQUE_REQUEST":
                self.window.inputmaxtorque.setValue(int(data[0]))
    
            case name if name.startswith("DREW_CFG_PEDAL_MAP_POINT_"):
                n = int(name.split("_")[-1])  # 1–16
                getattr(self.window, f"pointInput{n}").setValue(data[0])
                self.buffers["pedalMapVCU"][n] = data[0]
                self.curves["pedalMapVCU"].setData(self.buffers["x"], self.buffers["pedalMapVCU"])


    @Slot()
    def sendPedalMap(self):
        for i in range(2, 17):
            if self.buffers["pedalMap"][i] < self.buffers["pedalMap"][i-1]:
                self.logger.emit("Pedal Map not monotonically increasing! Mapping not sent.")
                return

        for i in range(1, 17):
            signal_name = f"DREW_CMD_Pedal_Map_Point_{i}"
            msg_name    = f"DREW_CMD_PEDAL_MAP_POINT_{i}"
            self.vcu.const.CONFIGURATION_SIGNALS[signal_name][1] = float(self.buffers["pedalMap"][i])
            QTimer.singleShot(100 * i, lambda msg_name=msg_name: self.vcu.set_param(msg_name))

    @Slot()  
    def show(self):
        self.window.raise_()
        self.window.show()
    
    @Slot()
    def setupApps1RangeSlider(self):
        self.apps1SignalSlider = QLabeledDoubleRangeSlider(QtCore.Qt.Vertical)
        #Configure Slider Properties, min max and starting points
        self.apps1SignalSlider.setMinimum(0)
        self.apps1SignalSlider.setMaximum(1.0)
        self.apps1SignalSlider.setValue((0.20,0.80)) #initial set
        self.apps1SignalSlider.setMinimumHeight(250)
        self.apps1SignalSlider.setMinimumWidth(60)
        self.apps1SignalSlider.setBarVisible(True)

        self.apps1SignalSlider.setProperty(
            "barColor",
            QtGui.QBrush(QtGui.QColor("#f6e16b"))
        )

        # Use QRangeSlider, not QSlider, for superqt range slider styling
        self.apps1SignalSlider.setStyleSheet("""
            QRangeSlider {
                qproperty-barColor: #f6e16b;
                background-color: transparent;
            }

            QRangeSlider::groove:vertical {
                background: #2b3048;
                width: 8px;
                border-radius: 4px;
            }

            QRangeSlider::handle:vertical {
                background: #f6e16b;
                border: 2px solid white;
                height: 18px;
                width: 18px;
                margin: 0 -6px;
                border-radius: 9px;
            }
        """)

        self.window.appsLSignal.setValue(0.20)
        self.window.appsHSignal.setValue(0.80)
        #Add slider to widget container
        layout = self.window.apps1SignalSliderContainer.layout()
        if layout is None:
            layout = QVBoxLayout(self.window.apps1SignalSliderContainer)
            layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.apps1SignalSlider, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.apps1SignalSlider)
        self.apps1SignalSlider.show()

        #when slider changes call update
        self.apps1SignalSlider.valuesChanged.connect(self.updateapps1SignalSlider)
        self.window.appsLSignal.valueChanged.connect(self.updateApps1InputBoxes)
        self.window.appsHSignal.valueChanged.connect(self.updateApps1InputBoxes)

    @Slot()
    def updateapps1SignalSlider(self, *args):
        #get values from the slider
        lowSignal, highSignal = self.apps1SignalSlider.value()

        #allow signals and then block
        self.window.appsLSignal.blockSignals(True)
        self.window.appsHSignal.blockSignals(True)

        self.window.appsLSignal.setValue(lowSignal)
        self.window.appsHSignal.setValue(highSignal)
        
        self.window.appsLSignal.blockSignals(False)
        self.window.appsHSignal.blockSignals(False)
        #update grew locally

        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP1_Signal_Low"][1]= lowSignal
        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP1_Signal_High"][1]= highSignal
    
    @Slot()
    def updateApps1InputBoxes(self):
        lowSignal = self.window.appsLSignal.value()
        highSignal = self.window.appsHSignal.value()

        if lowSignal>highSignal:
            return

        #stops triggering connected functions
        self.apps1SignalSlider.blockSignals(True)
        #sets new slider input values locally
        self.apps1SignalSlider.setValue((lowSignal,highSignal))
        #turns signals back on
        self.apps1SignalSlider.blockSignals(False)

        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP1_Signal_Low"][1]= lowSignal
        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP1_Signal_High"][1]= highSignal
    
    @Slot()
    def setupApps2RangeSlider(self):
        self.apps2SignalSlider = QLabeledDoubleRangeSlider(QtCore.Qt.Vertical)
        self.apps2SignalSlider.setMinimum(0)
        self.apps2SignalSlider.setMaximum(1.0)
        self.apps2SignalSlider.setValue((0.20, 0.80))
        self.apps2SignalSlider.setMinimumHeight(250)
        self.apps2SignalSlider.setMinimumWidth(60)
        self.apps2SignalSlider.setBarVisible(True)

        self.apps2SignalSlider.setProperty(
            "barColor",
            QtGui.QBrush(QtGui.QColor("#f6e16b"))
        )

        self.apps2SignalSlider.setStyleSheet("""
            QRangeSlider {
                qproperty-barColor: #f6e16b;
                background-color: transparent;
            }

            QRangeSlider::groove:vertical {
                background: #2b3048;
                width: 8px;
                border-radius: 4px;
            }

            QRangeSlider::handle:vertical {
                background: #f6e16b;
                border: 2px solid white;
                height: 18px;
                width: 18px;
                margin: 0 -6px;
                border-radius: 9px;
            }
        """)

        self.window.appsLSignal_2.setValue(0.20)
        self.window.appsHSignal_2.setValue(0.80)

        layout = self.window.apps2SignalSliderContainer.layout()
        if layout is None:
            layout = QVBoxLayout(self.window.apps2SignalSliderContainer)
            layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.apps2SignalSlider, alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(self.apps2SignalSlider)
        self.apps2SignalSlider.show()

        self.apps2SignalSlider.valuesChanged.connect(self.updateApps2SignalSlider)
        self.window.appsLSignal_2.valueChanged.connect(self.updateApps2InputBoxes)
        self.window.appsHSignal_2.valueChanged.connect(self.updateApps2InputBoxes)

    @Slot()
    def updateApps2SignalSlider(self, *args):
        lowSignal, highSignal = self.apps2SignalSlider.value()

        self.window.appsLSignal_2.blockSignals(True)
        self.window.appsHSignal_2.blockSignals(True)
        self.window.appsLSignal_2.setValue(lowSignal)
        self.window.appsHSignal_2.setValue(highSignal)
        self.window.appsLSignal_2.blockSignals(False)
        self.window.appsHSignal_2.blockSignals(False)

        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP2_Signal_Low"][1] = lowSignal
        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP2_Signal_High"][1] = highSignal

    @Slot()
    def updateApps2InputBoxes(self):
        lowSignal = self.window.appsLSignal_2.value()
        highSignal = self.window.appsHSignal_2.value()

        if lowSignal > highSignal:
            return

        self.apps2SignalSlider.blockSignals(True)
        self.apps2SignalSlider.setValue((lowSignal, highSignal))
        self.apps2SignalSlider.blockSignals(False)

        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP2_Signal_Low"][1] = lowSignal
        self.vcu.const.CONFIGURATION_SIGNALS["DREW_CMD_APP2_Signal_High"][1] = highSignal