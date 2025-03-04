from qtpy import QtCore, QtWidgets

from imswitch.imcontrol.view import guitools as guitools
from .basewidgets import Widget

class ShutterWidget(Widget):
    
    sigopenPressed = QtCore.Signal(bool)  # (enabled)
    sigclosePressed = QtCore.Signal()  # (enabled)
    sigloopPressed = QtCore.Signal(bool)  # (pos)
    sigsetdelay = QtCore.Signal(int)  # (rate)    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create Buttons
        self.open_button = guitools.BetterPushButton("OPEN")
        self.close_button = guitools.BetterPushButton("CLOSE")
        self.loop_button = guitools.BetterPushButton("LOOP")
        self.set_delay_button = guitools.BetterPushButton("Set Delay")

        # Create Input Field for Delay
        self.delay_input = QtWidgets.QLineEdit()
        self.delay_input.setPlaceholderText("Enter Delay (ms)")

        # Create Layout
        layout = QtWidgets.QGridLayout()
        layout.addWidget(QtWidgets.QLabel("Delay:"), 0, 0)  # Label for clarity
        layout.addWidget(self.delay_input, 0, 1)
        layout.addWidget(self.set_delay_button, 0, 2, 1, 2)
        layout.addWidget(self.open_button, 1, 0)
        layout.addWidget(self.close_button, 1, 1)
        layout.addWidget(self.loop_button, 1, 2)

        self.setLayout(layout)

        # Connect Signals
        self.open_button.clicked.connect(self.sigopenPressed)
        self.close_button.clicked.connect(self.sigclosePressed.emit)
        self.loop_button.clicked.connect(self.sigloopPressed)
        self.set_delay_button.clicked.connect(self.store_delay)

        self.delay = 0

    def store_delay(self):
        """Stores the delay value from input and emits a signal."""
        try:
            self.delay = int(self.delay_input.text())
            self.sigsetdelay.emit(self.delay)
            print(f"Delay set to {self.delay} ms")
        except ValueError:
            print("Invalid delay value. Please enter a number.")

    def emit_open_signal(self):
        """Emits the open signal with the stored delay."""
        self.sigopenPressed.emit(self.delay)

    def emit_loop_signal(self):
        """Emits the loop signal with the stored delay."""
        self.sigloopPressed.emit(self.delay)

    