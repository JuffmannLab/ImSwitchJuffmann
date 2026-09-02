import numpy as np
from qtpy import QtWidgets, QtCore

from imswitch.imcommon.model import shortcut
from imswitch.imcommon.view.guitools import naparitools


class ImageWidget(QtWidgets.QWidget):
    """Widget containing viewbox that displays the new detector frames."""
    sigCrosshairPlaced = QtCore.Signal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        naparitools.addNapariGrayclipColormap()
        self.napariViewer = naparitools.EmbeddedNapari()
        self.updateLevelsWidget = naparitools.NapariUpdateLevelsWidget.addToViewer(
            self.napariViewer
        )
        self.NapariShiftWidget = naparitools.NapariShiftWidget.addToViewer(self.napariViewer)
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

        # Track crosshair visibility so we only react to clicks when it's on
        self._crosshairVisible = False

        # Print crosshair position on mouse release when crosshair is visible
        # Note: left mouse button is event.button == 1 in vispy
        self.napariViewer.window.qt_viewer.canvas.events.mouse_release.connect(
            self._on_canvas_mouse_release
        )

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
                    addImage(name, 'viridis')

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

    def setImageDisplayLevels(self, name, minimum, maximum):
        self.imgLayers[name].contrast_limits = (minimum, maximum)

    def getCenterViewbox(self):
        """Returns the center point of the viewbox, as an (x, y) tuple."""
        return (
            self.napariViewer.window.qt_viewer.camera.center[2],
            self.napariViewer.window.qt_viewer.camera.center[1]
        )

    def updateGrid(self, imShape):
        self.grid.update(imShape)

    def setGridVisible(self, visible):
        self.grid.setVisible(visible)

    def setCrosshairVisible(self, visible):
        self._crosshairVisible = visible
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

    def _on_canvas_mouse_release(self, event):
        """Print crosshair position on left-click when crosshair is visible."""
        if not self._crosshairVisible:
            return
        # Left mouse button is 1 in vispy
        if getattr(event, "button", None) != 1:
            return

        try:
            pos = self.napariViewer.window.qt_viewer.viewer.cursor.position
            self.sigCrosshairPlaced.emit(pos)
        except AttributeError:
            return