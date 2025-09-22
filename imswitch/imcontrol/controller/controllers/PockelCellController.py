from ..basecontrollers import ImConWidgetController

class PockelCellController(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        data = self.getStatus()
        if data != 0:
            status = ""
            for key, value in data["status"].items():
                if value == True:
                    status = status + key + "\n"
            self._widget.setStatus(status)


            print(data)

        self._widget.sigSendVoltage.connect(self.sendVoltage)
        self._widget.sigSendControl.connect(self.sendControl)


    def getStatus(self):
        data = self._master.PockelCellManager.getStatus()
        return data

    def sendVoltage(self):
        voltages = self._widget.getVoltage()
        self._master.PockelCellManager.sendVoltage(voltages)

    def sendControl(self):
        controlbits = self._widget.getControlBits()
        self._master.PockelCellManager.sendControl(controlbits)


