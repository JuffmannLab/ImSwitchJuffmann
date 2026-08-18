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

        # One independent ROI overlay per detector
        self.ROIs = {}

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

        self.maxMarker = self.plot.plot(
            [],
            [],
            pen=None,
            symbol="o"
        )

        self.maxText = pg.TextItem(
            "",
            anchor=(0, 1)
        )
        self.plot.addItem(self.maxText)

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

    def getROIGraphicsItem(self, detectorName):
        if detectorName not in self.ROIs:
            self.ROIs[detectorName] = naparitools.VispyROIVisual(
                rect_color="yellow",
                handle_color="orange"
            )

        return self.ROIs[detectorName]

    def showROI(self, detectorName, position, size):
        roi = self.getROIGraphicsItem(detectorName)
        roi.position = position
        roi.size = size
        roi.show()

    def hideROI(self, detectorName):
        if detectorName in self.ROIs:
            self.ROIs[detectorName].hide()

    def updateGraph(self, profile):
        profile = np.asarray(profile)

        if profile.size == 0:
            self.profileCurve.setData([], [])
            self.maxMarker.setData([], [])
            self.maxText.setText("")
            self.statsLabel.setText("Empty profile")
            return

        pixels = np.arange(profile.size)
        self.profileCurve.setData(pixels, profile)

        maxPixel = int(np.nanargmax(profile))
        maxValue = float(profile[maxPixel])

        self.maxMarker.setData([maxPixel], [maxValue])
        self.maxText.setText(
            f"max = {maxValue:.1f}\n"
            f"pixel = {maxPixel}"
        )
        self.maxText.setPos(maxPixel, maxValue)

        self.statsLabel.setText(
            f"points={profile.size}, "
            f"min={np.nanmin(profile):.1f}, "
            f"max={maxValue:.1f} at pixel {maxPixel}, "
            f"mean={np.nanmean(profile):.1f}"
        )