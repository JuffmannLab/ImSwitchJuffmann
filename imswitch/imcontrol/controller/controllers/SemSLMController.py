from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController


class SemSLMController(ImConWidgetController):
    """Linked to SemSLMWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

