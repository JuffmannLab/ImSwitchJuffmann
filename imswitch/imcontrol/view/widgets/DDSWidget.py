from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class DDSWidget(Widget):

    sigSetClicked = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #Overall VBOX Layout
        mainLayout = QtWidgets.QVBoxLayout()
        #Channel Control Group
        self.channelGroup = QtWidgets.QGroupBox("Channel Control")
        channelLayout = QtWidgets.QGridLayout()

        self.ch0 = guitools.BetterPushButton("CH0")
        self.ch0.setCheckable(True)
        self.ch0.setChecked(False)

        self.ch1 = guitools.BetterPushButton("CH1")
        self.ch1.setCheckable(True)
        self.ch1.setChecked(False)

        self.ch2 = guitools.BetterPushButton("CH2")
        self.ch2.setCheckable(True)
        self.ch2.setChecked(False)

        self.ch3 = guitools.BetterPushButton("CH3")
        self.ch3.setCheckable(True)
        self.ch3.setChecked(False)

        self.freqLabel = QtWidgets.QLabel("Frequency (MHz)")
        self.phaseLabel = QtWidgets.QLabel("Phase (degrees)")
        self.ampLabel = QtWidgets.QLabel("Amplitude (0-1V)")

        self.ch0Freq = QtWidgets.QLineEdit()
        self.ch0Phase = QtWidgets.QLineEdit()
        self.ch0Amp = QtWidgets.QLineEdit()

        self.ch1Freq = QtWidgets.QLineEdit()
        self.ch1Phase = QtWidgets.QLineEdit()
        self.ch1Amp = QtWidgets.QLineEdit()

        self.ch2Freq = QtWidgets.QLineEdit()
        self.ch2Phase = QtWidgets.QLineEdit()
        self.ch2Amp = QtWidgets.QLineEdit()

        self.ch3Freq = QtWidgets.QLineEdit()
        self.ch3Phase = QtWidgets.QLineEdit()
        self.ch3Amp = QtWidgets.QLineEdit()

        self.setChannelsBtn = guitools.BetterPushButton("Set Active Channels")

        self.statusLabel = QtWidgets.QLabel("Status:")
        self.statusMessage = QtWidgets.QLabel("...")

        channelLayout.addWidget(self.ch0, 0, 1, 1, 1)
        channelLayout.addWidget(self.ch1, 0, 2, 1, 1)
        channelLayout.addWidget(self.ch2, 0, 3, 1, 1)
        channelLayout.addWidget(self.ch3, 0, 4, 1, 1)

        channelLayout.addWidget(self.freqLabel, 1, 0, 1, 1)
        channelLayout.addWidget(self.phaseLabel, 2, 0, 1, 1)
        channelLayout.addWidget(self.ampLabel, 3, 0, 1, 1)

        channelLayout.addWidget(self.ch0Freq, 1, 1, 1, 1)
        channelLayout.addWidget(self.ch0Phase, 2, 1, 1, 1)
        channelLayout.addWidget(self.ch0Amp, 3, 1, 1, 1)

        channelLayout.addWidget(self.ch1Freq, 1, 2, 1, 1)
        channelLayout.addWidget(self.ch1Phase, 2, 2, 1, 1)
        channelLayout.addWidget(self.ch1Amp, 3, 2, 1, 1)

        channelLayout.addWidget(self.ch2Freq, 1, 3, 1, 1)
        channelLayout.addWidget(self.ch2Phase, 2, 3, 1, 1)
        channelLayout.addWidget(self.ch2Amp, 3, 3, 1, 1)

        channelLayout.addWidget(self.ch3Freq, 1, 4, 1, 1)
        channelLayout.addWidget(self.ch3Phase, 2, 4, 1, 1)
        channelLayout.addWidget(self.ch3Amp, 3, 4, 1, 1)

        channelLayout.addWidget(self.setChannelsBtn, 4, 0, 1, 2)
        channelLayout.addWidget(self.statusLabel, 4, 2, 1, 1)
        channelLayout.addWidget(self.statusMessage, 4, 3, 1, 2)
        self.channelGroup.setLayout(channelLayout)

        #Table Control Group
        self.tableGroup = QtWidgets.QGroupBox("Table Control")
        tableLayout = QtWidgets.QGridLayout()

        self.table = QtWidgets.QTableWidget()
        self.table.setRowCount(3)
        self.table.setColumnCount(4)

        #Table formatting nightmare
        vheader = self.table.verticalHeader()
        vheader.setStretchLastSection(False)
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        vheader.setDefaultSectionSize(30)
        self.table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        hheader = self.table.horizontalHeader()
        hheader.setSectionResizeMode(
            QtWidgets.QHeaderView.Fixed
        )

        self.rowLabel = QtWidgets.QLabel("Format: Row, Dwell(µs), Channel#, Frequency(MHz), Phase(°), Amplitude(0-1V)")
        self.rowEdit = QtWidgets.QLineEdit()
        self.rowAddBtn = guitools.BetterPushButton("Add row")

        self.rowIdx = QtWidgets.QSpinBox()
        self.rowIdx.setRange(0, 14249)
        self.rowDelBtn = guitools.BetterPushButton("Delete row")

        self.tableCommand = QtWidgets.QComboBox()
        self.tableCommand.addItems(["TSAVE", "TSTOP", "TCLEAR", "TRUN", "TONCE"])
        self.tableCmdBtn = guitools.BetterPushButton("Send command")

        tableLayout.addWidget(self.tableCommand, 0, 0, 1, 2)
        tableLayout.addWidget(self.tableCmdBtn, 0, 2, 1, 1)

        tableLayout.addWidget(self.rowLabel, 1, 0, 1, 2)
        tableLayout.addWidget(self.rowEdit, 2, 0, 1, 2)
        tableLayout.addWidget(self.rowAddBtn, 2, 2, 1, 1)

        tableLayout.addWidget(self.rowIdx, 3, 0, 1, 1)
        tableLayout.addWidget(self.rowDelBtn, 3, 1, 1, 1)

        tableLayout.addWidget(self.table, 0, 3, 5, 3)

        tableLayout.setRowStretch(0, 0)
        tableLayout.setRowStretch(1, 0)
        tableLayout.setRowStretch(2, 0)
        tableLayout.setRowStretch(3, 0)
        tableLayout.setRowStretch(4, 1)

        self.tableGroup.setLayout(tableLayout)


        mainLayout.addWidget(self.channelGroup, 0)
        mainLayout.addWidget(self.tableGroup, 0)
        mainLayout.addStretch(1)

        self.setLayout(mainLayout)

        #connect signals
        self.setChannelsBtn.clicked.connect(self.sigSetClicked)

        #Helper variables
        self.channels = [self.ch0, self.ch1, self.ch2, self.ch3]
        self.frequencies = [self.ch0Freq, self.ch1Freq, self.ch2Freq, self.ch3Freq]
        self.phases = [self.ch0Phase, self.ch1Phase, self.ch2Phase, self.ch3Phase]
        self.amplitudes = [self.ch0Amp, self.ch1Amp, self.ch2Amp, self.ch3Amp]

        def isActive(self, int):
            return self.channels[int].isChecked()

        def getFreq(self, int):
            return self.frequencies[int].text()

        def getPhase(self, int):
            return self.phases[int].text()

        def getAmplitude(self, int):
            return self.amplitudes[int].text()
