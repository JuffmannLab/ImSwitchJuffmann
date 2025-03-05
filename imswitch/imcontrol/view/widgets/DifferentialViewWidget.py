import pyqtgraph as pg
import numpy as np
from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcommon.view.guitools import pyqtgraphtools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget, NapariHybridWidget

"""
Widget for showing differential imaging. 
Right now, the Widget is in hybrid mode with the napari viewer, showing the diff img in the viewer.
For more controllability I think it would be benefitial to show it in the widget itself. 
Also enables us to add colorbars etc.

Missing:
-Input for Batch Size
-Colorbar
-pyqtgraph implementation

-maybe showing the noise floor?
"""


class DifferentialViewWidget(Widget):
    """Displays the differential image for iScat measurements."""

    sigshowpushed = QtCore.Signal(bool)
    sigbatchsize = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Button to activate differential view
        self.showdiffpush = guitools.BetterPushButton("Differential View")
        self.showdiffpush.setCheckable(True)
        self.showdiffpush.toggled.connect(self.sigshowpushed.emit)

        # Input for batch size
        self.linebatchsize = QtWidgets.QLineEdit("1")
        self.linebatchsize.setValidator(QtGui.QIntValidator(1, 1000))  # Ensures positive integer input
        self.linebatchsize.textChanged.connect(self.update_batch_size)

        # pyqtgraph Viewbox
        self.diffimagegraph = pg.GraphicsLayoutWidget()
        self.diffimg = pg.ImageItem(border="w")
        self.viewbox = self.diffimagegraph.addViewBox(invertY=False, invertX=False)
        self.viewbox.setMouseMode(pg.ViewBox.RectMode)
        self.viewbox.setAspectLocked(True)
        self.viewbox.addItem(self.diffimg)

        # Colorbar
        #self.colorbar = pg.ColorBarItem(interactive=True)
        #self.colorbar.setImageItem(self.diffimg)
        #self.diffimagegraph.addItem(self.colorbar)

        # Layout
        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.showdiffpush, 0, 0, 1, 1)
        grid.addWidget(QtWidgets.QLabel("Batch Size:"), 0, 1, 1, 1)
        grid.addWidget(self.linebatchsize, 0, 2, 1, 1)
        grid.addWidget(self.diffimagegraph, 1, 0, 1, 3)

        self.layer = None

    def update_batch_size(self):
        """Emit the batch size when the input changes."""
        text = self.linebatchsize.text()
        if text:
            self.sigbatchsize.emit(int(text))

    def getDifferentialViewChecked(self):
        return self.showdiffpush.isChecked()
    
    def getBatchSize(self):
        return int(self.linebatchsize.text())
    
    def getImage(self):
        return self.diffimg.image
        
    def setImage(self, im):
        self.diffimg.setImage(im, autoLevels=False)

    def updateImageLimits(self, imgWidth, imgHeight):
        pyqtgraphtools.setPGBestImageLimits(self.viewbox, imgWidth, imgHeight)

