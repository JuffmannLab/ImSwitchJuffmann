import numpy as np

from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter, DetectorParameter, DetectorListParameter




class PCOCamManager(DetectorManager):
    
    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        
        self._camera = self._getCameraObj(detectorInfo.managerProperties['cameraListIndex'])
        self._binning = 1
        
        for propertyName, propertyValue in detectorInfo.managerProperties['PCO'].items():
            self._camera.setPropertyValue(propertyName, propertyValue)
            
        fullShape = (self._camera.getPropertyValue('image_width'), 
                     self._camera.getPropertyValue('image_height'))

        model = self._camera.model
        self._running = False
    
        
    # Parameters    
        parameters = {
            'Set Exposure Time': DetectorNumberParameter(group='Acquisition', value=1, valueUnits='ms',
                                                    editable=True),                                         
            'Adjust Exposure Time for Frame Period': DetectorListParameter(group='Settings', value=True, 
                                                                           options=[True,
                                                                                    False],
                                                                            editable=True),
            'Set Frame Period': DetectorNumberParameter(group='Acquisition', value=self._camera.getPropertyValue('frameperiod'), valueUnits='arb.u.',
                                                        editable=True),
            'Set Hotpixel Correction': DetectorListParameter(group='Settings', value='On', 
                                                             options= ['Off',
                                                                       'On'],
                                                             editable=True),
            'Set Noisefilter': DetectorListParameter(group='Settings', value='On',
                                                     options=['Off',
                                                              'On',
                                                              'NC_HP_ON'],
                                                    editable=True),
            'Set Double Imaging Mode': DetectorListParameter(group='Settings', value='Off', 
                                                             options=['Off',
                                                                      'On'],
                                                            editable=True),
            'Buffer Frames': DetectorNumberParameter(group='Acquisition', value = self._camera.nframes,
                                                     valueUnits='frames', editable=True)
            }
        
        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1,2,3,4],
                         model=model, parameters=parameters, actions=None, croppable=True)
        
    def getLatestFrame(self, is_save=False):
        # is_save is passed by RecordingManager.snap: wait for a fresh frame instead of
        # returning the last one from the live view
        return self._camera.getLast(waitForNew=is_save)
    
    def setParameter(self, name, value):
        
        super().setParameter(name, value)

        if name not in self._DetectorManager__parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')
        
        value = self._camera.setPropertyValue(name, value)
        return value
    
    def getParameter(self, name):

        if name not in self._parameters:
            raise AttributeError(f'Non-existent parameter "{name}" specified')

        value = self._camera.getPropertyValue(name)
        return value
    
    def setBinning(self, binning):
        super().setBinning(binning)
        try:
            self._updateFrameFromROI(self._camera.setBinning(binning))
        except Exception as e:
            self.__logger.error(e)

    def getChunk(self):
        try:
            return self._camera.getLastChunk()
        except:
            
            return None
    
    def startAcquisition(self):
        if not self._running:
            self._camera.start_live()
            self._running = True
            self.__logger.debug('startlive')
            
    def stopAcquisition(self):
        if self._running:
            self._running = False
            self._camera.stop_live()
            self.__logger.debug('stoplive')

    def stopAcquisitionForROIChange(self):
        self._running = False
        self._camera.stop_live()
        self.__logger.debug('stoplive') 

    def flushBuffers(self):
        self._camera.flushBuffer()

    def getLostFrames(self):
        """ Number of frames overwritten in the buffer before they were read. Used by the
        recording to report incomplete recordings. """
        return self._camera.getLostFrames()
    
    def finalize(self) -> None:
        super().finalize()
        self.__logger.debug('Safely disconnecting the camera...')
        self._camera.close()

    @property
    def pixelSizeUm(self):
        return [1, 1, 1]
    
    def crop(self, hpos, vpos, hsize, vsize):
        # hpos, vpos, hsize, vsize come from the SettingsController in unbinned sensor pixels.
        # pylablib pauses/resumes a running acquisition itself, so no stop/start needed here.
        self.__logger.debug(
            f'{self._camera.model}: crop frame to {hsize}x{vsize} at {hpos},{vpos}.'
        )
        try:
            self._updateFrameFromROI(self._camera.setROI(hpos, hpos + hsize, vpos, vpos + vsize))
        except Exception as e:
            self.__logger.error(e)

    def _updateFrameFromROI(self, roi):
        """ Sets frameStart and shape from the ROI the camera actually applied, given as
        (hstart, hend, vstart, vend, hbin, vbin). Like the Settings widget, they are in binned
        pixels. """
        hstart, hend, vstart, vend, hbin, vbin = roi
        self._frameStart = (hstart // hbin, vstart // vbin)
        self._shape = ((hend - hstart) // hbin, (vend - vstart) // vbin)

    def _performSafeCameraAction(self, function):
        try:
            function()
        except Exception:
            self.stopAcquisition()
            function()
            self.startAcquisition()

    def _getCameraObj(self, cameraId):
        try:
            from imswitch.imcontrol.model.interfaces.PCOCamera import PCOCamera
            self.__logger.debug(f'Trying to initialze PCO camera {cameraId}')
            camera = PCOCamera(idx=cameraId)
        except Exception as e:
            self.__logger.debug(e)
            self.__logger.warning(f'Failed to Initialize PFCam {cameraId}, loading TIS Mocker')
            from imswitch.imcontrol.model.interfaces.tiscamera_mock import MockCameraTIS
            camera = MockCameraTIS()
            
        self.__logger.info(f'Initialized camera, model: {camera.model}')
        return camera