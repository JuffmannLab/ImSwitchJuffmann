from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools
import imslib

class SynthControlWidget(Widget):
    sigStartPlayerClicked = QtCore.Signal(bool)
    sigStopPlayerClicked = QtCore.Signal(bool)
    sigRepeatOptionChanged = QtCore.Signal(int)
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
        self.programmedRepeats.setEnabled(False)

        self.imageTable = QtWidgets.QTableWidget(1,4)

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

        #Add signals
        self.repeatOptions.currentIndexChanged.connect(self.sigRepeatOptionChanged)
        self.startButton.clicked.connect(self.sigStartPlayerClicked)
        self.stopButton.clicked.connect(self.sigStopPlayerClicked)

        self.imPlayerGroup.setLayout(imPlayerLayout)
        self.layout().addWidget(self.imPlayerGroup)


    def setImageTable(self, imageTableInfo):
        rows = len(imageTableInfo)
        cols = 3
        self.imageTable.setRowCount(rows)
        self.imageTable.setColumnCount(cols)
        self.imageTable.setHorizontalHeaderLabels(["ID", "Image Points", "Name"])
        for i in range(rows):
            c1 = QtWidgets.QTableWidgetItem(imageTableInfo[i][0])
            c2 = QtWidgets.QTableWidgetItem(imageTableInfo[i][1])
            c3 = QtWidgets.QTableWidgetItem(imageTableInfo[i][2])
            self.imageTable.setItem(i,0,c1)
            self.imageTable.setItem(i,1,c2)
            self.imageTable.setItem(i,2,c3)
            self.currentImage.addItem("ID: "+str(imageTableInfo[i][0]))

    def enableRepeatSpinBox(self, enable):
        self.programmedRepeats.setEnabled(enable)

    def getConfig(self):
        config = {
            "clockrate": imslib.kHz(self.clockRateEdit.value()),
            "repeats": self.programmedRepeats.value(),
            "imageID": self.currentImage.currentIndex()
        }

        option_idx = self.repeatOptions.currentIndex()
        if option_idx == 0:
            config.update({"repeatOption": imslib.ImageRepeats_NONE})
        elif option_idx == 1:
            config.update({"repeatOption": imslib.ImageRepeats_PROGRAM})
        elif option_idx == 2:
            config.update({"repeatOption": imslib.ImageRepeats_FOREVER})

        if self.triggerRadioButtonExt.isChecked():
            config.update({"trigger": imslib.ImageTrigger.EXTERNAL})
        else:
            config.update({"trigger": imslib.ImageTrigger.CONTINUOUS})

        return config

    def isPlaying(self):
        return self.startButton.isChecked()

    def stopClicked(self):
        self.startButton.setChecked(False)
