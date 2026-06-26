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
        self._widget.sigSledEnable.connect(self.sledEnable)
        self._widget.sigSledAIEnable.connect(self.sledEnableAI)
        self._widget.sigSledControlUpdate.connect(self.updateSledControl)

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
        self.sledEnableLine = self._setupInfo.iScatFocus.sledEnableLine
        self.sledAIEnableLine = self._setupInfo.iScatFocus.sledAIEnableLine
        self.sledControlChannel = self._setupInfo.iScatFocus.sledControlChannel

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

        #Disable SLED on startup

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

    def sledEnable(self, clicked):
        isChecked = self._widget.sledEnable.isChecked()
        self._master.nidaqManager.setDigital(self._setupInfo.iScatFocus, isChecked, line=self.sledEnableLine)


    def sledEnableAI(self, clicked):
        isChecked = self._widget.sledEnableAI.isChecked()
        if isChecked:
            enable = 1
        else:
            enable = 0
        self._master.nidaqManager.setDigital(self._setupInfo.iScatFocus, isChecked, line=self.sledAIEnableLine)

    def updateSledControl(self, voltage):
        self._master.nidaqManager.setAnalog(self._setupInfo.iScatFocus, voltage, min_val=0, max_val=2.5, channel=self.sledControlChannel)

    def runCalibration(self, from_V: float, to_V: float, steps: int):
        try:
            # 1. Prepare measurement points with hysteresis compensation
            test_voltages = np.linspace(from_V, to_V, steps)
            test_voltages = np.concatenate([test_voltages, test_voltages[::-1]])  # Forward and back
            
            # 2. Store initial position
            initial_V = self._master.positionersManager[self.positioner].get_abs()
            positions = []
            
            # 3. Enhanced measurement collection
            for i, v in enumerate(test_voltages):
                # Move with overshoot compensation
                if i > 0:
                    overshoot = 0.1 * (v - test_voltages[i-1])
                    self._master.positionersManager[self.positioner].setPosition(v + overshoot, 0)
                    time.sleep(0.1)
                
                # Final precise positioning
                self._master.positionersManager[self.positioner].setPosition(v, 0)
                
                # Dynamic settling time based on step size
                step_size = abs(v - test_voltages[i-1]) if i > 0 else 0
                settle_time = max(0.5, step_size * 0.5)  # 0.5s + 0.5s per volt
                time.sleep(settle_time)
                
                # Capture multiple samples with validation
                sample_pos = []
                for _ in range(10):
                    img = self.__processDataThread.grabCameraFrame()
                    pos = self.__processDataThread.getBeamPosition(img)
                    if pos is not None:
                        sample_pos.append(pos)
                    time.sleep(0.05)
                
                if len(sample_pos) < 5:
                    raise ValueError(f"Insufficient valid positions at {v}V")
                    
                # Use median and IQR filtering
                q75, q25 = np.percentile(sample_pos, [75, 25])
                iqr = q75 - q25
                valid_pos = [p for p in sample_pos if (q25 - 1.5*iqr) < p < (q75 + 1.5*iqr)]
                median_pos = np.median(valid_pos)
                positions.append(median_pos)
                
                self.__logger.debug(f"Voltage {v:.2f}V -> {median_pos:.2f} px (n={len(valid_pos)})")
            
            # 4. Split forward and backward measurements
            n = len(test_voltages)//2
            forward_voltages = test_voltages[:n]
            forward_positions = positions[:n]
            backward_voltages = test_voltages[n:]
            backward_positions = positions[n:]
            
            # 5. Two-way linear regression
            def fit_line(voltages, positions):
                A = np.vstack([voltages, np.ones(len(voltages))]).T
                return np.linalg.lstsq(A, positions, rcond=None)[0]
            
            m_forward, b_forward = fit_line(forward_voltages, forward_positions)
            m_backward, b_backward = fit_line(backward_voltages, backward_positions)
            
            # 6. Use average of both directions
            px_per_volt = (m_forward + m_backward) / 2
            zero_offset = (b_forward + b_backward) / 2
            
            # 7. Validate results
            if abs(px_per_volt) < 1:
                raise ValueError(f"Implausible calibration: {px_per_volt:.2f} px/V")
            
            # 8. Store and update
            self.px_per_volt = px_per_volt
            self.volts_per_px = 1/px_per_volt
            self.zero_offset_px = zero_offset
            
            # 9. Restore original position
            self._master.positionersManager[self.positioner].setPosition(initial_V, 0)
            
            # 10. Update UI with both forward and backward results
            self._widget.updateCalibrationResult(
                slope=self.volts_per_px,
                intercept=self.zero_offset_px,
                forward_slope=1/m_forward,
                backward_slope=1/m_backward
            )
            
            self.__logger.info(f"Calibration complete: {px_per_volt:.2f} px/V, "
                            f"Zero at {zero_offset:.2f} px")
            
        except Exception as e:
            self.__logger.error(f"Calibration failed: {str(e)}")
            raise

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
        """More robust position detection with dynamic ROI"""
        if img is None:
            img = self.grabCameraFrame()
            if img is None:
                return self._last_valid_position
        
        try:
            # Dynamic ROI based on last valid position
            if np.isfinite(self._last_valid_position):
                x_center = int(self._last_valid_position)
                roi_width = min(100, img.shape[1]//3)
                x_start = max(0, x_center - roi_width//2)
                x_end = min(img.shape[1], x_center + roi_width//2)
                roi = img[:, x_start:x_end]
            else:
                roi = img
            
            # Adaptive thresholding
            threshold = np.percentile(roi, 95)  # Use top 5% pixels
            mask = roi > threshold
            
            # Check if we have enough signal
            if np.sum(mask) < 10:
                return self._last_valid_position
                
            # Weighted center of mass
            y, x = ndi.center_of_mass(roi * mask)
            global_x = x + x_start if 'x_start' in locals() else x
            
            # Validate position
            if not 0 <= global_x < img.shape[1]:
                return self._last_valid_position
                
            # Low-pass filter to reduce jumps
            filtered_x = 0.8 * global_x + 0.2 * self._last_valid_position
            self._last_valid_position = filtered_x
            return filtered_x
            
        except Exception as e:
            self.__logger.warning(f"Position detection error: {str(e)}")
            return self._last_valid_position
        
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

import numpy as np

class PID:
    """Enhanced discrete PID controller with Kalman filtering and stability monitoring."""
    def __init__(self, setpoint, dt=0.001, kp=0, ki=0, kd=0):
        # Gains
        self._kp = kp          # Proportional gain (V/px)
        self._ki = ki          # Integral gain (V/(px·s))
        self._kd = kd          # Derivative gain (V/(px/s))

        self._started = False
        
        # Control parameters
        self._setpoint = setpoint  # Target position (px)
        self._dt = dt          # Time step (s)
        self.volts_per_px = None  # Calibration factor
        
        # State variables
        self._integral = 0
        self._last_error = 0
        self._last_derivative = 0 
        self._output = 0
        
        # Anti-windup and limits
        self.integral_min = -5  # Conservative limits
        self.integral_max = 5
        self.output_min = -10
        self.output_max = 10
        
        # Kalman filter setup
        self._kf = None
        self.last_position = 0
        self.last_velocity = 0
        
        # Stability monitoring
        self.error_history = []
        self.stability_counter = 0
        self.max_unstable_count = 10
        self.stable_threshold = 1.0  # px RMS error for stability
        
        # Dynamic control parameters
        self.derivative_alpha = 0.3  # Smoothing factor for derivative
        self.error_scaling = 1.0     # Dynamic error scaling

    def setCalibration(self, volts_per_px):
        """Update calibration values with validation"""
        if abs(volts_per_px) < 1e-6:  # Avoid division by zero
            raise ValueError("Calibration factor too small")
        self.volts_per_px = volts_per_px

    def update(self, current_px):
        """
        Update controller with new measurement.
        Returns control output in volts.
        """
        # Initialize Kalman filter if needed
        if self._kf is None:
            self._init_kalman(current_px)
        
        # Get filtered position and velocity estimates
        filtered_pos, filtered_vel = self._update_kalman(current_px)
        
        # Calculate error with dynamic scaling
        error_px, error = self._calculate_error(filtered_pos)
        
        # Calculate PID terms
        p_term, i_term, d_term = self._calculate_terms(error, filtered_vel)
        
        # Combine terms with output limiting
        self._output = self._limit_output(p_term + i_term + d_term)
        
        # Monitor stability
        self._check_stability(error_px)
        
        return self._output

    def _init_kalman(self, current_px):
        """Initialize Kalman filter with reasonable defaults"""
        self._kf = KalmanFilter(
            initial_pos=current_px,
            initial_vel=0,
            dt=self._dt,
            process_noise=0.1,  # Adjust based on your system dynamics
            measurement_noise=1.0  # Should match your measurement variance
        )
        self.last_position = current_px
        self.last_velocity = 0

    def _update_kalman(self, current_px):
        """Update Kalman filter and return filtered estimates"""
        self._kf.predict()
        filtered_pos, filtered_vel = self._kf.update(current_px)
        self.last_position = filtered_pos
        self.last_velocity = filtered_vel
        return filtered_pos, filtered_vel

    def _calculate_error(self, filtered_pos):
        """Calculate error with dynamic scaling"""
        error_px = self._setpoint - filtered_pos
        
        # Dynamic error scaling - reduces aggression for large errors
        self.error_scaling = min(1.0, abs(error_px)/5.0)  # Scale down large errors
        
        if self.volts_per_px:
            error = error_px * self.error_scaling * self.volts_per_px
        else:
            error = error_px * self.error_scaling
            
        return error_px, error

    def _calculate_terms(self, error, filtered_vel):
        """Calculate PID terms with anti-windup and filtering"""
        # Proportional term
        p_term = self._kp * error
        
        # Integral term with conditional integration and anti-windup
        if abs(error) < 5:  # Only integrate when close to target
            self._integral += error * self._dt
        else:
            self._integral *= 0.95  # Leaky integration
        
        self._integral = np.clip(self._integral, self.integral_min, self.integral_max)
        i_term = self._ki * self._integral
        
        # Derivative term using filtered velocity
        if self.volts_per_px:
            d_term = self._kd * (-filtered_vel * self.volts_per_px)
        else:
            d_term = self._kd * (-filtered_vel)
            
        # Apply low-pass filtering to derivative term
        d_term = self.derivative_alpha * d_term + (1 - self.derivative_alpha) * self._last_derivative
        self._last_derivative = d_term
        
        return p_term, i_term, d_term

    def _limit_output(self, output):
        """Apply output limits with anti-windup compensation"""
        limited_output = np.clip(output, self.output_min, self.output_max)
        
        # Anti-windup: only integrate if not saturating
        if output != limited_output:
            self._integral -= (output - limited_output) * self._dt
            
        return limited_output

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
        """Reset controller state while preserving calibration"""
        self._integral = 0
        self._last_error = 0
        self._last_derivative = 0
        self.error_history = []
        self.stability_counter = 0
        
        if self._kf is not None:
            self._kf = KalmanFilter(
                self.last_position,
                self.last_velocity,
                self._dt
            )

    def restart(self):
        self._started = False

    @property
    def terms(self):
        """Return current PID terms for monitoring"""
        return {
            'p': self._kp * self._last_error,
            'i': self._ki * self._integral,
            'd': self._last_derivative
        }

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
    
    @property
    def kf(self):
        return self._kf
    
    @kf.setter
    def kf(self, value):
        self._kf = value