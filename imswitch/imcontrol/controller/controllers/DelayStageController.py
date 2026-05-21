import time
import atexit
from qtpy import QtCore, QtWidgets
from imswitch.imcommon.model import initLogger


from ..basecontrollers import ImConWidgetController

class DelayStageController(ImConWidgetController):
    """Linked to DelayStageWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._master.DelayStageManager.Open()
        self._widget.setDelaystarting(self._master.DelayStageManager.GetPos())

        atexit.register(self.cleanupfunction)

        # connect signal widgets
        self._widget.sigDelayposition.connect(self.moveStage)

    def __del__(self):
        self._master.DelayStageManager.Close()


    def updateValue(self, value):
        self._master.DelayStageManager.Update(value)
        self._widget.setDelaystarting(self._master.DelayStageManager.GetPos())

    def updateLabel(self, value: float):
        pos = self._master.DelayStageManager.GetPos()
        delay = int(abs((value - pos)*1000)+1000)
        self._widget.setLabel("Stage moving", "red")
        QtCore.QTimer.singleShot(delay, lambda: self._widget.setLabel("at rest", "green"))


    def moveStage(self, value):
        self._master.DelayStageManager.Move(value)
        self.updateLabel(value)

    def moveHome(self, value):
        self._master.DelayStageManager.Home
        self.updateLabel(value)


    def cleanupfunction(self):
        self._master.DelayStageManager.Close()