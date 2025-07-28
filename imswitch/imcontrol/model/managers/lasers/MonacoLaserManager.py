from .LaserManager import LaserManager
from imswitch.imcontrol.model.interfaces import LantzLaser
from imswitch.imcommon.model import initLogger
import telnetlib

HOST = "192.168.0.5"
PORT = 23
SHELL_PROMPT = b'Monaco>'
CONTROL_SEQ = "Error"
RR_UNIT_FACTORS = {
    "kHz": 1,
    "MHz": 1000,
    "GHz": 1000000,
}

class MonacoLaserManager(LaserManager):
    def __init__(self, laserInfo, name, isBinary=False, valueUnits="", valueDecimals=0,
                 **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        p = 1 if laserInfo.pulsing else 0
        #self.sendCommand(f"SET={laserInfo.repRate}")
        self.sendCommand("PM=2")
        #self.sendCommand(f"PC={p}")

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
        """ The SET command expects the reprate in kHz. Conversion needs to be done first! """
        rr = int(reprate * RR_UNIT_FACTORS[reprateUnits])
        command = f"SET={rr}"
        response = self.sendCommand(command)

    def getStatus(self):
        command = "?ST"
        response = self.sendCommand(command)
        try:
            status = response.strip().splitlines()[0]
            return status
        except Exception as e:
            self.__logger.error(f"Error getting Monaco Status: {e}")

    def startLaser(self):
        command = "L=1"
        #response = self.sendCommand(command)

    def stopLaser(self):
        command = "L=0"
        #response = self.sendCommand(command)

    def togglePulsing(self, pulsing):
        p = 1 if pulsing else 0
        response = self.sendCommand(f"PC={p}")

    def finalize(self):
        pass

    def sendCommand(self, command: str):
        try:
            with telnetlib.Telnet(HOST, PORT, timeout=3) as tn:
                output = tn.read_until(SHELL_PROMPT).decode('ascii')
                if "Monaco>" not in output:
                    self.__logger.error("Failed to connect to Monaco laser")
                    tn.close()
                    return None

                tn.write(command.encode('ascii') + b'\r\n')
                response = tn.read_until(SHELL_PROMPT).decode('ascii')
                if CONTROL_SEQ in response:
                    self.__logger.error(f'{command} failed, Monaco returns: {response}')
                tn.close()
                return response

        except Exception as e:
            self.__logger.error(f"Failed to connect to Monaco laser: {e}")
