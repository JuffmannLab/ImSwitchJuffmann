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
        self._widget.sigHome.connect(self.moveHome)

    def __del__(self):
        self._master.DelayStageManager.Close()


    def updateValue(self, value):
        self._master.DelayStageManager.Update(value)
        self._widget.setDelaystarting(self._master.DelayStageManager.GetPos())

    def updateLabel(self, value: float):
        self._widget.setLabel("Stage moving", "red")
        QtCore.QTimer.singleShot(value, lambda: self._widget.setLabel("at rest", "green"))


    def moveStage(self, value):
        self._master.DelayStageManager.Move(value)
        pos = self._master.DelayStageManager.GetPos()
        delay = int(abs((value - pos)*1000)+1000)
        self.updateLabel(delay)

    def moveHome(self):
        delay = int(abs((self._master.DelayStageManager.GetPos())*1000)+1000)
        self.updateLabel(delay)
        time.sleep(0.5)
        self._master.DelayStageManager.Home()
        self._widget.setDelaystarting(0.0)


    def cleanupfunction(self):
        self._master.DelayStageManager.Close()