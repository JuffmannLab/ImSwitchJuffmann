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
        self._widget.sigCountIR.connect(self.new_count_IR)
        self._widget.sigCountUV.connect(self.new_count_UV)

    def new_count_IR(self, count: int):
        self._master.HWPManager.change_position_IR(count)

    def new_count_UV(self, count: int):
        self._master.HWPManager.change_position_UV(count)

