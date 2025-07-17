import time

import numpy as np
from time import perf_counter
import scipy.ndimage as ndi
from lantz import Q_
from skimage.feature import peak_local_max
from scipy.optimize import curve_fit

from imswitch.imcommon.framework import Thread, Timer
from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController


class iScatFocusController(ImConWidgetController):
    """Linked to iScatFocusWidget."""
    

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._widget.sigPIDToggled.connect(self.toggleFocus)
        self._widget.sigSetPosition.connect(self.moveZ)
        self._widget.sigAutoTune.connect(self.autoTune)
        self._widget.sigPIDValuesChanged.connect(self.updatePIDParameters)

        # Reads the specific values from the configuration file. 
        if self._setupInfo.iScatFocus is None:
            return

        self.camera = self._setupInfo.iScatFocus.camera
        self.positioner = self._setupInfo.iScatFocus.positioner
        self.updateFreq = self._setupInfo.iScatFocus.updateFreq
        self.cropFrame = (self._setupInfo.iScatFocus.frameCropx,
                          self._setupInfo.iScatFocus.frameCropy,
                          self._setupInfo.iScatFocus.frameCropw,
                          self._setupInfo.iScatFocus.frameCroph)
        self._master.detectorsManager[self.camera].crop(*self.cropFrame)

        # Connect FocusLockWidget buttons
        self._widget.kpEdit.textChanged.connect(self.unlockFocus)
        self._widget.kiEdit.textChanged.connect(self.unlockFocus)
        self._widget.kdEdit.textChanged.connect(self.unlockFocus)

        self._widget.lockButton.clicked.connect(self.toggleFocus)
        self._widget.positionSetButton.clicked.connect(self.moveZ)
        self._widget.autoTuneButton.clicked.connect(lambda: self.autoTune(step_size=0.5))

        # Set the initial values
        self.setPointSignal = 0
        self.locked = False
        self.aboutToLock = False
        self.zStackVar = False
        self.twoFociVar = False
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
        
        self.pTermData = np.zeros(self.buffer)
        self.iTermData = np.zeros(self.buffer)
        self.dTermData = np.zeros(self.buffer)
        
        # PID diagnostics
        self.p_term_data = np.zeros(self.buffer)
        self.i_term_data = np.zeros(self.buffer)
        self.d_term_data = np.zeros(self.buffer)

        # Starts acquisition. I don't know if this can cause problems if, the camera of interest is also used for acquisition
        self._master.detectorsManager[self.camera].startAcquisition()
        self.__processDataThread = ProcessDataThread(self)

        self.timer = Timer()
        self.timer.timeout.connect(self.update)
        self.timer.start(int(self.focusTime))
        self.startTime = perf_counter()
    
    # Following functions are just for controlling and setting different parameters
    def __del__(self):
        self.__processDataThread.quit()
        self.__processDataThread.wait()
        if hasattr(super(), '__del__'):
            super().__del__()

    def unlockFocus(self):
        """Release focus lock and reset controller state."""
        if self.locked:
            self.locked = False
            if hasattr(self, 'pid'):
                self.pid.reset()
            self._widget.lockButton.setChecked(False)
            self._widget.setpointLine.hide()  # Hide rather than remove
            self.__logger.debug("Focus lock released")

    def toggleFocus(self):
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

    def moveZ(self):
        target_voltage = float(self._widget.positionEdit.text())
        # Ensure voltage stays within -10 to +10V range
        target_voltage = max(-10, min(10, target_voltage))
        self._master.positionersManager[self.positioner].setPosition(target_voltage, 0)
        self.__logger.debug(f'Move Z-piezo to {target_voltage} V')

    # Update focus lock
    def update(self):
        # 1 Grab camera frame
        img = self.__processDataThread.grabCameraFrame()
        # 2 Pass camera frame and get back focusSignalPosition from ProcessDataThread
        self.setPointSignal = self.__processDataThread.update()
        # 3 Update PID with the new setPointSignal and get back the distance to move, send to
        # update the PID control, and then send the move-distance to the z-piezo
        if self.locked:
            voltage_adjustment = self.updatePID()
            self._updateDiagnostics()
            if abs(voltage_adjustment) > 0.002:  # 2mV threshold
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
            self._widget.updatePIDDisplay(
                self.timeData[1:self.currPoint],
                self.pTermData[1:self.currPoint],
                self.iTermData[1:self.currPoint],
                self.dTermData[1:self.currPoint]
            )
        else:
            self._widget.updateFocusPlot(
                self.timeData,
                self.setPointData,
                self.setPointSignal
            )
            self._widget.updatePIDDisplay(
                self.timeData,
                self.pTermData,
                self.iTermData,
                self.dTermData
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
        
        # Get PID correction
        correction = self.pid.update(self.setPointSignal)
        
        # Record terms for diagnostics
        if self.currPoint < self.buffer:
            self.p_term_data[self.currPoint] = self.pid.kp * self.pid._last_error
            self.i_term_data[self.currPoint] = self.pid.ki * self.pid._integral
            self.d_term_data[self.currPoint] = self.pid.kd * self.pid._last_derivative
        
        # Safety checks
        if abs(correction) > 1.0:  # 1V max correction
            self.__logger.warning("Large correction detected! Unlocking for safety.")
            self.unlockFocus()
            return 0
            
        return correction
    
    def updatePIDParameters(self, kp: float, ki: float, kd: float):
        """Thread-safe PID parameter updates with validation."""
        # Validate ranges
        kp = np.clip(kp, 0, 0.1)  # Example max P gain
        ki = np.clip(ki, 0, 0.01)  # Example max I gain
        kd = np.clip(kd, 0, 0.005) # Example max D gain
        
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
            self.pid = PID(self.setPointSignal, 
                          dt=self.focusTime/1000, 
                          kp=kp, ki=ki, kd=kd)
            self.lockPosition = current_voltage
            self.locked = True
            self._initDiagnosticsPlot()
            
    def _initDiagnosticsPlot(self):
        """Initialize PID terms visualization"""
        self._widget.pidPlot.clear()
        self._widget.p_term_curve = self._widget.pidPlot.plot(pen='r', name='P')
        self._widget.i_term_curve = self._widget.pidPlot.plot(pen='g', name='I')
        self._widget.d_term_curve = self._widget.pidPlot.plot(pen='b', name='D')
    
    def _updateDiagnostics(self):
        """Update PID terms visualization"""
        if self.currPoint > 1:
            x_data = self.timeData[:self.currPoint]
            self._widget.p_term_curve.setData(x_data, self.p_term_data[:self.currPoint])
            self._widget.i_term_curve.setData(x_data, self.i_term_data[:self.currPoint])
            self._widget.d_term_curve.setData(x_data, self.d_term_data[:self.currPoint])
            
    def clearPlots(self):
        """Clear all plot data"""
        self.focusCurve.clear()
        self.pTermCurve.clear()
        self.iTermCurve.clear()
        self.dTermCurve.clear()
            
    def autoTune(self, step_size=0.5, settle_threshold=0.01):
        """Automated tuning routine"""
        self.__logger.info("Starting auto-tuning...")
        
        # 1. Disable controller
        self.unlockFocus()
        
        # 2. Find system response
        test_voltages = [-step_size, 0, step_size]
        positions = []
        for v in test_voltages:
            self._master.positionersManager[self.positioner].move(v, 0)
            time.sleep(0.5)  # Settling time
            positions.append(self.setPointSignal)
        
        # Calculate system gain
        response_slope = (positions[2] - positions[0]) / (2 * step_size)  # px/V
        
        # 3. Ziegler-Nichols tuning (conservative)
        ku = 1.0 / abs(response_slope)  # Ultimate gain estimate
        pu = 0.5  # Estimated oscillation period (s) - adjust based on observations
        
        # PID coefficients (Pessen Integral Rule)
        kp = 0.7 * ku
        ki = 1.75 * ku / pu
        kd = 0.21 * ku * pu
        
        self.__logger.info(f"Suggested parameters: kp={kp:.4f}, ki={ki:.4f}, kd={kd:.4f}")
        
        # Apply to GUI
        self._widget.kpEdit.setText(f"{kp:.4f}")
        self._widget.kiEdit.setText(f"{ki:.4f}")
        self._widget.kdEdit.setText(f"{kd:.4f}")
        
        return kp, ki, kd


class ProcessDataThread(Thread):
    def __init__(self, controller, *args, **kwargs):
        self._controller = controller
        super().__init__(*args, **kwargs)

    def grabCameraFrame(self):
        detectorManager = self._controller._master.detectorsManager[self._controller.camera]
        self.latestimg = detectorManager.getLatestFrame()
        self.latestimg = np.swapaxes(self.latestimg, 0, 1)
        return self.latestimg

    def gaussian_1d(self, x, a, x0, sigma, offset):
        return a * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + offset

    def update(self):
        # Apply Gaussian filter
        imagearraygf = ndi.filters.gaussian_filter(self.latestimg, 7)
        
        # Find approximate center (Y-axis)
        centercoords = np.where(imagearraygf == np.array(imagearraygf.max()))
        y_center = centercoords[0][0]
        x_center = centercoords[1][0]
        
        # Extract horizontal line profile through brightest point
        line_profile = imagearraygf[y_center, :]
        x_data = np.arange(len(line_profile))
        
        try:
            # Fit 1D Gaussian to horizontal profile
            popt, _ = curve_fit(self.gaussian_1d, x_data, line_profile,
                               p0=[line_profile.max(), x_center, 10, line_profile.min()])
            x_fit_center = popt[1]  # This is our X-position measurement
        except:
            # Fallback to center of mass if fit fails
            x_fit_center = np.sum(x_data * line_profile) / np.sum(line_profile)
        
        return x_fit_center



class PID:
    """Discrete PID controller with anti-windup and filtering."""
    def __init__(self, setpoint, dt=0.001, kp=0, ki=0, kd=0):
        self.kp = kp          # Proportional gain (V/px)
        self.ki = ki          # Integral gain (V/(px·s))
        self.kd = kd          # Derivative gain (V/(px/s))
        self.setpoint = setpoint  # Target position (px)
        self.dt = dt          # Time step (s)
        
        # State variables
        self._last_error = 0
        self._integral = 0
        self._last_derivative = 0
        self._output = 0
        
        # Anti-windup limits
        self.integral_min = -10  # Minimum output voltage
        self.integral_max = 10   # Maximum output voltage
        
        # Low-pass filter for derivative term
        self.derivative_alpha = 0.2  # Smoothing factor (0.1-0.5)

    def update(self, current_value):
        error = self.setpoint - current_value
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (with anti-windup)
        self._integral += error * self.dt
        self._integral = np.clip(self._integral, self.integral_min, self.integral_max)
        i_term = self.ki * self._integral
        
        # Filtered derivative term
        raw_derivative = (error - self._last_error) / self.dt
        self._last_derivative = (self.derivative_alpha * raw_derivative + 
                               (1 - self.derivative_alpha) * self._last_derivative)
        d_term = self.kd * self._last_derivative
        
        # Store error for next iteration
        self._last_error = error
        
        # Sum all terms
        self._output = p_term + i_term + d_term
        return self._output
    
    def reset(self):
        """Reset controller state"""
        self._integral = 0
        self._last_error = 0
        self._last_derivative = 0

    def restart(self):
        self.started = False

    @property
    def started(self):
        return self._started

    @started.setter
    def started(self, value):
        self._started = value

    @property
    def setPoint(self):
        return self._setPoint

    @setPoint.setter
    def setPoint(self, value):
        self._setPoint = value

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