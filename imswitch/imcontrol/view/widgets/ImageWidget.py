import numpy as np
from qtpy import QtWidgets

from imswitch.imcommon.model import shortcut
from imswitch.imcommon.view.guitools import naparitools


class ImageWidget(QtWidgets.QWidget):
    """ Widget containing viewbox that displays the new detector frames. """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        naparitools.addNapariGrayclipColormap()
        self.napariViewer = naparitools.EmbeddedNapari()
        self.updateLevelsWidget = naparitools.NapariUpdateLevelsWidget.addToViewer(
            self.napariViewer
        )
        self.NapariShiftWidget = naparitools.NapariShiftWidget.addToViewer(self.napariViewer)
        self.NapariColorbarWidget = naparitools.NapariColorbarWidget.addToViewer(self.napariViewer)
        self.imgLayers = {}

        self.viewCtrlLayout = QtWidgets.QVBoxLayout()
        self.viewCtrlLayout.addWidget(self.napariViewer.get_widget())
        self.setLayout(self.viewCtrlLayout)

        self.grid = naparitools.VispyGridVisual(color='yellow')
        self.grid.hide()
        self.addItem(self.grid)

        self.crosshair = naparitools.VispyCrosshairVisual(color='yellow')
        self.crosshair.hide()
        self.addItem(self.crosshair)

    def setLiveViewLayers(self, names):
        for name, img in self.imgLayers.items():
            if name not in names:
                self.napariViewer.layers.remove(img, force=True)

        def addImage(name, colormap=None):
            self.imgLayers[name] = self.napariViewer.add_image(
                np.zeros((1, 1)), rgb=False, name=f'Live: {name}', blending='additive',
                colormap=colormap, protected=True
            )

        for name in names:
            if name not in self.napariViewer.layers:
                try:
                    addImage(name, name.lower())
                except KeyError:
                    addImage(name, 'grayclip')

    def addStaticLayer(self, name, im):
        self.napariViewer.add_image(im, rgb=False, name=name, blending='additive')

    def getCurrentImageName(self):
        return self.napariViewer.active_layer.name

    def getImage(self, name):
        return self.imgLayers[name].data

    def setImage(self, name, im):
        self.imgLayers[name].data = im

    def clearImage(self, name):
        self.setImage(name, np.zeros((1, 1)))

    def getImageDisplayLevels(self, name):
        return self.imgLayers[name].contrast_limits

    def setLayerScale(self, name, scale):
        """ Displayed size of one pixel of this layer (same in x and y). """
        self.imgLayers[name].scale = (scale, scale)

    def updateGridLayout(self):
        """ Recomputes the positions of the layers in grid mode; napari only does that when the
        grid or the layer order changes, not when the size of an image changes. """
        if self.napariViewer.grid.enabled:
            self.napariViewer._on_grid_change()

    def getLayerScale(self, name):
        return float(self.imgLayers[name].scale[-1])

    def setGridEnabled(self, enabled):
        """ Shows the layers next to each other instead of on top of each other. """
        self.napariViewer.grid.enabled = enabled

    def _layerOffset(self, name):
        """ (x, y) offset of the layer on the canvas: its translation plus its grid position. """
        layer = self.imgLayers[name]
        offset = np.asarray(layer.translate, dtype=float)[-2:] + \
            np.asarray(layer._translate_grid, dtype=float)[-2:]
        return offset[1], offset[0]

    def pixelToScene(self, name, x, y):
        """ Converts a pixel position (x = column, y = row) of this layer to the canvas
        coordinates used by the ROI items. """
        s = self.getLayerScale(name)
        ox, oy = self._layerOffset(name)
        return (x - 0.5) * s + ox + 0.5, (y - 0.5) * s + oy + 0.5

    def sceneToPixel(self, name, x, y):
        """ Inverse of pixelToScene. """
        s = self.getLayerScale(name)
        ox, oy = self._layerOffset(name)
        return (x - 0.5 - ox) / s + 0.5, (y - 0.5 - oy) / s + 0.5

    def setImageDisplayLevels(self, name, minimum, maximum):
        # Set the slider range to the current image as well, otherwise it stays at the range
        # of the previous images when switching between live view and differential view
        layer = self.imgLayers[name]
        data = np.asarray(layer.data)
        finite = data[np.isfinite(data)] if data.dtype.kind == 'f' else data
        if finite.size > 0:
            layer.contrast_limits_range = (min(minimum, float(finite.min())),
                                           max(maximum, float(finite.max())))
        layer.contrast_limits = (minimum, maximum)

    def getCenterViewbox(self):
        """ Returns the center point of the viewbox, as an (x, y) tuple. """
        return (
            self.napariViewer.window.qt_viewer.camera.center[2],
            self.napariViewer.window.qt_viewer.camera.center[1]
        )

    def updateGrid(self, imShape):
        self.grid.update(imShape)

    def setGridVisible(self, visible):
        self.grid.setVisible(visible)

    def setCrosshairVisible(self, visible):
        self.crosshair.setVisible(visible)

    def resetView(self):
        self.napariViewer.reset_view()

    def addItem(self, item):
        item.attach(self.napariViewer,
                    canvas=self.napariViewer.window.qt_viewer.canvas,
                    view=self.napariViewer.window.qt_viewer.view,
                    parent=self.napariViewer.window.qt_viewer.view.scene,
                    order=1e6 + 8000)

    def removeItem(self, item):
        item.detach()

    @shortcut('Ctrl+U', "Update levels")
    def updateLevelsButton(self):
        self.updateLevelsWidget.updateLevelsButton.click()


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
