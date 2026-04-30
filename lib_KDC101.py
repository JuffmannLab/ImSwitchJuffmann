"""
kdc101_example.py
=================

This example demonstrates basic control of the Thorlabs KDC101 DC motor controller using python.

It achieves control of the device via the Kinesis C API, interfaced with via ctypes. The example connects, homes, moves
and disconnects the device.

"""
import time
import os
import sys
from ctypes import *

if sys.version_info < (3, 8):
        os.chdir(r"C:\Program Files\Thorlabs\Kinesis")
else:
        os.add_dll_directory(r"C:\\Program Files\\Thorlabs\\Kinesis")

lib_dll: CDLL = cdll.LoadLibrary("Thorlabs.MotionControl.KCube.DCServo.dll")
serial_num = c_char_p(b"27503766")




def Open():
    if lib_dll.TLI_BuildDeviceList() == 0:
        lib_dll.CC_Open(serial_num)
        lib_dll.CC_StartPolling(serial_num, c_int(200))

        #lib_dll.CC_Home(serial_num)
        # Set up the device to convert real units to device units
        STEPS_PER_REV = c_double(1919.64186)  # for the PRM1-Z8
        gbox_ratio = c_double(1.0)  # gearbox ratio
        pitch = c_double(1.0)
        lib_dll.CC_SetMotorParamsExt(serial_num, STEPS_PER_REV, gbox_ratio, pitch) # apply the values to the device


def Close():
     lib_dll.CC_Close(serial_num)


def Home():
    """
    Move the Thorlabs KDC101 DC motor controller to the zero position.

    Parameters:
    - serial_num (c_char_p): The serial number of the device.
    - lib (CDLL): The Thorlabs library object.

    Returns:
    None
    """

    print("KDC101 going to zero...")

    # set new position (0) in device units
    new_pos_real = c_double(0.0)  # in real units
    new_pos_dev = c_int()
    lib_dll.CC_GetDeviceUnitFromRealValue(serial_num,
                                        new_pos_real,
                                        byref(new_pos_dev),
                                        0)
    #print(f'New position: {new_pos_real.value}, in Device Units: {new_pos_dev.value}')

    # Move to new position as an absolute move
    lib_dll.CC_SetMoveAbsolutePosition(serial_num, new_pos_dev)
    time.sleep(0.25)
    lib_dll.CC_MoveAbsolute(serial_num)

    time.sleep(5)



def Move(pos): # pos in mm
    pos=pos*18 #Convert from mm to real units
    new_pos_real = c_double(pos)  # in real units
    new_pos_dev = c_int()
    lib_dll.CC_GetDeviceUnitFromRealValue(serial_num, new_pos_real,byref(new_pos_dev),0)
    # move the motor
    lib_dll.CC_SetMoveAbsolutePosition(serial_num, new_pos_dev)
    lib_dll.CC_MoveAbsolute(serial_num)


def PrintPos():
    # Get the device's current position in dev[ice] units
    lib_dll.CC_RequestPosition(serial_num)
    time.sleep(0.2)
    print("Position device units: ", lib_dll.CC_GetPosition(serial_num))


def GetPos():
     # Get the device's current position in dev[ice] units
     lib_dll.CC_RequestPosition(serial_num)
     time.sleep(0.2)
     pos = lib_dll.CC_GetPosition(serial_num)

     return pos


def Step_Scanning(stepsize, stepnum, steptime, serial_num, home):
    """
    Perform step scanning with the Thorlabs KDC101 DC motor controller.

    Parameters:
    - stepsize (float): The size of each step in mm
    - stepnum (int): The number of steps to perform.
    - steptime (float): The time to wait between steps in seconds.
    - serial_num (c_char_p): The serial number of the device.
    - lib (CDLL): The Thorlabs library object.
    - home (bool): Go to zero or not.

    Returns:
    None
    """
    print("Start scanning: ")

    # convert stepsize from mm to real units (1 mm = 18 real units)
    stepsize = stepsize*18

    pos = 0  # Initialize position before the loop

    for i in range(stepnum+1):
        print(" Position [mm]: ", pos/18.0, end = "  ")
        # convert the position to device units
        new_pos_real = c_double(pos)  # in real units
        new_pos_dev = c_int()
        lib_dll.CC_GetDeviceUnitFromRealValue(serial_num,
                                            new_pos_real,
                                            byref(new_pos_dev),
                                            0)
        # move the motor
        lib_dll.CC_SetMoveAbsolutePosition(serial_num, new_pos_dev)
        lib_dll.CC_MoveAbsolute(serial_num)
        time.sleep(steptime)

        # Get the device's current position in dev[ice] units
        lib_dll.CC_RequestPosition(serial_num)
        time.sleep(0.2)
        print("In device units: ", lib_dll.CC_GetPosition(serial_num))

        pos += stepsize # update position

    if home==True:
        # set position to 0 again
        Home(serial_num=serial_num, lib=lib_dll)

    return

if __name__ == "__main__":
    main()