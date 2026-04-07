from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class HWPWidget(Widget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setLayout(QtWidgets.QGridLayout())
        self.slider1 = guitools.BetterPushButton('HPW 1')
        self.slider2 = guitools.BetterPushButton('HPW 2')

        self.layout().addWidget(self.slider1, 0, 0, 1, 1)
        self.layout().addWidget(self.slider2, 1, 0, 1, 1)
