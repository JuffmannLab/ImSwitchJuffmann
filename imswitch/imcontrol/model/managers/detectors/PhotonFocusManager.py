import numpy as np

from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter, DetectorListParameter

"""
Manager for PhotonFocus camera connected via CameraLink to a Bitflow Frame Grabber
To Do:
-Fix recording and live view
-Enable change of ROI
-Check how to display the live image over the whole canvas
"""

class PhotonFocusManager(DetectorManager):
    
    def __init__(self, detectorInfo, name, **_lowlevelManagers):
        self.__logger = initLogger(self, instanceName=name)
       
        cameraId = detectorInfo.managerProperties['cameraListIndex']
        self._pixelSizeUm = detectorInfo.managerProperties.get('pixelSizeUm')
        self.camera = self._getPFObj(cameraId)
       
        for propertyName, propertyValue in detectorInfo.managerProperties['PFCam'].items():
           self.camera.setPropertyValue(propertyName, propertyValue)
        
        model = self.camera.model
        self._running = False
        self._adjustingParameters = False
        
        fullShape = (self.camera.getPropertyValue('image_width'),
                     self.camera.getPropertyValue('image_height'))
        
        # Prepare parameters
        parameters = {
            'ExposureTime': DetectorNumberParameter(group='Timings', value=0.005, valueUnits='s',
                                                editable=True),
            'FramePeriod': DetectorNumberParameter(group='Timings', value=self.camera.getPropertyValue('FramePeriod'), valueUnits='arb.u.',
                                                editable=True),
            'FineGain': DetectorNumberParameter(group='Misc', value=1, valueUnits='arb.u.', 
                                            editable=True),
            'BlackLevelOffset': DetectorNumberParameter(group='Misc', value=self.camera.getPropertyValue('BlackLevelOffset'), valueUnits='arb.u.', 
                                            editable=True),
            # Ring buffer size; can be set with "NumberOfFrames" under "PFCam" in the setup file
            'NumberOfFrames': DetectorNumberParameter(group='Misc', value=getattr(self.camera, 'nframes', 100), valueUnits='frames',
                                            editable=True),
            'Hstart': DetectorNumberParameter(group = 'Frame', value=self.camera.getPropertyValue('Hstart'), valueUnits='px',
                                              editable = True),
            'Vstart': DetectorNumberParameter(group = 'Frame', value=self.camera.getPropertyValue('Vstart'), valueUnits='px',
                                              editable = True),
            'CFR': DetectorListParameter(group='Advanced',                            
                                         value= True,
                                         options=[True,
                                                  False],
                                         editable=True),
            'StatusLine': DetectorListParameter(group='Advanced',                            
                                         value= False,
                                         options=[True,
                                                  False],
                                         editable=True)
            }
        
        actions = {
            'More properties': DetectorAction(group='Misc',
                                              func=self.camera.openPropertiesGUI)
        } 
        
        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1],
                         model=model, parameters=parameters, actions=actions, croppable=False) 

    def getLatestFrame(self, is_save = False):
        # is_save is passed by RecordingManager.snap: wait for a fresh frame instead of
        # returning the last one from the live view
        return self.camera.getLast(waitForNew=is_save)
    
    def setParameter(self, name, value):
        
        super().setParameter(name, value)
    
        if name not in self._DetectorManager__parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')

        try:
            self.camera.setPropertyValue(name, value)
            print(f"Changed {name} to {value}")
        except Exception as e:
            self.__logger.debug(e)
            self.__logger.warning(f'Failed to change value of {name}')
            
        return value
    
    def getParameter(self, name):
        
        if name not in self._parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')

        value = self.camera.getPropertyValue(name)
        return value
    
    def setBinning(self, binning):
        return super().setBinning(binning)
    
    def getChunk(self):
        try:
            return self.camera.getLastChunk()
        except:
            return None
        
    def flushBuffers(self):
        self.camera.flushBuffer()

    def getLostFrames(self):
        """ Number of frames overwritten in the buffer before they were read. Used by the
        recording to report incomplete recordings. """
        return self.camera.getLostFrames()
    
    def startAcquisition(self):
        if not self._running:
            self.camera.start_live()
            self._running = True
            self.__logger.debug('startlive')
            
    def stopAcquisition(self):
        if self._running:
            self._running = False
            self.camera.stop_live()
            self.__logger.debug('stoplive')
            
    def stopAcquisitionForROIChange(self):
        self._running = False
        self.camera.stop_live()
        self.__logger.debug('stoplive') 

    @property
    def pixelSizeUm(self):
        # "pixelSizeUm" in the managerProperties: effective pixel size at the sample (also used
        # to display the cameras in the same scale)
        size = self._pixelSizeUm if self._pixelSizeUm else 1
        return [1, size, size]

    def crop(self, hpos, vpos, hsize, vsize):
        pass
        """Crop the camera frame to the specified ROI
        # Stop acquisition if running
        was_running = self._running
        if was_running:
            self.stopAcquisitionForROIChange()
        
        try:
            # Set the new ROI
            actual_hpos, actual_vpos, actual_hsize, actual_vsize = self.camera.setROI(hpos, hsize, vpos, vsize)
            
            # Update frame parameters
            self._frameStart = (actual_hpos, actual_vpos)
            self._shape = (actual_hsize, actual_vsize)
            
            # Log the change
            self.__logger.debug(f'ROI set to: X={actual_hpos}, Y={actual_vpos}, '
                            f'Width={actual_hsize}, Height={actual_vsize}')
            
            return True
        except Exception as e:
            self.__logger.error(f'Error setting ROI: {str(e)}')
            return False
        finally:
            # Restart acquisition if it was running
            if was_running:
                self.startAcquisition()
        """
    
    def _performSafeCameraAction(self, function):
        """ This method is used to change those camera properties that need
        the camera to be idle to be able to be adjusted.
        """
        self._adjustingParameters = True
        wasrunning = self._running
        self.stopAcquisitionForROIChange()
        function()
        if wasrunning:
            self.startAcquisition()
        self._adjustingParameters = False

    def openPropertiesDialog(self):
        self.camera.openPropertiesGUI()
       
    def _getPFObj(self, cameraId):
        try:
            from imswitch.imcontrol.model.interfaces.PhotonFocus import PhotonFocusBitflowCamera
            self.__logger.debug(f'Trying to initialize PhotonFocus camera {cameraId}')
            camera = PhotonFocusBitflowCamera(pfcam_port=cameraId)
        except Exception as e:
            self.__logger.debug(e)
            self.__logger.warning(f'Failed to Initialize PFCam {cameraId}, loading TIS Mocker')
            from imswitch.imcontrol.model.interfaces.tiscamera_mock import MockCameraTIS
            camera = MockCameraTIS()

        self.__logger.info(f'Initialized camera, model: {camera.model}')
        return camera
    
    def finalize(self) -> None:
        # Called by the DetectorsManager on shutdown: stopping the acquisition also ends
        # pylablib's buffer thread before the camera is closed
        super().finalize()
        self.__logger.debug('Safely disconnecting the camera...')
        self.stopAcquisition()
        self.camera.close()

    def closeEvent(self):
        self.camera.close()