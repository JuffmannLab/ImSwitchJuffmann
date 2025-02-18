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
        self.camera.set_exposure(self.exposure_time)
        self.roi_limits = self.camera.get_roi_limits()

    def open(self):
        self.camera.open()

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
    
    def set_frame_period(self, frame_period):
        self.camera.set_frame_period(frame_period)

    def start_acquistion(self):
        self.camera.start_acquisition()

    def stop_acquistion(self):
        self.camera.stop_acquisition()

    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass
    
    def get_attributes(self, attribute_name):
        if attribute_name == 'ExposureTime':
            attribute_value = self.camera.get_attribute_value('ExposureTime')
        elif attribute_name == 'ROI':
            attribute_value = self.camera.get_roi()
        elif attribute_name == 'FramePeriod':
            attribute_value = self.camera.get_frame_period()
        elif attribute_name == 'BlackLevel':
            attribute_value = self.camera.get_black_level_offset()
        return attribute_value

    def set_attributes(self, attribute_name, attribute_value):
        if attribute_name == 'ExposureTime':
            self.camera.set_attribute_value('ExposureTime', attribute_value)
        elif attribute_name == 'ROI':
            if attribute_value[0] <= self.roi_limits[0] and attribute_value[0] >= 0:
                if attribute_value[1] <= self.roi_limits[1] and attribute_value[1] >= 0:
                    self.camera.set_roi(attribute_value)
                else: 
                    self._logger.error('ROI Error')
                    self._logger.info('ROI is out of bounds')
            else: 
                self._logger.error('ROI Error')
                self._logger.info('ROI is out of bounds')


        return attribute_value



        

        