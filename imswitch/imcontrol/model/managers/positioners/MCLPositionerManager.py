import ctypes
from ctypes import c_int, c_double, byref
from .PositionerManager import PositionerManager
from ...interfaces.MCL_microdrive_iscat import MicroDrive


class MCLPositionerManager(PositionerManager):
    def __init__(self, positionerInfo, name, **kwargs):
        # Use managerProperties instead of direct attribute access
        manager_props = positionerInfo.managerProperties or {}

        # Extract mock flag, library path, and axes safely
        self._mock = manager_props.get('mock', False)
        self._libraryPath = manager_props.get('libraryPath', 'MicroDrive/MCL_MICRODrive.dll')

        startPosition = float(manager_props.get('startPosition', 0))

        if not self._mock:
            self.MicroDrive = MicroDrive()
            self.MicroDrive.moveCoordinate(startPosition)

        initialPosition = {"X": 0, "Y": 0, "Z": startPosition}
        self._position = initialPosition
        super().__init__(positionerInfo, name, initialPosition=startPosition)

    def moveCoordinate(self, x):
        return self.MicroDrive.moveCoordinate(x)

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
        return round(self.MicroDrive.getPosition(), 4)

    def finalize(self):
        self.MicroDrive.closeConnection()