import numpy as np
import PySpin

from imswitch.imcommon.model import initLogger
from .DetectorManager import (
    DetectorManager,
    DetectorNumberParameter,
    DetectorListParameter,
)


class BlackflyManager(DetectorManager):
    """DetectorManager for a FLIR Blackfly camera using PySpin."""

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        self.detectorInfo = detectorInfo

        props = detectorInfo.managerProperties

        self._camera_index = props.get("cameraListIndex", 0)
        self._timeout_ms = props.get("timeout_ms", 1000)
        self._pixel_size = props.get("cameraEffPixelsize", 1.0)

        self.PySpin = None
        self.system = None
        self.cam_list = None
        self.cam = None
        self.imageAcqLastFailed = False
        self.frame = None

        self._running = False
        self._latest_frame = None
        self._chunk_buffer = []
        self._image = None
        self.timeout = 5

        self._model = "FLIR Blackfly"
        self._fullShape = (
            props.get("width", 5472),
            props.get("height", 3648),
        )

        self._open_camera()

        parameters = {
            "exposure": DetectorNumberParameter(
                group="Misc",
                value=props.get("exposure_ms", 10),
                valueUnits="ms",
                editable=True,
            ),
            "gain": DetectorNumberParameter(
                group="Misc",
                value=props.get("gain", 0),
                valueUnits="arb.u.",
                editable=True,
            ),
            "image_width": DetectorNumberParameter(
                group="Misc",
                value=self._fullShape[0],
                valueUnits="px",
                editable=False,
            ),
            "image_height": DetectorNumberParameter(
                group="Misc",
                value=self._fullShape[1],
                valueUnits="px",
                editable=False,
            ),
            "trigger_source": DetectorListParameter(
                group="Acquisition mode",
                value="Continuous",
                options=["Continuous", "Software trigger", "External trigger"],
                editable=True,
            ),
            "Camera pixel size": DetectorNumberParameter(
                group="Miscellaneous",
                value=self._pixel_size,
                valueUnits="µm",
                editable=True,
            ),
        }

        super().__init__(
            detectorInfo,
            name,
            fullShape=self._fullShape,
            supportedBinnings=[1],
            model=self._model,
            parameters=parameters,
            actions=None,
            croppable=True,
        )

    def _open_camera(self):

        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()

        num_cameras = self.cam_list.GetSize()
        self.__logger.info(f"Number of Blackfly cameras detected: {num_cameras}")

        if num_cameras == 0:
            self.cam_list.Clear()
            self.system.ReleaseInstance()
            raise RuntimeError("No Blackfly camera detected.")

        self.cam = self.cam_list.GetByIndex(self._camera_index)
        self.cam.Init()

        nodemap = self.cam.GetTLDeviceNodeMap()
        model_node = PySpin.CStringPtr(nodemap.GetNode("DeviceModelName"))

        if PySpin.IsReadable(model_node):
            self._model = model_node.GetValue()
            self.__logger.info(f"Camera model: {self._model}")

        self.cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)

        width = self.cam.Width.GetValue()
        height = self.cam.Height.GetValue()
        self._fullShape = (width, height)

        self.__logger.info("Blackfly camera opened")

    @property
    def pixelSizeUm(self):
        um_per_pixel = self.parameters["Camera pixel size"].value
        return [1, um_per_pixel, um_per_pixel]

    def crop(self, hpos, vpos, hsize, vsize):
        """Set the camera ROI. First version: only update ImSwitch shape."""
        self.__logger.debug(
            f"Requested ROI: {hsize}x{vsize} at ({hpos}, {vpos})"
        )

        self._frameStart = (hpos, vpos)
        self._shape = (hsize, vsize)

    def getExposure(self):
        """Return exposure time in microseconds."""
        exposure_ms = self.parameters["exposure"].value
        return int(exposure_ms * 1000)

    def _getFallbackFrame(self):
        """Return a valid fallback frame so ImSwitch never receives None."""
        if self._latest_frame is not None:
            return self._latest_frame

        width, height = self._fullShape
        return np.zeros((height, width), dtype=np.uint16)

    def getLatestFrame(self):
        """Return the latest frame from the Blackfly camera."""
        self.imageAcqLastFailed = False

        try:
            if not self.cam.IsStreaming() : # normally should not happen but if acquisition stopped, restart it
                self.startAcquisition()

            self._image = self.cam.GetNextImage(int(1000*self.timeout))

            if self._image.IsIncomplete():
                print('ERROR ! : Image incomplete with image status %d ...' % self._image.GetImageStatus())
                self.imageAcqLastFailed = True
                return False

            else:
                self.frame = np.array(self._image.GetNDArray())

        except PySpin.SpinnakerException as ex:
            print('ERROR : %s' % ex)
            print('Failed to grab array from camera : probably Timeout')
            self.imageAcqLastFailed = True
            return False

        finally:
            if self._image is not None:
                self._image.Release()
        return self.frame.copy()
    
    def getChunk(self):
        """Return frames collected since the previous getChunk call."""
        if len(self._chunk_buffer) == 0:
            return np.array([])

        chunk = np.stack(self._chunk_buffer, axis=0)
        self._chunk_buffer = []
        return chunk

    def flushBuffers(self):
        """Clear software frame buffer."""
        self._chunk_buffer = []

    def startAcquisition(self):
        """Start image acquisition."""
        if self._running:
            return

        try:
            self.cam.BeginAcquisition()
            self._running = True
            self.__logger.info("Blackfly acquisition started")

        except Exception as e:
            self._running = False
            self.__logger.warning(f"Could not start Blackfly acquisition: {e}")

    def stopAcquisition(self):
        """Stop image acquisition."""
        if not self._running:
            return

        try:
            self.cam.EndAcquisition()
            self.__logger.info("Blackfly acquisition stopped")

        except Exception as e:
            self.__logger.warning(f"Could not stop Blackfly acquisition: {e}")

        finally:
            self._running = False

    def finalize(self):
        """Safely disconnect the camera."""
        super().finalize()

        self.__logger.info("Closing Blackfly camera")

        if self._running:
            self.stopAcquisition()

        if self.cam is not None:
            self.cam.DeInit()
            self.cam = None

        if self.cam_list is not None:
            self.cam_list.Clear()
            self.cam_list = None

        if self.system is not None:
            self.system.ReleaseInstance()
            self.system = None