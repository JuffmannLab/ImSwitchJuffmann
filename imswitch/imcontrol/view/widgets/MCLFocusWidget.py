import numpy as np
from qtpy import QtWidgets
from qtpy.QtCore import Signal
from PyQt5.QtWidgets import QDoubleSpinBox

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget


class MCLFocusWidget(Widget):
    """Widget for manually controlling the MCL positioner in X, Y, Z directions."""

    sigMoveStage = Signal(float, float, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QVBoxLayout(self)

        # Group box for manual stage control
        stageControlBox = QtWidgets.QGroupBox("MCL Stage Control")
        stageLayout = QtWidgets.QGridLayout(stageControlBox)

        # Position input fields
        self.xEdit = QDoubleSpinBox()
        self.xEdit.setRange(-500.0, 500.0)
        self.xEdit.setSingleStep(0.1)
        self.xEdit.setValue(0.0)


        self.yEdit = QDoubleSpinBox()
        self.yEdit.setRange(-500.0, 500.0)
        self.yEdit.setSingleStep(0.1)
        self.yEdit.setValue(0.0)
        
        
        self.zEdit = QDoubleSpinBox()
        self.zEdit.setRange(-500.0, 500.0)
        self.zEdit.setSingleStep(0.1)
        self.zEdit.setValue(0.0)

        # Button to move the stage
        self.moveButton = QtWidgets.QPushButton("Move Stage")

        # Arrange widgets
        stageLayout.addWidget(QtWidgets.QLabel("X [µm]"), 0, 0)
        stageLayout.addWidget(self.xEdit, 0, 1)
        stageLayout.addWidget(QtWidgets.QLabel("Y [µm]"), 1, 0)
        stageLayout.addWidget(self.yEdit, 1, 1)
        stageLayout.addWidget(QtWidgets.QLabel("Z [µm]"), 2, 0)
        stageLayout.addWidget(self.zEdit, 2, 1)
        stageLayout.addWidget(self.moveButton, 3, 0, 1, 2)

        layout.addWidget(stageControlBox)
        layout.addStretch(1)

        self.moveButton.clicked.connect(self.emitMoveStage)

    def emitMoveStage(self):
        x = self.xEdit.value()
        y = self.yEdit.value()
        z = self.zEdit.value()
        self.sigMoveStage.emit(x, y, z)


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
