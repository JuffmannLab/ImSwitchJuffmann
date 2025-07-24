from .LaserManager import LaserManager
from imswitch.imcontrol.model.interfaces import LantzLaser
from imswitch.imcommon.model import initLogger
import telnetlib

HOST = "192.168.0.5"
PORT = 23
SHELL_PROMPT = b'Monaco>'
CONTROL_SEQ = "Error"

class CoherentLaserManager(LaserManager):
    def __init__(self, laserInfo, name, isBinary=False, valueUnits="", valueDecimals=0,
                 **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        p = 1 if laserInfo.pulsing else 0
        self.sendCommand(f"SET={laserInfo.repRate}")
        self.sendCommand("PM=2")
        self.sendCommand(f"PC={p}")

        super().__init__(laserInfo, name, isBinary=isBinary, valueUnits=valueUnits,
                         valueDecimals=valueDecimals)


    def setEnabled(self, enabled):
        s = 1 if enabled else 0
        command = f"S={s}"
        response = self.sendCommand(command)

    def setValue(self, power):
        command = f"RL={power}"
        response = self.sendCommand(command)

    def setReprate(self, reprate, reprateUnits):
        command = f"SET={reprate}"
        response = self.sendCommand(command)

    def finalize(self):
        pass

    def sendCommand(self, command: str):
        with telnetlib.Telnet(HOST, PORT) as tn:
            output = tn.read_until(SHELL_PROMPT).decode('ascii')
            if "Monaco>" not in output:
                self.__logger.error("Failed to connect to Monaco laser")
                tn.close()
                return None

            tn.write(command.encode('ascii') + b'\r\n')
            response = tn.read_until(SHELL_PROMPT).decode('ascii')
            if CONTROL_SEQ in response:
                self.__logger.error(f'Command failed, Monaco returns: {response}')
            tn.close()
            return response
