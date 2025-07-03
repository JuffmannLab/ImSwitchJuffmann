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
        self.delayField.setPlaceholderText("Enter a numerical delay value here")
        self.delayDisplay = QtWidgets.QLabel(" ")
        #Text Field
        self.delayUnit = QtWidgets.QLabel("ms")

        #Add widgets to the layout
        self.layout.addWidget(self.setDelayButton)
        self.layout.addWidget(self.delayField)
        self.layout.addWidget(self.delayDisplay)
        self.layout.addWidget(self.delayUnit)
        self.setLayout(self.layout)

        #Connect signals to the controller
        self.setDelayButton.clicked.connect(self.sigSetDelay)

    def addDefault(self, delay):
        self.delayDisplay.setText(str(delay))




