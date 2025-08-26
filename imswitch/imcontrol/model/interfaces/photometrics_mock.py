from typing import Tuple

from imswitch.imcommon.model import initLogger
import numpy as np

class MockPhotometrics:
    def __init__(self):
        self.__logger = initLogger(self, tryInheritParent=True)

        self.sensor_size = (2048, 2048)
        self.name = "mock photometrics"
        self.roi = None
        self.binning = 1
        self.exp_time = 10
        self.exp_mode = 1
        self.readout_port = 1
        self.scan_line_time = 10

    def check_frame_status(self):
        return "MOCK_STATUS"

    def poll_frame(self):
        return np.zeros((self.sensor_size, self.sensor_size))

    def start_live(self):
        return
    def abort(self):
        return
    def finish(self):
        return

    def close(self):
        return