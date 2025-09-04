import ctypes
from ctypes import c_int, c_double, byref
from .PositionerManager import PositionerManager


class MCLPositionerManager(PositionerManager):
    def __init__(self, positionerInfo, name, **kwargs):
        # Use managerProperties instead of direct attribute access
        manager_props = positionerInfo.managerProperties or {}

        # Extract mock flag, library path, and axes safely
        self._mock = manager_props.get('mock', False)
        self._libraryPath = manager_props.get('libraryPath', 'MicroDrive/MCL_MICRODrive.dll')
        self.axes = manager_props.get('axes', [])

        # Initialize superclass
        super().__init__(positionerInfo, name, initialPosition={axis: 0 for axis in self.axes})

        self._position = {axis: 0.0 for axis in self.axes}

        if not self._mock:
            self.dll = ctypes.windll.LoadLibrary(self._libraryPath)
            self.handle = self.dll.MDOpenBySerialNumber("MCL-µD2555".encode('utf-8'))  # Replace with actual S/N
            self.channel = 0

    def move(self, dist, axis):
        target_pos = self._position[axis] + dist
        self.setPosition(target_pos, axis)

    def setPosition(self, position, axis):
        self._position[axis] = position
        if not self._mock:
            self.dll.MDMoveAbsolute(self.handle, c_int(self.channel), c_double(position))

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

    def shutdown(self):
        if not self._mock:
            self.dll.MDClose(self.handle)