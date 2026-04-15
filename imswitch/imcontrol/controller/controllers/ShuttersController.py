from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController

class ShuttersController(ImConWidgetController):
    """Linked to ShuttersWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        # connect signal widgets
        self._widget.sigIRToggled.connect(self.on_ir_toggled)
        self._widget.sigUVToggled.connect(self.on_uv_toggled)

        # Optional: initialize as OFF
        self._widget.setIRLabel("OFF")
        self._widget.setUVLabel("OFF")
        self._master.ShuttersManager.connectDevice()
        self._master.ShuttersManager.newSignal('IR_OFF\n')
        self._master.ShuttersManager.newSignal('UV_OFF\n')

    def on_ir_toggled(self, checked: bool):
        if checked:
            self._widget.setIRLabel("ON")
            self._master.ShuttersManager.newSignal('IR_ON\n')
        else:
            self._widget.setIRLabel("OFF")
            self._master.ShuttersManager.newSignal('IR_OFF\n')


    def on_uv_toggled(self, checked: bool):
        if checked:
            self._widget.setUVLabel("ON")
            self._master.ShuttersManager.newSignal('UV_ON\n')
        else:
            self._widget.setUVLabel("OFF")
            self._master.ShuttersManager.newSignal('UV_OFF\n')
