import ctypes
from ctypes import c_int, c_double, byref
from .PositionerManager import PositionerManager
from ...interfaces.MCL_microdrive_iscat import MicroDrive
from imswitch.imcommon.model import initLogger



class MCLPositionerManager(PositionerManager):
    def __init__(self, positionerInfo, name, **kwargs):
        self.__logger = initLogger(self, instanceName=name)
        # Use managerProperties instead of direct attribute access
        manager_props = positionerInfo.managerProperties or {}

        # Extract mock flag, library path, and axes safely
        self._mock = manager_props.get('mock', False)
        self._libraryPath = manager_props.get('libraryPath', 'MicroDrive/MCL_MICRODrive.dll')

        startPosition = float(manager_props.get('startPosition', 0))

        if not self._mock:
            self.MicroDrive = MicroDrive()
            if self.MicroDrive.handle > 0:
                self.__logger.info('Connected to MCL stage: ' + str(self.MicroDrive.serialNumber) + ', with handle: ' + str(
                    self.MicroDrive.handle))
                self.MicroDrive.moveCoordinate(startPosition)
            else:
                self.__logger.warning('Connection failed. Maybe the device is turned off?')


        initialPosition = {"X": 0, "Y": 0, "Z": startPosition}
        self._position = initialPosition
        super().__init__(positionerInfo, name, initialPosition=initialPosition)

    def moveCoordinate(self, x):
        #check if motors are still moving first
        if self.MicroDrive.isMoving():
            self.__logger.warning("Motors are still moving, try again later.")
            return self.getPosition()

        if x > 25 or x < 0:
            self.__logger.error("Given position is out of bounds. Please enter a value between 0 and 25.")
            return self.getPosition()

        errorNumber, position = self.MicroDrive.moveCoordinate(x)
        if errorNumber != 0:
            self.__logger.error('Error while moving axis: ' + self.MicroDrive.errorDictionary[errorNumber])

        # Check if motors moved out of bounds
        status = self.MicroDrive.getStatus()
        if status[0] != [0, 0, 'All ok']:
            self.__logger.warning('Motor moved out of bounds: ' + str([temp[2] for temp in status]))
        return round(position, 4)

    def microUp(self):
        if self.MicroDrive.isMoving():
            self.__logger.warning("Motors are still moving, try again later.")
            return self.getPosition()

        errorNumber, position = self.MicroDrive.moveMicrostepUp()

        if errorNumber != 0:
            self.__logger.error('Error while moving axis: ' + self.MicroDrive.errorDictionary[errorNumber])

        # Check if motors moved out of bounds
        status = self.MicroDrive.getStatus()
        if status[0] != [0, 0, 'All ok']:
            self.__logger.warning('Motor moved out of bounds: ' + str([temp[2] for temp in status]))
        return round(position, 4)

    def microDown(self):
        if self.MicroDrive.isMoving():
            self.__logger.warning("Motors are still moving, try again later.")
            return self.getPosition()
        errorNumber, position = self.MicroDrive.moveMicrostepDown()

        if errorNumber != 0:
            self.__logger.error('Error while moving axis: ' + self.MicroDrive.errorDictionary[errorNumber])

        # Check if motors moved out of bounds
        status = self.MicroDrive.getStatus()
        if status[0] != [0, 0, 'All ok']:
            self.__logger.warning('Motor moved out of bounds: ' + str([temp[2] for temp in status]))
        return round(position, 4)

    def moveToZero(self):
        errorNumber, position = self.MicroDrive.home()
        if errorNumber != 0:
            self.__logger.error('Error while moving to zero position: ' + self.MicroDrive.errorDictionary[errorNumber])
        return round(position, 4)


    def move(self, dist, axis):
        target_pos = self._position[axis] + dist
        self.setPosition(target_pos, axis)

    def setPosition(self, position, axis):
        self._position[axis] = position
        if not self._mock:
            self.MicroDrive.moveAxis(1, position)

    def get_abs(self):
        if self._mock:
            return {axis: self._position[axis] for axis in self.axes}
        else:
            pos = {}
            for axis_index, axis in enumerate(self.axes):
                val = c_double()
                self.dll.MDGetPosition(self.handle, c_int(axis_index), byref(val))
                pos[axis] = val.value
            return pos

    def getPosition(self):
        errorNumber, pos = self.MicroDrive.getPosition()
        if errorNumber != 0:
            self.__logger.error('Error reading the encoders: ' + self.MicroDrive.errorDictionary[errorNumber])
        return round(pos, 4)

    def finalize(self):
        self.MicroDrive.closeConnection()