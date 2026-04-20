from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class HWPController(ImConWidgetController):
    """Linked to HWPWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        self._widget.setUVstarting(self._master.HWPManager.get_starting_position_UV())
        self._widget.setIRstarting(self._master.HWPManager.get_starting_position_IR())

        # connect signal widgets
        self._widget.sigCountIR.connect(self.new_count)
        self._widget.sigCountUV.connect(self.new_count)

    def new_count(self, count: int):
        print(count)

    def starting_position(self):
        self._master.HWPManager.get_starting_position()