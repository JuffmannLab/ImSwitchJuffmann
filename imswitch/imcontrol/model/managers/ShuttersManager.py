import imslib as ims
from imswitch.imcommon.model import initLogger
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import serial
import time

class ShuttersManager:

    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self._deviceProperties = self._setupInfo['ShuttersArduino'].managerProperties
        self.ser = None

        self.connection = ims.ConnectionList(max_discover_timeout_ms=100) #milliseconds

    def connectDevice(self):
        if self.ser and self.ser.is_open:
            return  # already connected

        self.ser = serial.Serial()  # do not open yet
        self.ser.port = self._deviceProperties["port"]
        self.ser.baudrate = self._deviceProperties["baudrate"]
        self.ser.timeout = 1

        # make sure HW flow control is off
        self.ser.rtscts = False
        self.ser.dsrdtr = False

        # de-assert lines BEFORE open to avoid auto-reset
        self.ser.dtr = False
        self.ser.rts = False

        self.ser.open()
        time.sleep(2)


    def newSignal(self, cmd):
        self.ser.write(cmd.encode('ascii'))
