from time import sleep

import numpy as np

from imswitch.imcommon.framework import Mutex, Signal, SignalInterface, Thread, Timer, Worker
from .MultiManager import MultiManager


class DetectorsManager(MultiManager, SignalInterface):
    """ 
    DetectorsManager is an interface for dealing with DetectorManagers. It
    is a MultiManager for detectors. Implemented Differential view in order to get the Chunks for the Batches
    directly from the camera which is faster than using the Live View image and save it in a deque data structure.
    """

    # Creating Signals
    sigAcquisitionStarted = Signal()
    sigAcquisitionStopped = Signal()
    sigDetectorSwitched = Signal(str, str)  # (newDetectorName, oldDetectorName)
    sigImageUpdated = Signal(
        str, np.ndarray, bool, bool
    )  # (detectorName, image, init, isCurrentDetector)

    def __init__(self, detectorInfos, updatePeriod, batch_size, **lowLevelManagers):
        MultiManager.__init__(self, detectorInfos, 'detectors', **lowLevelManagers)
        SignalInterface.__init__(self)

        self.batchSize = batch_size

        self._activeDetectorAcqHandles = {}
        self._activeDetectorAcqLVHandles = {}
        self._activeDetectorDVHandles = {}

        self._activeAcqHandles = []
        self._activeAcqLVHandles = []
        self._activeDVHandles = []
        self._activeAcqsMutex = Mutex()

        self._currentDetectorName = None
        for detectorName, detectorInfo in detectorInfos.items():
            if not self._subManagers[detectorName].forAcquisition and not self._subManagers[detectorName].forDifferential:
                continue
            # Connect signals
            self._subManagers[detectorName].sigImageUpdated.connect(
                lambda image, init, detectorName=detectorName: self.sigImageUpdated.emit(
                    detectorName, image, init, detectorName == self._currentDetectorName
                )
            )

            # Set as default if first detector
            if self._currentDetectorName is None:
                self._currentDetectorName = detectorName

        # A timer will collect the new frame and update it through the communication channel
        self._lvWorker = LVWorker(self, updatePeriod)
        self._thread = Thread()
        self._lvWorker.moveToThread(self._thread)
        self._thread.started.connect(self._lvWorker.run)
        self._thread.finished.connect(self._lvWorker.stop)

        # Create another thread for Differential View processing
        self._dvworker = DVWorker(self, self.batchSize, updatePeriod)
        self._dvthread = Thread()
        self._dvworker.moveToThread(self._dvthread)
        self._dvthread.started.connect(self._dvworker.run)
        self._dvthread.finished.connect(self._dvworker.stop)

    def __del__(self):
        self._thread.quit()
        self._thread.wait()
        self._dvthread.quit()
        self._dvthread.wait()
        if hasattr(super(), '__del__'):
            super().__del__()

    def adjustBatchSize(self, batch_size):
        """ Adjusting the batch size for the Differential View inside the dvworker class """

        self._dvworker._batch_size = batch_size

    def getCurrentDetectorName(self):
        """ Returns the name of the current detector. """

        if not self.hasDevices():
            raise NoDetectorsError

        return self._currentDetectorName

    def getCurrentDetector(self):
        """ Returns the current detector. """

        if not self.hasDevices():
            raise NoDetectorsError

        return self._subManagers[self._currentDetectorName]

    def setCurrentDetector(self, detectorName):
        """ Sets the current detector by its name. """

        self._validateManagedDeviceName(detectorName)

        oldDetectorName = self._currentDetectorName
        self._currentDetectorName = detectorName
        self.sigDetectorSwitched.emit(detectorName, oldDetectorName)

        if self._thread.isRunning():
            self.execOnCurrent(lambda c: c.updateLatestFrame(True))

    def execOnCurrent(self, func):
        """ Executes a function on the current detector and returns the result. """
        if not self.hasDevices():
            raise NoDetectorsError

        return self.execOn(self._currentDetectorName, func)

    def startAcquisition(self, liveView=False, differentialView=False):
        """ Starts detector acquisition. If `liveView` is True, sigImageUpdated will be emitted for every new frame.
            If `differentialView` is True, differential images will be computed and emitted instead of raw frames.
            Returns a handle that can be used to stop acquisition.
        """
        
        self._activeAcqsMutex.lock()
        try:
            handle = np.random.randint(2**31)

            if not liveView and not differentialView:
                self._activeAcqHandles.append(handle)
                enableLV = False
                enableDV = False
            elif liveView:
                self._activeAcqLVHandles.append(handle)
                enableLV = len(self._activeAcqLVHandles) == 1
                enableDV = differentialView  # Enable DV only if requested
            elif differentialView:
                self._activeDVHandles.append(handle)
                enableDV = len(self._activeDVHandles) == 1
                enableLV = False  # Differential view does not need live view

            enableAcq = len(self._activeAcqHandles) + len(self._activeAcqLVHandles) + len(self._activeDVHandles) == 1

        finally:
            self._activeAcqsMutex.unlock()

        # Start actual acquisition
        if enableAcq:
            self.execOnAll(lambda c: c.startAcquisition(), condition=lambda c: c.forAcquisition)
            self.sigAcquisitionStarted.emit()

        if enableLV:
            sleep(0.3)
            self._thread.start()

        if enableDV and not self._dvthread.isRunning():
            self._dvthread.start()

        return handle

    def stopAcquisition(self, handle, liveView=False, differentialView=False):
        """ Stops detector acquisition if no other handle is active. """

        self._activeAcqsMutex.lock()
        try:
            if liveView and handle in self._activeAcqLVHandles:
                self._activeAcqLVHandles.remove(handle)
                disableLV = len(self._activeAcqLVHandles) < 1
            else:
                disableLV = False

            if differentialView and handle in self._activeDVHandles:
                self._activeDVHandles.remove(handle)
                disableDV = len(self._activeDVHandles) < 1
            else:
                disableDV = False

            if not liveView and not differentialView and handle in self._activeAcqHandles:
                self._activeAcqHandles.remove(handle)

            disableAcq = len(self._activeAcqHandles) + len(self._activeAcqLVHandles) + len(self._activeDVHandles) < 1

        finally:
            self._activeAcqsMutex.unlock()

        # Stop threads if no more active handles
        if disableLV:
            self._thread.quit()
            self._thread.wait()

        if disableDV:
            self._dvthread.quit()
            self._dvthread.wait()

        if disableAcq:
            self.execOnAll(lambda c: c.stopAcquisition(), condition=lambda c: c.forAcquisition)
            self.sigAcquisitionStopped.emit()

    def setUpdatePeriod(self, updatePeriod):
        self._lvWorker.setUpdatePeriod(updatePeriod)
        self._thread.quit()
        self._thread.wait()
        self._thread.start()

    def startDetectorAcquisition(self, detector, liveView=False, differentialView=False):
        """Starts acquisition for a specific detector."""
        self._activeAcqsMutex.lock()
        try:
            handle = np.random.randint(2**31) # Creates a unique handler
            
            # adds the detector as a key in a dictionary, with the unique handler
            if detector not in self._activeDetectorAcqHandles:  
                self._activeDetectorAcqHandles[detector] = set()

            self._activeDetectorAcqHandles[detector].add(handle)
            
            # creates another dictionary for the live view with the specific handler
            if liveView:
                if detector not in self._activeDetectorAcqLVHandles:
                    self._activeDetectorAcqLVHandles[detector] = set()
                self._activeDetectorAcqLVHandles[detector].add(handle)
                enableLV = len(self._activeDetectorAcqLVHandles[detector]) == 1
            else:
                enableLV = False

            if differentialView:
                if detector not in self._activeDetectorDVHandles:
                    self._activeDetectorDVHandles[detector] = set()
                self._activeDetectorDVHandles[detector].add(handle)
                enableDV = len(self._activeDetectorDVHandles[detector]) == 1
            else:
                enableDV = False

            enableAcq = all(
                len(handles) == 1 for handles in self._activeDetectorAcqHandles.values()
            )

        finally:
            self._activeAcqsMutex.unlock()

        # Start acquisition only for this detector
        if enableAcq:
            self.execOnAll(lambda c: c.startAcquisition(), condition=lambda c: c == detector)

        if enableLV:
            sleep(0.3)
            self._thread.start()

        if enableDV and not self._dvthread.isRunning():
            sleep(0.3)
            self._dvthread.start()

        return handle
    
    def stopDetectorAcquisition(self, detector, handles_dict, liveView=False, differentialView=False):
        """Stops acquisition for a specific detector."""
        self._activeAcqsMutex.lock()
        # read the given dictionary and convert the values to set form for readout
        handles_dict_sets = [value_set if isinstance(value_set, set) else {value_set} for value_set in handles_dict.values()]
        handles = [next(iter(value_set)) for value_set in handles_dict_sets]
        try:
            disableLV = False 
            disableDV = False  
            
            if liveView and detector in self._activeDetectorAcqLVHandles:
                for handle in handles:
                    if handle in self._activeDetectorAcqLVHandles[detector]:
                        self._activeDetectorAcqLVHandles[detector].remove(handle)
                        disableLV = len(self._activeDetectorAcqLVHandles[detector]) == 0

            if differentialView and detector in self._activeDetectorDVHandles:
                for handle in handles:
                    if handle in self._activeDetectorDVHandles[detector]:
                        self._activeDetectorDVHandles[detector].remove(handle)
                        disableDV = len(self._activeDetectorDVHandles[detector]) == 0

            if detector in self._activeDetectorAcqHandles: 
                for handle in handles:
                    if handle in self._activeDetectorAcqHandles[detector]:
                        self._activeDetectorAcqHandles[detector].remove(handle)

            disableAcq = all(len(handles) == 0 for handles in self._activeDetectorAcqHandles.values())

        finally:
            self._activeAcqsMutex.unlock()

        if disableLV:
            self._thread.quit()
            self._thread.wait()

        if disableDV:
            self._dvthread.quit()
            self._dvthread.wait()

        if disableAcq:
            self.execOnAll(lambda c: c.stopAcquisition(), condition=lambda c: c == detector)



class LVWorker(Worker):
    def __init__(self, detectorsManager, updatePeriod):
        super().__init__()
        self._detectorsManager = detectorsManager
        self._updatePeriod = updatePeriod
        self._vtimer = None

    def run(self):
        self._detectorsManager.execOnAll(lambda c: c.updateLatestFrame(False),
                                         condition=lambda c: c.forAcquisition)
        self._vtimer = Timer()
        self._vtimer.timeout.connect(
            lambda: self._detectorsManager.execOnAll(lambda c: c.updateLatestFrame(True),
                                                     condition=lambda c: c.forAcquisition)
        )
        self._vtimer.start(self._updatePeriod)

    def stop(self):
        if self._vtimer is not None:
            self._vtimer.stop()

    def setUpdatePeriod(self, updatePeriod):
        self._updatePeriod = updatePeriod


class DVWorker(Worker):
    sigSetBatchSize = Signal(int)

    def __init__(self, detectorsManager, batch_size, updatePeriod):
        super().__init__()
        self._detectorsManager = detectorsManager
        self._batch_size = batch_size
        self._frames = []  # Stores averaged batches
        self._updatePeriod = updatePeriod
        self._timer = None

    def run(self):
        """ Continuously processes frames as they become available. """
        self._timer = Timer()
        self._timer.timeout.connect(
            lambda: self._detectorsManager.execOnAll(lambda c: self.process_frame(c),
                                                     condition=lambda c: c.forDifferential)
        )
        self._timer.start(self._updatePeriod)

    def stop(self):
        if self._timer is not None:
            self._timer.stop()

    def process_frame(self, detector):
        """ Processes frames for the given detector and computes the differential image. """
        batch_frames = []
        
        for _ in range(self._batch_size):
            chunk = detector.getLatestFrame()
            if chunk is None or not isinstance(chunk, np.ndarray):
                self.__logger.warning('No DV Image taken')
                return
            batch_frames.append(chunk)

        if len(batch_frames) == 0:
            return

        # Compute batch average
        batch_avg = np.mean(np.stack(batch_frames), axis=0)
        self._frames.append(batch_avg)

        # Ensure we have at least two batch averages for differential calculation
        if len(self._frames) >= 2:
            batch1_avg = self._frames[-2]  # Older batch
            batch2_avg = self._frames[-1]  # Newer batch

            diff_image = (batch1_avg / (batch2_avg + 1e-6)) - 1
            self.emit_diff_image(detector, diff_image)

            # Keep only the latest batch
            self._frames = [self._frames[-1]]


    def emit_diff_image(self, detector, diff_image):
        """ Emit the differential image. """
        self._detectorsManager.sigImageUpdated.emit(
            detector.name,
            diff_image,
            False,  # 'init' is False for differential images
            True    # This is the current detector's image
        )

    def set_batch_size(self, batch_size):
        """ Update the batch size and reset the frame buffer. """
        self._batch_size = batch_size
        self._frames = []


class NoDetectorsError(RuntimeError):
    """ Error raised when a function related to the current detector is called
    if the DetectorsManager doesn't manage any detectors (i.e. the manager is
    initialized without any detectors). """
    pass


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
