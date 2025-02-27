import pyqtgraph as pg
from qtpy import QtCore, QtWidgets

from imswitch.imcommon.view.guitools import pyqtgraphtools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget, NapariHybridWidget

class DifferentialViewWidget(NapariHybridWidget):
    """ Displays the differential image for iScat measurements. """

    def __post__init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Graphical elements
        self.showCheck = QtWidgets.QCheckBox('Show Differential View')
        self.showCheck.setCheckable(True)
        self.posCheck = guitools.BetterPushButton('Batch Size')
        self.posCheck.setCheckable(True)
        self.linePos = QtWidgets.QLineEdit('1')

        # Viewbox
        self.cwidget = pg.GraphicsLayoutWidget()
        self.vb = self.cwidget.addViewBox(row=1, col=1)
        self.vb.setMouseMode(pg.ViewBox.RectMode)
        self.img = pg.ImageItem(axisOrder='row-major')
        self.img.setTransform(self.img.transform().translate(-0.5, -0.5))
        self.vb.addItem(self.img)
        self.vb.setAspectLocked(True)

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.cwidget, 0, 0, 1, 6)
        grid.addWidget(self.showCheck, 1, 0, 1, 1)
        grid.addWidget(self.posCheck, 2, 0, 1, 1)
        grid.addWidget(self.linePos, 2, 1, 1, 1)

    def getShowFFTChecked(self):
        return self.showCheck.isChecked()

    def getShowPosChecked(self):
        return self.posCheck.isChecked()

    def getPos(self):
        return float(self.linePos.text())

    def getImage(self):
        return self.img.image

    def setImage(self, im):
        self.img.setImage(im, autoLevels=False)

    def updateImageLimits(self, imgWidth, imgHeight):
        pyqtgraphtools.setPGBestImageLimits(self.vb, imgWidth, imgHeight)