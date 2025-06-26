import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import cv2
import platform
if(platform.system() == 'Windows'):
    import msvcrt
    
    if (sys.version_info.major >= 3 and sys.version_info.minor >= 8):
        import os
        #Following lines specifying, the location of DLLs, are required for Python Versions 3.8 and greater
        os.add_dll_directory('C:\BitFlow SDK 6.5\Bin64')
        os.add_dll_directory('C:\Program Files\CameraLink\Serial')

from pylablib.devices import PhotonFocus

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger

class PhotonFocusBitflowCamera:
    def __init__(self, exposure_time = 10, nframes = 100, mode = 'sequence', pfcam_port = 0):
        super().__init__()
        self.__logger = initLogger(self, tryInheritParent=True)
        
        self.exposure_time = exposure_time
        self.nframes = nframes
        self.mode = mode
        self.pfcam_port = pfcam_port
        self.camera = None
        
        self._init_cam(port=self.pfcam_port)

    def _init_cam(self, index=0, camfile=None, port=0):

        self.camera = PhotonFocus.PhotonFocusBitFlowCamera(index, camfile, port) # to do: provide the path to the camfile in order to change the ROI
        self.model = self.getPropertyValue('CameraName')
        self.open()
        self.setPropertyValue('EposureTime', self.exposure_time)
        
    def open(self):
        self.camera.open()
    
    def close(self):
        self.camera.close()

    def setROI_shift(self, hstart, vstart):
        
        max_roi = self.getPropertyValue('MaxROI')
        h_max = max_roi[0].max
        v_max = max_roi[1].max
        h_current = self.getPropertyValue('image_width')
        v_current = self.getPropertyValue('image_height')
        h_limit = h_max - h_current
        v_limit = v_max - v_current

        if hstart <= h_limit and vstart <= v_limit:

            self.camera.fast_shift_roi(hstart, vstart)
        else:
            self.__logger.warning(
                f'ROI shift exceeds maximum boundaries. '
                f'Maximum horizontal start: {h_limit}. '
                f'Maximum vertical start: {v_limit}. '
                f'Requested: {hstart},{vstart}')
        
        return hstart, vstart

        
    def setROI(self, hstart, hend, vstart, vend):
        # Defining the ROI settings. Only multiples of 128 are allowed,
        # therefore it is rounding to the next instance of 128.
        # if the starting value + the roi size exceeds the frame size (1024)
        # the starting values will be changed accordingly 

        def clamp_and_snap(value, min_val, max_val, step):
            value = max(min_val, min(max_val, value))
            return round(value / step) * step

        roi_width = clamp_and_snap(hend, 128, 1024, 128)
        roi_height = clamp_and_snap(vend, 128, 1024, 128)

        hstart = min(hstart, 1024 - roi_width)
        vstart = min(vstart, 1024 - roi_height)

        hstart = (hstart // 128) * 128
        vstart = (vstart // 128) * 128

        hend = hstart + roi_width
        vend = vstart + roi_height

        self.camera.set_roi(hstart, hend, vstart, vend)

        return hstart, vstart, hend, vend
            
    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass
    
    def start_live(self):
        nframes = self.nframes
        mode = self.mode
        if self.camera.acquisition_in_progress() == False:
            self.camera.start_acquisition(nframes=nframes, mode=mode)
            
    def stop_live(self):
        if self.camera.acquisition_in_progress() == True:
            self.camera.stop_acquisition()
            
    def suspend_live(self):
        if self.camera.acquisition_in_progress() == True:
            self.camera.pausing_acquisition()
            
    def getLastChunk(self):
        try:
            self.camera.wait_for_frame()
            pf_newframe = self.camera.read_newest_image()
            return pf_newframe

        except Exception as e:
            self.__logger.error(e)
            self.__logger.warning(f'Something went wrong in acquiring a video')
            pass
        
    def getPropertyValue(self, attribute_name):
        if attribute_name == 'All':
            attribute_value = self.camera.get_all_attribute_values()
        elif attribute_name == 'ExposureTime':
            attribute_value = self.camera.get_attribute_value('ExposureTime')
        elif attribute_name == 'ROI':
            attribute_value = self.camera.get_roi()
        elif attribute_name == 'FramePeriod':
            attribute_value = self.camera.get_frame_period()
        elif attribute_name == 'FineGain':
            attribute_value = self.camera.get_attribute_value('FineGain')
        elif attribute_name == 'MaxROI':
            attribute_value = self.camera.get_roi_limits()
        elif attribute_name == 'BlackLevelOffset':
            attribute_value = self.camera.get_attribute_value('Voltages/BlackLevelOffset')
        elif attribute_name == 'image_width':
            attribute_value = self.camera.get_attribute_value('Window/H')
        elif attribute_name == 'image_height':
            attribute_value = self.camera.get_attribute_value('Window/W')
        elif attribute_name == 'CameraName':
            attribute_value = self.camera.get_attribute_value('CameraName')
        elif attribute_name == 'Hstart':
            attribute_value = self.camera.get_all_attribute_values('Window/X')
        elif attribute_name == 'Vstart':
            attribute_value = self.camera.get_all_attribute_values('Window/Y')
            
        return attribute_value
            
    def setPropertyValue(self, attribute_name, attribute_value):
        if attribute_name == 'ExposureTime':
            self.camera.set_exposure(attribute_value)
        elif attribute_name == 'FramePeriod':
            self.camera.set_frame_period(attribute_value)
        elif attribute_name == 'FineGain':
            self.camera.set_attribute_value('FineGain', attribute_value)
        elif attribute_name == 'BlackLevelOffset':
            self.camera.set_attribute_value('Voltages/BlackLevelOffset', attribute_value)
        elif attribute_name == 'Hstart':
            self.camera.set_attribute_value('Window/X', attribute_value)
        elif attribute_name == 'Vstart':
            self.camera.set_attribute_value('Window/Y', attribute_value)
            
    def openPropertiesGUI(self):
        pass
     