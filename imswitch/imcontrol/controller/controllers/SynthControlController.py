from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class SynthControlController(ImConWidgetController):
    """Linked to SynthControlWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)


        #connect signal widgets

    def updateLabel(self, value):
        if value % 2 == 0:
            self._widget.updateLabel("This is an even number.")
        else:
            self._widget.updateLabel("This is an odd number.")


