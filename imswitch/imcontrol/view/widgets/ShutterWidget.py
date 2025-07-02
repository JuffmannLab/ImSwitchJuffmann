from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class ShutterWidget(Widget):

    sigShowDelay = QtCore.Signal(str)
    sigSetDelay = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = QtWidgets.QHBoxLayout()

        #Button
        self.setDelayButton = guitools.BetterPushButton("Set Delay")

        #Numerical field
        self.delayField = QtWidgets.QLineEdit("")

        #Text Field
        self.delayUnit = QtWidgets.QLabel(" ms")

        #Add widgets to the layout
        self.layout.addWidget(self.setDelayButton)
        self.layout.addWidget(self.delayField)
        self.layout.addWidget(self.delayUnit)
        self.setLayout(self.layout)

        #Connect signals to the controller
        self.setDelayButton.clicked.connect(self.sigSetDelay)
        self.delayField.textChanged.connect(self.sigShowDelay)

        



