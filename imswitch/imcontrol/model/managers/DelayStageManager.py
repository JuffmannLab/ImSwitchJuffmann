from __future__ import annotations

import imslib as ims
from imswitch.imcommon.model import initLogger
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import atexit
import os
import sys
import time
from ctypes import cdll, CDLL, c_char_p, c_double, c_int, byref

class DelayStageManager:
    """
    Object-oriented wrapper around Thorlabs KDC101 control via Kinesis C API (ctypes).
    Mirrors the functionality of the provided script.

    Key methods:
      - open()
      - close()
      - home()
      - move_mm(pos_mm)           # absolute move in mm
      - print_pos()               # print position in device units
      - get_pos() -> int          # return position in device units
      - step_scanning(stepsize_mm, stepnum, steptime_s, home=True)

    Notes:
      - The example follows your script's conversions: 1 mm = 18 "real units".
      - For PRM1-Z8, steps_per_rev defaults to 1919.64186, gearbox_ratio=1.0, pitch=1.0.
      - On Python >= 3.8, we add the Kinesis directory via os.add_dll_directory.
    """

    def __init__(
        self,
        serial_number: str,
        kinesis_dir: str = r"C:\Program Files\Thorlabs\Kinesis",
        steps_per_rev: float = 1919.64186,  # PRM1-Z8
        gearbox_ratio: float = 1.0,
        pitch: float = 1.0,
        poll_interval_ms: int = 200,
        real_units_per_mm: float = 18.0,    # matches your script: 1 mm = 18 "real units"
    ):
        self.serial_str = serial_number
        self.serial = c_char_p(serial_number.encode("ascii"))
        self.kinesis_dir = kinesis_dir
        self.steps_per_rev = c_double(steps_per_rev)
        self.gearbox_ratio = c_double(gearbox_ratio)
        self.pitch = c_double(pitch)
        self.poll_interval = c_int(int(poll_interval_ms))
        self.real_units_per_mm = float(real_units_per_mm)

        self.lib: CDLL | None = None
        self._is_open = False

    # ------------------- Internal helpers -------------------

    def _load_library(self):
        # Make sure the DLL directory is available depending on Python version
        if sys.version_info < (3, 8):
            # Workdir approach (legacy)
            os.chdir(self.kinesis_dir)
        else:
            # Preferred approach on Python 3.8+
            os.add_dll_directory(self.kinesis_dir)

        # Load the specific KCube DC Servo library
        self.lib = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")

    def _to_device_units_from_real(self, real_value: float) -> int:
        """
        Convert a "real units" value to device units using CC_GetDeviceUnitFromRealValue.
        Returns an int device units value.
        """
        assert self.lib is not None, "Library not loaded"
        new_pos_real = c_double(real_value)
        new_pos_dev = c_int()
        self.lib.CC_GetDeviceUnitFromRealValue(self.serial, new_pos_real, byref(new_pos_dev), 0)
        return int(new_pos_dev.value)

    # ------------------- Public API -------------------

    def open(self):
        """
        Build device list, open the device, start polling, and apply motor parameters.
        """
        if self._is_open:
            return

        self._load_library()
        assert self.lib is not None

        # Build device list and open
        if self.lib.TLI_BuildDeviceList() != 0:
            raise RuntimeError("TLI_BuildDeviceList failed")

        # Open and start polling
        err = self.lib.CC_Open(self.serial)
        if err != 0:
            raise RuntimeError(f"CC_Open failed with code {err}")

        # Start polling
        self.lib.CC_StartPolling(self.serial, self.poll_interval)

        # Apply motor params (needed for real<->device unit conversion)
        self.lib.CC_SetMotorParamsExt(self.serial, self.steps_per_rev, self.gearbox_ratio, self.pitch)

        self._is_open = True

    def close(self):
        """
        Close the device.
        """
        if not self._is_open:
            return
        assert self.lib is not None

        # Optionally stop polling if available in your DLL version:
        # self.lib.CC_StopPolling(self.serial)

        self.lib.CC_Close(self.serial)
        self._is_open = False

    def home(self, settle_time_s: float = 5.0):
        """
        Move to zero (absolute position 0 in "real units").
        Mirrors the script logic (0 -> device units, set absolute, move).
        """
        assert self._is_open and self.lib is not None, "Call open() first"

        # Convert 0.0 real to device units
        dev_units = self._to_device_units_from_real(0.0)

        # Set absolute position and move
        self.lib.CC_SetMoveAbsolutePosition(self.serial, c_int(dev_units))
        time.sleep(0.25)
        self.lib.CC_MoveAbsolute(self.serial)

        # Wait a bit to settle (matches your script)
        time.sleep(settle_time_s)

    def move_mm(self, pos_mm: float):
        """
        Absolute move to pos_mm in millimeters.
        Uses the same conversion as your script: real = pos_mm * 18.
        """
        assert self._is_open and self.lib is not None, "Call open() first"

        real_value = pos_mm * self.real_units_per_mm
        dev_units = self._to_device_units_from_real(real_value)
        self.lib.CC_SetMoveAbsolutePosition(self.serial, c_int(dev_units))
        self.lib.CC_MoveAbsolute(self.serial)

    def request_position(self):
        """
        Request the device to update its position reading.
        """
        assert self._is_open and self.lib is not None, "Call open() first"
        self.lib.CC_RequestPosition(self.serial)

    def get_pos(self) -> int:
        """
        Return the current position in device units.
        Mirrors your script (requests, sleeps, then reads).
        """
        assert self._is_open and self.lib is not None, "Call open() first"
        self.request_position()
        time.sleep(0.2)  # allow controller to update reply buffer
        return int(self.lib.CC_GetPosition(self.serial))

    def print_pos(self):
        """
        Print current position in device units (for debugging/compat).
        """
        pos = self.get_pos()
        print("Position device units:", pos)

    def step_scanning(self, stepsize_mm: float, stepnum: int, steptime_s: float, home: bool = True):
        """
        Perform step scanning, moving in absolute steps (starting from 0 real units) and printing positions.
        Mirrors your script’s behavior:
          - pos starts at 0 real units
          - stepnum is inclusive in the loop (range(stepnum+1))
          - prints mm and device units each step
          - optional homing at the end

        stepsize_mm: step size in millimeters
        stepnum: number of steps (inclusive loop)
        steptime_s: pause between steps in seconds
        home: if True, go back to 0 at the end
        """
        assert self._is_open and self.lib is not None, "Call open() first"

        print("Start scanning:")

        # Convert step size to "real units"
        step_real = stepsize_mm * self.real_units_per_mm
        pos_real = 0.0

        for i in range(stepnum + 1):
            print(f" Position [mm]: {pos_real / self.real_units_per_mm:.6f}", end="  ")

            # Convert current pos_real to device units and move
            dev_units = self._to_device_units_from_real(pos_real)
            self.lib.CC_SetMoveAbsolutePosition(self.serial, c_int(dev_units))
            self.lib.CC_MoveAbsolute(self.serial)

            time.sleep(steptime_s)

            # Read and print device units
            self.request_position()
            time.sleep(0.2)
            print("In device units:", int(self.lib.CC_GetPosition(self.serial)))

            # Increment
            pos_real += step_real

        if home:
            self.home()

