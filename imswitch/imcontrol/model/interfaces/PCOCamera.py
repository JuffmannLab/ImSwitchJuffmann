import sys
import os
import numpy as np

import pylablib

# set path to dlls
pylablib.par['devices/dlls/pco_sc2']='C:\Program Files\PCO Digital Camera Toolbox\pco.camware'
from pylablib.devices import PCO

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger

"""
Interface for PCO camera using Pylablib    
"""

class PCOCamera:
    def __init__(self, idx = 0, cam_interface = None, reboot_on_fail = True, exposure_time = 1, binning = 1, nframes = 100):
        super().__init__()
        self.__logger = initLogger(self, tryInheritParent=True)

        # camera parameters
        self.camera = None
        self.camera_idx = idx
        self.model = 'pco.edge rolling shutter X2'
        self.cam_interface = cam_interface
        self.reboot_on_fail = reboot_on_fail
        self.exposure_time = exposure_time
        self.nframes = nframes
        
        # Binning is done in h and v direction. Even though we synchronize it for simplicity
        self.hbin = binning
        self.vbin = binning
        
        # define the buffer here:
        

        # initialise camera
        self._init_cam(idx=self.camera_idx, cam_interface=self.cam_interface, reboot_on_fail=self.reboot_on_fail, binning=binning)

    def _init_cam(self, idx, cam_interface, reboot_on_fail, binning = 1, hotpixelcorrection = 'On', noisefilter = 'On', doubleimagemode = False):
        
        self.hotpixelcorrection = hotpixelcorrection
        self.noisefilter = noisefilter
        self.doubleimagemode = doubleimagemode
        self.adjust_exposure = False
        
        self.camera = PCO.SC2.PCOSC2Camera(idx, cam_interface, reboot_on_fail)
        if self.camera.is_opened() == True:
            self.__logger.info(f'Camera already opened, Rebooting')
        else:
            self.open()
            
        self.setBinning(binning=binning)

        self.setExposure(exposuretime=self.exposure_time)
        
        self.setPropertyValue('hotpixel', hotpixelcorrection)
        
        self.setPropertyValue('noisefilter', noisefilter)
        
        self.setPropertyValue('doubleimagemode', doubleimagemode)
        
        
    def open(self):
        self.camera.open()

    def close(self):
        self.camera.close()

    def start_live(self):
        self.camera.start_acquisition()

    def stop_live(self):
        self.camera.stop_acquisition()

    def getLast(self):
        try:
            return self.camera.snap()
        except:
            pass

    def getLastChunk(self):

        try: 
            vid = self.camera.grab(nframes=self.nframes, frame_timeout=4) # unfortunately 100 frames is the maximum buffer size
            return vid
        
        except Exception as e:
            self.__logger.error(e)
            self.__logger.warning(f'Something went wrong in acquiring a video')
            pass

    def setExposure(self, exposuretime):
        self.exposure_time = exposuretime
        # it takes seconds as input variable, we change it to ms
        self.camera.set_exposure(self.exposure_time*0.001)
        
    def setBinning(self, binning):
        self.hbin = binning
        self.vbin = binning

    def setROI(self, hstart, hend, vstart, vend):
        # Check if the ROI has to be symmetric
        requires_h_symmetry, requires_v_symmetry = self.camera.requires_symmetric_roi()
        
        # Old version of setting ROI and proofing for constrains, however it will close the 
        # code if the input values does not fulfill the constrains. Therefore created a new 
        # definition which rounds to the nex allowed value. 
        """
        # get the center coordinates of the ROI
        h_center = (hstart + hend)/2
        v_center = (vstart + vend)/2
        h_width = (hend-hstart)
        v_height = (vend - vstart)
        
        # horizontal constrains min=160, max=2560, sstep=160, maxbin=4
        if not (0 <= hstart <=2560-160 and 160 <= hend <= 2560):
            self.__logger.warning(f'Horizontal Values must be between 160 and 2560')
            pass
        elif (hstart % 160 != 0) or (hend % 160 != 0):
            self.__logger.warning(f'Horizontal Values must be multiples of 160')
            pass
        elif hstart >= hend:
            self.__logger.warning(f'hstart must be smaller than hend')
            pass
        elif hend - hstart < 160:
            self.__logger.warning(f'Horizontal ROI width must be at least 160 pixels')
            pass
        elif self.hbin > 4:
            self.__logger.warning(f'Binning value not supported')
            pass
        
        # vertical constrains min=16, max=2160, sstep=1, maxbin=4
        elif not (0 <= vstart <=2160-16 and 16 <= vend <= 2160):
            self.__logger.warning(f'Vertical Values must be between 16 and 2160')
            pass
        elif vstart >= vend:
            self.__logger.warning(f'vstart must be smaller than vend')
            pass
        elif vend - vstart < 16:
            self.__logger.warning(f'Vertical ROI height must be at least 16 pixels')
        elif self.vbin > 4:
            self.__logger.warning(f'Binning value not supported')
            pass
        
        # Check for symmetric ROI requirement:
        elif requires_h_symmetry:
            hstart_expected = int(h_center - h_width/2)
            hend_expected = int(h_center + h_width/2)
            if (hstart, hend) != (hstart_expected, hend_expected):
                self.__logger.warning(f'Symmetric ROI in h direction required')
        
        elif requires_v_symmetry:
            vstart_expected = int(v_center - v_height/2)
            vend_expected = int(v_center + v_height/2)
            if (vstart, vend) != (vstart_expected, vend_expected):
                self.__logger.warning(f'Symmetric ROI v direction required')
             
        else:
            roi_values = (hstart, hend, vstart, vend, self.hbin, self.vbin, symmetric)
            self.setPropertyValue('roi', roi_values)

        return roi_values if roi_values else (hstart, hend, vstart, vend, self.hbin, self.vbin, symmetric)
        """
    # Ensure ROI values are within allowed constraints
        def clamp(value, min_val, max_val, step=1):
            value = max(min_val, min(max_val, value))  # Clamp within range
            return round(value / step) * step  # Snap to nearest step

        # Define constraints
        hstart = clamp(hstart, 0, 2560 - 160, step=1)
        hend = clamp(hend, 160, 2560, step=160)+hstart
        vstart = clamp(vstart, 0, 2160 - 16, step=1)
        vend = clamp(vend, 16, 2160, step=16)+vstart
        
        # Ensure hstart < hend and vstart < vend
        if hstart >= hend:
            hstart = hend - 160 
        if vstart >= vend:
            vstart = vend - 16
        
        # Apply symmetric ROI constraints if required
        if requires_h_symmetry:
            h_center = (hstart + hend) // 2
            h_width = (hend - hstart)
            hstart = h_center - (h_width // 2)
            hend = h_center + (h_width // 2)
        if requires_v_symmetry:
            v_center = (vstart + vend) // 2
            v_height = (vend - vstart)
            vstart = v_center - v_height // 2
            vend = v_center + (v_height // 2)
        
        roi_values = (hstart, hend, vstart, vend)
        return roi_values

    def reboot(self):
        self.camera.reboot(wait=True)

    def getPropertyValue(self, property_name):
        if property_name == 'all':
            property_value = self.camera.get_settings()
        elif property_name == 'exposure':
            property_value = self.camera.get_exposure()
        elif property_name == 'indexing':
            property_value = self.camera.get_settings()['image_indexing']
        elif property_name == 'frameformat':
            property_value = self.camera.get_settings()['frame_format']
        elif property_name == 'frameinfoformat':
            property_value = self.camera.get_settings()['frame_info_format']
        elif property_name == 'frameinfoperiod':
            property_value = self.camera.get_settings()['frame_info_period']
        elif property_name == 'image_height':
            property_value = self.camera.get_detector_size()[1]
        elif property_name == 'image_width':
            property_value = self.camera.get_detector_size()[0]
        elif property_name == 'doubleimagemode':
            property_value = self.camera.get_settings()['double_image_mode']
        elif property_name == 'roi':
            property_value = self.camera.get_settings()['roi']
        elif property_name == 'roilimits':
            property_value = self.camera.get_roi_limits()
        elif property_name == 'triggermode':
            property_value = self.camera.get_settings()['trigger_mode']
        elif property_name == 'framedelay':
            property_value = self.camera.get_settings()['frame_delay']
        elif property_name == 'frameperiod':
            property_value = self.camera.get_settings()['frame_period']
        elif property_name == 'bitalignment':
            property_value = self.camera.get_settings()['bit_alignment']
        elif property_name == 'hotpixel':
            if self.camera.get_settings()['hotpixel_correction']:
                property_value = 'On'
            else:
                property_value = 'Off'
        elif property_name == 'noisefilter':
            if self.camera.get_settings()['noise_filter'] == 0:
                property_value = 'Off'
            elif self.camera.get_settings()['noise_filter'] == 1:
                property_value = 'On'
        elif property_name == 'statusline':
            property_value = self.camera.get_settings()['status_line']
        elif property_name == 'pixelrate':
            property_value = self.camera.get_settings()['pixel_rate']
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
        if property_name == 'Set exposure time':
            self.setExposure(property_value)
        elif property_name == 'roi':
            self.camera.set_roi(property_value)
        elif property_name == 'Set Hotpixel Correction':
            if property_value == 'Off':
                self.camera.set_device_variable('hotpixel_correction', False)
            elif property_value == 'Off':
                self.camera.set_device_variable('hotpixel_correction', True)
        elif property_name == 'Set Noisefilter':
            if property_value == 'Off':
                self.camera.set_device_variable('noise_filter', 0)
            elif property_value == 'On':
                self.camera.set_device_variable('noise_filter', 1)
        elif property_name == 'Set Double Imaging Mode':
            if property_value == 'Off':
                self.camera.set_device_variable('double_image_mode', False)
            elif property_value == 'On':
                self.camera.set_device_variable('double_imaging_mode', True)
        elif property_name == 'Adjust Exposure Time for Frame Period':
            self.adjust_exposure = bool(property_value)
            self.camera.set_frame_period(frame_time=float(self.camera.get_frame_period()), adjust_exposure=self.adjust_exposure)
        elif property_name == 'Set Frame Period':
            self.camera.set_frame_period(frame_time=property_value, adjust_exposure=bool(property_value))
        elif property_name == 'Buffer Frames':
            self.camera.setup_acquisition(property_value)
        elif property_name == 'Status Line':
            self.camera.set_status_line_mode(binary = True, text = property_value)