import matplotlib.pyplot as plt
import numpy as np
import scipy.ndimage as ndi
from skimage.feature import peak_local_max
from scipy.optimize import curve_fit
from imswitch.imcommon.framework import Thread, Timer

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

    def generate_gaussian_laser(self,im_size=512,line_x=256,slope=0.2,sigma=10.0,peak=200):
        img = np.zeros((im_size, im_size), dtype=np.float32)

        for y in range(im_size):
            x0 = line_x + slope * (y - im_size // 2)
            xs = np.arange(im_size)
            img[y] = peak * np.exp(-0.5 * ((xs - x0) / sigma) ** 2)

        return img.astype(np.uint8)

    def test_getBeamPosition(self, img = None):
        if img is None:
            img = self.generate_gaussian_laser()
            if img is None:
                return self._last_valid_position

        try:
            nr_of_rows = img.shape[0]
            #for each row get the central position, index the function since tuple is returned
            row_positions = [ndi.center_of_mass(img[i])[0] for i in range(nr_of_rows)]
            x_position = np.sum(row_positions)/nr_of_rows
            return x_position

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

