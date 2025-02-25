import numpy as np

from imswitch.imcommon.model import initLogger
from .DetectorManager import DetectorManager, DetectorAction, DetectorNumberParameter




class PCOCamManager(DetectorManager):
    
    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        
        self._camera = self._getCameraObj(detectorInfo.managerProperties['cameraListIndex'])
        self._binning = 1
        
        for propertyName, propertyValue in detectorInfo.managerProperties['PCO'].items():
            self._camera.setPropertyValue(propertyName, propertyValue)
            
        fullShape = ()
        
        
        
        
        
    def _getCameraObj(self, cameraId):
        try:
            from imswitch.imcontrol.model.interfaces import PCOCamera
            self.__logger.debug(f'Trying to initialze PCO camera {cameraId}')
            camera = PCOCamera(idx=CameraId)
        except Exception as e:
            self.__logger.debug(e)
            self.__logger.warning(f'Failed to Initialize PFCam {cameraId}, loading TIS Mocker')
            from imswitch.imcontrol.model.interfaces.tiscamera_mock import MockCameraTIS
            camera = MockCameraTIS()
            
        self.__logger.info(f'Initialized camera, model: {camera.model}')
        return camera