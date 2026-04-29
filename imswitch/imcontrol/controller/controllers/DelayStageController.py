from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class DelayStageController(ImConWidgetController):
    """Linked to DelayStageWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        # connect signal widgets


