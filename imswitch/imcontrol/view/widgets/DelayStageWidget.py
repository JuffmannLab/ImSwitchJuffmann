from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class DelayStageWidget(Widget):
    sigDelayposition = QtCore.Signal(int)
    sigHome = QtCore.Signal(bool)


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)


        self.label1 = QtWidgets.QLabel("at rest")
        self.label1.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

        self.val1 = QtWidgets.QDoubleSpinBox(self)
        self.val1.setRange(0.0, 25.0)
        self.val1.setDecimals(4)  # number of decimal places to show
        self.val1.setSingleStep(0.1)  # step size
        self.val1.setSuffix(" mm")
        self.val1.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.val1.setValue(0.0)
        self.val1.setKeyboardTracking(False)

        self.button1 = QtWidgets.QPushButton("HOME")



        # Emit signals when counts change
        self.val1.valueChanged.connect(self.sigDelayposition.emit)
        self.button1.clicked.connect(self.sigHome.emit)


        # Layout:
        grid.addWidget(self.label1,     0, 0, 1, 1)
        grid.addWidget(self.val1,     0, 1, 1, 1)
        grid.addWidget(self.button1, 0, 2, 1, 1)



    # Methods the controller calls
    def setDelaystarting(self, val: int):
        self.val1.setValue(val)


