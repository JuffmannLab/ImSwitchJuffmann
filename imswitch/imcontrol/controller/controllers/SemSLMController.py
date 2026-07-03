from imswitch.imcommon.model import initLogger
from ..basecontrollers import ImConWidgetController
from slmsuite.holography.toolbox import phase
from PIL import Image
import numpy as np

class SemSLMController(ImConWidgetController):
    """Linked to SemSLMWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__logger = initLogger(self)

        self._widget.sigSetPresetClicked.connect(self.applyMask)
        self._widget.sigPresetChanged.connect(self.presetChanged)


    def presetChanged(self, bpm_file):
        presetPath = self._widget.getPresetPath()
        mask = str(presetPath) + "/" + bpm_file
        self._widget.updatePixmap(mask)

    def applyMask(self, clicked):

        #---- load current selected mask ----
        maskPath = str(self._widget.getPresetPath()) + "/" + self._widget.getCurrentMask()
        mask = Image.open(maskPath)
        mask = np.array(mask)[:, :, 0]

        if self._widget.enableFValue.isChecked():
            f = self._widget.getFValue()
            slm = self._master.SemSLMManager.getSLM()
            wav_um = self._master.SemSLMManager.getWavUm()
            f_eff = f / (wav_um * 1e-6)
            lens = phase.lens(slm, f_eff)
            mask = mask + lens

        self._master.SemSLMManager.writeMask(mask)
