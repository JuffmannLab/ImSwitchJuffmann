import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets, QtCore, QtGui
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class _GridLayoutWithoutHeightForWidth(QtWidgets.QGridLayout):
    def hasHeightForWidth(self):
        return False


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
    sigAutofocus = QtCore.Signal(float, int, int)  # (range +- V, steps, frames per step)
    sigStoreFocus = QtCore.Signal()
    sigGoToFocus = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Main layout with more organized grid. Without height-for-width: the word-wrapped
        # labels (also on the hidden tab) would make the scroll area of the dock size the widget
        # much higher than needed
        self.setLayout(_GridLayoutWithoutHeightForWidth())
        
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
        pidLayout.addWidget(self._label('P (V/px):', 'Proportional gain'), 0, 0)
        pidLayout.addWidget(self.kpEdit, 0, 1)
        pidLayout.addWidget(self._label('I (V/px·s):', 'Integral gain'), 1, 0)
        pidLayout.addWidget(self.kiEdit, 1, 1)
        pidLayout.addWidget(self._label('D (V·s/px):', 'Derivative gain'), 2, 0)
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
        calibLayout.addWidget(self._label("Start (V, rel.):", "Relative to the current piezo position"), 0, 0)
        self.calibFromEdit = QtWidgets.QLineEdit("-2")
        calibLayout.addWidget(self.calibFromEdit, 0, 1)
        
        calibLayout.addWidget(self._label("End (V, rel.):", "Relative to the current piezo position"), 1, 0)
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

        self.sledEnable = guitools.BetterPushButton('Enable')
        self.sledEnable.setToolTip('SLED enable')
        self.sledEnable.setCheckable(True)

        self.sledEnableAI = guitools.BetterPushButton('Current')
        self.sledEnableAI.setToolTip('SLED current control enable')
        self.sledEnableAI.setCheckable(True)

        self.sledSpinBox = QtWidgets.QDoubleSpinBox()
        self.sledSpinBox.setRange(0, 2.5)
        self.sledSpinBox.setValue(0)
        self.sledSpinBox.setSingleStep(0.1)

        self.sledControlUpdate = guitools.BetterPushButton('Set (V)')
        self.sledControlUpdate.setToolTip('Update the SLED control voltage')


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
        self.saveROIButton = guitools.BetterPushButton('Save ROI')
        self.saveROIButton.setToolTip('Save the ROI to the setup file (applied on startup)')
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

        # ---- Autofocus and focus memory ----
        self.afGroup = QtWidgets.QGroupBox("Autofocus")
        afLayout = QtWidgets.QGridLayout()
        self.afRangeEdit = QtWidgets.QLineEdit('2.0')
        self.afRangeEdit.setValidator(QtGui.QDoubleValidator(0.01, 10, 3))
        self.afStepsEdit = QtWidgets.QSpinBox()
        self.afStepsEdit.setRange(5, 201)
        self.afStepsEdit.setValue(21)
        self.afFramesEdit = QtWidgets.QSpinBox()
        self.afFramesEdit.setRange(1, 100)
        self.afFramesEdit.setValue(5)
        self.autofocusButton = guitools.BetterPushButton('Autofocus')
        self.storeFocusButton = guitools.BetterPushButton('Store focus')
        self.goToFocusButton = guitools.BetterPushButton('Go to focus')
        self.goToFocusButton.setToolTip('Move the piezo until the focus lock spot is at the stored position')
        self.goToFocusButton.setEnabled(False)
        self.afResultLabel = QtWidgets.QLabel('')
        self.afResultLabel.setWordWrap(True)
        self.focusMemoryLabel = QtWidgets.QLabel('Stored focus: none')
        self.focusMemoryLabel.setWordWrap(True)
        self.afPlot = pg.PlotWidget()
        self.afPlot.setLabels(left='Sharpness', bottom=('Piezo', 'V'))
        self.afPlot.setMinimumHeight(120)
        self.afCoarseCurve = self.afPlot.plot(pen=None, symbol='o', symbolSize=5,
                                              symbolBrush='c')
        self.afFineCurve = self.afPlot.plot(pen='y', symbol='o', symbolSize=5, symbolBrush='y')
        self.afBestLine = pg.InfiniteLine(angle=90, pen='r')
        self.afBestLine.hide()
        self.afPlot.addItem(self.afBestLine)

        afLayout.addWidget(self._label('Range (± V):', 'Scan range around the current piezo position'), 0, 0)
        afLayout.addWidget(self.afRangeEdit, 0, 1)
        afLayout.addWidget(QtWidgets.QLabel('Steps:'), 1, 0)
        afLayout.addWidget(self.afStepsEdit, 1, 1)
        afLayout.addWidget(self._label('Frames/step:', 'Frames averaged per scan step'), 2, 0)
        afLayout.addWidget(self.afFramesEdit, 2, 1)
        afLayout.addWidget(self.autofocusButton, 3, 0, 1, 2)
        afLayout.addWidget(self.afResultLabel, 4, 0, 1, 2)
        afLayout.addWidget(self.afPlot, 5, 0, 1, 2)
        afLayout.addWidget(self.storeFocusButton, 6, 0)
        afLayout.addWidget(self.goToFocusButton, 6, 1)
        afLayout.addWidget(self.focusMemoryLabel, 7, 0, 1, 2)
        self.afGroup.setLayout(afLayout)

        # ---- Layout ----
        # Normal view: controls on the left (at their natural width), graphics on the right
        # (all the remaining width). Calibration and autofocus share one place as tabs; the
        # Autofocus tab switches the whole widget to the autofocus view.
        calibPage = QtWidgets.QWidget()
        calibPageLayout = QtWidgets.QVBoxLayout(calibPage)
        calibPageLayout.setContentsMargins(0, 0, 0, 0)
        calibPageLayout.addWidget(self.calibGroup)
        calibPageLayout.addStretch(1)
        afPlaceholder = QtWidgets.QWidget()  # the autofocus is shown in its own view
        afPlaceholder.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(calibPage, 'Calibration')
        self.tabs.addTab(afPlaceholder, 'Autofocus')

        controls = QtWidgets.QWidget()
        controlsLayout = QtWidgets.QGridLayout(controls)
        controlsLayout.setContentsMargins(0, 0, 0, 0)
        controlsLayout.addWidget(self.pidControlGroup, 0, 0, 1, 2)
        controlsLayout.addWidget(self.positionGroup, 1, 0)
        controlsLayout.addWidget(self.roiGroup, 1, 1)
        controlsLayout.addWidget(self.tabs, 2, 0, 1, 2)
        controlsLayout.addWidget(self.sledGroup, 3, 0, 1, 2)
        controlsLayout.setRowStretch(4, 1)
        # Only a bit wider than needed (the input fields would otherwise take all the width)
        controls.setMaximumWidth(controls.minimumSizeHint().width() + 20)

        graphics = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        graphics.addWidget(self.focusPlotGraph)
        graphics.addWidget(self.camView)
        self.focusPlotGraph.setMinimumSize(120, 120)
        self.camView.setMinimumSize(120, 120)
        # Share the available height instead of asking for their (large) preferred height
        graphics.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Ignored)

        normalView = QtWidgets.QWidget()
        normalLayout = QtWidgets.QHBoxLayout(normalView)
        normalLayout.setContentsMargins(0, 0, 0, 0)
        normalLayout.addWidget(controls)
        normalLayout.addWidget(graphics, 1)

        # Autofocus view: the autofocus group with the whole area of the widget
        autofocusView = QtWidgets.QWidget()
        afViewLayout = QtWidgets.QVBoxLayout(autofocusView)
        afViewLayout.setContentsMargins(0, 0, 0, 0)
        self.afTabBar = QtWidgets.QTabBar()
        self.afTabBar.addTab('Calibration')
        self.afTabBar.addTab('Autofocus')
        self.afTabBar.setCurrentIndex(1)
        afViewLayout.addWidget(self.afTabBar)
        afViewLayout.addWidget(self.afGroup, 1)
        self.afGroup.layout().setRowStretch(5, 1)  # the sharpness plot gets the extra height

        self.views = QtWidgets.QStackedWidget()
        self.views.addWidget(normalView)
        self.views.addWidget(autofocusView)
        self.tabs.currentChanged.connect(self._onTabChanged)
        self.afTabBar.currentChanged.connect(self._onAfTabChanged)

        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().addWidget(self.views, 0, 0)

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
        self.autofocusButton.clicked.connect(self._emitAutofocus)
        self.storeFocusButton.clicked.connect(self.sigStoreFocus)
        self.goToFocusButton.clicked.connect(self.sigGoToFocus)
        self.positionSlider.valueChanged.connect(self._onSliderMove)

        self.sledEnable.clicked.connect(self.sigSledEnable)
        self.sledEnableAI.clicked.connect(self.sigSledAIEnable)
        self.sledControlUpdate.clicked.connect(
            lambda: self.sigSledControlUpdate.emit(float(self.sledSpinBox.value())))
        
        for edit in (self.kpEdit, self.kiEdit, self.kdEdit):
            edit.editingFinished.connect(self.emitPIDValues)



    def _onTabChanged(self, index):
        """ The Autofocus tab of the normal view switches to the autofocus view. """
        if index == 1:
            with QtCore.QSignalBlocker(self.tabs):
                self.tabs.setCurrentIndex(0)
            with QtCore.QSignalBlocker(self.afTabBar):
                self.afTabBar.setCurrentIndex(1)
            self.views.setCurrentIndex(1)

    def _onAfTabChanged(self, index):
        """ The Calibration tab of the autofocus view switches back to the normal view. """
        if index == 0:
            with QtCore.QSignalBlocker(self.afTabBar):
                self.afTabBar.setCurrentIndex(1)
            self.views.setCurrentIndex(0)

    @staticmethod
    def _label(text, tooltip):
        """ Short label with the longer explanation as tooltip. """
        label = QtWidgets.QLabel(text)
        label.setToolTip(tooltip)
        return label

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

    def _emitAutofocus(self):
        try:
            rangeV = float(self.afRangeEdit.text())
        except ValueError:
            self.afResultLabel.setText("<font color='red'>Invalid range</font>")
            return
        self.sigAutofocus.emit(rangeV, self.afStepsEdit.value(), self.afFramesEdit.value())

    def showAutofocusCurves(self, coarse, fine, best):
        """ Shows the sharpness curves of the coarse and fine scan, (voltages, values) each,
        and the chosen focus (None: not found). """
        self.afCoarseCurve.setData(*coarse) if coarse else self.afCoarseCurve.clear()
        self.afFineCurve.setData(*fine) if fine else self.afFineCurve.clear()
        if best is None:
            self.afBestLine.hide()
        else:
            self.afBestLine.setValue(best)
            self.afBestLine.show()

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