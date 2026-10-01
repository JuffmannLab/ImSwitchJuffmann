from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController


class DDSController(ImConWidgetController):
    """"Linked to DDSWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


        self.__logger = initLogger(self)
