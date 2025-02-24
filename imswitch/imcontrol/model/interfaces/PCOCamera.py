import sys
import os
import numpy as np

import pylablib

# set path to dlls
pylablib.par['devices/dlls/pco_sc2']='C:\Program Files\PCO Digital Camera Toolbox\pco.camware'
from pylablib.devices import PCO

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger

class PCOCamera:
    def __init__(self, idx = 0, cam_interface = None, reboot_on_fail = True, exposure_time = 1, ):
        self.__logger = initLogger(self, tryInheritParent=True)

        # camera parameters
        self.camera = None
        self.camera_idx = idx
        self.cam_interface = cam_interface
        self.reboot_on_fail = reboot_on_fail
        self.exposure_time = exposure_time

        # initialise camera
        self._init_cam(idx=self.camera_idx, cam_interface=self.cam_interface, reboot_on_fail=self.reboot_on_fail)

    def _init_cam(self, idx, cam_interface, reboot_on_fail):
        
        self.camera = PCO.SC2.PCOSC2Camera(idx, cam_interface, reboot_on_fail)

        self.pco_vid = []

    def open(self):
        self.camera.open()

    def close(self):
        self.camera.close()

    def startAcquisition(self):
        self.camera.start_acquisition()

    def stopAcquistion(self):
        self.camera.stop_acquisition()

    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass

    def getLastChunk(self):
        try:
            self.camera.wait_for_frame()
            pco_newframe = self.camera.read_newest_image()

            if isinstance(pco_newframe, np.ndarray):  
                return np.expand_dims(pco_newframe, axis=0)  

        except Exception as e:
            self.__logger.error(e)
            self.__logger.warning(f'Something went wrong in acquiring a video')

    def setExposure(self, exposuretime):
        self.exposure_time = exposuretime
        self.setPropertyValue('exposure', self.exposure_time*0.001)


    def reboot(self):
        self.camera.reboot(wait=True)

    def getPropertyValue(self, property_name):
        if property_name == 'all':
            property_value = self.camera.get_settings()
        elif property_name == 'exposure':
            property_value = self.camera.get_exposure()
        elif property_name == 'indexing':
            property_value = self.camera.get_settings('image_indexing')
        elif property_name == 'frameformat':
            property_value = self.camera.get_settings('frame_format')
        elif property_name == 'frameinfoformat':
            property_value = self.camera.get_settings('frame_info_format')
        elif property_name == 'frameinfoperiod':
            property_value = self.camera.get_settings('frame_info_period')
        elif property_name == 'doubleimagemode':
            property_value = self.camera.get_settings('double_image_mode')
        elif property_name == 'roi':
            property_value = self.camera.get_settings('roi')
        elif property_name == 'roilimits':
            property_value = self.camera.get_roi_limits()
        elif property_name == 'triggermode':
            property_value = self.camera.get_settings('trigger_mode')
        elif property_name == 'framedelay':
            property_value = self.camera.get_settings('frame_delay')
        elif property_name == 'frameperiod':
            property_value = self.camera.get_settings('frame_period')
        elif property_name == 'bitalignment':
            property_value = self.camera.get_settings('bit_alignment')
        elif property_name == 'hotpixel':
            property_value = self.camera.get_settings('hotpixel_correction')
        elif property_name == 'noisefilter':
            property_value = self.camera.get_settings('noise_filter')
        elif property_name == 'statusline':
            property_value = self.camera.get_settings('status_line')
        elif property_name == 'pixelrate':
            property_value = self.camera.get_settings('pixel_rate')
        elif property_name == 'temperature':
            property_value = self.camera.get_temperature()
        elif property_name == 'conversionfactor':
            property_value = self.camera.get_conversion_factor()
        elif property_name == 'detectorsize':
            property_value = self.camera.get_detector_size()
        elif property_name == 'framestatus':
            property_value = self.camera.get_frames_status()
        return property_value

    def setPropertyValue(self, property_name, property_value):
        if property_name == 'exposure':
            self.camera.set_exposure(property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)
        elif property_name == '':
            self.camera.set_device_variable(property_name ,property_value)

