import numpy as np

from ..basecontrollers import LiveUpdatedController


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

        height, width = image.shape[:2]

        # Average over a thin central band to reduce noise slightly.
        band_half_width = 2

        if self.profileMode == "horizontal":
            # Horizontal line profile:
            # x-axis = x pixel, y-axis = gray value around the central row.
            center_y = height // 2
            y0 = max(0, center_y - band_half_width)
            y1 = min(height, center_y + band_half_width + 1)

            profile = np.mean(image[y0:y1, :], axis=0)

        else:
            # Vertical line profile:
            # x-axis = y pixel, y-axis = gray value around the central column.
            center_x = width // 2
            x0 = max(0, center_x - band_half_width)
            x1 = min(width, center_x + band_half_width + 1)

            profile = np.mean(image[:, x0:x1], axis=1)

        self._widget.updateGraph(profile)

    def addROI(self):
        """Add ROI to the image viewbox."""
        if not self.roiAdded:
            self._commChannel.sigAddItemToVb.emit(
                self._widget.getROIGraphicsItem()
            )
            self.roiAdded = True

    def toggleROI(self, show):
        """Enable or disable the live profile plot."""
        self.active = show

    def setProfileMode(self, mode):
        """Set horizontal or vertical profile mode."""
        self.profileMode = mode

    def getCroppedImage(self, image, roiItem):
        """Return the cropped image within the ROI.

        This follows the existing ImSwitch AlignXY/AlignAverage ROI convention.
        """
        x0, y0, x1, y1 = roiItem.bounds

        x0 = int(x0)
        y0 = int(y0)
        x1 = int(x1)
        y1 = int(y1)

        height, width = image.shape[:2]

        x0 = max(0, min(x0, height))
        x1 = max(0, min(x1, height))
        y0 = max(0, min(y0, width))
        y1 = max(0, min(y1, width))

        if x1 <= x0 or y1 <= y0:
            return image[0:0, 0:0]

        return image[x0:x1, y0:y1]