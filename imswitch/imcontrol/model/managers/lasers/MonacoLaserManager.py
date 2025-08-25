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
        self.__wavelengthRanges = laserInfo.managerProperties["wavelengthRanges"]
        self.__pulsing = laserInfo.managerProperties["pulsing"]
        self.__repRate = laserInfo.managerProperties["repRate"]

        p = 1 if self.__pulsing else 0
        self.sendCommand(f"SET={self.__repRate}")
        self.sendCommand("PM=2")
        self.sendCommand(f"PC={p}")

        super().__init__(laserInfo, name, isBinary=isBinary, valueUnits=valueUnits,
                         valueDecimals=valueDecimals)

    @property
    def wavelengthRanges(self):
        return self.__wavelengthRanges

    @property
    def pulsing(self) -> bool:
        return self.__pulsing

    @property
    def repRate(self) -> float:
        return self.__repRate

    def setEnabled(self, enabled):
        s = 1 if enabled else 0
        command = f"S={s}"
        response, f_response = self.sendCommand(command)
        return f_response

    def setValue(self, power):
        command = f"RL={power}"
        response, f_response = self.sendCommand(command)
        return f_response

    def setAmplifier(self, reprate, reprateUnits, pulsewidth=278, divisor=1, pulses=1):
        """ The SET command expects the reprate in kHz. Conversion needs to be done first! """
        rr = int(reprate * RR_UNIT_FACTORS[reprateUnits])
        command = f"SET={rr}, {pulsewidth}, {divisor}, {pulses}"
        response, f_response = self.sendCommand(command)
        return rr, f_response

    def getStatus(self):
        command = "?ST"
        response, f_response = self.sendCommand(command)
        try:
            status = response.strip().splitlines()[0]
            return status, f_response
        except Exception as e:
            self.__logger.error(f"Error getting Monaco Status: {e}")

    def startLaser(self):
        command = "L=1"
        response, f_response = self.sendCommand(command)
        return f_response

    def stopLaser(self):
        command = "L=0"
        response , f_response= self.sendCommand(command)
        return f_response

    def togglePulsing(self, pulsing):
        p = 1 if pulsing else 0
        response, f_response = self.sendCommand(f"PC={p}")
        return f_response

    def clearFault(self):
        command = "FACK=1"
        response, f_response = self.sendCommand(command)
        return f_response

    def finalize(self):
        pass

    def sendCommand(self, command: str):
        try:
            with telnetlib.Telnet(HOST, PORT, timeout=3) as tn:
                output = tn.read_until(SHELL_PROMPT).decode('ascii')

                #command
                tn.write(command.encode('ascii') + b'\r\n')
                response = tn.read_until(SHELL_PROMPT).decode('ascii')
                if CONTROL_SEQ in response:
                    self.__logger.error(f'{command} failed, Monaco returns: {response}')
                    tn.close()
                    return None, None

                #check for faults
                f_cmd = "?F"
                tn.write(f_cmd.encode('ascii') + b'\r\n')
                f_response = tn.read_until(SHELL_PROMPT).decode('ascii').splitlines()[0]
                tn.close()
                return response, f_response

        except Exception as e:
            self.__logger.error(f"Failed to connect to Monaco laser: {e}")
            return None, None
