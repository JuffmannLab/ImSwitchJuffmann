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

        # One live curve and one statistics line per detector
        self.profileCurves = {}
        self.profileStats = {}
        self.detectorColors = {}

        # Live plot
        self.graph = pg.GraphicsLayoutWidget()
        self.graph.setAntialiasing(True)

        self.plot = self.graph.addPlot(row=0, col=0)
        self.plot.setLabels(
            bottom=("Pixel", ""),
            left=("Gray value", "a.u.")
        )
        self.plot.showGrid(x=True, y=True)

        self.plot.addLegend()

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

    def _getDetectorColor(self, detectorName):
        """Return a stable display color for each detector."""
        if detectorName not in self.detectorColors:
            colors = ["yellow", "cyan", "magenta", "green"]
            colorIndex = len(self.detectorColors) % len(colors)
            self.detectorColors[detectorName] = colors[colorIndex]

        return self.detectorColors[detectorName]

    def getROIGraphicsItem(self, detectorName):
        if detectorName not in self.ROIs:
            color = self._getDetectorColor(detectorName)

            self.ROIs[detectorName] = naparitools.VispyROIVisual(
                rect_color=color,
                handle_color=color
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

    def updateGraph(self, detectorName, profile):
        """Update the curve and statistics belonging to one detector."""
        profile = np.asarray(profile)

        if detectorName not in self.profileCurves:
            color = self._getDetectorColor(detectorName)

            self.profileCurves[detectorName] = self.plot.plot(
                pen=pg.mkPen(color, width=2),
                name=detectorName
            )

        curve = self.profileCurves[detectorName]

        if profile.size == 0:
            curve.setData([], [])
            self.profileStats[detectorName] = "empty profile"
        else:
            pixels = np.arange(profile.size)
            curve.setData(pixels, profile)

            maxPixel = int(np.nanargmax(profile))
            maxValue = float(profile[maxPixel])

            self.profileStats[detectorName] = (
                f"points={profile.size}, "
                f"min={np.nanmin(profile):.1f}, "
                f"max={maxValue:.1f} at pixel {maxPixel}, "
                f"mean={np.nanmean(profile):.1f}"
            )

        self.statsLabel.setText(
            "\n".join(
                f"{name}: {stats}"
                for name, stats in self.profileStats.items()
            )
        )
