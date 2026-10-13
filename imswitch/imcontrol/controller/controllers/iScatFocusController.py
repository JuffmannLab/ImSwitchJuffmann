import atexit
import threading
import time

import numpy as np
from time import perf_counter
import scipy.ndimage as ndi
from lantz import Q_
from scipy.optimize import curve_fit
from qtpy import QtCore

from imswitch.imcommon.framework import Signal, Thread, Timer, Worker
from imswitch.imcommon.model import initLogger
from imswitch.imcontrol.model import configfiletools
from ..basecontrollers import ImConWidgetController


class iScatFocusController(ImConWidgetController):
    """Linked to iScatFocusWidget.

    Grabbing and analyzing the focus camera frames, the calibration and the auto-tuning run in a
    FocusWorker thread. The PID update, the piezo moves of the lock and all GUI updates stay in the
    GUI thread, since the NidaqManager can't take commands from two threads at the same time. """

    sigStartCalibration = Signal(float, float, int)  # (from_V, to_V, steps), runs in FocusWorker
    sigStartAutoTune = Signal(float)  # (step_size), runs in FocusWorker

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)
        self._worker = None
        self._thread = None

        # Reads the specific values from the configuration file.
        if self._setupInfo.iScatFocus is None:
            return

        # Each widget action is connected once (the buttons emit these signals)
        self._widget.sigPIDToggled.connect(self.toggleFocus)
        self._widget.sigSetPosition.connect(self.moveZ)
        self._widget.sigAutoTune.connect(self.autoTune)
        self._widget.sigPIDValuesChanged.connect(self.updatePIDParameters)
        self._widget.sigCalibrate.connect(self.runCalibration)
        self._widget.sigSledEnable.connect(self.sledEnable)
        self._widget.sigSledAIEnable.connect(self.sledEnableAI)
        self._widget.sigSledControlUpdate.connect(self.updateSledControl)
        self._widget.sigSelectROI.connect(self.selectROI)
        self._widget.sigApplyROI.connect(self.applyROI)
        self._widget.sigSaveROI.connect(self.saveROI)

        # SLED (light source of the focus lock), controlled by the NiDAQ
        self.sledEnableLine = self._setupInfo.iScatFocus.sledEnableLine
        self.sledAIEnableLine = self._setupInfo.iScatFocus.sledAIEnableLine
        self.sledControlChannel = self._setupInfo.iScatFocus.sledControlChannel
        self._sledOff = False  # unknown state on startup, so sledOff() always runs once
        if None in (self.sledEnableLine, self.sledAIEnableLine, self.sledControlChannel):
            self.__logger.warning('SLED lines not set in the setup file, SLED control disabled')
            self._widget.sledGroup.setEnabled(False)
        else:
            # Make sure the SLED is off on startup, and switched off again if ImSwitch exits
            # without closing the controllers
            self.sledOff()
            atexit.register(self.sledOff)

        self.camera = self._setupInfo.iScatFocus.camera
        self.positioner = self._setupInfo.iScatFocus.positioner
        self.updateFreq = self._setupInfo.iScatFocus.updateFreq
        self.cropFrame = (self._setupInfo.iScatFocus.frameCropx,
                          self._setupInfo.iScatFocus.frameCropy,
                          self._setupInfo.iScatFocus.frameCropw,
                          self._setupInfo.iScatFocus.frameCroph)
        self._master.detectorsManager[self.camera].crop(*self.cropFrame)
        self.cropFrame = self._appliedCrop()
        self._showCropText()

        # Optional initial PID parameters from the setup file (before the edits are connected
        # to unlockFocus, the lock state doesn't exist yet)
        if self._setupInfo.iScatFocus.pidParams is not None:
            self._widget.setPIDparams(self._setupInfo.iScatFocus.pidParams)

        # Connect FocusLockWidget buttons
        self._widget.kpEdit.textChanged.connect(self.unlockFocus)
        self._widget.kiEdit.textChanged.connect(self.unlockFocus)
        self._widget.kdEdit.textChanged.connect(self.unlockFocus)

        # Calibration storage
        self.volts_per_px = None  # Calibration slope (V/px)
        self.px_per_volt = None   # Inverse calibration (px/V)
        self.zero_offset_px = None # Position at 0V
        self.px_per_volt_forward = None   # Slope while the voltage increases (px/V)
        self.px_per_volt_backward = None  # Slope while the voltage decreases (px/V)

        # Set the initial values
        self.setPointSignal = 0
        self.locked = False
        self.aboutToLock = False
        self.noStepVar = True
        self.focusTime = 1000 / self.updateFreq  # time between focus signal updates in ms
        self.lockPosition = 0
        self.currentPosition = 0
        self.lastZ = 0
        self.buffer = 50
        self.currPoint = 0
        self.setPointData = np.zeros(self.buffer)
        self.timeData = np.zeros(self.buffer)
        self.lockingData = np.zeros(7)
        self.pid = None
        self._lastPIDTime = None
        # Optional piezo sensitivity from the setup file, to show the stability in nm
        self.piezoNmPerVolt = self._setupInfo.iScatFocus.piezoNmPerVolt
        
        self.pTermData = np.zeros(self.buffer)
        self.iTermData = np.zeros(self.buffer)
        self.dTermData = np.zeros(self.buffer)

        self.startTime = perf_counter()

        # Starts acquisition. I don't know if this can cause problems if, the camera of interest is also used for acquisition
        self._master.detectorsManager[self.camera].startAcquisition()

        # Frame grabbing, analysis, calibration and auto-tuning run in their own thread
        self._worker = FocusWorker(self._master.detectorsManager[self.camera],
                                   self._master.positionersManager[self.positioner],
                                   int(self.focusTime))
        self._worker.sigFrameAnalyzed.connect(self.update)
        self._worker.sigCalibrationDone.connect(self.calibrationDone)
        self._worker.sigAutoTuneDone.connect(self.autoTuneDone)
        self.sigStartCalibration.connect(self._worker.runCalibration)
        self.sigStartAutoTune.connect(self._worker.runAutoTune)
        self._thread = Thread()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._thread.finished.connect(self._worker.stop)
        self._thread.start()

        # Shows the current piezo position, also when it is moved by the Positioner widget
        self._positionTimer = Timer()
        self._positionTimer.timeout.connect(self._showPosition)
        self._positionTimer.start(200)
        self._showPosition()

    def closeEvent(self):
        """ Stops the FocusWorker thread; a running calibration/auto-tune is aborted. Called before
        the cameras are closed. Also switches the SLED off. """
        if self._setupInfo.iScatFocus is not None:
            self.sledOff()
            self._positionTimer.stop()
        if self._thread is None:
            return
        self.unlockFocus()
        self._worker.abort()
        self._thread.quit()
        self._thread.wait()
        self._thread = None
        self.__logger.debug('Focus worker thread stopped')

    def sledOff(self):
        """ Disables the SLED and its current control and sets the control voltage to 0 V. """
        if self._sledOff or None in (self.sledEnableLine, self.sledAIEnableLine,
                                     self.sledControlChannel):
            return
        try:
            nidaq = self._master.nidaqManager
            nidaq.setDigital(self._setupInfo.iScatFocus, False, line=self.sledEnableLine)
            nidaq.setDigital(self._setupInfo.iScatFocus, False, line=self.sledAIEnableLine)
            nidaq.setAnalog(self._setupInfo.iScatFocus, 0, min_val=0, max_val=2.5,
                            channel=self.sledControlChannel)
            self._sledOff = True
        except Exception as e:
            self.__logger.error(f'Could not switch the SLED off: {e}')

    def sledEnable(self, *_):
        isChecked = self._widget.sledEnable.isChecked()
        self._master.nidaqManager.setDigital(self._setupInfo.iScatFocus, isChecked,
                                             line=self.sledEnableLine)
        self._sledOff = False

    def sledEnableAI(self, *_):
        isChecked = self._widget.sledEnableAI.isChecked()
        self._master.nidaqManager.setDigital(self._setupInfo.iScatFocus, isChecked,
                                             line=self.sledAIEnableLine)
        self._sledOff = False

    def updateSledControl(self, voltage):
        self._master.nidaqManager.setAnalog(self._setupInfo.iScatFocus, voltage, min_val=0,
                                            max_val=2.5, channel=self.sledControlChannel)
        self._sledOff = False

    def _appliedCrop(self):
        """ The crop the focus camera actually applied, as (x, y, width, height). """
        detector = self._master.detectorsManager[self.camera]
        return (*map(int, detector.frameStart), *map(int, detector.shape))

    def _crop(self, x, y, width, height):
        """ Crops the focus camera. The FocusWorker doesn't grab frames meanwhile. """
        with self._worker.cameraLock:
            self._master.detectorsManager[self.camera].crop(x, y, width, height)
        # The fallback spot position refers to the previous crop
        self._worker.resetSpot()

    def _showCropText(self, note=''):
        x, y, w, h = self.cropFrame
        self._widget.setROIText(f'ROI: x {x}, y {y}, {w} x {h} px{note}')

    def selectROI(self, enabled):
        """ Shows the full field of view of the focus camera with the current ROI drawn on it,
        or goes back to the current ROI (cancel). """
        if self._worker is None:
            return
        if enabled:
            if self._worker.busy:
                self._widget.setSelectROIChecked(False)
                return
            self.unlockFocus()
            self._setRoutineRunning(True)
            self._worker.setPreview(True)  # frames are shown without fitting the spot
            fullShape = self._master.detectorsManager[self.camera].fullShape
            self._crop(0, 0, *fullShape)
            self._widget.showROI(*self.cropFrame)
            self._widget.setROIText('Drag/resize the rectangle, then click "Apply ROI". '
                                    'Click "Select ROI" again to cancel.')
        else:
            # Cancel: back to the current ROI
            self._widget.hideROI()
            self._crop(*self.cropFrame)
            self._worker.setPreview(False)
            self._setRoutineRunning(False)
            self._showCropText()

    def applyROI(self, x, y, width, height):
        """ Crops the focus camera to the drawn ROI (sensor pixels). """
        if self._worker is None:
            return
        fullW, fullH = self._master.detectorsManager[self.camera].fullShape
        x = int(np.clip(x, 0, fullW - 1))
        y = int(np.clip(y, 0, fullH - 1))
        width = int(np.clip(width, 1, fullW - x))
        height = int(np.clip(height, 1, fullH - y))
        self._widget.hideROI()
        self._widget.setSelectROIChecked(False)
        self._crop(x, y, width, height)
        self.cropFrame = self._appliedCrop()
        self._worker.setPreview(False)
        self._setRoutineRunning(False)
        self.__logger.info(f'Focus camera ROI set to {self.cropFrame}')
        # The calibration slopes stay valid, positions in px refer to the new ROI
        self._showCropText(' (not saved; the positions in px refer to the new ROI, '
                           'recalibrate if needed)')

    def saveROI(self):
        """ Saves the current ROI of the focus camera in the setup file (frameCrop*), it is
        applied on startup. """
        x, y, w, h = self.cropFrame

        def update(setupDict):
            setupDict['iScatFocus'].update(
                {'frameCropx': x, 'frameCropy': y, 'frameCropw': w, 'frameCroph': h})
        try:
            configfiletools.updateSetupFile(configfiletools.loadOptions()[0], update)
        except Exception as e:
            self.__logger.error(f'Could not save the ROI: {e}')
            self._widget.setROIText(f"<font color='red'>Could not save the ROI: {e}</font>")
            return
        self._showCropText(' (saved)')

    def _setRoutineRunning(self, running, text=None):
        """ Disables the buttons that move the piezo while calibration/auto-tuning runs. """
        self._widget.calibButton.setEnabled(not running)
        self._widget.autoTuneButton.setEnabled(not running)
        self._widget.lockButton.setEnabled(not running)
        self._widget.positionSetButton.setEnabled(not running)
        if text is not None:
            self._widget.calibResultLabel.setText(text)

    def runCalibration(self, from_V: float, to_V: float, steps: int):
        """ Starts the calibration in the FocusWorker thread, so the GUI stays responsive. """
        if self._worker is None or self._worker.busy:
            return
        self.unlockFocus()
        self._setRoutineRunning(True, 'Calibration running...')
        self.sigStartCalibration.emit(from_V, to_V, steps)

    def calibrationDone(self, result):
        """ Receives the calibration result from the FocusWorker. """
        self._setRoutineRunning(False)
        if 'error' in result:
            self._widget.calibResultLabel.setText(
                f"<font color='red'>Calibration failed: {result['error']}</font>")
            return

        self.px_per_volt = result['px_per_volt']
        self.volts_per_px = 1 / result['px_per_volt']
        self.zero_offset_px = result['zero_offset']
        self.px_per_volt_forward = result['m_forward']
        self.px_per_volt_backward = result['m_backward']

        # Update UI with both forward and backward results
        self._widget.updateCalibrationResult(
            slope=self.volts_per_px,
            intercept=self.zero_offset_px,
            forward_slope=1 / result['m_forward'],
            backward_slope=1 / result['m_backward'],
            angle_deg=result['angle_deg']
        )
        self.__logger.info(f"Calibration complete: {self.px_per_volt:.2f} px/V "
                           f"(forward {self.px_per_volt_forward:.2f}, backward "
                           f"{self.px_per_volt_backward:.2f}), direction {result['angle_deg']:.1f} deg, "
                           f"Zero at {self.zero_offset_px:.2f} px")

    def unlockFocus(self):
        """Release focus lock and reset controller state."""
        if self.locked:
            self.locked = False
            if hasattr(self, 'pid'):
                self.pid.reset()
            self._widget.lockButton.setChecked(False)
            self._widget.setpointLine.hide()  # Hide rather than remove
            self.__logger.debug("Focus lock released")

    def toggleFocus(self, *_):
        """Toggle focus lock state with proper PID initialization."""
        if self._widget.lockButton.isChecked():
            try:
                # Get current position and PID parameters
                current_voltage = self._master.positionersManager[self.positioner].get_abs()
                kp = float(self._widget.kpEdit.text())
                ki = float(self._widget.kiEdit.text())
                kd = float(self._widget.kdEdit.text()) 
                
                # Initialize PID lock
                self.lockFocus(kp, ki, kd, current_voltage)
                self._widget.lockButton.setText('Unlock')
                self.__logger.info(f"Focus locked at {current_voltage:.3f} V "
                                f"with PID: P={kp:.4f}, I={ki:.4f}, D={kd:.4f}")
                
            except ValueError as e:
                self._widget.lockButton.setChecked(False)
                self.__logger.error(f"Invalid PID parameters: {str(e)}")
        else:
            self.unlockFocus()
            self._widget.lockButton.setText('Lock')
            self.__logger.info("Focus unlocked")

    def cameraDialog(self):
        self._master.detectorsManager[self.camera].openPropertiesDialog()
        self.__logger.debug('Open camera settings dialog')

    def moveZ(self, target_voltage=None):
        if target_voltage is None:
            target_voltage = float(self._widget.positionEdit.text())
        # Ensure voltage stays within -10 to +10V range
        target_voltage = max(-10, min(10, target_voltage))
        self._master.positionersManager[self.positioner].setPosition(target_voltage, 0)
        self.__logger.debug(f'Move Z-piezo to {target_voltage} V')
        self._showPosition()

    def _showPosition(self):
        self._widget.showCurrentPosition(self._master.positionersManager[self.positioner].get_abs())

    # Update focus lock
    def update(self, img, position):
        """ Called by the FocusWorker for every analyzed frame (runs in the GUI thread). """
        # 1+2 Camera frame and beam position come from the FocusWorker; the displayed frame is
        # the one that was analyzed
        self._worker.frameConsumed()
        if np.isnan(position):
            # ROI selection: frame without beam position, only displayed
            self._widget.camImg.setImage(img)
            return
        self.setPointSignal = position
        # 3 Update PID with the new setPointSignal and get back the distance to move, send to
        # update the PID control, and then send the move-distance to the z-piezo.
        # Every correction is applied (no deadband): at ~1 um/V, 1 mV is already ~1 nm.
        if self.locked:
            voltage_adjustment = self.updatePID()
            if voltage_adjustment != 0:
                new_voltage = self.currentPosition + voltage_adjustment
                # Clamp to -10V to +10V range
                new_voltage = max(-10, min(10, new_voltage))
                self._master.positionersManager[self.positioner].move(new_voltage - self.currentPosition, 0)
        
        self.updateSetPointData()
        self._widget.camImg.setImage(img)
        if self.currPoint < self.buffer:
            self._widget.updateFocusPlot(
                self.timeData[1:self.currPoint],
                self.setPointData[1:self.currPoint],
                self.setPointSignal
            )
        else:
            self._widget.updateFocusPlot(
                self.timeData,
                self.setPointData,
                self.setPointSignal
            )

    def updateSetPointData(self):
        if self.currPoint < self.buffer:
            self.setPointData[self.currPoint] = self.setPointSignal
            self.timeData[self.currPoint] = perf_counter() - self.startTime
        else:
            self.setPointData[:-1] = self.setPointData[1:]
            self.setPointData[-1] = self.setPointSignal
            self.timeData[:-1] = self.timeData[1:]
            self.timeData[-1] = perf_counter() - self.startTime
        self.currPoint += 1

    def updatePID(self):
        self.currentPosition = self._master.positionersManager[self.positioner].get_abs()

        # Real time since the last update (frames can be skipped if the GUI is busy)
        now = perf_counter()
        dt = now - self._lastPIDTime if self._lastPIDTime is not None else self.focusTime / 1000
        self._lastPIDTime = now

        # Get PID correction (voltage change for this step)
        try:
            correction = self.pid.update(self.setPointSignal, dt)
        except RuntimeError as e:
            # Raised by PID._check_stability if the lock oscillates
            self.__logger.warning(f"{e}. Unlocking for safety.")
            self.unlockFocus()
            return 0

        # Hysteresis correction: the gains are tuned for the average slope; the spot moves by
        # px_per_volt_forward per volt while the voltage increases and by px_per_volt_backward
        # while it decreases
        if self.px_per_volt_forward is not None and correction != 0:
            slope = self.px_per_volt_forward if correction > 0 else self.px_per_volt_backward
            correction *= self.px_per_volt / slope

        # Safety checks
        if abs(correction) > 1.0:  # 1V max correction
            self.__logger.warning("Large correction detected! Unlocking for safety.")
            self.unlockFocus()
            return 0
            
        return correction
    
    def updatePIDParameters(self, kp: float, ki: float, kd: float):
        """Thread-safe PID parameter updates with validation."""

        kp = np.clip(kp, 0.00000, 1)  # Example max P gain
        ki = np.clip(ki, 0.00000, 10)  # Max I gain; auto-tune gives ~alpha/(slope*dt), e.g. 0.3
        kd = np.clip(kd, 0.00000, 0.1) # Example max D gain
        
        if self.locked:
            # Live update if locked
            self.pid.kp = kp
            self.pid.ki = ki
            self.pid.kd = kd
            self.__logger.debug(f"Live PID update: P={kp:.4f}, I={ki:.4f}, D={kd:.4f}")
        else:
            # Store for next lock
            self._widget.kpEdit.setText(f"{kp:.4f}")
            self._widget.kiEdit.setText(f"{ki:.4f}")
            self._widget.kdEdit.setText(f"{kd:.4f}")

    def lockFocus(self, kp, ki, kd, current_voltage):
        if not self.locked:
            # Set point from the mean of the last measurements instead of a single noisy one
            n = min(self.currPoint, self.buffer, 10)
            recent = self.setPointData[:self.currPoint][-n:] if self.currPoint < self.buffer \
                else self.setPointData[-n:]
            setpoint = float(np.mean(recent)) if n > 0 else self.setPointSignal
            self.pid = PID(setpoint,
                          dt=self.focusTime/1000,
                          kp=kp, ki=ki, kd=kd)
            self._lastPIDTime = None
            self.lockPosition = current_voltage
            self.locked = True
    
            
    def clearPlots(self):
        """Clear all plot data"""
        self.focusCurve.clear()
        self.pTermCurve.clear()
        self.iTermCurve.clear()
        self.dTermCurve.clear()
            
    def autoTune(self, step_size=0.5):
        """ Automated tuning (see FocusWorker.runAutoTune). Runs in the FocusWorker thread; the
        result arrives in autoTuneDone. step_size is the piezo step in V for the step response;
        it must move the spot clearly more than the noise. """
        if self._worker is None or self._worker.busy:
            return
        self.__logger.info("Starting auto-tuning...")

        # 1. Disable controller
        self.unlockFocus()
        self._setRoutineRunning(True)
        self._widget.setAutoTuneResult('Auto-tuning running (keep the setup still)...')
        self.sigStartAutoTune.emit(step_size)

    def autoTuneDone(self, result):
        """ Receives the auto-tuning result from the FocusWorker. """
        self._setRoutineRunning(False)
        if 'error' in result:
            self.__logger.error(f"Auto-tuning failed: {result['error']}")
            self._widget.setAutoTuneResult(
                f"<font color='red'>Auto-tuning failed: {result['error']}</font>")
            return
        kp, ki, kd = result['kp'], result['ki'], result['kd']
        self.__logger.info(f"Suggested parameters: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f} "
                           f"({result})")

        # Apply to GUI
        self._widget.kpEdit.setText(f"{kp:.4f}")
        self._widget.kiEdit.setText(f"{ki:.4f}")
        self._widget.kdEdit.setText(f"{kd:.4f}")

        # Measured noise/drift and expected stability, in nm if the piezo sensitivity is known
        def fmt(px):
            if self.piezoNmPerVolt:
                return f"{px:.3f} px = {px / result['slope'] * self.piezoNmPerVolt:.2f} nm"
            return f"{px:.3f} px"
        self._widget.setAutoTuneResult(
            f"<b>Auto-tune:</b> gain {result['slope']:.2f} px/V, delay {result['delay']} frame(s), "
            f"period {result['dt'] * 1000:.0f} ms<br>"
            f"Noise per frame: {fmt(result['noise_px'])}<br>"
            f"Random drift per frame: {fmt(result['drift_px'])}<br>"
            f"Linear drift per frame: {fmt(abs(result['ramp_px']))}<br>"
            f"Integrator gain alpha = {result['alpha']:.3f}<br>"
            f"<b>Expected lock stability (RMS): {fmt(result['stability_px'])}</b>"
        )


class _Aborted(Exception):
    """ Raised in the FocusWorker when a calibration/auto-tune is aborted. """


class FocusWorker(Worker):
    """ Runs in its own thread: grabs one frame per update from the focus camera, determines the
    beam position and sends both to the controller. Also runs the calibration and the auto-tuning,
    which wait for the piezo and need many frames, so they don't block the GUI. """

    sigFrameAnalyzed = Signal(object, float)  # (image, beam position in px)
    sigCalibrationDone = Signal(object)  # dict with the results, or {'error': message}
    sigAutoTuneDone = Signal(object)  # dict with kp, ki, kd, or {'error': message}

    def __init__(self, detector, positioner, updatePeriodMs):
        super().__init__()
        self.__logger = initLogger(self)
        self._detector = detector
        self._positioner = positioner
        self._updatePeriodMs = updatePeriodMs
        self._timer = None
        self._busy = False  # calibration/auto-tune running
        self._abort = False
        self._frameConsumed = True  # the controller has processed the last emitted frame
        self._last_valid_spot = None  # Fallback spot centre (x, y) if a fit fails
        self._fit_radius = 50  # Half size of the fit window around the spot (px)
        # Unit vector along which the spot moves with the piezo voltage, from the calibration.
        # None: not calibrated, the x coordinate is used as position signal.
        self._direction = None
        # Held while a frame is grabbed; the controller holds it while it crops the camera
        self.cameraLock = threading.Lock()
        self._preview = False  # ROI selection: frames are emitted without fitting the spot

    @property
    def busy(self):
        return self._busy

    def setPreview(self, enabled):
        """ While enabled, frames are only displayed (position NaN), the spot isn't fitted. """
        self._preview = enabled

    def resetSpot(self):
        """ Forgets the fallback spot position, e.g. after the ROI changed. """
        self._last_valid_spot = None

    def run(self):
        self._timer = Timer()
        self._timer.timeout.connect(self._update)
        self._timer.start(self._updatePeriodMs)

    def stop(self):
        if self._timer is not None:
            self._timer.stop()

    def abort(self):
        """ Aborts a running calibration/auto-tune; can be called from any thread. """
        self._abort = True

    def frameConsumed(self):
        """ Called by the controller when it has processed the last emitted frame. """
        self._frameConsumed = True

    def _update(self):
        # Skip while the GUI hasn't processed the last frame, so frames don't pile up in the queue
        if self._busy or not self._frameConsumed:
            return
        img = self.grabCameraFrame()
        if img is None:
            return
        if self._preview:
            self._frameConsumed = False
            self.sigFrameAnalyzed.emit(img, float('nan'))
            return
        position = self.positionSignal(self.fitSpot(img))
        if position is None:
            return
        self._frameConsumed = False
        self.sigFrameAnalyzed.emit(img, float(position))

    def _sleep(self, seconds):
        """ time.sleep that ends early (raising _Aborted) when abort() is called. """
        end = time.time() + seconds
        while True:
            if self._abort:
                raise _Aborted()
            remaining = end - time.time()
            if remaining <= 0:
                return
            time.sleep(min(0.05, remaining))

    # Declared as Qt slots so that the controller's signals run them in the worker thread
    # (without @Slot, PyQt calls them in the thread of the emitting controller)
    @QtCore.Slot(float, float, int)
    def runCalibration(self, from_V, to_V, steps):
        self._busy = True
        self._abort = False
        initial_V = None
        try:
            # 1. Store initial position
            initial_V = self._positioner.get_abs()

            # 2. Prepare measurement points with hysteresis compensation. from_V and to_V are
            # relative to the current position, so the calibration scans around the focus
            test_voltages = np.clip(initial_V + np.linspace(from_V, to_V, steps), -10, 10)
            test_voltages = np.concatenate([test_voltages, test_voltages[::-1]])  # Forward and back
            spots = []  # spot centre (x, y) per voltage

            # 3. Enhanced measurement collection
            for i, v in enumerate(test_voltages):
                # Move with overshoot compensation
                if i > 0:
                    overshoot = 0.1 * (v - test_voltages[i-1])
                    self._positioner.setPosition(v + overshoot, 0)
                    self._sleep(0.1)

                # Final precise positioning
                self._positioner.setPosition(v, 0)

                # Dynamic settling time based on step size
                step_size = abs(v - test_voltages[i-1]) if i > 0 else 0
                settle_time = max(0.5, step_size * 0.5)  # 0.5s + 0.5s per volt
                self._sleep(settle_time)

                # Capture multiple samples with validation (2D Gaussian fit, same as the lock)
                samples = []
                for _ in range(10):
                    spot = self.fitSpot(self.grabCameraFrame(), fallback=False)
                    if spot is not None:
                        samples.append(spot)
                    self._sleep(0.05)

                if len(samples) < 5:
                    raise ValueError(f"Insufficient valid positions at {v}V")

                # Use median and IQR filtering, per coordinate
                samples = np.array(samples)
                q75, q25 = np.percentile(samples, [75, 25], axis=0)
                iqr = q75 - q25
                valid = np.all((samples >= q25 - 1.5*iqr) & (samples <= q75 + 1.5*iqr), axis=1)
                median_spot = np.median(samples[valid], axis=0)
                spots.append(median_spot)

                self.__logger.debug(f"Voltage {v:.2f}V -> x={median_spot[0]:.2f} px, "
                                    f"y={median_spot[1]:.2f} px (n={valid.sum()})")

            spots = np.array(spots)
            n = len(test_voltages)//2

            def fit_line(voltages, positions):
                A = np.vstack([voltages, np.ones(len(voltages))]).T
                return np.linalg.lstsq(A, positions, rcond=None)[0]

            # 4. Direction in which the spot moves with the voltage (from both sweeps); with a
            # tilted cover glass this is not along the x axis
            mx = fit_line(test_voltages, spots[:, 0])[0]
            my = fit_line(test_voltages, spots[:, 1])[0]
            if np.hypot(mx, my) < 1:
                raise ValueError(f"Implausible calibration: spot moves only "
                                 f"{np.hypot(mx, my):.2f} px/V")
            direction = np.array([mx, my]) / np.hypot(mx, my)

            # 5. Position along that direction; increases with the voltage by construction
            positions = spots @ direction

            # 6. Two-way linear regression: forward (increasing voltage) and backward sweep
            # separately, for the hysteresis correction of the lock
            m_forward, b_forward = fit_line(test_voltages[:n], positions[:n])
            m_backward, b_backward = fit_line(test_voltages[n:], positions[n:])
            if m_forward <= 0 or m_backward <= 0:
                raise ValueError(f"Implausible calibration: forward {m_forward:.2f} px/V, "
                                 f"backward {m_backward:.2f} px/V")

            # 7. Use average of both directions
            px_per_volt = (m_forward + m_backward) / 2
            zero_offset = (b_forward + b_backward) / 2

            # From now on the position signal is measured along the calibrated direction
            self._direction = direction

            self.sigCalibrationDone.emit({
                'px_per_volt': px_per_volt, 'zero_offset': zero_offset,
                'm_forward': m_forward, 'm_backward': m_backward,
                'angle_deg': float(np.degrees(np.arctan2(direction[1], direction[0])))
            })
        except _Aborted:
            self.sigCalibrationDone.emit({'error': 'aborted'})
        except Exception as e:
            self.__logger.error(f"Calibration failed: {str(e)}")
            self.sigCalibrationDone.emit({'error': str(e)})
        finally:
            # Restore original position (also if the calibration failed)
            if initial_V is not None:
                self._positioner.setPosition(initial_V, 0)
            self._busy = False

    @QtCore.Slot(float)
    def runAutoTune(self, step_size):
        """ Measures the loop and computes the gains (lock must be off):

        1. Noise and drift: the position signal at rest, sampled at the loop period. A random
           walk (drift, variance q per frame) and white measurement noise (variance r, e.g.
           camera noise and vibrations faster than the loop) are separated by how the variance
           of the differences grows with the lag: Var(lag k) = k*q + 2r. The mean difference
           per frame is the linear (thermal) drift.
        2. Step response up and back down: gain in px/V and the delay in frames until the
           spot has moved.
        3. The piezo follows the voltage within a frame, so the loop is a pure gain with
           delay, disturbed by drift and noise. For that the best controller is an integrator:
           each step corrects the fraction alpha of the measured error. Small alpha averages the
           noise, large alpha follows the drift; alpha is chosen to minimize the expected error
           (without linear drift this is the steady-state Kalman gain) and limited for the delay.
           Ki = alpha / (gain * dt); P and D would only add measurement noise, so Kp = Kd = 0.
        """
        self._busy = True
        self._abort = False
        start_V = None
        try:
            start_V = self._positioner.get_abs()
            self._sleep(0.5)

            # 1. Noise and drift with the piezo at rest: regression of the variance of the
            # differences over the lags 1..20 (robust variances, around the median, so a linear
            # drift doesn't enter q and r)
            signals, dt = self._sampleSignal(200)
            lags = np.arange(1, 21)
            variances = [self._robustVar(signals[lag:] - signals[:-lag]) for lag in lags]
            q, twoR = np.polyfit(lags, variances, 1)
            q = max(q, 0.0)  # random-walk drift variance per frame
            r = max(twoR / 2, 1e-12)  # measurement noise variance per frame
            noise = np.sqrt(r)
            ramp = float(np.median(np.diff(signals)))  # linear (thermal) drift per frame
            baseline = np.median(signals[-20:])

            # 2. Step response up and back down
            self._positioner.setPosition(start_V + step_size, 0)
            up, _ = self._sampleSignal(30)
            self._positioner.setPosition(start_V, 0)
            down, _ = self._sampleSignal(30)
            upper, lower = np.median(up[-10:]), np.median(down[-10:])
            step_px = upper - baseline
            if abs(step_px) < 10 * noise:
                raise ValueError(f'the step of {step_size} V moved the spot only {step_px:.2f} px '
                                 f'(noise {noise:.3f} px); use a larger step')
            slope = ((upper - baseline) + (upper - lower)) / (2 * step_size)  # px/V, both directions
            if slope <= 0:
                raise ValueError('the position signal decreases with the voltage; run the '
                                 'calibration first, it aligns the signal with the motion')

            def delayFrames(response, start, end):
                reached = np.nonzero((response - start) / (end - start) >= 0.9)[0]
                return int(reached[0]) if len(reached) else len(response)
            delay = max(delayFrames(up, baseline, upper), delayFrames(down, upper, lower))
            if delay >= 10:
                raise ValueError(f'the spot needs {delay} frames to follow a step; check the piezo')

            # 3. Integrator gain alpha minimizing the expected RMS error of the locked signal:
            # random walk and noise give (q + alpha^2 r) / (alpha (2 - alpha)) (minimal at the
            # steady-state Kalman gain), the linear drift a lag of ramp / alpha. alpha is limited
            # for the delay (an integrator with n frames delay is stable for
            # alpha < 2 sin(pi / (2 (2n + 1))); half of that is used as margin).
            def expectedError(alpha):
                return np.sqrt((q + alpha ** 2 * r) / (alpha * (2 - alpha)) + (ramp / alpha) ** 2)
            # Lower limit 0.05 (~20 frames time constant): drift that didn't show up during the
            # measurement still gets corrected within about a second
            alpha_max = np.sin(np.pi / (2 * (2 * delay + 1)))
            alphas = np.linspace(0.05, 1.0, 1000)
            alpha_opt = float(alphas[np.argmin(expectedError(alphas))])
            alpha = float(np.clip(alpha_opt, 0.05, alpha_max))

            self.sigAutoTuneDone.emit({
                'kp': 0.0, 'ki': alpha / (slope * dt), 'kd': 0.0,
                'alpha': alpha, 'alpha_opt': alpha_opt, 'slope': float(slope),
                'delay': delay, 'dt': dt, 'noise_px': float(noise), 'drift_px': float(np.sqrt(q)),
                'ramp_px': ramp, 'stability_px': float(expectedError(alpha))
            })
        except _Aborted:
            self.sigAutoTuneDone.emit({'error': 'aborted'})
        except Exception as e:
            self.sigAutoTuneDone.emit({'error': str(e)})
        finally:
            if start_V is not None:
                self._positioner.setPosition(start_V, 0)
            self._busy = False

    def _sampleSignal(self, n):
        """ Measures the position signal n times at the period of the lock loop and returns
        (signals, median period in s). Frames identical to the previous one (camera slower than
        the loop) are skipped, so every value comes from a new frame. """
        period = self._updatePeriodMs / 1000
        signals, times = [], []
        lastImg = None
        nextTime = time.perf_counter()
        for _ in range(10 * n):
            if len(signals) >= n:
                break
            nextTime = max(nextTime + period, time.perf_counter())
            img = self.grabCameraFrame()
            if img is not None and not (lastImg is not None and np.array_equal(img, lastImg)):
                lastImg = img
                signal = self.positionSignal(self.fitSpot(img, fallback=False))
                if signal is not None:
                    signals.append(signal)
                    times.append(time.perf_counter())
            self._sleep(max(0.0, nextTime - time.perf_counter()))
        if len(signals) < n:
            raise ValueError(f'only {len(signals)} of {n} frames with a spot')
        dt = float(np.median(np.diff(times))) if len(times) > 1 else period
        return np.array(signals), dt

    @staticmethod
    def _robustVar(values):
        """ Variance from the median absolute deviation; insensitive to single outliers
        (e.g. vibration spikes or a failed fit). """
        values = np.asarray(values)
        return (1.4826 * np.median(np.abs(values - np.median(values)))) ** 2

    def grabCameraFrame(self):
        """Grab frame with error handling"""
        try:
            with self.cameraLock:
                img = self._detector.getLatestFrame()
            return np.swapaxes(img, 0, 1) if img is not None else None
        except Exception as e:
            self.__logger.error(f"Frame grab failed: {str(e)}")
            return None

    def fitSpot(self, img, fallback=True):
        """ Fits a 2D Gaussian (centre, widths in x and y, amplitude, offset) to the spot in a
        window around its brightest point and returns the centre (x, y) in px. x is the second
        image axis. If the fit fails, the last valid centre is returned (fallback=True) or None. """
        failed = self._last_valid_spot if fallback else None
        if img is None:
            return failed

        try:
            img = np.asarray(img, dtype=np.float64)

            # Brightest point of the smoothed image as start value
            sigma = max(1.0, min(img.shape) * 0.02)  # ~2% of image size
            smoothed = ndi.gaussian_filter(img, sigma=sigma)
            py, px = np.unravel_index(np.argmax(smoothed), smoothed.shape)

            # Fit window around it
            r = self._fit_radius
            y0, y1 = max(0, py - r), min(img.shape[0], py + r + 1)
            x0, x1 = max(0, px - r), min(img.shape[1], px + r + 1)
            window = img[y0:y1, x0:x1]
            yy, xx = np.mgrid[y0:y1, x0:x1]

            # Start values: offset from the dark pixels, widths from the second moments
            offset = np.percentile(window, 5)
            weights = np.clip(window - offset, 0, None)
            if weights.sum() <= 0:
                return failed
            sx = np.sqrt(np.sum(weights * (xx - px) ** 2) / weights.sum())
            sy = np.sqrt(np.sum(weights * (yy - py) ** 2) / weights.sum())
            p0 = [window.max() - offset, px, py, max(sx, 1.0), max(sy, 1.0), offset]
            bounds = ([0, x0, y0, 0.5, 0.5, -np.inf],
                      [np.inf, x1 - 1, y1 - 1, 2 * r, 2 * r, np.inf])

            popt, _ = curve_fit(self.gaussian_2d, (xx.ravel(), yy.ravel()), window.ravel(),
                                p0=p0, bounds=bounds, maxfev=2000)
            spot = (float(popt[1]), float(popt[2]))
            self._last_valid_spot = spot
            return spot

        except Exception as e:
            self.__logger.warning(f"Spot fit failed: {str(e)}")
            return failed

    def positionSignal(self, spot):
        """ Position signal for the lock in px: the spot centre along the calibrated direction of
        motion, or the x coordinate before the first calibration. None if there is no spot. """
        if spot is None:
            return None
        if self._direction is None:
            return spot[0]
        return float(np.dot(spot, self._direction))

    @staticmethod
    def gaussian_2d(coords, a, x0, y0, sx, sy, offset):
        """2D Gaussian model (axes along x and y) for fitting"""
        x, y = coords
        return a * np.exp(-((x - x0) ** 2) / (2 * sx ** 2) - ((y - y0) ** 2) / (2 * sy ** 2)) + offset


class PID:
    """ Discrete PID controller in velocity (incremental) form: update() returns the voltage
    change for this step, which the controller adds to the piezo voltage. The gains have the
    usual meaning of a positional PID: kp in V/px, ki in V/(px*s), kd in V*s/px.

    The piezo follows the voltage within one frame, so the integral term does the drift
    correction; P and D mainly pass measurement noise to the piezo (see FocusWorker.runAutoTune).
    There is no Kalman filter: inside the loop it doesn't know the piezo corrections and adds
    lag, and the optimal filter for drift in noise is the integrator gain itself. """

    def __init__(self, setpoint, dt=0.001, kp=0, ki=0, kd=0):
        # Gains
        self._kp = kp          # Proportional gain (V/px)
        self._ki = ki          # Integral gain (V/(px·s))
        self._kd = kd          # Derivative gain (V/(px/s))

        self._started = False

        # Control parameters
        self._setpoint = setpoint  # Target position (px)
        self._dt = dt          # Nominal time step (s), used if update() gets no dt

        # State variables
        self._last_error = None
        self._prev_error = None
        self._p = self._i = self._d = 0  # terms of the last update, for monitoring

        # Stability monitoring
        self.error_history = []
        self.stability_counter = 0
        self.max_unstable_count = 10
        self.stable_threshold = 1.0  # px RMS error for stability

    def update(self, current_px, dt=None):
        """
        Update controller with new measurement.
        Returns the voltage change for this step in volts.
        """
        dt = dt if dt else self._dt
        error = self._setpoint - current_px
        if self._last_error is None:
            self._last_error = error  # no P/D kick on the first step
        if self._prev_error is None:
            self._prev_error = self._last_error

        # Incremental form of u = kp*e + ki*integral(e) + kd*de/dt
        self._p = self._kp * (error - self._last_error)
        self._i = self._ki * error * dt
        self._d = self._kd * (error - 2 * self._last_error + self._prev_error) / dt
        self._prev_error, self._last_error = self._last_error, error

        # Monitor stability
        self._check_stability(error)

        return self._p + self._i + self._d

    def _check_stability(self, error_px):
        """Monitor stability and detect oscillations"""
        self.error_history.append(abs(error_px))
        if len(self.error_history) > 100:
            self.error_history.pop(0)

        if len(self.error_history) == 100:
            rms_error = np.sqrt(np.mean(np.array(self.error_history)**2))
            if rms_error > self.stable_threshold:
                self.stability_counter += 1
                if self.stability_counter > self.max_unstable_count:
                    raise RuntimeError("PID controller unstable - needs retuning")
            else:
                self.stability_counter = 0

    def reset(self):
        """Reset controller state"""
        self._last_error = None
        self._prev_error = None
        self.error_history = []
        self.stability_counter = 0

    def restart(self):
        self._started = False

    @property
    def terms(self):
        """Return the terms of the last update (voltage changes) for monitoring"""
        return {'p': self._p, 'i': self._i, 'd': self._d}

    @property
    def started(self):
        return self._started

    @started.setter
    def started(self, value):
        self._started = value

    @property
    def setPoint(self):
        return self._setpoint

    @setPoint.setter
    def setPoint(self, value):
        self._setpoint = value

    @property
    def kp(self):
        return self._kp

    @kp.setter
    def kp(self, value):
        self._kp = value

    @property
    def ki(self):
        return self._ki

    @ki.setter
    def ki(self, value):
        self._ki = value

    @property
    def kd(self):
        return self._kd

    @kd.setter
    def kd(self, value):
        self._kd = value
