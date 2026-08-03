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
        self.roiAdded = False

        # Receive live images
        self._commChannel.sigUpdateImage.connect(self.update)

        # Widget signals
        self._widget.sigShowROIToggled.connect(self.toggleROI)
        self._widget.sigAxisChanged.connect(self.setProfileMode)

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

        cropped = self.getCroppedImage(
            image,
            self._widget.getROIGraphicsItem()
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

    def addROI(self):
        """Add ROI to the image viewbox."""
        if not self.roiAdded:
            self._commChannel.sigAddItemToVb.emit(
                self._widget.getROIGraphicsItem()
            )
            self.roiAdded = True

    def toggleROI(self, show):
        """Enable or disable the live profile plot and show the ROI."""
        if show:
            self.addROI()

            roiSize = (256, 256)
            roiCenter = self._commChannel.getCenterViewbox()

            roiPos = (
                roiCenter[0] - 0.5 * roiSize[0],
                roiCenter[1] - 0.5 * roiSize[1],
            )

            self._widget.showROI(roiPos, roiSize)
        else:
            self._widget.hideROI()

        self.active = show
    def setProfileMode(self, mode):
        """Set horizontal or vertical profile mode."""
        self.profileMode = mode

    def getCroppedImage(self, image, roiItem):
        """Return the image data inside the possibly rotated LiveProfile ROI.

        The returned image is expressed in the local coordinate system of the
        ROI. This means that horizontal/vertical profiles are taken along the
        rotated ROI axes, not along the camera x/y axes.
        """
        roi_position = np.asarray(roiItem.position, dtype=float)
        roi_size = np.asarray(roiItem.size, dtype=float)
        roi_center = np.asarray(roiItem.center, dtype=float)
        roi_angle = float(getattr(roiItem, "angle", 0.0))

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