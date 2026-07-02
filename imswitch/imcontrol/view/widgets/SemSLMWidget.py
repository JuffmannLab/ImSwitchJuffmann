from PyQt5.QtGui import QPixmap
from qtpy import QtWidgets, QtCore
from .basewidgets import Widget
from pathlib import Path
from imswitch.imcontrol.view import guitools as guitools


class SemSLMWidget(Widget):
    sigSetPresetClicked = QtCore.Signal(bool)
    sigPresetChanged = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.presetPath = Path(__file__).resolve().parents[4]/"slm_presets"

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)



        self.applyBtn = guitools.BetterPushButton("Set selected mask")
        self.maskSelect = QtWidgets.QComboBox()
        self.maskPreview = QtWidgets.QLabel()
        self.fSlider = guitools.BetterSlider(orientation=QtCore.Qt.Horizontal)

        grid.addWidget(self.maskSelect, 0, 0)
        grid.addWidget(self.applyBtn, 0, 1)
        grid.addWidget(self.maskPreview, 0, 2, 2, 2)
        grid.addWidget(self.fSlider, 1, 0, 1, 2)

        self._loadPresets(self.maskSelect, self.maskPreview)

        self.applyBtn.clicked.connect(self.sigSetPresetClicked)
        self.maskSelect.currentTextChanged.connect(self.sigPresetChanged)

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













