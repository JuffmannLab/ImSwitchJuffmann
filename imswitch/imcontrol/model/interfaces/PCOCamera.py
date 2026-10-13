import functools
import sys
import os
import threading
import numpy as np

import pylablib

# set path to dlls
pylablib.par['devices/dlls/pco_sc2']='C:\Program Files\PCO Digital Camera Toolbox\pco.camware'
from pylablib.devices import PCO

from logging import raiseExceptions
from imswitch.imcommon.model import initLogger


def _locked(func):
    """ Runs the method while holding the camera lock: frames are not read while the ROI,
    binning or acquisition state change. Otherwise the LiveView thread could read while pylablib
    pauses the acquisition for a new ROI, take a snap() and collide with the restart. """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return func(self, *args, **kwargs)
    return wrapper

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

        self._lastFrame = None
        self._lock = threading.RLock()
        

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

    @_locked
    def start_live(self):
        self.camera.start_acquisition()

    @_locked
    def stop_live(self):
        self.camera.stop_acquisition()

    @_locked
    def getLast(self, waitForNew=False):
        # snap()/grab() start and stop a new acquisition on every call, which stalls the
        # running live acquisition. While acquiring, read the newest frame from the buffer instead.
        # peek=True leaves the frames unread, so getLastChunk (differential view, recording)
        # still gets every frame. With waitForNew=True, wait for a frame recorded after this
        # call (used for snaps, so they don't return an old frame).
        try:
            if self.camera.acquisition_in_progress():
                if waitForNew:
                    self.camera.wait_for_frame(since='now', timeout=self.exposure_time * 1e-3 + 5)
                frame = self.camera.read_newest_image(peek=True)
                if frame is not None:
                    self._lastFrame = frame
            else:
                self._lastFrame = self.camera.snap()
        except Exception as e:
            self.__logger.error(e)
        return self._lastFrame

    @_locked
    def getLastChunk(self):
        # Returns all frames acquired since the last call, shape (nframes, height, width).
        # Returns an empty array (0, height, width) if there are none, since the recording
        # calls len() on the result.
        try:
            frames = self.camera.read_multiple_images()
            if frames:
                return np.stack(frames)
        except Exception as e:
            self.__logger.error(e)
            self.__logger.warning(f'Something went wrong in acquiring a video')
        return np.zeros((0, *self.camera.get_data_dimensions()), dtype=np.uint16)

    def getLostFrames(self):
        """ Number of frames that were overwritten in the ring buffer before they were read
        (pylablib counts frames skipped by flushBuffer here as well). """
        return self.camera.get_frames_status().skipped

    @_locked
    def flushBuffer(self):
        # Marks all frames recorded so far as read, so the next getLastChunk only returns new ones
        if self.camera.acquisition_in_progress():
            self.camera.read_newest_image()

    def setExposure(self, exposuretime):
        self.exposure_time = exposuretime
        # it takes seconds as input variable, we change it to ms
        self.camera.set_exposure(self.exposure_time*0.001)
        
    @_locked
    def setBinning(self, binning):
        self.hbin = binning
        self.vbin = binning
        # The PCO sets binning together with the ROI, so re-apply the current ROI with the new binning
        hstart, hend, vstart, vend, _, _ = self.camera.get_roi()
        return self.setROI(hstart, hend, vstart, vend)

    @_locked
    def setROI(self, hstart, hend, vstart, vend, symmetric=False):
        """ Sets the ROI in unbinned sensor pixels (end exclusive) and returns the ROI that was
        actually applied as (hstart, hend, vstart, vend, hbin, vbin).
        pylablib snaps the values to the allowed steps/limits of the camera and pauses/resumes
        a running acquisition itself. With symmetric=False the part of the ROI that the camera
        can't do in hardware is done as software ROI: smaller frames, but no faster readout.
        symmetric=True keeps the hardware ROI symmetric around the sensor centre, which is what
        actually increases the frame rate. """
        roi = self.camera.set_roi(hstart, hend, vstart, vend, self.hbin, self.vbin, symmetric=symmetric)
        if tuple(roi[:4]) != (hstart, hend, vstart, vend):
            hlim, vlim = self.camera.get_roi_limits(self.hbin, self.vbin)
            self.__logger.warning(
                f'Requested ROI h {hstart}-{hend}, v {vstart}-{vend} was adjusted to camera limits: '
                f'h {roi[0]}-{roi[1]}, v {roi[2]}-{roi[3]} '
                f'(h min {hlim.min}, step {hlim.pstep}; v min {vlim.min}, step {vlim.pstep})'
            )
        return roi

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
            self.camera.set_roi(*property_value)
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