from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class PockelCellWidget(Widget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QtWidgets.QGridLayout()

        #flags
        self.flagLabel = QtWidgets.QLabel("Control flags")
        self.flagHV = QtWidgets.QCheckBox("High Voltage On")
        self.flagRemote = QtWidgets.QCheckBox("Remote enable")
        self.flagCheckRation = QtWidgets.QCheckBox("Check Ratio")
        self.flagCalibrate = QtWidgets.QCheckBox("Calibrate")
        self.flagReset = QtWidgets.QCheckBox("Reset")
        self.flagSendButton = guitools.BetterPushButton("Send flag bits")

        #Voltage
        self.voltTargetLabel = QtWidgets.QLabel("Target Voltage [V]:")
        self.voltTargetSpin = QtWidgets.QSpinBox()
        self.voltTargetSpin.setMinimum(0)
        self.voltTargetSpin.setMaximum(3000)
        self.voltTargetSpin.setSingleStep(1)
        self.voltTargetSpin.setValue(0)
        self.voltSlider = guitools.BetterSlider(QtCore.Qt.Horizontal)
        self.voltSlider.setRange(0, 3000)
        self.voltSlider.setValue(0)
        self.voltSliderMinLabel = QtWidgets.QLabel("0V")
        self.voltSliderMaxLabel = QtWidgets.QLabel("3000V")
        self.voltActualLabel = QtWidgets.QLabel("Actual Voltage [V]: ")
        self.voltActualValue = QtWidgets.QLabel("")


        #Status
        self.statusLabel = QtWidgets.QLabel("Status flags")
        self.statusTextBox = QtWidgets.QTextEdit()
        self.statusTextBox.setReadOnly(True)
        self.statusTextBox.setPlaceholderText("Status flags will appear here")

        self.layout.addWidget(self.flagLabel, 0, 0)
        self.layout.addWidget(self.flagHV, 1, 0)
        self.layout.addWidget(self.flagRemote, 2, 0)
        self.layout.addWidget(self.flagCalibrate, 3, 0)
        self.layout.addWidget(self.flagReset, 4, 0)
        self.layout.addWidget(self.flagSendButton, 5, 0)

        self.layout.addWidget(self.voltTargetLabel, 0, 1)
        self.layout.addWidget(self.voltTargetSpin, 0, 2)
        self.layout.addWidget(self.voltSliderMinLabel, 1, 1)
        self.layout.addWidget(self.voltSlider, 1, 2)
        self.layout.addWidget(self.voltSliderMaxLabel, 1, 3)
        self.layout.addWidget(self.voltActualLabel, 2, 1)
        self.layout.addWidget(self.voltActualValue, 2, 2)

        self.layout.addWidget(self.statusLabel, 0, 4)
        self.layout.addWidget(self.statusTextBox, 1, 4)

        self.setLayout(self.layout)