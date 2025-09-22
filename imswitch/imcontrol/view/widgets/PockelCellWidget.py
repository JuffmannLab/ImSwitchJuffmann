from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class PockelCellWidget(Widget):

    sigSendControl = QtCore.Signal()
    sigSendVoltage = QtCore.Signal()

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
        self.voltSliderMinLabel.setAlignment(QtCore.Qt.AlignRight)
        self.voltSliderMaxLabel = QtWidgets.QLabel("3000V")
        self.voltActualLabel = QtWidgets.QLabel("Actual Voltage [V]: ")
        self.voltActualValue = QtWidgets.QLabel("")
        self.voltSend = guitools.BetterPushButton("Send target voltage")


        #Status
        self.statusLabel = QtWidgets.QLabel("Status flags")
        self.statusTextBox = QtWidgets.QTextEdit()
        self.statusTextBox.setReadOnly(True)
        self.statusTextBox.setPlaceholderText("Status flags will appear here")

        self.layout.addWidget(self.flagLabel, 0, 0)
        self.layout.addWidget(self.flagHV, 2, 0)
        self.layout.addWidget(self.flagRemote, 3, 0)
        self.layout.addWidget(self.flagCheckRation, 4, 0)
        self.layout.addWidget(self.flagCalibrate, 5, 0)
        self.layout.addWidget(self.flagReset, 6, 0)
        self.layout.addWidget(self.flagSendButton, 7, 0)

        self.layout.addWidget(self.voltTargetLabel, 0, 1)
        self.layout.addWidget(self.voltTargetSpin, 0, 2)
        self.layout.addWidget(self.voltSliderMinLabel, 2, 1)
        self.layout.addWidget(self.voltSlider, 1, 2, 2, 1)
        self.layout.addWidget(self.voltSliderMaxLabel, 2, 3)
        self.layout.addWidget(self.voltActualLabel, 3, 1)
        self.layout.addWidget(self.voltActualValue, 3, 2)
        self.layout.addWidget(self.voltSend, 4, 1)

        self.layout.addWidget(self.statusLabel, 0, 4)
        self.layout.addWidget(self.statusTextBox, 1, 4, 4, 1)

        self.setLayout(self.layout)

        self.voltSlider.valueChanged.connect(self.setVoltValue)
        self.voltTargetSpin.valueChanged.connect(self.setVoltValue)

        self.flagSendButton.clicked.connect(
            lambda: self.sigSendControl.emit()
        )

        self.voltSend.clicked.connect(
            lambda: self.sigSendVoltage.emit()
        )

    def setVoltValue(self, value):
        self.voltSlider.setValue(value)
        self.voltTargetSpin.setValue(value)

    def getVoltage(self):
        spin_value = self.voltTargetSpin.value()
        slider_value = self.voltSlider.value()
        if spin_value == slider_value:
            return spin_value
        else:
            return 0

    def getControlBits(self):
        controlbits = {
            "HV": self.flagHV.isChecked(),
            "Remote": self.flagRemote.isChecked(),
            "Ratio": self.flagCheckRation.isChecked(),
            "Calibrate": self.flagCalibrate.isChecked(),
            "Reset": self.flagReset.isChecked()
        }
        return controlbits
    def setStatus(self, status):
        self.statusTextBox.setText(status)