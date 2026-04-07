from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class ShuttersWidget(Widget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setLayout(QtWidgets.QGridLayout())
        self.button = guitools.BetterPushButton('Channel 1')
        self.layout().addWidget(self.button, 0, 0, 1, 1)
