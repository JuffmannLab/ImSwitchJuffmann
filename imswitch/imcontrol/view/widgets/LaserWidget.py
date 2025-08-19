from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QSizePolicy, QSpacerItem
from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcommon.view.guitools import colorutils
from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class LaserWidget(Widget):
    """ Laser widget for setting laser powers etc. """

    sigEnableChanged = QtCore.Signal(str, bool)  # (laserName, enabled)
    sigValueChanged = QtCore.Signal(str, float)  # (laserName, value)
    sigRepRateChanged = QtCore.Signal(str, float) #(laserName, reprate)
    sigRepEnableChanged = QtCore.Signal(str, bool)   # (laserName, enable reprate edit)
    sigAmpChanged = QtCore.Signal(str, int)            # (lasername, amplifier index value)
    sigPulsingChanged = QtCore.Signal(str, bool)  #(lasername, pulsing on/off)

    sigStartClicked = QtCore.Signal(str, str)  # (Start laser warming up, text of button)
    sigStopClicked = QtCore.Signal(str)  # (Stop laser)

    sigModEnabledChanged = QtCore.Signal(str, bool) # (laserName, modulationEnabled)
    sigFreqChanged = QtCore.Signal(str, int)        # (laserName, frequency)
    sigDutyCycleChanged = QtCore.Signal(str, int)   # (laserName, dutyCycle)

    sigRangeChanged = QtCore.Signal(str, int)  # (wavelength range index)
    sigWavelengthValueChanged = QtCore.Signal(str, int)  # (wavelength value)
    sigWavelengthSliderChanged = QtCore.Signal(str, int)  # (wavelength slider)

    sigPresetSelected = QtCore.Signal(str)  # (presetName)
    sigLoadPresetClicked = QtCore.Signal()
    sigSavePresetClicked = QtCore.Signal()
    sigSavePresetAsClicked = QtCore.Signal()
    sigDeletePresetClicked = QtCore.Signal()
    sigPresetScanDefaultToggled = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.laserModules = {}

        self.setMinimumHeight(320)

        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)

        # Lasers grid
        self.lasersGrid = QtWidgets.QGridLayout()
        self.lasersGrid.setContentsMargins(4, 4, 4, 4)

        self.lasersGridContainer = QtWidgets.QWidget()
        self.lasersGridContainer.setLayout(self.lasersGrid)

        self.scrollArea = QtWidgets.QScrollArea()
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scrollArea.setWidget(self.lasersGridContainer)
        self.scrollArea.setWidgetResizable(True)
        self.lasersGridContainer.installEventFilter(self)

        self.layout.addWidget(self.scrollArea, 0, 0)

        # Presets box
        # self.presetsBox = QtWidgets.QHBoxLayout()
        # self.presetsLabel = QtWidgets.QLabel('Presets: ')
        # self.presetsList = QtWidgets.QComboBox()
        # self.presetsList.currentIndexChanged.connect(
        #     lambda i: self.sigPresetSelected.emit(self.presetsList.itemData(i))
        # )
        # self.loadPresetButton = guitools.BetterPushButton('Load selected')
        # self.loadPresetButton.clicked.connect(self.sigLoadPresetClicked)
        # self.savePresetButton = guitools.BetterPushButton('Save to selected')
        # self.savePresetButton.clicked.connect(self.sigSavePresetClicked)
        # self.savePresetAsButton = guitools.BetterPushButton('Save as…')
        # self.savePresetAsButton.clicked.connect(self.sigSavePresetAsClicked)
        # self.moreButton = QtWidgets.QToolButton()
        # self.moreButton.setText('More…')
        # self.moreButton.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        # self.deletePresetAction = QtWidgets.QAction('Delete selected')
        # self.deletePresetAction.triggered.connect(self.sigDeletePresetClicked)
        # self.moreButton.addAction(self.deletePresetAction)
        # self.presetScanDefaultAction = QtWidgets.QAction('Make selected default for scanning')
        # self.presetScanDefaultAction.triggered.connect(self.sigPresetScanDefaultToggled)
        # self.moreButton.addAction(self.presetScanDefaultAction)
        #
        # self.setCurrentPreset(None)
        # self.setScanDefaultPresetActive(False)
        #
        # self.presetsBox.addWidget(self.presetsLabel)
        # self.presetsBox.addWidget(self.presetsList, 1)
        # self.presetsBox.addWidget(self.loadPresetButton)
        # self.presetsBox.addWidget(self.savePresetButton)
        # self.presetsBox.addWidget(self.savePresetAsButton)
        # self.presetsBox.addWidget(self.moreButton)
        #
        # self.layout.addLayout(self.presetsBox, 1, 0)

    def addLaser(self, laserName, valueUnits, valueDecimals, color, wavelengthRanges, pulsing, repRate, valueRange=None,
                 valueRangeStep=1, frequencyRange=(0, 0, 0)):
        """ Adds a laser module widget. valueRange is either a tuple
        (min, max), or None (if the laser can only be turned on/off).
        frequencyRange is either a tuple (min, max, initVal)
        or (0, 0, 0) (if the laser is not modulated in frequency)"""

        control = LaserModule(
            valueUnits=valueUnits, valueDecimals=valueDecimals, valueRange=valueRange,
            pulsing=pulsing, repRate=repRate,
            tickInterval=5, singleStep=valueRangeStep,
            initialPower=valueRange[0] if valueRange is not None else 0,
            frequencyRange=frequencyRange, wavelengthRanges=wavelengthRanges
        )
        control.sigEnableChanged.connect(
            lambda enabled: self.sigEnableChanged.emit(laserName, enabled)
        )
        control.sigValueChanged.connect(
            lambda value: self.sigValueChanged.emit(laserName, value)
        )

        control.sigRepRateChanged.connect(
            lambda reprate: self.sigRepRateChanged.emit(laserName, reprate)
        )

        control.sigAmpChanged.connect(
            lambda index: self.sigAmpChanged.emit(laserName, index)
        )

        control.sigStartClicked.connect(
            lambda buttontext: self.sigStartClicked.emit(laserName, buttontext)
        )

        control.sigStopClicked.connect(
            lambda: self.sigStopClicked.emit(laserName)
        )

        control.sigPulsingChanged.connect(
            lambda pulsing: self.sigPulsingChanged.emit(laserName, pulsing)
        )

        control.sigRepEnableChanged.connect(
            lambda enable: self.sigRepEnableChanged.emit(laserName, enable)
        )

        if all(num > 0 for num in frequencyRange):
            control.sigModEnabledChanged.connect(
                lambda enabled: self.sigModEnabledChanged.emit(laserName, enabled)
            )
            control.sigFreqChanged.connect(
                lambda frequency: self.sigFreqChanged.emit(laserName, frequency)
            )
            control.sigDutyCycleChanged.connect(
                lambda dutyCycle: self.sigDutyCycleChanged.emit(laserName, dutyCycle)
            )

        if not all(r["min"] == r["max"] for r in wavelengthRanges):
            control.sigRangeChanged.connect(
                lambda index: self.sigRangeChanged.emit(laserName, index)
            )
            control.sigWavelengthValueChanged.connect(
                lambda value: self.sigWavelengthValueChanged.emit(laserName, value)
            )
            control.sigWavelengthSliderChanged.connect(
                lambda value: self.sigWavelengthSliderChanged.emit(laserName, value)
            )


        nameLabel = QtWidgets.QLabel(laserName)
        GUIcolor = colorutils.wavelengthToHex(color)
        nameLabel.setStyleSheet(
            f'font-size: 16px; font-weight: bold; padding: 0 6px 0 12px;'
            f'border-left: 4px solid {GUIcolor}'
        )

        self.lasersGrid.addWidget(nameLabel, len(self.laserModules), 0)
        self.lasersGrid.addWidget(control, len(self.laserModules), 1)
        self.laserModules[laserName] = control

    def isLaserActive(self, laserName):
        """ Returns whether the specified laser is powered on. """
        return self.laserModules[laserName].isActive()

    def getValue(self, laserName):
        """ Returns the value of the specified laser, in the units that the
        laser uses. """
        return self.laserModules[laserName].getValue()

    def setEditable(self, editable):
        """ Sets whether the widget can be interacted with. """
        self.setEnabled(editable)

    def setLaserActive(self, laserName, active):
        """ Sets whether the specified laser is powered on. """
        self.laserModules[laserName].setActive(active)

    def setLaserActivatable(self, laserName, activatable):
        """ Sets whether the specified laser can be (de)activated by the user.
        """
        self.laserModules[laserName].setActivatable(activatable)

    def setLaserEditable(self, laserName, editable):
        """ Sets whether the specified laser's values can be edited by the
        user. """
        self.laserModules[laserName].setEditable(editable)

    def setValue(self, laserName, value):
        """ Sets the value of the specified laser, in the units that the laser
        uses. """
        self.laserModules[laserName].setValue(value)
    
    def setModulationFrequency(self, laserName, value):
        """ Sets the modulation frequency of the specified laser. """
        self.laserModules[laserName].setModulationFrequency(value)

    def setModulationDutyCycle(self, laserName, value):
        """ Sets the modulation duty cycle of the specified laser. """
        self.laserModules[laserName].setModulationDutyCycle(value)

    def updateWavelengthRange(self, laserName, index):
        self.laserModules[laserName].updateWavelengthRange(index)

    def setWavelengthValue(self, laserName, value):
        self.laserModules[laserName].setWavelengthValue(value)

    def getCurrentRange(self, laserName):
        return self.laserModules[laserName].getCurrentRange()

    def displayInvalidWavelength(self, laserName):
        self.laserModules[laserName].displayInvalidWavelength()

    def getRepRateUnits(self, laserName):
        return self.laserModules[laserName].getRepRateUnits()

    def setStatusLabel(self, laserName, status):
        self.laserModules[laserName].setStatusLabel(status)

    def setStatusLight(self, laserName, color):
        self.laserModules[laserName].setStatusLight(color)

    def toggleStartButtonText(self, laserName, text):
        self.laserModules[laserName].toggleStartButtonText(text)

    def setShutterState(self, laserName, state):
        self.laserModules[laserName].setShutterState(state)

    def setAmplifierEditable(self, laserName, enable):
        self.laserModules[laserName].setAmplifierEditable(enable)

    def setRepRateEditable(self, laserName, enable):
        self.laserModules[laserName].setRepRateEditable(enable)

    def getAmplifierIndex(self, laserName):
        return self.laserModules[laserName].getAmplifierIndex()

    def setRepRate(self, laserName, rr):
        self.laserModules[laserName].setRepRate(rr)
    # def getCurrentPreset(self):
    #     """ Returns the name of the currently selected preset. """
    #     return self.presetsList.currentData()
    #
    # def setCurrentPreset(self, name):
    #     """ Sets the selected preset in the preset list. Pass None to unselect
    #     all presets. """
    #     anyPresetSelected = True if name else False
    #
    #     if anyPresetSelected:
    #         nameIndex = self.presetsList.findData(name)
    #         if nameIndex > -1:
    #             self.presetsList.setCurrentIndex(nameIndex)
    #     else:
    #         self.presetsList.setCurrentIndex(-1)
    #
    #     self.loadPresetButton.setEnabled(anyPresetSelected)
    #     self.savePresetButton.setEnabled(anyPresetSelected)
    #     self.deletePresetAction.setEnabled(anyPresetSelected)
    #     self.presetScanDefaultAction.setEnabled(anyPresetSelected)
    #     if not anyPresetSelected:
    #         self.presetScanDefaultAction.setChecked(False)
    #
    # def setScanDefaultPreset(self, name):
    #     """ Sets which preset that is default for scanning. Pass None if there
    #     is no default. """
    #     for i in range(self.presetsList.count()):
    #         self.presetsList.setItemText(i, self.presetsList.itemData(i))
    #
    #     nameIndex = self.presetsList.findData(name)
    #     if nameIndex > -1:
    #         self.presetsList.setItemText(nameIndex, f'{name} [scan default]')
    #
    # def setScanDefaultPresetActive(self, active):
    #     """ Sets whether the preset that is default for scanning is active. """
    #     self.presetScanDefaultAction.setText(
    #         'Make selected default for scanning' if not active else 'Unset default for scanning'
    #     )
    #
    # def addPreset(self, name):
    #     """ Adds a preset to the preset list. """
    #     self.presetsList.addItem(name, name)
    #     self.presetsList.model().sort(0)
    #
    # def removePreset(self, name):
    #     """ Removes a preset from the preset list. """
    #     nameIndex = self.presetsList.findData(name)
    #     if nameIndex > -1:
    #         self.presetsList.removeItem(nameIndex)

    def eventFilter(self, source, event):
        if source is self.lasersGridContainer and event.type() == QtCore.QEvent.Resize:
            # Set correct minimum width (otherwise things can go outside the widget because of the
            # scroll area)
            width = self.lasersGridContainer.minimumSizeHint().width() \
                    + self.scrollArea.verticalScrollBar().width()
            self.scrollArea.setMinimumWidth(width)
            self.setMinimumWidth(width)

        return False


class LaserModule(QtWidgets.QWidget):
    """ Module from LaserWidget to handle a single laser. """

    sigEnableChanged = QtCore.Signal(bool)      # (enable laser)
    sigRepEnableChanged = QtCore.Signal(bool)   # (enable reprate edit)
    sigValueChanged = QtCore.Signal(float)      # (RF Level value)
    sigAmpChanged = QtCore.Signal(int)          # (amplifier index value)
    sigRepRateChanged = QtCore.Signal(float)    # (reprate value)
    sigStartClicked = QtCore.Signal(str)        # (Start laser warming up)
    sigStopClicked = QtCore.Signal()            # (Stop laser)
    sigPulsingChanged = QtCore.Signal(bool)

    sigModEnabledChanged = QtCore.Signal(bool) # (modulation enabled)
    sigFreqChanged = QtCore.Signal(int)        # (frequency)
    sigDutyCycleChanged = QtCore.Signal(int)   # (duty cycle)

    sigRangeChanged = QtCore.Signal(int)            # (wavelength range index)
    sigWavelengthValueChanged = QtCore.Signal(int)  # (wavelength value)
    sigWavelengthSliderChanged = QtCore.Signal(int) # (wavelength slider)

    def __init__(self, valueUnits, valueDecimals, valueRange, pulsing, repRate, tickInterval, singleStep,
                 initialPower, frequencyRange, wavelengthRanges, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.valueDecimals = valueDecimals
        self.wavelengthRanges = wavelengthRanges
        isBinary = valueRange is None
        isModulated = all(num > 0 for num in frequencyRange)
        isTunable = not all(r["min"] == r["max"] for r in wavelengthRanges)
        # Graphical elements
        #Power
        self.setPointLabel = QtWidgets.QLabel(f'RF Level (%):')
        self.setPointLabel.setAlignment(QtCore.Qt.AlignLeft)
        self.setPointEdit = QtWidgets.QSpinBox()
        self.setPointEdit.setFixedWidth(50)
        self.setPointEdit.setAlignment(QtCore.Qt.AlignLeft)
        self.setPointEdit.setRange(1, 100)

        #Amplifier
        self.ampLabel = QtWidgets.QLabel('Amplifier:')
        self.ampLabel.setAlignment(QtCore.Qt.AlignLeft)
        self.ampValues = QtWidgets.QComboBox()
        self.ampValues.addItems(["200 kHz 5x40 µJ", "250 kHz 4x40 µJ",
                                 "330 kHz 3x40 µJ", "500 kHz 2x40 µJ",
                                 "1 MHz 1x40 µJ", "2 MHz 1x20 µJ",
                                 "4 MHz 1x10 µJ", "10 MHz 1x4 µJ",
                                 "50 MHz 1x0.8 µJ"])
        self.ampValues.setFixedWidth(120)
        self.ampValues.setCurrentIndex(5)
        self.ampValues.setEditable(False)
        self.ampValues.setEnabled(False)



        #Reprate
        self.repRateLabel = QtWidgets.QLabel(f'Edit repetition rate:')
        self.repRateLabel.setAlignment(QtCore.Qt.AlignLeft)
        self.repRateEdit = QtWidgets.QLineEdit(str(repRate))
        self.repRateEdit.setFixedWidth(50)
        self.repRateEdit.setAlignment(QtCore.Qt.AlignLeft)
        self.repRateEdit.setEnabled(False)

        self.repRateEditButton = guitools.BetterPushButton("I understand \n reprate risk")
        self.repRateEditButton.setCheckable(True)

        #Pulsing
        self.pulsingLabel = QtWidgets.QLabel("Pulsing:")
        self.pulsingOff = QtWidgets.QRadioButton("Off")
        self.pulsingOn = QtWidgets.QRadioButton("On")
        self.pulsingOff.setChecked(not pulsing)
        self.pulsingOn.setChecked(pulsing)

        #Laser status
        self.statStartButton = guitools.BetterPushButton("Start")
        self.statStartButton.setFixedWidth(40)
        self.statStopButton = guitools.BetterPushButton("Stop")
        self.statStopButton.setFixedWidth(40)
        self.statLabel = QtWidgets.QLabel("System Status:")
        self.statLight = QtWidgets.QLabel()
        self.statLight.setFixedSize(QSize(25, 25))
        self.setStatusLight("grey")


        self.minpower = QtWidgets.QLabel()
        self.minpower.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.maxpower = QtWidgets.QLabel()
        self.maxpower.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        #self.slider = guitools.FloatSlider(QtCore.Qt.Horizontal, self, allowScrollChanges=False,
        #                                   decimals=valueDecimals)
        #self.slider.setFocusPolicy(QtCore.Qt.NoFocus)

        if not isBinary:
            valueRangeMin, valueRangeMax = valueRange

            self.minpower.setText(str(valueRangeMin))
            self.maxpower.setText(str(valueRangeMax))

            # self.slider.setMinimum(valueRangeMin)
            # self.slider.setMaximum(valueRangeMax)
            # self.slider.setTickInterval(tickInterval)
            # self.slider.setSingleStep(singleStep)
            # self.slider.setValue(0)

        powerFrame = QtWidgets.QFrame(self)
        self.powerGrid = QtWidgets.QGridLayout()
        powerFrame.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Plain)
        powerFrame.setLayout(self.powerGrid)


        spacer = QSpacerItem(50,0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.powerGrid.addWidget(self.setPointLabel, 0, 0)
        self.powerGrid.addWidget(self.setPointEdit, 0, 1)
        self.powerGrid.addItem(spacer, 0, 2, 1, 2)
        self.powerGrid.addWidget(self.statStartButton, 0, 4)
        self.powerGrid.addWidget(self.statStopButton, 0, 5)

        self.powerGrid.addWidget(self.ampLabel, 1, 0)
        self.powerGrid.addWidget(self.ampValues, 1, 1, 1, 2)


        self.powerGrid.addWidget(self.repRateLabel, 2, 0)
        self.powerGrid.addWidget(self.repRateEdit, 2, 1)
        self.powerGrid.addWidget(self.repRateEditButton, 2, 2)

        self.powerGrid.addItem(spacer, 2, 3)
        self.powerGrid.addWidget(self.statLight, 2, 4)
        self.powerGrid.addWidget(self.statLabel, 2, 5)

        self.powerGrid.addWidget(self.pulsingLabel, 3, 0)
        self.powerGrid.addWidget(self.pulsingOff, 3, 1)
        self.powerGrid.addWidget(self.pulsingOn, 3, 2)

        self.powerGrid.setColumnStretch(0, 0)  # Label column: no stretch
        self.powerGrid.setColumnStretch(1, 0)  # Edit box: no stretch
        self.powerGrid.setColumnStretch(2, 0)  # Units: no stretch
        self.powerGrid.setColumnStretch(6, 1)

        if isTunable:
            self.wavelengthGroup = QtWidgets.QGroupBox("Wavelength selection")
            self.wavelengthLayout = QtWidgets.QGridLayout()
            self.wavelengthGroup.setLayout(self.wavelengthLayout)

            self.rangeSelector = QtWidgets.QComboBox()
            for r in wavelengthRanges:
                self.rangeSelector.addItem(f"{r.min} - {r.max} nm")

            self.wavelengthEdit = QtWidgets.QLineEdit()
            self.wavelengthEdit.setFixedWidth(50)
            self.invalidValueLabel = QtWidgets.QLabel("")
            self.invalidValueLabel.setStyleSheet("color: red;")

            self.wavelengthSlider = guitools.FloatSlider(QtCore.Qt.Horizontal, self, allowScrollChanges=False, decimals=0)
            self.wavelengthSlider.setFocusPolicy(QtCore.Qt.NoFocus)
            self.wavelengthSlider.setFixedWidth(200)
            self.wavelengthSlider.setTickInterval(1)
            self.wavelengthSlider.setSingleStep(1)
            self.minWavelength = QtWidgets.QLabel()
            self.maxWavelength = QtWidgets.QLabel()




            #Set the range to the first one passed.
            self.updateWavelengthRange(0)

            self.wavelengthLayout.addWidget(QtWidgets.QLabel("Range:"), 0, 0)
            self.wavelengthLayout.addWidget(self.rangeSelector, 0, 1, 1, 2)
            self.wavelengthLayout.addWidget(QtWidgets.QLabel("Value:"), 1, 0)
            self.wavelengthLayout.addWidget(self.wavelengthEdit, 1, 1)
            self.wavelengthLayout.addWidget(self.invalidValueLabel, 1, 2)
            self.wavelengthLayout.addWidget(self.minWavelength, 2, 0, 1, 1)
            self.wavelengthLayout.addWidget(self.wavelengthSlider, 2, 1, 1, 3)
            self.wavelengthLayout.addWidget(self.maxWavelength, 2, 5, 1, 1)

            self.powerGrid.addWidget(self.wavelengthGroup, 5, 0, 1, 3)
        else:
            self.wavelengthLabel = QtWidgets.QLabel(f"Wavelength:")
            self.wavelengthValue = QtWidgets.QLabel(f"{wavelengthRanges[0]['min']} nm")
            self.powerGrid.addWidget(self.wavelengthLabel, 4, 0)
            self.powerGrid.addWidget(self.wavelengthValue, 4, 1)
            #self.powerGrid.setRowStretch(3,0)
            self.powerGrid.setRowStretch(4, 0)
            self.powerGrid.setRowStretch(5, 1)
        if isModulated:
            freqRangeMin, freqRangeMax, initialFrequency = frequencyRange
            # laser modulation widgets
            # enable button
            self.modulationEnable = guitools.BetterPushButton("ON")
            self.modulationEnable.setSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                            QtWidgets.QSizePolicy.Expanding)
            self.modulationEnable.setCheckable(True)

            # frequency slider
            self.modulationFrequencyLabel = QtWidgets.QLabel("Frequency [Hz]")
            self.modulationFrequencyLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.modulationFrequencyEdit = QtWidgets.QLineEdit(str(initialFrequency))
            self.modulationFrequencyEdit.setFixedWidth(50)
            self.modulationFrequencyEdit.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.modulationFrequencyMinLabel = QtWidgets.QLabel(str(freqRangeMin))
            self.modulationFrequencyMaxLabel = QtWidgets.QLabel(str(freqRangeMax))
            self.modulationFrequencySlider = guitools.BetterSlider(QtCore.Qt.Horizontal)
            self.modulationFrequencySlider.setRange(freqRangeMin, freqRangeMax)
            self.modulationFrequencySlider.setValue(initialFrequency)

            # duty cycle slider
            self.modulationDutyCycleLabel = QtWidgets.QLabel("Duty cycle [%]")
            self.modulationDutyCycleLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.modulationDutyCycleEdit = QtWidgets.QLineEdit(str(50))
            self.modulationDutyCycleEdit.setFixedWidth(50)
            self.modulationDutyCycleEdit.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.modulationDutyCycleMinLabel = QtWidgets.QLabel(str(1))
            self.modulationDutyCycleMaxLabel = QtWidgets.QLabel(str(99))
            self.modulationDutyCycleMinLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            self.modulationDutyCycleMaxLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            self.modulationDutyCycleSlider = guitools.BetterSlider(QtCore.Qt.Horizontal)
            self.modulationDutyCycleSlider.setRange(1, 99)
            self.modulationDutyCycleSlider.setValue(50)

            self.modulationGroup = QtWidgets.QGroupBox("Frequency modulation")
            self.modulationLayout = QtWidgets.QGridLayout()

            self.modulationLayout.addWidget(self.modulationFrequencyLabel, 0, 0)
            self.modulationLayout.addWidget(self.modulationFrequencyEdit, 0, 1)
            self.modulationLayout.addWidget(self.modulationFrequencyMinLabel, 0, 2)
            self.modulationLayout.addWidget(self.modulationFrequencySlider, 0, 3)
            self.modulationLayout.addWidget(self.modulationFrequencyMaxLabel, 0, 4)

            self.modulationLayout.addWidget(self.modulationDutyCycleLabel, 1, 0)
            self.modulationLayout.addWidget(self.modulationDutyCycleEdit, 1, 1)
            self.modulationLayout.addWidget(self.modulationDutyCycleMinLabel, 1, 2)
            self.modulationLayout.addWidget(self.modulationDutyCycleSlider, 1, 3)
            self.modulationLayout.addWidget(self.modulationDutyCycleMaxLabel, 1, 4)
            self.modulationLayout.addWidget(self.modulationEnable, 0, 5, 2, 1)
            self.modulationGroup.setLayout(self.modulationLayout)

            self.powerGrid.addWidget(self.modulationGroup, 2, 0, 1, 5)
                
        self.enableButton = guitools.BetterPushButton('Shutter:\nClosed')
        self.enableButton.setMinimumWidth(120)
        self.enableButton.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)
        self.enableButton.setCheckable(True)

        # Add elements to QHBoxLayout
        self.layout = QtWidgets.QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.layout.addWidget(powerFrame)
        if isBinary:
            sizePolicy = powerFrame.sizePolicy()
            sizePolicy.setRetainSizeWhenHidden(True)
            powerFrame.setSizePolicy(sizePolicy)
            powerFrame.hide()
        self.layout.addWidget(self.enableButton)

        # Connect signals
        self.enableButton.toggled.connect(self.sigEnableChanged)
        # self.slider.valueChanged.connect(
        #     lambda value: self.sigValueChanged.emit(value)
        # )
        self.setPointEdit.valueChanged.connect(
            lambda value: self.sigValueChanged.emit(value)
        )

        self.repRateEdit.editingFinished.connect(
            lambda : self.sigRepRateChanged.emit(float(self.repRateEdit.text()))
        )

        self.statStartButton.clicked.connect(
            lambda : self.sigStartClicked.emit(self.statStartButton.text())
        )

        self.statStopButton.clicked.connect(
            lambda : self.sigStopClicked.emit()
        )

        self.pulsingOn.toggled.connect(self.sigPulsingChanged)

        self.ampValues.currentIndexChanged.connect(
            lambda index: self.sigAmpChanged.emit(index)
        )

        self.repRateEditButton.toggled.connect(self.sigRepEnableChanged)

        if isModulated:
            self.modulationEnable.toggled.connect(self.sigModEnabledChanged)
            self.modulationFrequencySlider.valueChanged.connect(
                lambda value: self.sigFreqChanged.emit(value)
            )
            self.modulationFrequencyEdit.returnPressed.connect(
                lambda: self.sigFreqChanged.emit(self.getFrequency())
            )
            self.modulationDutyCycleSlider.valueChanged.connect(
                lambda value: self.sigDutyCycleChanged.emit(value)
            )
            self.modulationDutyCycleEdit.returnPressed.connect(
                lambda: self.sigDutyCycleChanged.emit(self.getDutyCycle())
            )

        if isTunable:
            self.rangeSelector.currentIndexChanged.connect(
                lambda value: self.sigRangeChanged.emit(value)
            )
            self.wavelengthEdit.editingFinished.connect(
                lambda: self.sigWavelengthValueChanged.emit(int(self.wavelengthEdit.text()))
            )
            self.wavelengthSlider.valueChanged.connect(
                lambda value: self.sigWavelengthSliderChanged.emit(value)
            )

    def isActive(self):
        """ Returns whether the laser is powered on. """
        return self.enableButton.isChecked()

    def getValue(self):
        """ Returns the value of the laser, in the units that the laser
        uses. """
        return float(self.setPointEdit.value())
    
    def getFrequency(self):
        """ Returns the selected frequency of the laser.
        """
        return int(self.modulationFrequencyEdit.text())
    
    def getDutyCycle(self):
        """ Returns the selected duty cycle of the laser.
        """
        return int(self.modulationDutyCycleEdit.text())

    def getRepRateUnits(self):
        """  Returns the units of the repRate """
        return str(self.repRateUnits.currentText())
    def setActive(self, active):
        """ Sets whether the laser is powered on. """
        self.enableButton.setChecked(active)

    def setActivatable(self, activatable):
        """ Sets whether the laser can be (de)activated by the user. """
        self.enableButton.setEnabled(activatable)

    def setEditable(self, editable):
        """ Sets whether the laser's values can be edited by the user. """
        self.setPointEdit.setEnabled(editable)
        #self.slider.setEnabled(editable)
        self.enableButton.setEnabled(editable)

    def setValue(self, value):
        """ Sets the value of the laser, in the units that the laser uses. """
        self.setPointEdit.setValue(value)
        #self.slider.setValue(value)
    
    def setModulationFrequency(self, value):
        """ Sets the laser modulation frequency. """
        self.modulationFrequencyEdit.setText(f"{value}")
        self.modulationFrequencySlider.setValue(value)
    
    def setModulationDutyCycle(self, value):
        """ Sets the laser modulation duty cycle. """
        self.modulationDutyCycleEdit.setText(f"{value}")
        self.modulationDutyCycleSlider.setValue(value)

    def updateWavelengthRange(self, index):
        wlrange = self.wavelengthRanges[index]
        self.wavelengthSlider.setMinimum(wlrange.min)
        self.wavelengthSlider.setMaximum(wlrange.max)
        self.minWavelength.setText(str(wlrange.min))
        self.maxWavelength.setText(str(wlrange.max))
        midval = (wlrange.min + wlrange.max) / 2
        self.wavelengthSlider.setValue(midval)
        self.wavelengthEdit.setText(str(midval))

    def setWavelengthValue(self, value):
        self.wavelengthSlider.setValue(value)
        self.wavelengthEdit.setText(str(value))
        self.invalidValueLabel.setText("")

    def getCurrentRange(self):
        idx = self.rangeSelector.currentIndex()
        return self.wavelengthRanges[idx]

    def displayInvalidWavelength(self):
        self.invalidValueLabel.setText("Select a value within specified range.")

    def setStatusLight(self, color:str):
        self.statLight.setStyleSheet(
            f"""
            background-color: {color};
            border-radius: 10px;
            border: 1px solid black;
            """
        )

    def setStatusLabel(self, status:str):
        self.statLabel.setText("System status: " + status)

    def toggleStartButtonText(self, text: str):
        self.statStartButton.setText(text)

    def setShutterState(self, state:str):
        self.enableButton.setText("Shutter:\n" + state)

    def setAmplifierEditable(self, enable):
        self.ampValues.setEnabled(enable)

    def setRepRateEditable(self, enable):
        self.repRateEdit.setEnabled(enable)

    def getAmplifierIndex(self):
        return self.ampValues.currentIndex()

    def setRepRate(self, rr):
        self.repRateEdit.setText(str(rr))
# Copyright (C) 2017 Federico Barabas 2020-2021 ImSwitch developers
# This file is part of Tormenta and ImSwitch.
#
# Tormenta and ImSwitch are free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tormenta and Imswitch are distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
