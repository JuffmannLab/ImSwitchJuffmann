from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class SynthControlWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setLayout(QtWidgets.QGridLayout())

        #components

        self.channel1button = guitools.BetterPushButton('Channel 1')
        self.channel1AmpSlider = guitools.BetterSlider(QtCore.Qt.Vertical, self, allowScrollChanges=False)

        self.channel2button = guitools.BetterPushButton('Channel 2')
        self.channel2AmpSlider = guitools.BetterSlider(QtCore.Qt.Vertical, self, allowScrollChanges=False)

        self.layout().addWidget(self.channel1AmpSlider, 0, 0, 2, 1)
        self.layout().addWidget(self.channel1button, 2, 0, 1, 1)

        self.layout().addWidget(self.channel2AmpSlider, 0, 1, 2, 1)
        self.layout().addWidget(self.channel2button, 2, 1, 1, 1)




