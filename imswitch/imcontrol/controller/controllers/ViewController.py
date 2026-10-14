from imswitch.imcommon.model import APIExport, initLogger
from ..basecontrollers import ImConWidgetController


class ViewController(ImConWidgetController):
    """ Linked to ViewWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        # Acquisition handles per camera, {detectorName: handle}. Differential View only runs
        # on the cameras marked forDifferential; all other cameras stay in LiveView.
        self._lvHandles = {}
        self._dvHandles = {}
        self._dvBeforeRecording = False
        # Cameras in the pseudo flat field view: LiveView with the background subtracted
        self._pffNames = set()

        self._widget.setViewToolsEnabled(False, 'LV')

        # DV and recording both take frames from the camera buffer, so the DV cameras are
        # switched to LV during a recording and back afterwards
        self._commChannel.sigRecordingStarting.connect(self.recordingStarting)
        self._commChannel.sigRecordingEnded.connect(self.recordingEnded)

        # Connect ViewWidget signals
        self._widget.sigLiveviewToggled.connect(self.liveview)
        self._widget.sigDifferentialviewToggled.connect(self.differentialview)
        self._widget.sigPseudoFlatFieldToggled.connect(self.pseudoflatfield)
        self._widget.sigSliderValueChanged.connect(self.sliderValue)

    def liveview(self, enabled):
        """ Called when the LiveView button is toggled. Starts/stops LiveView on all
        acquisition cameras that are not in Differential View. """
        if enabled:
            self._startLiveView(self._lvNames())
        else:
            # The cameras in the pseudo flat field view keep running
            self._stopLiveView([name for name in self._lvHandles if name not in self._pffNames])

    def differentialview(self, enabled):
        """ Called when the Differential View button is toggled. Switches the forDifferential
        cameras from LV to DV and back; the other cameras keep running in LV. """
        dvNames = self._dvNames()
        if enabled:
            # DV replaces the pseudo flat field view on the same camera
            self._stopPseudoFlatField([name for name in dvNames if name in self._pffNames],
                                      stopLiveView=False)
            # Start DV before stopping LV so the camera keeps running
            self._startDifferentialView(dvNames)
            self._stopLiveView(dvNames)
        else:
            # Back to LV if the LiveView is on
            if self._widget.getLiveViewActive():
                self._startLiveView(self._acqNames(dvNames))
            self._stopDifferentialView()

    def pseudoflatfield(self, enabled):
        """ Called when the Pseudo Flat Field button is toggled. The forPseudoFlatFielding
        cameras with a background (PseudoFlatField widget) show the live image minus the
        background; the other cameras are not affected. """
        detectorsManager = self._master.detectorsManager
        if enabled:
            candidates = self._acqNames(
                detectorsManager.getAllDeviceNames(lambda c: c.forPseudoFlatFielding))
            names = [name for name in candidates if detectorsManager.hasFlatField(name)]
            if not names:
                self._widget.setPseudoFlatFieldChecked(False)
                self._widget.showMessage(
                    'Pseudo Flat Field',
                    'No background loaded. Create or load a median background in the '
                    'Pseudo Flat Field widget first.')
                return
            missing = [name for name in candidates if name not in names]
            if missing:
                self.__logger.warning(f'No flat field background for {missing}')
            # DV and the pseudo flat field view exclude each other on the same camera
            if any(name in self._dvHandles for name in names):
                self._widget.setDifferentialViewChecked(False)
                self.differentialview(False)
            for name in names:
                detectorsManager.setFlatFieldActive(name, True)
            self._pffNames.update(names)
            self._startLiveView(names)
        else:
            self._stopPseudoFlatField(list(self._pffNames),
                                      stopLiveView=not self._widget.getLiveViewActive())

    def _stopPseudoFlatField(self, names, stopLiveView):
        """ Switches the background subtraction off for the given cameras; their LiveView is
        stopped if stopLiveView. """
        for name in names:
            self._master.detectorsManager.setFlatFieldActive(name, False)
            self._pffNames.discard(name)
        if stopLiveView:
            self._stopLiveView(names)
        if not self._pffNames:
            self._widget.setPseudoFlatFieldChecked(False)

    def recordingStarting(self):
        """ Switches the DV cameras to LV before a recording starts and blocks DV during it. """
        if self._dvHandles:
            self._dvBeforeRecording = True
            dvNames = list(self._dvHandles)
            self._startLiveView(self._acqNames(dvNames))
            self._stopDifferentialView()
            self._widget.setDifferentialViewChecked(False)
        self._widget.setDifferentialViewEnabled(False)

    def recordingEnded(self):
        """ Re-enables DV after a recording and switches back to it if it was active before. """
        self._widget.setDifferentialViewEnabled(True)
        if self._dvBeforeRecording:
            self._dvBeforeRecording = False
            # Only if the LiveView wasn't stopped by the user in the meantime
            if any(name in self._lvHandles for name in self._dvNames()):
                self._widget.setDifferentialViewActive(True)  # runs differentialview(True)

    def _dvNames(self):
        return self._master.detectorsManager.getAllDeviceNames(lambda c: c.forDifferential)

    def _acqNames(self, names):
        """ The given cameras that are used for acquisition, i.e. can run in LiveView. """
        acqNames = self._master.detectorsManager.getAllDeviceNames(lambda c: c.forAcquisition)
        return [name for name in names if name in acqNames]

    def _lvNames(self):
        """ Acquisition cameras that are not in Differential View. """
        return [name for name in self._acqNames(
                    self._master.detectorsManager.getAllDeviceNames())
                if name not in self._dvHandles]

    def _startLiveView(self, names):
        self._lvHandles.update(self._startOnDetectors(
            [name for name in names if name not in self._lvHandles], liveView=True))

    def _stopLiveView(self, names):
        self._stopOnDetectors({name: self._lvHandles.pop(name)
                               for name in names if name in self._lvHandles}, liveView=True)

    def _startDifferentialView(self, names):
        self._dvHandles.update(self._startOnDetectors(
            [name for name in names if name not in self._dvHandles], differentialView=True))

    def _stopDifferentialView(self):
        handles, self._dvHandles = self._dvHandles, {}
        self._stopOnDetectors(handles, differentialView=True)

    def _startOnDetectors(self, names, **kwargs):
        """ Starts the acquisition on the given detectors and returns the handles as
        {detectorName: handle}. A detector that fails to start is skipped, so the others still
        work and the view can be stopped again. """
        detectorsManager = self._master.detectorsManager
        handles = {}
        for name in names:
            try:
                handles[name] = detectorsManager.startDetectorAcquisition(
                    detectorsManager[name], **kwargs)
            except Exception as e:
                self.__logger.error(f'Could not start {name}: {e}')
        return handles

    def _stopOnDetectors(self, handles, **kwargs):
        """ Stops the acquisition started by _startOnDetectors on each of its detectors. """
        detectorsManager = self._master.detectorsManager
        for name, handle in handles.items():
            try:
                detectorsManager.stopDetectorAcquisition(detectorsManager[name], {name: handle},
                                                         **kwargs)
            except Exception as e:
                self.__logger.error(f'Could not stop {name}: {e}')

    def sliderValue(self, batch_size):
        self._master.detectorsManager.adjustBatchSize(batch_size)

    def closeEvent(self):
        """ Stops both live view and differential view acquisitions if active. """
        self._stopPseudoFlatField(list(self._pffNames), stopLiveView=False)
        self._stopLiveView(list(self._lvHandles))
        self._stopDifferentialView()

    def get_image(self, detectorName):
        if detectorName is None:
            return self._master.detectorsManager.execOnCurrent(lambda c: c.getLatestFrame())
        else:
            return self._master.detectorsManager[detectorName].getLatestFrame()

    @APIExport(runOnUIThread=True)
    def setLiveViewActive(self, active: bool) -> None:
        """ Sets whether the LiveView is active and updating. """
        self._widget.setLiveViewActive(active)

    @APIExport(runOnUIThread=True)
    def setDifferentialViewActive(self, active: bool) -> None:
        self._widget.setDifferentialViewActive(active)


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
