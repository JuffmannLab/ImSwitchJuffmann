from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class DDSWidget(Widget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #Overall Grid Layout
        self.setLayout(QtWidgets.QGridLayout())

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

        self.tableGroup.setLayout(tableLayout)

        self.layout().addWidget(self.channelGroup)
        self.layout().addWidget(self.tableGroup)