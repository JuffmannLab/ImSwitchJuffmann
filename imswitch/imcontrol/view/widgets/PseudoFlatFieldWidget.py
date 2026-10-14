import os

from qtpy import QtCore, QtGui, QtWidgets

from imswitch.imcontrol.view import guitools
from .basewidgets import Widget


class PseudoFlatFieldWidget(Widget):
    """ Records single images at manually chosen stage positions ("Snap" button or space bar)
    and builds their median as background image for the pseudo flat field view (live image minus
    median). Median images are saved in timestamped folders and can be loaded again. """

    sigAcquisitionToggled = QtCore.Signal(bool)
    sigSnap = QtCore.Signal()
    sigCreateMedian = QtCore.Signal()
    sigLoadMedian = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cameraList = QtWidgets.QComboBox()
        self.framesPerSnapEdit = QtWidgets.QSpinBox()
        self.framesPerSnapEdit.setRange(1, 1000)
        self.framesPerSnapEdit.setValue(1)
        self.framesPerSnapEdit.setToolTip('Number of consecutive frames averaged per snap')

        self.acquisitionButton = guitools.BetterPushButton('Start')
        self.acquisitionButton.setCheckable(True)
        self.snapButton = guitools.BetterPushButton('Snap (Space)')
        self.snapButton.setEnabled(False)
        self.countLabel = QtWidgets.QLabel('Images: 0')

        self.createButton = guitools.BetterPushButton('Create median')
        self.loadButton = guitools.BetterPushButton('Load median…')
        self.statusLabel = QtWidgets.QLabel('No background loaded')
        self.createButton.setToolTip('Median of all snaps, saved in a timestamped folder and used as background')
        self.acquisitionButton.setToolTip('Start/stop taking snaps for a new median background')
        self.statusLabel.setWordWrap(True)

        layout = QtWidgets.QGridLayout()
        self.setLayout(layout)
        layout.addWidget(QtWidgets.QLabel('Camera:'), 0, 0)
        layout.addWidget(self.cameraList, 0, 1)
        layout.addWidget(QtWidgets.QLabel('Frames/snap:'), 1, 0)
        layout.addWidget(self.framesPerSnapEdit, 1, 1)
        layout.addWidget(self.acquisitionButton, 2, 0)
        layout.addWidget(self.snapButton, 2, 1)
        layout.addWidget(self.countLabel, 3, 0, 1, 2)
        layout.addWidget(self.createButton, 4, 0)
        layout.addWidget(self.loadButton, 4, 1)
        layout.addWidget(self.statusLabel, 5, 0, 1, 2)
        layout.setRowStretch(6, 1)

        # Space bar snaps, only while the acquisition is running (otherwise it would take the
        # space key away from all text fields of ImSwitch)
        self.snapShortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Space), self)
        self.snapShortcut.setContext(QtCore.Qt.ApplicationShortcut)
        self.snapShortcut.setEnabled(False)
        self.snapShortcut.activated.connect(self.snapButton.click)

        self.acquisitionButton.toggled.connect(self.sigAcquisitionToggled)
        self.snapButton.clicked.connect(self.sigSnap)
        self.createButton.clicked.connect(self.sigCreateMedian)
        self.loadButton.clicked.connect(self.sigLoadMedian)

    def setCameras(self, names):
        self.cameraList.clear()
        self.cameraList.addItems(names)

    def getCamera(self):
        return self.cameraList.currentText()

    def getFramesPerSnap(self):
        return self.framesPerSnapEdit.value()

    def setAcquisitionActive(self, active):
        """ Updates the buttons for a running/stopped acquisition (without emitting signals). """
        with QtCore.QSignalBlocker(self.acquisitionButton):
            self.acquisitionButton.setChecked(active)
        self.acquisitionButton.setText('Stop' if active else 'Start')
        self.snapButton.setEnabled(active)
        self.snapShortcut.setEnabled(active)
        self.cameraList.setEnabled(not active)
        self.framesPerSnapEdit.setEnabled(not active)

    def setImageCount(self, count):
        self.countLabel.setText(f'Images: {count}')

    def setStatus(self, text):
        self.statusLabel.setText(text)

    def getBaseFolder(self):
        """ Folder in which the median images are saved, one timestamped folder each. """
        return os.path.join(self._options.recording.outputFolder, 'PseudoFlatField')


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
