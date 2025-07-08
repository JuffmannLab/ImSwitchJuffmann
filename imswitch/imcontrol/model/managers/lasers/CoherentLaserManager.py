from .LaserManager import LaserManager
from imswitch.imcontrol.model.interfaces import LantzLaser
from imswitch.imcommon.model import initLogger

class CoherentLaserManager(LaserManager):
    def __init__(self, laserInfo, name, isBinary=False, valueUnits="", valueDecimals=0,
                 **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        ports = laserInfo.managerProperties['digitalPorts']

        # Init laser

        self._laser = LantzLaser('cobolt.cobolt0601.Cobolt0601_f2', ports)
        self._numLasers = len(ports)
        self.__logger.info(f'Initialized laser, model: {self._laser.idn}')
        self.__wavelengthRanges = laserInfo.wavelengthRanges

        super().__init__(laserInfo, name, isBinary=isBinary, valueUnits=valueUnits,
                         valueDecimals=valueDecimals)

    @property
    def wavelengthRanges(self):
        """ The initial frequency of the laser modulation. """
        return self.__wavelengthRanges

    def setEnabled(self, enabled):
        self._laser.enabled = enabled

    def setValue(self, power):
        power = int(power)

    def finalize(self):
        self._laser.finalize()