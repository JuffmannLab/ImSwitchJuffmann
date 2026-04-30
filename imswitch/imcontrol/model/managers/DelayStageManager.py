import imslib as ims
from imswitch.imcommon.model import initLogger
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import time
import atexit
import os
import sys
from ctypes import *

if sys.version_info < (3, 8):
        os.chdir(r"C:\Program Files\Thorlabs\Kinesis")
else:
        os.add_dll_directory(r"C:\\Program Files\\Thorlabs\\Kinesis")

lib_dll: CDLL = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")
serial_num = c_char_p(b"27503766")

class ShuttersManager:

    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo


