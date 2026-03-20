from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class PockelCellWidget(Widget):

    sigSendHV = QtCore.Signal(bool)
    sigSendReset = QtCore.Signal(bool)
    sigSendVoltage = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.layout = QtWidgets.QGridLayout()

        #flags
        self.flagLabel = QtWidgets.QLabel("Control buttons")
        self.flagHV = guitools.BetterPushButton("High Voltage On")
        self.flagHV.setCheckable(True)
        self.flagReset = guitools.BetterPushButton("Reset")

        #Voltage
        self.voltTargetLabel = QtWidgets.QLabel("Target Voltage [V]:")
        self.voltTargetSpin = QtWidgets.QSpinBox()
        self.voltTargetSpin.setMinimum(0)
        self.voltTargetSpin.setMaximum(2000)
        self.voltTargetSpin.setSingleStep(1)
        self.voltTargetSpin.setValue(0)
        self.voltSlider = guitools.BetterSlider(QtCore.Qt.Horizontal)
        self.voltSlider.setRange(0, 2000)
        self.voltSlider.setValue(0)
        self.voltSliderMinLabel = QtWidgets.QLabel("0V")
        self.voltSliderMinLabel.setAlignment(QtCore.Qt.AlignRight)
        self.voltSliderMaxLabel = QtWidgets.QLabel("2000V")
        self.voltSend = guitools.BetterPushButton("Send target voltage")


        self.layout.addWidget(self.flagLabel, 0, 0)
        self.layout.addWidget(self.flagHV, 1, 0)
        self.layout.addWidget(self.flagReset, 2, 0)

        self.layout.addWidget(self.voltTargetLabel, 0, 1)
        self.layout.addWidget(self.voltTargetSpin, 0, 2)
        self.layout.addWidget(self.voltSliderMinLabel, 2, 1)
        self.layout.addWidget(self.voltSlider, 1, 2, 2, 1)
        self.layout.addWidget(self.voltSliderMaxLabel, 2, 3)
        self.layout.addWidget(self.voltSend, 4, 2)

        self.setLayout(self.layout)

        self.voltSlider.valueChanged.connect(self.setVoltValue)
        self.voltTargetSpin.valueChanged.connect(self.setVoltValue)

        self.voltSend.clicked.connect(
            lambda: self.sigSendVoltage.emit()
        )
        self.flagHV.clicked.connect(self.sigSendHV)
        self.flagReset.clicked.connect(self.sigSendReset)

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

    def getHV(self):
        return self.flagHV.isChecked()