from imswitch.imcommon.model import initLogger
from .LaserManager import LaserManager
import serial
import time

class gemLaserManager(LaserManager):
    """Laser Manager for a gem Laser which is controlled via Serial Port
    """

    def __init__(self, laserInfo, name):
        super().__init__(laserInfo, name, isBinary = False, valueUnits = 'mW', valueDecimals = 1, isModulated = False)

        self.__logger = initLogger(self, instanceName=name)

        ports = laserInfo.managerProperties['digitalPorts']
        baudrate = laserInfo.managerProperties['baudrate']

        self.ser = serial.Serial(port=ports, baudrate=baudrate, parity=serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, timeout = 1,rtscts=False,  dsrdtr=False, write_timeout = 0)

    def setEnabled(self, enabled):

        if enabled:
            self.ser.write(b'\r\n')
            self.ser.readline()

            self.ser.write(b'ON\r\n')
        else:
            self.ser.write(b'\r\n')
            self.ser.readline()

            self.ser.write(b'OFF\r\n')

    def setValue(self, power):
        self.ser.write(b'\r\n')
        self.ser.readline()

        power_str = f'POWER={power}\r\n'.encode("utf-8")
        self.ser.write(power_str)

    def finalize(self):
        try:
            self.setValue(power=0)
            self.setEnabled(enabled=False)
        except:
            self.__logger.error('Could not disconnect laser savely')
        self.ser.flush()
        time.sleep(0.2)
        self.ser.close()
        self.__logger.info('Successfully disconnected the laser')