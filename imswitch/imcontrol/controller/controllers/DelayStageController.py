from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class DelayStageController(ImConWidgetController):
    """Linked to DelayStageWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._master.DelayStageManager.Open()
        self._widget.setDelaystarting(self._master.DelayStageManager.GetPos())
        self._master.DelayStageManager.PrintPos()
        self._master.DelayStageManager.Close()



        # connect signal widgets


