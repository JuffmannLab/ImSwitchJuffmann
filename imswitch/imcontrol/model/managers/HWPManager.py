import imslib as ims
from imswitch.imcommon.model import initLogger
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import libximc.highlevel as ximc


class HWPManager:

    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self._deviceProperties = self._setupInfo['ShuttersArduino'].managerProperties
        self.ser = None

        self.connection = ims.ConnectionList(max_discover_timeout_ms=100) #milliseconds

    def connectDevice(self):
        return

    def newSignal(self, cmd):
        self.ser.write(cmd.encode('ascii'))

    def get_starting_position(self):
        a = ximc.Axis(r"xi-com:\\.\COM3"); a.open_device()
        try:
            print(int(a.get_position().Position))
        finally:
            a.close_device()