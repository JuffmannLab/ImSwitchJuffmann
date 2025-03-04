import sys
from PyQt5.QtWidgets import QApplication
from imswitch.imcommon.model import APIExport
from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger

class ShutterController(ImConWidgetController):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Shutter Manager and UI
        self.shutter_manager = self._master.shutterManager

        # Connect UI signals to ShutterManager actions
        self._widget.sigopenPressed.connect(self.open)
        self._widget.sigclosePressed.connect(self.close)
        self._widget.sigloopPressed.connect(self.loop)
        self._widget.sigsetdelay.connect(self.handle_delay_set)

    def handle_delay_set(self, delay):
        """Stores delay value from UI."""
        self.delay = delay
        print(f"Controller: Delay set to {self.delay} ms")

    def open(self):
        self.shutter_manager.open_shutter(self.delay)

    def close(self):
        self.shutter_manager.close_shutter()

    def loop(self):
        self.shutter_manager.loop_shutter(self.delay)




