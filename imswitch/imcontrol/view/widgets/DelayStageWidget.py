from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class DelayStageWidget(Widget):
    sigDelayposition = QtCore.Signal(int)


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
        self.val1.setSuffix("steps")
        self.val1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val1.setValue(0)
        self.val1.setKeyboardTracking(False)



        # Emit signals when counts change
        self.val1.valueChanged.connect(self.sigDelayposition.emit)


        # Layout:
        grid.addWidget(self.val1,     0, 0, 1, 1)


    # Methods the controller calls
    def setDelaystarting(self, val: int):
        self.val1.setValue(val)


