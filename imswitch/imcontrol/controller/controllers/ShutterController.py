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
        self._widget.addDefault(self.shutter_manager.delay)

        # Connect UI signals to ShutterManager actions
        self._widget.sigSetDelay.connect(self.setDelay)
        self._widget.sigShowDelay.connect(self.showDelay)



    def setDelay(self):
        input = self._widget.delayField.text()
        if input.isdigit():
            self._widget.delayDisplay.setText(input)
        else:
            self._logger.info("Delay needs to be an integer number")
        return

    def showDelay(self):
        self.shutter_manager.showDelay()
        return