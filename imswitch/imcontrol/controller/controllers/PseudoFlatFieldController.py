import json
import os
import time

import numpy as np
import tifffile

from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.view import guitools
from ..basecontrollers import ImConWidgetController


class PseudoFlatFieldController(ImConWidgetController):
    """ Linked to PseudoFlatFieldWidget. Takes snaps of a camera marked forPseudoFlatFielding at
    manually chosen positions, builds their median and sets it as background of the pseudo flat
    field view (View widget: live image minus median). """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        self._snaps = []
        self._acqCamera = None
        self._acqHandle = None

        detectorsManager = self._master.detectorsManager
        names = detectorsManager.getAllDeviceNames(lambda c: c.forPseudoFlatFielding)
        if not names:
            self._widget.replaceWithError('No camera with "forPseudoFlatFielding": true in the '
                                          'setup file.')
            return
        self._widget.setCameras(names)

        self._widget.sigAcquisitionToggled.connect(self.acquisitionToggled)
        self._widget.sigSnap.connect(self.snap)
        self._widget.sigCreateMedian.connect(self.createMedian)
        self._widget.sigLoadMedian.connect(self.loadMedian)

    def acquisitionToggled(self, enabled):
        """ Starts collecting snaps (the previous ones are discarded) or stops it. The camera
        is kept running meanwhile, also without LiveView. """
        detectorsManager = self._master.detectorsManager
        if enabled:
            self._snaps = []
            self._widget.setImageCount(0)
            name = self._widget.getCamera()
            try:
                self._acqHandle = detectorsManager.startDetectorAcquisition(detectorsManager[name])
            except Exception as e:
                self.__logger.error(f'Could not start {name}: {e}')
                self._widget.setAcquisitionActive(False)
                self._widget.setStatus(f"<font color='red'>Could not start {name}: {e}</font>")
                return
            self._acqCamera = name
            self._widget.setAcquisitionActive(True)
            self._widget.setStatus('Move the stage, then click "Snap" or press the space bar. '
                                   'Click "Create median background" when done.')
        else:
            self._stopAcquisition()

    def _stopAcquisition(self):
        if self._acqHandle is not None:
            detectorsManager = self._master.detectorsManager
            try:
                detectorsManager.stopDetectorAcquisition(detectorsManager[self._acqCamera],
                                                         {self._acqCamera: self._acqHandle})
            except Exception as e:
                self.__logger.error(f'Could not stop {self._acqCamera}: {e}')
            self._acqHandle = None
        self._widget.setAcquisitionActive(False)

    def snap(self):
        """ Takes one image (average of "frames per snap" fresh frames) at the current position. """
        if self._acqHandle is None:
            return
        detector = self._master.detectorsManager[self._acqCamera]
        frames = []
        for _ in range(self._widget.getFramesPerSnap()):
            frame = detector.getLatestFrame(is_save=True)  # waits for a frame taken after the call
            if frame is None:
                self._widget.setStatus("<font color='red'>No frame from the camera</font>")
                return
            frames.append(np.asarray(frame, dtype=np.float32))
        image = np.mean(frames, axis=0)

        if self._snaps and image.shape != self._snaps[0].shape:
            self._widget.setStatus(f"<font color='red'>Image size changed "
                                   f"({image.shape} instead of {self._snaps[0].shape}), "
                                   f"snap discarded</font>")
            return
        self._snaps.append(image)
        self._widget.setImageCount(len(self._snaps))
        self._widget.setStatus(f'Snap {len(self._snaps)}: mean {image.mean():.1f}')

    def createMedian(self):
        """ Median of all snaps, saved in a timestamped folder and set as background. """
        if self._acqHandle is not None:
            self._stopAcquisition()
        if not self._snaps:
            self._widget.setStatus("<font color='red'>No images taken</font>")
            return

        name = self._acqCamera
        stack = np.stack(self._snaps)
        median = np.median(stack, axis=0).astype(np.float32)

        folder = os.path.join(self._widget.getBaseFolder(),
                              f'{time.strftime("%Y-%m-%d_%H-%M-%S")}_{name}')
        try:
            os.makedirs(folder, exist_ok=True)
            tifffile.imwrite(os.path.join(folder, 'median.tif'), median)
            tifffile.imwrite(os.path.join(folder, 'snaps.tif'), stack.astype(np.float32))
            detector = self._master.detectorsManager[name]
            with open(os.path.join(folder, 'info.json'), 'w') as f:
                json.dump({'camera': name, 'numberOfImages': len(self._snaps),
                           'framesPerSnap': self._widget.getFramesPerSnap(),
                           'shape': list(median.shape),
                           'frameStart': [int(v) for v in detector.frameStart],
                           'created': time.strftime('%Y-%m-%d %H:%M:%S')}, f, indent=4)
        except Exception as e:
            self.__logger.error(f'Could not save the median image: {e}')
            self._widget.setStatus(f"<font color='red'>Could not save: {e}</font>")
            return

        self.__logger.info(f'Median of {len(self._snaps)} images saved in {folder}')
        self._setBackground(name, median, os.path.join(folder, 'median.tif'))

    def loadMedian(self):
        """ Loads a saved median image as background. The camera is taken from info.json next
        to it, otherwise the selected camera is used. """
        path = guitools.askForFilePath(self._widget, 'Load median background',
                                       defaultFolder=self._widget.getBaseFolder(),
                                       nameFilter='TIFF (*.tif *.tiff)')
        if not path:
            return
        try:
            median = tifffile.imread(path).astype(np.float32)
        except Exception as e:
            self._widget.setStatus(f"<font color='red'>Could not load {path}: {e}</font>")
            return

        name = self._widget.getCamera()
        infoPath = os.path.join(os.path.dirname(path), 'info.json')
        if os.path.exists(infoPath):
            try:
                with open(infoPath) as f:
                    infoCamera = json.load(f).get('camera')
                if infoCamera in self._master.detectorsManager.getAllDeviceNames():
                    name = infoCamera
            except Exception as e:
                self.__logger.warning(f'Could not read {infoPath}: {e}')
        self._setBackground(name, median, path)

    def _setBackground(self, name, median, path):
        self._master.detectorsManager.setFlatField(name, median)
        shape = tuple(self._master.detectorsManager[name].shape)[::-1]  # (rows, cols)
        note = '' if tuple(median.shape) == shape else \
            (f"<br><font color='orange'>The current image size of {name} is {shape}; the "
             f"background is only subtracted from images of the same size.</font>")
        self._widget.setStatus(f'Background of {name}: {median.shape[1]} x {median.shape[0]} px'
                               f'<br>{path}{note}<br>Use "Pseudo Flat Field" in the View widget.')

    def closeEvent(self):
        self._stopAcquisition()


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
