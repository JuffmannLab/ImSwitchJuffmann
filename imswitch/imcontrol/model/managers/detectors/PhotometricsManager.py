import numpy as np

from imswitch.imcommon.model import initLogger
from .DetectorManager import (
    DetectorManager, DetectorNumberParameter, DetectorListParameter
)
from pyvcam import pvc
from pyvcam import constants as consts
from pyvcam.camera import Camera
_pyvcam_initialized = False

class PhotometricsManager(DetectorManager):
    """ DetectorManager that deals with frame extraction for a Photometrics camera.

    Manager properties:

    - ``cameraListIndex`` -- the camera's index in the Photometrics camera list
      (list indexing starts at 0)
    - ``cameraProperties`` -- the camera properties as a dictionary
    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)

        self._camera = self._getCameraObj(detectorInfo.managerProperties['cameraListIndex'])
        self._binning = 1

        fullShape = self._camera.sensor_size

        model = self._camera.name

        # try:
        #     self.scanLineTime = self._camera.scan_line_time                         #Warning: Camera specific property!
        # except AttributeError:
        #     self.__logger.warning(f"Camera {model} has no scan line time attribute!")

        self.__acquisition = False
        # Prepare parameters
        parameters = {}
        for key, param in detectorInfo.managerProperties['cameraProperties'].items():
            if param["type"] == "number":
                current = {key: DetectorNumberParameter(group=param["group"], value=param["value"],
                                                        valueUnits=param["valueUnits"], editable=param["editable"])}
            elif param["type"] == "list":
                current = {key: DetectorListParameter(group=param["group"], value=param["value"],
                                                      options=param["options"], editable=param["editable"])}
            parameters.update(current)

        parameters.update({'Set exposure time': DetectorNumberParameter(group='Timings', value=10,
                                                                        valueUnits='ms', editable=True)})
        parameters.update({'Real exposure time': DetectorNumberParameter(group='Timings', value=0,
                                                                         valueUnits='ms', editable=False)})
        parameters.update({'Trigger source': DetectorListParameter(group='Acquisition mode',
                                                     value='Internal trigger',
                                                     options=['Internal trigger',
                                                         'External start-trigger',
                                                              'External frame-trigger'], editable=True)})
        # parameters.update({'Readout port': DetectorListParameter(group='ports',
        #                                           value='Sensitivity',
        #                                           options=['Sensitivity',
        #                                                    'Speed',
        #                                                    'Dynamic range'], editable=True)})

        # 'Trigger source': DetectorListParameter(group='Acquisition mode',
        #                                             value='Internal trigger',
        #                                             options=['Internal trigger',
        #                                                      'External "start-trigger"',
        #                                                      'External "frame-trigger"'],
        #
        #     'Camera pixel size': DetectorNumberParameter(group='Miscellaneous', value=0.1,
        #                                                  valueUnits='µm', editable=True)
        # }

        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1, 2],
                         model=model, parameters=parameters, croppable=True)
        self._updatePropertiesFromCamera()
        super().setParameter('Set exposure time', self.parameters['Real exposure time'].value)

    @property
    def pixelSizeUm(self):
        umxpx = self.parameters['Camera pixel size'].value
        return [1, umxpx, umxpx]

    def getLatestFrame(self, is_save=True):
        try:
            status = self._camera.check_frame_status()
            if status == "READOUT_NOT_ACTIVE":
                return self.image
            else:
                return np.array(self._camera.poll_frame()[0]['pixel_data'])
        except RuntimeError:
            return self.image

    def getChunk(self):
        frames = []
        status = self._camera.check_frame_status()
        try:
            if not status == "READOUT_NOT_ACTIVE":
                while True:
                    im = np.array(self._camera.poll_frame()[0]['pixel_data'])
                    frames.append(im)
        except RuntimeError:
            pass
        return frames

    def flushBuffers(self):
        pass

    def crop(self, hpos, vpos, hsize, vsize):
        """Method to crop the frame read out by the camera. """
        roi = (hpos, hpos + hsize, vpos, vpos + vsize)

        def cropAction():
            self._camera.roi = roi

        self._performSafeCameraAction(cropAction)
        # This should be the only place where self.frameStart is changed
        self._frameStart = (hpos, vpos)
        # Only place self.shapes is changed
        self._shape = (hsize, vsize)
        #self.setParameter('Readout time', self.__scanLineTime * vsize / 1e6)

    def setBinning(self, binning):
        super().setBinning(binning)

        def binningAction():
            self._camera.binning = binning

        self._performSafeCameraAction(binningAction)

    def setParameter(self, name, value):
        super().setParameter(name, value)
        if value == " ":
            return self.parameters

        if name == "Set exposure time":
            self._setExposure(value)
            self._updatePropertiesFromCamera()

        elif name == 'Trigger source':
            self._setTriggerSource(value)
        # elif name == 'Readout port':
        #     self._setReadoutPort(value)

        elif name == "Denoising/Enhance":           #post processing parameter: DENOISING, ENABLED 0 or 1 use strings in the getter/setter.
            self._camera.set_post_processing_param("DENOISING", "ENABLED", 1) if value == "Yes" else self._camera.set_post_processing_param("DENOISING", "ENABLED", 0)
            var = self._camera.get_post_processing_param("DENOISING", "ENABLED")

        elif name == "Despeckle (pixel defects)":    #post processing parameter: 4 different ones BRIGHT/DARK LOW/HIGH, ENABLED 0 or 1
            if value == "ON (all ON)":
                self._camera.set_post_processing_param("DESPECKLE BRIGHT LOW", "ENABLED", 1)
                self._camera.set_post_processing_param("DESPECKLE BRIGHT HIGH", "ENABLED", 1)
                self._camera.set_post_processing_param("DESPECKLE DARK LOW", "ENABLED", 1)
                self._camera.set_post_processing_param("DESPECKLE DARK HIGH", "ENABLED", 1)
            else:
                self._camera.set_post_processing_param("DESPECKLE BRIGHT LOW", "ENABLED", 0)
                self._camera.set_post_processing_param("DESPECKLE BRIGHT HIGH", "ENABLED", 0)
                self._camera.set_post_processing_param("DESPECKLE DARK LOW", "ENABLED", 0)
                self._camera.set_post_processing_param("DESPECKLE DARK HIGH", "ENABLED", 0)

        elif name == "Fan Speed":               #parameter: getter with constant: HIGH=0, MEDIUM=1, LOW=2, OFF (liquid cooled)=3
            if value == "High":
                self._camera.set_param(consts.PARAM_FAN_SPEED_SETPOINT, 0)
            elif value == "Medium":
                self._camera.set_param(consts.PARAM_FAN_SPEED_SETPOINT, 1)
            elif value == "Low":
                self._camera.set_param(consts.PARAM_FAN_SPEED_SETPOINT, 2)
            else:
                self._camera.set_param(consts.PARAM_FAN_SPEED_SETPOINT, 3)

            var = self._camera.get_param(consts.PARAM_FAN_SPEED_SETPOINT)

        elif name == "Gain 11bit":                  #parameter: getter with constant: full well = 1, balanced = 2, sensitivity = 3
            spdtab_index = 0
            self._setPortSpeedGain(value, spdtab_index)
            self.parameters["Gain 16bit"].value = " "
            self.parameters["Readout Rate (speed)"].value = "200MHz 11bit"

        elif name == "Gain 16bit":
            spdtab_index = 1
            self._setPortSpeedGain(value, spdtab_index)
            self.parameters["Gain 11bit"].value = " "
            self.parameters["Readout Rate (speed)"].value = "100MHz 16bit"

        elif name == "QuantView":                    #post processing parameter: QUANTVIEW, ENABLED 0 or 1
            self._camera.set_post_processing_param("QUANTVIEW", "ENABLED", 1) if value == "Yes" else self._camera.set_post_processing_param("QUANTVIEW", "ENABLED", 0)
            var = self._camera.get_post_processing_param("QUANTVIEW", "ENABLED")

        elif name == "Readout Rate (speed)":
            #Seems to be just a shortcut for setting the gain and speed modes. Doesn't matter, can be set via Gain 11/16bit
            #Changing the detector parameter will trigger the widget via the controller and call setParameter for the respective gain changes!
            if value == "200MHz 11bit":
                self.parameters["Gain 11bit"].value = "1-Full well"
                self.parameters["Gain 16bit"].value = " "
                self.parameters["Readout Rate (speed)"].value = "200MHz 11bit"

            elif value == "100MHz 16bit":
                self.parameters["Gain 11bit"].value = " "
                self.parameters["Gain 16bit"].value = "1-CMS"
                self.parameters["Readout Rate (speed)"].value = "100MHz 16bit"

        elif name == "Smart Stream Channel":
            #TODO: implement
            pass
        elif name == "Smart Stream Timing":
            #TODO: implement
            pass
        elif name == "Smart Stream ON/OFF":
            #TODO: implement
            pass
        elif name == "Set Temperature":
            #TODO: implement
            pass
        elif name == "Trigger IN":
            #TODO: implement
            pass
        elif name == "Trigger OUT":
            #TODO: implement
            pass
        else:
            self.__logger.warning(f'Setting parameter {name} not implemented.')
        return self.parameters

    def startAcquisition(self):
        self.__acquisition = True
        self._camera.start_live()

    def stopAcquisition(self):
        self.__acquisition = False
        self._camera.abort()
        self._camera.finish()

    def _setExposure(self, time):
        self._camera.exp_time = int(time)

    def _setTriggerSource(self, source):
        self.__logger.debug("Change trigger source")

        def triggerAction():
            self._camera.exp_mode = trigger_value

        if source == 'Internal trigger':
            trigger_value = 1792
            self._performSafeCameraAction(triggerAction)

        elif source == 'External "start-trigger"':
            trigger_value = 2048
            self._performSafeCameraAction(triggerAction)

        elif source == 'External "frame-trigger"':
            trigger_value = 2560
            self._performSafeCameraAction(triggerAction)
        else:
            raise ValueError(f'Invalid trigger source "{source}"')

    def _setPortSpeedGain(self, gain_name, spdtab_idx):
        self.__logger.info("Changing speed and/or gain")

        def portSpeedGainAction():
            self._camera.speed = spdtab_idx
            self._camera.gain = gain_idx

        if gain_name == "1-Full well":
            gain_idx = 1
            self._performSafeCameraAction(portSpeedGainAction)

        elif gain_name == "2-Balanced":
            gain_idx = 2
            self._performSafeCameraAction(portSpeedGainAction)

        elif gain_name == "3-Sensitivity":
            gain_idx = 3
            self._performSafeCameraAction(portSpeedGainAction)

        elif gain_name == "1-CMS":
            gain_idx = 1
            self._performSafeCameraAction(portSpeedGainAction)

        elif gain_name == "2-HDR":
            gain_idx = 2
            self._performSafeCameraAction(portSpeedGainAction)

        else:
            raise ValueError(f'Invalid gain name"{gain_name}"')
    # def _setReadoutPort(self, port):
    #     self.__logger.debug("Change readout port")
    #
    #     def portAction():
    #         self._camera.readout_port = port_value
    #
    #     def getScanTimeAction():
    #         self.__scanLineTime = self._camera.scan_line_time
    #
    #     if port == 'Sensitivity':
    #         port_value = 0
    #         self._performSafeCameraAction(portAction)
    #
    #     elif port == 'Speed':
    #         port_value = 1
    #         self._performSafeCameraAction(portAction)
    #
    #     elif port == 'Dynamic range':
    #         port_value = 2
    #         self._performSafeCameraAction(portAction)
    #     else:
    #         raise ValueError(f'Invalid readout port "{port}"')
        #self._performSafeCameraAction(getScanTimeAction)
        #self.setParameter('Readout time', self.__scanLineTime * self._shape[0] / 1e6)

    def _performSafeCameraAction(self, function):
        """ This method is used to change those camera properties that need
        the camera to be idle to be able to be adjusted.
        """
        if self.__acquisition:
            self.stopAcquisition()
            function()
            self.startAcquisition()
        else:
            function()

    def _updatePropertiesFromCamera(self):
        self.setParameter('Real exposure time', self._camera.exp_time)
        triggerSource = self._camera.exp_mode
        if triggerSource == 1792:
            self.setParameter('Trigger source', 'Internal trigger')
        elif triggerSource == 2304:
            self.setParameter('Trigger source', 'External "start-trigger"')
        elif triggerSource == 2048:
            self.setParameter('Trigger source', 'External "frame-trigger"')

        # readoutPort = self._camera.readout_port
        # if readoutPort == 0:
        #     self.setParameter('Readout port', 'Sensitivity')
        # elif readoutPort == 1:
        #     self.setParameter('Readout port', 'Speed')
        # elif readoutPort == 2:
        #     self.setParameter('Readout port', 'Dynamic range')

    def finalize(self):
        self._camera.close()

    def _getCameraObj(self, cameraId):
        name = "PMUSBCam0"+str(cameraId)
        try:
            global _pyvcam_initialized
            if not _pyvcam_initialized:
                rvalue = pvc.init_pvcam()
                _pyvcam_initialized = True

            self.__logger.debug(f'Trying to initialize Photometrics camera {name}')
            camera = Camera.select_camera(name)
            camera.open()
        except Exception:
            self.__logger.warning(f'Failed to initialize Photometrics camera {name},'
                                  f' loading mocker')
            from imswitch.imcontrol.model.interfaces import MockPhotometrics
            camera = MockPhotometrics()

        self.__logger.info(f'Initialized camera, model: {camera.name}')

        return camera

    def _ensure_pyvcam_initialized(self):
        global _pyvcam_initialized
        if not _pyvcam_initialized:
            rvalue = pvc.init_pvcam()
            _pyvcam_initialized = True

# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
