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
        """Set the current software ROI."""
        self.__logger.info(
            f"Requested ROI: {hsize}x{vsize} at ({hpos}, {vpos})"
        )

        self._frameStart = (int(hpos), int(vpos))
        self._shape = (int(hsize), int(vsize))

    def _applySoftwareCrop(self, frame):
        """Apply the current ImSwitch ROI as a software crop.

        The camera still acquires the full frame. This only crops the numpy array
        before sending it to LiveView/Snap.
        """
        if not hasattr(self, "_frameStart") or not hasattr(self, "_shape"):
            return frame

        hpos, vpos = self._frameStart
        hsize, vsize = self._shape

        height, width = frame.shape[:2]

        hpos = max(0, min(int(hpos), width - 1))
        vpos = max(0, min(int(vpos), height - 1))

        hsize = max(1, min(int(hsize), width - hpos))
        vsize = max(1, min(int(vsize), height - vpos))

        return frame[vpos:vpos + vsize, hpos:hpos + hsize]

    def getExposure(self):
        """Return exposure time in microseconds."""
        exposure_ms = self.parameters["exposure"].value
        return int(exposure_ms * 1000)

    def getExposure(self):
        """Return exposure time in microseconds."""
        exposure_ms = self.parameters["exposure"].value
        return int(exposure_ms * 1000)

    def _setExposureMs(self, exposure_ms):
        """Set Blackfly exposure time from milliseconds."""
        exposure_us = float(exposure_ms) * 1000.0

        try:
            self.cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
        except PySpin.SpinnakerException as ex:
            self.__logger.warning(f"Could not disable auto exposure: {ex}")

        try:
            min_us = self.cam.ExposureTime.GetMin()
            max_us = self.cam.ExposureTime.GetMax()

            exposure_us = max(min_us, min(exposure_us, max_us))

            self.cam.ExposureTime.SetValue(exposure_us)

            self.__logger.info(
                f"Blackfly exposure set to {exposure_us / 1000.0:.3f} ms"
            )

        except PySpin.SpinnakerException as ex:
            self.__logger.warning(f"Could not set Blackfly exposure: {ex}")

    def _setGain(self, gain):
        """Set Blackfly gain."""
        gain_value = float(gain)

        try:
            self.cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        except PySpin.SpinnakerException as ex:
            self.__logger.warning(f"Could not disable auto gain: {ex}")

        try:
            min_gain = self.cam.Gain.GetMin()
            max_gain = self.cam.Gain.GetMax()

            try:
                unit = self.cam.Gain.GetUnit()
            except Exception:
                unit = "unknown"

            self.__logger.info(
                f"Blackfly gain range: min={min_gain:.3f}, max={max_gain:.3f}, unit={unit}"
            )

            gain_value = max(min_gain, min(gain_value, max_gain))

            self.cam.Gain.SetValue(gain_value)

            actual_gain = self.cam.Gain.GetValue()

            self.__logger.info(
                f"Blackfly gain requested {float(gain):.3f}, set to {actual_gain:.3f} {unit}"
            )

        except PySpin.SpinnakerException as ex:
            self.__logger.warning(f"Could not set Blackfly gain: {ex}")

    def setParameter(self, name, value):
        """Update an ImSwitch detector parameter and apply it to the camera."""
        parameters = super().setParameter(name, value)

        self.__logger.info(f"Blackfly parameter changed: {name} = {value}")

        if name == "exposure":
            self._setExposureMs(value)

        elif name == "gain":
            self._setGain(value)

        return parameters


    def _getFallbackFrame(self):
        """Return a valid fallback frame so ImSwitch never receives None."""
        if self._latest_frame is not None:
            return self._latest_frame

        width, height = self._fullShape
        return np.zeros((height, width), dtype=np.uint16)

    def getLatestFrame(self, is_save=False):
        """Return the latest frame from the Blackfly camera.

        During LiveView, frames are continuously acquired from the camera.
        During Snap, ImSwitch calls this method with is_save=True. In that case,
        we return the latest good LiveView frame, cropped to the current ROI.
        """
        self.imageAcqLastFailed = False
        image = None

        if is_save and self._latest_frame is not None:
            # The latest live frame has already been cropped if an ROI is active.
            # Do not apply the software crop again here, otherwise Snap crops twice.
            frame_to_save = self._latest_frame

            self.__logger.info(
                "Saving latest live frame: "
                f"shape={frame_to_save.shape}, "
                f"min={frame_to_save.min()}, "
                f"max={frame_to_save.max()}, "
                f"mean={frame_to_save.mean():.2f}"
            )

            return frame_to_save.copy()

        try:
            if not self.cam.IsStreaming():
                self.startAcquisition()

            image = self.cam.GetNextImage(int(1000 * self.timeout))

            if image.IsIncomplete():
                print(
                    "ERROR ! : Image incomplete with image status %d ..."
                    % image.GetImageStatus()
                )
                self.imageAcqLastFailed = True
                return False

            full_frame = image.GetNDArray().copy()
            self.frame = self._applySoftwareCrop(full_frame)
            self._latest_frame = self.frame

            return self.frame

        except PySpin.SpinnakerException as ex:
            print("ERROR : %s" % ex)
            print("Failed to grab array from camera : probably Timeout")
            self.imageAcqLastFailed = True
            return False

        finally:
            if image is not None:
                image.Release()

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