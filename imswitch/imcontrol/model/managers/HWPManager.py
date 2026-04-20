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

    def change_position_UV(self, new_position: int, *, wait: bool = True, timeout_ms: int = 1000):
        a = ximc.Axis(rf"xi-com:\\.\{self._deviceProperties_UV['port']}")
        a.open_device()
        try:
            a.command_move(int(new_position), 0)  # absolute move in steps
            if wait:
                a.command_wait_for_stop(timeout_ms)
        finally:
            a.close_device()

    def change_position_IR(self, new_position: int, *, wait: bool = True, timeout_ms: int = 1000):
        a = ximc.Axis(rf"xi-com:\\.\{self._deviceProperties_IR['port']}")
        a.open_device()
        try:
            a.command_move(int(new_position), 0)
            if wait:
                a.command_wait_for_stop(timeout_ms)
        finally:
            a.close_device()