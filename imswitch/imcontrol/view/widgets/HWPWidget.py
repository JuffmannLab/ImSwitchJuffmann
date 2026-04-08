from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class HWPWidget(Widget):
    sigValueHWP1 = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        # Row 1: HPW1 label, value field, slider
        self.label1 = QtWidgets.QLabel("HPW1")
        self.label1.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.val1 = QtWidgets.QSpinBox()
        self.val1.setRange(0, 180)
        self.val1.setSuffix("°")
        self.val1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val1.setValue(0)
        self.val1.setKeyboardTracking(False)  # optional

        self.slider1 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider1.setRange(0, 180)
        self.slider1.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider1.setTickInterval(10)
        self.slider1.setSingleStep(1)
        self.slider1.setPageStep(5)
        self.slider1.setValue(0)

        # Sync slider and spinbox + emit signal
        self.slider1.valueChanged.connect(self.val1.setValue)
        self.val1.valueChanged.connect(self.slider1.setValue)
        self.slider1.valueChanged.connect(self.sigValueHWP1.emit)

        # Row 2: HPW2 label, value field, slider
        self.label2 = QtWidgets.QLabel("HPW2")
        self.label2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.val2 = QtWidgets.QSpinBox()
        self.val2.setRange(0, 180)
        self.val2.setSuffix("°")
        self.val2.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.val2.setValue(0)
        self.val2.setKeyboardTracking(False)  # optional

        self.slider2 = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider2.setRange(0, 180)
        self.slider2.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider2.setTickInterval(10)
        self.slider2.setSingleStep(1)
        self.slider2.setPageStep(5)
        self.slider2.setValue(0)

        # Sync slider and spinbox
        self.slider2.valueChanged.connect(self.val2.setValue)
        self.val2.valueChanged.connect(self.slider2.setValue)

        # Layout: [Label] [SpinBox] [Slider]
        grid.addWidget(self.label1,  0, 0, 1, 1)
        grid.addWidget(self.val1,    0, 1, 1, 1)
        grid.addWidget(self.slider1, 0, 2, 1, 1)

        grid.addWidget(self.label2,  1, 0, 1, 1)
        grid.addWidget(self.val2,    1, 1, 1, 1)
        grid.addWidget(self.slider2, 1, 2, 1, 1)

        grid.setColumnStretch(2, 1)