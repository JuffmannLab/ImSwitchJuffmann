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

        #ImagePlayer Config group
        self.imPlayerGroup = QtWidgets.QGroupBox("Image Player Configuration")
        imPlayerLayout = QtWidgets.QGridLayout()

        self.clockRateLabel = QtWidgets.QLabel("Clock Rate [1-5000 kHz]")
        self.clockRateEdit = QtWidgets.QSpinBox()
        self.clockRateEdit.setRange(1, 5000)
        self.clockRateEdit.setValue(100)

        self.triggerRadioButtonCon = QtWidgets.QRadioButton("Continuous Trigger")
        self.triggerRadioButtonExt = QtWidgets.QRadioButton("External Trigger")
        self.triggerRadioButtonExt.setChecked(True)

        self.repeatOptions = QtWidgets.QComboBox()
        self.repeatOptions.addItem("No Repeats")
        self.repeatOptions.addItem("Programmed Repeats")
        self.repeatOptions.addItem("Repeat Forever")

        self.programmedRepeats = QtWidgets.QSpinBox()
        self.programmedRepeats.setMinimum(0)
        self.programmedRepeats.setValue(0)

        self.imageTable = QtWidgets.QTableWidget(1,4)
        dummy = QtWidgets.QTableWidgetItem("ID: 0  -  Name: example  -  ImagePoints: 400  -   Size: 1600 bytes", 0)
        self.imageTable.setItem(0, 0, dummy)

        self.currentImageLabel = QtWidgets.QLabel("Current Image selected:")
        self.currentImage = QtWidgets.QComboBox()

        self.startButton = guitools.BetterPushButton("Start image playback")
        self.startButton.setCheckable(True)
        self.stopButton = guitools.BetterPushButton("Stop image playback")


        imPlayerLayout.addWidget(self.clockRateLabel, 0, 0, 1, 1)
        imPlayerLayout.addWidget(self.clockRateEdit, 0, 1, 1, 1)
        imPlayerLayout.addWidget(self.imageTable, 0, 2, 2, 3)

        imPlayerLayout.addWidget(self.triggerRadioButtonCon, 1, 0, 1, 1)
        imPlayerLayout.addWidget(self.triggerRadioButtonExt, 1, 1, 1, 1)

        imPlayerLayout.addWidget(self.currentImageLabel, 2, 0, 1, 1)
        imPlayerLayout.addWidget(self.currentImage, 2, 1, 1, 1)
        imPlayerLayout.addWidget(self.repeatOptions, 2, 2, 1, 1)
        imPlayerLayout.addWidget(self.programmedRepeats, 2, 3, 1, 1)

        imPlayerLayout.addWidget(self.startButton, 3, 0, 1, 1)
        imPlayerLayout.addWidget(self.stopButton, 3, 1, 1, 1)


        self.imPlayerGroup.setLayout(imPlayerLayout)
        self.layout().addWidget(self.imPlayerGroup)
