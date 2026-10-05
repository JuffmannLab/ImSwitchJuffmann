from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController


class DDSController(ImConWidgetController):
    """"Linked to DDSWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._widget.sigSetClicked.connect(self.setChannels)


    def setChannels(self):
        paramsToSet = {}
        for i in range(0, 4):
            if self._widget.isActive[i]:
                currentParams = [self._widget.getFreq[i], self._widget.getPhase[i], self._widget.getAmplitude[i]]
                paramsToSet.update({i: currentParams})

        if len(paramsToSet) != 0:
            #TODO manager!