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
    def __init__(self, idx = 0, cam_interface = None, reboot_on_fail = True, exposure_time = 0.001, ):
        
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

    def open(self):
        self.camera.open()

    def close(self):
        self.camera.close()

    def startAcquisition(self):
        self.camera.start_acquisition()

    def stopAcquistion(self):
        self.camera.stop_acquisition()

    def getLatest(self):
        self.camera.snap()

    def getChunk(self):
        pass

    def getPropertyValue(self, property_name):
        if property_name == 'all':
            self.camera.get_settings()
        elif property_name == 'exposure':
            self.camera.get_exposure()
        elif property_name == ''
        elif property_name ==
        elif property_name ==
        elif property_name ==
        elif property_name ==
        elif property_name ==
        elif property_name ==
        elif property_name ==

    def setPropertyValue(self, property_name, property_value):
        pass
