from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class HWPWidget(Widget):
    sigCountIR = QtCore.Signal(int)
    sigCountUV = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        # Row 1: Header
        self.labelsteps = QtWidgets.QLabel("Steps")
        self.labelsteps.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.labelangle = QtWidgets.QLabel("Angle")
        self.labelangle.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.labelpower = QtWidgets.QLabel("Power")
        self.labelpower.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        # Row 2: IR label, count, angle value, percent
        self.label1 = QtWidgets.QLabel("IR")
        self.label1.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.val1 = QtWidgets.QSpinBox()
        self.val1.setRange(0, 180)
        self.val1.setSuffix("°")
        self.val1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val1.setValue(0)
        self.val1.setKeyboardTracking(False)

        self.perc1 = QtWidgets.QSpinBox()
        self.perc1.setRange(0, 100)
        self.perc1.setSuffix("%")
        self.perc1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.perc1.setValue(0)
        self.perc1.setKeyboardTracking(False)

        self.count1 = QtWidgets.QSpinBox()
        self.count1.setRange(0, 10000)
        self.count1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.count1.setValue(0)
        self.count1.setSingleStep(100)  # adjust as desired
        self.count1.setKeyboardTracking(False)

        # Emit signals when counts change
        self.count1.valueChanged.connect(self.sigCountIR.emit)

        # Row 2: UV label, count, angle value, percent
        self.label2 = QtWidgets.QLabel("UV")
        self.label2.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.val2 = QtWidgets.QSpinBox()
        self.val2.setRange(0, 180)
        self.val2.setSuffix("°")
        self.val2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val2.setValue(0)
        self.val2.setKeyboardTracking(False)

        self.perc2 = QtWidgets.QSpinBox()
        self.perc2.setRange(0, 100)
        self.perc2.setSuffix("%")
        self.perc2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.perc2.setValue(0)
        self.perc2.setKeyboardTracking(False)

        self.count2 = QtWidgets.QSpinBox()
        self.count2.setRange(0, 50000)
        self.count2.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.count2.setValue(0)
        self.count2.setSingleStep(10)  # adjust as desired
        self.count2.setKeyboardTracking(False)

        # Emit signals when counts change
        self.count2.valueChanged.connect(self.sigCountUV.emit)

        # Layout: [Label] [Angle SpinBox] [Slider] [Percent SpinBox] [Count SpinBox]
        grid.addWidget(self.labelsteps, 0, 1, 1, 1)
        grid.addWidget(self.labelangle, 0, 2, 1, 1)
        grid.addWidget(self.labelpower, 0, 3, 1, 1)

        grid.addWidget(self.label1,   1, 0, 1, 1)
        grid.addWidget(self.count1,   1, 1, 1, 1)
        grid.addWidget(self.val1,     1, 2, 1, 1)
        grid.addWidget(self.perc1,    1, 3, 1, 1)


        grid.addWidget(self.label2,   2, 0, 1, 1)
        grid.addWidget(self.count2,   2, 1, 1, 1)
        grid.addWidget(self.val2,     2, 2, 1, 1)
        grid.addWidget(self.perc2,    2, 3, 1, 1)

        # Optional UI polish
        # Set minimum widths or tooltips if desired
        self.perc1.setToolTip("Power/Intensity (%)")
        self.perc2.setToolTip("Power/Intensity (%)")
        self.count1.setToolTip("Counts (0–50000)")
        self.count2.setToolTip("Counts (0–50000)")