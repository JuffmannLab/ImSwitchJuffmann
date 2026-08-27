import time
import numpy as np


class LiveProfileState:
    """Shared state for the latest LiveProfile data of each detector."""

    def __init__(self):
        self.profiles = {}
        self.roi_images = {}
        self.profile_modes = {}
        self.timestamps = {}

    def update(self, detector_name, profile, roi_image, profile_mode):
        self.profiles[detector_name] = np.asarray(profile).copy()
        self.roi_images[detector_name] = np.asarray(roi_image).copy()
        self.profile_modes[detector_name] = str(profile_mode)
        self.timestamps[detector_name] = time.strftime("%d%m%Y_%H%M%S")


liveprofile_state = LiveProfileState()
