import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore, QtGui
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class iScatFocusWidget(Widget):
    """ Enhanced widget with better calibration display and diagnostics """
    sigPIDToggled = QtCore.Signal(bool)
    sigPIDValuesChanged = QtCore.Signal(float, float, float)
    sigSetPosition = QtCore.Signal(float)
    sigAutoTune = QtCore.Signal()
    sigCalibrate = QtCore.Signal(float, float, int)

    sigSledEnable = QtCore.Signal(bool)
    sigSledAIEnable = QtCore.Signal(bool)
    sigSledControlUpdate = QtCore.Signal(float)
    sigSelectROI = QtCore.Signal(bool)  # show the full field of view to draw the ROI
    sigApplyROI = QtCore.Signal(int, int, int, int)  # (x, y, width, height) in sensor pixels
    sigSaveROI = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Main layout with more organized grid
        self.setLayout(QtWidgets.QGridLayout())
        
        # ---- PID Control Section ----
        self.pidControlGroup = QtWidgets.QGroupBox("PID Control")
        pidLayout = QtWidgets.QGridLayout()
        
        # PID Parameters
        self.kpEdit = QtWidgets.QLineEdit('0.0350')
        self.kpEdit.setValidator(QtGui.QDoubleValidator())
        self.kiEdit = QtWidgets.QLineEdit('0.0005')
        self.kiEdit.setValidator(QtGui.QDoubleValidator())
        self.kdEdit = QtWidgets.QLineEdit('0.0035')
        self.kdEdit.setValidator(QtGui.QDoubleValidator())
        
        # Control Buttons
        self.lockButton = guitools.BetterPushButton('Lock')
        self.lockButton.setCheckable(True)
        self.autoTuneButton = guitools.BetterPushButton('Auto-tune')
        
        # Add to PID layout
        pidLayout.addWidget(QtWidgets.QLabel('Proportional (V/px):'), 0, 0)
        pidLayout.addWidget(self.kpEdit, 0, 1)
        pidLayout.addWidget(QtWidgets.QLabel('Integral (V/px·s):'), 1, 0)
        pidLayout.addWidget(self.kiEdit, 1, 1)
        pidLayout.addWidget(QtWidgets.QLabel('Derivative (V/(px/s)):'), 2, 0)
        pidLayout.addWidget(self.kdEdit, 2, 1)
        pidLayout.addWidget(self.lockButton, 0, 2, 2, 1)
        pidLayout.addWidget(self.autoTuneButton, 2, 2)

        # Auto-tune result: measured noise, drift and expected stability
        self.autoTuneResultLabel = QtWidgets.QLabel('')
        self.autoTuneResultLabel.setWordWrap(True)
        pidLayout.addWidget(self.autoTuneResultLabel, 3, 0, 1, 3)
        self.pidControlGroup.setLayout(pidLayout)

        # ---- Position Control ----
        self.positionGroup = QtWidgets.QGroupBox("Position Control")
        posLayout = QtWidgets.QVBoxLayout()
        
        # Current piezo position, also when moved by the Positioner widget or the lock
        self.currentPositionLabel = QtWidgets.QLabel('Current: - V')
        self.positionEdit = QtWidgets.QLineEdit('0.0')
        self.positionEdit.setValidator(QtGui.QDoubleValidator(-10, 10, 3))
        
        self.positionSlider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.positionSlider.setRange(-1000, 1000)
        
        self.positionSetButton = guitools.BetterPushButton('Set (V)')
        
        posLayout.addWidget(self.currentPositionLabel)
        posLayout.addWidget(self.positionEdit)
        posLayout.addWidget(self.positionSlider)
        posLayout.addWidget(self.positionSetButton)
        self.positionGroup.setLayout(posLayout)

        # ---- Calibration ----
        self.calibGroup = QtWidgets.QGroupBox("Calibration")
        calibLayout = QtWidgets.QGridLayout()
        
        # Calibration inputs
        # Relative to the current piezo position, so the calibration scans around the focus
        calibLayout.addWidget(QtWidgets.QLabel("Start (V, rel. to current):"), 0, 0)
        self.calibFromEdit = QtWidgets.QLineEdit("-2")
        calibLayout.addWidget(self.calibFromEdit, 0, 1)
        
        calibLayout.addWidget(QtWidgets.QLabel("End (V, rel. to current):"), 1, 0)
        self.calibToEdit = QtWidgets.QLineEdit("2")
        calibLayout.addWidget(self.calibToEdit, 1, 1)
        
        calibLayout.addWidget(QtWidgets.QLabel("Steps:"), 2, 0)
        self.calibStepsEdit = QtWidgets.QLineEdit("50")
        calibLayout.addWidget(self.calibStepsEdit, 2, 1)
        
        self.calibButton = guitools.BetterPushButton("Run Calibration")
        calibLayout.addWidget(self.calibButton, 3, 0, 1, 2)
        
        self.calibResultLabel = QtWidgets.QLabel("Calibration: Not performed")
        self.calibResultLabel.setWordWrap(True)
        calibLayout.addWidget(self.calibResultLabel, 4, 0, 1, 2)
        
        self.calibGroup.setLayout(calibLayout)

        # ---- Plots ----
        self.focusPlotGraph = pg.GraphicsLayoutWidget()
        self.focusPlot = self.focusPlotGraph.addPlot(title="Beam Position")
        self.focusPlot.setLabels(left=('Position', 'px'), bottom=('Time', 's'))
        self.focusCurve = self.focusPlot.plot(pen='y')
        self.setpointLine = pg.InfiniteLine(angle=0, pen='r')


        # ---- SLED Control ----
        self.sledGroup = QtWidgets.QGroupBox("SLED Control")
        sledLayout = QtWidgets.QGridLayout()

        self.sledEnable = guitools.BetterPushButton('SLED Enable')
        self.sledEnable.setCheckable(True)

        self.sledEnableAI = guitools.BetterPushButton('SLED Current Enable')
        self.sledEnableAI.setCheckable(True)

        self.sledSpinBox = QtWidgets.QDoubleSpinBox()
        self.sledSpinBox.setRange(0, 2.5)
        self.sledSpinBox.setValue(0)
        self.sledSpinBox.setSingleStep(0.1)

        self.sledControlUpdate = guitools.BetterPushButton('Update Control Voltage')


        sledLayout.addWidget(self.sledEnable, 0, 0)
        sledLayout.addWidget(self.sledEnableAI, 0, 1)
        sledLayout.addWidget(self.sledSpinBox, 1, 0)
        sledLayout.addWidget(self.sledControlUpdate, 1, 1)

        self.sledGroup.setLayout(sledLayout)



        # ---- Camera View ----
        self.camView = pg.GraphicsLayoutWidget()
        self.camImg = pg.ImageItem()
        self.camViewBox = self.camView.addViewBox()
        self.camViewBox.addItem(self.camImg)
        self.camViewBox.setAspectLocked(True)

        # ---- Camera ROI ----
        # The ROI is drawn on the full field of view of the focus camera ("Select ROI")
        self.roiGroup = QtWidgets.QGroupBox("Camera ROI")
        roiLayout = QtWidgets.QGridLayout()
        self.selectROIButton = guitools.BetterPushButton('Select ROI')
        self.selectROIButton.setCheckable(True)
        self.applyROIButton = guitools.BetterPushButton('Apply ROI')
        self.applyROIButton.setEnabled(False)
        self.saveROIButton = guitools.BetterPushButton('Save ROI to setup file')
        self.roiLabel = QtWidgets.QLabel('')
        self.roiLabel.setWordWrap(True)
        roiLayout.addWidget(self.selectROIButton, 0, 0)
        roiLayout.addWidget(self.applyROIButton, 0, 1)
        roiLayout.addWidget(self.saveROIButton, 1, 0, 1, 2)
        roiLayout.addWidget(self.roiLabel, 2, 0, 1, 2)
        self.roiGroup.setLayout(roiLayout)

        self.roiItem = pg.RectROI([0, 0], [100, 100], pen=pg.mkPen('y', width=2),
                                  removable=False)
        self.roiItem.addScaleHandle([0, 0], [1, 1])
        self.roiItem.addScaleHandle([1, 0], [0, 1])
        self.roiItem.addScaleHandle([0, 1], [1, 0])
        self.roiItem.setZValue(10)
        self.roiItem.hide()
        self.camViewBox.addItem(self.roiItem)

        # ---- Layout ----
        self.layout().addWidget(self.pidControlGroup, 0, 0, 1, 2)
        self.layout().addWidget(self.positionGroup, 1, 0)
        self.layout().addWidget(self.roiGroup, 1, 1)
        self.layout().addWidget(self.focusPlotGraph, 0, 2, 2, 1)
        self.layout().addWidget(self.camView, 2, 2, 2, 1)
        self.layout().addWidget(self.calibGroup, 2, 0, 1, 2)
        self.layout().addWidget(self.sledGroup, 3, 0, 1, 2)

        # ---- Signal Connections ----
        self.lockButton.toggled.connect(self.sigPIDToggled)
        self.positionSetButton.clicked.connect(
            lambda: self.sigSetPosition.emit(float(self.positionEdit.text())))
        self.autoTuneButton.clicked.connect(self.sigAutoTune)
        self.calibButton.clicked.connect(self._emitCalibrate)
        self.selectROIButton.toggled.connect(self.sigSelectROI)
        self.applyROIButton.clicked.connect(
            lambda: self.sigApplyROI.emit(*self.getROI()))
        self.saveROIButton.clicked.connect(self.sigSaveROI)
        self.positionSlider.valueChanged.connect(self._onSliderMove)

        self.sledEnable.clicked.connect(self.sigSledEnable)
        self.sledEnableAI.clicked.connect(self.sigSledAIEnable)
        self.sledControlUpdate.clicked.connect(
            lambda: self.sigSledControlUpdate.emit(float(self.sledSpinBox.value())))
        
        for edit in (self.kpEdit, self.kiEdit, self.kdEdit):
            edit.editingFinished.connect(self.emitPIDValues)



    def _emitCalibrate(self):
        """Handle calibration signal emission with validation"""
        try:
            from_V = float(self.calibFromEdit.text())
            to_V = float(self.calibToEdit.text())
            steps = int(self.calibStepsEdit.text())
            if from_V >= to_V:
                raise ValueError("Start voltage must be less than end voltage")
            if steps < 2:
                raise ValueError("At least 2 steps required")
            self.sigCalibrate.emit(from_V, to_V, steps)
        except ValueError as e:
            self.calibResultLabel.setText(f"<font color='red'>Invalid input: {str(e)}</font>")

    def showCurrentPosition(self, voltage):
        """ Shows the current piezo position. The Set field and slider follow it while they
        aren't being edited. """
        self.currentPositionLabel.setText(f'Current: {voltage:.3f} V')
        if not self.positionEdit.hasFocus() and not self.positionSlider.isSliderDown():
            self.positionEdit.setText(f'{voltage:.3f}')
            with QtCore.QSignalBlocker(self.positionSlider):
                self.positionSlider.setValue(int(round(voltage * 100)))

    def _onSliderMove(self, value):
        """Handle slider movement and update position display"""
        voltage = value * 0.01  # Convert to volts (-10 to +10V range)
        self.positionEdit.setText(f"{voltage:.2f}")

    def updateCalibrationResult(self, slope, intercept, forward_slope=None, backward_slope=None,
                                angle_deg=None):
        """Display calibration results with optional forward/backward slopes"""
        px_per_volt = 1/slope
        
        # Base text
        text = (f"<b>Calibration Results:</b><br>"
                f"<b>Average:</b> {px_per_volt:.2f} px/V | {slope:.4f} V/px<br>"
                f"<b>Zero Offset:</b> {intercept:.1f} px")
        
        # Add forward/backward results if available
        if forward_slope is not None and backward_slope is not None:
            forward_px_per_v = 1/forward_slope
            backward_px_per_v = 1/backward_slope
            hysteresis = abs(forward_px_per_v - backward_px_per_v)
            text += (f"<br><b>Forward:</b> {forward_px_per_v:.2f} px/V<br>"
                    f"<b>Backward:</b> {backward_px_per_v:.2f} px/V<br>"
                    f"<b>Hysteresis:</b> {hysteresis:.2f} px/V")

        # Direction in which the spot moves on the camera (0 deg = along x)
        if angle_deg is not None:
            text += f"<br><b>Direction of motion:</b> {angle_deg:.1f} deg"

        # Color coding for plausibility
        if abs(px_per_volt) < 2:  # Unrealistically small
            color = "red"
            text += "<br><i>Warning: Very small sensitivity!</i>"
        elif abs(px_per_volt) > 100:  # Unrealistically large
            color = "orange"
            text += "<br><i>Warning: Very large sensitivity!</i>"
        else:
            color = "green"
        
        self.calibResultLabel.setText(text)
        self.calibResultLabel.setStyleSheet(f"color: {color};")

    def setAutoTuneResult(self, text):
        """ Shows the auto-tune result (rich text) below the PID parameters. """
        self.autoTuneResultLabel.setText(text)

    def emitPIDValues(self):
        """Emit current PID values"""
        try:
            kp = float(self.kpEdit.text())
            ki = float(self.kiEdit.text())
            kd = float(self.kdEdit.text())
            self.sigPIDValuesChanged.emit(kp, ki, kd)
        except ValueError:
            pass

    def updateFocusPlot(self, timeData, positionData, setpoint):
        """Update focus position plot"""
        self.focusCurve.setData(timeData, positionData)
        self.setpointLine.setValue(setpoint)

    def updateCameraImage(self, img):
        """Update camera display"""
        self.camImg.setImage(img)

    def showROI(self, x, y, width, height):
        """ Shows the ROI rectangle on the camera image (image coordinates = sensor pixels
        while the full field of view is shown). """
        self.roiItem.setPos([x, y], update=False)
        self.roiItem.setSize([width, height])
        self.roiItem.show()
        self.applyROIButton.setEnabled(True)

    def hideROI(self):
        self.roiItem.hide()
        self.applyROIButton.setEnabled(False)

    def getROI(self):
        """ The drawn ROI as (x, y, width, height) in pixels. """
        x, y = self.roiItem.pos()
        w, h = self.roiItem.size()
        return int(round(x)), int(round(y)), int(round(w)), int(round(h))

    def setSelectROIChecked(self, checked):
        """ Sets the Select ROI button without emitting sigSelectROI. """
        with QtCore.QSignalBlocker(self.selectROIButton):
            self.selectROIButton.setChecked(checked)

    def setROIText(self, text):
        self.roiLabel.setText(text)

    def setPIDparams(self, params):
        self.kpEdit.setText(str(params["p"]))
        self.kiEdit.setText(str(params["i"]))
        self.kdEdit.setText(str(params["d"]))