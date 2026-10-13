from time import sleep

import numpy as np

from imswitch.imcommon.framework import Mutex, Signal, SignalInterface, Thread, Timer, Worker
from imswitch.imcommon.model import initLogger
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

    def finalize(self):
        """ Stops the LiveView and Differential View threads, then closes the detectors. Called
        by the MasterController on shutdown, after the controllers were closed. """
        for thread in (self._thread, self._dvthread):
            thread.quit()
            thread.wait()
        super().finalize()

    def adjustBatchSize(self, batch_size):
        """ Adjusting the batch size for the Differential View inside the dvworker class """

        self._dvworker.set_batch_size(batch_size)

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
            # Keep cameras running that are still used by LiveView/Differential View or that
            # a focus lock needs
            self.execOnAll(lambda c: c.stopAcquisition(),
                           condition=lambda c: c.forAcquisition and not c.forFocusLock
                           and not self._activeDetectorAcqHandles.get(c))
            self.sigAcquisitionStopped.emit()

    def setUpdatePeriod(self, updatePeriod):
        self._lvWorker.setUpdatePeriod(updatePeriod)
        self._thread.quit()
        self._thread.wait()
        self._thread.start()

    def startDetectorAcquisition(self, detector, liveView=False, differentialView=False):
        """ Starts acquisition for a specific detector and returns a handle that can be used to
        stop it. The camera is started with its first handle; the LiveView/Differential View
        thread is started if it isn't running yet. """
        self._activeAcqsMutex.lock()
        try:
            handle = np.random.randint(2**31)  # Creates a unique handle

            self._activeDetectorAcqHandles.setdefault(detector, set()).add(handle)

            # Only this detector's handles count; a camera already running for a recording
            # (global startAcquisition) doesn't need to be started again
            enableAcq = (len(self._activeDetectorAcqHandles[detector]) == 1
                         and not self._hasGlobalAcqHandles())
        finally:
            self._activeAcqsMutex.unlock()

        if enableAcq:
            try:
                detector.startAcquisition()
            except Exception:
                # Remove the handle again, otherwise the camera would count as running
                self._activeAcqsMutex.lock()
                try:
                    self._activeDetectorAcqHandles.get(detector, set()).discard(handle)
                finally:
                    self._activeAcqsMutex.unlock()
                raise

        # The LiveView/Differential View handles are only added once the camera is started.
        # Otherwise the running LiveView thread would already read frames from it while it is
        # starting; a camera that isn't acquiring yet takes a snap then, which collides with
        # the start (seen with the PCO).
        self._activeAcqsMutex.lock()
        try:
            if liveView:
                self._activeDetectorAcqLVHandles.setdefault(detector, set()).add(handle)
                self._lvWorker.resetDetector(detector.name)
            if differentialView:
                self._activeDetectorDVHandles.setdefault(detector, set()).add(handle)
            enableLV = liveView and not self._thread.isRunning()
            enableDV = differentialView and not self._dvthread.isRunning()
        finally:
            self._activeAcqsMutex.unlock()

        if enableLV:
            sleep(0.3)
            self._thread.start()

        if enableDV:
            sleep(0.3)
            self._dvthread.start()

        return handle

    def stopDetectorAcquisition(self, detector, handles_dict, liveView=False, differentialView=False):
        """ Stops acquisition for a specific detector. handles_dict is the dict returned by
        execOnAll around startDetectorAcquisition ({detectorName: handle}). The camera is only
        stopped when it has no handles left, and the LiveView/Differential View thread only when
        no detector uses it any more. """
        handles = set()
        for value in handles_dict.values():
            handles |= value if isinstance(value, set) else {value}

        self._activeAcqsMutex.lock()
        try:
            self._activeDetectorAcqHandles.get(detector, set()).difference_update(handles)
            if liveView:
                self._activeDetectorAcqLVHandles.get(detector, set()).difference_update(handles)
            if differentialView:
                self._activeDetectorDVHandles.get(detector, set()).difference_update(handles)

            # A camera used by a focus lock keeps running
            disableAcq = (not self._activeDetectorAcqHandles.get(detector)
                          and not self._hasGlobalAcqHandles()
                          and not detector.forFocusLock)
            disableLV = liveView and not any(self._activeDetectorAcqLVHandles.values())
            disableDV = differentialView and not any(self._activeDetectorDVHandles.values())
        finally:
            self._activeAcqsMutex.unlock()

        if disableLV:
            self._thread.quit()
            self._thread.wait()

        if disableDV:
            self._dvthread.quit()
            self._dvthread.wait()

        if disableAcq:
            detector.stopAcquisition()

    def isInLiveView(self, detector):
        """ Whether the LiveView shows this detector: it was started with liveView=True, either
        on its own or through startAcquisition. """
        return detector.forAcquisition and bool(self._activeAcqLVHandles
                                                or self._activeDetectorAcqLVHandles.get(detector))

    def _hasGlobalAcqHandles(self):
        """ Whether acquisition was started through startAcquisition (e.g. by a recording). """
        return bool(self._activeAcqHandles or self._activeAcqLVHandles or self._activeDVHandles)



class LVWorker(Worker):
    def __init__(self, detectorsManager, updatePeriod):
        super().__init__()
        self._detectorsManager = detectorsManager
        self._updatePeriod = updatePeriod
        self._vtimer = None
        # Detectors that already got their first LiveView frame since they were started
        self._initialized = set()

    def run(self):
        self._initialized = set()
        self._update()
        self._vtimer = Timer()
        self._vtimer.timeout.connect(self._update)
        self._vtimer.start(self._updatePeriod)

    def _update(self):
        """ Updates the frame of each detector in LiveView (not those in Differential View).
        The first frame of a detector is sent with init=False, so the viewer sets its levels. """
        self._detectorsManager.execOnAll(lambda c: self._updateDetector(c),
                                         condition=self._detectorsManager.isInLiveView)

    def _updateDetector(self, detector):
        # Only counts as initialized once a frame was actually sent; right after starting, a
        # camera may not have a frame yet
        if detector.updateLatestFrame(detector.name in self._initialized):
            self._initialized.add(detector.name)

    def resetDetector(self, detectorName):
        """ The next frame of this detector is treated as its first one again. """
        self._initialized.discard(detectorName)

    def stop(self):
        if self._vtimer is not None:
            self._vtimer.stop()

    def setUpdatePeriod(self, updatePeriod):
        self._updatePeriod = updatePeriod


class DVWorker(Worker):
    sigSetBatchSize = Signal(int)

    def __init__(self, detectorsManager, batch_size, updatePeriod):
        super().__init__()
        self.__logger = initLogger(self)
        self._detectorsManager = detectorsManager
        self._batch_size = batch_size
        self._updatePeriod = updatePeriod
        self._timer = None
        self._resetBatches()

    def _resetBatches(self):
        # Per detector name: running sum and frame count of the batch being filled,
        # and the average of the last completed batch
        self._batchSum = {}
        self._batchCount = {}
        self._prevBatchAvg = {}
        # Detectors that already got a differential image; the first one sets the levels
        self._levelsSet = set()
        self._resetRequested = False

    def run(self):
        """ Continuously processes frames as they become available. """
        self._resetBatches()
        # Discard frames recorded before the differential view was started
        self._detectorsManager.execOnAll(lambda c: self._readChunk(c),
                                         condition=lambda c: c.forDifferential)
        self._timer = Timer()
        self._timer.timeout.connect(
            lambda: self._detectorsManager.execOnAll(lambda c: self.process_frame(c),
                                                     condition=lambda c: c.forDifferential)
        )
        self._timer.start(self._updatePeriod)

    def stop(self):
        if self._timer is not None:
            self._timer.stop()

    def _readChunk(self, detector):
        """ Returns the frames recorded since the last call as (n, height, width),
        or None if there are none. """
        try:
            chunk = detector.getChunk()
        except Exception as e:
            self.__logger.error(f'Could not read frames from {detector.name}: {e}')
            return None
        if chunk is None:
            return None
        chunk = np.asarray(chunk)
        if chunk.ndim == 2:
            chunk = chunk[np.newaxis]
        return chunk if len(chunk) > 0 else None

    def process_frame(self, detector):
        """ Adds all frames recorded since the last call to the current batch. Each time a
        batch of batch_size frames is complete, its average is compared with the average of
        the previous batch, and the newest difference is emitted. """
        if self._resetRequested:
            self._resetBatches()

        chunk = self._readChunk(detector)
        if chunk is None:
            return

        name = detector.name
        if name in self._batchSum and self._batchSum[name].shape != chunk.shape[1:]:
            # Frame size changed (e.g. new ROI), batches can't be compared any more
            self._batchSum.pop(name)
            self._batchCount.pop(name, None)
            self._prevBatchAvg.pop(name, None)

        diff_image = None
        i = 0
        while i < len(chunk):
            count = self._batchCount.get(name, 0)
            take = min(self._batch_size - count, len(chunk) - i)
            partSum = chunk[i:i + take].sum(axis=0, dtype=np.float32)
            self._batchSum[name] = partSum if count == 0 else self._batchSum[name] + partSum
            self._batchCount[name] = count + take
            i += take

            if self._batchCount[name] >= self._batch_size:
                batch_avg = self._batchSum[name] / self._batchCount[name]
                prev_avg = self._prevBatchAvg.get(name)
                if prev_avg is not None:
                    # Normalized iScat contrast: older batch / newer batch - 1. Pixels without
                    # signal (dark or dead pixels) are set to 0 instead of dividing by ~0.
                    diff_image = np.zeros_like(batch_avg)
                    np.divide(prev_avg, batch_avg, out=diff_image, where=batch_avg >= 1)
                    diff_image -= 1
                    diff_image[batch_avg < 1] = 0
                self._prevBatchAvg[name] = batch_avg
                self._batchCount[name] = 0

        if diff_image is not None:
            self.emit_diff_image(detector, diff_image)


    def emit_diff_image(self, detector, diff_image):
        """ Emit the differential image. Like the LiveView, 'init' is False only for the first
        image, so the viewer sets the levels once and they can be adjusted by hand afterwards. """
        first = detector.name not in self._levelsSet
        self._levelsSet.add(detector.name)
        self._detectorsManager.sigImageUpdated.emit(
            detector.name,
            diff_image,
            not first,  # init
            True    # This is the current detector's image
        )

    def set_batch_size(self, batch_size):
        """ Update the batch size. The batches are reset by the worker thread on the
        next update, so this is safe to call from the GUI thread. """
        self._batch_size = batch_size
        self._resetRequested = True


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
