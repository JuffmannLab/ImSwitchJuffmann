import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import cv2

import pylablib
from pylablib.devices import PhotonFocus

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger

class PhotonFocusBitflowCamera:
    def __init__(self, exposure_time = 10, nframes = 100):
        super().__init__()
        self._logger = initLogger(self, tryInheritParent=True)
        
        self.exposure_time = exposure_time
        self.nframes = nframes

    def _init_cam(self, bitflow_idx=1, bitflow_camfile=None, pfcam_port=0):
        self.bitlfow_idx = bitflow_idx
        self.bitflow_camfile = bitflow_camfile
        self.pfcam_port = pfcam_port

        self.camera = PhotonFocus.PhotonFocusBitFlowCamera(self.bitlfow_idx, self.bitflow_camfile, self.pfcam_port)
        device_info = self.camera.get_device_info()
        self.camera.open()
        self.camera.set_exposure(self.exposure_time)

    def close(self):
        self.camera.close()

    def set_exposure_time(self, exposure_time):
        self.exposure_time = exposure_time
        self.camera.set_exposure(self.exposure_time)

    def shift_roi(self, roi):
        hstart = roi[0]
        vstart = roi[2]
        self.camera.fast_shift_roi(hstart, vstart)

    def set_roi(self, roi):
        hstart, hend, vstart, vend = roi[:4]
        self.camera.set_roi(hstart, hend, vstart, vend)

    def get_current_roi(self):
        return self.camera.get_roi()

    def get_aquistion_param(self):
        return self.camera.get_acquisition_parameters()
    
    def get_frame_timings(self):
        return self.camera.get_frame_timings()
    
    def set_frame_period(self, frame_period):
        self.camera.set_frame_period(frame_period)

    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass
         




        

        