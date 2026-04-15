from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class HWPController(ImConWidgetController):
    """Linked to HWPWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        # connect signal widgets
        self._widget.sigCountIR.connect(self.new_count)
        self._widget.sigCountUV.connect(self.new_count)

    def new_count(self, count: int):
        print(count)