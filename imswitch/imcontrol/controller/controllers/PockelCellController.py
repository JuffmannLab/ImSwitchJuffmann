from ..basecontrollers import ImConWidgetController

class PockelCellController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._widget.sigSendVoltage.connect(self.sendVoltage)
        self._widget.sigSendControl.connect(self.sendControl)

        def sendVoltage(self):
            voltages = self._widget.getVoltage()


        def sendControl(self):
            controlbits = self._widget.getControlBits()

