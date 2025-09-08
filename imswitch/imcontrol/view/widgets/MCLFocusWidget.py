import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import Signal
from PyQt5.QtWidgets import QDoubleSpinBox

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class MCLFocusWidget(Widget):
    """Widget for manually controlling the MCL positioner in X, Y, Z directions."""

    sigMove = Signal()
    sigMicroUp = Signal()
    sigMicroDown = Signal()
    sigMoveToZero = Signal()
    sigSetFocus = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QVBoxLayout(self)

        # Group box for manual stage control
        stageControlBox = QtWidgets.QGroupBox("MCL Stage Control")
        stageLayout = QtWidgets.QGridLayout(stageControlBox)

        self.posLabel = QtWidgets.QLabel("Current position: ")
        self.posEdit = QtWidgets.QLineEdit()
        self.posEdit.setPlaceholderText("Enter coordinate")
        self.moveCoordinateBtn = guitools.BetterPushButton("Move")
        self.microLabel = QtWidgets.QLabel("Adjust with microsteps:")
        self.microUpBtn = guitools.BetterPushButton("+")
        self.microDownBtn = guitools.BetterPushButton("-")
        self.toZeroBtn = guitools.BetterPushButton("Move to 0 position")
        self.focusLabel = QtWidgets.QLabel("Current focus position: 0")
        self.focusBtn = guitools.BetterPushButton("Save position")




        # Arrange widgets
        stageLayout.addWidget(self.posLabel, 0, 0)
        stageLayout.addWidget(self.posEdit, 0, 1, 1, 2)
        stageLayout.addWidget(self.moveCoordinateBtn, 0, 3)
        stageLayout.addWidget(self.microLabel, 1, 0)
        stageLayout.addWidget(self.microUpBtn, 1, 1)
        stageLayout.addWidget(self.microDownBtn, 1, 2)
        stageLayout.addWidget(self.toZeroBtn, 1, 3)
        stageLayout.addWidget(self.focusLabel, 2, 0, 1, 2)
        stageLayout.addWidget(self.focusBtn, 2, 3)

        layout.addWidget(stageControlBox)
        layout.addStretch(1)

        #connect signals
        self.moveCoordinateBtn.clicked.connect(self.sigMove)
        self.microUpBtn.clicked.connect(self.sigMicroUp)
        self.microDownBtn.clicked.connect(self.sigMicroDown)
        self.toZeroBtn.clicked.connect(self.sigMoveToZero)
        self.focusBtn.clicked.connect(self.sigSetFocus)

    def setPosition(self, position):
        self.posLabel.setText("Current position: "+str(position))

    def getCoordinate(self):
        return float(self.posEdit.text())

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
