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
        """Return the cropped image within the LiveProfile ROI."""
        x0, y0, x1, y1 = roiItem.bounds

        x0 = int(round(x0))
        y0 = int(round(y0))
        x1 = int(round(x1))
        y1 = int(round(y1))

        height, width = image.shape[:2]

        x0 = max(0, min(x0, width))
        x1 = max(0, min(x1, width))
        y0 = max(0, min(y0, height))
        y1 = max(0, min(y1, height))

        if x1 <= x0 or y1 <= y0:
            return image[0:0, 0:0]

        return image[y0:y1, x0:x1]