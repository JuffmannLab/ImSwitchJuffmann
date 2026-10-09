from imswitch.imcommon.model import APIExport
from ..basecontrollers import ImConWidgetController


class ViewController(ImConWidgetController):
    """ Linked to ViewWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lvacqHandle = None
        self._dvacqHandle = None
        self._dvBeforeRecording = False

        self._widget.setViewToolsEnabled(False, 'LV')

        # DV and recording both take frames from the camera buffer, so DV is switched to LV
        # during a recording and back afterwards
        self._commChannel.sigRecordingStarting.connect(self.recordingStarting)
        self._commChannel.sigRecordingEnded.connect(self.recordingEnded)

        # Connect ViewWidget signals
        self._widget.sigGridToggled.connect(self.gridToggle)
        self._widget.sigCrosshairToggled.connect(self.crosshairToggle)
        self._widget.sigLiveviewToggled.connect(self.liveview)
        self._widget.sigDifferentialviewToggled.connect(self.differentialview)
        self._widget.sigSliderValueChanged.connect(self.sliderValue)

    def liveview(self, enabled):
        """ Called when the LiveView button is toggled. Starting LiveView while
        the Differential View is running switches from DV to LV. """
        if enabled:
            # Start LV before stopping DV so the camera keeps running
            self._startLiveView()
            if self._dvacqHandle is not None:
                self._stopDifferentialView()
                self._widget.setDifferentialViewChecked(False)
        else:
            self._stopLiveView()

    def differentialview(self, enabled):
        """ Called when the Differential View button is toggled. Starting DV
        switches from LV to DV, stopping DV switches back to LV. """
        if enabled:
            # Start DV before stopping LV so the camera keeps running
            self._startDifferentialView()
            if self._lvacqHandle is not None:
                self._stopLiveView()
                self._widget.setLiveViewChecked(False)
        else:
            self._startLiveView()
            self._stopDifferentialView()
            self._widget.setLiveViewChecked(True)

    def recordingStarting(self):
        """ Switches from DV to LV before a recording starts and blocks DV during it. """
        if self._dvacqHandle is not None:
            self._dvBeforeRecording = True
            self._widget.setLiveViewActive(True)  # runs liveview(True), which stops DV
        self._widget.setDifferentialViewEnabled(False)

    def recordingEnded(self):
        """ Re-enables DV after a recording and switches back to it if it was active before. """
        self._widget.setDifferentialViewEnabled(True)
        if self._dvBeforeRecording:
            self._dvBeforeRecording = False
            if self._lvacqHandle is not None:  # LV wasn't stopped by the user in the meantime
                self._widget.setDifferentialViewActive(True)  # runs differentialview(True)

    def _startLiveView(self):
        if self._lvacqHandle is None:
            self._lvacqHandle = self._master.detectorsManager.execOnAll(
                lambda c: self._master.detectorsManager.startDetectorAcquisition(c, liveView=True),
                condition=lambda c: c.forAcquisition
            )

    def _stopLiveView(self):
        if self._lvacqHandle is not None:
            self._master.detectorsManager.execOnAll(
                lambda c: self._master.detectorsManager.stopDetectorAcquisition(c, self._lvacqHandle, liveView=True),
                condition=lambda c: c.forAcquisition
            )
            self._lvacqHandle = None

    def _startDifferentialView(self):
        if self._dvacqHandle is None:
            self._dvacqHandle = self._master.detectorsManager.execOnAll(
                lambda c: self._master.detectorsManager.startDetectorAcquisition(c, differentialView=True),
                condition=lambda c: c.forDifferential
            )

    def _stopDifferentialView(self):
        if self._dvacqHandle is not None:
            self._master.detectorsManager.execOnAll(
                lambda c: self._master.detectorsManager.stopDetectorAcquisition(c, self._dvacqHandle, differentialView=True),
                condition=lambda c: c.forDifferential
            )
            self._dvacqHandle = None


    def sliderValue(self, batch_size):
        self._master.detectorsManager.adjustBatchSize(batch_size)

    def gridToggle(self, enabled):
        """ Connect with grid toggle from Image Widget through communication channel. """
        self._commChannel.sigGridToggled.emit(enabled)

    def crosshairToggle(self, enabled):
        """ Connect with crosshair toggle from Image Widget through communication channel. """
        self._commChannel.sigCrosshairToggled.emit(enabled)

    def closeEvent(self):
        """ Stops both live view and differential view acquisitions if active. """
        self._stopLiveView()
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

    @APIExport(runOnUIThread=True)
    def setLiveViewGridVisible(self, visible: bool) -> None:
        """ Sets whether the LiveView grid is visible. """
        self._widget.setLiveViewGridVisible(visible)

    @APIExport(runOnUIThread=True)
    def setLiveViewCrosshairVisible(self, visible: bool) -> None:
        """ Sets whether the LiveView crosshair is visible. """
        self._widget.setLiveViewCrosshairVisible(visible)


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
