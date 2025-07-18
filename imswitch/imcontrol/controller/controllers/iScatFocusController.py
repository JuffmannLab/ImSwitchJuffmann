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
        self._widget.sigCalibrate.connect(self.runCalibration)

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

        # Calibration storage
        self.volts_per_px = None  # Calibration slope (V/px)
        self.px_per_volt = None   # Inverse calibration (px/V)
        self.zero_offset_px = None # Position at 0V

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

    def runCalibration(self, from_V: float, to_V: float, steps: int):

        try:
            # 1. Prepare measurement points
            test_voltages = np.linspace(from_V, to_V, steps)
            positions = []
            
            # 2. Store initial position
            initial_V = self._master.positionersManager[self.positioner].get_abs()
            
            # 3. Collect data
            for v in test_voltages:
                self._master.positionersManager[self.positioner].setPosition(v, 0)
                time.sleep(1.0)
                
                # Capture multiple samples
                sample_pos = []
                for _ in range(10):  # Take 10 samples per voltage step
                    img = self.__processDataThread.grabCameraFrame()
                    pos = self.__processDataThread.getBeamPosition(img)
                    if pos is not None:
                        sample_pos.append(pos)
                    time.sleep(0.1)
                
                if not sample_pos:
                    raise ValueError(f"No valid positions at {v}V")
                    
                median_pos = np.median(sample_pos)
                positions.append(median_pos)
                self.__logger.debug(f"Voltage {v:.2f}V -> {median_pos:.2f} px")
            
            # 4. Robust linear regression
            coeffs, residuals, _, _ = np.linalg.lstsq(
                np.vstack([test_voltages, np.ones(len(test_voltages))]).T,
                positions,
                rcond=None
            )
            
            # 5. Validate results
            px_per_volt = coeffs[0]
            if abs(px_per_volt) < 1:  # Unrealistically small ratio
                raise ValueError(f"Implausible calibration: {px_per_volt:.2f} px/V")
            
            # 6. Store and update
            self.px_per_volt = px_per_volt
            self.volts_per_px = 1/px_per_volt
            self.zero_offset_px = coeffs[1]
            
            # 7. Restore original position
            self._master.positionersManager[self.positioner].setPosition(initial_V, 0)
            
            # 8. Update UI
            self._widget.updateCalibrationResult(
                slope=self.volts_per_px,
                intercept=self.zero_offset_px
            )
        
        except Exception as e:
            self.__logger.error(f"Calibration failed: {str(e)}")

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
            if abs(voltage_adjustment) > 0.001:  # 2mV threshold
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

        kp = np.clip(kp, 0.00000, 1)  # Example max P gain
        ki = np.clip(ki, 0.00000, 0.1)  # Example max I gain
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
        super().__init__(*args, **kwargs)
        self._controller = controller
        self._last_valid_position = 0  # Fallback position
        self._fit_fail_count = 0
        self._max_fit_fails = 3  # Allow 3 consecutive failures before fallback

    def grabCameraFrame(self):
        """Grab frame with error handling"""
        try:
            detector = self._controller._master.detectorsManager[self._controller.camera]
            img = detector.getLatestFrame()
            return np.swapaxes(img, 0, 1) if img is not None else None
        except Exception as e:
            self._controller._logger.error(f"Frame grab failed: {str(e)}")
            return None

    def getBeamPosition(self, img=None):
        """More robust position detection with full-frame analysis"""
        if img is None:
            img = self.grabCameraFrame()
            if img is None:
                return None
        
        try:
            # 1. Apply adaptive Gaussian filter
            sigma = max(img.shape) * 0.01  # Dynamic smoothing
            filtered = ndi.gaussian_filter(img, sigma=sigma)
            
            # 2. Find brightest region (avoid edge artifacts)
            center = np.array(filtered.shape) // 2
            roi_size = min(filtered.shape) // 3
            roi = filtered[
                center[0]-roi_size:center[0]+roi_size,
                center[1]-roi_size:center[1]+roi_size
            ]
            
            # 3. Subpixel fitting with error bounds
            com = ndi.center_of_mass(roi)
            global_com = (center - roi_size + np.array(com))[::-1]  # (x,y)
            
            # 4. Validate position
            if not np.all(np.isfinite(global_com)):
                raise ValueError("Invalid position detected")
                
            return global_com[0]  # Return x position
        
        except Exception as e:
            self._controller._logger.error(f"Position detection failed: {str(e)}")
            return None
        
    def analyzeFrame(self, img):
        """Main analysis method with calibration support"""
        if img is None:
            return self._last_valid_position

        try:
            # Gaussian filter with dynamic sigma based on image size
            sigma = min(img.shape) * 0.02  # ~2% of image size
            img_filtered = ndi.gaussian_filter(img, sigma=sigma)
            
            # Find brightest region
            coords = peak_local_max(img_filtered, num_peaks=1, min_distance=20)
            if len(coords) == 0:
                return self._last_valid_position
                
            y, x = coords[0]
            return self._fitSubpixelPosition(img_filtered, x, y)
            
        except Exception as e:
            self._controller._logger.warning(f"Analysis error: {str(e)}")
            return self._last_valid_position

    def _fitSubpixelPosition(self, img, approx_x, approx_y):
        """Robust subpixel fitting with fallback"""

        try:
            # Horizontal line profile
            line_profile = img[approx_y, max(0,approx_x-50):approx_x+50]
            x = np.arange(len(line_profile))
            
            # Gaussian fit
            popt, _ = curve_fit(
                self.gaussian_1d,
                x, line_profile,
                p0=[line_profile.max(), 50, 10, line_profile.min()],
                bounds=([0, 0, 1, 0], [np.inf, 100, 100, np.inf]))
            
            self._fit_fail_count = 0
            fitted_x = max(0, approx_x-50) + popt[1]
            self._last_valid_position = fitted_x
            return fitted_x
        
        except Exception as e:
            self._fit_fail_count += 1
            if self._fit_fail_count >= self._max_fit_fails:
                # Fallback to center of mass
                com = ndi.center_of_mass(img[max(0,approx_y-30):approx_y+30, 
                                           max(0,approx_x-30):approx_x+30])
                self._last_valid_position = approx_x - 30 + com[1]
                return self._last_valid_position
            return self._last_valid_position

    def gaussian_1d(self, x, a, x0, sigma, offset):
        """1D Gaussian model for fitting"""
        return a * np.exp(-((x - x0) ** 2) / (2 * sigma ** 2)) + offset

    def update(self):
        """Interface-compatible update method"""
        img = self.grabCameraFrame()
        return self.analyzeFrame(img)


class KalmanFilter:
    """Simple 1D Kalman filter for position and velocity estimation."""
    def __init__(self, initial_pos, initial_vel, dt=0.001, process_noise=0.1, measurement_noise=1.0):
        # State vector: [position, velocity]
        self.state = np.array([initial_pos, initial_vel])
        
        # State transition matrix
        self.F = np.array([[1, dt],
                          [0,  1]])
        
        # Process noise covariance
        self.Q = np.array([[dt**3/3, dt**2/2],
                          [dt**2/2,      dt]]) * process_noise
        
        # Measurement matrix (we only measure position)
        self.H = np.array([[1, 0]])
        
        # Measurement noise
        self.R = np.array([[measurement_noise]])
        
        # Covariance matrix
        self.P = np.eye(2) * 100  # Large initial uncertainty

    def predict(self):
        # Predict state
        self.state = self.F @ self.state
        # Predict covariance
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.state[0]  # Return predicted position

    def update(self, measurement):
        # Kalman gain
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state
        y = measurement - self.H @ self.state
        self.state = self.state + K @ y
        
        # Update covariance
        I = np.eye(2)
        self.P = (I - K @ self.H) @ self.P
        
        return self.state[0], self.state[1]  # Return position and velocity

class PID:
    """Discrete PID controller with Kalman filtering."""
    def __init__(self, setpoint, dt=0.001, kp=0, ki=0, kd=0):
        self.kp = kp          # Proportional gain (V/px)
        self.ki = ki          # Integral gain (V/(px·s))
        self.kd = kd          # Derivative gain (V/(px/s))
        self.setpoint = setpoint  # Target position (px)
        self.dt = dt          # Time step (s)
        
        self._last_error = 0
        self._integral = 0
        self._last_derivative = 0
        self._output = 0
        self.volts_per_px = None
        
        # Anti-windup limits
        self.integral_min = -10  # Minimum output voltage
        self.integral_max = 10   # Maximum output voltage
        
        # Low-pass filter for derivative term
        self.derivative_alpha = 0.2  # Smoothing factor (0.1-0.5)
        
        # Kalman filter (initialized on first measurement)
        self.kf = None
        self.last_position = 0
        self.last_velocity = 0

    def setCalibration(self, volts_per_px):
        """Update calibration values"""
        self.volts_per_px = volts_per_px

    def update(self, current_px):
        # Initialize Kalman filter on first measurement
        if self.kf is None:
            self.kf = KalmanFilter(current_px, 0, self.dt)
            self.last_position = current_px
        
        # Kalman filter predict step
        predicted_pos = self.kf.predict()
        
        # Kalman filter update step
        filtered_pos, filtered_vel = self.kf.update(current_px)
        
        # Store filtered values
        self.last_position = filtered_pos
        self.last_velocity = filtered_vel
        
        # Convert error to "effective volts" using filtered position
        error_px = self.setpoint - filtered_pos
        if self.volts_per_px:
            error = error_px * self.volts_per_px
        else:
            error = error_px  # Fallback (assumes 1:1)
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term (with anti-windup)
        self._integral += error * self.dt
        self._integral = np.clip(self._integral, self.integral_min, self.integral_max)
        i_term = self.ki * self._integral
        
        # Use filtered velocity for derivative term (better than finite difference)
        if self.volts_per_px:
            d_term = self.kd * (-filtered_vel * self.volts_per_px)
        else:
            d_term = self.kd * (-filtered_vel)
        
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
        if self.kf is not None:
            self.kf = KalmanFilter(self.last_position, self.last_velocity, self.dt)

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