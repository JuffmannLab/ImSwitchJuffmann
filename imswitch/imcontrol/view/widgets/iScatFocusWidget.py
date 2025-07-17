import numpy as np
import pyqtgraph as pg
from qtpy import QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class iScatFocusWidget(Widget):
    """ Widget containing focus lock interface. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Focus lock
        self.kpEdit = QtWidgets.QLineEdit('5')
        self.kpLabel = QtWidgets.QLabel('kp')
        self.kiEdit = QtWidgets.QLineEdit('0.1')
        self.kiLabel = QtWidgets.QLabel('ki')
        self.kdEdit = QtWidgets.QLineEdit('0.01')
        self.kdLabel = QtWidgets.QLabel('kd')

        self.lockButton = guitools.BetterPushButton('Lock')
        self.lockButton.setCheckable(True)
        self.lockButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Expanding)

        self.zStackBox = QtWidgets.QCheckBox('Z-stack')

        self.zStepFromEdit = QtWidgets.QLineEdit('0.001')
        self.zStepFromLabel = QtWidgets.QLabel('Min step (V)')
        self.zStepToEdit = QtWidgets.QLineEdit('1')
        self.zStepToLabel = QtWidgets.QLabel('Max step (V)')

        self.camDialogButton = guitools.BetterPushButton('Camera Dialog')
        
        self.autoTuneBotton = guitools.BetterPushButton('Auto-tune')

        # Piezo absolute positioning
        self.positionLabel = QtWidgets.QLabel(
            'Position (V)')  # Potentially disregard this and only use in the positioning widget?
        self.positionEdit = QtWidgets.QLineEdit('0')
        self.positionSetButton = guitools.BetterPushButton('Set')

        # Focus lock calibration
        self.calibFromLabel = QtWidgets.QLabel('From (V)')
        self.calibFromEdit = QtWidgets.QLineEdit('-2')
        self.calibToLabel = QtWidgets.QLabel('To (V)')
        self.calibToEdit = QtWidgets.QLineEdit('+2')
        self.focusCalibButton = guitools.BetterPushButton('Calib')
        self.focusCalibButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                            QtWidgets.QSizePolicy.Expanding)
        self.calibCurveButton = guitools.BetterPushButton('See calib')
        self.calibrationDisplay = QtWidgets.QLineEdit(
            'Previous calib: none')  # Edit this from the controller with calibration values
        self.calibrationDisplay.setReadOnly(True)
        # CREATE CALIBRATION CURVE WINDOW AND FOCUS CALIBRATION GRAPH SOMEHOW

        # Focus lock graph
        self.focusLockGraph = pg.GraphicsLayoutWidget()
        self.focusLockGraph.setAntialiasing(True)
        self.focusPlot = self.focusLockGraph.addPlot(row=1, col=0)
        self.focusPlot.setLabels(bottom=('Time', 's'), left=('Laser position', 'px'))
        self.focusPlot.showGrid(x=True, y=True)
        # update this (self.focusPlotCurve.setData(X,Y)) with update(focusSignal) function
        self.focusPlotCurve = self.focusPlot.plot(pen='y')

        # Webcam graph
        self.webcamGraph = pg.GraphicsLayoutWidget()
        self.camImg = pg.ImageItem(border='w')
        self.camImg.setImage(np.zeros((100, 100)))
        self.vb = self.webcamGraph.addViewBox(invertY=True, invertX=False)
        self.vb.setAspectLocked(True)
        self.vb.addItem(self.camImg)

        # PROCESS DATA THREAD - ADD SOMEWHERE ELSE, NOT HERE, AS IT HAS NO GRAPHICAL ELEMENTS!

        # GUI layout below
        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.focusLockGraph, 0, 0, 1, 9)
        grid.addWidget(self.webcamGraph, 0, 9, 4, 1)
        grid.addWidget(self.focusCalibButton, 1, 2, 2, 1)
        grid.addWidget(self.calibrationDisplay, 3, 0, 1, 2)
        grid.addWidget(self.kpLabel, 1, 3)
        grid.addWidget(self.kpEdit, 1, 4)
        grid.addWidget(self.kiLabel, 2, 3)
        grid.addWidget(self.kiEdit, 2, 4)
        grid.addWidget(self.kdLabel, 3, 3)
        grid.addWidget(self.kdEdit, 3, 4)
        grid.addWidget(self.lockButton, 1, 5, 2, 1)
        grid.addWidget(self.zStackBox, 4, 2)
        grid.addWidget(self.zStepFromLabel, 3, 4)
        grid.addWidget(self.zStepFromEdit, 4, 4)
        grid.addWidget(self.zStepToLabel, 3, 5)
        grid.addWidget(self.zStepToEdit, 4, 5)
        # grid.addWidget(self.focusDataBox, 4, 0, 1, 2)
        grid.addWidget(self.calibFromLabel, 1, 0)
        grid.addWidget(self.calibFromEdit, 1, 1)
        grid.addWidget(self.calibToLabel, 2, 0)
        grid.addWidget(self.calibToEdit, 2, 1)
        grid.addWidget(self.autoTuneBotton, 3, 2)
        grid.addWidget(self.positionLabel, 1, 6)
        grid.addWidget(self.positionEdit, 1, 7)
        grid.addWidget(self.positionSetButton, 2, 6, 1, 2)
        grid.addWidget(self.camDialogButton, 3, 6, 1, 2)