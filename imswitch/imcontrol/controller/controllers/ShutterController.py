import sys
from PyQt5.QtWidgets import QApplication
from imswitch.imcommon.model import APIExport
from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import initLogger


class ShutterController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Shutter Manager and UI
        self.shutter_manager = self._master.ShutterManager

        # Connect UI signals to ShutterManager actions
        self._widget.sigSetDelay.connect(self.setDelay)
        self._widget.sigShowDelay.connect(self.showDelay)

    def setDelay(self, delay):
        self.shutter_manager.setDelay(delay)
        return

    def showDelay(self, delay):
        self.shutter_manager.showDelay(delay)
        return