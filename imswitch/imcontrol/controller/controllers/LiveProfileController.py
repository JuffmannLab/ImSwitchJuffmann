import numpy as np
from ..basecontrollers import LiveUpdatedController
from imswitch.imcontrol.model.liveprofile_state import liveprofile_state
from scipy.ndimage import map_coordinates

class LiveProfileController(LiveUpdatedController):
    """Controller for the live intensity profile widget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("MARIA DEBUG: LiveProfileController was created")

        self.profileMode = "horizontal"
        self.roiAdded = {}

        # Receive live images
        self._commChannel.sigUpdateImage.connect(self.update)

        # Widget signals
        self._widget.sigShowROIToggled.connect(self.toggleROI)
        self._widget.sigAxisChanged.connect(self.setProfileMode)

    def _getDetectorYOffset(self, detectorName):
        """Return the vertical display offset of a detector."""
        margin = 20
        y_offset = 0

        detectorNames = self._master.detectorsManager.getAllDeviceNames(
            lambda c: c.forAcquisition
        )

        for name in detectorNames:
            if name == detectorName:
                return y_offset

            detector = self._master.detectorsManager[name]
            y_offset += detector.shape[1] + margin

        return 0

    def update(self, detectorName, im, init, isCurrentDetector):
        """Update profile plot with the current detector frame."""
        if not isCurrentDetector:
            return

        if not self.active:
            return

        image = np.asarray(im)

        if image.size == 0:
            return

        if image.ndim == 3:
            image = image.mean(axis=2)

        roiItem = self._widget.getROIGraphicsItem(detectorName)
        yOffset = self._getDetectorYOffset(detectorName)

        cropped = self.getCroppedImage(
            image,
            roiItem,
            yOffset
        )

        if cropped.size == 0:
            return

        height, width = cropped.shape[:2]

        # Average over a thin central band to reduce noise slightly.
        band_half_width = 2

        if self.profileMode == "horizontal":
            # Horizontal profile inside the ROI.
            center_y = height // 2
            y0 = max(0, center_y - band_half_width)
            y1 = min(height, center_y + band_half_width + 1)

            profile = np.mean(cropped[y0:y1, :], axis=0)

        else:
            # Vertical profile inside the ROI.
            center_x = width // 2
            x0 = max(0, center_x - band_half_width)
            x1 = min(width, center_x + band_half_width + 1)

            profile = np.mean(cropped[:, x0:x1], axis=1)

        liveprofile_state.update(
            profile=profile,
            roi_image=cropped,
            profile_mode=self.profileMode
        )
        
        self._widget.updateGraph(profile)

    def addROI(self, detectorName):
        """Add the ROI for one detector to the image viewbox."""
        if not self.roiAdded.get(detectorName, False):
            self._commChannel.sigAddItemToVb.emit(
                self._widget.getROIGraphicsItem(detectorName)
            )
            self.roiAdded[detectorName] = True

    def toggleROI(self, show):
        """Enable or disable the live profile and show one ROI per detector."""

        detectorNames = self._master.detectorsManager.getAllDeviceNames(
            lambda c: c.forAcquisition
        )

        for detectorName in detectorNames:
            if show:
                self.addROI(detectorName)

                detector = self._master.detectorsManager[detectorName]
                width, height = detector.shape

                # Keep the initial ROI inside the detector image,
                # even if the detector is currently cropped.
                roiWidth = min(256, width)
                roiHeight = min(256, height)
                roiSize = (roiWidth, roiHeight)

                yOffset = self._getDetectorYOffset(detectorName)

                # ROI coordinates are (x, y).
                # Center it inside this detector's displayed image.
                roiPos = (
                    0.5 * (width - roiWidth),
                    yOffset + 0.5 * (height - roiHeight),
                )

                self._widget.showROI(
                    detectorName,
                    roiPos,
                    roiSize
                )

            else:
                self._widget.hideROI(detectorName)

        self.active = show

    def setProfileMode(self, mode):
        """Set horizontal or vertical profile mode."""
        self.profileMode = mode

    def getCroppedImage(self, image, roiItem, yOffset=0):
        """Return the image data inside the possibly rotated LiveProfile ROI.

        The ROI lives in the global viewer coordinates, while the detector image
        starts at its own vertical display offset. Subtract that offset before
        sampling the detector image.
        """
        roi_position = np.asarray(roiItem.position, dtype=float).copy()
        roi_size = np.asarray(roiItem.size, dtype=float)
        roi_center = np.asarray(roiItem.center, dtype=float).copy()
        roi_angle = float(getattr(roiItem, "angle", 0.0))

        # Vispy ROI coordinates are (x, y), so the vertical offset is component 1.
        roi_position[1] -= yOffset
        roi_center[1] -= yOffset

        width = int(round(roi_size[0]))
        height = int(round(roi_size[1]))

        if width <= 0 or height <= 0:
            return image[0:0, 0:0]

        # Coordinates in the local, unrotated ROI system.
        local_x = roi_position[0] + np.arange(width) + 0.5
        local_y = roi_position[1] + np.arange(height) + 0.5
        local_x_grid, local_y_grid = np.meshgrid(local_x, local_y)

        # Rotate local ROI coordinates into image coordinates.
        angle_rad = np.deg2rad(roi_angle)
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        shifted_x = local_x_grid - roi_center[0]
        shifted_y = local_y_grid - roi_center[1]

        image_x = shifted_x * cos_a - shifted_y * sin_a + roi_center[0]
        image_y = shifted_x * sin_a + shifted_y * cos_a + roi_center[1]

        # map_coordinates expects coordinates in row/column order: y, x.
        cropped = map_coordinates(
            image,
            [image_y, image_x],
            order=1,
            mode="constant",
            cval=0.0
        )

        return cropped