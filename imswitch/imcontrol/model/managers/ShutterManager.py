from imswitch.imcommon.framework import Signal, SignalInterface
from imswitch.imcommon.model import initLogger

class ShutterManager(SignalInterface):
    def __init__(self, shutterInfo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        if shutterInfo is None:
            return
        self.__shutterInfo = shutterInfo
        self.__delay = self.__shutterInfo.delay

    @property
    def delay(self)->int:
        return self.__delay

    def setDelay(self, delay):
        self._delay = delay
        self.__logger.info("Delay set to: %d" % delay)
        return

    def showDelay(self):
        return self._delay