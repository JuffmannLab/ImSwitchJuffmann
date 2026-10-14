from imswitch.imcontrol.view import guitools
from ..basecontrollers import LiveUpdatedController
from imswitch.imcommon.model import initLogger
import numpy as np

class ImageController(LiveUpdatedController):
    """ Linked to ImageWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__logger = initLogger(self, tryInheritParent=True)
        if not self._master.detectorsManager.hasDevices():
            return

        self._lastShape = self._master.detectorsManager.execOnCurrent(lambda c: c.shape)
        self._shouldResetView = False

        # create live view layer for detectors which have the Attribute forAcquisition
        liveNames = self._master.detectorsManager.getAllDeviceNames(lambda c: c.forAcquisition)
        self._widget.setLiveViewLayers(liveNames)

        # Display scale of the cameras: with "pixelSizeUm" (effective pixel size at the sample)
        # in the managerProperties of all cameras, the images are shown in the same physical
        # scale; otherwise every image is shown with the same width. Image shapes per camera,
        # the scales are updated when a shape changes (e.g. new ROI).
        self._pixelSizes = {name: self._setupInfo.detectors[name].managerProperties.get('pixelSizeUm')
                            for name in liveNames}
        self._imageShapes = {}
        # Several cameras are shown next to each other (napari grid mode, can be toggled with
        # the grid button of the layer list)
        if len(liveNames) > 1:
            self._widget.setGridEnabled(True)

        # Connect CommunicationChannel signals
        self._commChannel.sigUpdateImage.connect(self.update)
        self._commChannel.sigAdjustFrame.connect(self.adjustFrame)
        self._commChannel.sigGridToggled.connect(self.gridToggle)
        self._commChannel.sigCrosshairToggled.connect(self.crosshairToggle)
        self._commChannel.sigAddItemToVb.connect(self.addItemToVb)
        self._commChannel.sigRemoveItemFromVb.connect(self.removeItemFromVb)
        self._commChannel.sigMemorySnapAvailable.connect(self.memorySnapAvailable)
        self._commChannel.sigSetExposure.connect(lambda t: self.setExposure(t))

    def autoLevels(self, detectorNames=None, im=None):
        """ Set histogram levels automatically with current detector image."""
        if detectorNames is None:
            detectorNames = self._master.detectorsManager.getAllDeviceNames(
                lambda c: c.forAcquisition
            )

        for detectorName in detectorNames:
            if im is None:
                im = self._widget.getImage(detectorName)

            # self._widget.setImageDisplayLevels(detectorName, *guitools.bestLevels(im))
            self._widget.setImageDisplayLevels(detectorName, *guitools.minmaxLevels(im))

    def addItemToVb(self, item):
        """ Add item from communication channel to viewbox."""
        item.hide()
        self._widget.addItem(item)

    def removeItemFromVb(self, item):
        """ Remove item from communication channel to viewbox."""
        self._widget.removeItem(item)

    def update(self, detectorName, im, init, isCurrentDetector):
        """ Update new image in the viewbox. """
        if np.prod(im.shape)>1: # TODO: This seems weird!

            # init is False for the first frame of the live view/differential view: only then
            # the levels are set automatically, so they can be adjusted by hand afterwards
            self._widget.setImage(detectorName, im)

            if self._imageShapes.get(detectorName) != im.shape[:2]:
                self._imageShapes[detectorName] = im.shape[:2]
                self._updateLayerScales()
                self._shouldResetView = True

            if not init or self._outsideLevels(detectorName, im):
                self.autoLevels([detectorName], im)

            if not init or self._shouldResetView:
                self.adjustFrame(instantResetView=True)

    def adjustFrame(self, shape=None, instantResetView=False):
        """ Adjusts the viewbox to a new width and height. """

        if shape is None:
            shape = self._lastShape

        self._widget.updateGrid(shape)
        if instantResetView:
            self._widget.resetView()
            self._shouldResetView = False
        else:
            self._shouldResetView = True

        self._lastShape = shape

    def _outsideLevels(self, detectorName, im):
        """ Whether the image no longer fits the displayed levels after the illumination changed:
        most of it above/below the levels (overexposed/black), or the brightest pixels using less
        than a quarter of the level range (very dim). The levels are then set again. """
        low, high = self._widget.getImageDisplayLevels(detectorName)
        sample = np.asarray(im)[::4, ::4]
        if low < 0 < high:
            # Symmetric levels of differential images: values much smaller than the levels
            # (e.g. after a strong first image) or mostly outside them
            m = max(-low, high)
            strength = float(np.percentile(np.abs(sample), 99.9))
            return strength < 0.25 * m or float(np.median(np.abs(sample))) > m
        median = float(np.median(sample))
        if median > high or median < low:
            return True
        return float(np.percentile(sample, 99.9)) < low + 0.25 * (high - low)

    def _updateLayerScales(self):
        """ Sets the display scale of all live layers that have an image (see __init__). The
        smallest scale is 1, so canvas units are never larger than a pixel (ROI items use
        integer canvas coordinates). """
        names = [name for name in self._imageShapes if name in self._pixelSizes]
        if not names:
            return
        if all(self._pixelSizes[name] for name in names):
            sizes = {name: float(self._pixelSizes[name]) for name in names}
        else:
            # Same displayed width: the size of a pixel is 1 / image width
            sizes = {name: 1 / self._imageShapes[name][1] for name in names}
        smallest = min(sizes.values())
        for name in names:
            self._widget.setLayerScale(name, sizes[name] / smallest)
        self._widget.updateGridLayout()

    def pixelToScene(self, detectorName, x, y):
        """ Pixel position of a detector image -> canvas coordinates of the ROI items. """
        return self._widget.pixelToScene(detectorName, x, y)

    def sceneToPixel(self, detectorName, x, y):
        """ Canvas coordinates of the ROI items -> pixel position of a detector image. """
        return self._widget.sceneToPixel(detectorName, x, y)

    def getDisplayScale(self, detectorName):
        """ Displayed size (canvas units) of one pixel of a detector image. """
        return self._widget.getLayerScale(detectorName)

    def getCenterViewbox(self):
        """ Returns center of viewbox to center a ROI. """
        return self._widget.getCenterViewbox()

    def gridToggle(self, enabled):
        """ Shows or hides grid. """
        self._widget.setGridVisible(enabled)

    def crosshairToggle(self, enabled):
        """ Shows or hides crosshair. """
        self._widget.setCrosshairVisible(enabled)

    def memorySnapAvailable(self, name, image, _, __):
        """ Adds captured image to widget. """
        self._widget.addStaticLayer(name, image)
        if self._shouldResetView:
            self.adjustFrame(image.shape, instantResetView=True)

    def setExposure(self, exp):
        detectorName = self._master.detectorsManager.getAllDeviceNames()[0]
        self.__logger.debug(f"Change exposure of {detectorName}, to {str(exp)}")
        #self._master.detectorsManager[detectorName].setParameter('Readout time', exp)

# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
