from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class SynthControlWidget(Widget):
    sigAmpValueChanged = QtCore.Signal(str, int)
    sigSomethingChanged = QtCore.Signal(int)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #main layout
        self.setLayout(QtWidgets.QGridLayout())

        #subcomponents
        #Documentation example
        self.examplegroup = QtWidgets.QGroupBox("Example Docu")
        examplelayout = QtWidgets.QGridLayout()

        self.spin = QtWidgets.QSpinBox()
        self.label = QtWidgets.QLabel("This is a label")
        examplelayout.addWidget(self.label, 0, 0)
        examplelayout.addWidget(self.spin, 0, 1)

        #Amplitude control group
        self.ampControlGroup = QtWidgets.QGroupBox("Synthesizer Amplitude Control")
        amplayout = QtWidgets.QGridLayout()

        #hardcoded the number of channels for current synth

        self.ch1button = guitools.BetterPushButton('Channel 1')
        self.ch1button.setCheckable(True)

        self.ch1SpinBox = QtWidgets.QSpinBox()
        self.ch1SpinBox.setRange(0,100)

        self.ch1AmpSlider = guitools.BetterSlider(QtCore.Qt.Vertical, self, allowScrollChanges=False)
        self.ch1AmpSlider.setRange(0, 100)


        self.ch2button = guitools.BetterPushButton('Channel 2')
        self.ch2button.setCheckable(True)

        self.ch2SpinBox = QtWidgets.QSpinBox()
        self.ch2SpinBox.setRange(0, 100)

        self.ch2AmpSlider = guitools.BetterSlider(QtCore.Qt.Vertical, self, allowScrollChanges=False)
        self.ch2AmpSlider.setRange(0, 100)

        amplayout.addWidget(self.ch1SpinBox, 0, 0, 1, 1)
        amplayout.addWidget(self.ch1AmpSlider, 1, 0, 1, 1)
        amplayout.addWidget(self.ch1button, 2, 0, 1, 1)

        amplayout.addWidget(self.ch2SpinBox, 0, 1, 1, 1)
        amplayout.addWidget(self.ch2AmpSlider, 1, 1, 1, 1)
        amplayout.addWidget(self.ch2button, 2, 1, 1, 1)

        self.ampControlGroup.setLayout(amplayout)
        self.examplegroup.setLayout(examplelayout)
        self.layout().addWidget(self.ampControlGroup)
        self.layout().addWidget(self.examplegroup)

        #connect signals
        self.ch1AmpSlider.valueChanged.connect(
            lambda value: self.sigAmpValueChanged.emit("1", value)
        )
        self.ch1SpinBox.valueChanged.connect(
            lambda value: self.sigAmpValueChanged.emit("1", value)
        )

        self.ch2AmpSlider.valueChanged.connect(
            lambda value: self.sigAmpValueChanged.emit("2", value)
        )
        self.ch2SpinBox.valueChanged.connect(
            lambda value: self.sigAmpValueChanged.emit("2", value)
        )

        self.spin.valueChanged.connect(self.sigSomethingChanged)

    def updateAmpValue(self, ID, value):
        if ID == "1":
            if value != self.ch1AmpSlider.value():
                self.ch1AmpSlider.setValue(value)
            if value != self.ch1SpinBox.value():
                self.ch1SpinBox.setValue(value)
        elif ID == "2":
            if value != self.ch2AmpSlider.value():
                self.ch2AmpSlider.setValue(value)
            if value != self.ch2SpinBox.value():
                self.ch2SpinBox.setValue(value)

    def updateLabel(self, text):
        self.label.setText(text)