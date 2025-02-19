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


import pylablib
from pylablib.devices import PhotonFocus

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger

class PhotonFocusBitflowCamera:
    def __init__(self, exposure_time = 10, nframes = 100, mode = 'sequence', pfcam_port = 0):
        super().__init__()
        self._logger = initLogger(self, tryInheritParent=True)
        
        self.exposure_time = exposure_time
        self.nframes = nframes
        self.mode = mode
        self.pfcam_port = pfcam_port
        self.camera = None
        
        self._init_cam(port=self.pfcam_port)

    def _init_cam(self, index=0, camfile=None, port=0):

        self.camera = PhotonFocus.PhotonFocusBitFlowCamera(index, camfile, port)
        self.model = self.get_attribute('CameraName')
        self.open()
        self.set_attribute('EposureTime', self.exposure_time)
        
    def open(self):
        self.camera.open()
    
    def close(self):
        self.camera.close()
        
    def set_roi(self, hstart, vstart):
        self.camera.set_roi(hstart=hstart, hend=hstart+128, vstart=vstart, vend=vstart+128)
            
    def shift_roi(self):
        roi =self.get_attribute('ROI')
        hstart = roi[0]
        vstart = roi[2]
        self.camera.fast_shift_roi(hstart, vstart)
        
    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass
    
    def start_acquisition(self):
        nframes = self.nframes
        mode = self.mode
        if self.camera.acquisition_in_progress == False:
            self.camera.start_acquisition(nframes=nframes, mode=mode)
            
    def stop_acquisition(self):
        if self.camera.acquisition_in_progress == True:
            self.camera.stop_acquisition()
            
    def pause_acquistion(self):
        if self.camera.acquisition_in_progress == True:
            self.camera.pausing_acquisition()
            
    def grab_video(self):
        vid = []
        self.camera.wait_for_frame()
        newframe = self.camera.read_newest_image()
        if type(newframe) == np.ndarray:
            vid.append(newframe)       
        video = np.array(self.vid)
        return video
        
    def get_attribute(self, attribute_name):
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
        elif attribute_name == 'ImageWidth':
            attribute_value = self.camera.get_attribute_value('Window/H')
        elif attribute_name == 'ImageHeight':
            attribute_value = self.camera.get_attribute_value('Window/W')
        elif attribute_name == 'CameraName':
            attribute_value = self.camera.get_attribute_value('CameraName')
            
        return attribute_value
            
    def set_attribute(self, attribute_name, attribute_value):
        if attribute_name == 'ExposureTime':
            self.camera.set_exposure(attribute_value)
        elif attribute_name == 'FramePeriod':
            self.camera.set_frame_period(attribute_value)
        elif attribute_name == 'FineGain':
            self.camera.set_attribute_value('FineGain', attribute_value)
        elif attribute_name == 'BlackLevelOffset':
            self.camera.set_attribute_value('Voltages/BlackLevelOffset', attribute_value)
            
    def openPropertiesGUI(self):
        pass
     