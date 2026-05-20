from __future__ import annotations

import imslib as ims
from imswitch.imcommon.framework import Signal, SignalInterface, Thread
import atexit

import os
import sys
import time
from ctypes import cdll, CDLL, c_char_p, c_double, c_int, byref
from typing import Optional

from imswitch.imcommon.model import initLogger


class DelayStageManager:
    """
    Thorlabs KDC101 delay stage manager via Kinesis C API (ctypes).

    Reads configuration from:
        setupInfo['Delaystage'].managerProperties

    Exposes the same functions as the reference script:
      - Open()
      - Close()
      - Home()
      - Move(pos_mm)              # pos in mm (absolute)
      - PrintPos()                # prints position in device units
      - GetPos() -> int           # returns position in device units
      - Step_Scanning(stepsize_mm, stepnum, steptime_s, serial_num=None, home=False)

    Notes:
      - 1 mm = 18 "real units" (same as your script; adjustable via managerProperties)
      - PRM1-Z8 defaults: stepsPerRev=1919.64186, gearboxRatio=1.0, pitch=1.0
      - The DLL path is configured via managerProperties.kinesisDir
    """

    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        self._deviceProperties = self._setupInfo['Delaystage'].managerProperties

        # Parse managerProperties (support dict-like or attribute-like access)
        props = self._deviceProperties
        getp = props.get if isinstance(props, dict) else (lambda k, d=None: getattr(props, k, d))

        # Required hardware info
        serial_str = (
            getp("serial")
            or getp("Serial")
            or getp("SerialNumber")
        )
        if not serial_str:
            raise ValueError("Delaystage.managerProperties must include 'serial' (string).")
        self._serial_str = str(serial_str)
        self._serial = c_char_p(self._serial_str.encode("ascii"))

        # Optional/advanced configuration
        self._kinesis_dir = getp("kinesisDir", r"C:\Program Files\Thorlabs\Kinesis")
        self._dll_name = getp("dllName", "Thorlabs.MotionControl.KCube.DCServo.dll")
        self._poll_interval_ms = int(getp("pollIntervalMs", 200))

        # Unit conversion (PRM1-Z8 defaults)
        self._steps_per_rev = c_double(float(getp("stepsPerRev", 1919.64186)))
        self._gearbox_ratio = c_double(float(getp("gearboxRatio", 1.0)))
        self._pitch = c_double(float(getp("pitch", 1.0)))

        # Real <-> mm conversion (same as your script by default)
        self._real_units_per_mm = float(getp("realUnitsPerMm", 18.0))

        # Homing settle time
        self._home_settle_s = float(getp("homeSettleTimeS", 5.0))

        # Internal state
        self._lib: Optional[CDLL] = None
        self._is_open = False

    # ------------------------------------------------------------------
    # API identical to the reference script
    # ------------------------------------------------------------------

    def Open(self):
        """
        Build device list, open device, start polling, and apply motor parameters.
        """
        if self._is_open:
            return

        self.__logger.info(f"Opening KDC101 (SN={self._serial_str}) using Kinesis at '{self._kinesis_dir}'")
        self._load_library()

        # Build USB device list
        rc = self._lib.TLI_BuildDeviceList()
        if rc != 0:
            raise RuntimeError(f"TLI_BuildDeviceList failed (rc={rc})")

        # Open the device and start polling
        rc = self._lib.CC_Open(self._serial)
        if rc != 0:
            raise RuntimeError(f"CC_Open failed (rc={rc})")

        self._lib.CC_StartPolling(self._serial, c_int(self._poll_interval_ms))

        # Set motor parameters for proper unit conversions
        self._lib.CC_SetMotorParamsExt(self._serial, self._steps_per_rev, self._gearbox_ratio, self._pitch)

        self._is_open = True
        self.__logger.info("Delay stage opened and polling started.")

    def Close(self):
        """
        Close the device (optionally stop polling if desired).
        """
        if not self._is_open:
            return
        try:
            # Optional (if available in your DLL version):
            # self._lib.CC_StopPolling(self._serial)
            self._lib.CC_Close(self._serial)
            self.__logger.info("Delay stage closed.")
        finally:
            self._is_open = False

    def Home(self):
        """
        Move the stage to zero (absolute 0.0 real-units), like in your script.
        """
        self._ensure_open()
        print("KDC101 going to zero...")  # keep same console behavior as your script

        # Convert 0.0 real-units to device units
        new_pos_real = c_double(0.0)
        new_pos_dev = c_int()
        self._lib.CC_GetDeviceUnitFromRealValue(self._serial, new_pos_real, byref(new_pos_dev), 0)

        # Issue absolute move
        self._lib.CC_SetMoveAbsolutePosition(self._serial, new_pos_dev)
        time.sleep(0.25)
        self._lib.CC_MoveAbsolute(self._serial)

        time.sleep(self._home_settle_s)

    def Move(self, pos_mm: float):
        """
        Absolute move to pos_mm (millimeters), using the same 1 mm -> 18 real units conversion.
        """
        self._ensure_open()
        real_val = c_double(float(pos_mm) * self._real_units_per_mm)
        new_pos_dev = c_int()
        self._lib.CC_GetDeviceUnitFromRealValue(self._serial, real_val, byref(new_pos_dev), 0)
        self._lib.CC_SetMoveAbsolutePosition(self._serial, new_pos_dev)
        self._lib.CC_MoveAbsolute(self._serial)

    def PrintPos(self):
        """
        Print the current position in device units, same as your script.
        """
        self._ensure_open()
        self._lib.CC_RequestPosition(self._serial)
        time.sleep(0.2)
        pos = self._lib.CC_GetPosition(self._serial)
        print("Position device units: ", pos)

    def GetPos(self) -> int:
        """
        Return the current position in device units, same as your script.
        """
        self._ensure_open()
        self._lib.CC_RequestPosition(self._serial)
        time.sleep(0.2)
        pos = int(self._lib.CC_GetPosition(self._serial))
        return pos

    def Step_Scanning(self, stepsize: float, stepnum: int, steptime: float, serial_num=None, home: bool = False):
        """
        Perform step scanning, mirroring the original function's signature and behavior.

        stepsize: step size in mm
        stepnum: number of steps
        steptime: wait between steps (seconds)
        serial_num: ignored (kept for API compatibility with your script)
        home: if True, home at the end
        """
        self._ensure_open()
        print("Start scanning: ")

        # Convert step size (mm) to real units
        step_real = stepsize * self._real_units_per_mm
        pos_real = 0.0  # start from 0 real-units

        for i in range(stepnum + 1):
            print(" Position [mm]: ", pos_real / self._real_units_per_mm, end="  ")

            # Convert real-units position to device units
            new_pos_real = c_double(pos_real)
            new_pos_dev = c_int()
            self._lib.CC_GetDeviceUnitFromRealValue(self._serial, new_pos_real, byref(new_pos_dev), 0)

            # Move to absolute position
            self._lib.CC_SetMoveAbsolutePosition(self._serial, new_pos_dev)
            self._lib.CC_MoveAbsolute(self._serial)
            time.sleep(steptime)

            # Request and print device-units position
            self._lib.CC_RequestPosition(self._serial)
            time.sleep(0.2)
            print("In device units: ", self._lib.CC_GetPosition(self._serial))

            # Advance to next target
            pos_real += step_real

        if home:
            self.Home()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_open(self):
        if not self._is_open:
            raise RuntimeError("DelayStageManager: device not opened. Call Open() first.")

    def _load_library(self):
        # Add DLL directory (Python 3.8+) or temporarily cd into it (older Pythons)
        if sys.version_info < (3, 8):
            os.chdir(self._kinesis_dir)
        else:
            os.add_dll_directory(self._kinesis_dir)

        # Load KCube DC Servo DLL
        self._lib = cdll.LoadLibrary(self._dll_name)