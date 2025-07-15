from qtpy import QtCore, QtWidgets, QtGui

from imswitch.imcommon.model.shortcut import shortcut
from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class ViewWidget(Widget):
    """ View settings (liveview, grid, crosshair).
        Adapted for a separate Differential View Button"""

    sigGridToggled = QtCore.Signal(bool)  # (enabled)
    sigCrosshairToggled = QtCore.Signal(bool)  # (enabled)
    sigLiveviewToggled = QtCore.Signal(bool)  # (enabled)
    sigDifferentialviewToggled = QtCore.Signal(bool)
    sigSliderValueChanged = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Graphical elements
        # Grid
        self.gridButton = guitools.BetterPushButton('Grid')
        self.gridButton.setCheckable(True)
        self.gridButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                      QtWidgets.QSizePolicy.Expanding)

        # Crosshair
        self.crosshairButton = guitools.BetterPushButton('Crosshair')
        self.crosshairButton.setCheckable(True)
        self.crosshairButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                           QtWidgets.QSizePolicy.Expanding)
        # liveview
        self.liveviewButton = guitools.BetterPushButton('LIVEVIEW')
        self.liveviewButton.setStyleSheet("font-size:20px")
        self.liveviewButton.setCheckable(True)
        self.liveviewButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Expanding)
        self.liveviewButton.setEnabled(True)

        # Differential View
        self.differentialviewButton = guitools.BetterPushButton('Differential View')
        self.differentialviewButton.setStyleSheet("font-size:20px")
        self.differentialviewButton.setCheckable(True)
        self.liveviewButton.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                          QtWidgets.QSizePolicy.Expanding)
        self.liveviewButton.setEnabled(True)

        # Slider and Input Field for Batch Size
        self.sliderLabel = QtWidgets.QLabel("Batch Size:")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(1, 250)
        self.slider.setValue(1)  
        self.slider.setTickInterval(1)  
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.inputField = QtWidgets.QLineEdit(str(self.slider.value()))
        self.inputField.setValidator(QtGui.QIntValidator(1, 250))
        self.inputField.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.slider.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        # Add elements to GridLayout
        self.viewCtrlLayout = QtWidgets.QGridLayout()
        self.setLayout(self.viewCtrlLayout)
        self.viewCtrlLayout.addWidget(self.liveviewButton, 0, 0, 1, 2)
        self.viewCtrlLayout.addWidget(self.gridButton, 1, 0)
        self.viewCtrlLayout.addWidget(self.crosshairButton, 1, 1)
        self.viewCtrlLayout.addWidget(self.differentialviewButton, 2, 0, 1, 2)
        # Add Slider Row
        sliderLayout = QtWidgets.QHBoxLayout()
        sliderLayout.addWidget(self.sliderLabel)
        sliderLayout.addWidget(self.slider, 1)
        sliderLayout.addWidget(self.inputField)

        # Add to main layout
        self.viewCtrlLayout.addLayout(sliderLayout, 3, 0, 1, 2)

        # Connect signals
        self.gridButton.toggled.connect(self.sigGridToggled)
        self.crosshairButton.toggled.connect(self.sigCrosshairToggled)
        self.liveviewButton.toggled.connect(self.sigLiveviewToggled)
        self.differentialviewButton.toggled.connect(self.sigDifferentialviewToggled)
        self.slider.valueChanged.connect(self.update_input_field)
        self.inputField.textChanged.connect(self.update_slider_value)

    def getLiveViewActive(self):
        return self.liveviewButton.isChecked()

    def update_input_field(self):
        self.inputField.setText(str(self.slider.value()))

    def update_slider_value(self):
        try:
            new_value = int(self.inputField.text())
            if 1 <= new_value <= 250: 
                self.slider.setValue(new_value)
                self.emit_slider_value(new_value)
        except ValueError:
            pass

    def emit_slider_value(self, value=None):
        if value is None:
            value = self.slider.value()
        self.sigSliderValueChanged.emit(value)

    def setViewToolsEnabled(self, enabled, mode):
        self.crosshairButton.setEnabled(enabled)
        self.gridButton.setEnabled(enabled)
        if enabled == True and mode == 'LV':
            self.differentialviewButton.setEnabled(False)
        elif enabled == False and mode == 'LV':
            self.differentialviewButton.setEnabled(True)
        elif enabled == True and mode == 'DV':
            self.liveviewButton.setEnabled(False)
        elif enabled == False and mode == 'DV':
            self.liveviewButton.setEnabled(True)

    def setLiveViewActive(self, active):
        """ Sets whether the LiveView is active. """
        self.liveviewButton.setChecked(active)

    def getDifferentialViewActive(self):
        return self.differentialviewButton.isChecked()
    
    def setDiffrentialViewActive(self, active):
        self.differentialviewButton.setChecked(active)

    def setLiveViewGridVisible(self, visible):
        """ Sets whether the LiveView grid is visible. """
        self.crosshairButton.setChecked(visible)

    def setLiveViewCrosshairVisible(self, visible):
        """ Sets whether the LiveView crosshair is visible. """
        self.gridButton.setChecked(visible)

    @shortcut('Ctrl+L', "Liveview")
    def toggleLiveviewButton(self):
        self.liveviewButton.toggle()

    @shortcut('Ctrl+G', "Grid")
    def toggleGridButton(self):
        self.gridButton.toggle()

    @shortcut('Ctrl+H', "Crosshair")
    def toggleCrosshairButton(self):
        self.crosshairButton.toggle()

    @shortcut('Ctrl+D', "Differential View")
    def toggleDifferentialviewButton(self):
        self.differentialviewButton.toggle()


# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
