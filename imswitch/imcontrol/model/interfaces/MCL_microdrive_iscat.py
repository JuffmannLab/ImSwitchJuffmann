"""
Class to control the Mad City Labs MicroDrive with 1 axis (26.1mm range) and encoders (50 nm resolution).
Movements and velocities are in mm and mm/s, respectively.

Functions include:
    - getPosition()
        Reads the encoders.
        return (x,y,z) encoder position
    - moveMicrostep()

    - moveCoordinate(x, velocity)
        move to a given x coordinate within 0 and 26.1mm


    - isMoving()
        Checks if a motor is moving.
        return motor response
    - stopMoving()
        Stops the motors from moving.
        return None
    - Home
        Moves to the (0,0,0) position of the encoders.
        return None
    - EncodersReset
        Sets the current position as the new center position (0,0,0)
        return None
    - getStatus()
        Checks if an axis is out of bounds and returns a list of axes which axes
        are out of bounds:
        return ListOfAxesOutOfBounds
    - getInfo()
        Returns information about the MicroStage:
            encoderResolution = 0.05
            stepSize =  9.525e-05
            maxVelocity = 4
            maxVelocityTwoAxis = 3.75
            maxVelocityThreeAxis = 3
            minVelocity = 0.01905
    - closeConnection()
        Releases the handle.
        return None

 "Private" functions:
    - wait
        Waits for the previous function to finish.
        return None
     - _move(x,y,z,velocity = 3)
        Moves to x, y, z position according to encoders with velocity. Waits
        until the movement is complete.
        return errorCode of movement
     - _moveRelative(self, dx, dy, dz, velocity = 3)
        Moves motors by dx, dy, dz relative to the current position. Waits
        until the movement is complete.
        return errorCode of movement
    - _moveRelativeAxis(self, axis, distance, velocity = 3)
        Moves axis by distance relative to the current position. Waits
        until the movement is complete.
        return errorCode of movement

Additional remarks:
    - Wait should be called after the movement to guarantee that the motors are
    not moving anymore. Trying to read the encoders or move the motors, while
    they are still movingn, might affect the internal timing pulses.
    However, wait should not  be called multiple times, as it is slowed if it
    is called more then once.


author: Cisse De Locht
"""

import ctypes
import numpy as np


class MicroDrive(object):
    def __init__(self, mcl_lib="C:/Program Files/Mad City Labs/MicroDrive/MicroDrive"):
        """
        Here, we initialize the object
        - Loading the DLL
        - Connecting to the stage.
        """

        self.errorDictionary = {0: 'MCL_SUCCESS',
                                -1: 'MCL_GENERAL_ERROR',
                                -2: 'MCL_DEV_ERROR',
                                -3: 'MCL_DEV_NOT_ATTACHED',
                                -4: 'MCL_USAGE_ERROR',
                                -5: 'MCL_DEV_NOT_READY',
                                -6: 'MCL_ARGUMENT_ERROR',
                                -7: 'MCL_INVALID_AXIS',
                                -8: 'MCL_INVALID_HANDLE'}

        # Dictionary to know the axis limit returns. Dicitionary saves [axis, forward (1) or backward (-1), description]
        self.motorLimits = [[1, -1, 'Axis 1 reverse limit'],  # 126 <-> '1111110' <-> position 0
                            [1, 1, 'Axis 1 forward limit'],  # 125 <-> '1111101' <-> position 1
                            [2, -1, 'Axis 2 reverse limit'],  # 123 <-> '1111011' <-> position 2
                            [2, 1, 'Axis 2 forward limit'],  # 119 <-> '1110111' <-> position 3
                            [3, -1, 'Axis 3 reverse limit'],  # 111 <-> '1101111' <-> position 4
                            [3, 1, 'Axis 3 forward limit']]  # 095 <-> '1011111' <-> position 5

        # Load the DLL
        self.mcl = ctypes.cdll.LoadLibrary(mcl_lib)
        # Release existing handles
        self.mcl.MCL_ReleaseAllHandles()
        # Connect to the instrument and creat a handle
        self.handle = self.mcl.MCL_InitHandle()  # Handle number is assigned, which is a positive integer
        # Check if connection was successful
        # if self.handle > 0:
        #     print('Connected to SN: ' + str(self.mcl.MCL_GetSerialNumber(self.handle)) + '\nWith handle: ' + str(
        #         self.handle))
        # else:
        #     print('Connection failed. Maybe the device is turned off?')

        # Save Product information
        # Create pointers for query
        encoderResolution_temp = ctypes.pointer(ctypes.c_double())
        stepSize_temp = ctypes.pointer(ctypes.c_double())
        maxVelocity_temp = ctypes.pointer(ctypes.c_double())
        maxVelocityTwoAxis_temp = ctypes.pointer(ctypes.c_double())
        maxVelocityThreeAxis_temp = ctypes.pointer(ctypes.c_double())
        minVelocity_temp = ctypes.pointer(ctypes.c_double())
        # Make the query
        self.mcl.MCL_MDInformation(encoderResolution_temp, stepSize_temp, maxVelocity_temp, maxVelocityTwoAxis_temp,
                                   maxVelocityThreeAxis_temp, minVelocity_temp, self.handle)
        # Save the information
        self.encoderResolution = encoderResolution_temp.contents.value
        self.stepSize = stepSize_temp.contents.value
        self.maxVelocity = maxVelocity_temp.contents.value
        self.maxVelocityTwoAxis = maxVelocityTwoAxis_temp.contents.value
        self.maxVelocityThreeAxis = maxVelocityThreeAxis_temp.contents.value
        self.minVelocity = minVelocity_temp.contents.value

        self.serialNumber = self.mcl.MCL_GetSerialNumber(self.handle)
        # Delete pointers just to be save
        del encoderResolution_temp
        del stepSize_temp
        del maxVelocity_temp
        del maxVelocityTwoAxis_temp
        del maxVelocityThreeAxis_temp
        del minVelocity_temp

        # Set standard minimum and maximum velocity
        self.velocityMin = self.minVelocity  # mm/s (normally 0.01905 mm/s)
        self.velocityMax = self.maxVelocity  # mm/s (normally 3 mm/s)
        self.totalScanRange = 26.1  # mm

    def __enter__(self):
        return self

    def getPosition(self):
        """
        This function takes approximately 10ms.
        """

        e1 = ctypes.pointer(ctypes.c_double())
        e2 = ctypes.pointer(ctypes.c_double())
        e3 = ctypes.pointer(ctypes.c_double())
        e4 = ctypes.pointer(ctypes.c_double())
        errorNumber = self.mcl.MCL_MDReadEncoders(e1, e2, e3, e4, self.handle)

        position_temp = e1.contents.value
        del e1
        del e2
        del e3
        del e4
        return errorNumber, position_temp

    def _getStatus(self): #Internal function to get the error number
        status_temp = ctypes.pointer(ctypes.c_ushort())
        self.mcl.MCL_MDStatus(status_temp,self.handle)
        result_temp = status_temp.contents.value
        del status_temp
        return result_temp

    def getStatus(self):
        """
        Returns a list of motors that are out of bounds (reverse of forward limit)
        [axis, forward (1) / reverse (-1), description]
        [1,-1,'Axis 1 reverse limit']
        [1, 1,'Axis 1 forward limit']
        [2,-1,'Axis 2 reverse limit']
        [2, 1,'Axis 2 forward limit']
        [3,-1,'Axis 3 reverse limit']
        [3, 1,'Axis 3 forward limit']
        """
        status = self._getStatus()

        errorsLimit = []
        for i, b in enumerate(bin(status)[:1:-1]):
            if i > 1:  # there is only 1 axis in the iscat setup.
                break
            if b == '0':
                errorsLimit.append(self.motorLimits[i])
        if errorsLimit == []:  # If no limit is detected, we add the All ok line
            errorsLimit.append([0, 0, 'All ok'])
        return errorsLimit

    def wait(self):
        """
        This function takes approximately 10ms if the motors are not moving.
        """
        errorNumber = self.mcl.MCL_MicroDriveWait(self.handle)
        if errorNumber != 0:
            print('Error while waiting: ' + self.errorDictionary[errorNumber])

    # Start: Internal move functions that have no error handling and should be used with caution and only if one is familiar with the motors
    # A negative distance moves towards the reverse limit, 0 will not move the axis.
    def _move(self, distance, velocity = 3):
        axis = 1
        rounding = 0 #round the distance to the nearest microstep
        errorCode = self.mcl.MCL_MDMoveR(ctypes.c_uint(axis), ctypes.c_double(velocity), ctypes.c_double(-distance), ctypes.c_uint(rounding),
                                        self.handle)
        self.wait()
        return errorCode

    def _microstep(self, direction):
        axis = 1
        errorCode = self.mcl.MCL_MDSingleStep(ctypes.c_uint(axis), ctypes.c_uint(-direction), self.handle)
        return errorCode

    def moveCoordinate(self, x, velocity=3):
        """
        Moves the stage to the specified position with velocity anc
        """

        # Check the given velocity
        if velocity > self.velocityMax:
            #print('Given velocity is too high. Velocity is set to maximum value.')
            velocity = self.velocityMax
        elif velocity < self.velocityMin:
            #print('Given velocity is too low. Velocity is set to minimum value.')
            velocity = self.velocityMin
        # Check if the movement would go out of bounds
        if x > 25 or x < 0:
            #print("Given position is out of bounds. Please enter a value between 0 and 25.")
            return self.getPosition()
        _, position = self.getPosition()

        # Move the stage
        errorNumber = self._move(x-position, velocity)
        # Check for error
        # if errorNumber != 0:
        #     print('Error while moving axis: ' + self.errorDictionary[errorNumber])
        #
        # # Check if motors moved out of bounds
        # status = self.getStatus()
        # if status[0] != [0, 0, 'All ok']:
        #     print('Motor moved out of bounds: ' + str([temp[2] for temp in status]))

        return errorNumber, self.getPosition()[1]

    def moveMicrostepUp(self):
        errorNumber = self._microstep(1)
        # if errorNumber != 0:
        #     print('Error while moving axis: ' + self.errorDictionary[errorNumber])
        #
        # # Check if motors moved out of bounds
        # status = self.getStatus()
        # if status[0] != [0, 0, 'All ok']:
        #     print('Motor moved out of bounds: ' + str([temp[2] for temp in status]))
        return errorNumber, self.getPosition()[1]

    def moveMicrostepDown(self):
        errorNumber =self._microstep(-1)
        # if errorNumber != 0:
        #     print('Error while moving axis: ' + self.errorDictionary[errorNumber])
        #
        # # Check if motors moved out of bounds
        # status = self.getStatus()
        # if status[0] != [0, 0, 'All ok']:
        #     print('Motor moved out of bounds: ' + str([temp[2] for temp in status]))
        return errorNumber, self.getPosition()[1]

    def isMoving(self):
        """
        Checks if motors are moving.
        This function takes approximately 20ms.
        returns 0 if motors are not moving, 1 if they are.
        """
        isMoving = ctypes.pointer(ctypes.c_int())
        self.mcl.MCL_MicroDriveMoveStatus(isMoving, self.handle)
        result_temp = isMoving.contents.value
        del isMoving
        return result_temp

    def stopMoving(self):
        """
        Stops motors from moving.
        """
        status = ctypes.pointer(ctypes.c_ushort())
        errorNumber = self.mcl.MCL_MDStop(status, self.handle)
        del status
        if errorNumber != 0:
            print('Error while stopping device: ' + self.errorDictionary[errorNumber])

    def home(self):
        """
        returns to 0 position
        """
        errorNumber, position = self.moveCoordinate(0)
        return errorNumber, position

    def EncodersReset(self):
        """
        Resets the encoders and sets the current position as the new (0,0,0) position.
        USE WITH CAUTION AS ISCAT SETUP DEPENDS ON 0 POSITION BEING AT THE FORWARD LIMIT
        """
        status_temp = ctypes.pointer(ctypes.c_ushort())
        self.mcl.MCL_MDResetEncoders(status_temp,self.handle)
        self.wait()
        del status_temp

    def getInfo(self):
        """
        Returns info about the motors:
            encoderResolution = 0.05
            stepSize =  9.??e-5??
            maxVelocity = 4
            maxVelocityTwoAxis = ??
            maxVelocityThreeAxis = 3
            minVelocity = 0.019??
        """
        if self.handle > 0:
            #Device attached
            print('Device attached: ' + str(self.mcl.MCL_DeviceAttached(ctypes.c_uint(500), self.handle)))
            #Serial number
            print('SN: ' + str(self.mcl.MCL_GetSerialNumber(self.handle)))
            #Product ID:
            PID = ctypes.pointer(ctypes.c_ushort())
            self.mcl.MCL_GetProductID(PID, self.handle)
            print('PID: ' + str(PID.contents.value))
            #Encoder, StepSize and Velocities
            encoderResolution = ctypes.pointer(ctypes.c_double())
            stepSize = ctypes.pointer(ctypes.c_double())
            maxVelocity = ctypes.pointer(ctypes.c_double())
            maxVelocityTwoAxis = ctypes.pointer(ctypes.c_double())
            maxVelocityThreeAxis = ctypes.pointer(ctypes.c_double())
            minVelocity = ctypes.pointer(ctypes.c_double())
            self.mcl.MCL_MDInformation(encoderResolution, stepSize, maxVelocity, maxVelocityTwoAxis, maxVelocityThreeAxis, minVelocity, self.handle)
            print('encoderResolution: ' + str(encoderResolution.contents.value))
            print('stepSize: ' + str(stepSize.contents.value))
            print('maxVelocity: ' + str(maxVelocity.contents.value))
            print('maxVelocityTwoAxis: ' + str(maxVelocityTwoAxis.contents.value))
            print('maxVelocityThreeAxis: ' + str(maxVelocityThreeAxis.contents.value))
            print('minVelocity: ' + str(minVelocity.contents.value))
        else:
            print('Invalid handle. No device is connncted.')

    def closeConnection(self):
        """
        Closes the connection by releasing the handle.
        """
    #    self.mcl.MCL_ReleaseAllHandles()
        self.stopMoving()
        self.mcl.MCL_ReleaseHandle(self.handle)
        print('Handle released.')

    def __exit__(self, exception_type, exception_value, traceback):
        if not(self.released == True):
            if exception_value == None:
                print('Handle released')
            else:
                print('An unexpected error occured. Releasing handle now.')
                self.closeConnection()
    def __del__(self):
        self.mcl.MCL_ReleaseHandle(self.handle)
        print('Deconstructor was called.')