from imswitch.imcommon.model import initLogger
from slmsuite.holography.toolbox import phase
from slmsuite.holography import toolbox

from slmsuite.hardware.slms.meadowlark import Meadowlark

class SemSLMManager():
    def __init__(self, setupInfo):
        self.__logger = initLogger(self)
        self._setupInfo = setupInfo
        #probably better to do this via the .json file
        self.wav_um = 1.035
        self.shift = (0, 0)
        self.settle = 0.2
        self.lut_path = r'C:\Program Files\Meadowlark Optics\Blink 1920 HDMI\LUT Files\lut_1064_scaled_0.9727443609022557.lut'
        self.slm = Meadowlark(lut_path=self.lut_path, wav_um=self.wav_um, settle_time_s=self.settle, verbose=True)

    def writeMask(self, mask):
        self.slm.write(mask)

    def getSLM(self):
        return self.slm

    def getWavUm(self):
        return self.wav_um



