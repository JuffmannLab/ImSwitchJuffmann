import pyqtgraph as pg
import numpy as np
from qtpy import QtCore, QtWidgets

from imswitch.imcommon.view.guitools import pyqtgraphtools
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget, NapariHybridWidget

class DifferentialViewWidget(NapariHybridWidget):
    """ Displays the differential image for iScat measurements. """

    sigShowToggled = QtCore.Signal(bool)
    def __post_init__(self, *args, **kwargs):

        self.showCheck = QtWidgets.QCheckBox('Differential View')
        self.showCheck.setCheckable(True)


        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)
        grid.addWidget(self.showCheck, 1, 0, 1, 1)

        self.showCheck.toggled.connect(self.sigShowToggled)

        self.layer = None

    def getDifferentialViewChecked(self):
        return self.showCheck.isChecked()
    
    def getImage(self):
        if self.layer is not None:
            return self.layer.data
        
    def setImage(self, im):
        if self.layer is None or self.layer.name not in self.viewer.layers:
            self.layer = self.viewer.add_image(im, rgb = False, name = "Holo", blending="additive")
        self.layer.data = im

