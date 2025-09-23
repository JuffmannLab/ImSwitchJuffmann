from ..basecontrollers import ImConWidgetController

class PockelCellController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.umonMax = 4014 #hardcoded 12-bit value from Powersupply web UI config
        self.vMax = 3000    #hardcoded decimal value for highest voltage
        self.getStatus()
        self._widget.sigSendVoltage.connect(self.sendVoltage)
        self._widget.sigSendControl.connect(self.sendControl)


    def getStatus(self):
        data = self._master.PockelCellManager.getStatus()
        if data != 0:
            status = ""
            for key, value in data["status"].items():
                if value == True:
                    status = status + key + "\n"
            self._widget.setStatus(status)

            actual_voltage  = self.bits_to_voltage(data["outputs"]["umon1"])
            self._widget.setActualVolt(actual_voltage)
        return data

    def sendVoltage(self):
        voltages = self._widget.getVoltage()
        voltage_bits = self.voltage_to_bits(voltages)
        self._master.PockelCellManager.sendVoltage(voltages)

    def sendControl(self):
        controlbits = self._widget.getControlBits()
        self._master.PockelCellManager.sendControl(controlbits)

    def bits_to_voltage(self, bit_value):
        return (bit_value / self.umonMax) * self.vMax

    def voltage_to_bits(self, voltage):
        return int((voltage / self.vMax) * self.umonMax)
