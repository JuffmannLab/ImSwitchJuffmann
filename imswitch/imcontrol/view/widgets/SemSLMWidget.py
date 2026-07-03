from PyQt5.QtGui import QPixmap
from qtpy import QtWidgets, QtCore
from .basewidgets import Widget
from pathlib import Path
from imswitch.imcontrol.view import guitools as guitools


class SemSLMWidget(Widget):
    sigSetPresetClicked = QtCore.Signal(bool)
    sigPresetChanged = QtCore.Signal(str)
    sigFValueChanged = QtCore.Signal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.presetPath = Path(__file__).resolve().parents[4]/"slm_presets"

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)



        self.applyBtn = guitools.BetterPushButton("Set mask")
        self.enableFValue = guitools.BetterPushButton("Enable f-value optimization")
        self.enableFValue.setCheckable(True)

        self.saveMaskBtn = guitools.BetterPushButton("Save current mask")
        self.maskSelect = QtWidgets.QComboBox()
        self.maskSelect.view().setTextElideMode(QtCore.Qt.ElideRight)
        self.maskSelect.setFixedWidth(200)

        self.maskPreview = QtWidgets.QLabel()
        self.fLabel = QtWidgets.QLabel("f-value:")
        self.fSpinbox = QtWidgets.QDoubleSpinBox()
        self.fSpinbox.setSingleStep(0.001)
        self.fSpinbox.setDecimals(3)

        grid.addWidget(self.maskSelect, 0, 0, 1, 1)
        grid.addWidget(self.applyBtn, 0, 1, 1, 1)
        grid.addWidget(self.maskPreview, 0, 2, 3, 2)
        grid.addWidget(self.fLabel, 1, 0, 1, 1)
        grid.addWidget(self.fSpinbox, 1, 1, 1, 1)
        grid.addWidget(self.enableFValue, 2, 0, 1, 1)
        grid.addWidget(self.saveMaskBtn, 2, 1, 1, 1)

        self._loadPresets(self.maskSelect, self.maskPreview)

        self.applyBtn.clicked.connect(self.sigSetPresetClicked)
        self.maskSelect.currentTextChanged.connect(self.sigPresetChanged)
        self.fSpinbox.valueChanged.connect(self.sigFValueChanged)

    def _loadPresets(self, combobox, label):
        for preset in self.presetPath.glob("*.bmp"):
            combobox.addItem(preset.name)

        pixmap = QPixmap(str(self.presetPath)+"/"+combobox.currentText())
        label.setFixedSize(400, 240)
        label.setPixmap(
            pixmap.scaled(
                400,
                240,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

    def updatePixmap(self, mask):
        pixmap = QPixmap(mask)
        self.maskPreview.setPixmap(pixmap.scaled(
            400, 240, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
        ))


    def getPresetPath(self):
        return self.presetPath

    def getFValue(self):
        return self.fSpinbox.value()

    def getCurrentMask(self):
        return self.maskSelect.currentText()













