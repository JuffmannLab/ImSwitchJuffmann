import imslib as ims
from imswitch.imcommon.model import initLogger
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import libximc.highlevel as ximc


class HWPManager:

    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self._deviceProperties_UV = self._setupInfo['UVHWP'].managerProperties
        self._deviceProperties_IR = self._setupInfo['IRHWP'].managerProperties



    def connectDevice(self):
        return

    def newSignal(self, cmd):
        self.ser.write(cmd.encode('ascii'))

    def get_starting_position_UV(self):
        a = ximc.Axis(rf"xi-com:\\.\{self._deviceProperties_UV['port']}")
        a.open_device()
        b = int(a.get_position().Position)
        a.close_device()
        return b

    def get_starting_position_IR(self):
        a = ximc.Axis(rf"xi-com:\\.\{self._deviceProperties_IR['port']}")
        a.open_device()
        b = int(a.get_position().Position)
        a.close_device()
        return b
