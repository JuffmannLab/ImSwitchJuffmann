from .LaserManager import LaserManager
from imswitch.imcontrol.model.interfaces import LantzLaser
from imswitch.imcommon.model import initLogger
import telnetlib

HOST = "192.168.0.5"
PORT = 23
SHELL_PROMPT = b'Monaco>'

class CoherentLaserManager(LaserManager):
    def __init__(self, laserInfo, name, isBinary=False, valueUnits="", valueDecimals=0,
                 **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        ports = laserInfo.managerProperties['digitalPorts']

        # Init laser

        self._laser = LantzLaser('cobolt.cobolt0601.Cobolt0601_f2', ports)
        self._numLasers = len(ports)
        self.__logger.info(f'Initialized laser, model: {self._laser.idn}')

        super().__init__(laserInfo, name, isBinary=isBinary, valueUnits=valueUnits,
                         valueDecimals=valueDecimals)


    def setEnabled(self, enabled):
        self._laser.enabled = enabled

    def setValue(self, power):
        command = f"RL={power}"
        response = self.sendCommand(command)

    def finalize(self):
        self._laser.finalize()

    def sendCommand(self, command: str):
        response = ""
        with telnetlib.Telnet(HOST, PORT) as tn:
            output = tn.read_until(SHELL_PROMPT).decode('ascii')
            tn.write(command.encode('ascii') + b'\r\n')
            setresponse = tn.read_until(SHELL_PROMPT).decode('ascii')
            if setresponse " \r\nMonaco>":

            tn.close()
        return response
