import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from imswitch.imcommon.view.guitools import naparitools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class LiveProfileWidget(Widget):
    """Live intensity profile widget with a selectable ROI."""

    sigShowROIToggled = QtCore.Signal(bool)
    sigAxisChanged = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("MARIA DEBUG: LiveProfileWidget was created")

        # Controls
        self.roiButton = guitools.BetterPushButton("Enable live profile")
        self.roiButton.setCheckable(True)

        self.horizontalButton = QtWidgets.QRadioButton("Horizontal profile")
        self.verticalButton = QtWidgets.QRadioButton("Vertical profile")
        self.horizontalButton.setChecked(True)

        self.statsLabel = QtWidgets.QLabel("No profile yet")

        # ROI overlay
        self.ROI = naparitools.VispyROIVisual(
            rect_color="yellow",
            handle_color="orange"
        )

        # Live plot
        self.graph = pg.GraphicsLayoutWidget()
        self.graph.setAntialiasing(True)

        self.plot = self.graph.addPlot(row=0, col=0)
        self.plot.setLabels(
            bottom=("Pixel", ""),
            left=("Gray value", "a.u.")
        )
        self.plot.showGrid(x=True, y=True)

        self.profileCurve = self.plot.plot(pen="y")

        # Layout
        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        grid.addWidget(self.graph, 0, 0, 1, 6)
        grid.addWidget(self.roiButton, 1, 0, 1, 1)
        grid.addWidget(self.horizontalButton, 1, 1, 1, 1)
        grid.addWidget(self.verticalButton, 1, 2, 1, 1)
        grid.addWidget(self.statsLabel, 2, 0, 1, 6)

        # Signals
        self.roiButton.toggled.connect(self.sigShowROIToggled)
        self.horizontalButton.clicked.connect(
            lambda: self.sigAxisChanged.emit("horizontal")
        )
        self.verticalButton.clicked.connect(
            lambda: self.sigAxisChanged.emit("vertical")
        )

    def getROIGraphicsItem(self):
        return self.ROI

    def showROI(self, position, size):
        self.ROI.position = position
        self.ROI.size = size
        self.ROI.show()

    def hideROI(self):
        self.ROI.hide()

    def updateGraph(self, profile):
        profile = np.asarray(profile)

        if profile.size == 0:
            self.profileCurve.setData([], [])
            self.statsLabel.setText("Empty profile")
            return

        pixels = np.arange(profile.size)
        self.profileCurve.setData(pixels, profile)

        self.statsLabel.setText(
            f"points={profile.size}, "
            f"min={profile.min():.1f}, "
            f"max={profile.max():.1f}, "
            f"mean={profile.mean():.1f}"
        )