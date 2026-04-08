from .basewidgets import Widget
from qtpy import QtWidgets, QtCore
from imswitch.imcontrol.view import guitools as guitools

class ShuttersWidget(Widget):
    sigIRToggled = QtCore.Signal(bool)
    sigUVToggled = QtCore.Signal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        #general layout
        grid = QtWidgets.QGridLayout()
        self.setLayout(grid)

        # Labels and Buttons
        self.labelIR = QtWidgets.QLabel("IR")
        self.labelUV = QtWidgets.QLabel("UV")
        self.labelIR.setAlignment(QtCore.Qt.AlignCenter)
        self.labelUV.setAlignment(QtCore.Qt.AlignCenter)
        self.labelIR.setStyleSheet("font-weight: bold;")
        self.labelUV.setStyleSheet("font-weight: bold;")

        self.btnIR = QtWidgets.QPushButton("IR")
        self.btnUV = QtWidgets.QPushButton("UV")

        for btn in (self.btnIR, self.btnUV):
            btn.setCheckable(True)  # makes them toggle on/off
            btn.setMinimumWidth(60)
            # Visual feedback when toggled on
            btn.setStyleSheet("QPushButton:checked { background-color: #2ecc71; color: white; }")

        # Layout
        grid.addWidget(self.btnIR,  1, 0, 1, 1)
        grid.addWidget(self.btnUV, 1, 1, 1, 1)
        grid.addWidget(self.labelIR, 0, 0, 1, 1)
        grid.addWidget(self.labelUV, 0, 1, 1, 1)

        # Forward signals to controller
        self.btnIR.toggled.connect(self.sigIRToggled)
        self.btnUV.toggled.connect(self.sigUVToggled)


    # Methods the controller calls
    def setIRLabel(self, text: str):
        self.btnIR.setText(text)

    def setUVLabel(self, text: str):
        self.btnUV.setText(text)