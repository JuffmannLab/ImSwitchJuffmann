import time
import numpy as np


class LiveProfileState:
    """Small shared state for the latest LiveProfile data."""

    def __init__(self):
        self.profile = None
        self.roi_image = None
        self.profile_mode = None
        self.timestamp = None

    def update(self, profile, roi_image, profile_mode):
        self.profile = np.asarray(profile).copy()
        self.roi_image = np.asarray(roi_image).copy()
        self.profile_mode = str(profile_mode)
        self.timestamp = time.strftime("%d%m%Y_%H%M%S")


liveprofile_state = LiveProfileState()