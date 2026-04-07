from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class ShuttersController(ImConWidgetController):
    """Linked to ShuttersWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
