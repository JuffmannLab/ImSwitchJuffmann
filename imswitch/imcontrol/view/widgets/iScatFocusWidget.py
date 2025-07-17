import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore, QtGui
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class iScatFocusWidget(Widget):
    """ Widget containing focus lock interface with PID controls. """
    sigPIDToggled = QtCore.Signal(bool)  # Lock/unlock
    sigPIDValuesChanged = QtCore.Signal(float, float, float)  # kp, ki, kd
    sigSetPosition = QtCore.Signal(float)  # Target position (V)
    sigAutoTune = QtCore.Signal()
    sigCalibrate = QtCore.Signal(float, float, int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # PID Control Section
        self.pidControlGroup = QtWidgets.QGroupBox("PID Control")
        
        # PID Parameters
        self.kpEdit = QtWidgets.QLineEdit('0.02')
        self.kpEdit.setValidator(QtGui.QDoubleValidator())
        self.kpLabel = QtWidgets.QLabel('Proportional (V/px):')
        
        self.kiEdit = QtWidgets.QLineEdit('0.002')
        self.kiEdit.setValidator(QtGui.QDoubleValidator())
        self.kiLabel = QtWidgets.QLabel('Integral (V/px·s):')
        
        self.kdEdit = QtWidgets.QLineEdit('0.0005')
        self.kdEdit.setValidator(QtGui.QDoubleValidator())
        self.kdLabel = QtWidgets.QLabel('Derivative (V/(px/s)):')

        # Control Buttons
        self.lockButton = guitools.BetterPushButton('Lock')
        self.lockButton.setCheckable(True)
        self.autoTuneButton = guitools.BetterPushButton('Auto-tune')

        # Position Control
        self.positionGroup = QtWidgets.QGroupBox("Position Control")
        self.positionEdit = QtWidgets.QLineEdit('0.0')
        self.positionEdit.setValidator(QtGui.QDoubleValidator(-10, 10, 3))
        self.positionSetButton = guitools.BetterPushButton('Set (V)')

        # Calibration UI Elements
        self.calibGroup = QtWidgets.QGroupBox("Calibration")
        self.calibFromLabel = QtWidgets.QLabel("Start (V):")
        self.calibFromEdit = QtWidgets.QLineEdit("-2")
        self.calibFromEdit.setValidator(QtGui.QDoubleValidator(-10, 10, 3))
        
        self.calibToLabel = QtWidgets.QLabel("End (V):")
        self.calibToEdit = QtWidgets.QLineEdit("2")
        self.calibToEdit.setValidator(QtGui.QDoubleValidator(-10, 10, 3))
        
        self.calibStepsLabel = QtWidgets.QLabel("Steps:")
        self.calibStepsEdit = QtWidgets.QLineEdit("50")
        self.calibStepsEdit.setValidator(QtGui.QIntValidator(2, 50))
        
        self.calibButton = guitools.BetterPushButton("Run Calibration")
        self.calibResultLabel = QtWidgets.QLabel("Calibration: Not performed")
        
        # Calibration Layout
        calibLayout = QtWidgets.QGridLayout()
        calibLayout.addWidget(self.calibFromLabel, 0, 0)
        calibLayout.addWidget(self.calibFromEdit, 0, 1)
        calibLayout.addWidget(self.calibToLabel, 1, 0)
        calibLayout.addWidget(self.calibToEdit, 1, 1)
        calibLayout.addWidget(self.calibStepsLabel, 2, 0)
        calibLayout.addWidget(self.calibStepsEdit, 2, 1)
        calibLayout.addWidget(self.calibButton, 3, 0, 1, 2)
        calibLayout.addWidget(self.calibResultLabel, 4, 0, 1, 2)
        self.calibGroup.setLayout(calibLayout)

        # Diagnostics Display
        self.diagGroup = QtWidgets.QGroupBox("Diagnostics")
        self.pidTermsGraph = pg.GraphicsLayoutWidget()
        self.pidPlot = self.pidTermsGraph.addPlot(title="PID Terms")
        self.pTermCurve = self.pidPlot.plot(pen='r', name='P')
        self.iTermCurve = self.pidPlot.plot(pen='g', name='I')
        self.dTermCurve = self.pidPlot.plot(pen='b', name='D')
        self.pidPlot.addLegend()

        # Focus Position Plot
        self.focusPlotGraph = pg.GraphicsLayoutWidget()
        self.focusPlot = self.focusPlotGraph.addPlot(title="Beam Position")
        self.focusPlot.setLabels(left=('Position', 'px'), bottom=('Time', 's'))
        self.focusCurve = self.focusPlot.plot(pen='y')
        self.setpointLine = pg.InfiniteLine(angle=0, pen='r')

        # Camera View
        self.camView = pg.GraphicsLayoutWidget()
        self.camImg = pg.ImageItem()
        self.camViewBox = self.camView.addViewBox()
        self.camViewBox.addItem(self.camImg)
        self.camViewBox.setAspectLocked(True)

        # Layout
        self.setLayout(QtWidgets.QGridLayout())
        
        # PID Control Layout
        pidLayout = QtWidgets.QGridLayout()
        pidLayout.addWidget(self.kpLabel, 0, 0)
        pidLayout.addWidget(self.kpEdit, 0, 1)
        pidLayout.addWidget(self.kiLabel, 1, 0)
        pidLayout.addWidget(self.kiEdit, 1, 1)
        pidLayout.addWidget(self.kdLabel, 2, 0)
        pidLayout.addWidget(self.kdEdit, 2, 1)
        pidLayout.addWidget(self.lockButton, 0, 2, 2, 1)
        pidLayout.addWidget(self.autoTuneButton, 2, 2)
        self.pidControlGroup.setLayout(pidLayout)

        # Position Control Layout
        posLayout = QtWidgets.QHBoxLayout()
        posLayout.addWidget(self.positionEdit)
        posLayout.addWidget(self.positionSetButton)
        self.positionGroup.setLayout(posLayout)

        # Diagnostics Layout
        diagLayout = QtWidgets.QVBoxLayout()
        diagLayout.addWidget(self.pidTermsGraph)
        self.diagGroup.setLayout(diagLayout)

        # Main Layout
        self.layout().addWidget(self.pidControlGroup, 0, 0, 1, 2)
        self.layout().addWidget(self.positionGroup, 1, 0)
        self.layout().addWidget(self.diagGroup, 2, 0)
        self.layout().addWidget(self.focusPlotGraph, 0, 2, 2, 1)
        self.layout().addWidget(self.camView, 2, 2)
        self.layout().addWidget(self.calibGroup, 3, 0, 1, 2)

        # Connect signals
        self.lockButton.toggled.connect(self.sigPIDToggled)
        self.positionSetButton.clicked.connect(
            lambda: self.sigSetPosition.emit(float(self.positionEdit.text())))
        self.autoTuneButton.clicked.connect(self.sigAutoTune)
        self.calibButton.clicked.connect(
            lambda: self.sigCalibrate.emit(
                float(self.calibFromEdit.text()),
                float(self.calibToEdit.text()),
                int(self.calibStepsEdit.text())
            )
        )
        
        # Update PID values when edited
        for edit in (self.kpEdit, self.kiEdit, self.kdEdit):
            edit.editingFinished.connect(self.emitPIDValues)

    def updateCalibrationResult(self, slope, intercept):
        """Update calibration display"""
        text = (f"Calibration: {slope:.3f} V/px | {1/slope:.3f} px/V | "
                f"Zero at {intercept:.2f} px")
        self.calibResultLabel.setText(text)

    def emitPIDValues(self):
        """Emit current PID values"""
        try:
            kp = float(self.kpEdit.text())
            ki = float(self.kiEdit.text())
            kd = float(self.kdEdit.text())
            self.sigPIDValuesChanged.emit(kp, ki, kd)
        except ValueError:
            pass

    def updatePIDDisplay(self, timeData, pData, iData, dData):
        """Update PID terms plot"""
        self.pTermCurve.setData(timeData, pData)
        self.iTermCurve.setData(timeData, iData)
        self.dTermCurve.setData(timeData, dData)

    def updateFocusPlot(self, timeData, positionData, setpoint):
        """Update focus position plot"""
        self.focusCurve.setData(timeData, positionData)
        self.setpointLine.setValue(setpoint)

    def updateCameraImage(self, img):
        """Update camera display"""
        self.camImg.setImage(img)