from ..basecontrollers import ImConWidgetController

class PockelCellController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.vMax = 2000    #hardcoded decimal value for highest voltage
        self._widget.sigSendVoltage.connect(self.sendVoltage)
        self._widget.sigSendHV.connect(self.sendHV)
        self._widget.sigSendReset.connect(self.sendReset)


    def sendVoltage(self):
        voltage = self._widget.getVoltage()
        control_voltage = (voltage/self.vMax)*5
        self._master.PockelCellManager.sendVoltage(control_voltage)

    def sendHV(self):
        HV_ON = self._widget.getHV()
        self._master.PockelCellManager.setHV(HV_ON)

    def sendReset(self):
        self._master.PockelCellManager.sendReset()

